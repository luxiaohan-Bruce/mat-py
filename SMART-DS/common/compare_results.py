#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    man=json.loads((ROOT/'MANIFEST.json').read_text()); ok=chk=0
    for item in man:
        chk+=1; c=ROOT/item['case']
        py=c/'results'/'python_result.json'; mat=c/'results'/'matlab_result.json'
        rep={'case':item['case'],'ok':False,'issues':[]}
        if not py.exists() or not mat.exists():
            rep['issues'].append('missing')
        else:
            po=json.loads(py.read_text())['smartds'].get('obj')
            mo=json.loads(mat.read_text())['smartds'].get('obj')
            if po is None or mo is None: rep['issues'].append('no obj')
            else:
                rel=abs(po-mo)/max(1.0,abs(po),abs(mo))
                if rel>0.05: rep['issues'].append(f'rel {rel}')
            rep['ok']=not rep['issues']
        (c/'results'/'comparison.json').write_text(json.dumps(rep,indent=2)+'\n')
        ok+=int(rep['ok']); print(f"{item['case']}: {'PASS' if rep['ok'] else 'FAIL'}")
    print(f'summary {ok}/{chk}'); return 0 if ok==chk else 1
if __name__=='__main__':
    raise SystemExit(main())
