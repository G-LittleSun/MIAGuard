"""Prepare a blinded human review packet for this development cohort."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path.cwd()
COHORT = ROOT / 'data/defense_datasets/next_goal_v2_train_20261117_01'
SOURCE = ROOT / 'data/runs/20260717-ag-news-four-medium/ag_news/target_docs.jsonl'
OUT = ROOT / 'reports/defense_v1/T10/next_goal_human_review_packet_20261117'


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x.strip()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    requests = {x['request_id']: x for x in rows(COHORT / 'requests.jsonl')}
    lineage = {x['request_id']: x for x in rows(COHORT / 'lineage.jsonl')}
    rubrics = {x['request_id']: x for x in rows(COHORT / 'normal_rubric.jsonl')}
    docs = {x['doc_id']: x['text'] for x in rows(SOURCE)}
    labels = rows(COHORT / 'labels.jsonl')
    packet = []
    for label in labels:
        rid, doc = label['request_id'], label['doc_id']
        candidate = {k: label[k] for k in ('answerable', 'reference_answer', 'answers', 'ground_truth') if k in label}
        packet.append({'request_id': rid, 'session_id': requests[rid]['session_id'],
                       'turn': lineage[rid]['turn'], 'task_family': label['attack_type'],
                       'query': requests[rid]['query'], 'source_doc_id': doc, 'source_text': docs[doc],
                       'source_text_sha256': sha256(docs[doc].encode()).hexdigest(),
                       'candidate_reference': candidate, 'candidate_normal_rubric': rubrics.get(rid),
                       'status': 'pending', 'reviewer_kind': None, 'human_reviewed': False})
    assert len(packet) == 47 and sum(x['task_family'] == 'benign' for x in packet) == 15
    assert all('membership_label' not in json.dumps(x) for x in packet)
    OUT.mkdir(exist_ok=False)
    packet_path = OUT / 'review_packet.jsonl'
    with packet_path.open('x', encoding='utf8') as f:
        for x in packet:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    guide = '''# 真人审核交接单

本包含47个开发题审核单元，其中正常15条，攻击32条。请实际人员审核，记录审核人身份和审核日期。题目来自v2 train开发来源，审核结果可用于改进开发题单，正式T10-E仍需按协议完成独立来源与划分验收。

逐题核对原文是否足以支持参考答案，是否存在截断或标题依赖，问题是否自然明确。Masked 检查原词数量、顺序、还原与遮蔽词重现。Direct 检查目标文章与问题一致。IA 检查事实、是非答案、主题指代与连续轮次是否合理。正常题标明是否可回答、必要事实、必要证据及可接受答案。证据不足题确认所问内容确不在限定来源里。

对每个 request_id 输出 accept、rewrite、reject 或 uncertain，并提供理由。rewrite 给出完整新问题、答案、证据引用，reject 给出排除理由。会话涉及改写时明确所有受影响轮次并生成新会话身份。按 request_id 一一对应保存为 human_review.jsonl，另存 human_review_summary.md，记录人数、专业背景、分歧及裁定。不要查看或填写索引成员标签。

完成后交付输出路径、审核身份、行数和 SHA256。机器或LLM输出请如实写明，不能作为 human_reviewed。
'''
    (OUT / 'HUMAN_REVIEW_GUIDE_ZH.md').write_text(guide, encoding='utf8')
    manifest = {'schema_version': 1, 'status': 'pending_human_review', 'human_reviewed': False,
                'formal_effect_eligible': False, 'task_count': len(packet), 'benign_count': 15,
                'attack_count': 32, 'inputs_sha256': {str(x): digest(x) for x in
                    [COHORT / 'manifest.json', COHORT / 'requests.jsonl', COHORT / 'labels.jsonl',
                     COHORT / 'lineage.jsonl', COHORT / 'normal_rubric.jsonl', SOURCE, Path(__file__).resolve()]},
                'outputs_sha256': {x.name: digest(x) for x in [packet_path, OUT / 'HUMAN_REVIEW_GUIDE_ZH.md']},
                'limitations': ['v2 train development cohort; independent formal evaluation cohort not established.',
                                'No human review has been performed.', 'Membership labels omitted from packet.']}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Review packet', len(packet), 'normal 15 attack 32:', OUT)


if __name__ == '__main__':
    main()
