# 文档宪章 (Docs Charter)

> 本页是全库文档体系的唯一规则源：真值拓扑、生命周期、文档类型、命名与链接门禁。
> 文风与措辞见 [writing-voice](writing-voice.md)，本页只管结构与流程；规则变更先改本页，再让门禁跟上。

## 真值拓扑

| 层 | 内容 | 位置 | 维护义务 |
| --- | --- | --- | --- |
| L0 | 运行与测试事实 | 源码（`nyxuri/` `configs/` `shell/`）+ `tests/` | 唯一事实。文档引用它，永远不是相反 |
| L1 | 行为契约与改动路由 | `AGENTS.md`（根 + `shell/`） | 常驻保鲜；根 AGENTS ≤150 行（测试门禁） |
| L2 | 架构知识与演进状态 | `llms-wiki/`（除 `upstream/` `archive/`）+ 双层 `ROADMAP.md` | 活区。受链接与索引门禁约束 |
| L3 | 外部参考与历史 | `llms-wiki/upstream/`、`llms-wiki/archive/`、`notes/` | 冻结。只进不改，豁免一切链接与内容维护 |

**单一权威规则**：每个事实有且仅有一个权威层，其余位置只链接、不复述。
状态只在 ROADMAP；契约只在 wiki 与 AGENTS；历史只在 archive；notes 是免维护杂物堆。
两处独立维护同一事实即口径漂移，是本体系唯一的头号违例。

## 生命周期（自我熵减）

知识只向上沉淀，历史只向后冻结，活区面积有界：

1. **草稿**：`notes/`（gitignored 屎山，零义务）。随手写，不要求格式与标注；成熟前不进任何流程。
2. **晋升**：草稿成熟 → 从 notes/ 捞出一份，改写成 `llms-wiki` 契约页（进索引、进门禁）或直接删除；捞出的那份与 notes 再无关系。
3. **压缩**：ROADMAP 阶段完成 → 台账加一行；明细**追加**至 `archive/shell-roadmap-ledger.md`（追加式，不改旧行）。
4. **冻结**：时点审计、比对矩阵、历史方案 → 对应 `archive/`。除「会误导当前操作的入口断链」外不修不改。

## 文档类型与最小结构

- **契约页**（`llms-wiki/` 大多数页面）：不变量 + 原因 + 验收方式。首行必须有一句定位声明（`> 本页是…，以…为准`）。
- **指南页**（如 `shell/development.md`）：可执行步骤，命令可复制粘贴。
- **索引页**（`llms.txt`）：一行一条目 = 名称、相对路径、一句话职责。全库唯一。
- **台账行**（ROADMAP）：阶段、一句话交付、状态。状态词只用 `待开始` / `进行中` / `阻断` / `待验收` / `已完成`。
- **归档页**：文件头注明冻结日期与原位置；正文保持历史原貌，不追认现状。
- **生成物**（如 `shell/lifecycle-inventory.json`）：文件内注明生成器与再生成命令；不手改生成结果。

## 命名与链接

- 文件名 kebab-case；`llms-wiki/` 下子目录只作语义分区：`shell/`（Shell 活契约）、`upstream/`（外部参考）、`archive/`（历史）。不再增设第四个。
- 代码目录内的 README 只承担「本目录是什么 + 来源/许可证归属」，不承载契约；契约一律上收 `llms-wiki/` 并索引。
- 活区相对链接必须可解析；`upstream/`、`archive/`、`notes/` 豁免（历史数据不追改）。
- `llms.txt` 双向闭包：每个活页被索引，每个索引项存在（`tests/test_ai_specs.py` 门禁）。

## 门禁

```bash
# 文档契约（链接闭合 + 索引双向闭包 + AGENTS 行数 + CLI 命令映射）
python3 -m unittest tests/test_ai_specs.py

# 全量（含上述）
python3 -m unittest discover -s tests -q
```

改动文档时：改完跑上面第一条；改动架构契约、命令或 manifest 时，同步对应 wiki 页与 ROADMAP 台账（见根 AGENTS.md 路由表）。
