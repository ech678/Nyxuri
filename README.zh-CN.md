<a id="readme-top"></a>

<div align="right">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>/nɪkˈsuːri/ · Arch / CachyOS 上的 Material You 桌面体验</strong><br />
<sub>基于 Niri 和 Noctalia V5 —— 然后闭嘴！</sub></p>

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

> 从原 **NyxNiri** 迁移？项目现已更名为 **Nyxuri**（/nɪkˈsuːri/），因为我们计划接入自研桌面 Shell 并支持更多窗口管理器。运行 `nyxuri` 会自动搬迁原有配置、历史快照与状态，并安全清理旧目录。

## 特性

- **壁纸选择器**（`Super+W`）— 静态和动态壁纸统一选择，支持搜索和分类。
- **色彩联动** — Noctalia V5 直接从壁纸取色；动态壁纸由 `mpvpaper` 配合 `ffmpeg` 抽帧。
- **明暗同步** — GTK 3/4、XDG Portal、Kitty、浏览器一起跟随主题切换。
- **护眼模式**（`Super+N`）— 暖色温、关模糊、纯色不透明窗口。
- **Scratchpad**（`Super+~`）— 随时呼出的 Kitty 持久浮动终端。
- **Orbit 启动器**（`Super+A` / `Super+鼠标前侧键`）— 矢量星环；应用、工具、网页、AI/搜索轮盘，全 TOML 自定义。
- **Shell 和终端** — Fish 代理/缓存别名，Kitty 光标轨迹，Windows 风格快捷键（智能 Ctrl+C/Ctrl+V、右键粘贴、划选防覆盖剪贴板）。
- **NyxMellow** — 动态 fcitx5 皮肤：mellow 圆角 + Noctalia Material You 配色。
- **配置预设** — 每个应用多套风味变体（如 kitty 透明）；一条命令切换，把当前配置存为私有预设，或直接在 `$EDITOR` 里改。

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
> 自动支持 Shelly、paru、yay；均未安装时，`nyxuri install full` 会自动装好 `paru`。

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

## 包含配置

```text
Nyxuri
├── install.sh                  # 极简引导入口
├── nyxuri/                     # Python 核心引擎（零 pip 依赖）
├── assets/                     # 静态资产（壁纸、fcitx5 皮肤模板）
└── configs/
    ├── niri/                   # 窗口管理器（.kdl、.toml）
    │   └── scripts/            # 胶水脚本与快捷网关
    ├── noctalia/               # 桌面 Shell 与主题同步
    │   └── tools/              # Orbit 星环启动器、壁纸选择器
    ├── xdg-desktop-portal/     # Portal 路由（主题与录屏分流）
    ├── kitty/                  # 终端
    ├── fish/                   # 别名与函数
    ├── fastfetch/              # 系统信息
    ├── zed/                    # 编辑器
    └── starship.toml           # 提示符
```

配置采用原子物理替换。个人改动通过 Dunder 协议保留：任何文件名或目录名含 `__custom__` 的文件（如 `__custom__.kdl`、`__custom__.conf`）与 `monitor.kdl` 在更新时自动保留。

自定义规则与部署后钩子见 [配置与自定义 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Configuration-zh)。

## 预设

预设叠在默认配置和你的 `__custom__` 之间，切换不会碰你的自定义改动。支持零件插槽化组合。

官方预设清单、Parts 插槽机制与私有预设制作见 [预设手册 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Presets-zh)。

## 快捷键

核心快捷键通过 `shell-action.sh` 网关调度，保证合成器与桌面外壳解耦。快速查看：`nyxhelp keys`。

完整窗口控制、多屏漫游按键表与全屏覆盖层见 [快捷键全景图 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Keybindings-zh)。

## 扩展

可选扩展包含动态取色 Fcitx5 皮肤（NyxMellow）、配套高清壁纸与动态视频包，以及和桌面主题一致的 Noctalia Greeter 登录界面。

扩展模块安装与生命周期管理见 [扩展模块指南 (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference-zh#扩展)。

## 工具

`nyxuri` 管理安装、更新、配置快照与系统诊断，终端内随时可用 `nyxhelp` 速查。

全量子命令、参数选项与 Shell 别名见 [CLI 命令手册 (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference-zh)。

## 故障排除

遇到启动卡死、双显卡渲染异常或样式白屏时，优先运行 `./install.sh doctor`。

详细排障步骤与完整清单见 [故障排除指南 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Troubleshooting-zh)。

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
