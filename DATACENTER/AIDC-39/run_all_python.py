from pathlib import Path
import argparse
import json
from common.data import CASES
from common.runner import run_case

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--with-baselines',action='store_true')
    parser.add_argument('--time-limit',type=float)
    parser.add_argument('--case',choices=[c[1] for c in CASES])
    args=parser.parse_args()
    failed=False
    for name,kind,_ in CASES:
        if args.case and kind!=args.case: continue
        case=Path(__file__).resolve().parent/name
        for mode in ['main']+(['baseline'] if args.with_baselines else []):
            print(f'Starting {name} {mode}',flush=True)
            r=run_case(case,mode,args.time_limit)
            print(json.dumps({'case':name,'mode':mode,**{k:r['aidc39'].get(k) for k in ['status','runtime','obj','mip_gap','validation_passed']}},ensure_ascii=False),flush=True)
            if mode=='main' and not r['aidc39']['validation_passed']:failed=True
    raise SystemExit(1 if failed else 0)
