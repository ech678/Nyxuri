<a id="readme-top"></a>

<div align="right">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</div>

<div align="center">

<h1>NyxNiri</h1>

<p><strong>Arch / CachyOS 上的 Material You 桌面体验</strong><br />
<sub>基于 Niri 和 Noctalia V5 —— 然后闭嘴！</sub></p>

<p>
  <a href="https://github.com/ech678/NyxNiri/stargazers"><img height="22" src="https://m3-markdown-badges.vercel.app/stars/3/3/ech678/NyxNiri" alt="Stars" /></a>
  &nbsp;
  <a href="https://archlinux.org"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/Arch/arch2.svg" alt="Arch Linux" /></a>
  &nbsp;
  <a href="LICENSE"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/LicenceGPLv3/licencegplv33.svg" alt="GPL-3.0" /></a>
</p>

<a href="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be">
  <img src="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be" alt="NyxNiri 预览" width="92%" />
</a>

<p>
  <sub><em><a href="https://nyxniri.com">官网</a> · 观看 <a href="https://www.bilibili.com/video/BV1c63n6dEEG">Bilibili 演示</a> · 参与 <a href="https://www.reddit.com/r/niri/comments/1vf53le/nyxniri_a_material_you_desktop_config_for_niri/">Reddit 讨论</a></em></sub>
</p>

</div>

## 特性

- **壁纸选择器**（`Super+W`）— 静态和动态壁纸统一选择，支持搜索和分类。
- **色彩联动** — Noctalia V5 直接从壁纸取色；动态壁纸由 `mpvpaper` 配合 `ffmpeg` 抽帧。
- **明暗同步** — GTK 3/4、XDG Portal、Kitty、浏览器一起跟随主题切换。
- **护眼模式**（`Super+N`）— 暖色温、关模糊、纯色不透明窗口。
- **Scratchpad**（`Super+~`）— 随时呼出的 Kitty 持久浮动终端。
- **Orbit 启动器**（`Super+A` / `Super+鼠标前侧键`）— 矢量星环；应用、工具、网页、AI/搜索轮盘，全 TOML 自定义。
- **Shell 和终端** — Fish 代理/缓存别名，Kitty 光标轨迹，Windows 风格快捷键。
- **NyxMellow** — 动态 fcitx5 皮肤：mellow 圆角 + Noctalia Material You 配色。
- **配置预设** — 每个应用多套风味变体（如 kitty 透明）；一条命令切换，把当前配置存为私有预设，或直接在 `$EDITOR` 里改。

## 安装

> [!IMPORTANT]
> **从旧版 Bash 目录（`lib/` + `v2/`）升级：**旧版 `nyxniri update` 无法直接切换到新版 Python 目录。更新前请先运行一次新版引导。现有配置、`~/.config/NyxNiri/backups/` 和旧版 `~/.config/dotfiles_backup_*` 快照都会保留。

### 独立在线安装

```bash
curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

> [!TIP]
> 没有 AUR helper 时，`nyxniri install full` 会自动装好 `paru`。

### 从 Git 仓库安装（推荐）

```bash
# 浅克隆：只拉最新快照；要完整历史去掉 --depth 1
git clone --depth 1 https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

### 系统包安装（AUR）

> 即将支持——`paru -S nyxniri-git`，更新由 pacman 管理。

<details>
<summary>国内镜像加速（gh-proxy / CDN）</summary>

```bash
# 通过 gh-proxy.org 独立安装
curl -fsSL --connect-timeout 10 https://gh-proxy.org/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash

# 通过 gh-proxy.org 克隆仓库
git clone --depth 1 https://gh-proxy.org/https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

拉取仓库时，`install.sh` 先走 GitHub，失败再走 gh-proxy。
</details>

## 包含配置

```text
NyxNiri
├── install.sh                  # 极简引导入口
├── nyxniri/                    # Python 核心引擎（零 pip 依赖）
├── assets/                     # 静态资产（壁纸、fcitx5 皮肤模板）
└── configs/
    ├── niri/                   # 窗口管理器（.kdl、.toml）
    │   └── scripts/            # Orbit 启动器、壁纸选择器、Scratchpad 脚本
    ├── noctalia/               # 桌面 Shell 与主题同步
    ├── xdg-desktop-portal/     # Portal 路由（主题与录屏分流）
    ├── kitty/                  # 终端
    ├── fish/                   # 别名与函数
    ├── fastfetch/              # 系统信息
    ├── zed/                    # 编辑器
    └── starship.toml           # 提示符
```

> [!NOTE]
> 配置采用原子部署。个人改动通过 Dunder 协议保留：
> - `*__custom__*` 文件（如 `01__custom__.kdl`）和目录自动保留——数字前缀控制加载顺序。
> - `~/.config/niri/monitor.kdl` 在部署时保留。

## 预设

有些应用自带多套风味——`kitty` 默认就带一个 `transparent` 透明预设。预设叠在默认配置和你的 `__custom__` 之间，切换不会碰你的自定义改动。

| 指令 | 作用 |
| :--- | :--- |
| `nyxniri preset <app> list` | 列出预设（`*` 标当前活动） |
| `nyxniri preset <app> apply <name>` | 切换预设（`apply default` 回默认） |
| `nyxniri preset <app> save <name>` | 把当前配置存为私有预设 |
| `nyxniri preset <app> edit <name>` | 在 `$EDITOR` 里改私有预设 |
| `nyxniri preset <app> delete <name>` | 删除私有预设（官方预设只读） |

官方预设随 `nyxniri update` 更新；私有预设存在 `~/.config/NyxNiri/presets/`。

## 快捷键

<details>
<summary>窗口控制</summary>

| 快捷键 | 动作 |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>Enter</kbd> | 打开终端 |
| <kbd>Super</kbd> + <kbd>Q</kbd> | 关闭窗口 |
| <kbd>Super</kbd> + <kbd>T</kbd> | 切换浮动/平铺 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>T</kbd> | 平铺层和浮动层之间切换焦点 |
| <kbd>Super</kbd> + <kbd>G</kbd> | 切换标签页列模式（Tabbed Group） |
| <kbd>Super</kbd> + <kbd>F</kbd> | 最大化当前列 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | 全屏 |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | 工作区总览 |
| <kbd>Super</kbd> + <kbd>Z</kbd> / <kbd>C</kbd> | 聚焦左/右列 |
| <kbd>Super</kbd> + <kbd>方向键</kbd> | 焦点移动（跨列 / 跨屏 / 跨工作区） |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>方向键</kbd> | 移动窗口（跨列 / 跨屏 / 跨工作区） |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>方向键</kbd> | 本地微调（含列内调位） |
| <kbd>Super</kbd> + <kbd>D</kbd> / <kbd>U</kbd> | 工作区下/上 |
| <kbd>Super</kbd> + <kbd>Space</kbd> | 切换预设列宽 |
| <kbd>Super</kbd> + <kbd>-</kbd> / <kbd>=</kbd> | 收缩/拉伸列宽 |

</details>

<details>
<summary>系统与组件</summary>

| 快捷键 | 动作 |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>R</kbd> | 启动器 |
| <kbd>Super</kbd> + <kbd>E</kbd> | 文件管理器 |
| <kbd>Super</kbd> + <kbd>X</kbd> | 电源菜单 |
| <kbd>Super</kbd> + <kbd>I</kbd> | 控制中心 |
| <kbd>Super</kbd> + <kbd>V</kbd> | 剪贴板 |
| <kbd>Super</kbd> + <kbd>W</kbd> | 壁纸选择器（静态和动态） |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>W</kbd> | 随机切换壁纸 |
| <kbd>Super</kbd> + <kbd>N</kbd> | 护眼模式 |
| <kbd>Super</kbd> + <kbd>~</kbd> | 切换 Kitty Scratchpad 浮动终端 |
| <kbd>Super</kbd> + <kbd>A</kbd> / <kbd>Super</kbd> + <kbd>鼠标前侧键</kbd> | Orbit 矢量星环启动器 |
| <kbd>Super</kbd> + <kbd>L</kbd> | 锁屏 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | 截图 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> | 重载 Niri |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>Q</kbd> | 退出 Niri |

</details>

> [!TIP]
> 快速查看：`nyxhelp keys`。Niri 完整按键覆盖层按 <kbd>Super</kbd> + <kbd>/</kbd>。

## 扩展

> GTK 主题和 fisher 插件管理器随全量安装自动部署；下面的条目按需启用。

**NyxMellow fcitx5 皮肤：** 圆角 mellow 风格，跟随 Noctalia 配色和明暗。`nyxniri fcitx install` 注册为模板，随主题自动重绘；按需启用，不覆盖现有配置。

<p align="center">
  <img src="https://github.com/user-attachments/assets/3f861e8e-55da-408e-a9d5-7f337a039b74" alt="NyxMellow 皮肤（亮色）" width="48%" />
  <img src="https://github.com/user-attachments/assets/291918e9-4532-480f-b777-7ebe0691eaf9" alt="NyxMellow 皮肤（暗色）" width="48%" />
  <br />
  <sub><em>NyxMellow 皮肤亮色 / 暗色效果</em></sub>
</p>

**壁纸和动态视频包：** 高清壁纸和动态视频（约 100MB）在独立仓库 [wallpaper-collection](https://github.com/ech678/wallpaper-collection)。`install` 时可选拉取，或随时用 `nyxniri wallpapers` 下载。

**Noctalia Greeter：** 和 Noctalia 主题一致的 greetd 登录界面，`nyxniri greeter install` 装 `greetd` + `noctalia-greeter`（AUR），备份现有配置并写入 Polkit 规则，随后切换下次启动使用 greetd，不会中断当前图形会话，切换失败或运行 `nyxniri greeter uninstall` 会恢复原显示管理器

## 工具

`nyxniri` 管理安装、快照和系统诊断。交互式部署默认先在 `~/.config/NyxNiri/backups/` 创建快照。

> 旧版 Bash 用户需先运行上面的新版引导，再用以下命令；旧版 `nyxniri update` 无法完成目录迁移。

**顶层**

| 指令 | 作用 |
| :--- | :--- |
| `nyxniri` | 交互式菜单 |
| `nyxniri test` | 开发者实机测试部署（不备份、保留 monitor.kdl） |

**部署**

| 指令 | 作用 |
| :--- | :--- |
| `nyxniri install [full\|config]` | 全量部署，或只同步配置 |
| `nyxniri update [--force\|--no-deploy]` | 更新源码，并强制部署或跳过配置部署 |

**快照**

| 指令 | 作用 |
| :--- | :--- |
| `nyxniri snapshot [备注]` | 保存当前配置快照 |
| `nyxniri snapshot delete [序号]` | 删除快照（未指定序号则可批量勾选） |
| `nyxniri rollback [序号]` | 恢复历史快照 |
| `nyxniri list` | 查看快照列表 |

**系统**

| 指令 | 作用 |
| :--- | :--- |
| `nyxniri doctor` | 依赖与系统健康检查 |
| `nyxniri deps` | 打开依赖检查与安装菜单 |
| `nyxniri apps` | 常用软件安装菜单（按用途分组：浏览器、社交通讯、游戏等） |
| `nyxniri wallpapers` | 从外部仓库下载全套壁纸和动态视频包 |
| `nyxniri theme [toggle\|dark\|light\|sync\|status]` | 切换或同步系统深浅主题 |
| `nyxniri bug` / `nyxniri report` | 生成诊断报告 |

**卸载**

| 指令 | 作用 |
| :--- | :--- |
| `nyxniri uninstall [--all\|standard\|restore\|purge]` | 勾选式卸载——逐项选择清理内容（配置、CLI、模块、快照、壁纸），默认勾选等同标准范围 |
| `nyxniri purge` | `uninstall --all` 的简写 |

**扩展**

| 指令 | 作用 |
| :--- | :--- |
| `nyxniri fcitx [install\|status\|uninstall]` | NyxMellow fcitx5 皮肤 |
| `nyxniri greeter [install\|status\|uninstall]` | Noctalia Greeter（登录界面） |
| `nyxniri gtk [install\|status\|uninstall]` | Material You GTK3/4 主题 |
| `nyxniri fisher [install\|status\|uninstall]` | Fish 的 fisher 插件管理器 |

`nyxhelp` 是基于 `fzf` 的简明速查，覆盖 CLI、Shell 助手和核心快捷键：

| 指令 | 作用 |
| :--- | :--- |
| `nyxhelp` | 双栏交互式速查菜单 |
| `nyxhelp keys` | Niri 快捷键 |
| `nyxhelp proxy` | 代理控制（`proxy_on [port]`、`proxy_off`、`proxy_status`） |
| `nyxhelp pkg` | 包管理快捷指令（`up`、`in`、`se`、`un`、`clean`） |
| `nyxhelp all` | 完整速查手册 |

## 故障排除

<details>
<summary><b>Noctalia 启动卡死</b> — 多为 <code>ddcutil</code> 扫描 I2C 总线超时（NVIDIA 常见）。</summary>

在 `~/.config/noctalia/noctalia-config.toml` 里禁用 `ddcutil`：

```toml
[brightness]
enable_ddcutil = false
```

亮度键仍然可用：笔记本内屏走 Noctalia 背光，外接显示器继续用 `ddcutil`。除非你希望由 Noctalia 自己管 DDC，否则保持关闭。

</details>

<details>
<summary><b>插件仓库损坏</b> — Noctalia 拉取插件卡住。</summary>

重置插件仓库：

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

</details>

<details>
<summary><b>Greeter 同步要密码</b> — 加一条 Polkit 免密规则（<code>nyxniri greeter install</code> 会自动写入）。</summary>

手动添加 Polkit 规则：

```bash
sudo bash -c 'cat > /etc/polkit-1/rules.d/50-noctalia-greeter.rules << EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.noctalia.greeter.apply-appearance" &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
EOF'
```

</details>

<details>
<summary><b>Nautilus 或 Libadwaita 应用白屏 / 深色模式失效</b> — 旧 CSS 覆盖了系统主题。</summary>

如果之前用过 Noctalia 自带 GTK 模板或其他美化工具，会在 `~/.config/gtk-4.0/` 生成 `noctalia.css` 或 `gtk.css`，GTK4 会优先加载并写死白色背景。

运行主题同步，或手动删掉残留文件：

```bash
nyxniri theme sync
# 或手动删除：
rm -f ~/.config/gtk-4.0/gtk.css ~/.config/gtk-4.0/noctalia.css ~/.config/gtk-3.0/gtk.css ~/.config/gtk-3.0/noctalia.css
```

</details>

<details>
<summary><b>Brave 切换主题后不变色</b> — Brave 冷启动 bug（非 NyxNiri 问题）。</summary>

Brave 在非 GNOME Wayland 上冷启动时，portal 主题信号订阅未正确初始化，`nyxniri theme toggle` 后不变色。去 `brave://settings/appearance` 手动切一次主题模式（如"经典"→"GTK"→"经典"）即可唤醒，此后实时跟随，无需重启 Brave；重启 Brave 后需再次唤醒。

</details>

## 致谢与社区

**联系与社区：**

- TG 频道：[@linux_ricing](https://t.me/linux_ricing)
- QQ：`2040244628` · Linux Ricing 交流群：`631425889`
- 赞助：[爱发电](https://afdian.com/a/Echoes678) · 问题反馈：[GitHub Issues](https://github.com/ech678/NyxNiri/issues)

**协助与鸣谢：**

- [@zhuhuaian](https://github.com/zhuhuaian) · [@Krits03](https://github.com/Krits03) · [@Yulljie](https://github.com/Yulljie) — 社区管理与情感支持
- [@TyhLxxxhLrqTq](https://github.com/TyhLxxxhLrqTq) — 配套壁纸站支持（开发中）

**致谢：**

- [RanXOM/glassy-niri](https://github.com/RanXom/glassy-niri) — blur 效果参考
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
