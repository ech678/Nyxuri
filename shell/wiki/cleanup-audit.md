# Nyxuri Shell 净化审计

本页是 2026-10-03 对 `shell/` 的只读审计记录。它记录当前事实、问题位置和建议动作；不把文件存在、字符串扫描或历史测试数字当作行为完成证据。本轮只允许修改本页与 [路线图](../ROADMAP.md)。

## 基线事实

扫描范围排除 `shell/build/` 和 `shell/references/` 的运行内容，但保留它们作为仓库结构问题记录：

| 项目 | 当前事实 |
| --- | --- |
| 非构建/参考的 Git 文件 | 860 |
| 运行树顶层文件分布 | `app` 66、`modules` 363、`shared` 95、`native` 151 |
| 含旧品牌/上游标识的文件 | 55 |
| `Clavis`/`clavis`/`CLAVIS` 等命中 | 2733 处（含文档、兼容代码与生成数据） |
| TODO/FIXME/HACK/WIP/legacy 等标记 | 46 处 |
| 生成/缓存/qmldir/pyc 等命名命中 | 15 处 |
| 当前工作区源码、配置、资源变更 | 无 |

数字是审计时的索引，不是后续验收目标；每次执行具体任务时必须重新生成。

## P0：阻断级问题

### P0-01 路线图状态与证据不一致

- 位置：`ROADMAP.md` 的 P1/P2/P3 历史完成项、P3-R08/R10/R13、P3-R09 门禁。
- 问题：同一文档同时声称 P3 第一阶段、生命周期治理和“全工程优雅化”完成，又明确写着按需启动、视觉验收、环境证据和 P3 收口未完成；测试数字出现 478、480、497、501、544、23、21 等多个版本，无法判断对应源码。
- 建议：历史交付改为“历史记录”；当前状态只保留可复现证据。统一采用“通过/跳过/环境阻断/产品失败/未验证”五态，完成项必须绑定命令、环境、提交或日志。

### P0-02 核心装配仍包含高成本宿主

- 位置：`app/AppShell.qml` 的 `WallpaperBackground`、`DesktopCardHost`、`DockHost`、`Keystone`、`SidebarHostWindow`、`Lock`、`SettingsHost` 等顶层实例。
- 问题：当前装配与 `P3-R09-01` 的“核心启动闭包”目标冲突；`visible: false` 或内部降级不能证明未创建后台、窗口、监听器或 native consumer。
- 建议：先生成真实消费者矩阵，再将可选宿主改为按需 Loader/显式生命周期；把冷启动、首帧、IPC ready 和专属资源作为验收证据。

### P0-03 运行标识没有完成 Nyxuri 收口

- 位置：`CMakeLists.txt`、`native/`、`app/Paths.qml`、`bin/nyxuri-shell`、`scripts/system/niri-actions.json`、`assets/i18n/clavis_*.ts`、fallback `Clavis/*` qmldir，以及 55 个命中文件。
- 问题：内部 module、安装目录、变量、配置目录、脚本动作和翻译仍混用 Clavis；兼容变量与产品内部标识没有边界或弃用期限。
- 建议：建立公开接口/迁移兼容/内部实现三层清单；作者拍板兼容保留期后，按依赖图统一重命名，最后删除无消费者兼容分支。

## P1：高优先级问题

### P1-01 目录边界与实际依赖需要重新核对

- 位置：`app/services/`、`modules/*/backend`、`shared/utils`、`native/fallback`、`native/plugin/*`。
- 问题：四层原则已经写入契约，但服务文件、模块专属 backend、fallback 和生成目录的归属标准不够明确；`app` 可能承担业务执行，`shared`/模块之间仍可能通过上下文 singleton 取值。
- 建议：以依赖图为准制定目录迁移表；每个文件记录 owner、输入、输出、副作用和允许 import，迁移完成后删除旧路径，不保留并行实现。

### P1-02 可选 native 和外部依赖的隔离证据不足

- 位置：`native/CMakeLists.txt`、`native/plugin/*`、`native/fallback/Clavis/*`、天气/歌词/Cava/MapLibre/window preview 相关目录。
- 问题：fallback、插件和构建 target 仍携带母体命名；“可选”与“核心加载闭包”的边界需要从 CMake、静态 import 和运行时实例化三处同时证明。
- 建议：为每个插件建立消费者、构建依赖、静态 import、失败降级和删除条件表；核心配置不得因缺失可选库而 configure 或启动失败。

### P0-04 Nyxuri 自有 C++ 仍是主要架构负担

- 参考：`shell/references/iNiR` 的项目树没有 C++ 源码，桌面业务主要由 QML/JavaScript、Quickshell 模块和外部脚本组成。
- 位置：`native/src/`、`native/plugin/`、`native/fallback/`、`native/tests/`、`native/tools/` 及其 CMake 安装入口。
- 问题：当前 Nyxuri 自有 C++ 覆盖 Niri IPC/模型、天气、媒体/频谱、文件/图标、亮度/udev、Gamma、窗口预览和测试；“可选插件解耦”仍保留较大的 native 体系，和用户希望的全面去 C++ 方向不一致。
- 建议：新增独立迁移主线，先迁纯算法和数据整形，再迁 IPC/文件/设备边界；优先使用 Quickshell 内置模块、QML/JS、`Process`/文件接口和外部工具。每项必须记录替代方案、行为差异和删除条件，最终移除 Nyxuri 自有 C++ target、fallback、native CTest 与安装元数据。
- 边界：不把 Quickshell、Wayland、Niri 或系统服务内部的原生实现算作 Nyxuri C++；若某项能力确实无法替代，必须单独记录“保留最小原生桥/删除功能/阻断”的决策，不能用空插件伪装完成。

### P1-03 兼容路径、环境变量和安装元数据重复

- 位置：`app/Paths.qml`、`bin/nyxuri-shell`、`scripts/lib/*`、`CMakeLists.txt`、`packaging/*`。
- 问题：`NYXURI_*` 与 `CLAVIS_*` 双向解析、旧配置路径和多个 build 搜索路径并存；CMake 安装目录仍使用 Clavis 名称，导致来源、开发树和安装树可能加载不同资源。
- 建议：确定唯一 Nyxuri 路径；兼容读取集中到一个迁移层并记录弃用期限，禁止业务文件直接读取旧变量；安装、源码运行和测试运行使用同一资源解析契约。

### P1-04 上游参考资料与运行文档边界不够清楚

- 位置：`wiki/upstream-docs/`、`wiki/upstream-licenses/`、`README.md`、`AGENTS.md`、`wiki/audit.md`。
- 问题：参考文档仍包含上游安装、软链、key-cli、旧配置和旧品牌内容，读者可能误把它们当作 Nyxuri 操作契约。
- 建议：参考资料统一加“仅供比对/不可执行”的索引和醒目标记；作者拍板长期保留完整上游文档还是压缩为许可证、来源和恢复所需最小资料。

### P1-05 生成物、缓存与 vendor 的仓库策略未统一

- 位置：`modules/settings/generated/SearchCatalog.js`、qsb shader、`scripts/**/__pycache__`、`tests/**/__pycache__`、`scripts/system/vendor/kdl`。
- 问题：生成文件、构建缓存、内嵌 vendor 和测试 fixture 混在同一资源树，未在文档中区分可审阅源文件、构建产物和第三方代码；构建树还存在历史产物痕迹。
- 建议：逐项决定“源码生成/提交生成结果/完全忽略”；vendor 记录版本、许可证、调用面和升级方式；清理策略必须不影响恢复和离线构建。

## P2：中优先级问题

### P2-01 命名与大小写风格仍不统一

- 位置：`modules/` 文件名大量 PascalCase，目录为小写；服务、backend、component、host、state、manager 后缀混用。
- 问题：同一层级的文件命名不能稳定推断职责，旧母体命名与 Nyxuri 新命名共存。
- 建议：冻结目录小写、QML 类型 PascalCase、纯数据/工具文件命名规则，并按域批量重命名；重命名必须同步 import、测试、文档和恢复矩阵。

### P2-02 注释、README 和路线图存在历史语气与重复契约

- 位置：`ROADMAP.md`、`AGENTS.md`、`README.md`、模块 README、脚本注释。
- 问题：设计原则、生命周期规则、上游来源和完成标准在多个文档重复，部分内容描述历史状态或未来目标，维护时容易互相漂移。
- 建议：`AGENTS.md` 只保留不变量，`ROADMAP.md` 只保留阶段和验收，`wiki/audit.md` 只保留事实，`wiki/development.md` 只保留工具；删除已失效注释，保留复杂边界的短说明。

### P2-03 直接副作用和生命周期检查需要从“静态通过”升级为行为证据

- 位置：所有 `Process`、`Timer`、`FileView`、网络、IPC 和 native consumer 使用点；`scripts/dev/audit-lifecycle.py`。
- 问题：现有审计器能拦截部分模式，但不能替代真实开关、取消、崩溃、SIGTERM、旧 generation 回调和资源稳态测试；路线图把静态 0 违规写成全面治理完成。
- 建议：保留静态门禁，另建按域的行为矩阵；完成项记录环境、重复次数、专属进程/连接/窗口和失败恢复结果。

### P2-04 资产和翻译需要重新做消费者盘点

- 位置：`assets/icons`、`assets/i18n`、`assets/shaders`、`assets/matugen`、天气资源和键盘图标。
- 问题：文件名和上游品牌仍可见，资源是否被运行代码引用、是否属于已封存模块、许可证是否随来源同步，当前文档没有一份可复核索引。
- 建议：生成资源消费者表，区分核心、可选、封存、第三方和死数据；删除前保留许可证和来源证据，避免仅按体积清理有效视觉资产。

### P2-05 测试目录和测试命名没有体现契约边界

- 位置：`tests/`、`native/tests/`、`tests/qml/`、fixture 目录。
- 问题：行为测试、静态审计 fixture、环境依赖测试和上游兼容测试混在一起；测试数量随生成/环境变化，路线图引用的总数无法作为稳定指标。
- 建议：按纯逻辑、运行时资源、native、图形环境和静态规则分组；测试报告记录分组结果，不再用单一总数代表完成。

## P3：低优先级整理

- 清除已确认无消费者的空目录、重复路径 helper 和旧脚本别名。
- 统一 Shell/Python/QML 的错误输出、日志前缀和帮助文本，避免同时出现 Clavis/Nyxuri。
- 为第三方 vendor、shader、图标和翻译补齐来源、版本、许可证和更新责任人。
- 为每个模块 README 选择保留、合并到 wiki 或删除，避免“代码旁边的旧说明”成为第二真值源。
- 统一换行、格式化工具版本和格式化范围；格式化变更必须单独提交，不能混入行为迁移。

## 需作者拍板

1. 是否彻底移除内部 `Clavis` 标识，还是保留一个明确期限的兼容迁移层。
2. `references/` 和 `wiki/upstream-*` 是长期恢复资料，还是压缩为最小来源/许可证档案。
3. 是否继续保留完整 Keystone、天气、地图、歌词等能力，还是按核心 Shell 与可选模块重新划界。
4. 生成文件、qsb、vendor Python 包和测试 fixture 的版本控制策略。
5. 对外 IPC、脚本命令、配置路径和旧环境变量的兼容期限。

## 建议执行顺序

1. 先修正路线图状态和验证数字，冻结本审计基线。
2. 决定品牌/兼容策略，再迁移 CMake、QML module、路径和脚本标识。
3. 画出启动闭包与依赖图，拆分可选 native 和高成本宿主。
4. 按功能域处理目录、命名、生命周期和副作用，边迁移边补行为证据。
5. 最后清理资源、vendor、生成物和上游文档，并做全树链接/构建/测试收口。
