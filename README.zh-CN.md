<a id="readme-top"></a>

<div align="right">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>/nɪkˈsuːri/ · Arch / CachyOS 上的模块化桌面配置系统</strong><br />
<sub>支持 Niri 与 Noctalia —— 慢慢来，搭好属于你的干净日常 (ゆっくりしていってね！)</sub></p>

<p>
  <a href="https://github.com/ech678/Nyxuri/stargazers"><img height="22" src="https://m3-markdown-badges.vercel.app/stars/3/3/ech678/Nyxuri" alt="Stars" /></a>
  &nbsp;
  <a href="https://archlinux.org"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/Arch/arch2.svg" alt="Arch Linux" /></a>
  &nbsp;
  <a href="LICENSE"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/LicenceGPLv3/licencegplv33.svg" alt="GPL-3.0" /></a>
</p>

<a href="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be">
  <img src="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be" alt="Nyxuri 预览" width="92%" />
</a>

<p>
  <sub><em><a href="https://nyxniri.com">官网</a> · 观看 <a href="https://www.bilibili.com/video/BV1c63n6dEEG">Bilibili 演示</a> · 参与 <a href="https://www.reddit.com/r/niri/comments/1vf53le/nyxniri_a_material_you_desktop_config_for_niri/">Reddit 讨论</a> · 查阅 <a href="https://github.com/ech678/Nyxuri/wiki/Home-zh">Wiki</a></em></sub>
</p>
<br />

</div>

> ⚠️ **开发警告**：当前 `main` 主分支正在重构与演进中（代码与配置结构随时可能变化）。如果你追求日常平稳，建议检出最新 Release 标签使用。
>
> 从原 **NyxNiri** 迁移？项目现已更名为 **Nyxuri**（/nɪkˈsuːri/），它不再只是一份死板的单套配置，而是演进为一套完全解耦的模块化桌面配置系统。运行 `nyxuri` 会自动把旧配置和快照安全搬家，并清理旧路径。
>
> **注意：** 自研的 **Nyxuri Shell** 目前是实验性功能——完全处于开发阶段、已知问题较多、外观尚未完工，暂不推荐日常使用。日常请留在 Noctalia，`nyxuri shell` 仅供测试。已知问题见 [shell/KNOWN-ISSUES.md](shell/KNOWN-ISSUES.md)。

### 名字的小秘密

名字读作 `/nɪkˈsuːri/`，是把几样喜欢的事情悄悄拼在一起的产物：

- **Nyx**：夜之女神，也是宁静夜晚的陪伴（以及老名字 NyxNiri 的念想）。
- **Yukkuri**（ゆっくり / にゅっくり）：**放轻松，慢慢来**。折腾 Linux 桌面本就该是件治愈开心的事，不要急躁，随心就好。
- **Yuri**（百合 / ゆり）：纯粹美好的日常与女孩子之间的羁绊（作者的小小私心）。
- **…至于 URI？**：早先在架构文档里硬编过一个叫“统一运行时接口 (Unified Runtime Interface)”的唬人缩写……忘掉它吧！其实真的只是因为读起来软软糯糯很顺口而已啦 (⁄ ⁄•⁄ω⁄•⁄ ⁄)

## 它是什么

简单来说，**Nyxuri 是一套面向 Arch / CachyOS 的模块化桌面配置系统与管理引擎**。

我们致力于长期提供双桌面外壳（成熟稳健的 **Noctalia** 与正在孵化打磨的自研 **Nyxuri Shell**），以 Niri 为首发基座，并逐步接入更多平铺与浮动窗口管理器。系统坚守**零臃肿、无暗箱、无残留**的减法原则，开箱即用的功能包括：

- **多 WM 协同与双外壳架构**：核心动作经由 `shell-action.sh` 网关彻底解耦；原生支持 **Niri**（滚动平铺）与 **MangoWM**（平铺与浮动），并持续扩展更多 Wayland 合成器；外壳层支持 Noctalia 与 Nyxuri Shell 自由选择与无缝过渡。
- **全域色彩与明暗联动**：壁纸取色（动态视频实时抽帧）驱动全局 Material You 配色，GTK 3/4、XDG Portal、Kitty、主流浏览器与外壳深浅色同步流转。
- **Noctalia 伴生工具集 (Noctalia Tools)**：
  - **Orbit 启动器**（`Super+A` / 鼠标侧键）：矢量星环轮盘，集成常用应用、网址与 AI/搜索转盘（TOML 全自定义）。
  - **壁纸选择器**（`Super+W`）：静态图片与动态视频壁纸统一检索与实时预览。
  - **划词翻译**：选中文本即刻弹出轻量释义。
  - **护眼模式**（`Super+N`）与 **Scratchpad**（`Super+~` Kitty 浮动终端）。
- **NyxMellow 输入法**：跟随系统配色的动态 fcitx5 皮肤（mellow 圆角几何），附带开箱即用的 Rime 输入配置。
- **现代终端体验**：Kitty 平滑光标轨迹与防冲快捷键，搭配 Fish 实用别名与 Starship 提示符。
- **即插即用的原子单元**：Fastfetch 看板、Noctalia Greeter 登录界面、Zed 编辑器与壁纸包，单键启闭（`nyxuri on` / `nyxuri off`），未启用单元零常驻、零开销。
- **原子部署、预设与零臃肿安全网**：
  - **Dunder 保护协议**：任何文件名含 `__custom__`（如 `__custom__.kdl`、`__custom__.conf`）或 `monitor.kdl` 的文件跨更新与预设切换永久保留，绝不覆盖用户私有改动。
  - **分层预设**：支持 Kitty 透明度等风味预设一键切换，并支持用户私有预设制作。
  - **零臃肿与白纸抹除**：引擎坚持纯 Python 标准库驱动，零 pip 依赖；停用单元即刻安全抹白无残留；30 轮滚动快照随时一键回退，`nyxuri doctor` 实时对账实机与声明状态。

## 安装

### 从 Git 仓库安装（推荐）

```bash
# 浅克隆：只拉最新快照；要完整历史去掉 --depth 1
git clone --depth 1 https://github.com/ech678/Nyxuri.git ~/Nyxuri
cd ~/Nyxuri && ./install.sh
```

### 独立在线安装

```bash
curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/ech678/Nyxuri/main/install.sh | bash
```

> [!TIP]
> Arch 自动探测 Shelly、paru、yay；缺少助手时尝试从已配置的软件源安装。

<details>
<summary>国内镜像加速（gh-proxy / CDN）</summary>

```bash
# 通过 gh-proxy.org 独立安装
curl -fsSL --connect-timeout 10 https://gh-proxy.org/https://raw.githubusercontent.com/ech678/Nyxuri/main/install.sh | bash

# 通过 gh-proxy.org 克隆仓库
git clone --depth 1 https://gh-proxy.org/https://github.com/ech678/Nyxuri.git ~/Nyxuri
cd ~/Nyxuri && ./install.sh
```
</details>

### 从 AUR 安装

```bash
paru -S nyxuri-git
```

若系统未安装 AUR 助手，可手动构建并安装 `nyxuri-git` 软件包：

```bash
# 克隆 PKGBUILD 仓库
git clone https://aur.archlinux.org/nyxuri-git.git

# 构建并安装
cd nyxuri-git && makepkg -si
```

## 架构与单元

```text
Nyxuri
├── install.sh                  # 极简引导入口
├── catalog.toml                # 软件目录清单（18 款日常软件同源依赖）
├── nyxuri/                     # Python 核心引擎（零 pip 依赖）
├── shell/                      # Nyxuri Shell（自研 QML/Qt6 桌面外壳，实验性）
└── units/                      # 13 个独立原子桌面能力单元
    ├── fastfetch/              # 系统信息展示
    ├── fcitx5-rime/            # 动态 Material You 输入法皮肤与配置
    ├── fish/                   # Shell 别名与实用函数
    ├── greeter/                # Noctalia Greeter 登录界面集成
    ├── kitty/                  # 终端模拟器与透明度预设
    ├── mango/                  # MangoWM 窗口管理器与动作调度脚本
    ├── niri/                   # 窗口管理器与动作调度脚本
    ├── noctalia/               # 桌面外壳、主题同步、Orbit 星环与壁纸选择器
    ├── starship/               # 终端提示符
    ├── theme/                  # 共享 matugen 主题模板池
    ├── wallpapers/             # 配套壁纸与动态视频包下载钩子
    ├── xdg-desktop-portal/     # Portal 路由（主题与录屏分流）
    └── zed/                    # 代码编辑器配置
```

配置采用原子物理替换。个人改动通过 Dunder 协议保留：任何文件名或目录名含 `__custom__` 的文件（如 `__custom__.kdl`、`__custom__.conf`）与 `monitor.kdl` 在更新时自动保留。

自定义规则与部署后钩子见 [配置与自定义 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Configuration-zh)。

## 预设

预设叠在默认配置和你的 `__custom__` 之间，切换不会碰你的自定义改动。支持零件插槽化组合。

官方预设清单、Parts 插槽机制与私有预设制作见 [预设手册 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Presets-zh)。

## 快捷键

核心快捷键通过 `shell-action.sh` 网关调度，保证合成器与桌面外壳解耦。快速查看：`nyxhelp keys`。

完整窗口控制、多屏漫游按键表与全屏覆盖层见 [快捷键全景图 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Keybindings-zh)。

## 单元能力

桌面上一切能力皆为可独立开关的原子单元。可选单元包括动态取色 Fcitx5 皮肤（`fcitx5-rime`）、配套壁纸与视频包（`wallpapers`），以及一致视觉的 Noctalia Greeter 登录界面（`greeter`）。随时单键启闭：`nyxuri on <unit>` / `nyxuri off <unit>`。

单元生命周期管理详见 [CLI 命令手册 (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference-zh#单元市场动词)。

## 工具

`nyxuri` 管理安装、更新、配置快照与系统诊断，终端内随时可用 `nyxhelp` 速查。

全量子命令、参数选项与 Shell 别名见 [CLI 命令手册 (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference-zh)。

## 故障排除

遇到启动卡死、双显卡渲染异常或样式白屏时，优先运行 `nyxuri doctor`。

详细排障步骤与完整清单见 [故障排除指南 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Troubleshooting-zh)。

## 其他发行版

**Ubuntu 26.04**：已完成 APT 适配与 Niri 核心功能验证。

## 致谢与社区

**联系与社区：**
- TG 频道：[@linux_ricing](https://t.me/linux_ricing)
- QQ：`2040244628` · Linux Ricing 交流群：`631425889`
- 赞助：[爱发电](https://afdian.com/a/Echoes678) · 问题反馈：[GitHub Issues](https://github.com/ech678/Nyxuri/issues)

**协作与鸣谢：**
- [Google Gemini](https://deepmind.google/technologies/gemini/) — 白嫖了谷歌一堆 token
- [@zhuhuaian](https://github.com/zhuhuaian) · [@Krits03](https://github.com/Krits03) · [@Yulljie](https://github.com/Yulljie) — 社区管理与情感支持
- [@TyhLxxxhLrqTq](https://github.com/TyhLxxxhLrqTq) — 配套壁纸站支持（开发中）

**致谢：**
- [RanXOM/glassy-niri](https://github.com/RanXOM/glassy-niri) — blur 效果参考
- [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri) — 抄了很多！
- [sanweiya/fcitx5-mellow-themes](https://github.com/sanweiya/fcitx5-mellow-themes) — NyxMellow 皮肤圆角形状来源
- [StarWhiteIsBusy/Round-Simple-Fcitx5-Skin](https://github.com/StarWhiteIsBusy/Round-Simple-Fcitx5-Skin) — Noctalia 取色联动方案参考
- [doctorlogix](https://github.com/doctorlogix) — 官网设计借鉴

**推荐项目：**
- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) — 状态栏歌词组件
- [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity) — 浏览器透明度脚本

---

<div align="right">
  <a href="#readme-top">↑ 返回顶部</a>
</div>
