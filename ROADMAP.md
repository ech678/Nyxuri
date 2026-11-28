# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段、D 卷明细与验收积压唯一见
> [shell/ROADMAP.md](shell/ROADMAP.md)。设计契约唯一见
> [design-system](llms-wiki/shell/design-system.md)。
> 状态词只用五态；历史明细只在 archive，此处不复述。

## 卷宗结构

| 卷 | 内容 | 状态 |
| --- | --- | --- |
| 第一卷「插件市场化改造」KM0–KM5 | 内核（registry · store · engine · catalog）+ 万物皆插件 + 单一真相 | 已完成（台账冻结于 [roadmap-history](llms-wiki/archive/roadmap-history.md)） |
| 第二卷「架构重塑与三方插件」G0–S1 | 定名 Plugin、Omarchy 五件套骨架整抄、S1 第三方生命周期 | 已完成（台账冻结于 [reconstruction-history](llms-wiki/archive/reconstruction-history.md)） |
| 第三卷「架构整理」P0–P5 | 根目录纯度、插件控制面、解耦、TOML 统一、引擎四域、并发审查 | 已完成（明细已迁入 [roadmap-history](llms-wiki/archive/roadmap-history.md)） |
| 第四卷「设计统一」D0–D5 | Material You 契约、bar 收尾与快修、SystemIcons QS 化、联动层、自定义引擎、跨表面过堂 | 进行中（唯一明细见 [shell/ROADMAP](shell/ROADMAP.md)） |

## 活跃路线（执行序即优先级）

| 站 | 交付 | 状态 |
| --- | --- | --- |
| D卷 | 设计统一：契约基石 → bar 快修 → SystemIcons QS 化 → 自定义引擎（D4a–D4h）→ 跨表面统一与联动（D5） | 进行中 |
| T4 | Shell 可控性与透明化（开工时立细则） | 待开始 |
| T5 | 多合成器解耦（门禁触发型） | 待开始 |
| T2 | TUI Textual 重做（搁置，分支 `archive/t2-textual-market` 备用） | 待开始 |

### T4 Shell 可控性与透明化（立项三件套）

- **T4-1 启动可见性**：`Terminal=true` 与桌面应用经 `xdg-terminal-exec` / `gio open`
  启动失败时，由发后即忘升级为状态捕获与用户通知反馈，终态消除「点击无声无息失败」。
- **T4-2 运行时透明度**：`nyxuri doctor` 与 `shell status` 输出插件挂载几何插槽状态、
  IPC 连通性与事件延迟指标。
- **T4-3 异常隔离**：UI 插件或脚本运行时崩溃时局部熔断隔离并上报错误横幅，
  主宿主与其它常驻插槽不瓦解。

### T5 多合成器解耦

S0 的 niri 适配层（`CompositorDriver` + `NiriDriver` 单文件方言）已兑现前置；
第三个合成器接入前收编残余字面量（债务登记见
[delayed-decisions](llms-wiki/delayed-decisions.md)）。

## 分支策略（PR #148 · Ubuntu 支持）

- PR #148（138 文件，+10519/−2532）整包暂存：自 main 建立 `legacy/ubuntu-support`，
  `gh pr edit 148 --base legacy/ubuntu-support` 后 merge（保署名）；该分支永不 rebase，
  仅作参考实现。分支操作待作者点头执行。
- 回植清单（R0-3 / S1 落地后按图索骥）：包后端窄驱动（pacman/apt、os-release 探测）、
  文件所有权账本。生命周期统一部分不回植。

## 冻结与挂起

- **T2 TUI**：选型 Textual、一次全搬定案不变；M0 spike 先行（kitty 终端交接、中文对齐、
  退出干净）。
- **Shell 功能阉割档：整档挂起（作者裁决）**。dashboard 双轨合并已划掉——双轨终局
  保留。其余候选留档备查：cookie 时钟链（约 −870）、lock 双风格链（约 −1,000）、
  通知双渲染实现合一、regionselector、PersonalizationConfig 死函数（约 −340）、
  mango 第二合成器去留、BezierCurveLayerEditor（1,153 行）、WeatherBackground（1,226 行）；
  零风险小件（约 −490 行）若迁移触及则顺带处置，不立项。

## 已收口（本卷前置）

- **T0 终端体验**：复制粘贴终审（`Ctrl+Shift+C/V` 唯一路径）；终端桥系统侧已修。
- **T1 上架 AUR**：`nyxuri-git` 上架；key-cli 废弃移除。
- **T3 设置界面替换**：Caelestia 原子套件 M0–M2 完成，M3/M4 待验收（状态见
  [shell/ROADMAP](shell/ROADMAP.md) 验收积压）。

## Shell 侧

阶段台账、D 卷分期、定案登记与门禁唯一见 [shell/ROADMAP.md](shell/ROADMAP.md)。
长期目标保留不减：启动器、壁纸/M3 调色、Noctalia TemplateAdapter、六大标准动作、
双 Shell 切换与伴生套件协同（契约见 [shell/AGENTS.md](shell/AGENTS.md)）。

## 全局门禁（每阶段验收都过）

1. 五原则验收给可复现证据（真诚透明 / 绝对主权 / 骨架包容 / 轻盈生长 /
   通用自然，见 [vision](llms-wiki/vision.md)）。
2. 单一开关真相与插件边界不变量的唯一权威在
   [plugin-model](llms-wiki/plugin-model.md) 与 [AGENTS.md](AGENTS.md)，此处只链接不复述。
3. 架构 / 命令 / manifest / 设计契约变更同步对应 wiki 页与台账（路由见 AGENTS.md）。
4. 完成声明防幻觉：状态改「已完成」前必须有独立复核命令的原始输出作证，AI 转述
   不算证据；查不出证据就不算完成，发现假象状态立即回退。

## 储备（不承诺）

- 第三方目录站、信任分级与签名——git URL 即源成立后再议。
- 安全 Downdate 体系：现场快照优先还原 + Git 逆向检出的安全版本回退。
- i18n 三处（引擎 translations.toml / shell i18n / humans-wiki 双语页）受众不同，
  低优登记不动；humans-wiki 与 operation-map 的受众重叠同理。
