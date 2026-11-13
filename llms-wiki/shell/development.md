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

资源探针只在一次性隔离容器内运行。它把 `/proc` 进程树采样与 QML/JS 静态资源
清单分开记录；宿主机不要直接调用 Shell、`qs`、Weston 或其它桌面入口。容器内的
入口示例（`/workspace` 为只读仓库挂载，`/results` 为独立结果挂载）：

```bash
python3 /workspace/shell/scripts/dev/resource_probe.py \
  --pid "$SHELL_PID" --qml-root /workspace/shell --samples 6 --interval 1 \
  --output /results/resource-probe.json
python3 /workspace/shell/scripts/dev/resource_report.py \
  /results/resource-probe.json --output /results/resource-report
```

`resource-probe.json` 的 `runtime.samples` 是容器内实时观察（RSS/PSS/Private、进程、
线程、fd、CPU ticks、page fault、I/O 和 cgroup memory）；`static_qml` 仅是源码计数，
不能替代 Loader/Timer/Process 的运行态证据。`resource-summary.json` 保留首末样本与
增量，缺失值为 `null`，不会伪装成零；`resource-summary.md` 供人工审阅。长稳态和
100 次开关循环应在同一容器中多次调用探针，并保留原始 JSON 与日志。

### 2. 容器内启动与 IPC 交互

性能调查期间不在宿主桌面启动调试实例。以下命令仅在私有 Wayland/D-Bus 容器会话内执行：

```bash
# 隔离前台启动（详细日志流，自动挂载 fallback QML 桩）
shell/nyxuri-shell -v

# 观察实时日志流（另一终端）
qs log --path ./shell --follow

# 检查当前暴露的 IPC 接口
qs ipc --path ./shell show

# 向调试实例派发动作（观察面板弹起与按需析构）
qs ipc --path ./shell call power-menu toggle
qs ipc --path ./shell call spotlight toggle
qs ipc --path ./shell call lock open

# 结束调试实例
qs kill --path ./shell
```

### 3. 用户实机验收：双 Shell 切换

以下操作改变当前桌面，仅供用户主动验收时执行。自动性能调查不得在宿主执行：

```bash
# 检查当前双轨状态
nyxuri shell status

# 平滑切换至 Nyxuri Shell（停止旧端 -> 启动新端 -> 3.0s 探测就绪 -> 失败回滚）
nyxuri shell set custom "$PWD/shell/nyxuri-shell"
nyxuri shell switch nyxuri-shell

# 验证六大标准动作（快捷键或命令行）
nyxuri-shell --action session        # 呼出会话菜单
nyxuri-shell --action launcher       # 呼出应用搜索
nyxuri-shell --action lock           # 锁屏

# 随时一键平滑切回 Noctalia
nyxuri shell switch noctalia
```

## 性能基准

宿主只编排 Podman，不启动图形进程：

```bash
python3 shell/scripts/dev/benchmark-shell.py \
  --runs 10 --ipc-runs 20 --steady-seconds 600 --reclaim-cycles 100 \
  --profile default-full --output /tmp/nyxuri-benchmark
```

runner 使用 Sway headless/pixman；默认 Bar 需要 layer-shell，Weston headless 不能代替这项验证。代码只读挂载，HOME、XDG、Wayland 和 D-Bus 均在容器内隔离。热启动仍经过生产 wrapper，并复用 run-0 的预热缓存；不再绕过 wrapper 直接调用 `qs`。源码静态计数、已登记对象的 live census 和 `/proc` 采样必须分开报告。

## 日常开发循环

每轮回答：现在什么能用，这一轮证明什么，失败回到哪里。

1. 查看工作区与 `git status`，确认基线绿再动工。
2. 选择一个功能域，遵守 `shell.qml`、`commons/`、`ui/`、`services/`、`plugins/` 五层结构；插件的 `manifest.toml` 与代码同目录（参见 [架构边界矩阵](architecture-matrix.md)）。
3. 修改 QML/JS，按影响选择定向测试；真实启动和预览仅在第 2 节的隔离容器中进行。
4. 维护全树清晰度，更新 ROADMAP 与对应 Wiki。

## 国际化与字典更新

Nyxuri Shell 采用纯净 TOML 字典组织多语言文案，免去臃肿 XML 困扰：

```bash
# 扫描源码并生成语言包（TS 输出仅作审阅，运行时只读 TOML 词典）
python3 shell/scripts/dev/compile-i18n.py \
  --input-dir shell/commons/i18n --output-dir /tmp/nyxuri-i18n
```

## 调试层次与检查

| 改动/问题 | 调试方式 | 注意 |
| --- | --- | --- |
| QML 布局/动画/文案 | 真实 Niri 预览、日志、保存热重载 | 对照上游几何与动画；只格式化改动文件 |
| 跨层引用/边界违规 | `audit-lifecycle.py --check` | 严禁 shared 层包含副作用，严禁 units 交叉越界 |
| Niri IPC 与通信 | `test_display_preview.py` / `NiriDriver.qml` | 必须通过 `CompositorDriver` → `NiriDriver` 单一运行时入口，禁止直接连接底层 Socket（`niri` argv 字面量仅许存在于 `NiriDriver.qml`；配置域 Python 工具 `niri_config.py`/`display_preview.py` 为登记例外） |
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
