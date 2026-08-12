# VERIFY_SUMMARY market_clearing

- checked: 56/56 PASS
- full tier: 32/32 PASS (dual required)
- relaxed tier: 24/24 PASS
- residual checks: offer bounds, power balance, welfare recompute
- model: copperplate multi-period welfare-max energy LP
- pricing: LP dual of balance (LMP); UC+MILP would fix binaries then re-LP
