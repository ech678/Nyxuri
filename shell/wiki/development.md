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

### 2. 隔离进程预览与 IPC 交互（不影响当前运行的桌面会话）

当前运行 Noctalia 时，无需关闭桌面，可直接拉起独立 Nyxuri Shell 进程进行预览：

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

### 3. 真实会话双 Shell 平滑热切换（全桌面接管与即时切回）

通过 Python 状态机实现有界探测与自动回滚安全接管：

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

## 日常开发循环

每轮回答：现在什么能用，这一轮证明什么，失败回到哪里。

1. 查看工作区与 `git status`，确认基线绿再动工。
2. 选择一个功能域，遵守 `app/`、`modules/`、`shared/` 三层分层契约（参见 [架构边界矩阵](architecture-matrix.md)）。
3. 修改 QML/JS，通过 `run-tests.py` 本地验证；必要时拉起 Tier 2 隔离进程预览视觉。
4. 维护全树清晰度，更新 ROADMAP 与对应 Wiki。

## 国际化与字典更新

Nyxuri Shell 采用纯净 TOML 字典组织多语言文案，免去臃肿 XML 困扰：

```bash
# 扫描源码并生成/编译二进制语言包
python3 shell/scripts/dev/compile-i18n.py
```

## 调试层次与检查

| 改动/问题 | 调试方式 | 注意 |
| --- | --- | --- |
| QML 布局/动画/文案 | 真实 Niri 预览、日志、保存热重载 | 对照上游几何与动画；只格式化改动文件 |
| 跨层引用/边界违规 | `audit-lifecycle.py --check` | 严禁 shared 层包含副作用，严禁 modules 交叉越界 |
| Niri IPC 与通信 | `test_display_preview.py` / `NiriService.qml` | 必须通过单一运行时入口 NiriService，禁止直接连接底层 Socket |
| 后台/关闭/切换 | 完整退出/重启、进程与连接观察 | 退出限时 2.5s 优雅终止，停用必须真实销毁 Process / Timer |
| 锁屏/多屏/通知 | 真实原版 Niri 会话验收 | 遵循 Wayland 安全锁屏与会话互斥契约 |
| 宿主命令/部署 | TempEnv 行为测试、参数数组断言、沙箱部署 | 不写真实 ~/.config，不通过源码字面匹配冒充行为测试 |

## 生命周期与副作用治理规范

为保障 Shell 在长时间运行和高频开关下的秩序感与整洁度，所有 QML/JS 资源必须遵守生命周期与副作用治理契约：

| 代号 | 检查项 | 治理契约与修复要求 |
|---|---|---|
| `ARCH001` | 分层边界违规 | 必须遵循 app -> modules -> shared 单向依赖，shared 绝对纯净 |
| `LIFE001` | 缺少 owner 声明 | `ActionGateway.execute(args, owner)` 必须传入非空 owner 标识 |
| `LIFE002` | 缺少销毁/清理路径 | 创建 Process、网络请求、长期订阅、周期 Timer 的组件必须具备释放钩子 |
| `LIFE003` | shared 层副作用 | `shared/` 严禁 Process、FileView、XMLHttpRequest、环境读取及业务服务引用 |
| `LIFE004` | 直接外部命令执行 | `app/` 与 `modules/` 严禁直接调用 `Quickshell.execDetached`，必须走 `ActionGateway` |
| `LIFE005` | 可选依赖无降级 | 可选插件导入必须经由 fallback 隔离层，缺失时不崩溃、有降级提示 |
| `LIFE006` | 仅通过 visible 隐藏 | 弹窗与面板停用时必须真实卸载或断开流（`active: false`），禁止仅用 `visible: false` |

```bash
# 一键静态与生命周期集成检查
./shell/scripts/dev/check.sh
