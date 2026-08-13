# Experimental active-power transport DNR / DNR+ESS

> **Maturity:** experimental · **validation:** structural only · **physics validated:** no

This package keeps the DNR category and contains **6 examples**: SimBench MV/LV DNR and DNR+ESS cases, one SMART-DS GSO rural DNR case (`case01_gso_rural_dnr`), and one complete mixed SimBench meta/profile source (`solve_tier=skip`). The executable model is an active-power transport proxy, not LinDistFlow or exact three-phase AC.

The model has active-power nodal balance, branch-capacity limits, switching variables, load shedding, and optional ESS. It does **not** have voltage-magnitude variables, voltage-drop equations, reactive-power balance, or radiality/energized-connectivity constraints. Therefore solver completion only validates model execution; these examples are excluded from physics-validated DNR coverage.

The two multiperiod DOPF cases were moved to [`../DISTRIBUTION-OPF`](../DISTRIBUTION-OPF/).

Volt/VAR and DER hosting from the same SMART-DS feeder live in `DISTRIBUTION/VOLT-VAR` and `DISTRIBUTION/DER-HOSTING`.

```bash
python3 common/build_all_from_simbench.py
python3 run_all_python.py
python3 case01_mv_rural_dnr/solve.py
```
