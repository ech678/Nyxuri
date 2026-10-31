# Ubuntu 兼容

> 本页说明 Ubuntu 的依赖供应、安装边界与会话限制，以 `nyxuri/pkg/`、单元 manifest 和 `catalog.toml` 为准；进度只在 [ROADMAP](../ROADMAP.md#u1-ubuntu-2604-兼容) 维护。

## 支持边界

当前适配基线为 Ubuntu 26.04，源码入口沿用 `nyxuri/launcher.sh`，Python 需 3.11+。
其他 Ubuntu 版本或衍生发行版可以识别为 Ubuntu 后端，但不代表其软件源、运行时版本
和桌面行为已经验收。原有 Arch/CachyOS 依赖及 AUR 打包声明继续保留。

- 包管理后端读取 `/etc/os-release`，Ubuntu 使用 `apt-get`、`apt-cache` 和
  `dpkg-query`，不根据 PATH 里偶然出现的 `pacman` 判断发行版。
- 安装前检查已安装状态与当前软件源候选；不自动添加 PPA、导入密钥、刷新索引、
  执行外部安装脚本或编译源码。源索引不可用时先提示用户准备软件源。
- `nyxuri pkg upgrade` 在 Ubuntu 执行普通 APT 升级；`remove` 保留配置，
  不附带 `autoremove`、`purge` 或发行版升级。
- `on <unit>`、CLI/工坊详情、依赖菜单和应用菜单共用平台依赖解析。
  没有 Ubuntu 声明的原生包不会退回 Arch 包名；手动依赖不会作为 APT 包名执行。
- `off` 仍只停用配置并保留软件包，原子部署、Dunder、Vault 和快照契约不变。

引擎目前只支持默认 XDG 根目录布局；自定义配置、缓存、数据或状态根目录会在写入前
明确拒绝，不会自动重置到默认目录。允许的变量取值见
[文件保留契约](file-preservation.md#xdg-根目录边界)。

## 安装方式

在已准备源码的目录中使用仓库自身入口，避免命中旧版本用户级启动器：

```bash
bash nyxuri/launcher.sh list niri
bash nyxuri/launcher.sh pkg search repo kitty
bash nyxuri/launcher.sh pkg info kitty
bash nyxuri/launcher.sh on kitty
```

单元启用会先披露缺失依赖；来源未配置或手动资源缺失时，报告原因，不把单元记为成功启用。
依赖齐全但会话钩子失败时，已经部署的配置保留，事务报告 `partial`，CLI 返回非零，
账本保留 `post_install` 待完成阶段；再次 `on` 会重试，不将会话动作记为完整成功。
手动安装了兼容二进制或资源后，再次启用会重新检测，不需要伪造 dpkg 状态。

`install config` 只部署配置，仍要求用户自行准备运行时。`install full` 在 Ubuntu
安装会话工具链与所选单元依赖，非交互默认不安装未使用的可选应用或 greeter。
会话工具链中的必需手动资源缺失时，已安装的普通包保留，命令报告未完成并返回非零，
不会继续部署配置。普通软件包安装失败或所选单元依赖缺失也会中止后续部署。
所选单元通过统一事务登记；配置模式会留下 `config-only` 待完成阶段，后续 `on`
检查依赖并运行钩子。

Noctalia v5 与旧版基于 Quickshell 的 Noctalia Shell 是不同运行时；Nyxuri 自研
Shell 仍需单独的 Quickshell。

Noctalia 单元附带的 Orbit 使用 GTK3 的 `draw` 信号绘制 Cairo 内容。Ubuntu 将
绘图模块 `python3-cairo` 与 GI 的 Cairo 转换器 `python3-gi-cairo` 分包；两者都需
声明，单独安装 `python3-gi` 和 `python3-cairo` 不保证 GTK 绘图回调可用。

Ubuntu 上除 Quickshell 外，还需安装 Nyxuri Shell 使用的 QML 模块，以及壁纸色板生成所需的
`matugen`、`jq`；启动 QML 不代表主题生成链路可用。具体依赖见
[catalog.toml](../catalog.toml) 的 Quickshell Ubuntu 条目。Qt 共享库不能代替 QML 插件。

Nyxuri Shell 的图标要求 `Material Symbols Rounded` 与 `Material Symbols Outlined`
两个字族，旧 `Material Icons` 不能替代。字体需手动准备并能被 Fontconfig 识别；
依赖流程只检测，不下载或安装字体。可使用 Google 提供的预编译 TTF：
[Rounded](https://github.com/google/material-design-icons/blob/master/variablefont/MaterialSymbolsRounded%5BFILL%2CGRAD%2Copsz%2Cwght%5D.ttf)、
[Outlined](https://github.com/google/material-design-icons/blob/master/variablefont/MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D.ttf)。

## 依赖供应

包名、手动资源与平台支持声明以单元 manifest 和 [catalog.toml](../catalog.toml)
为准，不以某台机器的软件源状态推断其他安装环境。安装前使用 `pkg info` 或
`apt-cache policy` 检查当前源和缓存中的候选；无候选时先准备来源，再执行安装。

- Niri、Noctalia、Quickshell 等声明了额外 APT 来源要求的软件，需要预先配置兼容来源；
  Nyxuri 不自动添加来源或导入密钥。
- 手动二进制依赖安装后应能由对应命令探针发现；字体与 Rime 等资源按资源探针检查。
  `mpvpaper` 在应用目录中作为可选视频壁纸能力供给，不属于 Ubuntu 必需工具链；
  缺失时视频壁纸不可用，不影响静态壁纸部署与完整安装的其他部分。
  JetBrains Nerd Font 仍是必需的手动字体资源，普通 JetBrains Mono 不能替代。
- Flatpak 应用使用目录中声明的 app ID，不转换为原生包名。
- Mango 和 Shelly 当前未声明 Ubuntu 支持；不要套用 Arch 安装或构建流程。
- Greeter 服务与显示管理器切换应单独安排，不属于普通依赖安装。

Fish 单元显式供给 Fisher 下载与解包所需的 `curl`、`tar`；从已准备的源码执行安装时，
不能依赖首次引导脚本或其他软件已顺带安装这些工具。

切换到 Nyxuri Shell 前先检查实际 Quickshell、平台包、字体和隔离 QML 导入探针。
失败时显示具体原因并保留当前 Shell；检查过程及运行时选择见
[Shell 开发指南](shell/development.md)。

### Greeter

`nyxuri on greeter` 使用已配置 APT 源提供的 `greetd` 与 `noctalia-greeter`。
Ubuntu 26.04 的 Noctalia 源需包含 `resolute-backports/`，以供给 Greeter 及其
wlroots 运行库；仍由用户准备来源，Nyxuri 不自动添加软件源或刷新索引。
Ubuntu 包通过 systemd 覆盖项读取 `/etc/greetd/noctalia-greeter.toml`，使用 `_greetd`
用户；启用前核对该配置、状态目录属主和 systemd 实际启动命令，不覆盖包内配置、VT
或会话选择。布局不一致时停止并报告，先修复软件包或已有服务覆盖项再重试。

启用只切换下次启动使用的显示管理器，不停止当前会话；原选择保存在
`/etc/greetd/nyxuri-display-manager`。外观同步规则仅允许本地活动会话中的 `sudo`
组成员免密同步。`nyxuri off greeter` 恢复原显示管理器和原 polkit 规则，保留软件包、
包内 TOML 与 `/var/lib/noctalia-greeter` 外观数据；接管前已经使用 greetd 时仍保持
greetd，原来没有显示管理器时恢复为不启用。恢复记录缺失或无效时拒绝猜测。

Greeter 首次安装前已经运行的 Noctalia 可能尚未注册 `greeter-sync`。安装后重新启动
Noctalia 或重新登录，再运行 `noctalia msg greeter-sync`；CLI 帮助列出该命令不代表
当前实例已经提供接口。`shell.greeter_sync.auto_sync = true` 时，后续壁纸、配色及深浅
模式变化由 Noctalia 自动同步；登录界面在下次启动时读取同步结果。

## Niri 会话行为与限制

Portal 单元向共享配置目录逐文件部署。只有已启用且当前平台支持的 WM 才获得对应
`niri-portals.conf` 或 `mango-portals.conf`；支持多个已启用 WM 共存，不依据当前会话
选择唯一规则。开关 WM 会同步已经启用的 Portal 单元，不自动启用它。
不再部署通用 `portals.conf`：历史版本未修改的受管文件先备份再退役，个人修改和未知文件
保留并报告。GNOME 等桌面的自有路由不受管；规则改变后需重新登录使会话重新采用配置，
Nyxuri 不在开关单元时重启 Portal 后端。

Niri 配置在登录时显式启动 GTK portal。该后端提供暗色偏好等接口；退出会话时遗留的
D-Bus 激活等待可能使新会话中的 GTK 应用启动缓慢或首次主题不正确。
`niri --session` 导入显示环境后，`spawn-at-startup` 向 systemd 提交后端启动任务，
不阻塞 Shell，也不重启已运行的服务。

自研 Shell 的可选功能限制见 [Shell 已知问题](../shell/KNOWN-ISSUES.md)。

Niri 26.04 未实现 GNOME portal 使用的 `InteractiveScreenshot` 接口；
`interactive=true` 截图请求会失败。非交互全屏截图与 Niri 自身截图快捷键是不同入口。

Niri 26.04 的 portal 全屏截图接口只接受单输出，双屏会失败；可使用普通 Niri
单屏截图路径。限制依据 [Niri 26.04 源码](https://github.com/niri-wm/niri/blob/v26.04/src/niri.rs#L5298-L5310)，
不能据此推断其他版本或所有截图接口都存在同样限制。

同一版本的 Portal 截图保存分支直接创建文件；若默认的 `图片/Screenshots` 尚不存在，
它会记录 `error creating file` 并在完成回调前返回，导致请求等待。这与普通快捷键截图
会准备父目录的分支不同，见 [Niri 26.04 源码](https://github.com/niri-wm/niri/blob/v26.04/src/niri.rs#L5335-L5358)。
Nyxuri 在 Niri 默认模板成功落地并完成路径渲染后，显式创建本地化图片目录下的
`Screenshots` 容器；纯模板渲染不执行此动作，个人 carry 配置和非默认截图路径不改。
目录创建失败会让事务保留未完成状态。该目录与实际截图属于用户数据，不登记为单元产物，
也不随 Niri 停用删除。该准备解决缺失目录导致的保存失败，不解除上述多输出限制。

## Fcitx 配置与旧布局迁移

`fcitx5-rime` 将配置部署到 Fcitx 实际读取的 `~/.config/fcitx5`，按共享目录处理；
`profile` 与 `conf/classicui.conf` 沿用保留声明，目录中的其他输入法配置不被整体替换。
hook 管理用户数据目录中的皮肤与 Rime 方案，资源检测通过仍不等于会话中输入法已启动。

Niri 模板在自身 `environment` 中设置 `GTK_IM_MODULE "fcitx"`，让其启动的 GTK 应用
走 Fcitx GTK 模块。
[Fcitx 官方说明](https://fcitx-im.org/wiki/Using_Fcitx_5_on_Wayland#Gtk3_/_Gtk4)
允许 GTK3/4 使用原生 text-input-v3 或 Fcitx 模块。此兼容选择只写入 Niri 配置，
不修改登录 profile、GTK 共享设置或 systemd 全局环境，避免改变 GNOME 会话的输入法。
[Niri 环境说明](https://niri-wm.github.io/niri/Configuration%3A-Miscellaneous.html#environment)
明确其环境配置仅传给 Niri 启动的进程；由 systemd / D-Bus 激活的应用不保证继承，
需按实际启动路径单独验收。配置变更后应重新启动相关应用；已有个人 Niri 配置仍按
保留规则处理，不自动覆盖。此设置也不自动改写个人 Fcitx `profile`、添加 Rime 或选择方案。

已有账本的旧 `~/.config/fcitx5-rime` 布局在启用或刷新时迁移；先备份旧区、新区、
账本与 Vault，再复制有归属证据或保留协议覆盖的文件。目标冲突默认保全双方并记待完成，
明确 force 后采用旧生效区内容；同轮模板刷新不会再覆盖迁移过来的个人修改。
无账本的旧目录不自动认领。迁移重试、停用与回滚边界见
[文件保留](file-preservation.md#共享目录布局迁移)。

## 数据声明与维护

平台字段含义以 [manifest-schema](manifest-schema.md#平台依赖覆盖) 为准。
`ModuleManifest` 与 `CatalogEntry` 的原始包字段始终保留 Arch 声明；只有运行时消费者
调用 `resolve_requirements()` 选择本机平台。`packaging/gen-deps.py` 继续读取原始字段，
在 Ubuntu 上生成 AUR 元数据也不能混入 Debian 包名。
