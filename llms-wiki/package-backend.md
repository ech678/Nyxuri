# Package Backend — 发行版家族与包名映射

> 引擎原本把「Arch 系」写死在代码里：`pacman -Qq` 探包、`pacman -S` 装包、AUR 辅助
> 器补足仓库缺口。`nyxuri/system/backend.py` 把这层收成一个**家族判定 + 映射表**的
> 单一真相，Arch 仍是默认口径，Fedora 系（dnf）作为第二家族接进来。本页只讲契约与
> 原因；具体包名以 `plugins/*/manifest.toml` 与 `system/env.py:CORE_DEPS` 为准，命令
> 行为以源码与 `tests/pkg/` 为准。

## 家族判定

判定只读 `/etc/os-release`，不看工具链形状：

| 家族 | 命中条件 | 原生管理器 |
|---|---|---|
| `arch` | `ID` / `ID_LIKE` ∈ arch, archarm, archlinux, artix, cachyos, endeavouros, garuda, manjaro, rebornos | `pacman`（有 paru/yay/shelly 时优先 AUR 助手） |
| `fedora` | `ID` / `ID_LIKE` ∈ fedora, nobara, rhel, centos, rocky, almalinux, ol | `dnf` |

未识别（容器镜像、Termux 本体、Debian 系）一律回落到 `arch`：引擎的历史行为是 Arch
唯一口径，未知发行版保持原样比猜一个家族更诚实。测试与临时验证可用
`NYXURI_PKG_FAMILY=arch|fedora` 显式覆盖。

## 包名映射

`manifest.toml` 与 `CORE_DEPS` 里的包名**永远写 Arch 名**——它们是仓库真相，不因发行版
改名。Fedora 的差异只在 `backend.FEDORA_RENAMES` 一张表里：

| Arch 名 | Fedora 名 |
|---|---|
| `ffmpeg` | `ffmpeg-free` |
| `ttf-jetbrains-mono` | `jetbrains-mono-fonts` |
| `noto-fonts-cjk` | `google-noto-sans-cjk-fonts` |
| `qt6-imageformats` | `qt6-qtimageformats` |
| `python-gobject` | `python3-gobject` |
| `python-cairo` | `python3-cairo` |
| `adw-gtk-theme` | `adw-gtk3-theme` |

表里没有的名字按原名查询（大量包名两大家族一致），所以这张表只登记真正改了名的包。
探包（`DependencyProbe.installed`）与装包（`pkg.install`）都先过 `backend.rename`，两侧
永远同一个名字。

## 缺包语义（重要）

Fedora 源里查不到、且没有 COPR 通道的名字**不阻断任何东西**：

- `pkg.install` 打印 `package_absent_here`，把该名字从本次事务剔除，其余包裹照装；
- `deploy/engine.py:missing_packages` 只把「本发行版供得上」的名字算进 preflight，供不上的
  逐个打印一次警告后放行——「装不上 mpvpaper」不该拦住 `nyxuri on niri`；
- AUR 名（`packages_aur`）在 Fedora 上走 `backend.FEDORA_COPRS` 通道（当前只有
  `starship → atim/starship`，安装前先 `dnf copr enable`），没有通道的按缺包跳过。

`aur_supported()` 是 AUR 分支的唯一闸门：Fedora 上 `ensure_aur_helper()` 直接返回 None
（不再弹 AUR 助手引导），`pkg.command(source="aur")` 抛 `ValueError`。

## 事务结果以「装到了没有」为准

容器里装包最典型的假失败：dnf 事务被 systemd / sysusers 这类 `%post` 脚本拖挂
（proot 下脚本写不进 `/run`，报 `Protocol driver not attached`），dnf 于是把整个事务报成
failed——但请求的包**其实全部落地**。所以 Fedora 分支不看 dnf 退出码走人：失败的安装会
再 `rpm -q` 逐个复核，全在则打印 `dnf_scriptlet_ignored` 并判定成功，真的缺包才返回失败。
判定依据是「机器上有没有这个包」，不是「包管理器高不高兴」。

## 查询与探测

| 用途 | Arch | Fedora |
|---|---|---|
| 已装包集合 | `pacman -Qq` | `rpm -qa --qf %{NAME}` |
| 源内包名索引 | `pacman -Slq` | `dnf -q repoquery --available --qf %{name}` |
| 包详情 | `pacman -Si` / `-Qi` | `dnf info` |
| 版本 | `pacman -Q` | `rpm -q --qf` |

源内索引一次进程只查一次（`pkg.repo_packages()`），因为 dnf 元数据查询是秒级开销；已装
状态不进跨进程缓存（`DependencyProbe` 一次检查一个实例），这是原有契约。
`pkg` 动词的检索、详情、已装、装卸全部按家族走同一张探针。

## 权限

- 装包命令的 `sudo` 前缀只在本进程不是 root 时加（`backend.needs_superuser_prefix`），
  容器里以 root 运行时不会被 `sudo` 挡住。
- `nyxuri` / `install.sh` / `clean` 的 root 拒绝只对**真机**生效：`system.env.in_container()`
  命中 `/.dockerenv`、`/run/.containerenv`、`/.singularity.d` 或 `container` /
  `PROOT_L2S_DIR` / `PROOT_LOADER` / `PROOT_TMP_DIR` 环境变量时放行，并打印
  `root_container_notice`；`NYXURI_ALLOW_ROOT=1` 可显式放行。
- `ui/workflows.py` 的 sudo 预检在 root 下直接跳过，不再要求容器里的 root 过一遍 `sudo -v`。

## 清理面

`nyxuri clean` 的系统级任务按家族切换：Arch 用 `pacman -Qdtq` / `pacman -Scc`，Fedora 用
`dnf repoquery --unneeded` / `dnf clean packages`，缓存根目录分别量 `/var/cache/pacman/pkg`
与 `/var/cache/dnf`、`/var/cache/libdnf5`。

## 验证

```bash
python3 -m unittest tests/pkg/test_backend.py tests/pkg/test_pkg.py tests/pkg/test_deps.py tests/test_i18n.py
python3 -c 'from nyxuri.system import backend; print(backend.family(), backend.native_manager())'
python3 -m nyxuri pkg search jetbrains      # 源内检索走原生索引
python3 -m nyxuri pkg installed fish        # 已装检索
```

无 DRM/GPU 的容器里怎么把 Shell 跑起来看画面，见
[shell/development.md](shell/development.md) 第 4 节。
