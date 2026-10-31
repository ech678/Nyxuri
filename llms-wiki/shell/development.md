# Nyxuri Shell — 开发与调试指南

## 当前架构与调试入口

Nyxuri Shell 现已完成全面去 C++ 化与架构收敛（R4-C），整体为 **纯 QML / JavaScript / 外部轻量脚本** 架构，零 CMake / 零 C++ 编译依赖，启动与开发极小、极快、可解释。
统一运行入口位于 `shell/nyxuri-shell`（与 `shell.qml` 并列位于根目录）。

日常调试支持三层递进方式，兼顾极速验证与真实会话测试：

### 1. 自动化秒级校验（无图形会话，零副作用）

```bash
# 语法与编译检查
python3 -m compileall nyxuri tests shell/scripts

# 全量契约测试集（零依赖秒级回归）
python3 -m unittest discover -s tests -q

# R5 分类测试套件（按 5 大分类独立执行与输出成绩单）
python3 shell/scripts/dev/run-tests.py --all

# 生命周期与架构矩阵静态审计（0 违规约束）
python3 shell/scripts/dev/audit-lifecycle.py --root shell --scope all --check
```

### 2. 独立进程预览与 IPC 交互

独立进程不等于独立桌面：直接运行会使用当前用户配置、写入主题模板和 Noctalia 色板，
还会参与通知服务注册。当前运行 Noctalia 时，先用临时 HOME/XDG 目录和私有 D-Bus 会话
隔离这些写入与服务；Wayland 和 Niri 仍是当前桌面，面板占位、窗口和用户触发的桌面动作仍可见。

```bash
# 从仓库根目录启动预览；保留真实 XDG_RUNTIME_DIR 以连接当前 Wayland
preview_root=$(mktemp -d /tmp/nyxuri-shell-preview.XXXXXX)
env HOME="$preview_root" \
    XDG_CONFIG_HOME="$preview_root/.config" XDG_DATA_HOME="$preview_root/.local/share" \
    XDG_STATE_HOME="$preview_root/.local/state" XDG_CACHE_HOME="$preview_root/.cache" \
    NYXURI_SHELL_RUNTIME_HOME="$preview_root/runtime" \
    dbus-run-session -- shell/nyxuri-shell -v

# 观察实时日志流（另一终端）
qs log --path ./shell --follow

# 检查当前暴露的 IPC 接口
qs ipc --path ./shell show

# 向调试实例派发动作（观察面板弹起与按需析构）
qs ipc --path ./shell call power-menu toggle
qs ipc --path ./shell call spotlight toggle

# 结束调试实例
qs kill --path ./shell
```

预览前检查没有同路径的 Nyxuri Shell 实例：wrapper 使用 `--no-duplicate`，重复调用会复用
现有实例。上例未覆盖主动设置的 `NYXURI_SHELL_*` 路径变量，若会话设置过这些变量，先核对
并将它们指向临时目录。锁屏单独人工验收，确认 PAM 认证与恢复手段后再执行 `lock open`。

wrapper 使用 Qt 官方支持的 [QML_DISK_CACHE_PATH](https://doc.qt.io/qt-6.10/qmldiskcache.html)
把编译缓存放入 `<用户缓存根>/nyxuri-shell/quickshell/qmlcache`，不更改 `XDG_CACHE_HOME`。
派生的 Python 引擎 API、CLI 和外部工具继承真实用户目录；不靠特殊标记绕过引擎的布局校验。
wrapper 只在真实启动路径（含锁屏补启动）清空这个专属 QML 缓存；`--status`、`--check-ready`、
普通 `--ipc` 和 `--stop` 不清缓存。`shell isReady` 只表示宿主 IPC 阶段已到达，不能代替
单元装载、Niri 连接、视觉及认证验收；结合 `shell diagnostics`、`shell log` 和实际窗口检查。

剪贴板和系统监测的工具后端是独立的 `key-cli`（默认命令 `key`，也可由
`NYXURI_KEY` 指向实际绝对路径），不在本仓库中；这项供给边界见
[已知问题](../../shell/KNOWN-ISSUES.md)。`wl-copy`、`wl-paste`、`cliphist` 可用
不能代替 `key clipboard` 的 JSON 接口，系统监测还要求 `key sysmon stream`。
后端未返回合法探测结果时，剪贴板依赖在诊断中为 `probed=false`、设置页显示 `?`，
不能把默认值误报为三个工具均未安装。启动失败可从 `shell log` 和 `qs log` 读取，
默认持久日志为 `~/.local/state/nyxuri/logs/shell.log`；设置了
`NYXURI_SHELL_STATE_HOME` 时使用覆盖路径。缺少这个外部可选后端时只降级相应能力，
Shell 的其他功能仍可使用。

### 3. 真实会话双 Shell 平滑热切换（全桌面接管与即时切回）

通过 Python 状态机实现有界探测与自动回滚安全接管：

```bash
# 检查当前双轨状态
nyxuri shell status

# 先确认仓库自带 wrapper 需要的运行时已在 PATH
command -v qs
qs --version

# 平滑切换（停止旧端 -> 启动新端 -> 按目标预算探测就绪 -> 失败回滚）
nyxuri shell switch nyxuri-shell "$PWD/shell/nyxuri-shell"

# 验证六大标准动作（快捷键或命令行）
nyxuri-shell --action session        # 呼出会话菜单
nyxuri-shell --action launcher       # 呼出应用搜索
nyxuri-shell --action lock           # 锁屏

# 随时一键平滑切回 Noctalia
nyxuri shell switch noctalia
```

`shell set` 与 `shell switch` 使用同一切换流程：有 `WAYLAND_DISPLAY` 时都会立即切换，
没有 Wayland 会话时才只记录偏好。不要用 `set` 登记路径后再执行一次 `switch`。
切换前先验证入口及其 `--runtime-path` 查询返回的实际 `qs` executable，再按
`catalog.toml` 的 Quickshell 平台声明检查依赖及两套 Material Symbols 字体。
入口需属于含 `shell.qml` 的 Shell 目录，并支持该查询；不能把任意可执行文件
登记为已就绪的 Nyxuri Shell。wrapper 的查询、IPC 与实际启动使用同一运行时路径。

预检随后用真实 `qs -p <临时目录>` 加载无窗口的外部 QML 导入探针，导入范围来自
`shell.qml` 与 app、units、shared，包含预热代码的必需模块和 M3Shapes。探针使用
临时 HOME/XDG、离屏 Qt 平台及不可连接的会话 bus；不会实例化现有 app 或业务域。
只有 FileView 写出明确的组件完成标记才通过，日志中的源码文字不能作为就绪证据。
导入探针最多等待 8 秒，结束后回收其独立进程组；缺运行时、依赖、字体、QML 或
超时均在停止旧实例之前返回失败。此预检证明基础加载能力，真实业务行为及视觉仍需
会话验收。实际启动后的就绪预算为 Nyxuri Shell 4 秒、Noctalia 30 秒；Noctalia 的
D-Bus 服务初始化可能等待单次约 25 秒，预算另留启动余量。失败回滚
恢复旧 Shell 时使用它自己的同一预算。只有真实 IPC 回应才算就绪，进程存活不能
代替就绪探测。
等待使用单调时钟；每次 IPC 超时及轮询间隔都不超过总预算剩余时间，预算耗尽
明确返回失败。切换及回滚报告显示实际采用的预算。

`--runtime-path` 纯查询及所有预检不清理现有 Shell 的缓存。wrapper 的 IPC 与启动
使用该查询解析出的同一个 `qs`；独立的 Orbit 工具不要求 Quickshell。

## 日常开发循环

每轮回答：现在什么能用，这一轮证明什么，失败回到哪里。

1. 查看工作区与 `git status`，确认基线绿再动工。
2. 选择一个功能域，遵守 `app/`、`units/`、`shared/` 三层分层契约（一单元一目录，`manifest.toml` 与代码同目录）（参见 [架构边界矩阵](architecture-matrix.md)）。
3. 修改 QML/JS，通过 `run-tests.py` 本地验证；必要时拉起 Tier 2 隔离进程预览视觉。
4. 维护全树清晰度，更新 ROADMAP 与对应 Wiki。

## 国际化与字典更新

Nyxuri Shell 采用纯净 TOML 字典组织多语言文案，免去臃肿 XML 困扰：

```bash
# 扫描源码并生成语言包（TS 输出仅作审阅，运行时只读 TOML 词典）
python3 shell/scripts/dev/compile-i18n.py \
  --input-dir shell/app/i18n --output-dir /tmp/nyxuri-i18n
```

## 调试层次与检查

| 改动/问题 | 调试方式 | 注意 |
| --- | --- | --- |
| QML 布局/动画/文案 | 真实 Niri 预览、日志、保存热重载 | 对照上游几何与动画；只格式化改动文件 |
| 跨层引用/边界违规 | `audit-lifecycle.py --check` | 严禁 shared 层包含副作用，严禁 units 交叉越界 |
| Niri IPC 与通信 | `test_display_preview.py` / `NiriService.qml` | 必须通过单一运行时入口 NiriService，禁止直接连接底层 Socket |
| 后台/关闭/切换 | 完整退出/重启、进程与连接观察 | 退出限时 2.5s 优雅终止，停用必须真实销毁 Process / Timer |
| 锁屏/多屏/通知 | 真实原版 Niri 会话验收 | 遵循 Wayland 安全锁屏与会话互斥契约 |
| 宿主命令/部署 | TempEnv 行为测试、参数数组断言、沙箱部署 | 不写真实 ~/.config，不通过源码字面匹配冒充行为测试 |

## 生命周期与副作用治理规范

为保障 Shell 在长时间运行和高频开关下的秩序感与整洁度，所有 QML/JS 资源必须遵守生命周期与副作用治理契约：

| 代号 | 检查项 | 治理契约与修复要求 |
|---|---|---|
| `ARCH001` | 分层边界违规 | 必须遵循 app -> units -> shared 单向依赖，shared 绝对纯净 |
| `LIFE001` | 缺少 owner 声明 | `ActionGateway.execute(args, owner)` 必须传入非空 owner 标识 |
| `LIFE002` | 缺少销毁/清理路径 | 创建 Process、网络请求、长期订阅、周期 Timer 的组件必须具备释放钩子 |
| `LIFE003` | shared 层副作用 | `shared/` 严禁 Process、FileView、XMLHttpRequest、环境读取及业务服务引用 |
| `LIFE004` | 直接外部命令执行 | `app/` 与 `units/` 严禁直接调用 `Quickshell.execDetached`，必须走 `ActionGateway` |
| `LIFE005` | 可选依赖无降级 | 可选插件导入必须经由 fallback 隔离层，缺失时不崩溃、有降级提示 |
| `LIFE006` | 仅通过 visible 隐藏 | 弹窗与面板停用时必须真实卸载或断开流（`active: false`），禁止仅用 `visible: false` |
| `LIFE007` | 事件循环空转 | 禁止 `Timer interval: 0` 隐式空转；帧级批处理统一走 `Qt.callLater` |
| `LIFE008` | UI 层直接 I/O | `units/` 视图与 `app/` 顶层文件禁止持有 `FileView`/`Process`；I/O 归 `*Service/*Config/*Backend/*State/*Catalog` 域文件或显式 allowlist，用户意图经 `ActionGateway` 派发 |

```bash
# 一键静态与生命周期集成检查
./shell/scripts/dev/check.sh
