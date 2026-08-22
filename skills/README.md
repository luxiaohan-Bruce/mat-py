# 约束处理 skills

每条 `SKILL.md`：论文算法解读 → 五段工具包装（元数据 / Schema / 代码 / 异常 / Few-shot）。有递进关系的放同一文件夹。

| 文件夹 | 路线 |
|--------|------|
| [`constraint-screening/`](constraint-screening/) | 第一次 `optimize` 前判定哪侧热稳可删 |
| [`iterative-enforcement/`](iterative-enforcement/) | 松弛先解，SFT 扫违反再加割 |
| [`decomposition/`](decomposition/) | 主问题 UC + 事故可行割；无开关不要 CNR |
