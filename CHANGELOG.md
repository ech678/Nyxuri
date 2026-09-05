# Changelog

此文件记录 NyxNiri 每个版本中用户可感知的重要变化。

格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Fixed
- 已配置全局免密 sudo 的安装不再索要从未设置的密码
- 笔记本亮度键调节内屏背光，外接显示器仍用原来的 DDC 方式
- 壁纸选择器支持生成带透明通道图片的缩略图

## [v3.0.4] - 2026-08-29

### Added
- se 的 AUR 搜索支持 shelly，没有 paru/yay 的机器也能搜
- 常用软件菜单重做：应用按用途分组、可折叠浏览，新增 Brave、VS Code、Steam、微信、QQ 等 15 款
- 微信、QQ、Spotify 改走 Flatpak 安装，需要的组件自动配好
- update 支持 --to 指定标签或提交号:多台机器可锁到同一版本,先在一台验证再整体推进;无标签环境的版本显示改为回退当前提交号,不再显示陈旧的固定版本号
- 设置 NYXNIRI_REPO 环境变量即可让安装与更新走自己的仓库源(fork 或内网镜像),不设置则一切照旧
- 非 Arch 发行版上运行安装或依赖菜单会直接说明情况并告知手动取用配置的方法,不再刷一屏 pacman 报错
- fish 终端里 nyxniri 的 Tab 补全覆盖全部命令与别名,预设和快照序号也能动态补出

### Changed
- Noctalia 顶栏左侧新增 CPU 与内存胶囊指示，右侧精简图标排列，调整日期格式
- se/un 的 fzf 界面去掉 emoji
- fish 里 Ctrl+V 改为粘贴系统剪贴板（原先被 fzf 变量搜索占用），kitty 与 zed 的粘贴体验从此一致
- 依赖检测与配置部署减少重复扫描和探测，安装流程更利落
- 预设管理界面改为树状折叠，可直接展开预设并在底部按 Tab 查看包含的文件与保留项。
- 系统诊断结果按类别分组呈现，末尾增加检查项统计。
- 配置快照回滚改为交互菜单单选。
- 壁纸选择器按 Material You 重做(还在打磨)，移除随机切换
- clean-cache 重做：勾选要清理的项目后回车执行（默认全选、TRIM 除外），支持 --only 指定项目，脚本改名 clean-cache.py

### Fixed
- se 搜 AUR 失败时会显示具体原因，不再无声地返回空列表
- 注销后残留的 Noctalia 进程不再占住旧 niri 会话，重新登录后顶栏会正常启动
- 选装 Fcitx5 Rime 后会立即启动，之后进入 niri 也会自动运行，不再出现安装成功却无法输入的情况
- clean-cache 试运行不再索要密码，也只展示清理计划不再动手
- 开启自动确认后，深度清理、删除快照、放弃本地改动仍会逐一询问
- orbit 启动器不再向身份不明的进程发送结束信号
- orbit 菜单项不再执行 shell 命令串，复杂命令请包成脚本再填路径
- 登录界面切换或安装失败时会保留原登录管理器与配置备份
- 预设活动状态中的路径穿越、绝对路径、符号链接和异常内容现在会冻结原配置并给出警告，不再回退默认预设
- NyxNiri 只会替换或删除自身创建的命令链接，不再碰同名文件、目录或其他链接
- 并发运行安装、部署、回滚或卸载时不会互相破坏锁定状态
- 找不到 AUR 助手且官方仓库没有 paru 时不再自动构建
- Fish 插件现在固定到已审查版本，卸载只清理 NyxNiri 安装的文件
- 从任意目录启动安装时不再加载同名伪造程序，避免干扰安装
- 依赖检测、系统诊断与插件更新等外部调用增加超时保护，遇到弱网或服务无响应时自动跳过并继续，不再卡死或中断安装。
- 更新成功后改用刚更新的新代码完成后续部署，跨版本更新不再带着旧程序跑到一半崩溃。
- 更新中途被打断或程序文件缺失时，给出一句话恢复指引，不再甩出大段报错。
- 切换 niri 配置时显示器不再闪一下:用户的 monitor.kdl 现在在替换前就放进新配置目录,不再先换成默认空文件再事后拷回。
- 检查更新后若自动重启失败,不再误报"更新失败",改为提示手动重新运行。
- 诊断报告改为并行收集系统信息,生成速度明显变快。
- 快照数量上限 30 个,超出自动清理最旧的,不再无限堆积。
- fisher 插件列表没变时不再重复跑网络更新。
- 配置差异查看器在系统没装 less 时改为直接输出,不再静默失败。

## [v3.0.3] - 2026-08-26

### Added
- 配置预设：支持多套风味变体的应用（如 kitty 透明）可一键切换，切换不影响你的自定义修改；也能把当前配置存成私有预设，或直接在编辑器里改。
- 卸载改为勾选清单：可逐项选择清理哪些，默认勾选等同原标准卸载范围；管道模式下默认全选并归档配置。
- fisher 现可作为模块单独查询状态或卸载（nyxniri fisher ...），归类与 fcitx/greeter/gtk 一致。

### Changed
- 引导脚本的报错与配色跟随系统语言并统一为主程序色阶。
- 控制面板重新分组（部署 / 管理 / 诊断 / 扩展），「可选模块」改为「扩展」并补齐 GTK 主题与 fisher 的菜单入口；深度清理并入卸载流程。
- 统一全项目文案：壁纸包、登录界面等一物一名；过程行统一用「安装」；英文菜单去除冗余括号与工程名。

### Fixed
- 检查更新与安装时的网络命令增加连接与整体超时，弱网或镜像无响应时不再卡死。
- GTK4 应用（Nautilus、GTK Demo 等）标题栏的最小化、最大化、关闭按钮不再显示成同心圆。
- 卸载时不再残留 fisher 与其插件、Noctalia Greeter 的系统状态目录、历史归档目录、以及被改过的 fcitx 快捷短语设置。
- 标准卸载现在也会清理 Noctalia Greeter（之前只在深度清理时清理）。
- 修复交互菜单里按住或自动重复的回车会残留并级联到下一个提示的问题（卸载确认后自动滚屏、甚至误触发安装）；确认提示改为单键响应，不再需要按回车。

## [v3.0.2] - 2026-08-24

### Fixed
- 检查更新时报 `key does not contain a section: --progress` 错误的问题。

## [v3.0.1] - 2026-08-24

### Added
- GTK3 和 GTK4 应用现在跟随壁纸自动切换 Material You 配色。

### Changed
- 壁纸选择器重写，缩略图改为按需加载。

### Fixed
- 切换深浅色模式后 Kitty、Nautilus 等应用跟随延迟数秒甚至不跟随的问题。
- 非交互式环境下运行 `nyxniri uninstall` 不再意外执行卸载。
- 配置写入失败时不再导致配置丢失。
- 推荐应用菜单中 Mission Center 和 Fcitx5 现在能正确安装。
- 安装 Fcitx5 后自动部署 NyxMellow 皮肤。
- mpvpaper 内存泄漏检测恢复，并可以一键升级到修复版。
- 更新仓库后自动检查并提示安装新增依赖。
- 系统诊断恢复音频、亮度、门户、磁盘空间等检查项。
- 诊断报告恢复显示器、工具版本、守护进程状态、系统日志等信息。
- `nyxniri update --force` 重新恢复壁纸和登录界面的完整部署。
- 从控制面板更新后新代码立即生效，不再需要手动重启。
- `nyxniri install config` 恢复壁纸同步和模块勾选项。
- 标准卸载现在会一并清理 NyxMellow 皮肤。
- 登录界面免密规则重新限制为管理员组，与旧版一致。
- 非交互模式下仓库有本地改动时不再误报更新成功。
- 壁纸包下载不再覆盖用户已自定义的同名壁纸。
- 护眼模式快捷切换留下的失效链接现在能自动修复。
- Fish 的 Tab 补全恢复，不再只采纳历史建议而无法补全文件路径。

## [v3.0.0] - 2026-08-22

### Added
- 配置快照现在支持在列表中批量勾选删除。
- 壁纸选择器在搜索框为空时支持使用左右方向键在网格中横向切换。

### Changed
- 安装与维护逻辑改为 Python 3.10+ 标准库实现，无需安装 pip 依赖。
- 源码目录统一为 `configs/`、`assets/` 和 `nyxniri/`。
- 旧版 Bash 用户必须重新运行新版安装引导后再更新，现有配置与新旧快照均会保留。
- 控制面板适配窄终端与中英文宽字符，长路径和快照备注会收拢显示，退出时恢复光标。
- 拉取主仓库和壁纸包时会在交互终端显示 Git 实时进度，自动化运行保持安静。

### Removed
- 仓库不再提供旧版 Bash 更新入口和旧目录镜像。

### Fixed
- 修复动态壁纸受用户 mpv 配置着色器影响导致播放崩溃或无法循环的问题。
- 修复快速连续打开壁纸选择器导致窗口抖动以及鼠标静止时悬停偶尔不触发的问题。
- 未知命令和无效参数不再误入安装流程，安装、更新或壁纸下载失败时会返回非零状态。
- 壁纸包下载后会检查实际内容，完成页会准确区分完整包、已有壁纸、内置壁纸和下载失败。
- 非交互安装不再等待 sudo 密码，权限不足时会直接退出并说明原因。
- 深度清除配置、快照、缓存与壁纸前会明确警告并要求确认。
- CLI 帮助、`nyxhelp` 与 Fish 补全已按实际命令统一，补上 `--no-deploy` 并过滤无效快照目录。

## [v2.3.4] - 2026-08-21

### Added
- 新增统一的静态与动态壁纸选择器，支持搜索、分类和中文输入。
- Orbit 启动器新增壁纸入口。
- Niri 会自动隐藏 Wine 与 Proton 程序产生的居中占位黑条。

### Changed
- `Super+W` 统一打开壁纸选择器，移除 `Super+Shift+W`。
- Starship 改为双行提示符，与 Fastfetch 使用一致的配色，并识别 CachyOS。

## [v2.3.3] - 2026-08-19

### Added
- 新增 `Super+Ctrl+W` 随机切换壁纸。
- 新增 `Super+G` 切换列标签页模式。
- 新增 `Super+Shift+T` 在平铺层与浮动层之间切换焦点。
- 浏览器与文件管理器现在会跟随系统深浅主题。
- 新增 `nyxniri theme` 主题控制命令，并补全 `nyxhelp` 与 `nyxniri` 的 Fish 补全。

### Changed
- Fastfetch 改为更紧凑的信息布局，并加入 STAY LIBRE 标题。
- 退出 Niri 的快捷键从 `Super+Shift+E` 改为 `Super+Shift+Q`。
- `Super+Shift+上下方向键` 现在用于调整同列窗口顺序。

### Fixed
- 修复缺少完整桌面环境时 GTK 4、浏览器与文件管理器主题不同步或卡住的问题。

## [v2.3.2] - 2026-08-18

### Added
- Orbit 启动器支持按住快捷键滑向目标后松手启动，并可直接输入字母开始搜索。

### Fixed
- 修复 Scratchpad 终端无法使用鼠标滚轮查看历史的问题。
- 修复 `nyxniri install config` 被当作全量安装的问题。

## [v2.3.1] - 2026-08-16

### Added
- Orbit 启动器新增可切换 DeepSeek、ChatGPT、Claude、Google 与 Bing 的搜索入口。
- 新增 Nautilus、Mission Center 与 Fcitx5 雾凇拼音的可选安装菜单。
- 更新源码后会检查新增依赖，并允许直接安装缺失项。
- 部署完成页新增常用软件、项目主页与退出入口。

### Changed
- Orbit 启动器快捷键改为 `Super+A` 与 `Super+鼠标前侧键`。
- 安装器和各级子菜单使用一致的导航、返回与退出操作。

### Fixed
- 修复控制面板中更新日志缩进错位的问题。
- 移除子菜单返回与退出时多余的按键等待。

## [v2.3.0] - 2026-08-15

### Added
- 新增 Orbit 矢量启动器，支持应用、文件夹、网页入口和 TOML 自定义。
- 更新或重新部署时会保留 Orbit 启动器的用户配置。
- 新增独立中文 README，并提供中英文切换入口。

### Changed
- Orbit 启动器快捷键改为 `Super+S` 与 `Super+鼠标前侧键`，不再占用浏览器后退侧键。
- 预览媒体移出主仓库，减少源码下载体积。

## [v2.2.4] - 2026-08-13

### Added
- 部署完成页会列出安装结果、保留的配置和下一步操作。
- 更新时会识别本地开发仓库，避免覆盖未提交的代码。

### Changed
- 安装前统一显示组件选择清单，并在部署配置前处理依赖。
- 安装器统一状态标记，并调整中英文菜单对齐。

### Fixed
- 修复在菜单中按 Esc 可能误触发部署或退出控制面板的问题。
- 修复更新日志被菜单刷新覆盖的问题。

## [v2.2.3] - 2026-08-12

### Changed
- Noctalia V5 改从 Arch 官方仓库安装，不再要求 AUR helper。

### Fixed
- 修复切换主题或同步壁纸时意外弹出身份验证的问题。

## [v2.2.2] - 2026-08-11

### Changed
- 调整终端界面的留白、列表间距和标题对齐。
- Scratchpad 快捷键改为 `Super+~`，避免与 Fcitx5 快速输入冲突。

### Fixed
- 修复通过管道或自动化脚本部署时等待键盘输入的问题。

## [v2.2.1] - 2026-08-10

### Added
- 安装与更新支持按组件选择，并在更新前默认创建配置快照。
- 配置覆盖前可以查看当前配置与新版本的差异。
- Fish 的 `se` 支持 `aur` 和 `pac` 搜索前缀。

### Changed
- 部署前集中显示变更清单并获取 sudo 权限，安装过程中不再重复询问。
- 安装器统一标题、列表和状态提示的排版。

### Fixed
- 修复锁文件残留导致再次运行安装器时无法继续的问题。

## [v2.2.0] - 2026-08-09

### Added
- 新增基于 tmux 的 Scratchpad 浮动终端，可跨工作区呼出并保留会话。
- `nyxniri doctor` 新增 Scratchpad 与 tmux 检查。

### Changed
- 默认启用触摸板与鼠标的打字防误触。
- 移除未使用的 `fd` 与 `bat` 依赖。

## [v2.1.20] - 2026-08-07

### Fixed
- 修复全新安装后 JetBrains Mono 字体回退的问题。
- 修复护眼模式快速连按时状态冲突，以及重新登录后特效和色温未恢复的问题。

## [v2.1.19] - 2026-08-06

### Added
- Fish 会自动加载 `__custom__/` 目录中的用户脚本。
- `clean` 新增孤立包清理与无需逐项确认的 `-y` 模式。

### Changed
- 完整壁纸包移至独立仓库，主仓库只保留一张内置壁纸。
- 壁纸包改为按需下载，并在已有完整包时跳过重复下载。
- 下载壁纸包时会依次尝试官方地址和备用镜像。

## [v2.1.18] - 2026-08-05

### Added
- 新增 `nyxniri snapshot delete` 删除配置快照。
- 安装结束后会显示本次部署结果。

### Changed
- 安装 NyxMellow 皮肤前会明确征求同意，不再自动修改输入法设置。

## [v2.1.17] - 2026-08-03

### Added
- 新增 NyxMellow Fcitx5 皮肤，可跟随 Noctalia 配色与深浅模式变化。

## [v2.1.16] - 2026-08-02

### Added
- 新增 Noctalia Greeter 可选安装模块。
- 缺少 paru 或 yay 时，安装器可以自动安装 paru。

### Changed
- Niri 配置拆分为核心、布局、动画和规则文件。
- 输入设备配置移至 `input__custom__.kdl`，更新时会保留用户修改。

## [v2.1.15] - 2026-08-02

### Fixed
- Fish 的 `up`、`in`、`se` 与 `un` 会按可用包管理器运行，并在命令不可用时回退。
- 安装器会拒绝删除空路径、根目录或用户主目录。
- 修复 Noctalia 外观同步的 Polkit 授权规则未生效的问题。

## [v2.1.14] - 2026-07-31

### Fixed
- 在纯 TTY 中禁用 Nerd Font 图标，避免提示符和文件列表出现方框乱码。

## [v2.1.13] - 2026-07-31

### Fixed
- 修复 `curl | bash` 安装时标准输入被管道占用，导致菜单直接跳过的问题。

## [v2.1.12] - 2026-07-31

### Changed
- 用户配置文件支持无扩展名和数字前缀排序，并扩展到 Kitty 配置。

### Fixed
- 修复字体名称包含空格时被误判为未安装的问题。

## [v2.1.11] - 2026-07-30

### Added
- 部署更新时会保留名称中含 `__custom__` 的用户文件和目录。

### Changed
- 源码下载失败时会自动尝试备用节点。

## [v2.1.10] - 2026-07-30

### Added
- 源码下载会依次尝试官方地址、Fastly CDN 和国内镜像。
- Starship 提示符新增代理状态标记。

### Changed
- 网络操作会显示 HTTP 状态与耗时，并写入安装日志。

## [v2.1.9] - 2026-07-29

### Added
- 部署时会自动识别新加入的配置模块。
- 更新配置时可以选择直接覆盖或先备份再覆盖。

### Changed
- 安装器移除装饰性 Emoji，统一使用简洁的状态标记。

## [v2.1.8] - 2026-07-28

### Added
- 新增基于 fzf 的 `nyxhelp` 命令，用于查询快捷键和常用命令。
- `proxy_on` 支持临时指定代理端口或地址。

## [v2.1.7] - 2026-07-27

### Added
- 新增自动锁屏、息屏与睡眠的空闲超时设置。

### Changed
- 方向键导航可以在窗口、屏幕和工作区边界之间继续移动。

### Fixed
- 修复护眼模式显示状态与实际进程不一致的问题。
- Qt 应用在 Wayland 不可用时会回退，避免直接退出。

## [v2.1.6] - 2026-07-26

### Added
- 新增 `nyxniri bug-report`，用于导出系统环境与关键日志。

### Fixed
- NVIDIA 专用环境变量改为检测到 NVIDIA 显卡后启用，避免 AMD、Intel 和虚拟机启动 Niri 时黑屏。

## [v2.1.5] - 2026-07-25

### Added
- 护眼模式新增 wlsunset 色温调节和 Noctalia 状态提示。

### Fixed
- 修复切换护眼模式时画面闪烁和撕裂的问题。

## [v2.1.4] - 2026-07-24

### Added
- 新增 `Super+N` 护眼模式，可关闭模糊、提高背景不透明度并降低色温。

## [v2.1.3] - 2026-07-23

### Added
- 新增 `nyxniri snapshot` 与 `nyxniri rollback`，用于备份和恢复配置。
- 新增 `nyxniri purge`，用于清除 NyxNiri 配置和相关文件。

## [v2.1.2] - 2026-07-22

### Added
- 新增 mpvpaper 动态壁纸与视频轮播。
- 新增 `nyxniri doctor`，用于检查音频、亮度服务和桌面组件状态。

## [v2.1.1] - 2026-07-21

### Fixed
- 修复只有 pacman、没有 AUR helper 时在线安装无法继续的问题。

## [v2.1.0] - 2026-07-20

### Changed
- 压缩并合并壁纸资源，减少源码下载体积。

## [v2.0.2] - 2026-07-18

### Added
- 安装脚本支持独立在线运行、自更新和国内镜像回退。
- 部署前可以选择是否备份现有配置。
- 安装器会检查字体包和 Niri 会话文件。
- Fish 新增自动配对与 fzf 补全，Kitty 新增常用编辑和字号快捷键。

### Changed
- Noctalia 配置目录统一为 `v2/`，避免旧目录名中的特殊字符影响 Shell 命令。

### Removed
- 主分支移除旧版 DMS 配置，只保留 Noctalia V5 配置。

## [v2.0.1] - 2026-07-16

### Added
- Fish 新增 `clean` 系统与用户缓存清理工具。

### Changed
- 配置与壁纸改为复制到用户目录，不再从仓库建立软链接。
- 壁纸路径会跟随系统的 Pictures 目录，并替换配置中的固定用户路径。
- 同一天已有配置备份时，安装器会先询问是否再次备份。

## [v2.0.0] - 2026-07-15

### Added
- 首次发布基于 Niri 与 Noctalia V5 的 NyxNiri 桌面配置。

[Unreleased]: https://github.com/ech678/NyxNiri/compare/v3.0.4...HEAD
[v3.0.4]: https://github.com/ech678/NyxNiri/compare/v3.0.3...v3.0.4
[v3.0.3]: https://github.com/ech678/NyxNiri/compare/v3.0.2...v3.0.3
[v3.0.2]: https://github.com/ech678/NyxNiri/compare/v3.0.1...v3.0.2
[v3.0.1]: https://github.com/ech678/NyxNiri/compare/v3.0.0...v3.0.1
[v3.0.0]: https://github.com/ech678/NyxNiri/compare/v2.3.4...v3.0.0
[v2.3.4]: https://github.com/ech678/NyxNiri/compare/v2.3.3...v2.3.4
[v2.3.3]: https://github.com/ech678/NyxNiri/compare/v2.3.2...v2.3.3
[v2.3.2]: https://github.com/ech678/NyxNiri/compare/v2.3.1...v2.3.2
[v2.3.1]: https://github.com/ech678/NyxNiri/compare/v2.3.0...v2.3.1
[v2.3.0]: https://github.com/ech678/NyxNiri/compare/v2.2.4...v2.3.0
[v2.2.4]: https://github.com/ech678/NyxNiri/compare/v2.2.3...v2.2.4
[v2.2.3]: https://github.com/ech678/NyxNiri/compare/v2.2.2...v2.2.3
[v2.2.2]: https://github.com/ech678/NyxNiri/compare/v2.2.1...v2.2.2
[v2.2.1]: https://github.com/ech678/NyxNiri/compare/v2.2.0...v2.2.1
[v2.2.0]: https://github.com/ech678/NyxNiri/compare/v2.1.20...v2.2.0
[v2.1.20]: https://github.com/ech678/NyxNiri/compare/v2.1.19...v2.1.20
[v2.1.19]: https://github.com/ech678/NyxNiri/compare/v2.1.18...v2.1.19
[v2.1.18]: https://github.com/ech678/NyxNiri/compare/v2.1.17...v2.1.18
[v2.1.17]: https://github.com/ech678/NyxNiri/compare/v2.1.16...v2.1.17
[v2.1.16]: https://github.com/ech678/NyxNiri/compare/v2.1.15...v2.1.16
[v2.1.15]: https://github.com/ech678/NyxNiri/compare/v2.1.14...v2.1.15
[v2.1.14]: https://github.com/ech678/NyxNiri/compare/v2.1.13...v2.1.14
[v2.1.13]: https://github.com/ech678/NyxNiri/compare/v2.1.12...v2.1.13
[v2.1.12]: https://github.com/ech678/NyxNiri/compare/v2.1.11...v2.1.12
[v2.1.11]: https://github.com/ech678/NyxNiri/compare/v2.1.10...v2.1.11
[v2.1.10]: https://github.com/ech678/NyxNiri/compare/v2.1.9...v2.1.10
[v2.1.9]: https://github.com/ech678/NyxNiri/compare/v2.1.8...v2.1.9
[v2.1.8]: https://github.com/ech678/NyxNiri/compare/v2.1.7...v2.1.8
[v2.1.7]: https://github.com/ech678/NyxNiri/compare/v2.1.6...v2.1.7
[v2.1.6]: https://github.com/ech678/NyxNiri/compare/v2.1.5...v2.1.6
[v2.1.5]: https://github.com/ech678/NyxNiri/compare/v2.1.4...v2.1.5
[v2.1.4]: https://github.com/ech678/NyxNiri/compare/v2.1.3...v2.1.4
[v2.1.3]: https://github.com/ech678/NyxNiri/compare/v2.1.2...v2.1.3
[v2.1.2]: https://github.com/ech678/NyxNiri/compare/v2.1.1...v2.1.2
[v2.1.1]: https://github.com/ech678/NyxNiri/compare/v2.1.0...v2.1.1
[v2.1.0]: https://github.com/ech678/NyxNiri/compare/v2.0.2...v2.1.0
[v2.0.2]: https://github.com/ech678/NyxNiri/compare/v2.0.1...v2.0.2
[v2.0.1]: https://github.com/ech678/NyxNiri/compare/v2.0.0...v2.0.1
[v2.0.0]: https://github.com/ech678/NyxNiri/releases/tag/v2.0.0
