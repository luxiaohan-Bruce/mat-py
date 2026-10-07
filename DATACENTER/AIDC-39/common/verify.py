"""File-backed independent verification, usable without importing a solver."""
import json
from pathlib import Path
import numpy as np
from .data import load_case,data_hash,mean_data
from .validation import validate


def revalidate_saved(case,result_path=None):
    case=Path(case); d,_=load_case(case)
    result=json.loads(Path(result_path or case/'results/python_result.json').read_text())
    if result.get('mode')=='mean':d=mean_data(d)
    if result.get('input_sha256')!=data_hash(d):
        return dict(passed=False,violations={'input_sha256':'Saved solution does not match current physical/business inputs'})
    if not result.get('schedule'):
        return dict(passed=False,violations={'schedule':'No complete solution'})
    out=validate(d,result['schedule'],result['aidc39']['obj'],result['cost_breakdown'])
    if d['kind']=='stochastic' and result.get('mode')=='baseline':
        fixed=result.get('fixed_first_stage')
        if fixed is None:
            out['passed']=False;out['violations']['fixed_policy']='Missing fixed mean policy'
        else:
            actual=result['schedule']['first_stage']
            for key in ['gpu_blocks','gpu_starts','pg0_mw','reserve_up_mw','reserve_down_mw']:
                if not np.allclose(actual[key],fixed[key],rtol=0,atol=1e-6):
                    out['passed']=False;out['violations']['fixed_policy_'+key]='Policy differs from mean plan'
            for key in ['on','start','stop']:
                if not np.allclose(actual['uc'][key],fixed['uc'][key],rtol=0,atol=1e-6):
                    out['passed']=False;out['violations']['fixed_policy_uc_'+key]='UC policy differs from mean plan'
    return out
