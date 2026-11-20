# MIAGuard Git 版本管理与同步

2026-11-20。项目本地 Git 仓库位于 `D:/Project/MIAGuard/.git`，开发分支为 `main`，远程名称为 `origin`。[GitHub 仓库](https://github.com/G-LittleSun/MIAGuard)

## 提交范围

| 内容 | 管理方式 |
|---|---|
| `src/`、`scripts/`、`tests/`、`configs/`、`schemas/`、模式库和环境定义 | Git 保存源码、测试、配置及依赖声明 |
| `docs/`、`reports/` 和 `models/` 下载清单 | Git 保存文档、分析报告、审核记录、复算脚本和模型来源信息 |
| `data/defense_datasets/`、`data/defense_v1_runs/` | Git 保存冻结题单与防御实验归档 |
| `data/query_banks/`、`data/query_bank_splits/`、`data/runs/` | Git 保存查询库、划分及运行时固定的目标样本 |
| `data/judge_score_*/`、`data/two_stage_*/` | Git 保存评分分析、冻结评分头、相关标定与结果 |
| `LLM/`、`EmbeddingModel/`、`DataSet/`、向量索引、预处理数据、其他运行输出、日志和缓存 | 由 `.gitignore` 忽略，在本地存放并另行备份 |

查询库构建中的 `.work/`、运行目录下的 `logs/`、Python 缓存和测试临时目录也配置了忽略规则。精确范围以根目录 [.gitignore](../.gitignore) 为准。查看某个文件为何被忽略，可运行 `git check-ignore -v 文件路径`。

冻结 manifest 绑定文件的字节摘要。项目的 [.gitattributes](../.gitattributes) 为文件关闭自动换行转换，克隆和暂存时保留原有 LF/CRLF 字节，便于复核 SHA256。实验选样、评分头与运行身份继续通过[版本总表](CURRENT_VERSIONS_ZH.md)、[数据目录](DATA_CATALOG_ZH.md)和原始清单核对。

## 日常保存和同步

从项目根目录执行。先查看本次修改和暂存内容，再提交。

```powershell
Set-Location D:\Project\MIAGuard
git status
git diff
git add -A
git diff --cached --stat
git commit -m "Describe the completed change"
git push
```

多台电脑协作时，先在工作区干净的情况下执行 `git pull --ff-only`。发生分支分歧时查看两端提交并解决，按实际合并结果继续提交。

## 历史和回滚

运行 `git log --oneline --decorate -15` 查看最近版本，用 `git show 提交ID` 检查对应改动。撤销已经同步的提交时，运行 `git revert 提交ID` 生成一条撤销记录，处理完成后运行 `git push`。这样远端历史仍可追溯。

代码提交保存 Git 跟踪的文件版本。模型、原始数据和索引的恢复依靠它们的本地备份、来源以及 manifest 中的身份记录。在新机器上克隆后，按相同相对路径恢复这些输入。现有实验规格内还保留 `D:\Project\MIAGuard` 的绝对路径，在不同工作目录使用时应根据规格和原始摘要检查路径。

```powershell
git clone https://github.com/G-LittleSun/MIAGuard.git
Set-Location MIAGuard
git status
```

依赖安装、模型和数据准备见[工程目录](PROJECT_STRUCTURE_ZH.md)与[使用手册](USAGE_GUIDE_ZH.md)。已有四类对照的复算还需恢复原索引及对应输入，按[实验结果汇总](EXPERIMENT_RESULTS_ZH.md)中的产物路径核验。

## 首次初始化记录

- 本地已执行 `git init -b main`、添加 `origin` 并配置当前仓库的作者。作者使用 GitHub 账号 `G-LittleSun` 和对应的 GitHub 隐私邮箱，配置保存在本项目的 `.git/config`。
- 首次提交前检查远端为空、忽略范围、待提交文件大小及凭据特征。5,350 个文件的 Git 暂存对象与本地原字节逐项一致，两批四类对照运行各 240 次的核验通过，61 项相关测试通过。旧 `.gitignore` 的本地副本保存在 `.codex_tmp/git-initialization-20261120/gitignore.before`。
- 首次提交与推送的完成状态，以本地 `git log -1`、`git status -sb` 和远端 `main` 分支的实际提交 ID 核对。
