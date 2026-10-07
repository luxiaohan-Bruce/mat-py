"""Refresh only this pack's configs/manifest, and optionally the shared catalog."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import gurobipy as gp
from common.data import CASES,PACK,load_case,write_json
from common.runner import build_model
from framework.features import extract_features
from framework.catalog import write_catalog


def refresh(rebuild_catalog=False):
    manifest=[]
    for name,_,_ in CASES:
        case=PACK/name;d,cfg=load_case(case)
        if not cfg.get('model_size'):
            with gp.Env(empty=True) as env:
                env.setParam('OutputFlag',0);env.start()
                with gp.Model(env=env) as m:
                    build_model(m,d);m.update()
                    cfg['model_size']=dict(n_variables=m.NumVars,n_constraints=m.NumConstrs,n_nonzeros=m.NumNZs,
                        n_binary=m.NumBinVars,n_general_integer=m.NumIntVars-m.NumBinVars,n_continuous=m.NumVars-m.NumIntVars)
        feats=extract_features(cfg,d['network'],pack='DATACENTER/AIDC-39')
        cfg['features']={**feats,'math_class':'milp','solver_family':'temporal_mip'}
        write_json(case/'data/config.json',cfg)
        manifest.append(dict(case=name,source='pglib_opf_case39_epri',**feats,
                             solve_tier='full',base_problem='datacenter_flex',problem='aidc39',variant=cfg['variant']))
    write_json(PACK/'MANIFEST.json',manifest)
    if rebuild_catalog:write_catalog(PACK.parents[1])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalog',action='store_true')
    refresh(p.parse_args().catalog)
