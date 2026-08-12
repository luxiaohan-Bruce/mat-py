# case50_ferc_2015_09_01_lw_market

- Source: `数据集/pglib-uc-master/ferc/2015-09-01_lw.json`
- Horizon: 48 periods (copperplate multi-period energy market)
- Thermal units: 978, renewable: 1, supply blocks: 2857
- Demand utility: synthetic VOLL = 10000.0 $/MWh
- Model: max welfare LP (offer acceptance + curtailable load)
- solve_tier: relaxed
- Pricing: LP dual of power balance (= LMP per period)
