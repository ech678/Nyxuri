# 上游母体历史文档导引与状态清单

> 本文档针对 `shell/docs/` 下由母体 [StatIndet/quickshell](https://github.com/StatIndet/quickshell)（Clavis，commit `91cdecb`）导入的 22 篇原版文档建立分级索引。
> **免责声明**：上游文档属于历史设计参考，不具备 Nyxuri Shell 契约效力。当前架构契约见 [AGENTS](../AGENTS.md)，路线图见 [ROADMAP](../ROADMAP.md)，自研设计见 [子 Wiki 首页](index.md)。

---

## 1. 冲突 / 已失效文档（已在 R5 彻底物理删除）

以下 4 篇文档描述上游单体开发模式或旧构建/安装流程，与 Nyxuri 的物理隔离不变量、纯标准库引擎和原子部署契约直接冲突，**已在 R5 阶段彻底物理删除，防止对开发造成误导**：

- `development.md`（引导使用软链接将源码软链至 `~/.config`，违背物理隔离红线）
- `installation.md`（引导运行 `scripts/install/arch.py` 全量安装上游依赖，违背无未声明依赖）
- `architecture/install-layout.md`（描述 Clavis 原版打包布局，现已收敛为 `nyxuri-shell`）
- `releasing.md`（上游发布流，现由 Nyxuri 统一管道承接）

---

## 2. 核心架构与协议参考（按功能域按需查阅）

以下文档记录了母体在 Wayland、IPC、图层与安全等方面的具体实现思路与协议格式，后续各功能域重构时可作为深入上下文参考：

| 文件 | 核心价值与内容 | 后续参考阶段 |
| --- | --- | --- |
| [architecture/clipboard.md](upstream-docs/architecture/clipboard.md) | 剪贴板历史监听、MIME 类型支持与持久化思路 | P3-04 (Clipboard 动作接入) |
| [architecture/logical-metrics.md](upstream-docs/architecture/logical-metrics.md) | 多显示器逻辑像素缩放、对齐与几何边界处理 | P1-02 / P3-01 (多屏适配) |
| [architecture/cpu-power-security.md](upstream-docs/architecture/cpu-power-security.md) | 电池、电源状态与空闲省电策略 | P3-01 (系统状态栏服务) |
| [architecture/spotlight-search.md](upstream-docs/architecture/spotlight-search.md) | 启动器搜索权重算法、.desktop 解析与缓存逻辑 | P1-02 (应用启动器接入) |
| [architecture/config-isolation.md](upstream-docs/architecture/config-isolation.md) | 原版配置文件隔离思考 | 架构参考 |
| [architecture/runtime-compatibility.md](upstream-docs/architecture/runtime-compatibility.md) | 运行时动态兼容性探测策略 | P2-05 (可选 native 降级) |
| [lock-snapshot-crash.md](upstream-docs/lock-snapshot-crash.md) | Wayland `ext-session-lock-v1` 锁屏崩溃恢复与快照保护 | P3-03 (锁屏安全状态机) |
| [ipc.md](upstream-docs/ipc.md) | 原版 Quickshell IPC socket 通信协议与动作格式 | P0-06 / P1-03 (动作路由) |
| [sysmon-schema-v1.md](upstream-docs/sysmon-schema-v1.md) | 硬件监视 JSON/JSONL 数据契约规格 | P3 (系统监控域，本期封存) |
| [ui-guidelines.md](upstream-docs/ui-guidelines.md) | Material 3 动效曲线、圆角 Token 与组件视觉规约 | 贯穿全阶段 (视觉守护红线) |
| [wallpaper-backends.md](upstream-docs/wallpaper-backends.md) | swww / hyprpaper 等壁纸后端优劣比对 | P4-02 (原生壁纸后端选型) |
| [internationalization.md](upstream-docs/internationalization.md) | 原版 qsTr / qsTranslate 双语翻译组织方式 | P3 / 宿主 i18n 对齐 |

---

## 3. 上游代码审计与质量基准

| 文件 | 内容概览 |
| --- | --- |
| [development-checks.md](upstream-docs/development-checks.md) | 上游格式化、lint 与代码检查脚本说明 |
| [system-monitor-material3-audit.md](upstream-docs/system-monitor-material3-audit.md) | 监控组件 M3 适配审计记录 |
| [repository-split-audit.md](upstream-docs/repository-split-audit.md) | 上游仓库拆分历史与模块溯源记录 |
| [shell-background-effects.md](upstream-docs/shell-background-effects.md) | 背景模糊与合成器特效细节分析 |
| [dependencies.md](upstream-docs/dependencies.md) | 上游全量依赖表（注意：当前处于臃肿状态，待净化） |
