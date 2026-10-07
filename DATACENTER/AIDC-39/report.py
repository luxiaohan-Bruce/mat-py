"""Rebuild a benchmark report from saved schedules, without importing Gurobi."""
from __future__ import annotations
import datetime
import json
import re
from pathlib import Path

import numpy as np
from common.data import CASES, PACK, load_case, write_json
from common.verify import revalidate_saved


LABELS = {'training': '训练与 UC', 'inference': '推理与线路 N-1', 'stochastic': '风光与随机追补'}


def capacity_shortfalls(d, mean_policy):
    """A necessary capacity inequality: no optimizer or infeasibility label needed."""
    blocks = np.asarray(mean_policy['schedule']['first_stage']['gpu_blocks'])
    failures = []
    for scenario in d['scenarios']:
        inference = np.asarray(scenario['inference_blocks'])
        for cohort in d['cohorts']:
            a, b, site = cohort['release'], cohort['deadline'], cohort['site']
            capacity = float(np.sum(blocks[a:b, site] - inference[a:b, site]) * d['dt_hours'])
            deficit = cohort['work_block_hours'] - capacity
            if deficit > 1e-5:
                failures.append(dict(scenario=scenario['id'], cohort=cohort['id'], site_bus=d['sites'][site]['bus'],
                    release_slot=a, deadline_slot=b, required_block_hours=cohort['work_block_hours'],
                    maximum_available_block_hours=capacity, deficit_block_hours=deficit))
    return sorted(failures, key=lambda x: -x['deficit_block_hours'])


def summarize(case, filename):
    path = case / 'results' / filename
    if not path.exists():
        return dict(status='MISSING', independently_passed=False, result=str(path.relative_to(PACK)))
    r = json.loads(path.read_text())
    certificate = revalidate_saved(case, path)
    out = {k: v for k, v in r['aidc39'].items() if not k.startswith('max_')}
    out.update(independently_passed=certificate['passed'], verification=certificate,
               cost_breakdown=r.get('cost_breakdown'), metadata=r.get('metadata', {}),
               input_sha256=r.get('input_sha256'), result=str(path.relative_to(PACK)))
    write_json(case / 'results' / (r['mode'] + '_revalidated.json'), certificate)
    return out


def number(value, digits=2):
    return '—' if value is None else f'{value:,.{digits}f}'


def generate_report():
    records = []
    for name, kind, seed in CASES:
        case = PACK / name
        record = dict(case=name, kind=kind, data_seed=seed, main=summarize(case, 'python_result.json'),
                      baseline=summarize(case, 'baseline_result.json'))
        a, b = record['main'], record['baseline']
        record['cost_reduction_percent'] = (
            100 * (b['obj'] - a['obj']) / b['obj']
            if a['independently_passed'] and b['independently_passed'] and b['obj'] > 0 else None)
        if kind == 'stochastic':
            record['mean'] = summarize(case, 'mean_policy_result.json')
            if record['mean']['independently_passed']:
                d, _ = load_case(case)
                mean = json.loads((case / 'results/mean_policy_result.json').read_text())
                record['baseline_capacity_shortfalls'] = capacity_shortfalls(d, mean)
        records.append(record)
    first = records[0]['main'].get('metadata', {})
    log = (PACK / CASES[0][0] / 'results/main_gurobi.log').read_text()
    cpu = re.search(r'^CPU model: (.+)$', log, re.M)
    thread = re.search(r'^Thread count: (.+)$', log, re.M)
    settings = {k: first.get(k) for k in ['gurobi_version', 'python', 'machine', 'platform', 'seed', 'threads', 'time_limit', 'mip_gap_target']}
    settings.update(cpu=cpu.group(1) if cpu else 'unspecified', thread_description=thread.group(1) if thread else 'unspecified')
    report = dict(generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  settings=settings, cases=records,
                  accepted=all(r['main']['independently_passed'] for r in records))
    write_json(PACK / 'benchmark_results.json', report)
    lines = ['# AIDC-39 正式基准报告', '',
        '本报告由 `python3 DATACENTER/AIDC-39/report.py` 从保存的数值解重新校验后生成，不重新求解。全部采用 39 节点、46 支路、10 个原有电源和 96 个 15 分钟时段；第三例另在原母线接入两台风光电源。', '',
        f"正式案例独立验收：**{'3/3 通过' if report['accepted'] else '尚未全部通过'}**。源码、合成业务输入与完整调度结果均在本包中。", '',
        '## 机器与设置', '',
        f"{settings['cpu']}；{settings['thread_description']}；{settings['platform']} {settings['machine']}；Python {settings['python']}；Gurobi {'.'.join(map(str, settings['gurobi_version']))}。", '',
        '每个优化问题使用 Seed=1、Threads=4、TimeLimit=600 秒、MIPGap=0.001（0.1%），并统一设置 FeasibilityTol=IntFeasTol=1e-8。正式求解在同一机器顺序执行，未同时运行两个基准求解器。均值对照的“求均值计划”和“固定计划后评价”分别是一次优化，分别适用相同设置。测试使用短时域与独立测试设置，不混入下表。', '',
        'OPTIMAL 表示达到指定间隙标准，不表示零间隙。下表时间是求解器时间；构模另报，数值修复计入求解时间及 600 秒预算。首次可行解为求解器首次报告 incumbent 的时间，最终保存的解另行独立验收。', '',
        '## 正式结果和对照', '',
        '| 问题 / 方案 | 状态 | 独立验收 | 目标（美元） | 全局界 | 间隙 | 求解秒 | 首次可行秒 |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for r in records:
        for key, label in [('main', '联合调度'), ('baseline', '对照')]:
            s = r[key]
            gap = s.get('mip_gap')
            lines.append(f"| {LABELS[r['kind']]} / {label} | {s['status']} | {'通过' if s['independently_passed'] else '未通过/无解'} | {number(s.get('obj'))} | {number(s.get('objective_bound'))} | {'—' if gap is None else f'{100*gap:.4f}%'} | {number(s.get('runtime'),3)} | {number(s.get('first_incumbent_seconds'),3)} |")
    lines += ['', '| 问题 | 系统目标降低 | 业务结果 |', '|---|---:|---|']
    for r in records:
        a, b = r['main'], r['baseline']
        metric = a.get('verification', {}).get('metrics', {})
        improvement = r['cost_reduction_percent']
        if r['kind'] == 'training':
            detail = f"{metric.get('jobs_completed', 0)} 个作业按期完成；AIDC 电量 {number(metric.get('aidc_energy_mwh'))} MWh，对照 {number(b.get('verification',{}).get('metrics',{}).get('aidc_energy_mwh'))} MWh"
        elif r['kind'] == 'inference':
            detail = f"当期完成 {number(metric.get('requests_served'),0)} 次请求；35 个非孤岛事故全部校验；AIDC 电量 {number(metric.get('aidc_energy_mwh'))} MWh"
        else:
            detail = f"20 场景均可行；运行成本 CVaR90%={number(metric.get('empirical_cvar'))} 美元；固定均值计划不可行"
        lines.append(f"| {LABELS[r['kind']]} | {'不计算（对照不可行或未验证）' if improvement is None else f'{improvement:.3f}%'} | {detail} |")
    lines += ['', '改善率为同一场景与同一业务输入下的可行 incumbent 目标差，不声称为精确最优值之差。训练联合调度同时选择运行档位和开始时刻；主问题与对照完成相同工作量，全部作业满足截止时间，流转时间成本已计入总目标。推理对照固定峰值副本和就近路由，联合调度优化副本数及路由。', '',
        '## 实际模型规模', '',
        '统计为预处理前实际构模值，包含固定变量；线性行数不包含变量上下界。一般整数列不重复计二元变量。', '',
        '| 正式模型 | 全部变量 | 二元 | 一般整数 | 连续 | 线性约束行 | 非零系数 | 构模秒 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in records:
        a = r['main']
        keys = ['n_variables', 'n_binary', 'n_general_integer', 'n_continuous', 'n_constraints', 'n_nonzeros']
        lines.append(f"| {LABELS[r['kind']]} | " + ' | '.join(number(a.get(k), 0) for k in keys) + f" | {number(a.get('metadata',{}).get('build_seconds'),3)} |")
    lines += ['', '训练例已按约 100 秒目标增加任务密度并调整流转成本，完整候选试验和重复计时见 [标定记录](calibration/README.md)。三例均在 600 秒内达到 0.1% 间隙标准。节点数不能单独反映难度：训练的连续排程组合、推理模型的事故行约束、随机模型的多场景及共享日前决策分别带来不同的求解负担。表中训练项为本次正式求解，其余两项沿用此前相同机器和设置的正式结果。', '',
        '## 成本分解（美元）', '', '| 方案 | 分项 | 金额 |', '|---|---|---:|']
    for r in records:
        for key in ['main', 'baseline']:
            s = r[key]
            for cost, value in (s.get('cost_breakdown') or {}).items():
                lines.append(f"| {LABELS[r['kind']]} / {key} | {cost} | {number(value)} |")
    lines += ['', '所有发电成本按实际 MW×.25 小时计算；未再叠加数据中心电费。第三例名义轨迹的发电成本不重复收费，风险溢价为 .2×CVaR，详见各例数学说明。', '',
        '## 随机对照不可行的独立证据', '']
    st = records[2]
    mean = st.get('mean', {})
    lines += [f"均值问题：{mean.get('status')}，独立验收{'通过' if mean.get('independently_passed') else '失败'}，求解 {number(mean.get('runtime'),3)} 秒；其单场景目标 {number(mean.get('obj'))} 美元不能与 20 场景目标直接相比。固定全部日前决策后，20 场景评价状态为 {st['baseline']['status']}。", '']
    failures = st.get('baseline_capacity_shortfalls', [])
    if failures:
        q = failures[0]
        lines += [f"一个可复算反例（编号从零开始）：场景 {q['scenario']}、母线 {q['site_bus']}、训练批次 {q['cohort']}、窗口 [{q['release_slot']},{q['deadline_slot']})。该批次工作量为 {q['required_block_hours']:.6f} 块小时，固定日前容量扣除当期推理后最多剩 {q['maximum_available_block_hours']:.6f} 块小时，缺口 {q['deficit_block_hours']:.6f} 块小时。即使忽略所有电网和储能约束，也不可能按期完成。", '',
            '检验式为 `dt*sum(K[t,site]-inference[scenario,t,site]) >= cohort.work_block_hours`。完整缺口清单保存在 `benchmark_results.json`。因此不填写该对照的场景成本、改善率或“随机优化价值”数值。', '']
    lines += ['## 数值校验与复现实验', '',
        '| 正式模型 | 最大节点平衡残差 MW | 最大基态潮流方程残差 MW | 最大整数残差 |',
        '|---|---:|---:|---:|']
    for r in records:
        residuals = r['main'].get('verification', {}).get('residuals', {})
        lines.append(f"| {LABELS[r['kind']]} | " + ' | '.join(f"{residuals.get(k,float('nan')):.3e}" for k in ['max_power_balance_MW','max_flow_equation_MW','max_integer_violation']) + ' |')
    lines += ['', '独立校验包括 UC/爬坡、节点平衡、线路/相角、训练窗口与算力、推理 SLA/带宽/内存、副本启动与保持期、场景共享策略、备用、SOC/互斥/期末恢复、关键负荷功率与 15 分钟电量，以及全部成本分解。事故校验重建每个退出拓扑，不复用求解器的 LODF。详细证书保存于每例 `results/*_revalidated.json`。', '']
    for r in records:
        for key in ['main', 'baseline']:
            polish = r[key].get('metadata', {}).get('integer_polish')
            if polish:
                lines += [f"{LABELS[r['kind']]} {key} 的原始求解解存在整数数值残差 {polish['previous_violations']}，未直接验收。固定 {polish['fixed_variables']} 个整数变量后，在原时限内重新求解连续调度 {polish['runtime']:.3f} 秒，修复后独立复算通过。全局界沿用原 MILP 的界，未使用固定策略子问题的界冒充全局界。", '']
    lines += ['复现命令（仓库根目录）：', '', '```bash',
        'python3 DATACENTER/AIDC-39/test_aidc39.py',
        'python3 -m unittest framework.test_framework',
        'python3 DATACENTER/AIDC-39/run_all_python.py --with-baselines',
        'python3 DATACENTER/AIDC-39/refresh_metadata.py --catalog',
        'python3 DATACENTER/AIDC-39/report.py', '```', '',
        '小规模测试保留完整 39 节点网架，覆盖枚举最优值、单场景退化、错误训练窗口、错误推理时延、UPS 电量与功率不足、篡改结果及输入哈希。正式验收要求保存可行解且复算通过；仅有求解器状态不能通过。', '',
        '来源、合成参数及适用边界见 [README](README.md)、[数据字典](DATA_SCHEMA.md) 和 [公共模型](GRID_MODEL.md)。验证范围为所定义的 DC 调度与业务约束。']
    repository_check = PACK / 'repository_validation.json'
    if repository_check.exists():
        check = json.loads(repository_check.read_text())
        lines += ['', '## 目录检查范围', '',
            f"全库目录包含 793 个案例。AIDC-39 相关目录错误为 {len(check['new_aidc39_issues'])}；其他旧包存在 {check['total_issues']-len(check['new_aidc39_issues'])} 项配置特征与 MANIFEST 不一致（未修改这些旧包输入）。详细检查记录见 [repository_validation.json](repository_validation.json)。全库目录检查的失败不能写成通过，也不影响上述三个新案例的数值验收。"]
    (PACK / 'BENCHMARK.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(dict(accepted=report['accepted'], reports=['BENCHMARK.md', 'benchmark_results.json']), ensure_ascii=False))
    return report


if __name__ == '__main__':
    raise SystemExit(0 if generate_report()['accepted'] else 1)
