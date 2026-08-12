#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / 'common'))
from bid_model_py import run_case
if __name__ == '__main__':
    r = run_case(CASE_DIR, quiet=True)
    e = r['bid']
    print(f"[{r['case']}] {e['status']} profit={e.get('profit')} level={e.get('best_level')} firm_MW={e.get('firm_MW')}")
