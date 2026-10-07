"""Solver, reproducible result writing, and expected-value baseline evaluation."""
from __future__ import annotations
import argparse
import json
import math
import platform
import time
from pathlib import Path

import gurobipy as gp
from .data import load_case,write_json,data_hash,mean_data
from .verify import revalidate_saved
from .validation import validate


def build_model(m,d,mode='main',fixed_first_stage=None):
    if d['kind']=='training':
        from .training import build
        return build(m,d,baseline=mode=='baseline')
    if d['kind']=='inference':
        from .inference import build
        return build(m,d,baseline=mode=='baseline')
    from .stochastic import build
    return build(m,d,fixed_first_stage=fixed_first_stage)


def solve_data(d,cfg,*,mode='main',output_dir=None,fixed_first_stage=None):
    output_dir=Path(output_dir) if output_dir else None
    if output_dir: output_dir.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter(); first_incumbent=None; last_progress=-30.
    def finite(x): return float(x) if math.isfinite(x) and abs(x)<gp.GRB.INFINITY/2 else None
    def callback(model,where):
        nonlocal first_incumbent,last_progress
        if where==gp.GRB.Callback.MIPSOL and first_incumbent is None:
            first_incumbent=float(model.cbGet(gp.GRB.Callback.RUNTIME))
        if where==gp.GRB.Callback.MIP and output_dir:
            runtime=float(model.cbGet(gp.GRB.Callback.RUNTIME))
            if runtime-last_progress>=30:
                last_progress=runtime
                write_json(output_dir/(mode+'_progress.json'),dict(runtime=runtime,
                    incumbent=finite(model.cbGet(gp.GRB.Callback.MIP_OBJBST)),
                    bound=finite(model.cbGet(gp.GRB.Callback.MIP_OBJBND)),
                    nodes=finite(model.cbGet(gp.GRB.Callback.MIP_NODCNT))))
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        with gp.Model('aidc39_'+d['kind']+'_'+mode,env=env) as m:
            m.Params.Seed=cfg.get('seed',1);m.Params.Threads=cfg.get('threads',4)
            m.Params.TimeLimit=cfg.get('time_limit',600.);m.Params.MIPGap=cfg.get('mip_gap',.001)
            m.Params.FeasibilityTol=1e-8;m.Params.IntFeasTol=1e-8
            if output_dir:
                m.Params.LogToConsole=0;m.Params.OutputFlag=1
                m.Params.LogFile=str(output_dir/(mode+'_gurobi.log'))
            built=build_model(m,d,mode,fixed_first_stage)
            m.update()
            stats=dict(n_variables=m.NumVars,n_constraints=m.NumConstrs,n_nonzeros=m.NumNZs,
                       n_binary=m.NumBinVars,n_general_integer=m.NumIntVars-m.NumBinVars,
                       n_continuous=m.NumVars-m.NumIntVars)
            build_seconds=time.perf_counter()-started
            if output_dir:write_json(output_dir/(mode+'_model_stats.json'),stats)
            m.optimize(callback)
            names={gp.GRB.OPTIMAL:'OPTIMAL',gp.GRB.TIME_LIMIT:'TIME_LIMIT',gp.GRB.INFEASIBLE:'INFEASIBLE',
                   gp.GRB.INF_OR_UNBD:'INF_OR_UNBD',gp.GRB.INTERRUPTED:'INTERRUPTED',gp.GRB.SUBOPTIMAL:'SUBOPTIMAL',
                   gp.GRB.NUMERIC:'NUMERIC',gp.GRB.UNBOUNDED:'UNBOUNDED'}
            block=dict(status=names.get(m.Status,str(m.Status)),obj=None,objective_bound=finite(m.ObjBound),
                       mip_gap=None,runtime=float(m.Runtime),first_incumbent_seconds=first_incumbent,
                       solution_count=int(m.SolCount),node_count=float(m.NodeCount),
                       validation_passed=False,**stats)
            result=dict(schema_version=1,case=cfg.get('case',d['kind']),mode=mode,
                        input_sha256=data_hash(d),aidc39=block,
                        metadata=dict(gurobi_version=list(gp.gurobi.version()),python=platform.python_version(),
                            machine=platform.machine(),platform=platform.system(),build_seconds=build_seconds,
                            seed=m.Params.Seed,threads=m.Params.Threads,time_limit=m.Params.TimeLimit,
                            mip_gap_target=m.Params.MIPGap,baseline_note=built['baseline_note']))
            if fixed_first_stage is not None:
                result['fixed_first_stage']=fixed_first_stage
            if m.SolCount:
                block['obj']=float(m.ObjVal);block['mip_gap']=float(m.MIPGap)
                schedule=built['extract']()
                costs={key:float(value.getValue() if hasattr(value,'getValue') else value) for key,value in built['costs'].items()}
                tick=time.perf_counter(); certificate=validate(d,schedule,block['obj'],costs)
                integer_error=certificate.get('residuals',{}).get('max_integer_violation',0.)
                remaining=cfg.get('time_limit',600.)-block['runtime']
                if not certificate['passed'] and 1e-6<integer_error<1e-3 and remaining>1.:
                    # Numerical crossover can leave nearly-integer values outside
                    # our independent tolerance. Fix the discrete policy and solve
                    # the continuous problem again, within the original time budget.
                    policy=[(var,round(var.X)) for var in m.getVars()
                            if var.VType in (gp.GRB.BINARY,gp.GRB.INTEGER)]
                    original_certificate=certificate
                    for var,value in policy:var.LB=value;var.UB=value
                    m.Params.TimeLimit=remaining
                    m.optimize()
                    repair_runtime=float(m.Runtime)
                    block['runtime']+=repair_runtime
                    result['metadata']['integer_polish']=dict(runtime=repair_runtime,
                        fixed_variables=len(policy),previous_violations=original_certificate['violations'])
                    if m.SolCount:
                        block['obj']=float(m.ObjVal)
                        # The fixed-policy LP bound is not a global MILP bound.
                        bound=block['objective_bound']
                        block['mip_gap']=max(0.,(block['obj']-bound)/max(abs(block['obj']),1e-10)) if bound is not None else None
                        if block['status']=='OPTIMAL' and (block['mip_gap'] is None or block['mip_gap']>cfg.get('mip_gap',.001)+1e-9):
                            block['status']='SUBOPTIMAL'
                        schedule=built['extract']()
                        costs={key:float(value.getValue() if hasattr(value,'getValue') else value) for key,value in built['costs'].items()}
                        certificate=validate(d,schedule,block['obj'],costs)
                result.update(schedule=schedule,cost_breakdown=costs,validation=certificate)
                block['validation_passed']=certificate['passed']
                block.update(certificate['residuals'])
                result['metadata']['validation_seconds']=time.perf_counter()-tick
            else:
                result['validation']=dict(passed=False,violations={'no_solution':block['status']},residuals={})
            result['metadata']['wall_seconds']=time.perf_counter()-started
    if output_dir:
        filename={'main':'python_result.json','baseline':'baseline_result.json','mean':'mean_policy_result.json'}[mode]
        write_json(output_dir/filename,result)
    return result


def run_case(case,mode='main',time_limit=None):
    case=Path(case); d,cfg=load_case(case)
    if time_limit is not None:cfg['time_limit']=time_limit
    fixed=None
    if mode=='mean':d=mean_data(d)
    if mode=='baseline' and d['kind']=='stochastic':
        mean=solve_data(mean_data(d),cfg,mode='mean',output_dir=case/'results')
        if not mean['aidc39']['validation_passed']:
            out=dict(case=case.name,mode='baseline',input_sha256=data_hash(d),
                     aidc39=dict(status='ERROR',obj=None,validation_passed=False),
                     validation=dict(passed=False,violations={'mean_policy':'No independently validated mean policy'}))
            write_json(case/'results/baseline_result.json',out)
            return out
        fixed=mean['schedule']['first_stage']
    result=solve_data(d,cfg,mode=mode,output_dir=case/'results',fixed_first_stage=fixed)
    if mode=='main':
        on_disk=json.loads((case/'data/config.json').read_text())
        b=result['aidc39']
        on_disk['model_size']={k:b[k] for k in ['n_variables','n_constraints','n_nonzeros','n_binary','n_general_integer','n_continuous']}
        on_disk['physics_validated']=b['validation_passed']
        write_json(case/'data/config.json',on_disk)
    return result


def main(case):
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['main','baseline','mean'],default='main')
    parser.add_argument('--time-limit',type=float)
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    if args.validate_only:
        result=revalidate_saved(case); print(json.dumps(result,ensure_ascii=False));return 0 if result['passed'] else 1
    result=run_case(case,args.mode,args.time_limit); b=result['aidc39']
    print(json.dumps({k:b.get(k) for k in ['status','obj','runtime','mip_gap','validation_passed']},ensure_ascii=False))
    return 0 if b['validation_passed'] else 1
