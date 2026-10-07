"""Time-indexed, nonpreemptive gang-training scheduling with UC."""
from __future__ import annotations
import math
import gurobipy as gp
from . import grid


def candidates(d):
    dt=d['dt_hours']; out=[]
    for j,job in enumerate(d['jobs']):
        for k,mode in enumerate(d['modes']):
            duration=math.ceil(job['work_block_hours']/(job['blocks']*mode['speed']*dt)-1e-10)
            for start in range(job['release'],job['deadline']-duration+1):
                out.append((j,k,start,duration))
    return out


def earliest_deadline_schedule(d):
    usage=[0]*d['T']; choices={}
    for j in sorted(range(len(d['jobs'])),key=lambda j:(d['jobs'][j]['deadline'],d['jobs'][j]['release'],j)):
        job=d['jobs'][j]
        k=max(range(len(d['modes'])),key=lambda k:d['modes'][k]['speed'])
        length=math.ceil(job['work_block_hours']/(job['blocks']*d['modes'][k]['speed']*d['dt_hours'])-1e-10)
        for t in range(job['release'],job['deadline']-length+1):
            if max(usage[t:t+length])+job['blocks']<=d['site']['blocks']:
                choices[j]=(k,t)
                for q in range(t,t+length): usage[q]+=job['blocks']
                break
        if j not in choices:
            return None
    return choices


def build(m,d,baseline=False):
    T=d['T']; dt=d['dt_hours']; cs=candidates(d)
    x=m.addVars(len(cs),vtype=gp.GRB.BINARY,name='job_start_mode')
    by_job=[[] for _ in d['jobs']]; active=[[] for _ in range(T)]
    for i,(j,k,start,length) in enumerate(cs):
        by_job[j].append(i)
        for t in range(start,start+length): active[t].append(i)
        witness=d['jobs'][j]
        x[i].Start=float((k,start)==(witness['witness_mode'],witness['witness_start']))
    for js in by_job: m.addConstr(gp.quicksum(x[i] for i in js)==1)
    pdc=m.addVars(1,T,lb=0,ub=d['site']['pcc_max_mw'],name='aidc_import')
    for t in range(T):
        m.addConstr(gp.quicksum(d['jobs'][cs[i][0]]['blocks']*x[i] for i in active[t])<=d['site']['blocks'])
        m.addConstr(pdc[0,t]==d['site']['pue']*(d['site']['idle_it_mw']+
            gp.quicksum(d['jobs'][cs[i][0]]['blocks']*d['modes'][cs[i][1]]['mw_per_block']*x[i] for i in active[t])))
    uc=grid.add_uc(m,d); pg=grid.add_dispatch(m,d,uc,'base')
    net=grid.add_network(m,d,pg,pdc,[d['site']],'base')
    wait=gp.quicksum(d['jobs'][j]['wait_cost_per_hour']*(start+length-d['jobs'][j]['release'])*dt*x[i]
                    for i,(j,k,start,length) in enumerate(cs))
    costs=dict(energy=grid.energy_cost(d,pg),startup=uc['startup_cost'],no_load=uc['no_load_cost'],job_flow_time=wait)
    m.setObjective(gp.quicksum(costs.values()))
    for g in range(len(d['uc'])):
        for t in range(T):
            uc['on'][g,t].Start=1; uc['start'][g,t].Start=uc['stop'][g,t].Start=0
    if baseline:
        chosen=earliest_deadline_schedule(d)
        if chosen is None:
            # Deliberately infeasible baseline, explicitly explained in report.
            m.addConstr(gp.LinExpr()>=1,name='edf_schedule_not_found')
        else:
            for i,(j,k,t,length) in enumerate(cs):
                x[i].LB=x[i].UB=float(chosen[j]==(k,t))
    def extract():
        out=grid.dispatch_solution(pg,net,d)
        out.update(uc=grid.uc_solution(uc,d),imports_mw=grid.values(pdc,1,T),
                   jobs=[dict(job=j,mode=k,start=t,duration=length)
                         for i,(j,k,t,length) in enumerate(cs) if x[i].X>.5])
        return out
    return dict(extract=extract,costs=costs,baseline_note='EDF, fastest mode, earliest available contiguous placement')
