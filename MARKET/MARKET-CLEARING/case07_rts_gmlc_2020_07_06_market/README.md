# case07_rts_gmlc_2020_07_06_market

- Source: `数据集/pglib-uc-master/rts_gmlc/2020-07-06.json`
- Horizon: 48 periods (copperplate multi-period energy market)
- Thermal units: 73, renewable: 81, supply blocks: 372
- Demand utility: synthetic VOLL = 10000.0 $/MWh
- Model: max welfare LP (offer acceptance + curtailable load)
- solve_tier: full
- Pricing: LP dual of power balance (= LMP per period)
