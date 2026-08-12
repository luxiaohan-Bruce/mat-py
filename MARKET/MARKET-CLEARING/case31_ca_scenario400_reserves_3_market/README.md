# case31_ca_scenario400_reserves_3_market

- Source: `数据集/pglib-uc-master/ca/Scenario400_reserves_3.json`
- Horizon: 48 periods (copperplate multi-period energy market)
- Thermal units: 610, renewable: 1, supply blocks: 1489
- Demand utility: synthetic VOLL = 10000.0 $/MWh
- Model: max welfare LP (offer acceptance + curtailable load)
- solve_tier: full
- Pricing: LP dual of power balance (= LMP per period)
