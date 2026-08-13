#!/usr/bin/env python3
"""One-shot: unmix packs, unify entrypoints, backfill config, write catalog."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.catalog import backfill_config, iter_cases, write_catalog  # noqa: E402
from framework.runner import SOLVE_SHIM  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def move_mld() -> None:
    src = ROOT / "DISPATCH" / "MAXIMUM-LOAD-DELIVERY"
    dst = ROOT / "RESILIENCE" / "MAXIMUM-LOAD-DELIVERY"
    if src.is_dir() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"moved {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    elif dst.is_dir():
        print("MLD already under RESILIENCE")
    else:
        print("WARN: MLD source missing")


def _copy_pack_scaffold(src_pack: Path, dst_pack: Path, case_name: str, title: str, mode: str) -> None:
    if dst_pack.exists():
        print(f"exists {dst_pack.relative_to(ROOT)}")
        return
    dst_pack.mkdir(parents=True)
    shutil.copytree(src_pack / "common", dst_pack / "common")
    shutil.copytree(src_pack / case_name, dst_pack / case_name)
    man = [{"case": case_name, "mode": mode, "solve_tier": "full"}]
    (dst_pack / "MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    run_all = '''#!/usr/bin/env python3
import json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from smartds_model_py import run_case

def main():
    man = json.loads((ROOT / "MANIFEST.json").read_text())
    fail = 0
    for item in man:
        try:
            r = run_case(ROOT / item["case"], quiet=True)["smartds"]
            print(f"[{item['case']}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime', 0):.2f}s", flush=True)
            if r.get("obj") is None:
                fail += 1
        except Exception as e:
            fail += 1
            print(f"[{item['case']}] ERROR {e}")
            traceback.print_exc()
    print(f"done; failures={fail}")
    return 1 if fail else 0

if __name__ == "__main__":
    raise SystemExit(main())
'''
    _write(dst_pack / "run_all_python.py", run_all)
    _write(
        dst_pack / "README.md",
        f"# {title}\n\n"
        f"Experimental active-power transport placeholder from an aggregated "
        f"SMART-DS feeder; not physics-validated LinDistFlow or three-phase AC.\n\n"
        f"```bash\npython3 run_all_python.py\n"
        f"python3 {dst_pack.relative_to(ROOT)}/{case_name}/solve.py\n```\n",
    )
    vs = src_pack / "VERIFY_SUMMARY.md"
    if vs.is_file():
        shutil.copy2(vs, dst_pack / "VERIFY_SUMMARY.md")
    print(f"created {dst_pack.relative_to(ROOT)}")


def split_smartds() -> None:
    src = ROOT / "DISTRIBUTION" / "SMART-DS"
    if not src.is_dir():
        print("SMART-DS already split")
        return
    dnr = ROOT / "DISTRIBUTION" / "DNR"
    common_src = src / "common" / "smartds_model_py.py"
    if common_src.is_file():
        shutil.copy2(common_src, dnr / "common" / "smartds_model_py.py")
        cmp = src / "common" / "compare_results.py"
        if cmp.is_file():
            shutil.copy2(cmp, dnr / "common" / "smartds_compare_results.py")
        bld = src / "common" / "build_all_from_smartds.py"
        if bld.is_file():
            shutil.copy2(bld, dnr / "common" / "build_all_from_smartds.py")

    dnr_case = src / "case01_gso_rural_dnr"
    dest_case = dnr / "case01_gso_rural_dnr"
    if dnr_case.is_dir() and not dest_case.exists():
        shutil.copytree(dnr_case, dest_case)
        print("copied SMART-DS DNR case into DISTRIBUTION/DNR")

    man_path = dnr / "MANIFEST.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    if not any(x.get("case") == "case01_gso_rural_dnr" for x in man):
        man.append({
            "case": "case01_gso_rural_dnr",
            "folder": "GSO-rural-base_peak-rhs1_1247--rdt137",
            "mode": "smartds_dnr",
            "T": 1,
            "solve_tier": "full",
        })
        man_path.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")

    run_all = dnr / "run_all_python.py"
    _write(
        run_all,
        '''#!/usr/bin/env python3
import json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from dnr_model_py import run_case as run_dnr
try:
    from smartds_model_py import run_case as run_smartds
except ImportError:
    run_smartds = None

def main():
    man = json.loads((ROOT / "MANIFEST.json").read_text())
    fail = 0
    for item in man:
        if item.get("solve_tier") == "skip":
            print(f"[{item['case']}] SKIP")
            continue
        case_dir = ROOT / item["case"]
        try:
            cfg = json.loads((case_dir / "data" / "config.json").read_text())
            prob = str(cfg.get("problem") or item.get("mode") or "")
            if run_smartds is not None and ("smartds" in prob or item.get("mode") == "smartds_dnr"):
                r = run_smartds(case_dir, quiet=True)["smartds"]
            else:
                r = run_dnr(case_dir, quiet=True)["dnr"]
            print(f"[{item['case']}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime', 0):.2f}s", flush=True)
            if r.get("obj") is None:
                fail += 1
        except Exception as e:
            fail += 1
            print(f"[{item['case']}] ERROR {e}")
            traceback.print_exc()
    print(f"done; failures={fail}")
    return 1 if fail else 0

if __name__ == "__main__":
    raise SystemExit(main())
''',
    )

    _copy_pack_scaffold(
        src,
        ROOT / "DISTRIBUTION" / "VOLT-VAR",
        "case02_gso_rural_voltvar",
        "VOLT-VAR",
        "voltvar",
    )
    _copy_pack_scaffold(
        src,
        ROOT / "DISTRIBUTION" / "DER-HOSTING",
        "case03_gso_rural_hosting",
        "DER-HOSTING",
        "hosting",
    )
    shutil.rmtree(src)
    print("removed DISTRIBUTION/SMART-DS")


def _fix_case_dir(text: str) -> str:
    text = text.replace("parents[1]s[1]", "parents[1]")
    if "parents[1]" in text:
        return text
    text = text.replace(
        "CASE_DIR = Path(__file__).resolve().parent\nROOT = CASE_DIR.parent",
        "CASE_DIR = Path(__file__).resolve().parents[1]\nROOT = CASE_DIR.parent",
    )
    text = text.replace(
        "CASE_DIR = Path(__file__).resolve().parent\n",
        "CASE_DIR = Path(__file__).resolve().parents[1]\n",
    )
    return text


def normalize_entries() -> None:
    moved = 0
    renamed = 0
    for case in iter_cases(ROOT):
        py = case / "python"
        for src in list(case.glob("solve_*.py")):
            if src.name == "solve.py":
                continue
            py.mkdir(exist_ok=True)
            dest = py / src.name
            text = _fix_case_dir(src.read_text(encoding="utf-8"))
            dest.write_text(text, encoding="utf-8")
            src.unlink()
            moved += 1
        sca = py / "solve_scacopf.py"
        if sca.is_file() and case.parent.name in {"SC-AC-OTS", "LINEARIZED-SC-OTS"}:
            dest = py / "solve_scacots.py"
            if not dest.exists():
                sca.rename(dest)
                renamed += 1
    print(f"moved root solvers into python/: {moved}; renamed scacots: {renamed}")


def write_shims() -> None:
    n = 0
    for case in iter_cases(ROOT):
        shim = case / "solve.py"
        shim.write_text(SOLVE_SHIM, encoding="utf-8")
        n += 1
    print(f"wrote {n} case-root solve.py shims")


def backfill_all() -> None:
    n = 0
    for case in iter_cases(ROOT):
        backfill_config(case, ROOT)
        n += 1
    print(f"backfilled config.json on {n} cases")


def main() -> int:
    move_mld()
    split_smartds()
    normalize_entries()
    write_shims()
    backfill_all()
    cat, idx = write_catalog(ROOT)
    print(f"catalog -> {cat.name}, {idx.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
