# File Preservation — Dunder + manifest preserve（两套刻意不合并）

> 跨部署保留用户文件有**两套机制**，服务不同场景，是双机制不是重复设计——后人勿"统一"。
> 源码：`nyxniri/deploy/atomic.py`。

## 机制 1：Dunder `__custom__`（按名通用 walk）

`atomic_replace_item` 在 swap 前扫描 **dest** 里所有名字含 `__custom__` 的文件和目录
（任意深度），把它们的当前内容继承进新部署的 tmp 目录。与 src 是哪个预设**无关**——
不管切到 transparent 还是 default，dest 里的 `__custom__` 都原样保留。
`preserve_custom=False` 是回滚的精确恢复模式，不继承当前配置的自定义内容

两步走（`atomic.py`）：
1. **Custom 文件**：`os.walk(dest)`，prune `__custom__` 目录不递归进文件搜索，逐个 `copy2`
   或保符号链接，打印 `log_keep_custom_file`。
2. **Custom 目录**：再 `os.walk`，遇 `__custom__` 目录 `rmtree` 目标 + `copytree` 整树，
   打印 `log_keep_custom_dir`。

test_mode 下跳过 `scratchpad-items__custom__.toml` 和 `orbit-items__custom__.toml`
（test_deploy 的 idempotent 场景）。

> **保留与加载解耦**：引擎只管“保留”（只要路径含 `__custom__` 就原子继承），应用各自“加载”（按各软件语法引入）。想要多文件模块化，直接在主自定义文件里再次 `include` 即可（例如在 `__custom__.kdl` 中写 `include "my_binds__custom__.kdl"`，子文件同样因包含 `__custom__` 享受更新保护）。

## 机制 2：manifest preserve（按声明注入）

`.module.toml` 的 `preserve = ["monitor.kdl", "effects.kdl"]` 声明要保留的文件（按**名**，不是魔法文件名）。
`atomic_replace_item` 接收 `preserve` 参数，在 copytree + Dunder walk 完成、**rename 之前**
把这些文件从 dest 复制进 tmp_new——swap 完成后 dest 即最终态，没有事后恢复窗口。
如果是符号链接（如 `effects.kdl` → `effects_normal.kdl`/`effects_eyecare.kdl` 编码的 EyeCare 开关状态），
会保留链接本身而不解引用，跨部署与跨预设切换完整继承。

为什么 niri 的 monitor.kdl / effects.kdl 走这套而不走 Dunder：monitor.kdl 被 `config.kdl` 的
`include "monitor.kdl"` **按名引用**，不能改名成 `monitor__custom__.kdl` 走 dunder；
effects.kdl 是脚本动态管理的软链接，同样需要固定文件名。例外靠 manifest 声明，不散落代码。

> **竞态消除**：旧实现先 rename 整目录、再事后拷回 monitor.kdl，Niri 的 inotify 会在恢复前
> 读到仓库默认的空 monitor.kdl 导致闪屏。现在注入在 rename 前完成，inotify 看到的就是最终态。

## 机制 3：预设底版继承（Base Overlay）

若当前部署的预设开启了继承，`atomic_replace_item` 接收可选的 `base_src`、`base_include` 与 `base_exclude` 参数：
1. **Base 拷贝与白黑名单过滤**：先将 `base_src` 拷贝至 `tmp_new`（应用 `base_include` 与 `base_exclude` 规则过滤）；
2. **Preset 覆盖**：将预设自身目录 `src` 覆盖拷贝至 `tmp_new`（`dirs_exist_ok=True`）；
3. **Dunder 保护**：扫描 `dest` 中的 `__custom__` 文件与目录并注入 `tmp_new`；
4. **Manifest 保护**：将 `preserve` 声明的文件（如 `monitor.kdl`、`effects.kdl`）从 `dest` 注入 `tmp_new`；
5. **原子对调**：`os.replace` 将组装完成的 `tmp_new` 替换至 `dest`。

## 为什么不合并

| | Dunder | manifest preserve |
|---|---|---|
| 触发 | 魔法文件名（含 `__custom__`） | 显式声明（`preserve = [...]`） |
| 谁的 | 用户自定义（任意内容） | 按名引用的固定文件（monitor.kdl） |
| walk 谁 | dest（不管 src） | dest（注入 tmp_new，rename 前） |

两套服务不同场景：一个是"用户随意改、按名通用保留"，一个是"固定文件按名保留"。合并会
逼用户把 monitor.kdl 改名才能保留，破坏 config.kdl 的 include——得不偿失。

## 模板冻结（安全代价）

仓库 ship 的 `__custom__` 模板（`__custom__.kdl`、`__custom__.conf` 等）纯注释，第一次部署
进用户家后被 Dunder 当用户文件保留——开发者后续改进模板内容**到不了已安装用户**。这是
"一旦用户可能改过就不碰"的安全代价。因为模板只有注释无生效配置，冻结的只是注释 wording，
不影响功能。

## 边界（§10.4）

NyxNiri 元数据只许在 `~/.config/NyxNiri/`（backups、presets、active 状态）。
`~/.config/<app>/` 里不塞 NyxNiri 自己的东西——`__custom__` 是约定保留名，属 app 配置一部分，
不算"拉屎"。`.module.toml` 是仓库元数据，deploy 时被 `_deploy_ignore_factory` 跳过，不进 dest。
