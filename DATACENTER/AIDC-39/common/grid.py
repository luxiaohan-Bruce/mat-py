"""Shared DC physics and UC. Business models are separate modules."""
from __future__ import annotations

import math
import gurobipy as gp
import numpy as np


def matrices(net, outage=None):
    ids = [int(b['bus_i']) for b in net['buses']]
    index = {b:i for i,b in enumerate(ids)}
    branches = [b for b in net['branches'] if b['status'] and b['id'] != outage]
    a = np.zeros((len(branches),len(ids)))
    beta = []; phase = []
    for l,b in enumerate(branches):
        a[l,index[int(b['fbus'])]]=1; a[l,index[int(b['tbus'])]]=-1
        beta.append(net['baseMVA']/(b['x']*(b['ratio'] or 1.)))
        phase.append(math.radians(b['angle']))
    beta=np.array(beta); phase=np.array(phase)
    B=a.T@(beta[:,None]*a)
    ref=index[31]; free=[i for i in range(len(ids)) if i!=ref]
    inv=np.zeros_like(B)
    inv[np.ix_(free,free)]=np.linalg.inv(B[np.ix_(free,free)])
    return dict(ids=ids,index=index,branches=branches,A=a,beta=beta,phase=phase,
                B=B,inverse=inv,ptdf=(beta[:,None]*a)@inv)


def add_uc(m,d):
    T=d['T']; G=len(d['network']['gens']); dt=d['dt_hours']
    u=m.addVars(G,T,vtype=gp.GRB.BINARY,name='on')
    v=m.addVars(G,T,vtype=gp.GRB.BINARY,name='start')
    w=m.addVars(G,T,vtype=gp.GRB.BINARY,name='stop')
    for g,p in enumerate(d['uc']):
        for t in range(T):
            if p['must_run']:
                u[g,t].LB=u[g,t].UB=1; v[g,t].UB=w[g,t].UB=0
            previous=u[g,t-1] if t else p['initial_on']
            m.addConstr(u[g,t]-previous==v[g,t]-w[g,t])
            m.addConstr(v[g,t]+w[g,t]<=1)
            up=p['min_up_slots']; down=p['min_down_slots']
            m.addConstr(gp.quicksum(v[g,k] for k in range(max(0,t-up+1),t+1))<=u[g,t])
            m.addConstr(gp.quicksum(w[g,k] for k in range(max(0,t-down+1),t+1))<=1-u[g,t])
            if t+up>T: v[g,t].UB=0
            if t+down>T: w[g,t].UB=0
            remaining=(up if p['initial_on'] else down)-p['initial_status_age_slots']
            if t<remaining:
                m.addConstr(u[g,t]==p['initial_on'])
    startup=gp.quicksum(p['startup_cost']*v[g,t]+p['shutdown_cost']*w[g,t]
                        for g,p in enumerate(d['uc']) for t in range(T))
    no_load=dt*gp.quicksum(p['no_load_cost_per_hour']*u[g,t]
                          for g,p in enumerate(d['uc']) for t in range(T))
    return dict(on=u,start=v,stop=w,startup_cost=startup,no_load_cost=no_load)


def add_dispatch(m,d,uc,name):
    T=d['T']; dt=d['dt_hours']; gens=d['network']['gens']
    p=m.addVars(len(gens),T,lb=0.,name=name+'_pg')
    for g,gen in enumerate(gens):
        spec=d['uc'][g]
        for t in range(T):
            m.addConstr(p[g,t]<=gen['Pmax']*uc['on'][g,t])
            m.addConstr(p[g,t]>=spec['pmin_mw']*uc['on'][g,t])
            if t:
                ramp=spec['ramp_mw_per_hour']*dt
                m.addConstr(p[g,t]-p[g,t-1]<=ramp*uc['on'][g,t-1]+gen['Pmax']*uc['start'][g,t])
                m.addConstr(p[g,t-1]-p[g,t]<=ramp*uc['on'][g,t]+gen['Pmax']*uc['stop'][g,t])
    return p


def energy_cost(d,pg):
    return d['dt_hours']*gp.quicksum(g['c1']*pg[i,t] for i,g in enumerate(d['network']['gens']) for t in range(d['T']))


def add_network(m,d,pg,imports,sites,name,renewable=None,security=False):
    net=d['network']; T=d['T']; mat=matrices(net)
    idx=mat['index']; N=len(net['buses']); L=len(net['branches'])
    theta=m.addVars(N,T,lb=-gp.GRB.INFINITY,name=name+'_theta')
    flow=m.addVars(L,T,lb=-gp.GRB.INFINITY,name=name+'_flow')
    for t in range(T):
        theta[idx[31],t].LB=theta[idx[31],t].UB=0.
        for l,b in enumerate(net['branches']):
            a,z=idx[int(b['fbus'])],idx[int(b['tbus'])]
            flow[l,t].LB=-b['rateA']; flow[l,t].UB=b['rateA']
            m.addConstr(flow[l,t]==mat['beta'][l]*(theta[a,t]-theta[z,t]-mat['phase'][l]))
            m.addConstr(theta[a,t]-theta[z,t]>=math.radians(b['angmin']))
            m.addConstr(theta[a,t]-theta[z,t]<=math.radians(b['angmax']))
        for i,b in enumerate(net['buses']):
            bus=int(b['bus_i'])
            supply=gp.quicksum(pg[g,t] for g,x in enumerate(net['gens']) if int(x['bus'])==bus)
            if renewable is not None:
                supply+=gp.quicksum(renewable[r,t] for r,x in enumerate(d['renewables']) if x['bus']==bus)
            demand=b['Pd']*d['background_multiplier'][t]+gp.quicksum(imports[k,t] for k,s in enumerate(sites) if s['bus']==bus)
            m.addConstr(supply-demand==gp.quicksum(mat['A'][l,i]*flow[l,t] for l in range(L) if mat['A'][l,i]))
    if security:
        # Exact preventive DC contingency constraints for this fixed topology.
        # Reuse base flow variables: each row has at most two coefficients.
        assert np.max(np.abs(mat['phase']))==0
        for c in d['contingencies']:
            br=net['branches'][c]
            h=mat['ptdf'][:,idx[int(br['fbus'])]]-mat['ptdf'][:,idx[int(br['tbus'])]]
            if abs(1-h[c])<1e-9: raise ValueError('Islanding outage in security set')
            lodf=h/(1-h[c]); lodf[c]=-1.
            for l,b in enumerate(net['branches']):
                if l==c: continue
                lo=max(-b['rateA'],mat['beta'][l]*math.radians(b['angmin']))
                hi=min(b['rateA'],mat['beta'][l]*math.radians(b['angmax']))
                for t in range(T):
                    f=flow[l,t]+float(lodf[l])*flow[c,t]
                    m.addConstr(f>=lo); m.addConstr(f<=hi)
    return dict(theta=theta,flow=flow)


def values(x,n,T):
    return [[float(x[i,t].X if hasattr(x[i,t],'X') else x[i,t]) for i in range(n)] for t in range(T)]


def uc_solution(uc,d):
    return {key:values(uc[key],len(d['uc']),d['T']) for key in ['on','start','stop']}


def dispatch_solution(pg,network,d):
    return dict(pg_mw=values(pg,len(d['uc']),d['T']),
                theta_rad=values(network['theta'],39,d['T']),
                flow_mw=values(network['flow'],46,d['T']))


def fixed_array(vars_,array,n,T):
    for i in range(n):
        for t in range(T):
            val=float(array[t][i])
            if vars_[i,t].VType in (gp.GRB.BINARY,gp.GRB.INTEGER): val=round(val)
            vars_[i,t].LB=val; vars_[i,t].UB=val
