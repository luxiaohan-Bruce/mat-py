"""Small, physical 39-bus tests; all long benchmark runs are explicit."""
from __future__ import annotations
import copy
import itertools
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import gurobipy as gp
import numpy as np

PACK=Path(__file__).resolve().parent
sys.path.insert(0,str(PACK))
sys.path.insert(0,str(PACK.parents[1]))
from common.data import make_data,data_hash,write_json,nonislanding_contingencies
from common.runner import solve_data,mean_data
from common.validation import validate
from framework.evaluate import evaluate


CFG=dict(time_limit=30.,threads=1,mip_gap=1e-8,seed=1)


class AIDCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={k:make_data(k,T=8,S=2) for k in ['training','inference','stochastic']}
        cls.results={k:solve_data(d,CFG) for k,d in cls.data.items()}

    def check_result(self,kind,alter):
        r=copy.deepcopy(self.results[kind]);alter(r)
        return validate(self.data[kind],r['schedule'],r['aidc39']['obj'],r['cost_breakdown'])

    def test_small_cases_and_independent_validation(self):
        for k,r in self.results.items():
            with self.subTest(kind=k):self.assertTrue(r['validation']['passed'],r['validation'])

    def test_reproducible_public_data_and_full_dimensions(self):
        for kind in self.data:
            a=make_data(kind);b=make_data(kind)
            self.assertEqual(data_hash(a),data_hash(b))
            self.assertEqual((len(a['network']['buses']),len(a['network']['branches']),len(a['network']['gens'])),(39,46,10))
        self.assertEqual(len(make_data('training')['jobs']),240)
        self.assertEqual(len(make_data('stochastic')['scenarios']),20)
        self.assertEqual(len(nonislanding_contingencies(self.data['inference']['network'])),35)

    def test_energy_boundaries_are_fixed_not_merely_lower_bounds(self):
        r=self.results['stochastic']
        for stage in [r['schedule']['nominal']]+r['schedule']['scenarios']:
            self.assertTrue(np.allclose(stage['energy_mwh'][0],[80.]*3))
            self.assertTrue(np.allclose(stage['energy_mwh'][-1],[80.]*3))

    def test_missing_training_job_rejected(self):
        out=self.check_result('training',lambda r:r['schedule']['jobs'].pop())
        self.assertFalse(out['passed'])

    def test_tampered_grid_dispatch_rejected(self):
        def change(r):r['schedule']['pg_mw'][0][0]+=1.
        out=self.check_result('inference',change)
        self.assertFalse(out['passed']);self.assertGreater(out['residuals']['max_power_balance_MW'],.9)

    def test_missing_contingency_rejected(self):
        out=self.check_result('inference',lambda r:r['schedule']['checked_contingencies'].pop())
        self.assertFalse(out['passed'])

    def test_tampered_replica_start_or_latency_route_rejected(self):
        def change(r):r['schedule']['replicas'][0][0][0]+=1.
        self.assertFalse(self.check_result('inference',change)['passed'])
        def forbidden(r):r['schedule']['routes_rps'][0][0][0][2]=10.
        self.assertFalse(self.check_result('inference',forbidden)['passed'])

    def test_infeasible_training_deadline_is_not_softened(self):
        d=copy.deepcopy(self.data['training']);d['jobs'][0]['deadline']=d['jobs'][0]['release']
        r=solve_data(d,CFG)
        self.assertEqual(r['aidc39']['status'],'INFEASIBLE');self.assertFalse(r['aidc39']['validation_passed'])

    def test_impossible_inference_slo_is_not_dropped(self):
        d=copy.deepcopy(self.data['inference']);d['services'][0]['slo_ms']=0.
        r=solve_data(d,CFG)
        self.assertEqual(r['aidc39']['status'],'INFEASIBLE')

    def test_impossible_ups_requirement_is_not_relaxed(self):
        d=copy.deepcopy(self.data['stochastic']);d['sites'][0]['ups_hours']=10.
        r=solve_data(d,CFG)
        self.assertEqual(r['aidc39']['status'],'INFEASIBLE')

    def test_ups_power_rating_is_required_as_well_as_energy(self):
        d=copy.deepcopy(self.data['stochastic']);d['sites'][0]['battery_power_mw']=1.
        r=solve_data(d,CFG)
        self.assertEqual(r['aidc39']['status'],'INFEASIBLE')
        old=self.results['stochastic']
        check=validate(d,old['schedule'],old['aidc39']['obj'],old['cost_breakdown'])
        self.assertFalse(check['passed'])
        self.assertGreater(check['residuals']['max_ups_power_violation_MW'],1.)

    def test_cvar_and_scenario_completeness(self):
        r=self.results['stochastic'];values=r['validation']['metrics']['scenario_operating_costs']
        self.assertAlmostEqual(r['validation']['metrics']['empirical_cvar'],max(values),places=5)
        self.assertFalse(self.check_result('stochastic',lambda r:r['schedule']['scenarios'].pop())['passed'])
        def change(r):r['schedule']['first_stage']['pg0_mw'][0][0]+=1
        self.assertFalse(self.check_result('stochastic',change)['passed'])

    def test_identical_scenarios_reduce_to_single_scenario(self):
        one=mean_data(self.data['stochastic']);r1=solve_data(one,CFG)
        two=copy.deepcopy(one)
        two['scenarios']=[dict(copy.deepcopy(one['scenarios'][0]),id=i,probability=.5) for i in range(2)]
        r2=solve_data(two,CFG)
        self.assertTrue(r1['validation']['passed']);self.assertTrue(r2['validation']['passed'])
        self.assertAlmostEqual(r1['aidc39']['obj'],r2['aidc39']['obj'],delta=.05)

    def test_mean_policy_can_be_fixed_and_re_evaluated(self):
        d=mean_data(self.data['stochastic']);mean=solve_data(d,CFG)
        r=solve_data(d,CFG,mode='baseline',fixed_first_stage=mean['schedule']['first_stage'])
        self.assertTrue(r['validation']['passed'],r['validation'])
        self.assertAlmostEqual(r['aidc39']['obj'],mean['aidc39']['obj'],delta=.05)

    def test_evaluate_recomputes_instead_of_trusting_cached_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);d=copy.deepcopy(self.data['training']);net=d.pop('network')
            write_json(p/'data/aidc.json',d);write_json(p/'data/network.json',net)
            write_json(p/'data/config.json',dict(problem='aidc39',base_problem='datacenter_flex',solve_tier='full'))
            r=copy.deepcopy(self.results['training']);write_json(p/'results/python_result.json',r)
            self.assertTrue(evaluate(p)['passed'])
            r['schedule']['pg_mw'][0][0]+=1
            write_json(p/'results/python_result.json',r)
            self.assertFalse(evaluate(p)['passed'])
            r=copy.deepcopy(self.results['training']);write_json(p/'results/python_result.json',r)
            d['background_multiplier'][0]*=.9;write_json(p/'data/aidc.json',d)
            self.assertFalse(evaluate(p)['passed'])

    def test_unified_solver_and_evaluator_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack=Path(tmp);case=pack/'case_smoke'
            shutil.copytree(PACK/'common',pack/'common',ignore=shutil.ignore_patterns('__pycache__'))
            (case/'python').mkdir(parents=True)
            shutil.copyfile(PACK/'case001_training_uc/python/solve_aidc39.py',case/'python/solve_aidc39.py')
            d=copy.deepcopy(self.data['training']);net=d.pop('network')
            write_json(case/'data/aidc.json',d);write_json(case/'data/network.json',net)
            write_json(case/'data/config.json',dict(CFG,problem='aidc39',base_problem='datacenter_flex',solve_tier='full'))
            for entry in ['solve.py','evaluate.py']:
                proc=subprocess.run([sys.executable,str(PACK.parents[1]/entry),str(case)],
                                    capture_output=True,text=True,timeout=45)
                self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)

    def test_nan_and_forged_objective_rejected(self):
        def nan(r):r['schedule']['pg_mw'][0][0]=float('nan')
        self.assertFalse(self.check_result('training',nan)['passed'])
        def obj(r):r['aidc39']['obj']-=1000
        self.assertFalse(self.check_result('training',obj)['passed'])

    def test_training_optimum_matches_exhaustive_start_mode_search(self):
        # Reference oracle: enumerate all legal placements, then solve an
        # independently written fixed-commitment DC LP (no training/grid builder).
        T=6;d=make_data('training',T=T);d['site']['blocks']=4
        d['jobs']=[dict(id=0,blocks=4,work_block_hours=2.,release=0,deadline=T,
                       wait_cost_per_hour=5.,witness_start=0,witness_mode=2),
                   dict(id=1,blocks=2,work_block_hours=1.,release=0,deadline=T,
                       wait_cost_per_hour=9.,witness_start=2,witness_mode=2)]
        d['n_jobs']=2
        result=solve_data(d,CFG)
        self.assertTrue(result['validation']['passed'])
        net=d['network'];ids={int(b['bus_i']):i for i,b in enumerate(net['buses'])}
        reference=[]
        with gp.Env(empty=True) as env:
            env.setParam('OutputFlag',0);env.start()
            for modes in itertools.product(d['modes'],repeat=2):
                durations=[math.ceil(j['work_block_hours']/(j['blocks']*mode['speed']*.25)-1e-10)
                           for j,mode in zip(d['jobs'],modes)]
                for starts in itertools.product(*(range(T+1-length) for length in durations)):
                    load=np.full(T,16.*1.25);usage=np.zeros(T)
                    for job,mode,start,length in zip(d['jobs'],modes,starts,durations):
                        load[start:start+length]+=job['blocks']*mode['mw_per_block']*1.25
                        usage[start:start+length]+=job['blocks']
                    if max(usage)>d['site']['blocks']:continue
                    with gp.Model(env=env) as lp:
                        p=lp.addVars(T,10,lb=0);th=lp.addVars(T,39,lb=-gp.GRB.INFINITY)
                        for t in range(T):
                            lp.addConstr(th[t,ids[31]]==0)
                            flows=[]
                            for b in net['branches']:
                                angle=th[t,ids[int(b['fbus'])]]-th[t,ids[int(b['tbus'])]]
                                f=100/(b['x']*(b['ratio'] or 1))*(angle-math.radians(b['angle']))
                                lp.addConstr(f<=b['rateA']);lp.addConstr(f>=-b['rateA'])
                                lp.addConstr(angle<=math.radians(b['angmax']));lp.addConstr(angle>=math.radians(b['angmin']))
                                flows.append(f)
                            for g,gen in enumerate(net['gens']):
                                p[t,g].LB=d['uc'][g]['pmin_mw'];p[t,g].UB=gen['Pmax']
                                if t:
                                    ramp=d['uc'][g]['ramp_mw_per_hour']*.25
                                    lp.addConstr(p[t,g]-p[t-1,g]<=ramp);lp.addConstr(p[t-1,g]-p[t,g]<=ramp)
                            for b in net['buses']:
                                bid=int(b['bus_i'])
                                injection=gp.quicksum(p[t,g] for g,x in enumerate(net['gens']) if int(x['bus'])==bid)-b['Pd']*d['background_multiplier'][t]-(load[t] if bid==16 else 0)
                                outgoing=gp.quicksum(flows[l]*(1 if int(x['fbus'])==bid else -1) for l,x in enumerate(net['branches']) if bid in (int(x['fbus']),int(x['tbus'])))
                                lp.addConstr(injection==outgoing)
                        fixed_cost=.25*T*sum(x['no_load_cost_per_hour'] for x in d['uc'])
                        fixed_cost+=.25*sum(j['wait_cost_per_hour']*(start+length) for j,start,length in zip(d['jobs'],starts,durations))
                        lp.setObjective(.25*gp.quicksum(p[t,g]*x['c1'] for t in range(T) for g,x in enumerate(net['gens']))+fixed_cost)
                        lp.optimize()
                        if lp.SolCount:reference.append(lp.ObjVal)
        self.assertAlmostEqual(result['aidc39']['obj'],min(reference),places=4)


if __name__=='__main__':unittest.main(verbosity=2)
