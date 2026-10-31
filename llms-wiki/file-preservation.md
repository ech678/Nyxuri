# File Preservation — 判定权归账本，三层机制各司其职

> 跨部署保留用户文件 = **一条判定规则**（#139，所有权 carry）+ **三层实现机制**
> （Dunder / manifest preserve / preserve_values，刻意不合并）。规则的判定权在
> 账本基线，机制的实现各守其位——后人勿把三者"统一"进任何一方。
> 源码：`nyxuri/deploy/atomic.py`（`atomic_replace_item`）。

## 判定规则（#139）：swap 永不销毁引擎解释不了的文件

目录交换组装 `tmp_new` 时，dest 里每个文件按序过三道判据，全部只读现成数据：

1. **名字含 `__custom__`** → 用户的（Dunder walk，机制 1）
2. **在 manifest `preserve` 列表** → 运行时管的（机制 2）
3. **其余文件对照账本基线**（该插件 ledger `files`，即引擎上次铺设的哈希）——
   **领地按账本划，不按 payload 划**：
   - 基线有此路径 + dest == 基线 + 这次 payload 也不含 → 引擎这次不再铺设
     （钩子产物正是此类）→ **随 swap 消失，钩子重放重铺**（KM3 语义恢复：
     产物受管、off 抹白）
   - 基线有此路径 + dest == 基线 + payload 含 → **用新模板**（这才是"更新"）
   - dest == 新模板内容 → 已是目标态，无事可做
   - 基线有此路径但 dest != 基线 → **用户改过 → 原样搬入**（报"你的改动"）
   - 基线没有此路径 → 用户自放 → **原样搬入**（报"用户文件"）
   - 整插件无账本记录（Ghost）→ 来源不明 → update 立场**原样搬入**
     （报"来源不明"，宁可错保）；install/`on` 是收编立场，payload 名字归引擎

`__pycache__` 与 `*.pyc` 在两侧 walk 一律剪除——字节码缓存既非模板产物亦非用户
内容，不搬、不进报告（#139 实机报告定案）。

两条不变式：
- **账本只记引擎铺设的模板产物**，搬入的文件永不入账——否则下次部署会把它当
  "引擎铺设过且未被动过"的文件覆盖掉，账本自吞用户数据（详见 plugin-model.md §3）。
- **所有权只经 `on` 增长**。`update` 永不把新路径登记为受管；`update --force`
  是唯一的"模板优先"动词（payload 名字全部采纳 + 重登记清账），但它不是清剿——
  用户自放文件在 force 下照样搬入。

零交互是刻意的：宁可错保，不可错删；报告按判定分组全量交底（受保护文件 /
你的改动 / 用户文件 / 来源不明各自成节），不做中途确认弹窗。Ghost 插件由
update 报告逐插件提示 `nyxuri on <plugin>` 收编。

## 机制 1：Dunder `__custom__`（模板预留槽的命名约定）

`atomic_replace_item` 在 swap 前扫描 **dest** 里所有名字含 `__custom__` 的文件和目录
（任意深度），把它们的当前内容继承进新部署的 tmp 目录。与 src 是哪个形态**无关**——
不管切到 transparent 还是 default，dest 里的 `__custom__` 都原样保留。
`preserve_custom=False` 是回滚的精确恢复模式，不继承当前配置的自定义内容。

Dunder 的新定位（#139 之后）：**只有模板 include 链按名引用的槽位才需要它**
（如 `input__custom__.kdl` 被 `config.kdl` 引用）。用户**自放的文件不再需要任何后缀**——
账本自动认领为未登记内容。保留与加载解耦不变：引擎只管"保留"，应用各自"加载"
（多文件模块化在主自定义文件里再 `include` 即可）。

test_mode 下跳过 `scratchpad-items__custom__.toml` 和 `orbit-items__custom__.toml`
（test_deploy 的 idempotent 场景）。

## 机制 2：manifest preserve（运行时状态豁免）

`preserve` 的真实语义不是"保留用户文件"，而是**drift 信号豁免**：声明"这个路径的内容
变化不由模板/用户负责，由运行时（脚本、应用自己）管理"——不进账本快照、swap 时从
dest 原样注入（rename 前，inotify 看到的就是最终态，无半态窗口）。典型：
`effects.kdl → effects_normal.kdl/effects_eyecare.kdl` 脚本软链（链接本身保留不解引用）。

条目可以是**目录**（#139 实机报告定案）：整树归运行时管理，部署前整目录注入、
off 进 Vault、目录下所有文件经前缀匹配不入账、不参与 Drifted、不进搬运报告——
整个目录只报一行。典型：fish 的 `functions/`（Fisher 插件领地，模板完全不铺设）。
**禁令**：preserve 目录不得混铺模板 payload——声明即承诺"模板不在此目录铺设任何
文件"，混居会把 payload 永久冻结在旧版（`completions/`、`conf.d/` 正因此不可
preserve，其中 Fisher 的文件继续按 carry 用户文件处理：保护正确，标注近似）。

niri 的 `monitor.kdl` 曾因"被 `config.kdl` 按名引用、不能改名"而走 preserve；
#139 之后它由账本基线判定（没动过 → 跟随模板更新，修掉了 preserve 永久冻结模板
改进的暗病；动过 → gate 提示）。按名引用不再是 preserve 的理由，只有**运行时写它**
才是。例外靠 manifest 声明，不散落代码。

> **竞态消除**：旧实现先 rename 整目录、再事后拷回 monitor.kdl，Niri 的 inotify 会在
> 恢复前读到仓库默认的空 monitor.kdl 导致闪屏。注入在 rename 前完成，看到的就是最终态。

按键级豁免 `preserve_values`：文件级 preserve 的同族扩展，声明形如
`preserve_values = { "noctalia-config.toml" = ["enable_ddcutil"] }`。换入新目录前从旧文件
按段读出这些键的原始写法写进暂存新文件，再整体 rename。键按所在段匹配，旧文件里没有的
键不携带（沿用新模板值），路径越界检查与 preserve 走同一套。preserve_values 目标
**豁免于 carry**（键级机制比整文件搬运更精确，优先级更高）。

## 为什么三套实现不合并

| | Dunder | preserve | carry 判定 |
|---|---|---|---|
| 触发 | 魔法文件名 | 显式声明 | 账本基线比对 |
| 谁的 | 设计预期用户填的槽位 | 运行时（脚本/应用）写的 | 引擎铺设之外的一切 |
| 入账 | 否 | 否 | 只记引擎铺设侧 |

三套服务三种真实来源（模板预留槽 / 运行时状态 / 用户心血），实现各守其位；
统一会互相破坏（Dunder 改名破坏 include、preserve 入账会把脚本切换误报成漂移、
carry 吞掉按名保留）。

## 模板冻结（安全代价）

仓库 ship 的 `__custom__` 模板（`__custom__.kdl`、`__custom__.conf` 等）纯注释，第一次部署
进用户家后被 Dunder 当用户文件保留——开发者后续改进模板内容**到不了已安装用户**。这是
"一旦用户可能改过就不碰"的安全代价。因为模板只有注释无生效配置，冻结的只是注释 wording，
不影响功能。同理，carry 使"用户改过的受管文件"停止跟随模板（改进需 `--force` 或 off/on
采纳）——诚实的代价：引擎不假装会合并配置。

## 存储路径与命名边界

Nyxuri 元数据只许在 `~/.config/nyxuri/`（backups、用户形态、hooks）。
`~/.config/<app>/` 里不塞 Nyxuri 自己的东西——`__custom__` 是约定保留名，属 app 配置一部分，
不算"拉屎"。`manifest.toml` 是仓库元数据，deploy 时被 `_deploy_ignore_factory` 跳过，不进 dest。

## 动词语义表（谁传什么立场）

| 调用方 | carry | 基线 | unknown 立场 |
|---|---|---|---|
| `update`（普通） | ✓ | 账本 | True（宁可错保，Ghost 冻结 + 提示） |
| `update --force` | ✓ | 无 | False（模板认领 payload 名，自放文件仍搬入） |
| `install` / `on` | ✓ | 账本 | False（收编：payload 名归引擎，自放文件搬入） |
| `nyxuri test` | ✓ | 账本 | False（"对齐仓库"语义，含硬件中立清洗） |
| 形态切换（整型轴 / 槽位轴）/ 回滚 | ✗ | — | 原样模板替换（显式选择/精确还原；回滚另传 `preserve_custom=False`） |

原语默认 `carry=False`：裸调用保持纯模板替换语义，工作流显式选择立场。
