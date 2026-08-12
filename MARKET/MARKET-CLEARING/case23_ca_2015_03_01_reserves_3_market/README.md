# case23_ca_2015_03_01_reserves_3_market

- Source: `数据集/pglib-uc-master/ca/2015-03-01_reserves_3.json`
- Horizon: 48 periods (copperplate multi-period energy market)
- Thermal units: 610, renewable: 0, supply blocks: 1488
- Demand utility: synthetic VOLL = 10000.0 $/MWh
- Model: max welfare LP (offer acceptance + curtailable load)
- solve_tier: full
- Pricing: LP dual of power balance (= LMP per period)
