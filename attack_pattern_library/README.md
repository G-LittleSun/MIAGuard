# 攻击模式库

该目录保存 LLM-as-Judge 使用的可查询、可更新攻击定义，不属于 Codex Skill。

- `manifest.yaml`：注册模式、版本、入口文件和所需上下文。
- `JUDGE_PROTOCOL.md`：所有 Judge 共用的最小安全协议。
- `patterns/*/PATTERN.md`：每种攻击的定义、排除项和判断示例。

更新某种攻击时，只修改对应 `PATTERN.md`，递增该模式和模式库版本，然后运行
模式库校验与回归测试。正式实验会在结果目录保存本次模式库快照，避免后续更新
影响历史实验的复现。
