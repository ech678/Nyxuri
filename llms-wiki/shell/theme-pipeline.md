# Shell 主题管线契约 (Theme Pipeline)

> 本页是壁纸取色到应用模板渲染的管线契约与渲染队列不变量，以
> `shell/scripts/theme/`、`shell/app/services/TemplateService.qml` 与
> `tests/shell/test_shell_runtime.py` 的真实行为为准。

## 管线

壁纸变更（Shell 选择器或启动再生成）→ `generate-matugen-colors.sh`
（matugen 仅做纯取色）→ 一次运行双写 `colors.json`（Shell 热载）与
`palette-modes.json`（dark+light 双模式）。TemplateService 监听
`palette-modes.json`：写 Noctalia 色板镜像，然后对全部启用模板执行渲染
队列；队列按表达式子集（`TemplateExpr.js`）渲染每个模板。内置模板先写状态区，
再由 `desktop.owned_outputs` 持锁核对消费者开关、原值及最后写入身份后提交；
btop 和 Starship 的配置接线也按同样方式登记，后续个人修改会阻断自动覆盖。
用户自建模板仍按其显式输出与 post hook 执行。Kitty 的主要受管色板实际提交到
`themes/noctalia.conf` 后，再通知同 UID 的现有 GUI Kitty 实例重载；`theme sync`
不发送 Kitty 重载，因为当时异步渲染可能还未写出新色板。停用门控会阻止通知，
没有实例是正常情况，信号发送失败则让模板 post hook 返回未完成以便重试。
归属与停用规则见 [Manifest Schema](../manifest-schema.md#跨单元模板消费者)。

## 渲染队列不变量

- 单模板串行；失败记入 `renderErrors`，不阻断余队。
- **内容相同的渲染也是完成的渲染**：Quickshell `FileView.setText` 在新文本
  等于已加载内容时静默 no-op、不发射 `saved()`。启动再生成与同壁纸重渲染
  必然命中，因此队列用 settle 时捕获的 `outputContent` 判等，命中即走完成
  路径；hook 照常运行，Kitty 提交后的通知仍检查消费者开关与现有实例。
- **输出视图写同步**（`blockWrites: true`）：0.3.1 的 FileView 在同一视图
  上快速交错 read/write 会丢失操作完成事件（实测 writer 启动后 `saved()`
  永不到达）。同步保存没有可丢的异步完成。
- **hook 每次全新 Process**：复用实例会静默吞掉 spawn 请求。实例在完成或
  销毁时终结。
- **每个异步等待都有 10s 看门狗**：模板读取、输出 settle、hook 运行任一
  丢失事件，都退化为该模板的一条已记录失败并推进队列。`renderingId`
  在结构上不可能永久卡死；下一次 `renderAll`（下一次换壁纸）自然重试。
- **输入模板加载防重入**：只有路径相同时才调用 `reload()`，路径变更由 `FileView.path` 赋值自发启动加载，杜绝多重 `onLoaded` 触发并发重复 hook 进程。
- **队列推进跨帧解耦**（`Qt.callLater(root.renderNext)`）：在 `renderDone` 中推进下一个模板必须通过 `Qt.callLater` 投递至下一事件循环。Quickshell 0.3.1 的 `FileView` 在 `onSaved` 信号处理期间如果在同一调用栈内同步改变 `path`，底层 C++ `FileViewOperation` 会发生状态竞争并丢弃后续读操作（`got operation finished from dropped operation`），导致连续无 hook 模板（如 `fcitx5_theme` ➔ `fcitx5_panel`）后者读取超时。
- **深浅模式即时重载**：`PersonalizationConfig.onThemeModeChanged` 触发时，利用内存中已加载的 `tokenColors` 双模式映射即刻调用 `renderAll()`，避免依赖磁盘写盘延迟。
- **QML 编译缓存与业务路径分离**：`shell/nyxuri-shell` 只通过 Qt 的 `QML_DISK_CACHE_PATH` 隔离编译缓存，保留 `XDG_CACHE_HOME` 原值，不再导出 `NYXURI_ORIGINAL_CACHE_HOME`。`Paths.xdgCacheHome` 直接读取用户缓存根，不反推或裁去目录后缀。`TemplateService` 创建 hook 子进程时继续显式传递 `XDG_CACHE_HOME: Paths.xdgCacheHome`，外部脚本、Python 引擎桥与 CLI 因而使用同一业务缓存位置；QML 的私有编译目录不成为用户布局。具体清理范围见 [Shell 开发约定](../../shell/AGENTS.md)。
- 空渲染结果按失败处理，不进入写入门控。

## Quickshell 0.3.1 平台约束（原因记录）

- `FileView.setText`：内容等价即 no-op（C++ 侧 `writeCmpData` 比较），
  不会写盘也不会发 `saved()`。
- `FileView` 异步操作：同视图交错时 `cancelAsync` 会 disown 在途 read，
  其完成被丢弃；写完成同样可能丢失。保存回调内直接重置路径会导致紧随其后的读操作被丢弃。队列不得在 settle 窗口之外触碰输出视图，且队列切换必须跨事件帧。
- `Process` 复用：紧随上一个子进程退出的 spawn 请求可能被静默丢弃。
- 升级 Quickshell 后应重跑队列行为测试；若平台已修复，可重新评估
  `blockWrites` 与看门狗的必要性。

## 验收方式

`tests/shell/test_shell_runtime.py::test_template_render_queue_writes_outputs_and_hooks`
在私有合成器里跑真实 QML：palette-modes 热重载必须渲染 kitty/btop/starship
并运行 hook；同色板重渲染必须排空队列且 hook 照跑；随后的色板改写必须仍被
跟随；`renderErrors` 保持为空；不得出现 QML 诊断。
