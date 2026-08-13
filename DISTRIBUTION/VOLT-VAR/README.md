# VOLT-VAR

> **Maturity:** experimental · **validation:** structural only · **physics validated:** no

Exploratory SMART-DS GSO rural feeder placeholder built on an active-power transport model. The model has no voltage variables, voltage-drop equations, or reactive-power balance. Its `Qsh` decision is not coupled to the network constraints, so the stored result does not demonstrate Volt/VAR control or voltage feasibility.

The category is retained to make the coverage gap explicit, but this example is excluded from physics-validated Volt/VAR coverage.

```bash
python3 run_all_python.py
python3 DISTRIBUTION/VOLT-VAR/case02_gso_rural_voltvar/solve.py
```
