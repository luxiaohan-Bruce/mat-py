"""Summarize all calibration trials and repeated timings of the current input."""
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
PACK=HERE.parent
sys.path.insert(0,str(PACK))
from common.data import load_case, data_hash, write_json
from common.verify import revalidate_saved


def report():
    case=PACK/'case001_training_uc'
    d,cfg=load_case(case)
    current=json.loads((case/'results/python_result.json').read_text())
    original=json.loads((HERE/'original_160_jobs/results/python_result.json').read_text())
    checksum=data_hash(d)
    certificate=revalidate_saved(case)
    if not certificate['passed']:raise ValueError('Current formal result did not pass independent verification')
    trials=[];samples=[]
    for path in sorted(HERE.glob('*/summary.json'),key=lambda p:p.stat().st_mtime):
        s=json.loads(path.read_text())
        for i,r in enumerate(s['runs']):
            row=dict(label=s['label'],jobs=s['n_jobs'],wait_cost_scale=s.get('wait_cost_scale',1.),
                window_margin_slots=s['window_margin_slots'],input_sha256=s['input_sha256'],
                **r,settings=s['settings'],result=str((path.parent/f'run_{i+1}/python_result.json').relative_to(PACK)))
            trials.append(row)
            if row['input_sha256']==checksum:
                verified=revalidate_saved(path.parent,path.parent/f'run_{i+1}/python_result.json')
                if not verified['passed']:raise ValueError(f"Trial validation failed: {row['label']}")
                samples.append(dict(label=row['label'],runtime=row['runtime'],status=row['status'],
                    mip_gap=row['mip_gap'],objective=row['obj'],independently_passed=True,result=row['result']))
    block=current['aidc39']
    samples.append(dict(label='正式入口 solve.py',runtime=block['runtime'],status=block['status'],
        mip_gap=block['mip_gap'],objective=block['obj'],independently_passed=True,
        result='case001_training_uc/results/python_result.json'))
    times=[s['runtime'] for s in samples]
    band=[80.,120.]
    out=dict(target_seconds=100.,calibration_band_seconds=band,current_input_sha256=checksum,
        original_runtime=original['aidc39']['runtime'],formal_runtime=block['runtime'],
        n_jobs=len(d['jobs']),flow_time_cost_range=[min(j['wait_cost_per_hour'] for j in d['jobs']),max(j['wait_cost_per_hour'] for j in d['jobs'])],
        solver_settings={k:cfg[k] for k in ['seed','threads','time_limit','mip_gap']},
        samples=samples,median_seconds=statistics.median(times),mean_seconds=statistics.mean(times),
        minimum_seconds=min(times),maximum_seconds=max(times),trials=trials,
        accepted=len(samples)>=3 and band[0]<=statistics.median(times)<=band[1]
                 and all(s['status']=='OPTIMAL' and s['independently_passed'] and s['mip_gap']<=.001+1e-9 for s in samples))
    write_json(HERE/'calibration_results.json',out)
    lines=['# 训练案例：约 100 秒难度标定', '',
        '用户目标为将约 10 秒的训练与机组组合案例提高到约 100 秒。本次采用 80～120 秒作为“约 100 秒”的标定区间，以相同输入重复运行的中位数判断。', '',
        f"当前版本：**{len(d['jobs'])} 个作业，完成时间成本系数为原版的 4.5 倍**；保留 39 节点、46 支路、10 电源、96 时段、64 算力块、3 档位和 300 MW 接入上限。所有优化均用 Gurobi 13.0.2、Apple M5、Seed=1、Threads=4、TimeLimit=600 秒、MIPGap=0.1%，顺序执行。", '',
        '## 原版与当前版', '', '| 项目 | 原版 | 当前版 |', '|---|---:|---:|',
        '| 作业数 | 160 | 240 |',
        '| 总训练工作量，标准块小时 | 1159.0 | 1368.5 |',
        '| 最快档工作量 / 全天可用算力 | 75.5% | 89.1% |',
        '| 完成时间成本，美元/小时 | 3～12 | 13.5～54 |',
        '| 合法开始时间与档位组合 | 7241 | 11095 |',
        f"| 全部变量 | {original['aidc39']['n_variables']} | {block['n_variables']} |",
        f"| 二元变量 | {original['aidc39']['n_binary']} | {block['n_binary']} |",
        f"| 线性约束行 | {original['aidc39']['n_constraints']} | {block['n_constraints']} |",
        f"| 正式求解时间，秒 | {original['aidc39']['runtime']:.3f} | {block['runtime']:.3f} |", '',
        '更多任务提高连续区间内的算力竞争；更高的流转时间成本强化尽早完成与低功率档位之间的取舍。时间窗口扩展规则、计算速度、功率和 UC 参数保留原值。小规模正确性测试仍使用短时域参数。', '',
        '## 相同最终输入的重复运行', '',
        '| 运行 | 时间，秒 | 最优间隙 | 独立验收 |', '|---|---:|---:|---|']
    for sample in samples:
        lines.append(f"| [{sample['label']}](../{sample['result']}) | {sample['runtime']:.3f} | {100*sample['mip_gap']:.5f}% | 通过 |")
    lines += ['', f"中位数 **{out['median_seconds']:.3f} 秒**，均值 **{out['mean_seconds']:.3f} 秒**，范围 **{out['minimum_seconds']:.3f}～{out['maximum_seconds']:.3f} 秒**。标定{'通过' if out['accepted'] else '未通过'}。所有结果以实际间隙条件正常结束。", '',
        '计时是求解器报告的 Runtime，构模与文件写入另计。目标 100 秒是数据选择标准；正式求解器的时间上限仍为 600 秒。不同机器、软件版本及系统负载会影响秒数。', '',
        '## 全部候选试验', '',
        '下列记录保留全部已完成的标定候选。MILP 的搜索复杂度对数据变化不单调，因此在选定输入后进行重复验证。', '',
        '| 候选 | 作业数 | 时间成本倍数 | 求解秒 | 间隙 | 独立验收 |', '|---|---:|---:|---:|---:|---|']
    for trial in trials:
        gap='—' if trial['mip_gap'] is None else f"{100*trial['mip_gap']:.5f}%"
        lines.append(f"| [{trial['label']}](../{trial['result']}) | {trial['jobs']} | {trial['wait_cost_scale']:g} | {trial['runtime']:.3f} | {gap} | {'通过' if trial['validation_passed'] else '失败'} |")
    lines += ['', '## 复现与文件', '',
        '正式案例默认已切换到选定难度。使用仓库统一入口：', '',
        '```bash', 'python3 solve.py DATACENTER/AIDC-39/case001_training_uc',
        'python3 DATACENTER/AIDC-39/case001_training_uc/solve.py --mode baseline',
        'python3 evaluate.py DATACENTER/AIDC-39/case001_training_uc', '```', '',
        '新建一个标定记录目录可复现相同工作负载的多次测量：', '',
        '```bash',
        'python3 DATACENTER/AIDC-39/calibration/calibrate_training.py --label fresh_240_cost4p5 --jobs 240 --wait-cost-scale 4.5 --repeats 3',
        'python3 DATACENTER/AIDC-39/calibration/report_calibration.py', '```', '',
        '标签目录已存在时程序拒绝覆盖，避免丢失旧计时。原版输入、主问题及对照完整结果位于 `original_160_jobs/`；所有候选保留独立输入、结果、日志和摘要。当前输入可由种子 101 的数据生成器完整重建。', '',
        '正式对照已在当前 240 个作业与相同成本参数下重新求解，比较见 [BENCHMARK.md](../BENCHMARK.md)。其他两个正式案例的输入与原有主问题/对照结果按 SHA-256 核对保持一致。']
    (HERE/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:out[k] for k in ['accepted','median_seconds','mean_seconds','minimum_seconds','maximum_seconds']},ensure_ascii=False))
    return out


if __name__=='__main__':raise SystemExit(0 if report()['accepted'] else 1)
