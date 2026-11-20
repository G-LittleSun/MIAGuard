# T2Ranking 本地源数据探查报告

- 探查时间：2026-07-14T03:17:58.705440+00:00
- 数据集：T2Ranking
- 本地路径：`DataSet/T2Ranking`
- 来源：unknown（本地文件无法确认）
- 许可：unknown（本地文件无法确认）
- revision：unknown（本地文件无法确认）
- 原始数据被流水线修改：否

## 文件清单

| 文件 | 字节数 | 记录数 | 字段 | SHA-256 |
|---|---:|---:|---|---|
| `DataSet/T2Ranking/collection.tsv` | 3659243528 | 2303643 | pid, text | `07b84e543e9ba696124a727c00629d5bce586631648c436c98dd6e9b146da212` |
| `DataSet/T2Ranking/info.md` | 4 | 1 | - | `9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08` |
| `DataSet/T2Ranking/qrels.dev.tsv` | 6537957 | 400535 | qid, -, pid, rel | `a0356bd3c6d72c532ca17a4d88d7765554857f321346cf0f9cb4ad480738b25a` |
| `DataSet/T2Ranking/qrels.retrieval.dev.tsv` | 1468343 | 118932 | qid, pid | `17f31db546ce3a5f861c9139939a97c19b0082a0a864be35a7821770a0705a06` |
| `DataSet/T2Ranking/qrels.retrieval.train.tsv` | 10845519 | 744662 | qid, pid | `4a2c224021a39637873a2cd69d90a9e41cb117d0560e940399439dcc6af61cfa` |
| `DataSet/T2Ranking/qrels.train.tsv` | 29881875 | 1613421 | qid, -, pid, rel | `5da21371d1f2fa2700bc74a4fdc69b2389b5f304e864a42ac2fe555cad87c77e` |
| `DataSet/T2Ranking/queries.dev.tsv` | 939767 | 24831 | qid, text | `1df544dd04bf9b6d0de0dd77e0f3a84a0d74fc4bb9a1ff67b7306de8169135ba` |
| `DataSet/T2Ranking/queries.test.tsv` | 953406 | 24831 | qid, text | `143b701f0bf4dfccee6ba3c6d08e620cf740a688ade02e7727beb7f5735ddbb1` |
| `DataSet/T2Ranking/queries.train.tsv` | 10210389 | 258042 | qid, text | `b9328c8a0be4980cb8860819285ff3da8c6976f5089e0a606ff003165c4b2c0e` |
| `DataSet/T2Ranking/train.bm25.tsv` | 3650744848 | 200359730 | qid, pid, index | `81b9a4da076d517eb904338a20c6099dd1ce73874e65e4a65a7a2e253605ddbd` |
| `DataSet/T2Ranking/train.mined.tsv` | 5584965614 | 200376000 | qid, pid, index, score | `5b9ae93b7ab30050d1bdf0f37f3bc0d02d0b7e0289eecf92e41a203ef3063f03` |

## 语料质量

- 记录数：2303643
- 空 ID：0
- 重复 ID：0
- 空正文：0
- 规范化文本精确重复：10843（比例 0.004707）
- 字符长度分布：`{'count': 2303643, 'min': 0, 'p25': 193.0, 'p50': 341.0, 'p75': 706.0, 'p95': 1616.0, 'p99': 4605.0, 'max': 312861, 'mean': 591.0849979792876}`

## 查询与 qrels 关联

- 查询数：307704
- qrels 记录数：2877550
- 未知 query ID 记录：0
- 未知 document ID 记录：0
- 没有相关标注的查询：58666

## 安全样例

### DataSet/T2Ranking/collection.tsv

- `{'pid': '0', 'text': '找寄件人改号码'}`
- `{'pid': '1', 'text': '<br><img><br>凡是生过孩子的必会留下痕迹”,相信许多年轻妈咪对这句话感同身受。而产后肚子大就是女性生没生孩子的重要标志,今天我们讲了为什么女性生完孩子肚子还是很大的原因,也说了新妈妈们产后如何快速恢复肚子,让我们远离“妈妈肚”,生完孩子还是小姐姐。产后半年是恢复身材的关键时间,新妈妈时间这么紧,时间哪里找!!赶紧行动吧!!下一位辣妈就是你!!!zy(为什么产后肚子还很大?产后如何恢复肚'}`
- `{'pid': '2', 'text': '让产后妈妈最烦恼的是什么?不用多想肯定是产后如何恢复肚子,都说生育是女人的分水岭一点也不错,生完孩子后我的肚子一层一层的像千层糕一样叠在肚皮上,松松垮垮,穿什么衣服都走形,而且怎么减都减不掉,即使因怀孕而发胖的其他部分都在逐渐恢复,但凸起的肚子似乎没有任何动摇。为此老公还调侃我肚子里还有一个,平时出门也有嘴欠的说我“孩子还这么小,肚子里又揣了一个了!”有碎嘴的还会问我肚子里的几个月了。产后五个月,'}`

### DataSet/T2Ranking/info.md

- `test`

### DataSet/T2Ranking/qrels.dev.tsv

- `{'qid': '0', '-': '0', 'pid': '159474', 'rel': '3'}`
- `{'qid': '0', '-': '0', 'pid': '159475', 'rel': '3'}`
- `{'qid': '0', '-': '0', 'pid': '219110', 'rel': '2'}`

### DataSet/T2Ranking/qrels.retrieval.dev.tsv

- `{'qid': '0', 'pid': '159474'}`
- `{'qid': '0', 'pid': '159475'}`
- `{'qid': '0', 'pid': '219110'}`

### DataSet/T2Ranking/qrels.retrieval.train.tsv

- `{'qid': '50000', 'pid': '762244'}`
- `{'qid': '50000', 'pid': '762246'}`
- `{'qid': '50000', 'pid': '762247'}`

### DataSet/T2Ranking/qrels.train.tsv

- `{'qid': '50000', '-': '0', 'pid': '762239', 'rel': '0'}`
- `{'qid': '50000', '-': '0', 'pid': '762240', 'rel': '0'}`
- `{'qid': '50000', '-': '0', 'pid': '762241', 'rel': '0'}`

### DataSet/T2Ranking/queries.dev.tsv

- `{'qid': '0', 'text': '蜂巢取快递验证码摁错怎么办'}`
- `{'qid': '1', 'text': '生产过后怎么还有一层肚子'}`
- `{'qid': '2', 'text': '大学怎么网上选宿舍'}`

### DataSet/T2Ranking/queries.test.tsv

- `{'qid': '24996', 'text': '规划人员只能起到参谋的作用,他们不是决策者'}`
- `{'qid': '24997', 'text': '蹦迪夜店中的术语'}`
- `{'qid': '24998', 'text': '申请发展对象申请书'}`

### DataSet/T2Ranking/queries.train.tsv

- `{'qid': '50000', 'text': '鹦鹉吃自己的小鱼吗'}`
- `{'qid': '50001', 'text': '鹦鹉的生活习性是什么'}`
- `{'qid': '50002', 'text': '鹦鹉跳舞原因'}`

### DataSet/T2Ranking/train.bm25.tsv

- `{'qid': '50000', 'pid': '762244', 'index': '1'}`
- `{'qid': '50000', 'pid': '2163684', 'index': '2'}`
- `{'qid': '50000', 'pid': '762245', 'index': '3'}`

### DataSet/T2Ranking/train.mined.tsv

- `{'qid': '50000', 'pid': '762244', 'index': '1', 'score': '346.6772'}`
- `{'qid': '50000', 'pid': '762246', 'index': '2', 'score': '346.36865'}`
- `{'qid': '50000', 'pid': '762245', 'index': '3', 'score': '344.22745'}`

流水线仅以只读方式访问 `DataSet/T2Ranking`，未向该目录写入文件。
