# SimBench LinDistFlow DNR / DOPF / DNR+ESS

Linear distribution network reconfiguration (not exact AC). Built from SimBench MV/LV switchable feeders; complete mixed dataset kept as meta/profile source.

```bash
python3 common/build_all_from_simbench.py
python3 run_all_python.py
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
