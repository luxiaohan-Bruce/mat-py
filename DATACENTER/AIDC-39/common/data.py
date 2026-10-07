"""Deterministic input generation; never reads older local AIDC/UC case data."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

PACK = Path(__file__).resolve().parents[1]
COMMIT = 'dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3'
SOURCE_SHA256 = '83a1a6ec49c9a0533b51e928f6bd95b93aea745a620e5123bedcd88f716c286b'
CASES = [('case001_training_uc', 'training', 101),
         ('case002_inference_n1', 'inference', 202),
         ('case003_stochastic_ups', 'stochastic', 303)]
TRAINING_JOB_COUNT = 240
TRAINING_WAIT_COST_SCALE = 4.5


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def public_network():
    src = PACK / 'source/pglib_opf_case39_epri.m'
    raw = src.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256, 'Public source checksum mismatch'
    def matrix(name):
        body = re.search(r'mpc\.' + name + r'\s*=\s*\[(.*?)\];', raw.decode(), re.S).group(1)
        return [[float(v) for v in line.split('%')[0].strip().rstrip(';').split()]
                for line in body.splitlines() if line.split('%')[0].strip()]
    buskeys = 'bus_i type Pd Qd Gs Bs area Vm Va baseKV zone Vmax Vmin'.split()
    genkeys = 'bus Pg Qg Qmax Qmin Vg mBase status Pmax Pmin'.split()
    brkeys = 'fbus tbus r x b rateA rateB rateC ratio angle status angmin angmax'.split()
    buses = [dict(zip(buskeys, r)) for r in matrix('bus')]
    gens = [dict(zip(genkeys, r[:10])) for r in matrix('gen')]
    for g, row in zip(gens, matrix('gencost')):
        g.update(cost_model=2, c2=row[-3], c1=row[-2], c0=row[-1])
        assert g['c2'] == 0, 'This benchmark uses the source linear energy cost'
    branches = [dict(id=i, **dict(zip(brkeys, r))) for i, r in enumerate(matrix('branch'))]
    return dict(name='pglib_opf_case39_epri', baseMVA=100.,
                source=f'https://raw.githubusercontent.com/power-grid-lib/pglib-opf/{COMMIT}/pglib_opf_case39_epri.m',
                source_commit=COMMIT, source_sha256=SOURCE_SHA256,
                buses=buses, gens=gens, branches=branches)


def nonislanding_contingencies(net):
    ids = {int(b['bus_i']) for b in net['buses']}
    out = []
    for removed in net['branches']:
        adj = {i: [] for i in ids}
        for b in net['branches']:
            if b['id'] == removed['id'] or not b['status']:
                continue
            a, z = int(b['fbus']), int(b['tbus'])
            adj[a].append(z); adj[z].append(a)
        seen = {min(ids)}; todo = list(seen)
        while todo:
            for z in adj[todo.pop()]:
                if z not in seen:
                    seen.add(z); todo.append(z)
        if seen == ids:
            out.append(removed['id'])
    return out


def uc_parameters(net):
    return [dict(bus=int(g['bus']), must_run=int(g['bus']) in (30, 39),
                 pmin_mw=0. if int(g['bus']) == 39 else .20*g['Pmax'],
                 ramp_mw_per_hour=.6*g['Pmax'], min_up_slots=8, min_down_slots=8,
                 initial_on=1, initial_status_age_slots=16,
                 startup_cost=0.25*g['Pmax']*g['c1'], shutdown_cost=0.,
                 no_load_cost_per_hour=0. if int(g['bus']) == 39 else .04*g['Pmax']*g['c1'])
            for g in net['gens']]


def training_data(rng, T, *, job_count=None, window_margin_slots=None, wait_cost_scale=None):
    dt = .25
    site = dict(bus=16, pcc_max_mw=300., blocks=64, idle_it_mw=16., pue=1.25)
    modes = [dict(name='eco', speed=.70, mw_per_block=2.),
             dict(name='balanced', speed=.85, mw_per_block=2.7),
             dict(name='fast', speed=1., mw_per_block=3.5)]
    # Pack jobs into an explicit feasible fastest-mode witness first, then widen
    # their start windows. This creates feasible workload data, not an optimum.
    count = job_count if job_count is not None else (TRAINING_JOB_COUNT if T == 96 else max(2, T // 2))
    margin = window_margin_slots if window_margin_slots is not None else max(2, T//5)
    if wait_cost_scale is None:
        wait_cost_scale = TRAINING_WAIT_COST_SCALE if T == 96 else 1.
    used = np.zeros(T)
    jobs = []
    for j in range(count):
        placed = False
        for _ in range(2000):
            k = int(rng.choice([2, 4, 8]))
            duration = int(rng.integers(2, min(13, T+1)))
            start = int(rng.integers(0, T-duration+1))
            if np.max(used[start:start+duration]) + k <= 60:
                used[start:start+duration] += k
                release = max(0, start-int(rng.integers(0, margin)))
                deadline = min(T, start+duration+int(rng.integers(0, margin)))
                jobs.append(dict(id=j, blocks=k, work_block_hours=k*duration*dt,
                                 release=release, deadline=deadline,
                                 wait_cost_per_hour=wait_cost_scale*float(rng.integers(3, 13)),
                                 witness_start=start, witness_mode=2))
                placed = True
                break
        if not placed:
            raise ValueError('Unable to pack training workload; no silent job removal')
    return dict(site=site, modes=modes, jobs=jobs, n_jobs=count)


def inference_data(rng, T):
    sites = [dict(bus=b, blocks=48, memory_gb=3200., pcc_max_mw=200.,
                  pue=pue, idle_it_mw=8., boot_mw_per_block=2.,
                  startup_cost_per_block=18., deploy_cost_per_replica=12.,
                  bandwidth_gbps=150.)
             for b, pue in zip([4,16,27], [1.20,1.25,1.30])]
    services = [dict(id=m, capacity_rps=cap, processing_ms=delay,
                     slo_ms=slo, memory_gb=mem, active_idle_mw=1.1+.08*m,
                     dynamic_mw_at_capacity=1.75, megabits_per_request=mb)
                for m,(cap,delay,slo,mem,mb) in enumerate(zip(
                    [900,800,700,600,500,400], [8,12,18,25,32,40],
                    [40,50,55,70,80,90], [40,48,60,72,90,110], [1,1.5,2,3,4,6]))]
    latency = [[8. if d == r//2 else float(22+9*abs(d-r//2)+2*(r%2))
                for d in range(3)] for r in range(6)]
    demand = np.empty((T,6,6))
    for t in range(T):
        for r in range(6):
            shape = .85 + .65*math.sin(math.pi*(t/T-.23-r*.018))**2
            for m,s in enumerate(services):
                demand[t,r,m] = round(s['capacity_rps']*(1.05+.045*r)*shape*
                                      (1+.10*math.sin(2*math.pi*t/T+m))*(1+rng.uniform(-.025,.025)), 5)
    fixed = np.zeros((3,6), dtype=int)
    for d in range(3):
        for m,s in enumerate(services):
            fixed[d,m] = math.ceil(max(demand[:,2*d,m]+demand[:,2*d+1,m])/s['capacity_rps'])
        assert sum(fixed[d]) <= 48
    return dict(sites=sites, services=services, n_regions=6, demand_rps=demand.tolist(),
                latency_ms=latency, link_gbps=[[50.]*3 for _ in range(6)],
                route_cost_per_million_requests=[[.6+.08*latency[r][d] for d in range(3)] for r in range(6)],
                initial_replicas=fixed.tolist(), baseline_replicas=fixed.tolist(),
                boot_slots=1, minimum_active_slots=4)


def stochastic_data(rng, T, S):
    sites = [dict(bus=b, blocks=48, pcc_max_mw=200., pue=1.25,
                  idle_it_mw=8., idle_mw_per_block=1., dynamic_mw_per_busy_block=2.,
                  block_start_cost=25., initial_blocks=32,
                  battery_power_mw=40., battery_energy_mwh=100., initial_energy_mwh=80.,
                  eta_charge=.95, eta_discharge=.95, ups_hours=.25,
                  critical_inference_fraction=.25,
                  battery_throughput_cost_per_mwh=2.) for b in [4,16,27]]
    h = np.arange(T)*24/T
    wind = 350*(.55+.16*np.cos(2*np.pi*(h-3)/24))
    solar = 250*np.maximum(0., np.sin(np.pi*(h-6)/12))
    inf = np.array([[13+5*math.sin(math.pi*(t/T-.2))**2+d for d in range(3)] for t in range(T)])
    cohorts = []
    for d in range(3):
        for r in range(0,T,16):
            end = min(T,r+16)
            cohorts.append(dict(id=len(cohorts),site=d,release=r,deadline=end,
                                work_block_hours=round((10+d)*(end-r)*.25*(1+rng.uniform(-.08,.08)),6)))
    def ar():
        z = np.empty(T); z[0] = rng.normal()
        for t in range(1,T):
            z[t] = .92*z[t-1] + math.sqrt(1-.92**2)*rng.normal()
        return np.clip(z,-2.,2.)
    scenarios = []
    for s in range(S):
        shared = ar(); w = ar(); sun = ar()
        demand = inf*(1+.065*shared[:,None]+.025*np.stack([ar() for _ in sites],axis=1))
        scenarios.append(dict(id=s,probability=1/S,
            renewable_mw=np.stack([np.clip(wind*(1+.16*w),0,350),
                                   np.clip(solar*(1+.18*sun),0,250)],axis=1).tolist(),
            inference_blocks=demand.tolist()))
    # Nominal forecasts are exactly the ensemble means used by the EV baseline.
    nominal = dict(id='nominal', renewable_mw=np.mean([s['renewable_mw'] for s in scenarios],axis=0).tolist(),
                   inference_blocks=np.mean([s['inference_blocks'] for s in scenarios],axis=0).tolist())
    return dict(sites=sites, cohorts=cohorts, scenarios=scenarios, nominal=nominal,
                renewables=[dict(bus=21,kind='wind',pmax_mw=350.),dict(bus=26,kind='solar',pmax_mw=250.)],
                cvar_alpha=.9, risk_weight=.2, reserve_fraction=.05,
                reserve_up_cost_per_mw_hour=1.,reserve_down_cost_per_mw_hour=.3,
                reserve_response_hours=.25, curtailment_cost_per_mwh=1.,
                information_structure='two_stage_full_trajectory_revealed_after_day_ahead')


def make_data(kind, T=96, S=20):
    seed = dict(training=101,inference=202,stochastic=303)[kind]
    net = public_network()
    rng = np.random.default_rng(seed)
    peak = .68 if kind == 'inference' else .85
    data = dict(schema_version=1,kind=kind,seed=seed,T=T,dt_hours=.25,
                background_multiplier=[peak*(.8+.2*math.sin(math.pi*(t/T-.25))**2) for t in range(T)],
                uc=uc_parameters(net), network=net,
                provenance=dict(grid='PGLib official pinned source',
                    synthetic=['UC operating parameters','background daily curve','AIDC capacities and performance',
                               'workloads','WAN and service times','battery and renewable scenarios'],
                    previous_aidc_data_used=False))
    if kind == 'training': data.update(training_data(rng,T))
    if kind == 'inference':
        data.update(inference_data(rng,T))
        data['contingencies'] = nonislanding_contingencies(net)
        assert len(data['contingencies']) == 35
    if kind == 'stochastic':
        data.update(stochastic_data(rng,T,S))
        net['renewable'] = copy.deepcopy(data['renewables'])
        net['storage'] = [dict(bus=s['bus'],power_mw=40.,energy_mwh=100.) for s in data['sites']]
    return data


def load_case(case):
    case=Path(case)
    data=json.loads((case/'data/aidc.json').read_text())
    data['network']=json.loads((case/'data/network.json').read_text())
    return data,json.loads((case/'data/config.json').read_text())


def data_hash(d):
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def mean_data(d):
    out=copy.deepcopy(d)
    s=copy.deepcopy(d['nominal']);s['id']=0;s['probability']=1.
    out['scenarios']=[s]
    return out


def generate():
    from framework.runner import SOLVE_SHIM
    for name,kind,seed in CASES:
        case=PACK/name
        data=make_data(kind)
        config=dict(schema_version=1,case=name,problem='aidc39',base_problem='datacenter_flex',
                    source_network='pglib_opf_case39_epri',source=data['network']['source'],
                    T=96,dt_hours=.25,n_scenarios=20 if kind=='stochastic' else 1,
                    contingencies=data.get('contingencies',[]),
                    seed=1,data_seed=seed,threads=4,time_limit=600.,mip_gap=.001,solve_tier='full',
                    variant=dict(power_flow='dc',security='n-1' if kind=='inference' else 'none',
                        uncertainty='two_stage_stochastic' if kind=='stochastic' else 'deterministic',
                        horizon='multi_period',recourse='dispatch' if kind=='stochastic' else 'none',
                        formulation='aidc_'+kind,commitment='binary',
                        contingency_scope='all_credible_non_islanding' if kind=='inference' else 'not_applicable'),
                    validation_scope='independent_dc_and_business_residuals',physics_validated=False,
                    known_limitations=['DC approximation; no voltage/reactive/transient certification',
                        'Synthetic workloads and UC operating parameters',
                        'No initial dispatch ramp boundary; initial on-status history specified',
                        'Single nonislanding branch contingencies only' if kind=='inference' else 'No N-1 constraints',
                        'Full-path second-stage information' if kind=='stochastic' else 'Deterministic forecasts'])
        net=data.pop('network')
        if kind=='training':
            config['difficulty_target_seconds']=100.
            config['training_profile']=dict(n_jobs=TRAINING_JOB_COUNT,wait_cost_scale=TRAINING_WAIT_COST_SCALE)
        write_json(case/'data/network.json',net)
        write_json(case/'data/aidc.json',data)
        write_json(case/'data/config.json',config)
        (case/'python').mkdir(parents=True,exist_ok=True)
        (case/'solve.py').write_text(SOLVE_SHIM)
        (case/'python/solve_aidc39.py').write_text(
            'from pathlib import Path\nimport sys\nCASE=Path(__file__).resolve().parents[1]\n'
            'sys.path.insert(0,str(CASE.parent))\nfrom common.runner import main\n'
            'if __name__ == "__main__":\n    raise SystemExit(main(CASE))\n')
    write_json(PACK/'source/provenance.json',dict(commit=COMMIT,sha256=SOURCE_SHA256,
        source_url=public_network()['source'],source_version='PGLib-OPF v23.07',
        grid_license='CC BY 4.0, attribution retained in source',
        generator='common/data.py',numpy_rng='PCG64/default_rng',data_seeds=[101,202,303]))


if __name__ == '__main__':
    generate()
