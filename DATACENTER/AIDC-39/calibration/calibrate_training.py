"""Record sequential workload-difficulty experiments, with unchanged solver settings."""
import argparse
import copy
import json
from pathlib import Path
import sys

import numpy as np

PACK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACK))
from common.data import make_data, training_data, load_case, write_json, data_hash
from common.runner import solve_data
from common.training import candidates, earliest_deadline_schedule


def run(label,job_count,margin,repeats,wait_cost_scale=1.):
    _,cfg=load_case(PACK/'case001_training_uc')
    cfg.update(seed=1,threads=4,time_limit=600.,mip_gap=.001)
    cfg.pop('model_size',None);cfg.pop('features',None);cfg['physics_validated']=False
    cfg['training_profile']=dict(n_jobs=job_count,wait_cost_scale=wait_cost_scale,window_margin_slots=margin)
    d=make_data('training')
    d.update(training_data(np.random.default_rng(101),96,job_count=job_count,
                           window_margin_slots=margin,wait_cost_scale=wait_cost_scale))
    destination=PACK/'calibration'/label
    if destination.exists():raise ValueError('Use a new label to preserve earlier timing evidence')
    inputs=copy.deepcopy(d);network=inputs.pop('network')
    write_json(destination/'data/aidc.json',inputs)
    write_json(destination/'data/network.json',network)
    write_json(destination/'data/config.json',cfg)
    summary=dict(label=label,n_jobs=job_count,window_margin_slots=margin,wait_cost_scale=wait_cost_scale,
        work_block_hours=sum(j['work_block_hours'] for j in d['jobs']),
        start_mode_choices=len(candidates(d)),edf_compute_feasible=earliest_deadline_schedule(d) is not None,
        input_sha256=data_hash(d),settings={k:cfg[k] for k in ['seed','threads','time_limit','mip_gap']},runs=[])
    print(json.dumps(summary),flush=True)
    for i in range(repeats):
        result=solve_data(d,cfg,output_dir=destination/f'run_{i+1}')
        summary['runs'].append({k:result['aidc39'][k] for k in ['status','runtime','obj','objective_bound','mip_gap','validation_passed','node_count','n_binary']})
        cfg['model_size']={k:result['aidc39'][k] for k in ['n_variables','n_constraints','n_nonzeros','n_binary','n_general_integer','n_continuous']}
        cfg['physics_validated']=result['aidc39']['validation_passed']
        write_json(destination/'data/config.json',cfg)
        write_json(destination/'summary.json',summary)
        print(json.dumps(summary['runs'][-1]),flush=True)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--label',required=True)
    p.add_argument('--jobs',type=int,required=True)
    p.add_argument('--margin',type=int,default=19)
    p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--wait-cost-scale',type=float,default=1.)
    a=p.parse_args();run(a.label,a.jobs,a.margin,a.repeats,a.wait_cost_scale)
