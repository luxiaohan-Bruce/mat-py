# case14_ca_2014_09_01_reserves_1_market

- Source: `数据集/pglib-uc-master/ca/2014-09-01_reserves_1.json`
- Horizon: 48 periods (copperplate multi-period energy market)
- Thermal units: 610, renewable: 0, supply blocks: 1488
- Demand utility: synthetic VOLL = 10000.0 $/MWh
- Model: max welfare LP (offer acceptance + curtailable load)
- solve_tier: full
- Pricing: LP dual of power balance (= LMP per period)
