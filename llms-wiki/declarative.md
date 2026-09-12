# Declarative vs Imperative — 边界（啥该 / 不该声明式）

> NyxNiri 已是 80% 声明式。这不是范式重写，是让现有的隐式声明式**显式化**——用加法做。

## 已是声明式的部分

- ✅ 仓库 `configs/` = 期望状态（source of truth）
- ✅ `~/.config/` = 当前状态
- ✅ `atomic_replace_item` = 对账器，Dunder = 增量保留
- ✅ snapshot = 存档当前状态，rollback = 恢复
- ✅ active 预设名写在 state 文件，`nyxniri install` = 读 state + 对账到 `~/.config` + 跑命令式副作用

让"期望状态"更显式：active 预设名在 state 文件里，repo = 真值、`~/.config` = 派生物。

## 不该声明式的部分（必命令式）

依赖安装、主题同步、Fcitx 配置重载都是命令式副作用，由对应模块的生命周期入口负责。
安装可选软件只安装包，不自动调用皮肤模块；皮肤模块不修改输入法快捷键，也不接管进程启停。

## 明确不做（避免熵增）

- `~/.config/NyxNiri/apps/<myapp>/` 用户 drop-in app 目录（加扫描路径 + 覆盖语义）
- `.module.toml` 里声明 doctor 检查项、post-install hook（会让 manifest 膨胀成小语言）
- `.module.toml` 里放 i18n 键（文案集中在 `translations.toml`，已有自动校验）
- stable + git 双 AUR 包（双倍熵）
- Nix 风格纯函数式部署引擎（杀不掉副作用，徒增复杂度）
- 根据 PCI 设备自动选择驱动变量（PCI 列表无法确定实际渲染 GPU，见 [nvidia-patch](nvidia-patch.md)）
- `.nyxignore` 替代 `__custom__`（"魔法文件名"换成"魔法文件列魔法文件名"，更绕）
- 安装方式优先级规则（被"哪里跑就是哪里的模式"取代，见 [install-modes](install-modes.md)）
- `preset diff`（`~/.config/<app>/` 是预设+custom 混合体，diff 会把 custom 当差异报；
  update 已有 diff 查看器，够用）
- `.module.toml` `detect` 前缀 DSL（`detect = "kitty"` 纯名字，不要 `binary:` 前缀语法）
- TUI 预设切换的两个级联 `Menu` 与自写焦点分发——被单栏树状折叠拓扑工作台取代（见 [tui-switcher](tui-switcher.md)）
