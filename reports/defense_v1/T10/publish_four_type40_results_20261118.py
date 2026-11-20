"""Publish verified single-round results, then extend the same section with IA."""

import argparse
from pathlib import Path
import re

from inventory_four_type40_20261118 import REPORT, ROOT, digest, read
from render_four_type40_tables_20261118 import KINDS, METHODS, render
from verify_four_type40_run_20261118 import verify_run


RUN_ROOT = ROOT / 'data/defense_v1_runs'
DOCS = ROOT / 'docs'
SINGLE = 'four-type40-single-paired-20261118-01'
IA = 'four-type40-ia-paired-20261118-01'
HEADING = '## 2026-11-18 四类成员推断的 B0/V2 开发配对'


def link(path, label):
    return f'[{label}](../{path.relative_to(ROOT).as_posix()})'


def check_summary(run_id, expected_kinds):
    run = RUN_ROOT / run_id
    path = REPORT / f"{run_id.replace('-', '_')}_summary.json"
    summary = read(path)
    assert summary['verification'] == verify_run(run), f'{run_id} verification record differs from the archive.'
    assert summary['scorer_sha256'] == digest(REPORT / 'score_four_type40_20261118.py')
    assert set(summary['measures']) == set(expected_kinds)
    assert summary['verification']['verified_method_request_pairs'] == 240
    for kind in expected_kinds:
        sides = summary['measures'][kind]
        for method in METHODS:
            for side in ('0', '1'):
                group = sides[method][side]
                assert group['sessions'] == group['targets'] == 20
                assert group['execution']['denominator'] == (60 if kind == 'ia' else 20)
    return path, summary['verification']


def make_section(include_ia):
    runs = [(SINGLE, check_summary(SINGLE, tuple(kind for kind in KINDS if kind != 'ia')))]
    if include_ia:
        runs.append((IA, check_summary(IA, ('ia',))))
    lines = [HEADING, '', 'B0 关闭动态防御。V2 使用冻结的风险识别与类型访问控制。两组题目、索引和生成配置配对一致。'
             '每类 20 个库内和 20 个库外目标，IA 每目标固定三轮。结果来自 v2 train 的本地开发对照。', '']
    for run_id, (path, verified) in runs:
        status = verified['event_status']
        n, d = status.get('complete', 0), verified['verified_method_request_pairs']
        cases = path.with_name(path.name.replace('_summary.json', '_cases.jsonl'))
        group = 'IA' if run_id == IA else 'Direct、S²、Masked'
        lines.append(f'- **{group}**已归档 {d} 次配对请求，执行完成 {100 * n / d:.1f}%（{n}/{d}），'
                     f'失败 {status.get("failed", 0)}，跳过 {status.get("skipped", 0)}。'
                     f' {link(RUN_ROOT / run_id / "run_manifest.json", "运行清单")} · '
                     f'{link(path, "指标 JSON")} · {link(cases, "逐请求评分")}')
    if not include_ia:
        lines.append('- **IA** 题单已冻结，B0/V2 主批待完成并核验，指标暂未发布。'
                     f' {link(ROOT / "data/defense_datasets/four_type40_ia_v2_train_20261118_01/manifest.json", "IA 冻结题单")}')
    lines += ['', render(*(path for _, (path, _) in runs)).rstrip(), '', '#### 汇报时的口径', '',
              '- 三类单轮共享 40 篇，IA 与单轮重用 27 篇，四类合计 53 篇不同文档。'
              '按标题和导语初步区分 53 个报道主题，独立事件数未评估。'
              f' {link(REPORT / "four_type40_source_event_overlap_20261118.json", "来源盘点")}',
              '- Judge 触发率以有触发记录的请求为分母。B0 关闭动态 Judge，分母为零。'
              '回答、目标原文交付及风险触发是三个环节的指标。'
              '目标原文交付率使用计划目标或轮次作分母，配对明细另列两侧证据日志齐全的数量。',
              '- S² AUROC 为本地样本中相似度分数的描述性排序结果。固定攻击阈值下的 TPR/FPR、'
              '独立成员泄露下降及统计显著性均未评估。']
    if include_ia:
        lines.append('- IA 库内、库外各有 16 个会话能匹配相同参考组合，另外 4 个组合不同。'
                     '部分题干已经写出对应事实。库外回答 Yes 也可能来自题干或模型已有知识，须与原文交付分开解读。')
    lines += ['- 正常 RAG 效用单独引用 48 题配对。V2 在这批题上全部放行，触发访问限制后的效用仍待验证。'
              f' {link(REPORT / "UTILITY48_REUSE_RESULTS_20261117_ZH.md", "48 题正常效用")}',
              '', '复算入口见'
              f'{link(REPORT / "verify_four_type40_run_20261118.py", "运行核验")}、'
              f'{link(REPORT / "score_four_type40_20261118.py", "评分脚本")}、'
              f'{link(REPORT / "render_four_type40_tables_20261118.py", "生成对照表")}及'
              f'{link(REPORT / "FOUR_TYPE40_SCORING_ZH.md", "预登记评分")}。', '']
    return '\n'.join(lines)


def upsert_section(doc, section):
    own = re.compile(r'^' + re.escape(HEADING) + r'\n.*?(?=^## |\Z)', re.M | re.S)
    if own.search(doc):
        return own.sub(lambda _: section.rstrip() + '\n\n', doc, count=1)
    introduction, heading, content = doc.partition('\n## ')
    assert heading and HEADING in section
    return introduction.rstrip() + '\n\n' + section.rstrip() + '\n\n## ' + content


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-ia', action='store_true', help='Include the verified IA archive.')
    parser.add_argument('--write', action='store_true', help='Update the project experiment-results document.')
    args = parser.parse_args()
    section = make_section(args.include_ia)
    if args.write:
        path = DOCS / 'EXPERIMENT_RESULTS_ZH.md'
        old = path.read_text(encoding='utf-8')
        assert args.include_ia or '- **IA**已归档' not in old, 'The combined report is already published.'
        new = upsert_section(old, section)
        if new != old:
            path.write_text(new, encoding='utf-8')
        print(f'Published verified results in {path}')
    else:
        print(section, end='')
