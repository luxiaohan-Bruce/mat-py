# mat-py

你自己的电力系统难优化实验仓库：用 **Matlab 基准（MATPOWER / MOST / PGLib）** 跑通，以后再迁 **Python**。

**当前阶段：** 自有脚本 + 笔记；第三方工具箱仅作本地依赖，不进 Git。

## 双主线

| 主线 | 问题 | 本地依赖 | 难度 |
|------|------|----------|------|
| **A** | AC-OPF | MATPOWER + PGLib-OPF | 非凸 NLP |
| **B** | UC / SCUC | MOST + Gurobi/CPLEX | 大规模 MILP |

## 目录

```text
mat-py/
  scripts/          # ★ 你改代码的地方
  notes/            # 公式、跑分记录
  refs/             # 文献与基准链接
  matlab/           # 本地依赖（gitignore，不提交）
    matpower/
    most/
    pglib-opf/
```

## 快速开始

```bash
# 1. 克隆第三方依赖（若还没有）
bash scripts/bootstrap_deps.sh

# 2. 初始化本仓库 Git（若尚未 init）
git status
```

MATLAB：

```matlab
cd('/Users/bruce/Documents/mat-py/scripts')
setup_paths
smoke_acopf
```

需要本机已安装 **MATLAB**；UC 建议配置 **Gurobi/CPLEX**。

## 改代码约定

- **只提交** `scripts/`、`notes/`、`refs/`、顶层文档。
- **不提交** `matlab/matpower` 等第三方树（体积大、有独立 license/版本）。
- 实验目标值记到 `notes/solver-baselines.md`。

## 推到 GitHub（账号连好后）

```bash
# 装 CLI 并登录（任选一次）
brew install gh && gh auth login

# 在 GitHub 建空仓库后：
git remote add origin git@github.com:你的用户名/mat-py.git
git push -u origin main
```

## 阶段计划

1. AC-OPF 冒烟与 PGLib 对标 → 记 `notes/`
2. MOST `ex1`→`ex6`→`ex7` UC/SCUC
3. （可选）SCOPF / 更大算例
4. （以后）Python 只移植选定模型 + 算例

## License

本仓库自有脚本按你后续声明的许可；MATPOWER/MOST 为 BSD 等，见各自 `LICENSE`。PGLib 再分发前请核对其许可证。
