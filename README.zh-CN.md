<a id="readme-top"></a>

<div align="right">
<a href="README.md">English</a> | <strong>简体中文</strong>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>Arch 系发行版上的插件化桌面配置系统</strong><br />
<sub>慢慢来，搭好属于你的干净日常。ゆっくりしていってね！</sub></p>

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
<a href="https://nyxniri.com">官网</a> · <a href="https://www.bilibili.com/video/BV1c63n6dEEG">演示</a> · <a href="https://www.reddit.com/r/niri/comments/1vf53le/nyxniri_a_material_you_desktop_config_for_niri/">Reddit</a> · <a href="https://github.com/ech678/Nyxuri/wiki/Home-zh">Wiki</a>
</p>

</div>

Nyxuri 管的是桌面上那一堆配置：WM、Shell、输入法皮肤、终端……每样是一个插件，单独开关，关掉时会把自己的文件带走。我希望它足够透明，改什么之前先告诉你；哪里和预期不一样，`nyxuri doctor` 能查出来。

## 特点

<table>
<tr>
<td width="50%" valign="top">
<strong>多 WM</strong><br />
目前支持 Niri 和 MangoWM。快捷键动作统一走一层转接，换 WM、换 Shell 都不用重新记键位。
</td>
<td width="50%" valign="top">
<strong>多 Shell</strong><br />
Noctalia V5，以及我们自己的 Nyxuri Shell（基于 Quickshell，插件化，还在早期）。
</td>
</tr>
<tr>
<td width="50%" valign="top">
<strong>全局 Monet 取色</strong><br />
从静态或动态壁纸取色，铺到 Shell、GTK、kitty、fcitx5 等几乎所有地方。Nyxuri Shell 也能直接用 Noctalia V5 的应用配色模板。
</td>
<td width="50%" valign="top">
<strong>万物皆插件</strong><br />
NyxMellow 输入法皮肤、Fastfetch、Kitty、Starship、Greeter、Zed、壁纸包……没开的插件不常驻，零开销。
</td>
</tr>
<tr>
<td width="50%" valign="top">
<strong>改动不丢</strong><br />
带 <code>__custom__</code> 的文件和 <code>monitor.kdl</code> 更新时原样保留。形态（比如 Kitty 透明度）一条命令就能切。
</td>
<td width="50%" valign="top">
<strong>走得干净</strong><br />
纯 Python 标准库，不装 pip 依赖。关掉插件会把配置清理干净，出问题还有快照可以回滚。
</td>
</tr>
</table>

<details>
<summary>给 Noctalia 做的补充小工具</summary>

- **Orbit 启动器**：矢量星环轮盘，常用应用、网址和 AI/搜索转盘都在上面，TOML 全自定义。
- **壁纸选择器**：静态图片和动态视频壁纸一起检索、实时预览。
- **划词翻译**：选中文本，马上弹出轻量释义。
- **护眼模式** 与 **Scratchpad**：<kbd>Super</kbd> + <kbd>~</kbd> 呼出浮动 Kitty 终端。

</details>

## 安装

> [!WARNING]
> `main` 分支正在激进开发。想要稳定的话，建议用最新的 [Release](https://github.com/ech678/Nyxuri/releases)。Nyxuri Shell 也远没完工，外观和架构都还会大改，暂不推荐日用。

**从 Git 仓库安装（推荐）**

```bash
# 浅克隆：只拉最新快照；要完整历史去掉 --depth 1
git clone --depth 1 https://github.com/ech678/Nyxuri.git ~/Nyxuri
cd ~/Nyxuri && ./install.sh
```

**独立在线安装**

```bash
curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/ech678/Nyxuri/main/install.sh | bash
```

> [!TIP]
> 自动支持 Shelly、paru、yay；都没装的话，`nyxuri install full` 会帮你装好 `paru`。

**从 AUR 安装**

```bash
paru -S nyxuri-git
```

<details>
<summary>还没有 AUR 助手？手动构建</summary>

```bash
# 克隆 PKGBUILD 仓库
git clone https://aur.archlinux.org/nyxuri-git.git

# 构建并安装
cd nyxuri-git && makepkg -si
```

</details>

## 上手

所有事情都交给一条命令：

```bash
nyxuri list                    # 所有插件和开关状态
nyxuri on <插件>               # 开启插件
nyxuri off <插件>              # 关闭并清理干净
nyxuri use <插件> <形态>       # 切换形态
nyxuri doctor                  # 看看哪里不对
nyxhelp                        # 速查菜单（nyxhelp keys 看快捷键）
```

> [!NOTE]
> 自己的修改放进名字带 `__custom__` 的文件或目录（比如 `__custom__.kdl`、`__custom__.conf`），或者写在 `monitor.kdl` 里。更新和切换形态都不会碰它们。

## 文档

| 主题 | 内容 |
| :--- | :--- |
| [配置与自定义](https://github.com/ech678/Nyxuri/wiki/Configuration-zh) | 插件怎么组织，你的修改怎么保留 |
| [形态](https://github.com/ech678/Nyxuri/wiki/Forms-zh) | 官方形态、槽位轴、自己写形态 |
| [快捷键](https://github.com/ech678/Nyxuri/wiki/Keybindings-zh) | 全部按键，以及转接是怎么工作的 |
| [CLI 命令手册](https://github.com/ech678/Nyxuri/wiki/CLI-Reference-zh) | 所有命令 |
| [故障排除](https://github.com/ech678/Nyxuri/wiki/Troubleshooting-zh) | 进不去桌面、双显卡花屏、主题没生效 |

## 社区

**交流**：TG 频道 [@linux_ricing](https://t.me/linux_ricing) · QQ 群 `631425889` · 作者 QQ `2040244628`<br />
**反馈与支持**：[GitHub Issues](https://github.com/ech678/Nyxuri/issues) · [爱发电](https://afdian.com/a/Echoes678)

## 致谢

特别感谢这几位，帮我做了很多杂活呢~❤️

<p>
<a href="https://github.com/zhuhuaian"><img src="https://images.weserv.nl/?url=github.com/zhuhuaian.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@zhuhuaian" title="@zhuhuaian" /></a>
<a href="https://github.com/Krits03"><img src="https://images.weserv.nl/?url=github.com/Krits03.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@Krits03" title="@Krits03" /></a>
<a href="https://github.com/TyhLxxxhLrqTq"><img src="https://images.weserv.nl/?url=github.com/TyhLxxxhLrqTq.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@TyhLxxxhLrqTq" title="@TyhLxxxhLrqTq" /></a>
<a href="https://github.com/Yulliil"><img src="https://images.weserv.nl/?url=avatars.githubusercontent.com/u/78137234&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@Yulliil" title="@Yulliil" /></a>
<a href="https://github.com/StarWhiteIsBusy"><img src="https://images.weserv.nl/?url=github.com/StarWhiteIsBusy.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@StarWhiteIsBusy" title="@StarWhiteIsBusy" /></a>
</p>

以及每一位贡献者：

<p>
<a href="https://github.com/ech678/Nyxuri/graphs/contributors"><img src="https://contrib.rocks/image?repo=ech678/Nyxuri" alt="贡献者" /></a>
</p>

**参考与借鉴**

- [RanXOM/glassy-niri](https://github.com/RanXOM/glassy-niri)：blur 效果
- [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri)：抄了很多！
- [sanweiya/fcitx5-mellow-themes](https://github.com/sanweiya/fcitx5-mellow-themes)：NyxMellow 的圆角形状
- [StarWhiteIsBusy/Round-Simple-Fcitx5-Skin](https://github.com/StarWhiteIsBusy/Round-Simple-Fcitx5-Skin)：NyxMellow 参考
- [doctorlogix](https://github.com/doctorlogix)：官网设计借鉴

<details>
<summary>名字的小秘密</summary>

读作 `/nɪkˈsuːri/`，是把几样喜欢的东西悄悄拼在一起：

- **Nyx**：夜之女神，陪你过安静的夜晚（也是老名字 NyxNiri 的念想）。
- **Yukkuri**（ゆっくり / にゅっくり）：放轻松，慢慢折腾。
- **Yuri**（百合 / ゆり）：美好的日常和女孩子之间的羁绊（作者的小小私心）。
- **…至于 URI？** 早先在架构文档里硬编过一个唬人的缩写，叫"统一运行时接口 (Unified Runtime Interface)"……忘掉它吧~ QWQ

</details>

---

<div align="right">
<a href="#readme-top">↑ 返回顶部</a>
</div>
