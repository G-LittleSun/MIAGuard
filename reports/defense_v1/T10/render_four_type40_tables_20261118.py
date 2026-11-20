"""Render Chinese comparison tables from verified scores, without changing the results."""

import sys
from pathlib import Path

from inventory_four_type40_20261118 import digest, read, rows

KINDS = {'direct_rag_mia': 'Direct', 's2_mia': 'S²', 'masked_mia': 'Masked', 'ia': 'IA'}
METHODS = ('B0', 'B_TYPE_V2')
SIDES = {'1': '库内', '0': '库外'}
METRICS = {
    'direct_rag_mia': [('yes', '回答 Yes')],
    's2_mia': [('exact_prefix_echo', '原样复述题中片段')],
    'masked_mia': [('masked_recovered', '原词恢复位置'), ('masked_parsed', '可解析题目')],
    'ia': [('session_yes', '至少一轮回答 Yes 的会话'), ('session_raw', '至少一轮交付原文的会话'),
           ('completed_sessions', '完整执行会话')],
}
OUTPUTS = {'yes': 'Yes', 'no': 'No', 'unknown': '未知', 'deny': '拒答', 'unavailable': '不可用',
           'failed': '失败', 'skipped': '跳过', 'other': '其他'}
ACTIONS = {'allow': '放行', 'deny': '拒答', 'hide_target_refill': '排除目标后用其他文档补位',
           'no_context_answer': '不交付检索材料，仍可回答', 'sanitized_context': '交付经过处理的材料',
           'unavailable': '不可用'}


def rate(m, digits=1):
    n, d = m['numerator'], m['denominator']
    return f'{100 * n / d:.{digits}f}%（{n:g}/{d:g}）' if d else f'未评估（{n:g}/{d:g}）'


def comparison(kind, side, metric, a, b, digits=1):
    diff = 100 * (b['value'] - a['value']) if a['value'] is not None and b['value'] is not None else None
    change = f'{diff:+.{digits}f} 个百分点' if diff is not None else '—'
    return f'| {kind} | {side} | {metric} | {rate(a, digits)} | {rate(b, digits)} | {change} |'


def distribution(counts, names, denominator):
    if not counts:
        return '—'
    return '、'.join(f'{names.get(name, name)} {rate({"numerator": n, "denominator": denominator})}'
                  for name, n in sorted(counts.items()))


def example_lines(cases):
    by_case = {(row['run_id'], row['method'], row['request_id']): row for row in cases}
    paired = [(base, by_case[run, 'B_TYPE_V2', rid]) for (run, method, rid), base in by_case.items()
              if method == 'B0' and base['membership_label'] == 1]
    paired = [(a, b) for a, b in paired if a['evidence_log_present'] and b['evidence_log_present']]
    prevented = next(((a, b) for a, b in paired if a['target_raw_delivered'] and not b['target_raw_delivered']), None)
    residual = next(((a, b) for a, b in paired if b['target_raw_delivered']), None)
    if residual is None:
        residual = next(((a, b) for a, b in paired if b['output_category'] == 'yes' or
                         (b.get('masked') or {}).get('matched')), None)
    lines = ['', '#### 可回查案例', '']
    for caption, example in [('原文交付受到限制', prevented), ('仍有原文交付或输出信号', residual)]:
        if example is None:
            lines.append(f'- 本批未观察到“{caption}”的合格案例。')
            continue
        a, b = example
        descriptions = []
        for row in (a, b):
            action = ACTIONS.get(row['action'], row['action'])
            raw = '交付' if row['target_raw_delivered'] else '未交付'
            category = OUTPUTS.get(row['output_category'], row['output_category'])
            masked = row.get('masked')
            output = f"恢复 {masked['matched']}/{masked['total']} 个原词" if masked and masked['matched'] is not None else f'回答分类 {category}'
            descriptions.append(f"{row['method']} {action}，{raw}目标原文，{output}")
        lines.append(f"- {caption}，{KINDS[a['attack_type']]}，运行 `{a['run_id']}` 中的 `{a['request_id']}`，"
                     f"来源 `{a['doc_id']}`。" + '。'.join(descriptions) + '。')
    return lines


def render(*summary_paths):
    measures, pairs, cases = {}, {}, []
    for summary_path in summary_paths:
        summary = read(summary_path)
        verification = summary['verification']
        case_path = summary_path.with_name(summary_path.name.replace('_summary.json', '_cases.jsonl'))
        assert digest(case_path) == summary['cases_sha256']
        run_cases = rows(case_path)
        assert len(run_cases) == verification['verified_method_request_pairs']
        assert not measures.keys() & summary['measures'].keys(), 'Overlapping strata in report inputs.'
        measures.update(summary['measures'])
        pairs.update(summary['paired'])
        cases.extend(dict(row, run_id=verification['run_id']) for row in run_cases)
    lines = ['| 类型 | 目标 | 指标 | B0 | B_TYPE_V2 | V2−B0 |', '|---|---|---|---:|---:|---:|']
    details = []
    for kind, name in KINDS.items():
        if kind not in measures:
            continue
        outcome_details = []
        if kind == 's2_mia':
            a, b = (measures[kind][method]['descriptive_auc'] for method in METHODS)
            lines.append(comparison(name, '库内×库外', '描述性 AUROC', a['auc'], b['auc'], digits=2))
            breakdown = '；'.join(f'{method} 库内 {m["scored_indexed_targets"]}、库外 {m["scored_nonindexed_targets"]} 个分数，'
                                 f'{m["strict_wins"]} 个严格顺序对、{m["ties"]} 个并列对'
                                 for method, m in zip(METHODS, (a, b), strict=True))
            outcome_details.append(f'- AUROC 按库内和库外分数组成的两两比较计算，并列计半。{breakdown}。')
        for side, side_name in SIDES.items():
            a, b = (measures[kind][method][side] for method in METHODS)
            unit = '请求轮次' if kind == 'ia' else '目标'
            columns = METRICS[kind] + [('target_raw_delivered', f'交付目标原文（按{unit}）'),
                                      ('judge_triggered', 'Judge 风险触发'), ('execution', '请求执行完成')]
            for metric, label in columns:
                lines.append(comparison(name, side_name, label, a[metric], b[metric]))
            paired = pairs[kind][side]
            p, completed = paired['planned_request_pairs'], paired['complete_pairs']
            coverage = paired['evidence_pair_coverage']
            raw_removed, raw_added = (len(paired[f'raw_{key}_request_ids']) for key in ('removed', 'added'))
            outcome_details.append(f'- {side_name} {a["targets"]} 个目标，完成请求配对 {completed}/{p}。证据日志齐全的配对 '
                                   f'{coverage}/{p}，目标原文由有变无 {raw_removed}/{coverage}，由无变有 {raw_added}/{coverage}。')
            if kind == 's2_mia':
                outcome_details.append(f'  - 两方法均有有限分数的目标 {paired["common_finite_score_targets"]}/{a["targets"]}。')
            if kind == 'ia':
                outcome_details.append(f'  - 完整会话配对 {paired["complete_session_pairs"]}/{paired["planned_session_pairs"]}。')
                patterns = distribution(a['reference_patterns'], {}, a['sessions'])
                outcome_details.append(f'  - 固定题单参考答案组合 {patterns}。题干前缀已经给出待核事实的轮次 '
                                       f'{rate(a["premise_supplied"])}。')
                transitions = distribution(paired['session_yes_transitions'], {'0 -> 0': '两组均未答 Yes',
                                           '1 -> 0': '由有 Yes 变为无 Yes', '0 -> 1': '由无 Yes 变为有 Yes',
                                           '1 -> 1': '两组均有 Yes'}, paired['planned_session_pairs'])
                outcome_details.append(f'  - 会话输出变化 {transitions}。')
            for method, group in zip(METHODS, (a, b), strict=True):
                completed_requests = group['execution']['numerator']
                all_requests = group['execution']['denominator']
                actions = distribution(group['actions'], ACTIONS, completed_requests)
                outputs = dict.fromkeys(OUTPUTS, 0) | group['outputs'] if kind == 'direct_rag_mia' else group['outputs']
                categories = distribution(outputs, OUTPUTS, all_requests)
                outcome_details.append(f'  - {method} 执行动作 {actions}。回答类别 {categories}。')
                if kind == 'masked_mia':
                    parse = distribution(group['masked_status'], {'parsed': '可解析', 'denied': '拒答',
                                         'parse_failed': '格式失败', 'unsupported_structure': '结构不符'}, all_requests)
                    outcome_details.append(f'    - 填空评分 {parse}。可判位置的恢复率 '
                                           f'{rate(group["masked_recovered_known_slots"])}。')
                if kind == 'ia':
                    for turn, output in group['per_turn'].items():
                        turn_dist = distribution(output, OUTPUTS, group['sessions'])
                        fusion = rate(group['session_fusion_by_turn'][turn])
                        outcome_details.append(f'    - 第 {turn} 轮 {turn_dist}。使用会话融合分数 {fusion}。')
        details.extend(['', f'#### {name} 配对明细', '', *outcome_details])
    if 'ia' in measures:
        details.extend(['', 'IA 按固定三轮会话计目标。Judge 会话融合按实际风险来源计数，'
                        '逐轮出题保持固定。'])
    return '\n'.join(lines + details + example_lines(cases)) + '\n'


if __name__ == '__main__':
    print(render(*(Path(arg) for arg in sys.argv[1:])), end='')
