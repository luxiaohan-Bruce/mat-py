# SMART-DS aggregated feeder cases

Three linearized variants from one GSO rural OpenDSS feeder (node-aggregated):

1. LinDistFlow DNR
2. Volt/VAR capacitors
3. DER hosting capacity

```bash
python3 common/build_all_from_smartds.py
python3 run_all_python.py
matlab -batch "run_all_matlab"
```
