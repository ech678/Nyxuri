# 单窗口捕获技术验证

这是独立的 Qt/QML 验证入口，使用 `Clavis.WindowPreview` 原生模块，通过一条独立
Wayland 连接枚举 ext toplevel，并按稳定的 `identifier` 捕获窗口。它不会启动 Clavis
服务，不更改 Dock 设置。无需替换系统 Quickshell。

Dock 使用同一模块的 `WindowPreviewManager`：按 niri 的十进制 IPC window ID 关联
ext identifier，只为悬停弹层中可见的卡片创建会话，多输出上的消费者共享窗口捕获。
弹层关闭、窗口关闭、锁屏或连接断开时释放捕获；设置中心按当前协议能力显示缩略图
开关与尺寸选项。标题模式仍可使用，单窗口捕获失败时显示图标和标题。

## 构建

在 Clavis 仓库根目录执行（依赖本机的 `wayland-client`、`wayland-scanner` 和
`wayland-protocols >= 1.41`；协议代码由 CMake 生成）：

```bash
cmake -S . -B build -G Ninja -DCLAVIS_BUILD_WINDOW_PREVIEW_PROBE=ON
cmake --build build --target clavis-window-preview ClavisWindowPreviewplugin
```

构建和单元测试不依赖 niri 源码仓库。以下运行验证才需要支持相应协议的合成器。

## 连接嵌套 niri

从嵌套 niri 的日志确认 `WAYLAND_DISPLAY`。下面的 `wayland-2` 仅为示例，
每次重新启动合成器后应重新确认。`--display` 必须显式给出，不会自动连接日用会话。

```bash
# 先用独立工具核对窗口 identifier；不是标题、app-id 或列表下标。
WAYLAND_DISPLAY=wayland-2 wayshot --list-toplevels-json

# 实时视图：选择窗口后 Start；捕获中切换选择会替换会话；Stop 清空画面并释放缓冲。
WAYLAND_DISPLAY=wayland-2 QT_QPA_PLATFORM=wayland \
  build/tools/clavis-window-preview --display wayland-2 --timeout 300000

# 纯协议枚举，不创建显示窗口。
QT_QPA_PLATFORM=offscreen build/tools/clavis-window-preview --display wayland-2 --list

# 将实际 identifier 填入 2、3 的位置。
QT_QPA_PLATFORM=offscreen build/tools/clavis-window-preview \
  --display wayland-2 --capture 2 --frames 10 --timeout 15000

# 反复停止、创建及切换目标，输出每帧及最终资源统计。
QT_QPA_PLATFORM=offscreen build/tools/clavis-window-preview \
  --display wayland-2 --capture 2 --alternate 3 --frames 2 --cycles 100 --timeout 30000
```

可用 `--view IDENTIFIER` 让 GUI 自动开始预览。`--save /tmp/frame.png` 只在批处理
结束时保存最后一帧，实时画面始终直接由 SHM 进入 QImage，再由 QQuickPaintedItem
显示，没有循环截图进程或 PNG 中转。

`--fixture A` / `--fixture B` 创建同 app-id 的红/蓝动态测试窗口，带计数器和移动方块；
`--static` 停止动画。通过同样的 `WAYLAND_DISPLAY` 启动它们，再重新枚举 identifier。
这些窗口有明确的退出时限，不读取用户文件或启动终端命令。

批处理退出码：`0` 为完成，`2` 为连接/协议/捕获失败，`3` 为等待新帧超时。
默认运行时限为 15 秒，可用 `--timeout` 调整。静态画面可能只有一帧，因此超时
不等于捕获失败，应同时查看 `frames`、`distinctFrames` 和失败原因。

## 验证边界

- 必需接口：`wl_shm`、`ext_foreign_toplevel_list_v1`、
  `ext_foreign_toplevel_image_capture_source_manager_v1`、`ext_image_copy_capture_manager_v1`。
- SHM 支持 ARGB8888 / XRGB8888；单缓冲复用、最多约 30 次请求/秒，后续请求可由
  合成器等待内容变化。图像尺寸是源窗口像素尺寸，不是预览控件尺寸。
- resize 收到新约束后重新分配缓冲；切换/停止/窗口关闭/断线清空图像并释放会话。
  诊断统计保留首帧耗时、帧数、尺寸、SHA-256、退出原因与进程 FD 数量。
- 当前明确拒绝非 normal 的 buffer transform 和不支持的格式，不显示方向错误的画面。
- Dock 限制为最多约 15 次请求/秒，并将保留图像的长边限制为 512 像素；原始 SHM
  缓冲仍按窗口尺寸分配。SHM CPU 拷贝与 QQuickPaintedItem 绘制不是 DMA-BUF
  零拷贝。合成器与应用决定实际更新速度；隐藏工作区可能降频。
- 不将 popup 当成独立任务，不用标题或 app-id 猜测窗口身份。此独立入口不运行 Dock
  分组与悬停 UI。最小化不在捕获模块的职责内。
