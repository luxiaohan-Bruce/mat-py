# case01_gso_rural_dnr

SMART-DS aggregated-feeder `dnr` example. **Experimental / structural-only; not physics validated.**

The executable formulation is active-power transport with switching, not LinDistFlow: it omits voltage/drop equations, reactive-power balance, and radiality/connectivity constraints. A solver optimum is not a certified radial feeder configuration.
