# AGENTS.md (这个是给AI开发看的,当然你也可以看一下)

## 0. 关于作者 / 协作原则

我是 Echoes678，更愿意被当作艺术家而不是程序员。完美主义只用在我在意
的事情上——核心逻辑和主项目零将就；边角/我不感兴趣的模块可以适度放
宽标准，你自行判断，不用每处都死磕。极简对我来说不是风格是秩序感：
几何精度（对齐规整）+ 做减法（砍掉一切不必要的）。我受不了任何"失控
感"——依赖地狱、体积膨胀、卸载残留，本质上都是熵增，能不产生就不产生。

- "能跑但脏" vs "慢一点但干净可控"——默认选后者。
- 我懒得开局，一旦犹豫要不要动手，直接给个最小可执行起点，别等我把全部细节想清楚再问。
- 别用"这已经很好了"敷衍，我要的是经得起自己回头看的东西；汇报说重点，不用每次背景铺垫。
- 经用户标注/声明后能整抄成熟实现的绝不从零自研脑补：凡有成熟参考树、上游母体或既有规格的模块，坚守「先全量物理复制（`cp`）原件建立基线，再做减法剪裁适配」的 **Fork & Trim** 模式。

---

## 1. 真值体系与改动路由 (Task Routing)

- **真值分工 (Source of Truth)**：运行时行为与实现细节以**源码（`plugins/` + `nyxuri/`）与契约测试（`tests/`）**为准；架构契约、设计决策与原因意图以 [llms-wiki/llms.txt](llms-wiki/llms.txt) 为准。
- **改动范围 ➔ 必读 Wiki 契约**：拒绝盲目全库勘探，按改动范围查阅对应契约：

| 部署引擎 / 插件模型 (`nyxuri/deploy/`, `plugins/`) | `overview.md`, `plugin-model.md`, `file-preservation.md` | `python3 -m unittest tests/deploy/test_deploy.py tests/test_plugin_model.py` + 沙箱部署 |
| 部署执行 / 状态校验 (`nyxuri/deploy/engine.py`, `nyxuri/state/`) | `plugin-model.md` | `python3 -m unittest tests/kernel/test_transaction.py` |
| 环境与系统供给 (`nyxuri/system/`, plugins-only 声明) | `package-backend.md`（家族与包名映射）, `manifest-schema.md`, `overview.md` | `python3 -m unittest tests/pkg/` |
| 状态与快照 (`nyxuri/state/`) | `state-ops.md` | `python3 -m unittest tests/state/` |
| CLI 入口与编排 (`nyxuri/cli.py`, `nyxuri/ui/workflows.py`) | `operation-map.md`, `manifest-schema.md` | `python3 -m unittest tests/test_cli.py tests/test_ai_specs.py` |
| 终端 UI 与交互 (`nyxuri/ui/`) | `tui-charter.md` | 交互冒烟，检查退出 trap |
| 形态机制 (`nyxuri/deploy/forms.py`) | `forms.md`, `plugin-model.md` | `python3 -m unittest tests/deploy/test_forms.py tests/kernel/test_transaction.py` |
| 双语文案 / 提示信息 (`translations.toml`, `nyxuri/system/i18n.py`) | `i18n.md`, `writing-voice.md` | `python3 -m unittest tests/test_i18n.py` |
| 文档体系 (`llms-wiki/`, `notes/`, `ROADMAP*`) | `docs-charter.md` | `python3 -m unittest tests/test_ai_specs.py` |
| Nyxuri Shell (`shell/`) | `shell-rules` (`shell/AGENTS.md`), `shell/ROADMAP.md`, `llms-wiki/shell/` | `python3 -m unittest tests/shell/` + `compileall` |
| AUR 打包 (`packaging/`) | `overview.md`（仓库地图） | `python3 -m unittest tests/pkg/test_packaging.py` |
| 版本发布 / 变更记录 (`CHANGELOG.md`) | `changelog-spec.md` | `git log <last-release-tag>..HEAD` 对齐净变更 |

---

## 2. 核心架构不变量 (Invariants)

1. **物理隔离**：仓库源码与 `~/.config/` 物理隔离，只能走 `nyxuri.deploy.atomic` 的 `atomic_replace_item` 机制原子复制，严禁 `ln -s` 软链接进 `~/.config/`。
2. **Dunder 保留协议**：文件或目录名含 `__custom__`（如 `__custom__.kdl`）在更新/预设切换时必须保留；`monitor.kdl` 等按名引用走 manifest `preserve`。
3. **纯标库与无未声明依赖**：`nyxuri/` 引擎坚守 Python 纯标准库（零 pip 依赖，需 3.11+ 因 `tomllib`）。
4. **权限防御**：`install.sh` / `nyxuri` / `clean` 严禁以 root 权限运行（`id -u == 0` 直接拒绝）；容器环境（`system.env.in_container()` 命中 docker/podman/proot 标记，或 `NYXURI_ALLOW_ROOT=1`）里 root 是运行时唯一的身份，放行并提示（契约见 `package-backend.md`）。
5. **模板占位符**：`plugins/` 模板里的 `/home/user` 必须由部署引擎替换为目标 `$HOME`，禁止硬编码。
6. **硬件中立**：默认配置不指定特定 GPU 驱动变量，部署不按 PCI 设备改写驱动（历史案卷见 `llms-wiki/archive/nvidia-patch.md`）。

---

## 3. 按需验证与拒绝盲目乱测试

**严禁盲目乱跑全量测试，禁止无谓耗时**：
- **纯文档 / 路线图 / 方案交流（`*.md`, `notes/`）**：
  **免测直接交付**。严禁跑全量单测、严禁跑沙箱部署。仅当修改涉及文档结构、索引（`llms.txt`）或相对链接时，按需运行秒级专项测试：
  ```bash
  python3 -m unittest tests/test_ai_specs.py   # 0.06 秒秒级文档契约
  ```
- **模块代码改动**：严格按第 1 节路由表**精准定向跑对应单测**（秒级），不默认跑全量测试。
- **全量回归与沙箱部署**（仅在重大核心重构或用户明确要求全量验收时才跑）：
  ```bash
  python3 -m unittest discover -s tests -q     # 全量回归
  HOME=$(mktemp -d) python3 -m nyxuri test     # 沙箱部署
  ```

---

## 4. 协作工作流与完成定义 (Definition of Done)

- **Session 启动**：`git status` 看工作区净空即可；**严禁**开局盲目跑全量测试浪费时间（仅在将要大动核心代码时按需跑对应定向单测）。
- **改动原则**：
  - 3 步以下直接做；涉及卸载/破坏性操作先确认。
  - 只动请求范围，不顺手重构无关代码；文字遵循 `writing-voice.md`（像人说话、去 AI 味）。
  - **整抄再裁（Fork & Trim）**：凡有上游参考树或成熟母体的模块，以「物理复制原件 ➔ 定向做减法/适配」为标准工作流，严禁自研缩水残卷冒充整抄。
- **测试规范**：所有新测试必须使用 `tests/utils.py:TempEnv`，严禁写入真实 `~/.config`；外部命令必须有参数形状断言。
- **完成检查**：
  1. 纯文档/文本：文本就绪、链接正确即完成（必要时 `test_ai_specs.py` 绿），零额外测试；
  2. 代码改动：按第 1 节路由表定向单测绿即可交付；
  3. 若改动涉及架构契约、命令或 manifest，对应 `llms-wiki/` 页面必须已同步事实；
  4. 不主动 commit，除非用户明确要求。
