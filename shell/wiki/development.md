# Nyxuri Shell — 开发与调试指南

## 当前可用与调试入口

当前已完成 P1（启动解耦、状态机与基础亮屏）和 P2（四层架构与会话自治生命周期），正式进入 P3。
开发统一在 `feat/nyxuri-shell` 分支推进，提供统一包装入口 `shell/bin/nyxuri-shell`。

日常调试支持三层递进方式，兼顾极速验证与真实会话测试：

### 1. 自动化秒级校验（无图形会话，零副作用）

```bash
# 语法与编译检查
python3 -m compileall nyxuri tests shell

# 480 个宿主契约测试（含状态机与隔离环境单测）
python3 -m unittest discover -s tests -q

# 原生 CTest 契约测试集（23 个原生 IPC 与协议测试）
ctest --test-dir build/shell-test --output-on-failure
```

### 2. 隔离进程预览与 IPC 交互（不影响当前运行的 Noctalia）

当前运行 Noctalia 时，无需关闭桌面，可直接拉起独立 Nyxuri Shell 进程进行预览：

```bash
# 带编译插件路径的隔离前台启动（详细日志）
QML2_IMPORT_PATH=build/shell-test/qml qs --path ./shell --no-duplicate -v

# 观察实时日志流（另一终端）
qs log --path ./shell --follow

# 检查当前暴露的 IPC 接口
qs ipc --path ./shell show

# 向调试实例派发动作（观察面板弹起与关闭后析构）
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
nyxuri shell set custom /home/ray/dev/Nyxuri/shell/bin/nyxuri-shell

# 验证六大标准动作（快捷键或命令行）
nyxuri-shell --action session        # 呼出会话菜单
nyxuri-shell --action launcher       # 呼出应用搜索
nyxuri-shell --action lock           # 锁屏

# 随时一键平滑切回 Noctalia
nyxuri shell set noctalia
```

## 日常开发循环

每轮回答：现在什么能用，这一轮证明什么，失败回到哪里。

1. 查看工作区与 `git status`，确认基线绿再动工。
2. 选择一个功能域，记录范围、四层分工、验收方式与恢复点。
3. 修改 QML/C++，通过 Tier 1 本地单测验证；必要时拉起 Tier 2 隔离进程预览视觉。
4. 消除死路径，更新 ROADMAP 与对应 Wiki。

## 分支与提交约定

所有开发在长期分支 `feat/nyxuri-shell` 进行。
- 基准提交：`15403b9`（纯净母体平铺导入）；
- P1 检查点：`f2c3582`（启动阻断消除、热切换状态机与基础 Bar）；
- P2 检查点：四层架构骨架、会话面板生命周期与 Action Gateway；
- 不主动 commit，除非用户明确要求。

## 视觉、资源与清理证据

视觉改动前保存可获得的截图、短录屏与机器、版本、分辨率、缩放、字体信息。
母体暂时不能运行时区分上游参考与本机实测，注明缺失证据，不凭记忆确认视觉保真。
检查对齐、裁切、图标完整、字体回退、动画连续性和输入反馈。系统字体替换允许字形变化，
但不能接受布局破坏；视觉与架构冲突时记录阻断和候选方案，不默默降低质量。

首次可运行即记录首帧与 ready、空闲 CPU/RSS、专属进程和退出残留，固定比较环境；
正式 p50/p95 与冷暖缓存统计在 P6 完成。重复操作观察后半程稳态，不把 Qt/字体缓存
直接判成泄漏。数据不支持时不承诺秒级或零泄漏。

清理记录缩小的加载闭包、停止的后台、退出默认构建的依赖和删除的源码资产；
迁移记录消除的跨域调用、注入接口、资源 owner、释放路径与移除的旧实现。
封存清单列出保留理由、入口、依赖、检查范围及重新启用条件，不能用封存代替永久清理。
证据注明版本、命令、环境、结果和未解决问题；避免提交含私人路径或用户数据的日志。

## 调试层次与检查

| 改动/问题 | 调试方式 | 注意 |
| --- | --- | --- |
| QML 布局/动画/文案 | 真实 Niri 预览、日志、保存热重载 | 对照上游几何、字体裁切和动画；只格式化改动文件 |
| import/插件缺失 | 读第一条加载错误，检查真实组件加载闭包与构建 import 路径 | 不手写 qmldir、不伪造 plugin，不把隐藏当可选解析 |
| C++ 模型/协议 | 配置/构建受影响目标，已有逻辑/协议测试，完整重启 | 需要时使用已有 debugger；不为普通 UI 引入额外 native |
| 后台/关闭/切换 | 完整退出/重启、进程与连接观察、重复开关 | 热重载成功不证明退出清理；不杀其他实例或用户应用 |
| 锁屏/多屏/通知 | 真实原版 Niri 会话验收 | offscreen 与普通窗口不能替代安全锁或通知服务互斥 |
| 宿主命令/部署 | TempEnv 行为测试、参数数组断言、沙箱部署 | 不写真实 ~/.config，不通过 source matching 冒充行为测试 |

上游 scripts/dev/check.sh 尚需确认宿主路径与变更选择；当前不能承诺一条 check 已覆盖全部。
文档修改检查一致性、链接和空白；日常实现按风险选择上表验证，阶段完成时执行宿主
规定的完整检查与受影响上游检查。工具缺失记录阻断，不安装大工具链来掩盖未验证行为。
生成物写独立 build/staging，运行日志注明时间、实例与失败阶段，限制增长。
P0 调查后在此补齐实际命令、路径和恢复步骤，撤下过期建议；未实现工具始终标为计划。
