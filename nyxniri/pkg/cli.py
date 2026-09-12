"""Package search and command adapter used by Fish's fzf interface."""

import json
import sys

from nyxniri.pkg import QUERY_TIMEOUT, command, preferred_manager, run


def _print_result(result) -> int:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode


def search(query: str) -> int:
    parts = query.strip().split(maxsplit=1)
    source = parts[0] if parts and parts[0] in ("aur", "pac", "repo") else "repo"
    keyword = (parts[1] if len(parts) > 1 else "") if parts and parts[0] in ("aur", "pac", "repo") else query.strip()
    if source == "aur":
        if not keyword:
            return 0
        manager = preferred_manager()
        if manager == "pacman":
            print("AUR search requires paru, yay or shelly", file=sys.stderr)
            return 1
        argv = ([manager, "search", "aur", "--json", keyword] if manager == "shelly"
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
    else:
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
    if action == "installed":
        result = run(["pacman", "-Qq"], capture=True, timeout=QUERY_TIMEOUT)
        if result.returncode == 0 and operands:
            result.stdout = "".join(name + "\n" for name in result.stdout.splitlines()
                                    if all(word.casefold() in name.casefold() for word in operands))
        return _print_result(result)
    manager = preferred_manager()
    if action == "info":
        if len(operands) != 1 or operands[0].startswith("-"):
            return 2
        name = operands[0]
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
        return run(command(action, operands, manager=manager)).returncode

    # Source tags from fzf are retained. Plain names use the local repo database.
    repo = run(["pacman", "-Slq"], capture=True, timeout=QUERY_TIMEOUT)
    if repo.returncode:
        return _print_result(repo)
    available = set(repo.stdout.splitlines())
    groups = {"repo": [], "aur": []}
    for operand in operands:
        if operand.startswith(("aur/", "repo/")):
            source, name = operand.split("/", 1)
        else:
            name = operand
            source = "repo" if name in available else "aur"
        if not name or name.startswith("-"):
            return 2
        groups[source].append(name)
    for source, packages in groups.items():
        if not packages:
            continue
        try:
            argv = command("install", packages, source=source, manager=manager)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        result = run(argv)
        if result.returncode:
            return result.returncode
    return 0
