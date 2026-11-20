"""Prepare the previously model-reviewed D-dev pilot for human adjudication."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path.cwd()
OVERLAY = ROOT / 'data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030'
CANDIDATE = ROOT / 'data/defense_datasets/defense_access_v1_candidate06'
REVISION = ROOT / 'reports/defense_v1/T10/pilot_revision_20261030_01'
OUT = ROOT / 'reports/defense_v1/T10/t10e_ddev_human_review_20261117'


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x.strip()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((OVERLAY / 'manifest.json').read_text(encoding='utf8'))
    for name, expected in manifest['output_files_sha256'].items():
        assert digest(OVERLAY / name) == expected, name
    evidence_path = REVISION / 'review_packet_d_dev_normal_evidence.jsonl'
    assert digest(evidence_path) == manifest['pilot_evidence_sha256']
    documents_path = CANDIDATE / 'documents.jsonl'
    assert digest(documents_path) == manifest['source_files_sha256']['documents.jsonl']
    evidence = {x['request_id']: x['supporting_documents'] for x in rows(evidence_path)}
    docs = {x['doc_id']: x['text'] for x in rows(documents_path) if x['partition'] == 'D-dev'}
    packet = []
    for family, requests_name, labels_name in [
        ('normal', 'normal_requests.jsonl', 'normal_tasks.jsonl'),
        ('attack', 'attack_requests.jsonl', 'attack_labels.jsonl'),
    ]:
        requests = {x['request_id']: x for x in rows(OVERLAY / requests_name)}
        for label in rows(OVERLAY / labels_name):
            rid = label['request_id']
            refs = ({k: label[k] for k in ('answerable', 'reference_answer', 'gold_evidence_ids',
                                           'unanswerable_reason', 'answers', 'ground_truth', 'target_text') if k in label})
            sources = evidence[rid] if family == 'normal' else [{'doc_id': label['doc_id'], 'text': docs[label['doc_id']]}]
            if family == 'normal':
                assert set(label['gold_evidence_ids']) <= {x['doc_id'] for x in sources}
            packet.append({'request_id': rid, 'session_id': requests[rid]['session_id'],
                           'family': label.get('task_family') or label['attack_type'],
                           'query': requests[rid]['query'], 'source_documents': sources,
                           'candidate_reference': refs, 'human_reviewed': False, 'status': 'pending'})
    assert len(packet) == 86 and len({x['request_id'] for x in packet}) == 86
    assert all('membership_label' not in json.dumps(x) for x in packet)
    OUT.mkdir(exist_ok=False)
    packet_path = OUT / 'review_packet.jsonl'
    with packet_path.open('x', encoding='utf8') as f:
        for item in packet:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    guide = '''# T10-E D-dev 试点真人审核交接

本包来自 candidate06 的 D-dev 修订试点，70 条正常查询、16 条攻击查询，均待真人审核。参考答案包含模型建议，按会话检查自然性及递进。原文及证据 ID 为审核依据。输出不代表该批可立即回放，T10-E 还需处理截断、来源、会话、独立划分和全部正式任务覆盖。

正常题逐项审核是否可回答、答案是否忠于所附原文、证据是否齐全、是否依赖标题或截断、会话是否自然。跨文档题须检查两篇证据、因果和时间描述。证据不足题须检查没有超出材料推断。攻击题核对原文匹配、IA事实及提示是否自带答案、Masked遮蔽词是否泄漏及恢复顺序。

对每个 request_id 输出 accept、rewrite、reject 或 uncertain。rewrite 给完整问题、答案与证据，reject 写原因。记录真实审核者、审核日期、分歧和裁定，保存 human_review.jsonl 与 human_review_summary.md。不要读取或填写成员标签。模型审核只作建议，不能标记 human_reviewed。
'''
    guide_path = OUT / 'HUMAN_REVIEW_GUIDE_ZH.md'
    guide_path.write_text(guide, encoding='utf8')
    metadata = {'status': 'pending_human_review', 'human_reviewed': False, 'formal_effect_eligible': False,
                'partition': 'D-dev', 'request_count': 86, 'normal_count': 70, 'attack_count': 16,
                'inputs_sha256': {str(p): digest(p) for p in [OVERLAY / 'manifest.json', documents_path,
                    evidence_path, *[OVERLAY / n for n in manifest['output_files_sha256']], Path(__file__).resolve()]},
                'outputs_sha256': {p.name: digest(p) for p in (packet_path, guide_path)},
                'limits': ['D-dev pilot, not the A-cal/V/T formal cohort.', 'Human gold and cohort gates incomplete.',
                           'Reviewers are not shown membership labels.']}
    (OUT / 'manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('D-dev human review packet:', len(packet), 'requests:', OUT)


if __name__ == '__main__':
    main()
