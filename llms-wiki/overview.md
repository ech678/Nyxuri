# Overview — 一页仓库地图

> Nyxuri 是精选桌面配置的原子部署引擎，正在收敛为「桌面插件市场」：
> 单元（plugins/）× 内核（kernel/）× 市场界面（4 动词 + TUI 工坊）。
> 本页是文件树与分层的一页地图；单元模型契约见 [unit-model](unit-model.md)。

## 精神

三条原则（详见 [vision](vision.md)）：**秩序**（每层职责明确）、**做减法**
（一个机制能覆盖两处就用一个）、**无熵**（零 pip 依赖，纯标库，3.11+ 因 tomllib）。

## 仓库地图（KM3.5 终态，文件树即架构）

```
Nyxuri/
├─ nyxuri/            引擎 · 11 项
│   ├─ kernel/        registry（蓝图唯一读者）· resolver（纯依赖计算）·
│   │                 ledger（state.json 唯一写者）· transaction（唯一副作用编排）
│   ├─ deploy/        atomic（原子置换+Dunder）· manifest · templates ·
│   │                 preset（引擎半：active/staging/继承/fd 安全）· hardware · deploy
│   ├─ pkg/           包管理抽象（pacman/paru/shelly）+ 供给收编：deps · net ·
│   │                 fzf · detection · catalog（根 catalog.toml 解析）
│   ├─ state/         backup（30 滚动快照）· uninstall（勾选式清理）
│   ├─ desktop/       theme（深浅轴）· shell_switcher · clean · presets（流程半，渲染归 UI）
│   ├─ installer/     workflows + menus（交互式主菜单与整装/更新编排，作者裁决保留为常驻产品面）
│   └─ cli.py · core.py（环境+锁+日志+i18n 地基）· sysdoctor.py（系统体检）·
│       tui.py · translations.toml（双语文案）
├─ plugins/             蓝图 · 13 目录 = 12 真单元 + wallpapers（KM4 + theme 共享模板池；wallpapers/theme 为 merge 共享生活区）
├─ shell/             自研 Quickshell 桌面（契约见 shell/AGENTS.md；`shell/plugins/` 为
│                     shell 命名空间蓝图，12 个 runtime 单元，KM4）
├─ tests/             镜像源码树：kernel/ deploy/ pkg/ state/ desktop/ installer/
│                     tools/{orbit,wallpaper_picker,translate}/ shell/ + 契约测试置顶
├─ packaging/         AUR PKGBUILD + gen-deps.py（单包全量：引擎+单元+Shell；
│                     depends=引擎运行时，optdepends 自动汇聚）+ .install 提示
├─ llms-wiki/ humans-wiki/
├─ catalog.toml       包目录清单——「装但不部署」，不是单元
└─ install.sh         一次性引导（KM5：无参数透传；常驻入口 = nyxuri/launcher.sh）
```

每个目录一行「为什么在这」：kernel 是不可开关的底座；deploy 只管文件机械；
pkg 管包与供给；state 管账本外的状态副本；desktop 管活桌面副作用；installer 是
交互菜单与整装编排（作者裁决常驻）；packaging 是开发者工具不进运行时；catalog.toml 只喂 `deps apps` 菜单（T1 起与 PKGBUILD 脱钩）。

## 三个概念（用户面）

```
默认 config  ←  官方/用户预设  ←  __custom__ 文件
（最低）         （中）            （最高，永远赢）
```

- **Configs**：`plugins/<unit>/` ship 的默认配置，`nyxuri on <unit>` 原子部署到实机。
- **Presets**：单元的风味变体（官方住 `plugins/<unit>/__presets__/`，用户住
  `~/.config/nyxuri/presets/`），机制见 [preset-mechanism](preset-mechanism.md)。
- **Customs**：`__custom__` 文件跨更新、跨预设切换保留，见 [file-preservation](file-preservation.md)。

## 四大动词与新旧命令的分界

`list / on / off / doctor` 是市场面（语义等价长动词 enable/disable），任何开关
只走 `transaction` 一条事务路径落账本；install/update/preset/theme 等是过渡期
的领域动词（退役清单见 [unit-model](unit-model.md) §7）。全部命令表见
[operation-map](operation-map.md)。

## 运行时拓扑速览（原 runtime-topology 页，细节归档见 archive/）

- **会话启动**：niri `spawn-at-startup` → `session-shell.sh`（读 state.json 的
  `active_shell` 路由 Noctalia / 自研 Shell）+ fcitx5 + 护眼同步。
- **动作网关**：快捷键 → `shell-action.sh`（launcher/session/settings/clipboard/
  lock/wallpaper-random 等标准动作）→ Noctalia IPC 或自研 Shell；
  星环启动器 / 壁纸选择器 / 划词翻译是 `plugins/noctalia/tools/` 的一次性进程。
- **主题调度**：`nyxuri theme` 单一实现——gsettings（portal→GTK4/Brave）、
  settings.ini、Noctalia IPC、Kitty SIGUSR1 四路同步，flock 排他。
- **Shell 事件**：事务落账后发一次 `unit-changed` 事件（`quickshell ipc unit reload`，
  外层注入，内核不认识投递实现），见 [unit-model](unit-model.md) §6。

## 真值分工

运行行为以源码（`nyxuri/` + `plugins/` + `shell/`）与契约测试（`tests/`）为准；
架构契约以本 wiki 为准；阶段状态只在 [ROADMAP](../ROADMAP.md)；历史在
`llms-wiki/archive/`（冻结）。文档体系自身的规则见 [docs-charter](docs-charter.md)。
