# Mango WM 适配契约 (Mango WM Adaptation)

> 本页是 Nyxuri 对 Mango (mangowm / wlroots) 合成器适配的架构契约与设计决策记录，以源码（`configs/mango/` 与 `nyxuri/`）为准。

## 1. 架构总览与双轴定位

Mango (`mangowm`) 是一款现代、轻量、基于 wlroots 的 Wayland 合成器，具备类似 Niri 的 Scroller（无限滚动）与 Dwm-like 平铺混合模式。

遵循 Nyxuri 的 [two-axis-config](two-axis-config.md)（双轴解耦）设计：
- **配置轴（Axis A）**：`configs/mango/` 目录存在，由部署引擎原子复制到 `~/.config/mango/`。
- **可选轴（Axis B）**：登记在 `configs/.optional-apps.toml` 中，声明为可选桌面组件（`aur = ["mangowm"]`），不强占系统硬依赖，不破坏 PKGBUILD 纯度。

## 2. 目录结构与配置文件分工

```
configs/mango/
├── .module.toml        # 模块清单（preserve、chmod、reload 钩子）
├── config.conf         # 核心合成器配置
├── monitors.conf       # 显示器配置（由 Noctalia 生成，动态保留）
├── __custom__.conf     # 用户自定义配置（Dunder 保护）
└── scripts/
    ├── session-shell.sh    # 外壳启动网关（nyxuri-shell / noctalia 探测与回退）
    ├── shell-action.sh     # 桌面外壳动作网关（启动器、锁屏、壁纸、翻译等）
    └── mango-brightness.sh # 亮度调节脚本（内屏背光 + 外接屏 DDC/CI 穿透）
```

## 3. 核心设计契约与不变量

### 3.1 Dunder 与 Preserve 双机制保障
- **`monitors.conf` 与 `noctalia.conf`**：在 `configs/mango/.module.toml` 中声明为 `preserve`，更新与部署时不覆盖运行时状态。
- **`__custom__.conf`**：命名遵循 Dunder 协议，由部署引擎 `atomic_replace_item` 自动继承，用户在其中添加的自定义按键与窗口规则永久生效。
- **优雅包含**：在 `config.conf` 中统一使用 `source-optional=` 语法（如 `source-optional=~/.config/mango/noctalia.conf`），即使外部文件尚未生成也不会导致合成器报错或中断。

### 3.2 外壳与脚本解耦
- **外壳网关**：快捷键不硬编码特定桌面外壳命令，通过 `/home/user/.config/mango/scripts/shell-action.sh` 统一分发至当前活动的桌面外壳（Noctalia 或 Nyxuri 自研 Shell），支持 Orbit 星环启动器、划词翻译与壁纸选择器。
- **会话启动**：通过 `session-shell.sh` 挂载桌面外壳，并自动清理残留 scope。
- **路径中立**：脚本引用统一采用 `/home/user` 模板占位符，由 `nyxuri.deploy.templates` 部署时自动重写为目标 `$HOME`。

### 3.3 主题同步与渲染管线
- **Noctalia 模板注册**：`configs/noctalia/noctalia-config.toml` 在 `[theme.templates]` 的 `builtin_ids` 中启用 `"mango"`。Noctalia 取色引擎会自动将配色渲染至 `~/.config/mango/noctalia.conf`。
- **热重载总线**：在 `nyxuri/theme.py` 主题同步与切换时，自动探测并执行 `mmsg dispatch reload_config`，实现免重启即时变色。

### 3.4 门户路由 (XDG Desktop Portal)
- 在 `configs/xdg-desktop-portal/mango-portals.conf` 中为 Mango 单独配置 `preferred` 路由：
  - `ScreenCast` 与 `Screenshot` 显式路由至 `wlr`（由 `xdg-desktop-portal-wlr` 处理 `zwlr-screencopy` 协议），规避 GNOME/Mutter 专属后端的启动崩溃。

## 4. 验证方式

```bash
# 1. 语法检查
mango -c configs/mango/config.conf -p

# 2. 契约单测
python3 -m unittest tests/test_mango_adaptation.py

# 3. 全局单测与文档闭包验证
python3 -m unittest discover -s tests -q
```
