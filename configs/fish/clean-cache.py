#!/usr/bin/env python3
"""NyxNiri clean-cache v4.1 — 勾选要清理的项目，回车执行。

安全模型（不可妥协）：
  1. 所有本地删除必须过 fence 闸门：目标严格位于白名单根之内；
  2. 符号链接一律不碰，防止逃出围栏；
  3. 只清空目录内容，目录本身永远保留；
  4. 外部命令一律参数列表，绝不拼接 shell 字符串；
  5. 干跑 (-n) 与实删共用同一条代码路径，动作层静默而已。
"""

import os
import select
import shutil
import signal
import subprocess
import sys
import termios
import tty
import unicodedata
from pathlib import Path

VERSION = "4.1"

TASK_KEYS = ("cache", "flatpak-cache", "steam", "thumbnails", "npm", "cargo",
             "trash", "scc", "orphans", "journal", "coredump", "var-tmp",
             "flatpak", "drop-caches", "trim")
DEFAULT_OFF = ("trim",)  # TRIM 慢且日常非必需，默认不勾

try:
    HOME = Path.home()
except (RuntimeError, OSError):
    print("cannot determine $HOME", file=sys.stderr)
    sys.exit(1)

DRY = False
ONLY_KEYS = None
WARN_COUNT = 0
ACT_WARNED = False


def _detect_zh():
    return any(os.environ.get(k, "").lower().startswith("zh")
               for k in ("LANG", "LC_ALL", "LC_MESSAGES"))


ZH = _detect_zh()


def t(zh, en):
    return zh if ZH else en


_TTY = sys.stdout.isatty()


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _TTY else s


def warn(msg):
    global WARN_COUNT
    WARN_COUNT += 1
    print(_c("33", "  ! ") + msg, file=sys.stderr)


HELP = f"""clean-cache v{VERSION} — {t("NyxNiri 缓存清理", "NyxNiri cache sweeper")}

{t("用法", "Usage")}: clean-cache.py [-n] [--only <任务,...>] [-h]

  -n, --dry-run       {t("干跑：只展示计划，不删除、不提权", "dry run: plan only, no deletion, no elevation")}
  --only <a,b,...>    {t("非交互执行指定任务（免确认），all = 全部", "run only these tasks (no prompts); all = everything")}
  -h, --help          {t("显示本帮助", "show this help")}

{t("交互模式：↑/↓/j/k 移动，Space 勾选，a 全选，n 清空，Enter 执行，Esc/q 取消。",
   "Interactive: ↑/↓/j/k move, Space toggle, a all, n none, Enter run, Esc/q cancel.")}
{t("默认全选（TRIM 除外）。", "All on by default (except TRIM).")}

{t("任务 key：", "Task keys:")} {", ".join(TASK_KEYS)}

{t("所有删除目标被限制在缓存、回收站等白名单目录内，绝不会触碰 $HOME 本身。",
   "Deletions are fenced inside cache/trash directories; $HOME itself is never touched.")}"""


# ---------- 基础工具 ----------

def _w(s):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)


def pad(s, width):
    return s + " " * max(1, width - _w(s) + 1)


def human(n):
    x = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if x < 1024 or unit == "TiB":
            return f"{int(x)} B" if unit == "B" else f"{x:.1f} {unit}"
        x /= 1024


def tilde(path):
    s = str(path)
    home = str(HOME)
    return "~" + s[len(home):] if s.startswith(home) else s


def probe(cmd, timeout=600):
    """只读探测：即使干跑也照常执行（du / pacman -Qdtq / pacdiff -o）。"""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None


def act(cmd, sudo=False, input_text=None, quiet=False):
    """变更型动作的唯一出口：干跑只打印，绝不执行。"""
    global ACT_WARNED
    full = (["sudo"] if sudo else []) + cmd
    if DRY:
        print(t("  [干跑] 将执行: ", "  [dry-run] would run: ") + " ".join(full))
        return None
    try:
        r = subprocess.run(full, input=input_text, text=True, timeout=1800,
                           capture_output=quiet)
    except (subprocess.TimeoutExpired, OSError) as exc:
        ACT_WARNED = True
        warn(" ".join(full) + f": {exc}")
        return None
    if r.returncode != 0:
        ACT_WARNED = True
        if r.returncode < 0:
            desc = signal.Signals(-r.returncode).name
        else:
            desc = f"exit {r.returncode}"
        warn(" ".join(full) + f" → {desc}")
    return r


# ---------- 围栏闸门 ----------

def _resolve(p):
    try:
        return p.resolve(strict=True)
    except OSError:
        return None


def _fenced(child, root):
    if child.is_symlink() or root.is_symlink():
        return False
    c, r = _resolve(child), _resolve(root)
    if not c or not r:
        return False
    if c == r or r not in c.parents:
        return False
    if c == HOME or c in HOME.parents:
        return False
    return True


def fence_clear(root):
    """清空 root 的内容（目录本身保留）。本地删除的唯一原语。"""
    if root.is_symlink():
        warn(t(f"跳过符号链接 {tilde(root)}", f"skip symlinked {tilde(root)}"))
        return
    if not root.is_dir():
        return
    try:
        entries = list(os.scandir(root))
    except OSError as exc:
        warn(f"{tilde(root)}: {exc}")
        return
    if DRY:
        print(t(f"  [干跑] 将清空 {tilde(root)}（{len(entries)} 项）",
                f"  [dry-run] would clear {tilde(root)} ({len(entries)} items)"))
        return
    for entry in entries:
        p = Path(entry.path)
        if p.is_symlink():
            warn(t(f"跳过符号链接: {p}", f"skip symlink: {p}"))
            continue
        if not _fenced(p, root):
            warn(t(f"拒绝越界项: {p}", f"refuse out-of-fence item: {p}"))
            continue
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        except OSError as exc:
            warn(f"{p}: {exc}")


def flatpak_cache_roots():
    base = HOME / ".var" / "app"
    if base.is_symlink() or not base.is_dir():
        return []
    rb = _resolve(base)
    if rb is None:
        return []
    try:
        entries = list(os.scandir(base))
    except OSError:
        return []
    roots = []
    for e in entries:
        if e.is_symlink():
            continue
        cache = Path(e.path) / "cache"
        rc = _resolve(cache)
        if rc and cache.is_dir() and rb in rc.parents:
            roots.append(cache)
    return roots


# ---------- 计量 ----------

def du(path):
    if path.is_symlink() or not path.is_dir():
        return None
    r = probe(["du", "-sb", "--", str(path)])
    if not r or not r.stdout:
        return None
    try:
        return int(r.stdout.strip().splitlines()[-1].split()[0])
    except (ValueError, IndexError):
        return None


def _measured_roots(flat_roots):
    roots = [HOME / r for r in (
        ".cache", ".thumbnails", ".npm",
        ".cargo/registry/cache", ".cargo/registry/src", ".cargo/git/db",
        ".local/share/Trash",
        ".local/share/Steam/steamapps/shadercache",
        ".local/share/Steam/steamapps/htmlcache",
        ".var/app", ".local/share/flatpak",
    )]
    roots += flat_roots
    roots += [Path("/var/cache/pacman/pkg"), Path("/var/log/journal"),
              Path("/var/lib/systemd/coredump"), Path("/var/tmp")]
    return [p for p in roots if p.is_dir() and not p.is_symlink()]


# ---------- 任务构建 ----------

def build_tasks(sizes, flat_roots):
    tasks = []

    def add(key, label, target, size, sudo, fn):
        tasks.append({"key": key, "label": label, "target": target, "size": size,
                      "sudo": sudo, "run": fn})

    def group_size(roots):
        return sum(sizes.get(r) or 0 for r in roots) or None

    groups = [
        ("cache", t("清空用户缓存", "Clear user cache"), "~/.cache", [HOME / ".cache"]),
        ("flatpak-cache", t("清空 Flatpak 应用缓存", "Clear Flatpak app caches"),
         "~/.var/app/*/cache", flat_roots),
        ("steam", t("清空 Steam 着色器缓存", "Clear Steam shader caches"),
         "~/.local/share/Steam/steamapps",
         [HOME / ".local/share/Steam/steamapps/shadercache",
          HOME / ".local/share/Steam/steamapps/htmlcache"]),
        ("thumbnails", t("清空旧版缩略图", "Clear legacy thumbnails"),
         "~/.thumbnails", [HOME / ".thumbnails"]),
        ("npm", t("清空 npm 缓存", "Clear npm cache"), "~/.npm", [HOME / ".npm"]),
        ("cargo", t("清空 Cargo 缓存", "Clear Cargo caches"), "~/.cargo/{registry,git}",
         [HOME / ".cargo/registry/cache", HOME / ".cargo/registry/src",
          HOME / ".cargo/git/db"]),
        ("trash", t("清空回收站（不可恢复）", "Empty trash (unrecoverable)"),
         "~/.local/share/Trash", [HOME / ".local/share/Trash"]),
    ]
    for key, label, target, roots in groups:
        for r in roots:
            if r.is_symlink():
                warn(t(f"跳过符号链接 {tilde(r)}", f"skip symlinked {tilde(r)}"))
        live = [r for r in roots if not r.is_symlink() and r.is_dir()]
        if not live:
            continue
        add(key, label, target, group_size(live), False,
            lambda live=live: [fence_clear(r) for r in live])

    orphans = []
    if shutil.which("pacman"):
        r = probe(["pacman", "-Qdtq"])
        if r and r.returncode == 0:
            orphans = r.stdout.split()

    if shutil.which("pacman"):
        # --noconfirm 会按默认值答 N，包缓存反而清不掉；两问都必须显式喂 y。
        add("scc", t("清空 pacman 包缓存", "Wipe pacman package cache"),
            "/var/cache/pacman/pkg (-Scc)", sizes.get(Path("/var/cache/pacman/pkg")),
            True, lambda: act(["pacman", "-Scc"], sudo=True, input_text="y\ny\n"))
    if orphans:
        names = " ".join(orphans[:6]) + (" …" if len(orphans) > 6 else "")
        add("orphans", t(f"移除 {len(orphans)} 个孤立包", f"Remove {len(orphans)} orphan package(s)"),
            names, None, True,
            lambda orphans=orphans: act(["pacman", "-Rns", "--noconfirm", *orphans],
                                        sudo=True))
    if shutil.which("journalctl"):
        add("journal", t("日志压缩至 3 天 / 100M", "Vacuum journal to 3 days / 100M"),
            "/var/log/journal", sizes.get(Path("/var/log/journal")), True,
            lambda: act(["journalctl", "--vacuum-time=3d", "--vacuum-size=100M",
                         "--rotate"], sudo=True))
    if Path("/var/lib/systemd/coredump").is_dir():
        add("coredump", t("清空崩溃转储", "Wipe core dumps"), "/var/lib/systemd/coredump",
            sizes.get(Path("/var/lib/systemd/coredump")), True,
            lambda: act(["find", "/var/lib/systemd/coredump", "-mindepth", "1",
                         "-maxdepth", "1", "-exec", "rm", "-rf", "--", "{}", "+"],
                        sudo=True))
    if Path("/var/tmp").is_dir():
        add("var-tmp", t("清理 /var/tmp 旧文件", "Clean /var/tmp files older than 7 days"),
            "/var/tmp (>7d)", sizes.get(Path("/var/tmp")), True,
            lambda: act(["find", "/var/tmp", "-mindepth", "1", "-maxdepth", "1",
                         "-mtime", "+7", "-exec", "rm", "-rf", "--", "{}", "+"],
                        sudo=True))
    if shutil.which("flatpak") and ((HOME / ".local/share/flatpak").is_dir()
                                    or Path("/var/lib/flatpak").is_dir()):
        def _flatpak():
            if (HOME / ".local/share/flatpak").is_dir():
                act(["flatpak", "uninstall", "--unused", "--delete-data", "-y", "--user"])
            if Path("/var/lib/flatpak").is_dir():
                act(["flatpak", "uninstall", "--unused", "--delete-data", "-y", "--system"],
                    sudo=True)
        add("flatpak", t("移除未用 Flatpak 运行时与数据", "Remove unused Flatpak runtimes and data"),
            "flatpak --unused --delete-data",
            sizes.get(HOME / ".local/share/flatpak"), True, _flatpak)

    def _drop_caches():
        act(["sync"])
        act(["tee", "/proc/sys/vm/drop_caches"], sudo=True, input_text="3\n", quiet=True)

    add("drop-caches", t("释放内存页缓存", "Drop memory page caches"), "/proc/sys/vm/drop_caches",
        None, True, _drop_caches)
    if shutil.which("fstrim"):
        def _fstrim():
            if not DRY:
                print(t("  TRIM 正在逐盘归还空闲块，期间没有进度输出，属正常…",
                        "  TRIM is walking your disks; silence means it is working..."))
            act(["fstrim", "-av"], sudo=True)
        add("trim", t("TRIM 回收 SSD 空间", "TRIM to reclaim SSD space"), "fstrim -av", None, True,
            _fstrim)
    return tasks


# ---------- 呈现 ----------

def _print_title():
    print()
    print("  " + _c("1;35", f"NyxNiri · Cache Cleaner v{VERSION}"))
    print("  " + _c("2", t("把磁盘还给你。", "Giving your disk back.")))


def _print_plan(tasks):
    header = (t("清理项", "Task"), t("目标", "Target"), t("体积", "Size"))
    rows = [header] + [
        (x["label"], x["target"], human(x["size"]) if x["size"] else "—") for x in tasks
    ]
    w1 = max(_w(r[0]) for r in rows)
    w2 = max(_w(r[1]) for r in rows)
    print()
    for i, (a, b, c) in enumerate(rows):
        line = "  " + pad(a, w1) + pad(b, w2) + c
        print(_c("2", line) if i == 0 else line)
    print("  " + "─" * (w1 + w2 + 14))


def _pacnew_hint():
    if not shutil.which("pacdiff"):
        return
    r = probe(["pacdiff", "-o"])
    files = [l for l in (r.stdout or "").splitlines() if l.strip()] if r else []
    if files:
        print()
        print(_c("33", t("  以下配置文件有 .pacnew/.pacsave 冲突，需手动合并：",
                        "  Config conflicts need manual merge:")))
        for f in files:
            print(f"    {f}")


def _big_folders():
    r = probe(["du", "-x", "-b", "--max-depth=1", "--", str(HOME)], timeout=900)
    print()
    print("  " + _c("2", t("HOME 占用大户（≥100 MiB）：",
                          "Biggest folders under HOME (≥100 MiB):")))
    total = 0
    entries = []
    if r and r.stdout:
        home_s = str(HOME)
        for line in r.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            try:
                size = int(parts[0])
            except ValueError:
                continue
            if parts[1] == home_s:
                total = size
                continue
            entries.append((size, parts[1]))
    entries.sort(reverse=True)
    shown = [e for e in entries if e[0] >= 100 * 1024 * 1024][:8]
    if not shown:
        print("  " + t("（没有超过 100 MiB 的目录）", "(no folder over 100 MiB)"))
    for size, path in shown:
        print(f"  {human(size):>10}  {tilde(path)}")
    if total:
        print("  " + t(f"HOME 总计 {human(total)}", f"HOME total {human(total)}"))


# ---------- 勾选 UI（镜像 nyxniri/tui.py CheckboxList 交互） ----------

def _read_key():
    fd = sys.stdin.fileno()
    ch = os.read(fd, 1)
    if ch == b"\x1b":
        r, _, _ = select.select([fd], [], [], 0.05)
        if not r:
            return "ESC"
        seq = os.read(fd, 2)
        return {b"[A": "UP", b"[B": "DOWN"}.get(seq, "")
    if ch in (b"\r", b"\n"):
        return "ENTER"
    if ch == b" ":
        return "SPACE"
    if not ch:
        return "ESC"
    return ch.decode("utf-8", "replace")


def _picker_lines(tasks, checked, focus):
    w1 = max(_w(x["label"]) for x in tasks)
    w2 = max(_w(x["target"]) for x in tasks)
    rows = []
    for i, x in enumerate(tasks):
        box = _c("32", "[✓]") if checked[i] else _c("2", "[ ]")
        size = human(x["size"]) if x["size"] else "—"
        body = f"{box} {pad(x['label'], w1)}{pad(x['target'], w2)}{size}"
        if i == focus:
            rows.append("  " + _c("1;36", "❯ ") + _c("1", body))
        else:
            rows.append("    " + body)
    hint = _c("2", t("  [↑/↓/j/k] 移动  [Space] 勾选  [a] 全选  [n] 清空  [Enter] 执行  [Esc/q] 取消",
                     "  [↑/↓/j/k] move  [Space] toggle  [a] all  [n] none  [Enter] run  [Esc/q] cancel"))
    return rows, hint


def _checkbox(tasks):
    """交互勾选。返回选中 key 列表；Esc/q 取消返回 None。"""
    checked = [x["key"] not in DEFAULT_OFF for x in tasks]
    focus = 0
    if shutil.get_terminal_size((80, 24)).lines < len(tasks) + 4:
        return _numbered_picker(tasks, checked)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    drawn = 0
    try:
        tty.setcbreak(fd)
        sys.stdout.write("\033[?25l")
        while True:
            rows, hint = _picker_lines(tasks, checked, focus)
            out = []
            if drawn:
                out.append(f"\r\033[{drawn - 1}A")
            for r in rows:
                out.append(r + "\033[K\n")
            out.append(hint + "\033[K")
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            drawn = len(rows) + 1
            key = _read_key()
            if key in ("UP", "k", "K"):
                focus = (focus - 1) % len(tasks)
            elif key in ("DOWN", "j", "J"):
                focus = (focus + 1) % len(tasks)
            elif key == "SPACE":
                checked[focus] = not checked[focus]
            elif key in ("a", "A"):
                checked = [True] * len(tasks)
            elif key in ("n", "N"):
                checked = [False] * len(tasks)
            elif key == "ENTER":
                return [x["key"] for x, c in zip(tasks, checked) if c]
            elif key in ("ESC", "q", "Q"):
                return None
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if drawn:
            sys.stdout.write("\n")


def _numbered_picker(tasks, checked):
    """终端过矮时的退路：序号切换，行式输入。"""
    while True:
        print()
        print(t("  输入序号切换勾选（如 2 或 3,5），回车执行，q 取消：",
                "  Toggle by number (e.g. 2 or 3,5), Enter to run, q to cancel:"))
        for i, x in enumerate(tasks):
            box = "[✓]" if checked[i] else "[ ]"
            print(f"  {i + 1:>2} {box} {x['label']}")
        try:
            reply = input("> ").strip()
        except EOFError:
            return None
        if reply.lower() in ("q", "quit"):
            return None
        if not reply:
            return [x["key"] for x, c in zip(tasks, checked) if c]
        ok = True
        for part in reply.replace(",", " ").split():
            if part.isdigit() and 1 <= int(part) <= len(tasks):
                checked[int(part) - 1] = not checked[int(part) - 1]
            else:
                ok = False
        if not ok:
            print(t("  看不懂这个序号，重来。", "  Bad number, try again."))


# ---------- 执行 ----------

def _elevate(sudo_tasks):
    if DRY or not sudo_tasks:
        return True
    if not shutil.which("sudo"):
        warn(t("sudo 不可用，系统级任务将跳过", "sudo unavailable; system tasks skipped"))
        return False
    print()
    print(t("  提权以执行系统级清理…", "  Elevating for system cleanup..."))
    try:
        rc = subprocess.run(["sudo", "-v"]).returncode
    except OSError as exc:
        warn(str(exc))
        return False
    if rc != 0:
        warn(t("提权失败，系统级任务跳过", "elevation failed; system tasks skipped"))
        return False
    return True


def _run_task(x):
    global ACT_WARNED
    ACT_WARNED = False
    try:
        x["run"]()
    except Exception as exc:
        warn(f"{x['label']}: {exc}")
        ACT_WARNED = True
    if DRY:
        return
    mark = _c("33", "!") if ACT_WARNED else _c("32", "✓")
    print("  " + mark + " " + x["label"])


def _pause():
    if sys.stdin.isatty():
        try:
            input(t("\n按回车退出…", "\nPress Enter to exit..."))
        except EOFError:
            pass


def _set_only(spec):
    global ONLY_KEYS
    keys = []
    for part in spec.split(","):
        k = part.strip()
        if not k:
            continue
        if k == "all":
            ONLY_KEYS = set(TASK_KEYS)
            return
        if k not in TASK_KEYS:
            print(t(f"未知任务: {k}", f"unknown task: {k}"), file=sys.stderr)
            print(t("可选任务: ", "Valid tasks: ") + ", ".join(TASK_KEYS), file=sys.stderr)
            sys.exit(1)
        if k not in keys:
            keys.append(k)
    ONLY_KEYS = set(keys)


def _parse_args(argv):
    global DRY
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(HELP)
            sys.exit(0)
        if a in ("-n", "--dry-run"):
            DRY = True
        elif a == "--only":
            i += 1
            if i >= len(argv):
                print(t("--only 缺少参数", "--only requires a value"), file=sys.stderr)
                sys.exit(1)
            _set_only(argv[i])
        elif a.startswith("--only="):
            _set_only(a[len("--only="):])
        else:
            print(t(f"未知参数: {a}", f"unknown argument: {a}"), file=sys.stderr)
            print(HELP, file=sys.stderr)
            sys.exit(1)
        i += 1


def main(argv):
    _parse_args(argv)
    if os.geteuid() == 0:
        print(t("请勿以 root 运行。", "Do not run as root."), file=sys.stderr)
        return 1
    _print_title()

    flat_roots = flatpak_cache_roots()
    measured = _measured_roots(flat_roots)
    sizes = {p: du(p) for p in measured}
    before = sum(v or 0 for v in sizes.values())

    tasks = build_tasks(sizes, flat_roots)
    if not tasks:
        print(t("  没有可清理的项目。", "  Nothing to clean."))
        return 0
    _pacnew_hint()

    if DRY:
        _print_plan(tasks)
        for x in tasks:
            _run_task(x)
        _big_folders()
        print()
        print("  " + "─" * 44)
        print("  " + t("干跑模式：未删除任何文件，未提权。",
                      "Dry-run: nothing deleted, no elevation."))
        _pause()
        return 0

    if ONLY_KEYS is not None:
        chosen = [x for x in tasks if x["key"] in ONLY_KEYS]
        if not chosen:
            print(t("  没有匹配的任务。", "  No matching tasks."))
            return 0
        _print_plan(chosen)
    elif sys.stdin.isatty():
        keys = _checkbox(tasks)
        if keys is None:
            print(t("\n已取消，未做任何改动。", "\nCancelled. Nothing was changed."))
            return 1
        chosen = [x for x in tasks if x["key"] in keys]
        if not chosen:
            print(t("  未选择任何项目，未做任何改动。", "  Nothing selected. Nothing was changed."))
            return 0
    else:
        _print_plan(tasks)
        print()
        print(t("  非交互环境：用 --only <任务> 执行指定项，或 -n 只看计划。",
                "  Non-interactive: use --only <tasks> to run, or -n to preview."))
        return 1

    print()
    user = [x for x in chosen if not x["sudo"]]
    sys_tasks = [x for x in chosen if x["sudo"]]
    for x in user:
        _run_task(x)
    if _elevate(sys_tasks):
        for x in sys_tasks:
            _run_task(x)
    else:
        for x in sys_tasks:
            print("  " + _c("2", "- " + x["label"]))

    _big_folders()

    print()
    print("  " + "─" * 44)
    after = sum(du(p) or 0 for p in measured)
    freed = max(0, before - after)
    print("  " + _c("1;32", t(f"共回收 {human(freed)}", f"Recovered {human(freed)}")))
    if WARN_COUNT:
        print("  " + _c("33", t(f"（{WARN_COUNT} 处警告，见上方）",
                               f"({WARN_COUNT} warning(s), see above)")))
    _pause()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\n" + t("已中断。", "Interrupted."), file=sys.stderr)
        sys.exit(130)
