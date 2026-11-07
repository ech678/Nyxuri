# Overview — 一页仓库地图

> Nyxuri 是精选桌面配置的原子部署引擎，收敛为「桌面插件引擎」：
> 插件（plugins/）× 执行与状态（deploy/ · state/ · system/）× 插件界面（动词面 + TUI 面板）。
> 本页是文件树与分层的一页地图；插件模型契约见 [plugin-model](plugin-model.md)。

## 精神

三条原则（详见 [vision](vision.md)）：**秩序**（每层职责明确）、**做减法**
（一个机制能覆盖两处就用一个）、**无熵**（零 pip 依赖，纯标库，3.11+ 因 tomllib）。

## 仓库地图（P4 终态，散文化与去企味架构）

```
Nyxuri/
├─ nyxuri/            引擎（分工正交的 4 大目录）
│   ├─ deploy/        部署与蓝图：atomic（原子置换+Dunder）· catalog（蓝图发现与依赖排序）·
│   │                 engine（部署执行流与安全网）· forms（形态机制）·
│   │                 manifest · templates · sources · deploy
│   ├─ state/         状态与快照：store（state.json 状态存储）· backup（快照）· uninstall（清理）
│   ├─ system/        系统与桌面集成：env（环境+进程锁+日志）· i18n（双语引擎）·
│   │                 backend（发行版家族与包名映射）· pkg（包管理器与依赖检测）· net（网络与镜像下载）·
│   │                 compositors（合成器契约）· theme（深浅主题）· shell（切壳网关）·
│   │                 doctor（体检诊断）· clean（缓存清理）
│   ├─ ui/            终端交互：tui（交互组件与样式）· menus（菜单路由）· workflows（整装编排）
│   └─ cli.py · translations.toml（双语文案）· launcher.sh
├─ plugins/           蓝图 · 13 目录 = 13 真插件（KM4 + theme 共享模板池；wallpapers/theme 为 merge 共享生活区）
├─ shell/             自研 Quickshell 桌面（契约见 shell/AGENTS.md；`shell/plugins/` 为
│                     shell 命名空间蓝图，12 个 runtime 插件，KM4）
├─ tests/             镜像源码树：deploy/ pkg/ state/ desktop/ installer/
│                     tools/{orbit,wallpaper_picker}/ shell/ + 契约测试置顶
├─ packaging/         AUR PKGBUILD + gen-deps.py（单包全量：引擎+插件+Shell；
│                     depends=引擎运行时，optdepends 自动汇聚）+ .install 提示
├─ llms-wiki/ humans-wiki/
└─ install.sh         一次性引导（KM5：无参数透传；常驻入口 = nyxuri/launcher.sh）
```

每个目录一行「为什么在这」：deploy 管文件置换与部署执行；state 管状态记录与快照；
system 管进程环境、包供给、双语、合成器与桌面副作用；ui 是终端交互与整装编排；
packaging 是开发者工具不进运行时。
常用推荐软件供给面（catalog.toml → 18 个仅包声明插件 → `deps apps` 菜单）已随
R0-2 步 5 处决：插件装包统一走 `nyxuri on <plugin>`。

## 三个概念（用户面）

```
默认 config  ←  官方/用户形态  ←  __custom__ 文件
（最低）         （中）            （最高，永远赢）
```

- **Configs**：`plugins/<plugin>/` ship 的默认配置，`nyxuri on <plugin>` 原子部署到实机。
- **Forms**：插件的形态变体（整型形态 + 槽位轴；官方住 `plugins/<plugin>/__forms__/`，
  用户住 `~/.config/nyxuri/forms/`），机制见 [forms](forms.md)。
- **Customs**：`__custom__` 文件跨更新、跨形态切换保留，见 [file-preservation](file-preservation.md)。

## 生命周期动词与新旧命令的分界

`list / on / off / use / doctor` 是已落地的插件动词面（语义等价长动词
enable/disable），任何开关只走 `engine` 一条部署管线记录状态 (`state.json`)；`add / remove /
update`（第三方生命周期）随 S1 落地，契约已定稿（[plugin-model](plugin-model.md)
§5 终态八条）。install/update（引擎自更新）/theme 等是过渡期的领域动词（退役清单见
[plugin-model](plugin-model.md) §7）。全部命令表见 [operation-map](operation-map.md)。

## 运行时拓扑速览（原 runtime-topology 页，细节归档见 archive/）

- **会话启动**：niri `spawn-at-startup` → `session-shell.sh`（读 state.json 的
  `active_shell` 路由 Noctalia / 自研 Shell）+ fcitx5 + 护眼同步。
- **动作网关**：快捷键 → `shell-action.sh`（launcher/session/settings/clipboard/
  lock/wallpaper-random 等标准动作）→ Noctalia IPC 或自研 Shell；
  星环启动器 / 壁纸选择器是 `plugins/noctalia/tools/` 的一次性进程；划词翻译已外迁
  上游（S1 起经 `nyxuri add` 以第三方插件回归）。
- **主题调度**：`nyxuri theme` 单一实现——gsettings（portal→GTK4/Brave）、
  settings.ini、Noctalia IPC、Kitty SIGUSR1 四路同步，flock 排他。
- **Shell 事件**：状态记录后发一次 `plugin-changed` 事件（`quickshell ipc unit reload`，
  外层注入，内核不认识投递实现），见 [plugin-model](plugin-model.md) §6。

## 真值分工

运行行为以源码（`nyxuri/` + `plugins/` + `shell/`）与契约测试（`tests/`）为准；
架构契约以本 wiki 为准；阶段状态只在 [ROADMAP](../ROADMAP.md)；历史在
`llms-wiki/archive/`（冻结）。文档体系自身的规则见 [docs-charter](docs-charter.md)。
