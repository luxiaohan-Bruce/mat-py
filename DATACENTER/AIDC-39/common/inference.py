"""Replica autoscaling and latency-constrained routing with preventive line N-1."""
from __future__ import annotations
import gurobipy as gp
from . import grid


def build(m,d,baseline=False):
    T=d['T']; D=len(d['sites']); M=len(d['services']); R=d['n_regions']; dt=d['dt_hours']
    n=m.addVars(D,M,T,vtype=gp.GRB.INTEGER,lb=0,ub=48,name='replicas')
    start=m.addVars(D,M,T,vtype=gp.GRB.INTEGER,lb=0,ub=48,name='replica_boot')
    stop=m.addVars(D,M,T,vtype=gp.GRB.INTEGER,lb=0,ub=48,name='replica_stop')
    route=m.addVars(R,M,D,T,lb=0,name='requests_per_second')
    pdc=m.addVars(D,T,lb=0,name='aidc_import')
    for a,site in enumerate(d['sites']):
        for k,s in enumerate(d['services']):
            for t in range(T):
                prev=n[a,k,t-1] if t else d['initial_replicas'][a][k]
                new=start[a,k,t-1] if t else 0
                m.addConstr(n[a,k,t]==prev+new-stop[a,k,t])
                m.addConstr(n[a,k,t]>=gp.quicksum(start[a,k,j] for j in range(max(0,t-d['minimum_active_slots']),t)))
                if t+d['minimum_active_slots']>=T: start[a,k,t].UB=0
                served=gp.quicksum(route[r,k,a,t] for r in range(R))
                m.addConstr(served<=s['capacity_rps']*n[a,k,t])
                n[a,k,t].Start=d['initial_replicas'][a][k]
                start[a,k,t].Start=stop[a,k,t].Start=0
                if baseline:
                    n[a,k,t].LB=n[a,k,t].UB=d['baseline_replicas'][a][k]
                    start[a,k,t].UB=stop[a,k,t].UB=0
        for t in range(T):
            m.addConstr(gp.quicksum(n[a,k,t]+start[a,k,t] for k in range(M))<=site['blocks'])
            m.addConstr(gp.quicksum(s['memory_gb']*(n[a,k,t]+start[a,k,t]) for k,s in enumerate(d['services']))<=site['memory_gb'])
            traffic=gp.quicksum(s['megabits_per_request']*route[r,k,a,t]/1000
                                for r in range(R) for k,s in enumerate(d['services']))
            m.addConstr(traffic<=site['bandwidth_gbps'])
            power=site['idle_it_mw']+gp.quicksum(s['active_idle_mw']*n[a,k,t]+
                site['boot_mw_per_block']*start[a,k,t]+s['dynamic_mw_at_capacity']/s['capacity_rps']*
                gp.quicksum(route[r,k,a,t] for r in range(R)) for k,s in enumerate(d['services']))
            m.addConstr(pdc[a,t]==site['pue']*power)
            pdc[a,t].UB=site['pcc_max_mw']
    for r in range(R):
        for k,s in enumerate(d['services']):
            for t in range(T):
                m.addConstr(gp.quicksum(route[r,k,a,t] for a in range(D))==d['demand_rps'][t][r][k])
                for a in range(D):
                    if d['latency_ms'][r][a]+s['processing_ms']>s['slo_ms']:
                        route[r,k,a,t].UB=0
                    route[r,k,a,t].Start=d['demand_rps'][t][r][k] if a==r//2 else 0
                    if baseline:
                        val=d['demand_rps'][t][r][k] if a==r//2 else 0
                        # A forbidden route must remain forbidden, even for baseline.
                        m.addConstr(route[r,k,a,t]==val)
        for a in range(D):
            for t in range(T):
                m.addConstr(gp.quicksum(s['megabits_per_request']*route[r,k,a,t]/1000
                                       for k,s in enumerate(d['services']))<=d['link_gbps'][r][a])
    uc=grid.add_uc(m,d); pg=grid.add_dispatch(m,d,uc,'base')
    net=grid.add_network(m,d,pg,pdc,d['sites'],'base',security=True)
    boots=gp.quicksum((s['startup_cost_per_block']+s['deploy_cost_per_replica'])*start[a,k,t]
                     for a,s in enumerate(d['sites']) for k in range(M) for t in range(T))
    traffic_cost=gp.quicksum(d['route_cost_per_million_requests'][r][a]*dt*3600/1e6*route[r,k,a,t]
                             for r in range(R) for k in range(M) for a in range(D) for t in range(T))
    costs=dict(energy=grid.energy_cost(d,pg),startup=uc['startup_cost'],no_load=uc['no_load_cost'],
               replica_starts=boots,communication=traffic_cost)
    m.setObjective(gp.quicksum(costs.values()))
    def extract():
        out=grid.dispatch_solution(pg,net,d)
        out.update(uc=grid.uc_solution(uc,d),imports_mw=grid.values(pdc,D,T),
            replicas=[[[n[a,k,t].X for k in range(M)] for a in range(D)] for t in range(T)],
            replica_boot=[[[start[a,k,t].X for k in range(M)] for a in range(D)] for t in range(T)],
            replica_stop=[[[stop[a,k,t].X for k in range(M)] for a in range(D)] for t in range(T)],
            routes_rps=[[[[route[r,k,a,t].X for a in range(D)] for k in range(M)] for r in range(R)] for t in range(T)],
            checked_contingencies=list(d['contingencies']))
        return out
    return dict(extract=extract,costs=costs,baseline_note='Fixed initial peak replicas; nearest-site routing; identical 35 line contingencies')
