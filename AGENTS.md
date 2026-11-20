# MIAGuard 新会话入口

开始开发前，依次阅读：

1. `docs/PROJECT_STATUS_ZH.md`：当前已完成、未完成和下一步。
2. `docs/DATA_CATALOG_ZH.md`：正式数据、冻结划分和产物身份。
3. `docs/EXPERIMENT_INDEX_ZH.md`：实验状态、指标摘要和原始结果入口。
4. 与任务相关的专题文档；从 `docs/README.md` 或 `docs/文档总目录_ZH.md` 查找。

查找工程目录和源码入口时，阅读 `docs/PROJECT_STRUCTURE_ZH.md`；逐文件用途和测试覆盖见 `docs/CODE_FILE_INDEX_ZH.md`。Git 同步、回滚和忽略项见 `docs/GIT_WORKFLOW_ZH.md`。同日多条进度记录按本页指定的当前状态和台账最新记录核对，旧检查点按历史阅读。

选择数据、模型、实验或开发基线前，读取 `docs/CURRENT_VERSIONS_ZH.md` 统一版本总表，并核对其原始 manifest/选择清单及 SHA256。当前防御数据复用入口为 `ag_news_queries_v2` + `ag_news_threshold_v2` 的 train；已完成 Judge v3 和 E00 的历史数据仍为 v1，不能混用。规格/计划/协议 v1.1 与代码包 0.1.0 也不是同一类版本。版本切换须同步总表、分项目录和台账；不得仅按日期、目录名或文件默认值判定“最新”。

文档是导航，运行清单与结果 JSON 是数字和身份的核对依据。遇到冲突时先读取相应 `run_manifest.json`、`benchmark_summary.json`、冻结模型和评估 JSON，再更新过期文档。`docs/superpowers/specs/` 与 `plans/` 中的文件不能单独证明完成状态；当前有效计划由进度台账明确指定，其余按历史记录阅读。

防御开发阶段继续阅读 `docs/DEFENSE_PROGRESS_ZH.md`，再阅读其中链接的开发规格、详细实施计划和实验协议。按台账的 `next_task` 与依赖推进，不跳过验收门禁。每次任务开始、完成可验证子步骤、运行实验、失败/中断、恢复或改变设计时，在台账追加记录，并同步任务状态、计划复选框与下一步。执行记录必须包含实际命令、结果、产物位置和限制；不得将计划、预期输出或文档完成当作功能/实验完成。

截至 2026-11-20，四类各 40 目标的 B0/V2 真实模型开发对照完成 480/480，48 题正常效用配对完成 96/96，另有困难正常题的事后补评。具体范围、指标、评分资格及原始运行入口见 `docs/EXPERIMENT_INDEX_ZH.md` 和 `docs/EXPERIMENT_RESULTS_ZH.md`。48 题中 V2 全部放行，触发过滤后的效用参考困难正常题对照及其限制。成员泄露结论须依据访问控制后的攻击效果及相应原始记录。正式独立防御效果评估、人工 gold 和校准仍待完成。已有历史 test 结果已查看；后续改提示、模型或策略，应在开发数据上进行，并注明复用 test 的限制。

当前有效防御规格、主实施计划和实验协议为原路径的 v1.1；T10-C 的 D-dev 开发设计已完成，T10-D 仍进行中。后续从台账最新 `next_task` 和追加记录恢复，结合实际缺口推进独立来源、人工审核、攻击校准与受控过滤对照。正式多轮评估需核对独立来源和题单质量，当前开发对照的资格及限制按对应原始记录使用。

完成新功能或实验时，更新 `docs/PROJECT_STATUS_ZH.md` 和 `docs/EXPERIMENT_INDEX_ZH.md`；新增数据版本时再更新 `docs/DATA_CATALOG_ZH.md`。只记录实际完成并能指向产物的结果，明确标记中断运行。
