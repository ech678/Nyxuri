"""Package search and command adapter used by Fish's fzf interface."""

import json
import sys

from nyxuri.pkg import QUERY_TIMEOUT, command, install as install_packages, preferred_manager, run
from nyxuri.pkg.platform import current_platform


def _print_result(result) -> int:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode


def _group_operands(operands, available):
    groups = {"repo": [], "aur": []}
    for operand in operands:
        if operand.startswith(("aur/", "repo/", "pac/")):
            source, name = operand.split("/", 1)
            if source == "pac":
                source = "repo"
        else:
            name = operand
            # Ubuntu 没有 AUR；未命中的裸包名仍留给 APT 明确报错。
            source = "repo" if current_platform() == "ubuntu" or name in available else "aur"
        if not name or name.startswith("-"):
            return None
        groups[source].append(name)
    return groups


def _run_groups(action, groups, manager) -> int:
    # 先拒绝整批里不受 APT 支持的来源，避免前面的仓库包已经触发 sudo。
    if manager == "apt" and groups.get("aur"):
        print("AUR packages are unavailable through APT", file=sys.stderr)
        return 1
    for source, packages in groups.items():
        if not packages:
            continue
        if manager == "apt" and action == "install" and source == "repo":
            # 显式 fzf 选择保持交互确认；统一经过安装入口完成索引与候选预检。
            if not install_packages(packages, source="repo", manager=manager, automatic=False):
                return 1
            continue
        try:
            argv = command(action, packages, source=source, manager=manager)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        result = run(argv)
        if result.returncode:
            return result.returncode
    return 0


def _normalize_remove_operands(operands, manager):
    """移除前剥离 fzf 来源标签，并阻止 APT 接收 AUR 条目。"""
    normalized = []
    for operand in operands:
        source, separator, name = operand.partition("/")
        if separator and source in ("aur", "repo", "pac"):
            if source == "aur" and manager == "apt":
                print("AUR packages cannot be removed with APT", file=sys.stderr)
                return None
            if not name:
                return None
            operand = name
        normalized.append(operand)
    return normalized


def search(query: str) -> int:
    parts = query.strip().split(maxsplit=1)
    manager = preferred_manager()
    source = parts[0] if parts and parts[0] in ("aur", "pac", "repo") else "repo"
    keyword = (parts[1] if len(parts) > 1 else "") if parts and parts[0] in ("aur", "pac", "repo") else query.strip()
    if source == "aur":
        if not keyword:
            return 0
        if manager in ("apt", "unsupported", "pacman"):
            if manager == "apt":
                print("AUR search is unavailable on Ubuntu; search the configured APT sources instead", file=sys.stderr)
                return 1
            if manager == "unsupported":
                print("Package search is unavailable on this distribution", file=sys.stderr)
                return 1
            print("AUR search requires paru, yay or shelly", file=sys.stderr)
            return 1
        argv = ([manager, "search", "aur", "--json", "--", keyword] if manager == "shelly"
                else [manager, "-Ssq", "--aur", "--", keyword])
        result = run(argv, capture=True, timeout=QUERY_TIMEOUT)
        if result.returncode:
            return _print_result(result)
        if manager == "shelly":
            try:
                data = json.loads(result.stdout)
                if not isinstance(data, list):
                    raise ValueError("Expected an array")
                entries = data
                names = [entry["Name"] for entry in entries]
                if not all(isinstance(name, str) and name and not any(c.isspace() for c in name) for name in names):
                    raise ValueError("Invalid package name")
            except (ValueError, KeyError, TypeError):
                print("Invalid package search response from Shelly", file=sys.stderr)
                return 1
        else:
            names = result.stdout.splitlines()
        tag = "AUR"
    elif manager == "apt":
        # APT 搜索范围来自当前缓存索引；这里不执行 apt update。
        result = run(["apt-cache", "search", "--names-only", "--", keyword],
                     capture=True, timeout=QUERY_TIMEOUT)
        if result.returncode:
            return _print_result(result)
        names = []
        for line in result.stdout.splitlines():
            fields = line.split(maxsplit=1)
            if fields and keyword.casefold() in fields[0].casefold():
                names.append(fields[0])
        tag = "APT"
    else:
        if manager == "unsupported":
            print("Package search is unavailable on this distribution", file=sys.stderr)
            return 1
        result = run(["pacman", "-Slq"], capture=True, timeout=QUERY_TIMEOUT)
        if result.returncode:
            return _print_result(result)
        names = [name for name in result.stdout.splitlines() if keyword.casefold() in name.casefold()]
        tag = "PAC"
    for name in dict.fromkeys(names):
        print(f"[{tag}] {name}")
    return 0


def main(args: list[str]) -> int:
    if not args or args[0] not in ("install", "upgrade", "remove", "search", "info", "installed"):
        print("pkg: expected install, upgrade, remove, search, info or installed", file=sys.stderr)
        return 2
    action, *operands = args
    if action == "search":
        return search(" ".join(operands))
    manager = preferred_manager()
    if manager == "unsupported":
        print("Package operations are unavailable on this distribution", file=sys.stderr)
        return 1
    if action == "installed":
        if manager == "apt":
            result = run(["dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n"],
                         capture=True, timeout=QUERY_TIMEOUT)
            if result.returncode == 0:
                names = [
                    fields[1]
                    for line in result.stdout.splitlines()
                    if len(fields := line.split(maxsplit=1)) == 2 and fields[0].startswith("ii")
                ]
                result.stdout = "".join(
                    name + "\n" for name in names
                    if not operands or all(word.casefold() in name.casefold() for word in operands)
                )
        else:
            result = run(["pacman", "-Qq"], capture=True, timeout=QUERY_TIMEOUT)
            if result.returncode == 0 and operands:
                result.stdout = "".join(name + "\n" for name in result.stdout.splitlines()
                                        if all(word.casefold() in name.casefold() for word in operands))
        return _print_result(result)
    if action == "info":
        if len(operands) != 1 or operands[0].startswith("-"):
            return 2
        name = operands[0]
        if manager == "apt":
            result = run(["apt-cache", "show", "--", name], capture=True, timeout=QUERY_TIMEOUT)
            if result.returncode == 0:
                return _print_result(result)
            return _print_result(run(["dpkg-query", "-s", "--", name],
                                     capture=True, timeout=QUERY_TIMEOUT))
        local = run(["pacman", "-Si", "--", name], capture=True, timeout=QUERY_TIMEOUT)
        if local.returncode == 0:
            return _print_result(local)
        installed = run(["pacman", "-Qi", "--", name], capture=True, timeout=QUERY_TIMEOUT)
        if installed.returncode == 0:
            return _print_result(installed)
        if manager == "pacman":
            return _print_result(local)
        argv = (["shelly", "search", "aur", "--detail", name] if manager == "shelly"
                else [manager, "-Si", "--", name])
        return _print_result(run(argv, capture=True, timeout=QUERY_TIMEOUT))
    if action in ("install", "remove") and (not operands or any(p.startswith("-") for p in operands)):
        return 2
    if action != "install":
        if action == "remove" and manager == "shelly":
            repo = run(["pacman", "-Slq"], capture=True, timeout=QUERY_TIMEOUT)
            if repo.returncode:
                return _print_result(repo)
            groups = _group_operands(operands, set(repo.stdout.splitlines()))
            if groups is None:
                return 2
            return _run_groups("remove", groups, manager)
        if action == "remove":
            normalized = _normalize_remove_operands(operands, manager)
            if normalized is None:
                return 1
            operands = normalized
        try:
            argv = command(action, operands, manager=manager)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        return run(argv).returncode

    # fzf 选择的来源标记保留；裸包名按当前软件源索引分类。
    index_command = ["apt-cache", "pkgnames"] if manager == "apt" else ["pacman", "-Slq"]
    repo = run(index_command, capture=True, timeout=QUERY_TIMEOUT)
    if repo.returncode:
        return _print_result(repo)
    groups = _group_operands(operands, set(repo.stdout.splitlines()))
    if groups is None:
        return 2
    return _run_groups("install", groups, manager)
