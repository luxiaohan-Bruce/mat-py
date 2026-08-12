#!/usr/bin/env python3
import json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'common'))
from smartds_model_py import run_case
def main():
    man=json.loads((ROOT/'MANIFEST.json').read_text()); fail=0
    for item in man:
        try:
            r=run_case(ROOT/item['case'],quiet=True)['smartds']
            print(f"[{item['case']}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime',0):.2f}s", flush=True)
            if r.get('obj') is None: fail+=1
        except Exception as e:
            fail+=1; print(f"[{item['case']}] ERROR {e}"); traceback.print_exc()
    print(f'done; failures={fail}'); return 1 if fail else 0
if __name__=='__main__':
    raise SystemExit(main())
