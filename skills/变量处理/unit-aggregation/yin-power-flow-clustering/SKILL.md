---
name: yin-power-flow-clustering
description: >-
  当随机或确定性网络约束 UC 中跨节点机组聚合造成潮流偏差或场景间机组身份不一致时，用代表工况的 NCUC 对照和电气距离迭代拆簇，再恢复原机组共同启停。
---

# Yin：以潮流偏差迭代细分机组簇

Yue Yin, Chuan He, Tianqi Liu, Lei Wu. Risk-Averse Stochastic Midterm Scheduling of Thermal-Hydro-Wind System: A Network-Constrained Clustered Unit Commitment Approach. IEEE Transactions on Sustainable Energy 13(3), 2022, 1293–1304.

## 算法解读

用相同代表工况分别求原 NCUC 和聚合 NC-CUC，比较潮流后迭代拆簇。优先处理簇内电气距离和最大的簇，再拆出距离和高于簇内均值的成员。带符号潮流误差会相互抵消，验收还必须检查绝对误差、过载及原逐机共同启停。

本 skill 的核心是改善机组分簇。原问题没有风险目标或场景缩减时，不为采用本方法新增 CVaR、改概率或减少场景。先读[关键建模关系](#关键建模关系)。

**整段算法：**

1. 选择并固定代表工况，求解原 NCUC 得参考潮流；完整记录这部分成本。按容量、爬坡、最小开停时间等相似性初始化热机簇；水机只能在共享真实水文连接且参数兼容的厂站内分组。
2. 建立 NC-CUC：簇整数启停与总出力，逐机连续出力保留真实节点，用总和耦合，再施加全网络约束。每个场景共用第一阶段簇启停，场景出力作追索。
3. 在相同代表工况求聚合潮流，计算论文带符号平均偏差；另记录逐线绝对偏差、最大偏差及过载。带符号均值可抵消误差，不能仅靠它验收原模型可行性。
4. 不达阈值时，找簇内成对电气距离总和最大的非单例簇；将与其余成员距离和超过均值的机组移到新簇，再求解。距离相等导致空分割时，按固定顺序拆出一台，保证簇数增长；这是工程退化处理。
5. 固定最终簇映射求目标实例。恢复时使用**跨场景共同的逐机二元状态**，允许场景出力变化；分别在每个场景检查原最小出力、爬坡、启停、网络及原有风险/水量约束。逐场景独立选机不能满足两阶段非预见性。
6. 恢复失败时继续拆簇或释放聚合建议，最终回退原逐机模型。代表工况阈值达标仅说明训练工况接近，不保证新负荷和场景下误差有界。

### 关键建模关系

#### 原方法与关键约束

§II.B Algorithm 1：固定代表负荷，先求原NCUC，再初始化参数相似簇，循环求NC-CUC并比较潮流；对电气距离总和最大的簇拆出偏离成员。$\mathrm{DG}_c=\sum_{k\in c}\sum_{j\in c,\,j\ne k}\mathrm{DG}(k,j)$；每成员分数应解释为固定该成员对其它成员的距离和，比较阈值 $\mathrm{DG}_c/N_c$。原Step5求和变量与待选变量重复，PDF第5页仍有这一记号问题，本文代码以“每个成员的距离和”明确化。

原偏差 $\Delta=\frac{1}{L}\sum_{\ell}\Upsilon_{\ell}\frac{F_{\ell}^{\mathrm{UC}}-F_{\ell}^{\mathrm{CUC}}}{F_{\ell}^{\mathrm{UC}}}$，$\Upsilon_{\ell}=F_{\ell}^{\mathrm{UC}}/F_{\ell}^{\mathrm{UC,max}}$。同向正归一化基准下可代数约为 $\frac{1}{L}\sum_{\ell}\frac{F_{\ell}^{\mathrm{UC}}-F_{\ell}^{\mathrm{CUC}}}{F_{\ell}^{\mathrm{UC,max}}}$，避免零参考潮流相除；但基准为零仍需改用正线路容量/绝对MW阈值并记录适配。原文没完整定义 $F^{\mathrm{UC,max}}$ 的选择，也没唯一指定 DG 计算方式；实施前明确口径，不能宣称使用了作者未提供的公式。符号均值会让+10%与−10%相抵，因此增加绝对/最大差及原线限检查属于必要的工程验收。

§II.A式14保留逐机 $0\le p_g\le p_g^{\max}$、$\sum_{g\in c}p_g=P_c$；逐机最低稳定出力和身份被省略。第一阶段共用簇数量，并不意味着各场景自动共用真实机组身份。电气位置不同的机组可能在场景间替换。拆簇改善这一近似但没有一般误差界，恢复仍需共同逐机状态。

原式10–13用算术均值处理容量、爬坡、开停时间及水机排水量，区别于Du/Palmintier的容量加权部分。源文称同质簇等价，不能忽略其仍简化的爬坡、启停/历史和网络身份条件。

#### 时序、水电与风险部分

原研究以12个月、每月4个代表日、每代表日24小时表示年度，并非8760个连续小时。保持水库前期末=后期初及上下游滞后；代表日权重和水量缩放没有在所有式子中明确展开，不可直接将1152小时能量当作全年总能量。仓库只测试分簇时应保持原始时间网格。

式7 $P=\eta Q(h_0+\delta V)$ 双线性。水量守恒须将流量乘秒数或直接用时段水量，初末库容与跨时段上游来水时滞不能丢失。附录A.1–A.4是Q、V边界上的四个 McCormick 包络；内部点并不强制乘积相等。若离线$q=0$，应使用覆盖0的界或条件化包络，不能用正qmin对所有状态无条件套用。必须检验原非线性转换残差，不能把MILP松弛可行称为水电物理精确。

§III式28的印刷目标为基准工况运行成本 $G(x,y_b)+\lambda\operatorname{CVaR}$，不是任意加入“期望成本+CVaR”的新目标。第一阶段不允许弃风/失负荷，第二阶段允许有罚项的追索，并有基准与场景出力纠正爬坡连接。x跨场景共享；多阶段逐步获知信息的非预见性扩展在结论列为未来工作。

CVaR等概率式26–27为 $\alpha+\frac{\sum_\xi z_\xi}{N_S(1-\beta)}$，$z_\xi\ge\mathrm{loss}_\xi-\alpha,\quad z_\xi\ge0$。表I缩减后场景概率明显不等，工程实现应使用 $\alpha+\frac{\sum_\xi\rho_\xi z_\xi}{1-\beta}$，验证 $\sum_\xi\rho_\xi=1$；这是修正等概率样本公式到实际加权场景的适配。概率、β、λ和loss单位须与原问题一致。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `split_by_electrical_distance`
- **Description**: 当随机或确定性网络约束 UC 中跨节点机组聚合造成潮流偏差或场景间机组身份不一致时，用代表工况的 NCUC 对照和电气距离迭代拆簇，再恢复原机组共同启停。
- **实现范围**: 对一个已选簇按给定电气距离拆分；不计算距离、不选择目标簇，也不求 NCUC。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回 `(retained_ids,moved_ids)` 两个非空成员列表；等距退化时稳定拆出一台。

**完整流程输出与保证：**

输出代表工况及参考解质量、电气距离定义、每轮簇映射/潮流误差/耗时、最终聚合解与跨场景逐机恢复、原目标、有效界/gap和全部残差。该方法为近似分簇，不保证原问题全局最优或逐机身份自动一致。水头双线性项的 McCormick 包络是松弛，若原问题使用非线性水电关系，须按原关系恢复验证。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入原 NCUC、逐机参数和节点、电气距离矩阵、代表负荷/可再生工况、初始簇数与潮流偏差阈值、线路方向/限额 MW、场景概率及信息结构、原成本和时间网格。含水电时还需真实库容 m³、流量 m³/s或时段水量、时滞、水头和转换系数、初末库容。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "ids",
    "distances"
  ],
  "properties": {
    "ids": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "原机组 id，顺序用于退化时稳定选择。"
      },
      "minItems": 2,
      "uniqueItems": true
    },
    "distances": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "number",
          "description": "调用方定义的非负电气距离；全矩阵采用一致尺度。",
          "minimum": 0
        },
        "minItems": 2
      },
      "minItems": 2
    }
  },
  "additionalProperties": false
}
```

矩阵为 $N\times N$（$N$ 为机组数量），须对称、对角为零。论文未唯一明确距离计算公式，必须记录调用方定义或明确标注 PTDF 距离适配。

---

## 3. 核心代码实现 (Python Implementation)

该函数接收已经选出的簇及其对称非负距离矩阵；论文没有唯一明确的距离计算公式，不要把欧氏地理距离当作论文定义。可由调用者提供电气距离，或明确采用 PTDF 差异距离作为工程适配。

```python
import math

def split_by_electrical_distance(ids, distances):
    n = len(ids)
    if n < 2 or len(set(ids)) != n or len(distances) != n:
        raise ValueError("a non-singleton cluster with unique ids is required")
    if any(len(row) != n for row in distances):
        raise ValueError("distance matrix shape mismatch")
    for i in range(n):
        for j in range(n):
            value = distances[i][j]
            if not math.isfinite(value) or value < 0:
                raise ValueError("invalid electrical distance")
            if abs(value - distances[j][i]) > 1e-10:
                raise ValueError("symmetric distance required")
        if abs(distances[i][i]) > 1e-10:
            raise ValueError("diagonal must be zero")
    scores = [sum(row) for row in distances]
    mean = sum(scores) / n
    moved = {i for i, score in enumerate(scores) if score > mean + 1e-12}
    if not moved:
        moved = {max(range(n), key=lambda i: (scores[i], -i))}
    return ([ids[i] for i in range(n) if i not in moved],
            [ids[i] for i in range(n) if i in moved])
```

例：A/B距离1、A/C和B/C距离5，则把C拆出。两机距离相等时按固定规则拆一台，最多经过N−初始簇数次有效拆分可到逐机；是否在预算内完成另行判断。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 单例簇、重复 id、矩阵维度或数值不合法 | 抛出 ValueError。 |
| 距离全部相等，没有高于均值的成员 | 按固定顺序拆出一台，保证簇数增长。 |
| 参考潮流为零、带符号偏差抵消或跨场景身份不一致 | 使用有效归一化并报告绝对误差；以共同逐机二元状态恢复，不按场景独立选机。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: A/B 电气距离为 1，A/C 与 B/C 为 5，拆分这个三机簇。

**调用说明**: 使用 `split_by_electrical_distance` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "split_by_electrical_distance",
  "ids": [
    "A",
    "B",
    "C"
  ],
  "distances": [
    [
      0,
      1,
      5
    ],
    [
      1,
      0,
      5
    ],
    [
      5,
      5,
      0
    ]
  ]
}
```

**Observation**: 保留 [A,B]，移出 [C]。下一轮在相同代表工况重解聚合网络模型；达到训练工况阈值不保证新负荷和新场景下可行。

### 验证与后续对照实验

小测三机拆分及全相等距离退化、零参考潮流与带符号抵消；构造两个场景簇在线数均1但分别选择A/B的解，确认共同启停恢复拒绝它。对照相同实例、硬件、总预算与停止标准，报告参考NCUC求解+距离/分簇+各轮聚合求解+正式求解+恢复+验证的总耗时，及原目标、有效界/gap、原可行性和变量数。预处理重复使用时分别报告首次与摊销成本；不得隐去首次成本。本次未运行全库实验。
