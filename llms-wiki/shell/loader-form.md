# Loader 装载形态（S0-0 spike 定案）

> 本页是 Shell 插件/单元 QML 装载形态的契约权威：Quickshell qs-import 静态扫描闭包
> 缺陷的根因、注册表装载形态定案、落选方案与重估触发条件。行为细节以源码与
> [spike-loader-registry.py](../../shell/scripts/dev/spike-loader-registry.py) 复跑
> 输出为准；阶段状态见 [ROADMAP](../../ROADMAP.md)。

## 装载形态定案（S0-0，2026-10-31）

**注册表装载形态 = file:// URL 装载**（即 Omarchy 4 `entryPointUrl` 形态）：

1. 插件入口一律按**绝对 `file://` URL** 装载（`Loader.source` / `Qt.createComponent`）。
   禁用相对路径 source——它被 qs: URL 拦截器接管，落入缺陷区（见根因）。
2. 插件内部组件互访用**同目录隐式类型 + 相对目录 import**（`import "tools"`）；
   **不得**用 `import qs.<自有模块根>` 引用自己或自己的子目录。
3. `import qs.*` 模块 import 只指向启动扫描闭包内的共享层（`commons/` `ui/`
   `services/`）——这些目录由 `shell.qml` 顶层 import 保证 qmldir 合成。
4. SlotHost 静态预热名单是本缺陷的补丁：S0-1 机械迁移期间保留（现状机制等价），
   S0-2 运行时注册表落地后随四件套一并退役（届时「新增插件 = 加目录 + manifest +
   代码，零宿主改动」不再受静态名单牵制）。
5. config root 之外的插件（S1 第三方 `~/.local/share/nyxuri/plugins/<id>/`）与
   root 内插件同形态，实测同为 20/20——S1 接入清单的装载面由本定案覆盖。

## 根因（源码 + 行为双证）

Quickshell 的 `qs.` 模块 import 不是真模块系统，而是「启动时静态扫描合成 qmldir」：

- `src/core/rootwrapper.cpp:60-61`：每次启动仅 `QmlScanner(rootPath).scanQmlRoot(shell.qml)` 一次。
- `src/core/scan.cpp`：扫描器只解析**文件头 import 语句**（`qs.` 与相对引号 import）
  递归目录，为闭包内目录合成 `qmldir`，经 `fileIntercepts` 网络拦截注入。
  `Loader { source: ... }` 的 URL 不是 import，不进闭包。
- `src/core/qsintercept.cpp`：`qs:` scheme URL 由拦截器处理，非 `@/qs/` 路径被黑洞。
  Loader 相对路径 source 解析为 `qs:` URL——该 scheme 下的组件连同目录隐式类型
  与相对 import 都不可用；`file://` URL 不经拦截，行为正常。
- config root 之外的目录不参与 qmldir 合成（scanner 明确警告
  "outside of the config folder"）——第三方插件只能走 file:// 形态。

行为证据（`--case baseline --scanner-log`，Quickshell 0.3.2）：scanner 仅合成
`.../baseline` 与 `.../baseline/commons` 两个 qmldir，`plugins/*` 全部缺席，随后
`module "qs.plugins.alpha" is not installed`、组件 compiled empty。qmldir 合成集合
与动态装载面的差集 = 缺陷面。

**旧描述修正**：`shell/AGENTS.md` 约束①记录的「不确定地整单元暴毙 / run-to-run
shifting failure sets」不准确——清缓存冷启动下失败是**确定性**的（baseline 0/20）；
游移来自 QML 磁盘缓存与该缺陷的交互。对策（SlotHost 预热、nyxuri-shell 每次清
qmlcache）独立成立，继续有效至 S0-2。

## 形态矩阵（2026-10-31，每格 20 次清缓存冷启动）

| case | 形态 | release 0.3.2 | master 9b0f339 |
| --- | --- | --- | --- |
| baseline | Loader 相对路径（qs: URL）+ 自有模块 import | 0/20 | 0/20 |
| warmup | 同 baseline + shell.qml 静态预热 import | 20/20 | 20/20 |
| url-relative | qs: URL + 相对 import / 隐式类型 | 0/20 | 0/20 |
| url-file | **file:// URL + 相对 import / 隐式类型** | **20/20** | **20/20** |
| external | **root 外 file:// URL（S1 第三方形态）** | **20/20** | **20/20** |
| prewarm | baseline + 启动期 Qt.createComponent 预热 | 0/20 | 0/20 |

master = 2026-10-22 上游最新（本地构建，未动系统包）。

**落选方案**：

- **升级 Quickshell**（ROADMAP 二选一的「升级」支）：master 9b0f339 与 release
  逐格同行为，缺陷未修；且 S1 root 外场景无论如何受限。升级不作为解法。
- **启动期 `Qt.createComponent` 预热**（B'）：0/20——运行时预编译同样不在启动
  扫描闭包内，救不回模块 import。不要反复提出。

## 复跑与重估

```bash
python3 shell/scripts/dev/spike-loader-registry.py --all --runs 20            # release
python3 shell/scripts/dev/spike-loader-registry.py --all --runs 20 --qs PATH  # 候选构建
python3 shell/scripts/dev/spike-loader-registry.py --case baseline --runs 1 --scanner-log  # 根因日志
```

fixture 生成在系统临时目录（`/tmp/opencode/spike-loader-registry/`），沙箱
XDG 目录、不触真实 `~/.config`；探针即输出，末尾 SUMMARY 行为验收证据。

重估触发条件：quickshell 升级（> 0.3.2）时以 `--qs` 复跑六形态矩阵。若 baseline /
url-relative 转绿可重议简化装载形态，但无需回退本定案——file:// 形态不受该修复
影响，且对 S1 root 外插件仍是唯一形态。
