# Shell 主题管线契约 (Theme Pipeline)

> 本页是壁纸取色到应用模板渲染的管线契约与渲染队列不变量，以
> `shell/scripts/theme/`、`shell/app/services/TemplateService.qml` 与
> `tests/test_shell_runtime.py` 的真实行为为准。

## 管线

壁纸变更（Shell 选择器或启动再生成）→ `generate-matugen-colors.sh`
（matugen 仅做纯取色）→ 一次运行双写 `colors.json`（Shell 热载）与
`palette-modes.json`（dark+light 双模式）。TemplateService 监听
`palette-modes.json`：写 Noctalia 色板镜像，然后对全部启用模板执行渲染
队列；队列按表达式子集（`TemplateExpr.js`）渲染每个模板，原子写输出，
再跑注册表里的 post hook（kitty include、btop 信号、starship 托管块）。

## 渲染队列不变量

- 单模板串行；失败记入 `renderErrors`，不阻断余队。
- **内容相同的渲染也是完成的渲染**：Quickshell `FileView.setText` 在新文本
  等于已加载内容时静默 no-op、不发射 `saved()`。启动再生成与同壁纸重渲染
  必然命中，因此队列用 settle 时捕获的 `outputContent` 判等，命中即走完成
  路径；hook 照常运行（hook 全部幂等，kitty-apply 结尾无条件重载实例）。
- **输出视图写同步**（`blockWrites: true`）：0.3.1 的 FileView 在同一视图
  上快速交错 read/write 会丢失操作完成事件（实测 writer 启动后 `saved()`
  永不到达）。同步保存没有可丢的异步完成。
- **hook 每次全新 Process**：复用实例会静默吞掉 spawn 请求。实例在完成或
  销毁时终结。
- **每个异步等待都有 10s 看门狗**：模板读取、输出 settle、hook 运行任一
  丢失事件，都退化为该模板的一条已记录失败并推进队列。`renderingId`
  在结构上不可能永久卡死；下一次 `renderAll`（下一次换壁纸）自然重试。
- 空渲染结果按失败处理，不进入写入门控。

## Quickshell 0.3.1 平台约束（原因记录）

- `FileView.setText`：内容等价即 no-op（C++ 侧 `writeCmpData` 比较），
  不会写盘也不会发 `saved()`。
- `FileView` 异步操作：同视图交错时 `cancelAsync` 会 disown 在途 read，
  其完成被丢弃；写完成同样可能丢失。队列不得在 settle 窗口之外触碰
  输出视图。
- `Process` 复用：紧随上一个子进程退出的 spawn 请求可能被静默丢弃。
- 升级 Quickshell 后应重跑队列行为测试；若平台已修复，可重新评估
  `blockWrites` 与看门狗的必要性。

## 验收方式

`tests/test_shell_runtime.py::test_template_render_queue_writes_outputs_and_hooks`
在私有合成器里跑真实 QML：palette-modes 热重载必须渲染 kitty/btop/starship
并运行 hook；同色板重渲染必须排空队列且 hook 照跑；随后的色板改写必须仍被
跟随；`renderErrors` 保持为空；不得出现 QML 诊断。
