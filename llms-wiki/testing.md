# Testing — 策略、形状、隔离

> 对照 AGENTS.md §9（TempEnv 隔离、参数形状契约、mock 紧贴被测代码）。

## 隔离（铁律）

**所有测试必须用 `tests/utils.py:TempEnv`，禁止碰真实 `~/.config` / `~/.local` / `~/.cache`。**

TempEnv 把 HOME 指向 tmpdir、建目录骨架、override `XDG_*` 环境变量、reset `core._ENV` 和
模块级缓存（core 的 `_PICS_DIR_CACHE`、deploy 的 `_CONFIG_ITEMS_CACHE`/`_IS_NVIDIA`、
manifest 的 `_MANIFEST_CACHE`、deps 的 pacman/fc-list/GI/AUR 助手缓存、greeter 状态缓存）
防止跨测试泄漏。反例：早期测试把实仓库 `configs/niri/config.kdl` 写成桩文件——已修。

## mock 层级（紧贴被测代码）

mock 打得太高会绕过命令构造逻辑。反例：测 `safe_git_pull` 时 mock `_run_git_transfer` 跳过了
`_with_git_progress` 的参数变形。

**更隐蔽的反例**：`test_orbit_lock` 曾 mock `_is_orbit_process` 本身——被测函数读 `/proc` 的
argv[0]（shebang 直启下是解释器名，不是脚本名），验证恒假、orbit toggle 失灵，mock 把回归
盖得严严实实。修正：真实子进程 + 真实 `/proc` 验证匹配逻辑，**验证函数本身永不 mock**。
（附带发现：`Popen` 返回后立即读 `/proc/<pid>/cmdline` 大概率还是空的，argv 发布与 exec
有竞态——测试需轮询等 cmdline 落地，真实运行场景不受影响。）

正确做法：被测代码**懒加载**（函数内 `from nyxniri.deploy.atomic import X`），测试
`patch("nyxniri.deploy.atomic.X")` 直接打**源模块**——运行时懒加载读到 patched 属性。
（re-export 绑定在 `__init__` import 时，patch 源不影响 re-export，所以测试用直接子模块路径。）

## 测试形状（按功能）

| 功能 | 测试形状 | 文件 |
|---|---|---|
| 预设 src 四分支 | 参数列表形状契约：(active, dest_exists, repo_preset, user_preset) → 断言选中 src 路径 | `test_preset.py` |
| active 写时序 | mock `atomic_replace_item` 失败 → active **没被写**（deploy-then-write） | `test_preset.py` |
| manifest 解析 | schema 校验：全默认、各字段覆盖、坏 toml 报错、文件型 sidecar、toml-only 可选 app | `test_manifest.py` |
| __custom__ 保留 | dest 有 custom → src 切换后 custom 仍在 dest | `test_preset.py` |
| 勾选卸载 | 各模块已装/未装 → 只显示已装；勾某模块 → 对应 `*_uninstall` 被调；模块恢复先于 nyx_dir 删 | `test_uninstall.py` |
| [gap] 清理 | archive glob / greeter /var/lib / fisher 降级（fish 不在）/ quickphrase 恢复——逐条 | `test_uninstall.py` |
| system marker 检测 | .system-install → system；configs+assets → repo；都不在 → standalone；PATH 遮蔽警告 | `test_system_mode.py` |
| doctor preset drift | active 指向已删预设 → 警告 | `test_doctor.py` |
| 双栏菜单 | ←/→ 跳栏不丢光标、↑/↓ 循环、Enter 调 apply、apply 走窄 deploy 不调 fisher | `test_preset.py` |
| atomic replace | 文件/目录回滚、断链 symlink、no-clobber 壁纸 | `test_deploy.py` |
| i18n 完整性 | ast 扫所有 `msg()`/`prompt_confirm()` 调用 vs TRANSLATIONS——无孤儿、无缺失 | `test_i18n.py` |

## 必跑命令

```bash
python3 -m compileall nyxniri                                    # 语法/静态检查
bash -n install.sh configs/noctalia/*.sh configs/niri/scripts/*.sh
shellcheck install.sh
python3 -m unittest discover -s tests -q                        # 行为契约
HOME=$(mktemp -d) ./install.sh test                             # 沙箱隔离部署
```
