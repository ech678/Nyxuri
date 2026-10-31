<a id="readme-top"></a>

<div align="right">
<a href="README.md">English</a> | <strong>简体中文</strong>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>Arch 系发行版上的插件化桌面配置系统</strong><br />
<sub>Material Design & 慢慢来，搭好属于你的干净日常 (ゆっくりしていってね！)</sub></p>

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

> **要注意的事**：当前 `main` 主分支激进开发中。想要稳定的话——建议使用最新Release哦~ (同时我们的Shell也完全没有完工,外观和架构都有待大改,暂不推荐日用)

### 名字的小秘密

名字读作 `/nɪkˈsuːri/`，是把几样喜欢的事情悄悄拼在一起的产物：

- **Nyx**：夜之女神，也是宁静夜晚的陪伴（以及老名字 NyxNiri 的念想）。
- **Yukkuri**（ゆっくり / にゅっくり）：**放轻松，慢慢折腾**。
- **Yuri**（百合 / ゆり）：纯粹美好的日常与女孩子之间的羁绊（作者的小小私心）。
- **…至于 URI？**：早先在架构文档里硬编过一个叫“统一运行时接口 (Unified Runtime Interface)”的唬人缩写……忘掉它吧~! QWQ

## Nyxuri 是什么

简单来说，**Nyxuri 是一个Arch系发行版上的插件化桌面配置系统**。
哲学是变得最透明、给用户最大的知情权和选择权。然后因为作者喜欢折腾，所以在尽量保持简洁的同时，整了很多有意思的功能:

- **多 WM 支持** 现在我们支持Niri和MangoWM哦(也许还会有Hyprland!?)。给不同的WM和Shell间的快捷键动作做了一层转接，让无缝切换WM和Shell很方便!
- **多桌面 Shell 支持** 目前持续更新的有 Noctalia V5 和我们自己的Shell配置啦
- **Nyxuri Shell** 我们自己的Shell(基于Quickshell),处于开发中,采用插件化设计,一定不会像其他Quickshell一样臃肿啦
- **全局的 Monet 取色** 从静态和动态壁纸生成覆盖几乎全局(Shell、GTK主题、kitty、fcitx5...好多好多)的Monet(Material You)风格配色.并且Nyxuri Shell也支持直接用 Noctalia v5 的第三方应用配色模板!
- **丰富的插件(Dotfiles)** NyxMellow(fcitx5输入法皮肤)、Fastfetch 看板、Kitty、Starship、Noctalia Greeter 登录界面、Zed 编辑器与壁纸包... 未启用时不常驻，零开销。
- **良好的用户体验**
  - **不会弄丢你的自定义**：只要文件名里带 `__custom__`（比如 `__custom__.kdl`、`__custom__.conf`）或者显示器配置 `monitor.kdl`，更新和切预设时都会自动保留，不会覆盖你改过的东西!
  - **预设随便切**：支持像 Kitty 透明度这样的预设一键切换，也能自己写预设玩。
  - **干净不留垃圾**：管理工具只用 Python 自带的标准库，不需要装一堆 pip 依赖；关掉插件就会把配置清理干净，还带 30 次自动备份快照和 `nyxuri doctor` 检查工具。

<details>
<summary>也做了一些对于Noctalia的补充工具~</summary>

- **Orbit 启动器**：矢量星环轮盘，集成常用应用、网址与 AI/搜索转盘（TOML 全自定义）。
- **壁纸选择器**：静态图片与动态视频壁纸统一检索与实时预览。
- **划词翻译**：选中文本即刻弹出轻量释义。
- **护眼模式** 与 **Scratchpad**（`Super+~` Kitty 浮动终端）。
</details>

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

## 目录结构

```text
Nyxuri
├── install.sh                  # 安装引导脚本
├── nyxuri/                     # Python 核心管理脚本（零 pip 依赖）
├── shell/                      # Nyxuri Shell（自研 QML/Qt6 桌面外壳，实验性）
└── plugins/                    # 独立的插件配置
    ├── fastfetch/              # 系统信息展示
    ├── fcitx5-rime/            # 动态配色的输入法皮肤与配置
    ├── fish/                   # Shell 别名与好用的小函数
    ├── greeter/                # Noctalia Greeter 登录界面
    ├── kitty/                  # 终端配置与透明度预设
    ├── mango/                  # MangoWM 窗口管理器配置
    ├── niri/                   # Niri 窗口管理器配置
    ├── noctalia/               # Noctalia 外壳、主题同步与补充小工具
    ├── starship/               # 终端提示符
    ├── theme/                  # 共享的 matugen 配色模板
    ├── wallpapers/             # 配套壁纸与动态视频下载脚本
    ├── xdg-desktop-portal/     # Portal 配置文件
    └── zed/                    # 代码编辑器配置
```

自己的个人修改只要放在名字带 `__custom__` 的文件或目录里（比如 `__custom__.kdl`、`__custom__.conf`），或者写在 `monitor.kdl` 里，更新的时候就会自动保留，不会被覆盖掉。

更详细的自定义规则可以看 [配置与自定义 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Configuration-zh)。

## 预设

预设会叠在默认配置和你的 `__custom__` 之间，所以切换预设不会弄乱你自己的修改。也支持把不同部分像拼积木一样组合起来用。

预设列表和自己写预设的方法见 [预设手册 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Forms-zh)。

## 快捷键

常用快捷键通过 `shell-action.sh` 脚本转发，这样换 WM 或换 Shell 的时候就不用重新适应一套按键啦。平时忘了按键可以在终端输 `nyxhelp keys` 查看。

完整的按键列表见 [快捷键全景图 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Keybindings-zh)。

## 插件开关与命令行工具

桌面里的组件都是独立插件，比如 Fcitx5 皮肤（`fcitx5-rime`）、壁纸包（`wallpapers`）、登录界面（`greeter`）等等。平时想开哪个、关哪个，直接敲 `nyxuri on <插件名>` 或 `nyxuri off <插件名>` 就行。

安装、更新、回滚备份和检查问题也都用 `nyxuri` 命令搞定，终端里输 `nyxhelp` 可以看常用命令提示。所有命令的详细用法见 [CLI 命令手册 (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference-zh)。

## 故障排除

如果遇到进不去桌面、双显卡显示不正常或者主题没生效，可以先跑一下 `nyxuri doctor` 检查看看。

常见问题和解决办法见 [故障排除指南 (Wiki)](https://github.com/ech678/Nyxuri/wiki/Troubleshooting-zh)。

## 社区

**交流：**

* TG 频道：[@linux_ricing](https://t.me/linux_ricing)
* QQ：`2040244628` · Linux Ricing 交流群：`631425889`
* 赞助：[爱发电](https://afdian.com/a/Echoes678) · 问题反馈：[GitHub Issues](https://github.com/ech678/Nyxuri/issues)

**感谢：**

* [@zhuhuaian](https://github.com/zhuhuaian) · [@Krits03](https://github.com/Krits03) · [@TyhLxxxhLrqTq](https://github.com/TyhLxxxhLrqTq) · [@Yulljie](https://github.com/Yulljie) — 帮我做了很多杂活呢~❤️
* [RanXOM/glassy-niri](https://github.com/RanXOM/glassy-niri) — blur 效果参考
* [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri) — 抄了很多！
* [sanweiya/fcitx5-mellow-themes](https://github.com/sanweiya/fcitx5-mellow-themes) — NyxMellow 皮肤圆角形状来源
* [StarWhiteIsBusy/Round-Simple-Fcitx5-Skin](https://github.com/StarWhiteIsBusy/Round-Simple-Fcitx5-Skin) — NyxMellow 参考
* [doctorlogix](https://github.com/doctorlogix) — 官网设计借鉴

**推荐项目：**

* [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) — 状态栏歌词组件
* [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity) — 浏览器透明度脚本

---

<div align="right">
<a href="#readme-top">↑ 返回顶部</a>
</div>
