# AIDC-39 三个优化调度案例的完整数学模型

| 案例 | 要决定什么 | 优化目标 | 主要耦合关系 |
|---|---|---|---|
| 一：训练作业与机组组合 | 每个训练作业何时开始、采用哪个档位，以及机组启停和出力 | 发电、机组启停、空载及作业流动时间成本最小 | 训练的时间选择改变电力负荷，机组组合与训练共享同一时间轴 |
| 二：跨站点推理与线路安全 | 各站模型副本数量、启动与关闭、实时请求路由，以及机组调度 | 发电、机组启停、空载、算力启动、模型部署及通信成本最小 | 请求空间分配改变节点负荷，并须满足全部 35 个非孤岛线路事故约束 |
| 三：日前—随机追补调度 | 日前确定机组、出力基准、备用和算力容量；各场景安排发电、训练、储能和风光消纳 | 日前成本、期望运行成本及 CVaR 风险成本之和最小 | 共享日前计划与 20 个场景的电网、工作量和电池状态耦合 |

## 1. 时间、符号和单位

三个案例均保留 39 个母线、46 条支路、10 个原有电源，优化 24 小时，时间分辨率为 15 分钟。案例三另在现有母线上接入风电和光伏，节点数不增加。

$$
\mathcal T=\{0,1,\ldots,95\},\qquad T=96,\qquad \Delta t=0.25\ \mathrm{h}.
$$

时段 $t$ 对应区间 $[t\Delta t,(t+1)\Delta t)$。作业到达和截止时刻用时段边界编号表示，执行窗口为 $[r_j,d_j)$；截止值 96 表示当日结束。储能电量定义在边界 $t=0,\ldots,T$ 上。

| 符号 | 定义 | 单位/范围 |
|---|---|---|
| $b\in\mathcal B$ | 母线，沿用原始编号 | $1,\ldots,39$ |
| $g\in\mathcal G$ | 原有电源，按输入顺序编号 | $0,\ldots,9$，接入母线 30～39 |
| $\ell\in\mathcal L$ | 支路，按输入 `id` 编号 | $0,\ldots,45$ |
| $d\in\mathcal D$ | AIDC 站点 | 案例一为 1 站；案例二、三为 3 站 |
| $\mathcal G_b,\mathcal D_b,\mathcal R_b$ | 接入母线 $b$ 的原有电源、AIDC、风光电源集合 | 前两例 $\mathcal R_b=\varnothing$ |
| $P_b^D$ | 原始母线有功负荷 | MW |
| $p_{gt}$ | 原有电源有功出力 | MW，连续非负变量 |
| $\theta_{bt},f_{\ell t}$ | 母线相角、支路有功潮流 | rad、MW，连续变量 |
| $P^{\mathrm{grid}}_{dt}$ | AIDC 与电网连接点的净取电功率 | MW，正值表示负荷 |
| $w_{rt}$ | 风光电源 $r$ 的实际消纳功率 | MW，仅案例三使用 |
| $u_{gt},v_{gt},z_{gt}$ | 电源在线、启动、停机状态 | 二元变量 |
| $A_{\ell b}$ | 支路—母线关联矩阵：起点为 $+1$、终点为 $-1$ | 常数 |

全部成本统一采用基准美元。功率乘 $\Delta t$ 后才是电量；请求速率乘 $3600\Delta t$ 后才是请求数量。算力块为合成的聚合资源单位，不等同于单张 GPU。

## 2. 三例共用的电网与机组组合模型

### 2.1 基础负荷与网络参数

基础负荷倍率为

$$
a_t=a_{\max}\left[0.8+0.2\sin^2\left(\pi\left(\frac{t}{T}-0.25\right)\right)\right],
\qquad
a_{\max}=\begin{cases}0.85,&\text{案例一、三},\\0.68,&\text{案例二}.\end{cases}
\tag{G1}
$$

令 $i(\ell),j(\ell)$ 分别为支路起点、终点，$x_\ell$ 为标幺电抗，$\tau_\ell$ 为变比，$\phi_\ell$ 为相移。原始 `ratio=0` 按 $\tau_\ell=1$ 处理；输入的角度由度转换为弧度。定义

$$
\beta_\ell=\frac{S_{\mathrm{base}}}{x_\ell\tau_\ell},\qquad S_{\mathrm{base}}=100\ \mathrm{MVA}.
$$

$F_\ell$ 取原始 `rateA` 的数值，在本 DC 模型中解释为 MW 限额。当前 46 条支路的 $x_\ell>0$ 且 $\phi_\ell=0$。

### 2.2 直流潮流、节点平衡和线路限制

对所有 $\ell\in\mathcal L,t\in\mathcal T$：

$$
f_{\ell t}=\beta_\ell\bigl(\theta_{i(\ell),t}-\theta_{j(\ell),t}-\phi_\ell\bigr).
\tag{G2}
$$

对所有 $b\in\mathcal B,t\in\mathcal T$：

$$
\sum_{g\in\mathcal G_b}p_{gt}+\sum_{r\in\mathcal R_b}w_{rt}
-a_tP_b^D-\sum_{d\in\mathcal D_b}P^{\mathrm{grid}}_{dt}
=\sum_{\ell\in\mathcal L}A_{\ell b}f_{\ell t}.
\tag{G3}
$$

支路功率和两端相角差满足

$$
-F_\ell\le f_{\ell t}\le F_\ell,\qquad
\underline\delta_\ell\le\theta_{i(\ell),t}-\theta_{j(\ell),t}\le\overline\delta_\ell,
\qquad \theta_{31,t}=0.
\tag{G4}
$$

其中 $\underline\delta_\ell,\overline\delta_\ell$ 来自源数据 `angmin/angmax`。模型无切负荷变量，电力和业务需求均须满足。

### 2.3 启停、出力和最小开停机时间

对所有 $g,t$，定义 $u_{g,-1}=1$，并施加

$$
u_{gt}-u_{g,t-1}=v_{gt}-z_{gt},\qquad
v_{gt}+z_{gt}\le1,\qquad u_{gt},v_{gt},z_{gt}\in\{0,1\}.
\tag{G5}
$$

$$
\underline P_g u_{gt}\le p_{gt}\le\overline P_g u_{gt}.
\tag{G6}
$$

30 号母线电源和 39 号母线外部电网等值固定在线：

$$
u_{gt}=1,\quad v_{gt}=z_{gt}=0
\qquad \text{若电源 }g\text{ 接入母线 }30\text{ 或 }39.
\tag{G7}
$$

设最小开机和停机时间均为 $U_g=D_g=8$ 个时段，即 2 小时：

$$
\sum_{k=\max(0,t-U_g+1)}^t v_{gk}\le u_{gt},\qquad
\sum_{k=\max(0,t-D_g+1)}^t z_{gk}\le1-u_{gt}.
\tag{G8}
$$

时域末端禁止无法履行完整持续期的启停：

$$
v_{gt}=0\ \text{若 }t+U_g>T,\qquad
z_{gt}=0\ \text{若 }t+D_g>T.
\tag{G9}
$$

所有电源初始已在线 16 个时段，大于最小开机时间，因此正式输入不存在初始剩余保持期。若改用一般初始状态，则在“最小持续期减去已持续时间”的正值区间内固定初始状态；这是实现支持的初始边界处理。

### 2.4 跨时段爬坡

对所有 $g$ 和 $t=1,\ldots,T-1$：

$$
\begin{aligned}
p_{gt}-p_{g,t-1}&\le R_g\Delta t\,u_{g,t-1}+\overline P_gv_{gt},\\
p_{g,t-1}-p_{gt}&\le R_g\Delta t\,u_{gt}+\overline P_gz_{gt}.
\end{aligned}
\tag{G10}
$$

这里 $R_g=0.6\overline P_g$ MW/h。启动、停机时允许额定出力幅度的变化。模型只给定初始在线状态和持续时间，**不指定 $p_{g,-1}$，不对首时段施加日初出力爬坡边界**。

### 2.5 公共参数和成本

原始电源最大出力 $\overline P_g$ 和边际能量成本 $c_g$ 如下；最小出力、爬坡、启停和空载成本为本算例合成参数。

| 接入母线 | $\overline P_g$（MW） | $c_g$（美元/MWh） |
|---|---:|---:|
| 30 | 1040 | 6.724778 |
| 31 | 646 | 14.707625 |
| 32 | 725 | 24.804734 |
| 33 | 652 | 34.844643 |
| 34 | 508 | 24.652994 |
| 35 | 687 | 32.306483 |
| 36 | 580 | 18.157477 |
| 37 | 564 | 31.550181 |
| 38 | 865 | 22.503168 |
| 39 | 1100 | 27.434444 |

$$
\begin{aligned}
\underline P_g&=\begin{cases}0,&b(g)=39,\\0.2\overline P_g,&b(g)\ne39,\end{cases}\\
C_g^{\mathrm{start}}&=(0.25\ \mathrm h)\,\overline P_gc_g,\qquad C_g^{\mathrm{stop}}=0,\\
C_g^{\mathrm{idle}}&=\begin{cases}0,&b(g)=39,\\0.04\overline P_gc_g,&b(g)\ne39.\end{cases}
\end{aligned}
$$

启动成本单位为美元/次，空载成本单位为美元/h。公共成本定义为

$$
C^{\mathrm{UC}}=\sum_{g,t}\left(C_g^{\mathrm{start}}v_{gt}+C_g^{\mathrm{stop}}z_{gt}\right)
+\Delta t\sum_{g,t}C_g^{\mathrm{idle}}u_{gt},\qquad
C^{\mathrm E}(p)=\Delta t\sum_{g,t}c_gp_{gt}.
\tag{G11}
$$

源文件的二次成本和常数项均为零，因此发电能量成本为线性。AIDC 取电通过节点平衡增加发电需求，目标中不再另加一次购买同一电量的电费。

下文把 (G2)～(G4) 称为“公共网络约束”，把 (G5)～(G10) 称为“公共 UC/出力约束”。案例三对每条出力轨迹分别施加出力与爬坡约束，共享同一组启停状态。

## 3. 案例一：训练作业与机组组合联合调度

### 3.1 参数和决策变量

在 16 号母线设置一个 AIDC，包含 64 个算力块，最大取电功率 300 MW，固定 IT 功率 16 MW，PUE 为 1.25。作业集合 $\mathcal J$ 包含 **240 个作业**。

| 参数 | 含义与当前设置 |
|---|---|
| $n_j$ | 作业固定并行规模，取 2、4 或 8 个块 |
| $W_j$ | 作业工作量，单位为标准块小时；全体合计 1368.5 标准块小时 |
| $r_j,d_j$ | 到达边界、截止边界 |
| $h_j$ | 作业流动时间成本系数，$4.5\times\{3,4,\ldots,12\}$ 美元/h |
| $q_k$ | 档位 $k$ 的吞吐系数，标准块小时/(块·小时) |
| $e_k$ | 档位 $k$ 的 IT 功率，MW/块 |

| 档位 $k$ | 名称 | $q_k$ | $e_k$（MW/块） |
|---|---|---:|---:|
| 0 | eco | 0.70 | 2.0 |
| 1 | balanced | 0.85 | 2.7 |
| 2 | fast | 1.00 | 3.5 |

给定档位后，先计算作业所需整时段数及允许开始集合：

$$
L_{jk}=\left\lceil\frac{W_j}{n_jq_k\Delta t}\right\rceil,\qquad
\mathcal S_{jk}=\{s\in\mathcal T:r_j\le s,\ s+L_{jk}\le d_j\}.
\tag{T1}
$$

定义二元变量 $x_{jks}$：若作业 $j$ 在时段 $s$ 开始并全程采用档位 $k$，则等于 1。仅对 $s\in\mathcal S_{jk}$ 建立变量。另定义预计算的占用指示常数

$$
a_{t,jks}=\begin{cases}1,&s\le t<s+L_{jk},\\0,&\text{其他}.
\end{cases}
\tag{T2}
$$

网络和 UC 变量为第 2 节的 $p,\theta,f,u,v,z$，另有连续变量 $P^{\mathrm{grid}}_{16,t}$；此处下标 16 直接标明接入母线。

### 3.2 每个作业恰好执行一次

$$
\sum_{k=0}^2\sum_{s\in\mathcal S_{jk}}x_{jks}=1
\qquad \forall j\in\mathcal J,\qquad x_{jks}\in\{0,1\}.
\tag{T3}
$$

候选开始集合保证不能提前执行且按期完成。每个候选对应一个固定的连续执行区间，因此上述变量定义同时保证不可抢占、不中断和执行中不切换档位。若某作业所有候选集合为空，模型不可行。

### 3.3 并行算力和用电耦合

每个时段的同时占用量不得超过 64 块：

$$
\sum_{j\in\mathcal J}\sum_{k=0}^2\sum_{s\in\mathcal S_{jk}}
n_ja_{t,jks}x_{jks}\le64
\qquad \forall t.
\tag{T4}
$$

取电功率满足

$$
P^{\mathrm{grid}}_{16,t}=1.25\left[16+
\sum_{j\in\mathcal J}\sum_{k=0}^2\sum_{s\in\mathcal S_{jk}}
n_je_ka_{t,jks}x_{jks}\right],\qquad
0\le P^{\mathrm{grid}}_{16,t}\le300.
\tag{T5}
$$

执行时间向上取整后，最后一个时段仍按完整时段占用算力并消耗该档位功率；模型没有最后一段按剩余工作量折减功率的处理。

### 3.4 目标函数和完整问题

作业完成边界为

$$
C_j=\sum_{k=0}^2\sum_{s\in\mathcal S_{jk}}(s+L_{jk})x_{jks}.
$$

完整优化问题为

$$
\begin{aligned}
\min\quad &C^{\mathrm{UC}}+C^{\mathrm E}(p)
+\Delta t\sum_{j\in\mathcal J}h_j(C_j-r_j),\\
\mathrm{s.t.}\quad &\text{公共网络约束、公共 UC/出力约束，}\ a_{\max}=0.85,\\
&\text{约束 (T3)～(T5)，候选和占用按 (T1)、(T2) 定义。}
\end{aligned}
\tag{T6}
$$

其中 $\Delta t(C_j-r_j)$ 是到达至完成的总时间，**包含排队和执行时间**。输入字段虽名为 `wait_cost_per_hour`，实际计入的是流动时间成本；本例没有允许逾期并缴纳罚金的决策。

## 4. 案例二：线路安全约束下的跨站点推理服务调度

### 4.1 集合、参数及服务能力—时延表

站点 $d=0,1,2$ 分别位于母线 4、16、27；请求区域 $r=0,\ldots,5$；推理模型 $m=0,\ldots,5$。区域 $r$ 的就近站点为 $\lfloor r/2\rfloor$。令 $\lambda_{rmt}$ 为每秒到达请求数，按时段给定。

| 站点参数 | 母线 4 | 母线 16 | 母线 27 |
|---|---:|---:|---:|
| 可用算力块上限 | 48 | 48 | 48 |
| 模型内存上限（GB） | 3200 | 3200 | 3200 |
| 取电功率上限（MW） | 200 | 200 | 200 |
| PUE，记为 $\gamma_d$ | 1.20 | 1.25 | 1.30 |
| 固定 IT 功率（MW） | 8 | 8 | 8 |
| 启动期功率（MW/块） | 2 | 2 | 2 |
| 总通信容量（Gbps） | 150 | 150 | 150 |

单副本参数如下，全部为合成设定。其中 $\mu_m$ 为请求服务能力，$\ell_m^{\mathrm{proc}}$ 为配套的处理时延，$L_m^{\mathrm{SLA}}$ 为端到端时延上限，$M_m$ 为模型内存，$e_m^{\mathrm{idle}}$ 为在线空载功率，$e_m^{\mathrm{dyn}}$ 为满负载额外功率，$b_m$ 为每请求通信量。

| $m$ | $\mu_m$（请求/s） | $\ell_m^{\mathrm{proc}}$（ms） | $L_m^{\mathrm{SLA}}$（ms） | $M_m$（GB） | $e_m^{\mathrm{idle}}$（MW） | $e_m^{\mathrm{dyn}}$（MW） | $b_m$（Mbit/请求） |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 900 | 8 | 40 | 40 | 1.10 | 1.75 | 1.0 |
| 1 | 800 | 12 | 50 | 48 | 1.18 | 1.75 | 1.5 |
| 2 | 700 | 18 | 55 | 60 | 1.26 | 1.75 | 2.0 |
| 3 | 600 | 25 | 70 | 72 | 1.34 | 1.75 | 3.0 |
| 4 | 500 | 32 | 80 | 90 | 1.42 | 1.75 | 4.0 |
| 5 | 400 | 40 | 90 | 110 | 1.50 | 1.75 | 6.0 |

区域到站点的通信时延矩阵为

$$
[\ell_{rd}^{\mathrm{net}}]=
\begin{bmatrix}
8&31&40\\
8&33&42\\
31&8&31\\
33&8&33\\
40&31&8\\
42&33&8
\end{bmatrix}\ \mathrm{ms}.
\tag{I1}
$$

每条区域—站点链路容量为 50 Gbps。通信单价为

$$
c_{rd}^{\mathrm{route}}=0.6+0.08\ell_{rd}^{\mathrm{net}}
\quad\text{美元/百万请求，其中时延代入 ms 数值。}
$$

处理时延按上表固定给出，并与不超过 $\mu_m$ 的服务能力配套使用。该设定是线性基准假设，不是由排队模型计算出的利用率相关时延，也不代表真实硬件测量或尾延迟保证。

### 4.2 决策变量

| 变量 | 含义 | 类型 |
|---|---|---|
| $n_{dmt}$ | 时段 $t$ 可服务的在线模型副本数 | 整数，$0\le n_{dmt}\le48$ |
| $b_{dmt}^{\mathrm{boot}}$ | 在时段 $t$ 启动的副本数，下个时段才可服务 | 整数，$0\le b_{dmt}^{\mathrm{boot}}\le48$ |
| $q_{dmt}^{\mathrm{off}}$ | 时段 $t$ 关闭的副本数 | 整数，$0\le q_{dmt}^{\mathrm{off}}\le48$ |
| $y_{rmdt}$ | 区域 $r$ 的模型 $m$ 请求分配到站点 $d$ 的速率 | 连续非负，请求/s |
| $P^{\mathrm{grid}}_{dt}$ | 各站点取电功率 | 连续非负，MW |

每个副本占用一个算力块；启动期也占用一个块。因此算力块启停与副本启停合并建模，不再另建一套硬件开关变量。公共电网和 UC 变量同时参与优化。

### 4.3 启动延迟与最小在线时间

副本状态递推为

$$
n_{dmt}=n_{dm,t-1}+b_{dm,t-1}^{\mathrm{boot}}-q_{dmt}^{\mathrm{off}}
\qquad \forall d,m,t.
\tag{I2}
$$

初始 $b_{dm,-1}^{\mathrm{boot}}=0$，$n_{dm,-1}=n_{dm}^{\mathrm{init}}$，初始副本矩阵为

$$
[n_{dm}^{\mathrm{init}}]=
\begin{bmatrix}
3&4&4&4&4&4\\
4&4&4&4&4&4\\
4&4&5&5&4&4
\end{bmatrix}.
$$

设副本启动后至少在线 $H=4$ 个时段，则

$$
n_{dmt}\ge\sum_{k=\max(0,t-H)}^{t-1}b_{dmk}^{\mathrm{boot}},
\qquad
b_{dmt}^{\mathrm{boot}}=0\quad\text{若 }t+H\ge T.
\tag{I3}
$$

在 $t$ 启动的副本于 $t+1$ 可用，至少覆盖 $t+1,\ldots,t+4$；因此最后一个允许启动的时段为 91。初始副本已满足最小在线时间，可以从首时段关闭。当前模型未增加最小离线时间或独立的启动—关闭互斥条件。

### 4.4 当期需求、服务能力和时延

所有请求必须在当期分配并服务：

$$
\sum_{d\in\mathcal D}y_{rmdt}=\lambda_{rmt}
\qquad \forall r,m,t.
\tag{I4}
$$

只有已上线的副本可以处理请求：

$$
\sum_r y_{rmdt}\le\mu_m n_{dmt}
\qquad \forall d,m,t.
\tag{I5}
$$

根据固定时延参数预先排除不满足服务要求的路由：

$$
y_{rmdt}=0\quad\text{若 }\ell_{rd}^{\mathrm{net}}+\ell_m^{\mathrm{proc}}>L_m^{\mathrm{SLA}}.
\tag{I6}
$$

模型允许将一个区域的同类请求按速率拆分到多个站点，但没有跨时段请求积压变量，也不允许把实时请求推迟到下一时段。

### 4.5 算力、内存和通信容量

对所有 $d,t$：

$$
\sum_m(n_{dmt}+b_{dmt}^{\mathrm{boot}})\le48,\qquad
\sum_mM_m(n_{dmt}+b_{dmt}^{\mathrm{boot}})\le3200.
\tag{I7}
$$

对所有 $r,d,t$ 和 $d,t$，分别限制链路与站点总流量：

$$
\sum_m\frac{b_m}{1000}y_{rmdt}\le50,\qquad
\sum_{r,m}\frac{b_m}{1000}y_{rmdt}\le150.
\tag{I8}
$$

$b_m$ 的单位是 Mbit/请求，$y$ 为请求/s，除以 1000 后单位为 Gbps。

### 4.6 推理服务的用电模型

$$
\begin{aligned}
P^{\mathrm{grid}}_{dt}
&=\gamma_d\left[8+\sum_m\left(
e_m^{\mathrm{idle}}n_{dmt}+2b_{dmt}^{\mathrm{boot}}
+\frac{e_m^{\mathrm{dyn}}}{\mu_m}\sum_r y_{rmdt}
\right)\right],\\
0&\le P^{\mathrm{grid}}_{dt}\le200.
\end{aligned}
\tag{I9}
$$

在线副本消耗空载功率，动态功率按所服务请求量增加，正在启动的副本消耗启动功率。PUE 将上述 IT 功率换算为站点总取电。

### 4.7 预防性线路 N-1 安全约束

事故集合 $\mathcal C$ 包括删除后仍保持全网连通的全部单支路退出，共 35 个。其余 11 个造成孤岛的退出和发电机退出不在本例事故集合内。对应输入支路 `id` 为

```text
0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18,
20, 21, 22, 23, 24, 25, 27, 28, 29, 30, 34, 35, 37, 39, 41, 42, 43, 44
```

预防性调度要求每个事故使用与基态相同的 $p_{gt}$、$P^{\mathrm{grid}}_{dt}$，也使用相同的业务配置与请求路由。事故发生后没有即时迁移请求或重新调整发电出力的决策。

其物理含义可写为：对每个 $c\in\mathcal C$，存在事故相角 $\theta^c$ 和事故潮流 $f^c$，满足

$$
\begin{aligned}
f^c_{\ell t}&=\beta_\ell(\theta^c_{i(\ell),t}-\theta^c_{j(\ell),t}),&&\ell\ne c,\\
f^c_{ct}&=0,\qquad\theta^c_{31,t}=0,\\
\sum_{g\in\mathcal G_b}p_{gt}-a_tP_b^D-\sum_{d\in\mathcal D_b}P^{\mathrm{grid}}_{dt}
&=\sum_{\ell\ne c}A_{\ell b}f^c_{\ell t},&&\forall b,t,\\
-F_\ell\le f^c_{\ell t}&\le F_\ell,&&\ell\ne c,\\
\underline\delta_\ell\le\theta^c_{i(\ell),t}-\theta^c_{j(\ell),t}&\le\overline\delta_\ell,&&\ell\ne c.
\end{aligned}
\tag{I10}
$$

实际实现用线路退出分布因子（LODF）消去 $\theta^c,f^c$，不额外建立事故潮流变量。令

$$
B=A^{\mathsf T}\operatorname{diag}(\beta)A,\qquad
H=\operatorname{diag}(\beta)A\widetilde B^{-1},\qquad
h_{\ell c}=H_{\ell,i(c)}-H_{\ell,j(c)}.
\tag{I11}
$$

$\widetilde B^{-1}$ 表示移除 31 号参考母线的行列、对剩余矩阵求逆，再在参考行列补零得到的矩阵。对非孤岛事故，$1-h_{cc}\ne0$，定义

$$
L_{\ell c}=\begin{cases}\dfrac{h_{\ell c}}{1-h_{cc}},&\ell\ne c,\\-1,&\ell=c,\end{cases}
\qquad f^c_{\ell t}=f_{\ell t}+L_{\ell c}f_{ct}.
\tag{I12}
$$

由于当前网架 $\phi_\ell=0$ 且 $\beta_\ell>0$，事故后的功率和相角差限制可合并为如下线性不等式：

$$
\max(-F_\ell,\beta_\ell\underline\delta_\ell)
\le f_{\ell t}+L_{\ell c}f_{ct}
\le\min(F_\ell,\beta_\ell\overline\delta_\ell)
\quad \forall c\in\mathcal C,\ \ell\ne c,\ t.
\tag{I13}
$$

上述实现与 (I10) 对本固定网架等价，共加入 $35\times45\times96\times2=302{,}400$ 条事故不等式。独立校验器对退出后的拓扑重新建立网络方程，复算事故潮流及相角，不直接复用模型的 LODF 校验路径。

### 4.8 目标函数、完整问题

每次副本启动支付 18 美元的算力启动成本和 12 美元的模型部署成本：

$$
C^{\mathrm{deploy}}=(18+12)\sum_{d,m,t}b_{dmt}^{\mathrm{boot}},\qquad
C^{\mathrm{comm}}=\frac{3600\Delta t}{10^6}\sum_{r,m,d,t}c_{rd}^{\mathrm{route}}y_{rmdt}.
\tag{I14}
$$

完整模型为

$$
\begin{aligned}
\min\quad &C^{\mathrm{UC}}+C^{\mathrm E}(p)+C^{\mathrm{deploy}}+C^{\mathrm{comm}},\\
\mathrm{s.t.}\quad &\text{公共网络约束、公共 UC/出力约束，}\ a_{\max}=0.68,\\
&\text{副本、服务、资源与用电约束 (I2)～(I9)，变量域见第 4.2 节，}\\
&\text{全部 35 个事故的线性安全约束 (I13)。}
\end{aligned}
\tag{I15}
$$

## 5. 案例三：风光与推理需求不确定性下的日前—追补调度

### 5.1 场景、站点与信息结构

设置 $\Omega=\{0,\ldots,19\}$ 共 20 个场景，概率 $\pi_\omega=1/20$。每个场景给定全天的风光可用功率 $\widehat w_{rt}^{\omega}$ 和推理所需忙碌算力块数 $I_{dt}^{\omega}$。本例的推理需求已聚合为站点算力需求，不含案例二的六模型、六区域请求路由子模型。

均值预测轨迹定义为

$$
\widehat w_{rt}^{\mathrm{nom}}=\sum_{\omega\in\Omega}\pi_\omega\widehat w_{rt}^{\omega},\qquad
I_{dt}^{\mathrm{nom}}=\sum_{\omega\in\Omega}\pi_\omega I_{dt}^{\omega}.
\tag{S1}
$$

模型同时包含名义轨迹和 20 条场景轨迹，记 $\mathcal S=\{\mathrm{nom}\}\cup\Omega$。名义轨迹用于保证出力基准和平均预测下的业务、电网可行，并计算备用需求；它不是第 21 个等概率场景，不计入期望运行成本。

采用两阶段信息假设：日前决定共享计划，之后追补阶段已知所实现场景的**完整 24 小时轨迹**。因此场景内储能、训练和再调度可以利用该场景之后时段的信息；这不是逐时揭示信息的多阶段在线策略。

| 参数 | 当前值 |
|---|---|
| 站点 $d=0,1,2$ 的接入母线 | 4、16、27 |
| 每站算力块上限、初始可用块数 | 48 块、32 块 |
| 每站设施功率和净取电功率上限 | 均为 200 MW |
| PUE、固定 IT 功率 | 1.25、8 MW |
| 每个可用块空载功率、每个忙碌块动态功率 | 1 MW/块、2 MW/块 |
| 每站电池功率、能量上限 | 40 MW、100 MWh |
| 初始与期末电量 | 均为 80 MWh |
| 充电、放电效率 | $\eta^{\mathrm{ch}}=\eta^{\mathrm{dis}}=0.95$ |
| UPS 支持时长、关键推理比例 | $\tau^{\mathrm{UPS}}=0.25$ h、$\kappa=0.25$ |
| 新增风电、光伏 | 母线 21 的 350 MW 风电；母线 26 的 250 MW 光伏 |
| 上下备用下限比例、响应时间 | $\rho=0.05$、$\tau^{\mathrm{res}}=0.25$ h |
| CVaR 置信水平、风险权重 | $\alpha=0.90$、$\lambda^{\mathrm{risk}}=0.20$ |

### 5.2 日前变量与场景变量

日前变量合记为

$$
X=\{u_{gt},v_{gt},z_{gt},p^0_{gt},R^\uparrow_{gt},R^\downarrow_{gt},K_{dt},V_{dt}\}.
$$

| 日前变量 | 含义 | 类型/单位 |
|---|---|---|
| $u,v,z$ | 共享机组启停状态 | 二元 |
| $p^0_{gt}$ | 出力基准，等于名义轨迹出力 $p_{gt}^{\mathrm{nom}}$ | 连续非负，MW |
| $R^\uparrow_{gt},R^\downarrow_{gt}$ | 上调、下调备用 | 连续非负，MW |
| $K_{dt}$ | 已安排可用的算力块数 | 整数，$0\le K_{dt}\le48$ |
| $V_{dt}$ | 算力块启动计数 | 整数，$0\le V_{dt}\le48$ |

对每条 $s\in\mathcal S$ 轨迹建立以下变量；其中名义轨迹变量为构建基准计划的辅助变量，$s=\omega$ 时为该场景的追补变量。

| 轨迹变量 | 含义 | 类型/单位 |
|---|---|---|
| $p^s,\theta^s,f^s$ | 发电出力、相角、潮流 | 连续，MW/rad |
| $x^s_{jt}$ | 训练批次 $j$ 在时段 $t$ 的执行速率 | 连续非负，算力块 |
| $P^{\mathrm{fac},s}_{dt},P^{\mathrm{grid},s}_{dt}$ | 设施功率、电网连接点净取电 | 连续非负，MW |
| $P^{\mathrm{ch},s}_{dt},P^{\mathrm{dis},s}_{dt}$ | 电池充电、放电功率 | 连续非负，MW |
| $\chi^s_{dt}$ | 充放电方向，1 允许充电，0 允许放电 | 二元 |
| $E^s_{dt}$ | 时段边界的电池电量 | 连续非负，MWh |
| $w^s_{rt}$ | 实际消纳风光功率 | 连续非负，MW |

另有 CVaR 辅助变量 $\eta\ge0$、$\xi_\omega\ge0$，单位为美元。$\eta$ 是风险阈值变量，与固定的充放电效率参数 $\eta^{\mathrm{ch}},\eta^{\mathrm{dis}}$ 区分。

### 5.3 日前算力配置与机组备用

给定 $K_{d,-1}=32$，算力启动满足

$$
V_{dt}\ge K_{dt}-K_{d,t-1},\qquad
K_{dt},V_{dt}\in\mathbb Z,\quad0\le K_{dt},V_{dt}\le48.
\tag{S2}
$$

$V$ 在目标中具有正的启动成本，因此最优解取最小必要启动数。本例算力容量允许当期生效，未采用案例二的副本启动延迟和最小在线时间。

日前备用必须留在出力上下界以内，并可在 15 分钟内交付：

$$
\begin{aligned}
p^0_{gt}+R^\uparrow_{gt}&\le\overline P_gu_{gt},\\
p^0_{gt}-R^\downarrow_{gt}&\ge\underline P_gu_{gt},\\
0\le R^\uparrow_{gt}&\le R_g\tau^{\mathrm{res}}u_{gt},\\
0\le R^\downarrow_{gt}&\le R_g\tau^{\mathrm{res}}u_{gt}.
\end{aligned}
\tag{S3}
$$

各场景再调度必须落在已购买备用的范围内：

$$
p^0_{gt}-R^\downarrow_{gt}\le p^\omega_{gt}\le p^0_{gt}+R^\uparrow_{gt}
\qquad \forall g,t,\omega\in\Omega.
\tag{S4}
$$

每条轨迹的 $p^s$ 还须满足公共出力约束 (G6) 和爬坡约束 (G10)，其启停状态均为同一组 $u,v,z$。

名义总需求定义为基础负荷加 AIDC 净取电：

$$
D_t^{\mathrm{nom}}=a_t\sum_bP_b^D+\sum_dP^{\mathrm{grid},\mathrm{nom}}_{dt}.
$$

两个方向的系统备用下限分别为

$$
\sum_gR^\uparrow_{gt}\ge0.05D_t^{\mathrm{nom}},\qquad
\sum_gR^\downarrow_{gt}\ge0.05D_t^{\mathrm{nom}}.
\tag{S5}
$$

该需求口径含储能充放电对 AIDC 净取电的影响，不扣除风光发电。名义取电是模型变量，因此备用下限与名义业务及电池计划联动。

### 5.4 训练批次完成和推理服务

共有 18 个训练批次，每站 6 个，窗口依次为 $[0,16),[16,32),\ldots,[80,96)$，每个窗口 4 小时。批次 $j$ 的站点为 $d(j)$，到达、截止、工作量分别为 $r_j,d_j,W_j$。令 $\mathcal J_d$ 为站点 $d$ 的批次集合。

对全部 $s\in\mathcal S$，训练只能在窗口内执行，并完成精确工作量：

$$
x^s_{jt}=0\quad\text{若 }t\notin[r_j,d_j),\qquad
\Delta t\sum_{t=r_j}^{d_j-1}x^s_{jt}=W_j,\qquad x^s_{jt}\ge0.
\tag{S6}
$$

推理需求与训练共用已安排的算力容量：

$$
I^s_{dt}+\sum_{j\in\mathcal J_d}x^s_{jt}\le K_{dt}
\qquad \forall d,t,s\in\mathcal S.
\tag{S7}
$$

$I^s_{dt}$ 是必须当期完成的固定需求，没有跨时段延期变量。训练 $x$ 可分割、可暂停并在窗口内调整速率，与案例一固定并行规模、连续运行的作业模型不同。

为说明累计积压含义，可从解中定义剩余工作量

$$
B^s_{j,t}=W_j-\Delta t\sum_{k=r_j}^{t-1}x^s_{jk},\quad r_j\le t\le d_j;
\qquad B^s_{j,r_j}=W_j,\quad B^s_{j,d_j}=0.
\tag{S8}
$$

由于 $x\ge0$ 且总执行量为 $W_j$，$B^s_{j,t}\ge0$ 自动成立。$B$ 是解释和复算用的派生量，当前实现没有为其另建决策变量。

### 5.5 设施功率与连接点功率

对全部 $d,t,s\in\mathcal S$：

$$
P^{\mathrm{fac},s}_{dt}=1.25\left[8+K_{dt}
+2\left(I^s_{dt}+\sum_{j\in\mathcal J_d}x^s_{jt}\right)\right],
\qquad 0\le P^{\mathrm{fac},s}_{dt}\le200.
\tag{S9}
$$

$$
P^{\mathrm{grid},s}_{dt}=P^{\mathrm{fac},s}_{dt}
+P^{\mathrm{ch},s}_{dt}-P^{\mathrm{dis},s}_{dt},\qquad
0\le P^{\mathrm{grid},s}_{dt}\le200.
\tag{S10}
$$

设施功率包含已安排块的空载功率和实际忙碌块的动态功率；充放电在连接点功率中计入。两种功率均有独立的 200 MW 上限，站点不向电网反送电。

### 5.6 电池互斥、能量递推和期末恢复

$$
0\le P^{\mathrm{ch},s}_{dt}\le40\chi^s_{dt},\qquad
0\le P^{\mathrm{dis},s}_{dt}\le40(1-\chi^s_{dt}),\qquad
\chi^s_{dt}\in\{0,1\}.
\tag{S11}
$$

$$
E^s_{d,t+1}=E^s_{dt}+\Delta t\left(0.95P^{\mathrm{ch},s}_{dt}
-\frac{P^{\mathrm{dis},s}_{dt}}{0.95}\right).
\tag{S12}
$$

$$
0\le E^s_{dt}\le100\quad(t=0,\ldots,T),\qquad
E^s_{d,0}=E^s_{d,T}=80.
\tag{S13}
$$

### 5.7 关键负荷的 15 分钟 UPS 要求

按照固定 IT 功率加 25% 关键推理业务计算保障功率：

$$
P^{\mathrm{crit},s}_{dt}=1.25\left[8+(1+2)\times0.25I^s_{dt}\right]
=1.25(8+0.75I^s_{dt}).
\tag{S14}
$$

要求电池功率足以承担关键负荷，且时段首尾电量均满足备用电量：

$$
P^{\mathrm{crit},s}_{dt}\le40,\qquad
E^s_{dt}\ge\frac{0.25}{0.95}P^{\mathrm{crit},s}_{dt},\qquad
E^s_{d,t+1}\ge\frac{0.25}{0.95}P^{\mathrm{crit},s}_{dt}.
\tag{S15}
$$

式中 $0.25$ 为小时，除以放电效率将输出电量折算为所需电池电量。正常调度仍须服务全部推理需求；25% 仅定义 UPS 关键部分。这里建模的是功率和备用电量条件，没有额外模拟停电轨迹或切换暂态。

### 5.8 风光消纳、网络与非预见性

每条轨迹的可用风光功率可被弃用，但不能超用：

$$
0\le w^s_{rt}\le\widehat w^s_{rt},\qquad
w^{\mathrm{curt},s}_{rt}=\widehat w^s_{rt}-w^s_{rt}\ge0.
\tag{S16}
$$

$w^{\mathrm{curt}}$ 是由可用量与实际消纳量之差计算的派生量。对每条 $s\in\mathcal S$，用 $p^s,w^s,P^{\mathrm{grid},s},\theta^s,f^s$ 施加公共网络约束 (G2)～(G4)，其中 $a_{\max}=0.85$。本例没有案例二的线路 N-1 约束。

所有场景共享同一份日前决策。若写成各场景拥有日前变量副本的形式，非预见性条件为

$$
X^\omega=X^{\omega'}\qquad\forall\omega,\omega'\in\Omega.
\tag{S17}
$$

当前实现直接建立一组 $X$，由各轨迹共同引用，从变量结构上满足 (S17)。场景追补变量之间不再加前缀历史相同的约束，这与完整轨迹揭示的两阶段假设一致。

### 5.9 日前成本、场景成本与 CVaR

日前成本包括共享机组成本、备用购买成本和算力块启动成本：

$$
C^0(X)=C^{\mathrm{UC}}+\Delta t\sum_{g,t}\left(
c^{\uparrow}R^\uparrow_{gt}+c^{\downarrow}R^\downarrow_{gt}\right)
+c^{\mathrm{block}}\sum_{d,t}V_{dt},
\tag{S18}
$$

其中 $c^{\uparrow}=1$、$c^{\downarrow}=0.3$ 美元/(MW·h)，$c^{\mathrm{block}}=25$ 美元/块次。

场景 $\omega$ 的运行成本为

$$
\begin{aligned}
Q_\omega={}&\Delta t\sum_{g,t}c_gp^\omega_{gt}\\
&+\Delta t\,c^{\mathrm{bat}}\sum_{d,t}
\left(P^{\mathrm{ch},\omega}_{dt}+P^{\mathrm{dis},\omega}_{dt}\right)\\
&+\Delta t\,c^{\mathrm{curt}}\sum_{r,t}
\left(\widehat w^\omega_{rt}-w^\omega_{rt}\right),
\end{aligned}
\tag{S19}
$$

其中 $c^{\mathrm{bat}}=2$ 美元/MWh，按充放电吞吐电量计费；$c^{\mathrm{curt}}=1$ 美元/MWh。$Q_\omega$ 不含已由日前支付的机组启停、空载、备用和算力启动成本。名义出力 $p^0$ 不额外计一遍发电能量成本。

对场景运行成本使用 CVaR：

$$
\operatorname{CVaR}_{\alpha}(Q)
=\min_{\eta\ge0,\,\xi\ge0}
\left\{\eta+\frac{1}{1-\alpha}\sum_{\omega\in\Omega}\pi_\omega\xi_\omega:
\xi_\omega\ge Q_\omega-\eta\right\}.
\tag{S20}
$$

当前所有 $Q_\omega\ge0$，因此实现中对 $\eta$ 施加非负下界不改变最优 CVaR。$\alpha=0.9$、20 个等概率场景时，目标中的 CVaR 表达式为

$$
\eta+\frac{1}{1-0.9}\sum_{\omega=0}^{19}\frac{1}{20}\xi_\omega
=\eta+0.5\sum_{\omega=0}^{19}\xi_\omega.
\tag{S21}
$$

该指标控制场景运行成本最高的尾部，风险项作用于 $Q_\omega$，不再对确定的日前成本 $C^0$ 加收一次风险权重。

### 5.10 完整两阶段随机 MILP

$$
\begin{aligned}
\min_{X,\,\{Y^s\}_{s\in\mathcal S},\,\eta,\,\xi}\quad
&C^0(X)+\sum_{\omega\in\Omega}\pi_\omega Q_\omega
+0.2\left(\eta+\frac{1}{1-0.9}\sum_{\omega\in\Omega}\pi_\omega\xi_\omega\right),\\
\mathrm{s.t.}\quad
&\text{一组共享 UC 状态约束 (G5)、(G7)～(G9)，}\\
&\text{每条 }s\in\mathcal S\text{ 的出力/爬坡约束 (G6)、(G10) 及网络约束 (G2)～(G4)，}\\
&p^{\mathrm{nom}}=p^0,\quad a_{\max}=0.85,\\
&\text{日前算力与备用约束 (S2)～(S5)，}\\
&\text{每条 }s\in\mathcal S\text{ 的训练/服务约束 (S6)、(S7)，}\\
&\text{每条 }s\in\mathcal S\text{ 的设施、储能、UPS 和风光约束 (S9)～(S16)，}\\
&\xi_\omega\ge Q_\omega-\eta,\quad\xi_\omega\ge0\quad\forall\omega\in\Omega,\quad\eta\ge0.
\end{aligned}
\tag{S22}
$$

$Y^s$ 代表第 5.2 节的轨迹变量，变量域按该节及具体约束执行。共享 $X$ 体现非预见性；(S8) 是派生积压量，无须额外加入；$C^0,Q_\omega$ 分别按 (S18)、(S19) 计算。
