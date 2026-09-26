# Install Modes — standalone / repo / system 三模式

> "哪里跑就是哪里的模式"——不搞优先级规则、不搞自动判定胜出者。源码：`nyxuri/core.py`、
> `nyxuri/network.py`、`nyxuri/packaging/PKGBUILD`。

## 三模式

| 方式 | repo_dir | run_mode | mode_label | update 行为 |
|---|---|---|---|---|
| `curl \| bash` | `~/.cache/nyxuri` | `standalone` | Remote Cache | `git pull` |
| `git clone` + `./install.sh` | 任意路径 | `repo` | Local Path | `git pull`（脏树跳过） |
| AUR `nyxuri-git` | `/usr/share/nyxuri` | `system` | System Package | `pacman -Syu`（禁 git pull） |

## 检测（`_detect_run_mode`，marker 最先）

```python
if (root_dir / ".system-install").is_file():   → system
elif root_dir.resolve() == cache_dir.resolve(): → standalone
elif (root_dir / "configs") and (root_dir / "assets"): → repo
else: → standalone（fallback）
```

`.system-install` marker **最先**检查——system 包在 `/usr/share/nyxuri/` 也 ship 了
configs/+assets/，不加 marker 会被误判成 repo。AUR 包 `package()` 里 `touch .system-install`。

`nyxuri` 命令模式由软链指向的 `install.sh` 决定，跟 cwd 无关——`cd /tmp && nyxuri update`
不改模式。要切模式重新跑对应目录的 `./install.sh`。

## CLI 软链（`ensure_nyxuri_symlink`）

`~/.local/bin/nyxuri` 软链指向你**主动跑** install.sh 的那个目录：

- 从 `~/Nyxuri` 跑 → 软链指 `~/Nyxuri` → `nyxuri` 命令用开发仓库代码
- 从 `bash <(curl)` 跑 → 软链指 `~/.cache/nyxuri`
- **system 模式 no-op**：包 owns `/usr/bin/nyxuri`（及兼容链 `/usr/bin/nyxniri`），不动用户 `~/.local/bin/nyxuri`
  （包不主动跑 install.sh，不抢软链）

## PATH 遮蔽（`check_path_occlusion`）

`~/.local/bin` 一般在 `/usr/bin` 前面，所以用户软链会盖住系统包。AUR 用户若之前用过
curl/git 装法，`~/.local/bin/nyxuri` 还在，会盖住包——`nyxuri update` 看似成功其实更新的是
缓存副本，pacman 更新的 `/usr/share/nyxuri` 用户感知不到。

system 模式下 `update` / `doctor` **开头都检测**：实际解析到的 install.sh 不在
`/usr/share/nyxuri` 就**持续**警告"你正用一个遮蔽系统包的旧软链"——不只装包时提醒一次。
控制感：用户随时知道自己到底在跑什么。

## update 分支（`safe_git_pull`，network.py）

```python
if run_mode == "system":
    print(msg("update_use_pacman"))   # "系统包由 pacman 管，跑 sudo pacman -Syu nyxuri-git"
    return None                        # 拒绝 git pull
```

堵死"对系统包跑 git pull"的故障路径。system 模式 **不做版本预检测**——禁了 git pull 就无法
知道上游有没有新版，要查就得调 AUR RPC / GitHub Releases API，违背纯标准库原则。诚实比
花哨重要：直接提示 pacman 管更新，pacman 自己会告诉用户有没有更新。

## update 交接（re-exec-first）

pull 成功后**当前进程不做任何部署**：菜单路径与 `nyxuri update` 都立即 `os.execve` 重启，
用 `PENDING_UPGRADE_ENV`（constants.py）把 deploy flag 带给新进程；`main()` 开头消费该
标记，在**新代码**上跑 `offer_overwrite_upgrade` + 依赖检查。菜单来源额外带
`PENDING_UPGRADE_MENU_ENV`，部署完回主菜单；CLI 来源部署完退出。

为什么必须先换代码：pull 会改写磁盘上的引擎文件，旧进程内存里还是旧模块，任何懒加载
导入（如 `_phase_post_install_services` 的 gtktheme）都会 ModuleNotFoundError——拆子包
（16bfb89→fc9cad6）时真实崩过，部署走到一半死在 traceback 上。

入口兜底：`__main__._run()` 捕获 `nyxuri.*` 的 ModuleNotFoundError（树混合/更新中断的
残留状态），一句话指引重跑 install.sh；非 nyxuri 的缺模块原样抛出。`install.sh` 侧的
`engine_is_complete` 只护住走引导的入口，直接 `python3 -m nyxuri` 靠这层兜底。

## AUR 包（`nyxuri/packaging/PKGBUILD`）

- 单一 rolling 包 `nyxuri-git`，`source=("git+https://github.com/ech678/Nyxuri.git#branch=main")`
- `pkgver()` = `git describe --long --tags`
- `package()`：cp nyxuri/configs/assets/install.sh 到 `/usr/share/nyxuri/`、`touch .system-install`、
  `/usr/bin/nyxuri` 软链到 install.sh、strip `__pycache__`
- **不做交互安装**（makepkg 不能 sudo）；用户装完包跑 `nyxuri install`
- 不发 stable 包——现状更新模型就是 rolling，双包 = 双倍熵
- `depends` / `optdepends` 由 `nyxuri/packaging/gen-deps.py` 扫所有 manifest 聚合生成——
  单一数据源，加 app 只动 configs/，不动 PKGBUILD

## 用户数据正交

无论哪种方式，用户数据都在两处、与方法无关：
- `~/.config/<app>/` — 部署的配置 + `__custom__` 覆盖
- `~/.config/nyxuri/` — backups / presets / active 状态

curl → AUR 迁移 = 装包 + 删 `~/.cache/nyxuri`，用户数据零迁移。**切换安装方式 = 换代码来源，
不换用户数据**。
