"""Independent checks of saved numeric schedules. No Gurobi/model imports.

Contingency verification rebuilds each network and solves its nodal equations;
it deliberately does not use the solver's LODF formulation or constraint slacks.
"""
from __future__ import annotations
import math
import numpy as np


class Checks:
    def __init__(self): self.residuals={}; self.tolerances={}
    def put(self,key,error,tol=1e-4):
        value=float(np.max(np.asarray(error),initial=0.))
        if not math.isfinite(value): raise ValueError(f'Non-finite residual: {key}')
        self.residuals[key]=max(self.residuals.get(key,0.),value)
        self.tolerances[key]=tol
    def eq(self,key,a,b=0.,tol=1e-4): self.put(key,np.abs(np.asarray(a)-b),tol)
    def le(self,key,a,b=0.,tol=1e-4): self.put(key,np.maximum(np.asarray(a)-b,0.),tol)
    def bounds(self,key,a,lo,hi,tol=1e-4):
        self.le(key,lo-np.asarray(a),0,tol); self.le(key,a,hi,tol)
    def integer(self,x): self.eq('max_integer_violation',x,np.rint(x),1e-6)
    def finish(self,costs,metrics):
        bad={k:v for k,v in self.residuals.items() if v>self.tolerances[k]}
        return dict(passed=not bad,residuals=self.residuals,tolerances=self.tolerances,
                    violations=bad,recomputed_costs=costs,metrics=metrics)


def array(value,shape,label):
    a=np.asarray(value,dtype=float)
    if a.shape!=tuple(shape) or not np.isfinite(a).all():
        raise ValueError(f'{label}: expected finite shape {shape}, got {a.shape}')
    return a


def check_uc(v,d,s):
    T=d['T']; G=len(d['uc']); dt=d['dt_hours']
    u,st,sp=[array(s[k],(T,G),k) for k in ['on','start','stop']]
    for x in [u,st,sp]: v.integer(x); v.bounds('max_uc_state_violation',x,0,1,1e-6)
    for g,p in enumerate(d['uc']):
        if p['must_run']: v.eq('max_uc_state_violation',u[:,g],1,1e-6)
        for t in range(T):
            previous=u[t-1,g] if t else p['initial_on']
            v.eq('max_uc_transition_violation',u[t,g]-previous,st[t,g]-sp[t,g],1e-6)
            v.le('max_uc_transition_violation',st[t,g]+sp[t,g],1,1e-6)
            up=p['min_up_slots']; down=p['min_down_slots']
            v.le('max_min_up_down_violation',sum(st[max(0,t-up+1):t+1,g]),u[t,g],1e-6)
            v.le('max_min_up_down_violation',sum(sp[max(0,t-down+1):t+1,g]),1-u[t,g],1e-6)
            if t+up>T: v.eq('max_min_up_down_violation',st[t,g],0,1e-6)
            if t+down>T: v.eq('max_min_up_down_violation',sp[t,g],0,1e-6)
            if t<(up if p['initial_on'] else down)-p['initial_status_age_slots']:
                v.eq('max_min_up_down_violation',u[t,g],p['initial_on'],1e-6)
    costs=dict(startup=sum(p['startup_cost']*sum(st[:,g])+p['shutdown_cost']*sum(sp[:,g]) for g,p in enumerate(d['uc'])),
               no_load=dt*sum(p['no_load_cost_per_hour']*sum(u[:,g]) for g,p in enumerate(d['uc'])))
    return (u,st,sp),costs


def check_grid(v,d,s,uc,sites,renewables=None,security=False):
    T=d['T']; net=d['network']; buses=net['buses']; gens=net['gens']; br=net['branches']
    index={int(b['bus_i']):i for i,b in enumerate(buses)}; N=len(buses); L=len(br)
    pg=array(s['pg_mw'],(T,len(gens)),'pg_mw')
    theta=array(s['theta_rad'],(T,N),'theta_rad'); flow=array(s['flow_mw'],(T,L),'flow_mw')
    imports=array(s['imports_mw'],(T,len(sites)),'imports_mw')
    u,start,stop=uc
    for g,gen in enumerate(gens):
        v.bounds('max_generator_bound_MW',pg[:,g],d['uc'][g]['pmin_mw']*u[:,g],gen['Pmax']*u[:,g])
        ramp=d['uc'][g]['ramp_mw_per_hour']*d['dt_hours']
        v.le('max_ramp_violation_MW',pg[1:,g]-pg[:-1,g],ramp*u[:-1,g]+gen['Pmax']*start[1:,g])
        v.le('max_ramp_violation_MW',pg[:-1,g]-pg[1:,g],ramp*u[1:,g]+gen['Pmax']*stop[1:,g])
    injection=-np.array(d['background_multiplier'])[:,None]*np.array([b['Pd'] for b in buses])[None,:]
    for g,gen in enumerate(gens): injection[:,index[int(gen['bus'])]]+=pg[:,g]
    for a,site in enumerate(sites):
        v.bounds('max_pcc_bound_MW',imports[:,a],0,site['pcc_max_mw'])
        injection[:,index[site['bus']]]-=imports[:,a]
    if renewables is not None:
        r=array(s['renewable_mw'],(T,len(d['renewables'])),'renewable_mw')
        v.bounds('max_renewable_bound_MW',r,0,np.array(renewables))
        for k,rn in enumerate(d['renewables']): injection[:,index[rn['bus']]]+=r[:,k]
    A=np.zeros((L,N)); beta=np.zeros(L); phi=np.zeros(L)
    for l,b in enumerate(br):
        A[l,index[int(b['fbus'])]]=1; A[l,index[int(b['tbus'])]]=-1
        beta[l]=net['baseMVA']/(b['x']*(b['ratio'] or 1.)); phi[l]=math.radians(b['angle'])
    angles=theta@A.T
    v.eq('max_reference_angle_rad',theta[:,index[31]],0,1e-7)
    v.eq('max_flow_equation_MW',flow,(angles-phi)*beta)
    v.eq('max_power_balance_MW',injection,flow@A)
    v.bounds('max_thermal_violation_MW',flow,-np.array([b['rateA'] for b in br]),np.array([b['rateA'] for b in br]))
    v.bounds('max_angle_violation_rad',angles,np.radians([b['angmin'] for b in br]),np.radians([b['angmax'] for b in br]),1e-7)
    if security:
        if s.get('checked_contingencies')!=d['contingencies']:
            raise ValueError('Missing or incorrect complete contingency list')
        free=[i for i in range(N) if i!=index[31]]
        for c in d['contingencies']:
            keep=[l for l in range(L) if l!=c]
            ac=A[keep]; bc=beta[keep]; pc=phi[keep]
            B=ac.T@(bc[:,None]*ac)
            th=np.zeros((T,N))
            rhs=injection+ac.T@(bc*pc)
            th[:,free]=np.linalg.solve(B[np.ix_(free,free)],rhs[:,free].T).T
            ang=th@ac.T; fc=(ang-pc)*bc
            v.eq('max_contingency_balance_MW',injection,fc@ac)
            v.bounds('max_contingency_thermal_MW',fc,-np.array([br[l]['rateA'] for l in keep]),np.array([br[l]['rateA'] for l in keep]))
            v.bounds('max_contingency_angle_rad',ang,np.radians([br[l]['angmin'] for l in keep]),np.radians([br[l]['angmax'] for l in keep]),1e-7)
    return float(d['dt_hours']*np.sum(pg*np.array([g['c1'] for g in gens]))),pg


def training(v,d,s):
    T=d['T']; dt=d['dt_hours']; uc,costs=check_uc(v,d,s['uc'])
    costs['energy'],_=check_grid(v,d,s,uc,[d['site']])
    usage=np.zeros(T); power=np.full(T,d['site']['idle_it_mw']); count=np.zeros(len(d['jobs']))
    wait=0.
    for choice in s['jobs']:
        nums=[choice[k] for k in ['job','mode','start','duration']]; v.integer(np.array(nums))
        j,k,start,length=map(int,nums)
        if j<0 or j>=len(d['jobs']) or k<0 or k>=len(d['modes']): raise ValueError('Unknown job or mode')
        job=d['jobs'][j]; mode=d['modes'][k]; count[j]+=1
        expected=math.ceil(job['work_block_hours']/(job['blocks']*mode['speed']*dt)-1e-10)
        v.eq('max_job_duration_slots',length,expected,1e-6)
        v.le('max_job_window_slots',job['release'],start,1e-6)
        v.le('max_job_window_slots',start+length,job['deadline'],1e-6)
        if start<0 or length<=0 or start+length>T: raise ValueError('Job outside horizon')
        usage[start:start+length]+=job['blocks']
        power[start:start+length]+=job['blocks']*mode['mw_per_block']
        wait+=job['wait_cost_per_hour']*(start+length-job['release'])*dt
    v.eq('max_job_count_violation',count,1,1e-6)
    v.le('max_compute_block_violation',usage,d['site']['blocks'],1e-6)
    v.eq('max_aidc_power_equation_MW',np.array(s['imports_mw'])[:,0],power*d['site']['pue'])
    costs['job_flow_time']=wait
    return costs,dict(jobs_completed=int(sum(count==1)),peak_blocks=float(max(usage)),
                       aidc_energy_mwh=float(sum(power)*d['site']['pue']*dt))


def inference(v,d,s):
    T=d['T']; D=len(d['sites']); M=len(d['services']); R=d['n_regions']; dt=d['dt_hours']
    uc,costs=check_uc(v,d,s['uc']); costs['energy'],_=check_grid(v,d,s,uc,d['sites'],security=True)
    n,boot,stop=[array(s[k],(T,D,M),k) for k in ['replicas','replica_boot','replica_stop']]
    route=array(s['routes_rps'],(T,R,M,D),'routes_rps'); v.le('max_negative_route_rps',-route)
    for x in [n,boot,stop]: v.integer(x); v.bounds('max_replica_bound_violation',x,0,48,1e-6)
    v.eq('max_request_balance_rps',route.sum(axis=3),np.array(d['demand_rps']))
    served=route.sum(axis=1).transpose(0,2,1)
    capacity=np.array([x['capacity_rps'] for x in d['services']])
    v.le('max_service_capacity_rps',served,n*capacity)
    for t in range(T):
        previous=n[t-1] if t else np.array(d['initial_replicas'])
        arriving=boot[t-1] if t else 0.
        v.eq('max_replica_transition_violation',n[t],previous+arriving-stop[t],1e-6)
        v.le('max_replica_hold_violation',boot[max(0,t-d['minimum_active_slots']):t].sum(axis=0),n[t],1e-6)
        if t+d['minimum_active_slots']>=T: v.eq('max_replica_hold_violation',boot[t],0,1e-6)
    costs['replica_starts']=sum((site['startup_cost_per_block']+site['deploy_cost_per_replica'])*boot[:,a,:].sum() for a,site in enumerate(d['sites']))
    mb=np.array([s['megabits_per_request'] for s in d['services']]); mem=np.array([s['memory_gb'] for s in d['services']])
    traffic=(route*mb[None,None,:,None]).sum(axis=2)/1000
    for a,site in enumerate(d['sites']):
        v.le('max_compute_block_violation',(n[:,a]+boot[:,a]).sum(axis=1),site['blocks'],1e-6)
        v.le('max_memory_gb',(n[:,a]+boot[:,a])@mem,site['memory_gb'],1e-5)
        v.le('max_wan_gbps',traffic[:,:,a].sum(axis=1),site['bandwidth_gbps'],1e-6)
        power=site['idle_it_mw']+n[:,a]@np.array([x['active_idle_mw'] for x in d['services']])+site['boot_mw_per_block']*boot[:,a].sum(axis=1)+(served[:,a]/capacity)@np.array([x['dynamic_mw_at_capacity'] for x in d['services']])
        v.eq('max_aidc_power_equation_MW',np.array(s['imports_mw'])[:,a],power*site['pue'])
    for r in range(R):
        for a in range(D):
            v.le('max_wan_gbps',traffic[:,r,a],d['link_gbps'][r][a],1e-6)
            for k,svc in enumerate(d['services']):
                if d['latency_ms'][r][a]+svc['processing_ms']>svc['slo_ms']:
                    v.eq('max_forbidden_latency_route_rps',route[:,r,k,a],0,1e-5)
    costs['communication']=float(dt*3600/1e6*np.sum(route.sum(axis=2)*np.array(d['route_cost_per_million_requests'])[None,:,:]))
    return costs,dict(n_contingency=len(d['contingencies']),requests_served=float(route.sum()*dt*3600),
                       aidc_energy_mwh=float(np.sum(s['imports_mw'])*dt))


def stochastic(v,d,s):
    T=d['T']; dt=d['dt_hours']; D=len(d['sites']); G=len(d['uc']); fs=s['first_stage']
    uc,costs=check_uc(v,d,fs['uc']); u=uc[0]
    blocks=array(fs['gpu_blocks'],(T,D),'gpu_blocks'); starts=array(fs['gpu_starts'],(T,D),'gpu_starts')
    for x in [blocks,starts]: v.integer(x); v.bounds('max_compute_block_violation',x,0,48,1e-6)
    previous=np.vstack([np.array([a['initial_blocks'] for a in d['sites']]),blocks[:-1]])
    v.le('max_compute_start_violation',blocks-previous,starts,1e-6)
    p0=array(fs['pg0_mw'],(T,G),'pg0'); ru=array(fs['reserve_up_mw'],(T,G),'reserve_up'); rd=array(fs['reserve_down_mw'],(T,G),'reserve_down')
    v.le('max_reserve_violation_MW',-ru); v.le('max_reserve_violation_MW',-rd)
    for g,gen in enumerate(d['network']['gens']):
        v.le('max_reserve_violation_MW',p0[:,g]+ru[:,g],gen['Pmax']*u[:,g])
        v.le('max_reserve_violation_MW',d['uc'][g]['pmin_mw']*u[:,g],p0[:,g]-rd[:,g])
        for r in [ru,rd]: v.le('max_reserve_violation_MW',r[:,g],d['uc'][g]['ramp_mw_per_hour']*d['reserve_response_hours']*u[:,g])
    v.eq('max_nonanticipativity_MW',p0,np.array(s['nominal']['pg_mw']))
    if len(s['scenarios'])!=len(d['scenarios']): raise ValueError('Missing stochastic scenario')
    scenario_costs=[]
    for i,(inp,sol) in enumerate(zip([d['nominal']]+d['scenarios'],[s['nominal']]+s['scenarios'])):
        energy_cost,pg=check_grid(v,d,sol,uc,d['sites'],renewables=inp['renewable_mw'])
        if i:
            v.le('max_recourse_violation_MW',pg-p0,ru); v.le('max_recourse_violation_MW',p0-pg,rd)
        f=array(sol['facility_mw'],(T,D),'facility'); imp=array(sol['imports_mw'],(T,D),'imports')
        ch=array(sol['charge_mw'],(T,D),'charge'); dis=array(sol['discharge_mw'],(T,D),'discharge')
        mode=array(sol['charging'],(T,D),'charging'); v.integer(mode); v.bounds('max_battery_mode_violation',mode,0,1,1e-6)
        E=array(sol['energy_mwh'],(T+1,D),'energy')
        work=array(sol['training_blocks'],(T,len(d['cohorts'])),'training_blocks')
        v.le('max_negative_training_blocks',-work,0,1e-6)
        served=np.zeros((T,D))
        for k,c in enumerate(d['cohorts']):
            r,e=c['release'],c['deadline']
            v.eq('max_training_work_error_block_hours',work[r:e,k].sum()*dt,c['work_block_hours'],1e-5)
            v.eq('max_training_window_violation',work[:r,k],0,1e-6); v.eq('max_training_window_violation',work[e:,k],0,1e-6)
            served[:,c['site']]+=work[:,k]
        inf=np.array(inp['inference_blocks']); v.le('max_compute_block_violation',inf+served,blocks,1e-6)
        degradation=0.
        for a,site in enumerate(d['sites']):
            expected=site['pue']*(site['idle_it_mw']+site['idle_mw_per_block']*blocks[:,a]+site['dynamic_mw_per_busy_block']*(inf[:,a]+served[:,a]))
            v.eq('max_aidc_power_equation_MW',f[:,a],expected)
            v.bounds('max_facility_bound_MW',f[:,a],0,site['pcc_max_mw'])
            v.eq('max_aidc_power_equation_MW',imp[:,a],f[:,a]+ch[:,a]-dis[:,a])
            v.bounds('max_battery_power_violation_MW',ch[:,a],0,site['battery_power_mw']*mode[:,a])
            v.bounds('max_battery_power_violation_MW',dis[:,a],0,site['battery_power_mw']*(1-mode[:,a]))
            v.eq('max_soc_equation_MWh',E[1:,a],E[:-1,a]+dt*(site['eta_charge']*ch[:,a]-dis[:,a]/site['eta_discharge']),1e-5)
            v.bounds('max_soc_bound_MWh',E[:,a],0,site['battery_energy_mwh'],1e-5)
            v.eq('max_terminal_energy_MWh',[E[0,a],E[-1,a]],site['initial_energy_mwh'],1e-5)
            critical=site['pue']*(site['idle_it_mw']+(site['idle_mw_per_block']+site['dynamic_mw_per_busy_block'])*inf[:,a]*site['critical_inference_fraction'])
            v.le('max_ups_power_violation_MW',critical,site['battery_power_mw'])
            minimum=critical*site['ups_hours']/site['eta_discharge']
            v.le('max_ups_reserve_MWh',minimum,E[:-1,a],1e-5);v.le('max_ups_reserve_MWh',minimum,E[1:,a],1e-5)
            degradation+=dt*site['battery_throughput_cost_per_mwh']*(ch[:,a].sum()+dis[:,a].sum())
        curtail=dt*d['curtailment_cost_per_mwh']*np.sum(np.array(inp['renewable_mw'])-np.array(sol['renewable_mw']))
        op=float(energy_cost+degradation+curtail)
        v.eq('max_scenario_cost_error_usd',sol['operating_cost'],op,1e-3+abs(op)*1e-9)
        if i: scenario_costs.append(op)
        else:
            demand=np.array(d['background_multiplier'])*sum(b['Pd'] for b in d['network']['buses'])+imp.sum(axis=1)
            for r in [ru,rd]:v.le('max_reserve_violation_MW',d['reserve_fraction']*demand,r.sum(axis=1))
    probs=np.array([x['probability'] for x in d['scenarios']]);v.eq('max_probability_error',sum(probs),1,1e-9)
    eta=float(s['cvar_eta']);excess=array(s['cvar_excess'],(len(probs),),'cvar_excess')
    if not math.isfinite(eta):raise ValueError('Non-finite CVaR threshold')
    v.le('max_cvar_epigraph_violation_usd',-excess,0,1e-3)
    v.le('max_cvar_epigraph_violation_usd',np.array(scenario_costs)-eta,excess,1e-3)
    cvar=eta+float(probs@excess)/(1-d['cvar_alpha'])
    exact_cvar=min(a+float(probs@np.maximum(np.array(scenario_costs)-a,0))/(1-d['cvar_alpha']) for a in scenario_costs)
    costs.update(reserve=float(dt*(d['reserve_up_cost_per_mw_hour']*ru.sum()+d['reserve_down_cost_per_mw_hour']*rd.sum())),
                 compute_starts=sum(site['block_start_cost']*starts[:,a].sum() for a,site in enumerate(d['sites'])),
                 expected_operation=float(probs@scenario_costs),risk_premium=d['risk_weight']*cvar)
    return costs,dict(n_scenario=len(probs),scenario_operating_costs=scenario_costs,
                      empirical_cvar=float(exact_cvar),cvar_epigraph=float(cvar),
                      expected_aidc_energy_mwh=float(sum(p*np.sum(x['imports_mw'])*dt for p,x in zip(probs,s['scenarios']))))


def validate(d,schedule,objective,cost_breakdown):
    v=Checks()
    try:
        costs,metrics=globals()[d['kind']](v,d,schedule)
        for k,value in costs.items():
            supplied=float(cost_breakdown[k])
            if not math.isfinite(supplied): raise ValueError('Non-finite cost')
            v.eq('max_cost_decomposition_error_usd',supplied,value,1e-3+abs(value)*1e-9)
        obj=float(objective)
        if not math.isfinite(obj):raise ValueError('Non-finite objective')
        v.eq('max_objective_error_usd',obj,sum(costs.values()),1e-3+abs(obj)*1e-9)
        return v.finish({k:float(x) for k,x in costs.items()},metrics)
    except (KeyError,IndexError,ValueError,TypeError,np.linalg.LinAlgError) as exc:
        return dict(passed=False,residuals=v.residuals,tolerances=v.tolerances,
                    violations={'invalid_saved_schedule':str(exc)},recomputed_costs={},metrics={})
