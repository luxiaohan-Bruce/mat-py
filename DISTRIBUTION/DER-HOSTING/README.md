# DER-HOSTING

> **Maturity:** experimental · **validation:** structural only · **physics validated:** no

Exploratory SMART-DS GSO rural feeder placeholder built on an active-power transport model. It has no voltage variables, voltage-drop equations, reactive-power balance, or radiality constraints. DER injection is only a secondary objective term; the formulation does not maximize or certify feeder hosting capacity.

The category is retained to make the coverage gap explicit, but this example is excluded from physics-validated DER-hosting coverage.

```bash
python3 run_all_python.py
python3 DISTRIBUTION/DER-HOSTING/case03_gso_rural_hosting/solve.py
```
