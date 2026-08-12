# LinDistFlow DNR / DOPF / DNR+ESS

Linear distribution network reconfiguration (not exact AC). SimBench MV/LV switchable feeders, plus one SMART-DS GSO rural DNR case (`case01_gso_rural_dnr`). Complete mixed SimBench dataset is a meta/profile source (`solve_tier=skip`).

Volt/VAR and DER hosting from the same SMART-DS feeder live in `DISTRIBUTION/VOLT-VAR` and `DISTRIBUTION/DER-HOSTING`.

```bash
python3 common/build_all_from_simbench.py
python3 run_all_python.py
python3 case01_mv_rural_dnr/solve.py
```
