# Nyxuri Shell — 开发与调试指南

## 当前可用与调试入口

当前已完成 P1（启动解耦、状态机与基础亮屏）和 P2（四层架构与会话自治生命周期），正式进入 P3。
开发统一在 `feat/nyxuri-shell` 分支推进，提供统一包装入口 `shell/bin/nyxuri-shell`。

日常调试支持三层递进方式，兼顾极速验证与真实会话测试：

### 1. 自动化秒级校验（无图形会话，零副作用）

```bash
# 语法与编译检查
python3 -m compileall nyxuri tests shell

# 宿主契约与行为测试（含状态机、启动器和隔离 QML 测试）
python3 -m unittest discover -s tests -q

# 原生 CTest 契约测试集（23 个原生 IPC 与协议测试）
ctest --test-dir build/shell-test --output-on-failure
```

### 2. 隔离进程预览与 IPC 交互（不影响当前运行的 Noctalia）

当前运行 Noctalia 时，无需关闭桌面，可直接拉起独立 Nyxuri Shell 进程进行预览：

```bash
# 带编译插件路径的隔离前台启动（详细日志）
CLAVIS_BUILD_DIR="$PWD/build/shell-test" shell/bin/nyxuri-shell -v

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

scripts/dev/check.sh 已适配宿主 Git：变更路径以 shell/ 为基准，宿主文件不会混入 Shell 检查。lint 的自动构建就绪判断只要求核心插件；全树包含封存组件，缺可选插件时须区分诊断，不能把核心启动通过写成全树导入通过。
文档修改检查一致性、链接和空白；日常实现按风险选择上表验证，阶段完成时执行宿主
规定的完整检查与受影响上游检查。工具缺失记录阻断，不安装大工具链来掩盖未验证行为。
生成物写独立 build/staging，运行日志注明时间、实例与失败阶段，限制增长。
P0 调查后在此补齐实际命令、路径和恢复步骤，撤下过期建议；未实现工具始终标为计划。

## 目录迁移复核与可复现验证

启动器构建路径：`CLAVIS_QML_BUILD_DIR` → `CLAVIS_BUILD_DIR/qml` → 仓库 `build/shell-test/qml` → `shell/build/qml` → 历史 `shell/native/build/qml`。显式目录不存在直接报错；自动发现路径追加到已有 QML 搜索路径后。系统已安装插件不需要构建目录。

```bash
# 干净默认构建（不构建封存插件）
cmake -S shell -B /tmp/nyxuri-shell-default -G Ninja -DBUILD_TESTING=ON
cmake --build /tmp/nyxuri-shell-default
ctest --test-dir /tmp/nyxuri-shell-default --output-on-failure

# 可选窗口预览与独立 probe
cmake -S shell -B /tmp/nyxuri-shell-preview -G Ninja -DBUILD_TESTING=ON \
  -DENABLE_WINDOWPREVIEW=ON -DCLAVIS_BUILD_WINDOW_PREVIEW_PROBE=ON
cmake --build /tmp/nyxuri-shell-preview

# 使用现有工具：临时 HOME、私有 D-Bus、无界面 Weston，测试完成后清理进程
CLAVIS_TEST_QML_IMPORT_PATH=/tmp/nyxuri-shell-default/qml \
  python3 -m unittest tests.test_shell_runtime -v
```

QML 行为测试验证调色热更新、非法文件保留最后有效值、字体回退、资源/透明度注入、设置搜索锚点注册与销毁、图标重载、无可选预览插件时 Dock/账户组件加载。缺 qs、Weston、D-Bus 或核心构建时明确跳过，不自动安装工具。

复核还修正了 native probe 和翻译提取旧路径、快捷键面板相对 URL、会话/设置的翻译上下文。翻译更新在隔离副本执行；先核对全部消息与译文，再同步失配上下文和目录迁移后的源码位置。

真实桌面的声音、锁屏认证、通知互斥、双 Shell 接管与像素级视觉仍须在用户会话验收；无界面预览和 CTest 不替代这些证据。

### 本轮复核结果

- 宿主完整测试：490 项通过，6 项跳过；新增的 8 项启动器/工具选择/QML 行为测试均执行通过。
- 独立目录默认构建、窗口预览 + probe 构建、安装到临时 prefix、宿主沙箱部署通过；干净构建 CTest 为 22 项通过，matugen registry 因工具缺失跳过。
- 改动的 65 个 QML 文件格式检查通过；真实 Quickshell VFS 下 qmllint 退出 0，但仍产生 1172 条 advisory 诊断，主要涉及动态 QObject 接口、类型收窄和 PanelWindow 工具类型信息。未将这些诊断标为全绿，运行时加载与交互另由行为测试验证。
- 无界面 Weston 内嵌套 Niri：默认插件集完整 Shell 启动，启动器、会话面板、账户/主题设置页与命令模式的开关通过；没有致命 QML 加载、引用、赋值或绑定环错误；默认构建缺预览插件时有局部不可用警告。启用预览插件的构建也通过完整启动，快捷键面板和壁纸清除动作通过。私有环境没有 PipeWire，音频连接报环境错误；未据此验收真实音频能力。
- 隔离翻译更新：每种语言 2637 条消息，上下文迁移后没有新增/删除消息或译文变化。同步两个失配上下文和迁移后的源码位置；每条位置均指向存在的文件。
- 退出时结束测试进程组和临时 D-Bus/合成器；没有修改真实 HOME、启动持久服务、安装依赖或自动提交。
