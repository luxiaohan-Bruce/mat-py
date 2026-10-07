"""Two-stage UC/reserve/compute commitment with full-path scenario recourse."""
from __future__ import annotations
import gurobipy as gp
from . import grid


def build(m,d,fixed_first_stage=None):
    T=d['T']; dt=d['dt_hours']; D=len(d['sites']); G=len(d['uc'])
    uc=grid.add_uc(m,d)
    blocks=m.addVars(D,T,vtype=gp.GRB.INTEGER,lb=0,ub=48,name='reserved_compute_blocks')
    starts=m.addVars(D,T,vtype=gp.GRB.INTEGER,lb=0,ub=48,name='compute_starts')
    rup=m.addVars(G,T,lb=0,name='up_reserve')
    rdown=m.addVars(G,T,lb=0,name='down_reserve')
    for a,site in enumerate(d['sites']):
        for t in range(T):
            previous=blocks[a,t-1] if t else site['initial_blocks']
            m.addConstr(starts[a,t]>=blocks[a,t]-previous)
            blocks[a,t].Start=48
            starts[a,t].Start=48-site['initial_blocks'] if not t else 0
    stages=[]
    for si,s in enumerate([d['nominal']]+d['scenarios']):
        prefix='nominal' if si==0 else f's{si-1}'
        pg=grid.add_dispatch(m,d,uc,prefix)
        facility=m.addVars(D,T,lb=0,name=prefix+'_facility')
        imports=m.addVars(D,T,lb=0,name=prefix+'_import')
        charge=m.addVars(D,T,lb=0,name=prefix+'_charge')
        discharge=m.addVars(D,T,lb=0,name=prefix+'_discharge')
        charging=m.addVars(D,T,vtype=gp.GRB.BINARY,name=prefix+'_charging')
        energy=m.addVars(D,T+1,lb=0,name=prefix+'_energy')
        service=m.addVars([(k,t) for k,c in enumerate(d['cohorts']) for t in range(c['release'],c['deadline'])],
                         lb=0,name=prefix+'_training_rate')
        renew=m.addVars(len(d['renewables']),T,lb=0,name=prefix+'_renewables')
        for k,c in enumerate(d['cohorts']):
            m.addConstr(dt*gp.quicksum(service[k,t] for t in range(c['release'],c['deadline']))==c['work_block_hours'])
        for a,site in enumerate(d['sites']):
            for t in range(T+1): energy[a,t].UB=site['battery_energy_mwh']
            energy[a,0].LB=energy[a,0].UB=site['initial_energy_mwh']
            energy[a,T].LB=energy[a,T].UB=site['initial_energy_mwh']
            for t in range(T):
                inf=s['inference_blocks'][t][a]
                training=gp.quicksum(service[k,t] for k,c in enumerate(d['cohorts'])
                                    if c['site']==a and (k,t) in service)
                m.addConstr(inf+training<=blocks[a,t])
                m.addConstr(facility[a,t]==site['pue']*(site['idle_it_mw']+
                    site['idle_mw_per_block']*blocks[a,t]+site['dynamic_mw_per_busy_block']*(inf+training)))
                facility[a,t].UB=imports[a,t].UB=site['pcc_max_mw']
                m.addConstr(charge[a,t]<=site['battery_power_mw']*charging[a,t])
                m.addConstr(discharge[a,t]<=site['battery_power_mw']*(1-charging[a,t]))
                m.addConstr(imports[a,t]==facility[a,t]+charge[a,t]-discharge[a,t])
                m.addConstr(energy[a,t+1]==energy[a,t]+dt*(site['eta_charge']*charge[a,t]-discharge[a,t]/site['eta_discharge']))
                critical=site['pue']*(site['idle_it_mw']+
                    (site['idle_mw_per_block']+site['dynamic_mw_per_busy_block'])*inf*site['critical_inference_fraction'])
                reserve=critical*site['ups_hours']/site['eta_discharge']
                m.addConstr(gp.LinExpr(critical)<=site['battery_power_mw'])
                m.addConstr(energy[a,t]>=reserve); m.addConstr(energy[a,t+1]>=reserve)
                charging[a,t].Start=0
        for r in range(len(d['renewables'])):
            for t in range(T): renew[r,t].UB=s['renewable_mw'][t][r]
        net=grid.add_network(m,d,pg,imports,d['sites'],prefix,renewable=renew)
        energy_cost=grid.energy_cost(d,pg)
        degradation=dt*gp.quicksum(site['battery_throughput_cost_per_mwh']*(charge[a,t]+discharge[a,t])
                                   for a,site in enumerate(d['sites']) for t in range(T))
        curtailment=dt*d['curtailment_cost_per_mwh']*gp.quicksum(s['renewable_mw'][t][r]-renew[r,t]
                                                              for r in range(len(d['renewables'])) for t in range(T))
        stages.append(dict(pg=pg,facility=facility,imports=imports,charge=charge,discharge=discharge,
                           charging=charging,energy=energy,service=service,renewable=renew,network=net,
                           energy_cost=energy_cost,degradation=degradation,curtailment_cost=curtailment,
                           operating_cost=energy_cost+degradation+curtailment))
    nominal=stages[0]; pg0=nominal['pg']
    for g,gen in enumerate(d['network']['gens']):
        for t in range(T):
            m.addConstr(pg0[g,t]+rup[g,t]<=gen['Pmax']*uc['on'][g,t])
            m.addConstr(pg0[g,t]-rdown[g,t]>=d['uc'][g]['pmin_mw']*uc['on'][g,t])
            deliverable=d['uc'][g]['ramp_mw_per_hour']*d['reserve_response_hours']
            m.addConstr(rup[g,t]<=deliverable*uc['on'][g,t])
            m.addConstr(rdown[g,t]<=deliverable*uc['on'][g,t])
            for stage in stages[1:]:
                m.addConstr(stage['pg'][g,t]-pg0[g,t]<=rup[g,t])
                m.addConstr(pg0[g,t]-stage['pg'][g,t]<=rdown[g,t])
    for t in range(T):
        demand=sum(b['Pd'] for b in d['network']['buses'])*d['background_multiplier'][t]+gp.quicksum(nominal['imports'][a,t] for a in range(D))
        m.addConstr(gp.quicksum(rup[g,t] for g in range(G))>=d['reserve_fraction']*demand)
        m.addConstr(gp.quicksum(rdown[g,t] for g in range(G))>=d['reserve_fraction']*demand)
    reserve_cost=dt*gp.quicksum(d['reserve_up_cost_per_mw_hour']*rup[g,t]+d['reserve_down_cost_per_mw_hour']*rdown[g,t]
                               for g in range(G) for t in range(T))
    compute_starts=gp.quicksum(site['block_start_cost']*starts[a,t] for a,site in enumerate(d['sites']) for t in range(T))
    expectation=gp.quicksum(s['probability']*stage['operating_cost'] for s,stage in zip(d['scenarios'],stages[1:]))
    eta=m.addVar(lb=0,name='var_threshold')
    excess=m.addVars(len(d['scenarios']),lb=0,name='cvar_excess')
    for s,stage in enumerate(stages[1:]): m.addConstr(excess[s]>=stage['operating_cost']-eta)
    cvar=eta+gp.quicksum(s['probability']*excess[i] for i,s in enumerate(d['scenarios']))/(1-d['cvar_alpha'])
    costs=dict(startup=uc['startup_cost'],no_load=uc['no_load_cost'],reserve=reserve_cost,
               compute_starts=compute_starts,expected_operation=expectation,risk_premium=d['risk_weight']*cvar)
    m.setObjective(gp.quicksum(costs.values()))
    if fixed_first_stage is not None:
        m.update()
        for key in ['on','start','stop']:
            grid.fixed_array(uc[key],fixed_first_stage['uc'][key],G,T)
        for variables,key,n in [(blocks,'gpu_blocks',D),(starts,'gpu_starts',D),(pg0,'pg0_mw',G),
                                (rup,'reserve_up_mw',G),(rdown,'reserve_down_mw',G)]:
            grid.fixed_array(variables,fixed_first_stage[key],n,T)
    def one_stage(stage):
        out=grid.dispatch_solution(stage['pg'],stage['network'],d)
        out.update(imports_mw=grid.values(stage['imports'],D,T),facility_mw=grid.values(stage['facility'],D,T),
            charge_mw=grid.values(stage['charge'],D,T),discharge_mw=grid.values(stage['discharge'],D,T),
            charging=grid.values(stage['charging'],D,T),energy_mwh=grid.values(stage['energy'],D,T+1),
            renewable_mw=grid.values(stage['renewable'],len(d['renewables']),T),
            training_blocks=[[float(stage['service'][k,t].X) if (k,t) in stage['service'] else 0.
                              for k in range(len(d['cohorts']))] for t in range(T)],
            operating_cost=float(stage['operating_cost'].getValue()))
        return out
    def extract():
        first=dict(uc=grid.uc_solution(uc,d),gpu_blocks=grid.values(blocks,D,T),gpu_starts=grid.values(starts,D,T),
                   pg0_mw=grid.values(pg0,G,T),reserve_up_mw=grid.values(rup,G,T),reserve_down_mw=grid.values(rdown,G,T))
        return dict(first_stage=first,nominal=one_stage(nominal),scenarios=[one_stage(x) for x in stages[1:]],
                    cvar_eta=eta.X,cvar_excess=[excess[s].X for s in range(len(d['scenarios']))])
    return dict(extract=extract,costs=costs,baseline_note='Ensemble-mean first-stage policy fixed; identical reserve floors and full-scenario recourse')
