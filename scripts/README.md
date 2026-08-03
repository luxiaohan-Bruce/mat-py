# scripts/ — 你自己的代码

这里才是 **mat-py 仓库里要改的主代码**。  
`matlab/matpower`、`matlab/most`、`matlab/pglib-opf` 是本地依赖（已被 `.gitignore`，不提交）。

## 第一次

```bash
# 若第三方目录不在，重新克隆：
bash scripts/bootstrap_deps.sh
```

## MATLAB 里

```matlab
cd('/Users/bruce/Documents/mat-py/scripts')  % 改成你的路径
setup_paths
smoke_acopf   % 需要本机已装 MATLAB + 能跑 MATPOWER
```

## 建议你改什么

| 文件/目录 | 用途 |
|-----------|------|
| `setup_paths.m` | 路径配置 |
| `smoke_acopf.m` | AC-OPF 冒烟 / 基准实验 |
| 新建 `smoke_uc.m` | MOST UC 实验（下一步） |
| 新建 `experiments/` | 正式算例、参数扫描 |
| 将来 `../python/` | Python 移植 |

改完后：

```bash
cd /Users/bruce/Documents/mat-py
git add scripts notes
git commit -m "Describe your change"
```
