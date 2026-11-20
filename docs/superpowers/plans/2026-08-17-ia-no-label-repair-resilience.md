# IA `no` 标签修复韧性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 IA Query Bank 修复器稳定构造经验证的 `no` 查询，并在失败或中断后从已验证候选继续。

**Architecture:** 在 `builder.py` 增加仅用于 `no` 目标的“原子事实→单属性矛盾”候选提示；仍用现有独立标签验证、去重和固定数量收集。`repair.py` 将逐文档的已验证候选和失败原因写入 `.work/ia_repair_progress.jsonl`，重启时载入并继续；聚合 Query Bank 仅在所有文档校验成功后原子发布。

**Tech Stack:** Python 3.10、pytest、现有 ModelClient、JSONL 原子写入、Query Bank storage。

---

### Task 1: 测试证据驱动的 `no` 候选提示

**Files:**
- Modify: `tests/test_query_bank_builder.py`
- Modify: `src/miaguard/query_bank/builder.py`

- [ ] 写失败测试：调用 `_ia_candidates(..., required_answer="no")`，断言提示带 `[IA_NO_FACTS]` 和 `[IA_NO_CONTRADICTIONS]`，并且只有验证为 `no` 的候选返回。
- [ ] 运行：`conda run -n rag_env python -m pytest tests/test_query_bank_builder.py::test_ia_no_candidates_use_single_attribute_contradictions -v`
- [ ] 实现：新增 `_ia_no_candidates()`；第一阶段要求 JSON `{"facts":[{"subject":"…","attribute":"…","value":"…"}]}`，第二阶段要求 JSON `{"summary":"…","questions":["…"]}`，并要求每题只改变一项原子事实、包含显式主体、无模糊指代。将结果送入既有 `_verify_ia_answers()`；`_ia_candidates()` 在 `required_answer == "no"` 时委派该函数。
- [ ] 再次运行同一测试，预期 PASS。

### Task 2: 测试恢复状态和失败审计

**Files:**
- Modify: `tests/test_query_bank_repair.py`
- Modify: `src/miaguard/query_bank/storage.py`
- Modify: `src/miaguard/query_bank/repair.py`

- [ ] 写失败测试：第一次修复用故障客户端产生部分 `no` 后失败；断言 `paths.repair_progress` 记录文档 ID、已接受候选、目标标签和失败计数，且主查询/清单不变。第二次修复用成功客户端，断言仅生成缺口、发布成功、进度文件删除。
- [ ] 运行：`conda run -n rag_env python -m pytest tests/test_query_bank_repair.py::test_repair_resumes_verified_candidates_after_a_no_label_failure -v --basetemp D:\Project\MIAGuard\.pytest-tmp`
- [ ] 实现：为 `QueryBankPaths` 增加 `repair_progress`；在每个已完成目标标签后原子写入进度。恢复时将进度候选合并到内存的 `added_rows` 与 `existing_questions`，只请求剩余数。任何异常写入 `last_error` 并保留进度；成功发布后删除状态文件。
- [ ] 再次运行同一测试，预期 PASS。

### Task 3: 端到端回归与后台恢复

**Files:**
- Verify: `tests/test_query_bank_builder.py`
- Verify: `tests/test_query_bank_repair.py`
- Verify: `data/query_banks/ag_news_queries_v1/ag_news/.work/ia_repair_progress.jsonl`

- [ ] 运行：`conda run -n rag_env python -m pytest tests/test_query_bank.py tests/test_query_bank_builder.py tests/test_query_bank_repair.py tests/test_query_bank_scripts.py -v --basetemp D:\Project\MIAGuard\.pytest-tmp`
- [ ] 在 CUDA 环境先对 `ag_news_teacher_00000027` 执行恢复式定向修复，确认 4 条 `yes` 和 8 条 `no` 均可收集；若无法满足，保留进度并退出，不发布主数据。
- [ ] 启动唯一后台全量修复命令，使用 `python -u` 使标准输出实时写入 `data/logs/ia_query_bank_repair_*.log`；完成后运行 Query Bank 验证与 30 轮 15+15 抽样检查。

## 自检

- 覆盖：Task 1 解决 `no` 定向性，Task 2 提供失败恢复，Task 3 验证和继续真实修复。
- 一致性：状态文件统一为 `repair_progress`，正式日志仍为 `ia_repair_log.jsonl`。
- 当前工作区非 Git 仓库，因此不包含提交步骤。
