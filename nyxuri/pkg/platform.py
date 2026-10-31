"""发行版识别与原生软件包数据库查询。"""

import os
import re
import shutil
import subprocess
from pathlib import Path


def _os_release() -> dict[str, str]:
    """读取系统发行版标识，避免依赖第三方发行版探测库。"""
    values: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key in {"ID", "ID_LIKE"}:
                values[key] = value.strip().strip('"').strip("'").lower()
    except OSError:
        pass
    return values


def _native_architecture() -> str:
    """读取 dpkg 的本机架构，以免外来架构包误满足普通包声明。"""
    if not shutil.which("dpkg"):
        return ""
    try:
        result = subprocess.run(["dpkg", "--print-architecture"], capture_output=True,
                                text=True, check=False, timeout=5,
                                env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def normalize_dpkg_package_names(output: str) -> set[str]:
    """提取已安装 dpkg 包名，并补上本机多架构包的无后缀别名。"""
    native_arch = _native_architecture()
    names = set()
    for line in output.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or not fields[0].startswith("ii"):
            continue
        name = fields[1]
        names.add(name)
        # manifest 通常省略本机架构；外来架构包不能满足这个普通名称。
        if native_arch and ":" in name and name.rsplit(":", 1)[1] == native_arch:
            names.add(name.rsplit(":", 1)[0])
    return names


def current_platform() -> str:
    """返回受支持的平台键；发行版标识优先于 PATH 中偶然存在的工具。"""
    release = _os_release()
    distro_id = release.get("ID", "")
    id_like = set(release.get("ID_LIKE", "").split())
    if distro_id in {"ubuntu", "kubuntu", "xubuntu", "lubuntu", "ubuntustudio"}:
        return "ubuntu"
    if "ubuntu" in id_like:
        return "ubuntu"
    if distro_id in {"arch", "cachyos"} or "arch" in id_like or Path("/etc/cachyos-release").is_file():
        return "arch"
    # 精简容器可能没有 os-release；仅在缺少发行版标识时才用 pacman 识别 Arch，
    # 避免 Ubuntu 的 PATH 中偶然出现 pacman 后误选包管理器。
    if not distro_id and shutil.which("pacman"):
        return "arch"
    return "unsupported"


def installed_package_names() -> set[str]:
    """列出原生包数据库中已安装的软件包名称。"""
    platform = current_platform()
    if platform == "arch":
        argv = ["pacman", "-Qq"]
    elif platform == "ubuntu":
        argv = ["dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n"]
    else:
        return set()
    if not shutil.which(argv[0]):
        return set()
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False,
                                timeout=30, env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if result.returncode != 0:
        return set()
    if platform == "arch":
        return set(result.stdout.split())
    # 同一解析器也供 DependencyProbe 使用，保证菜单与事务采用相同架构规则。
    return normalize_dpkg_package_names(result.stdout)


def backend_available() -> bool:
    """检查当前发行版的安装与数据库查询命令是否齐全。"""
    platform = current_platform()
    if platform == "arch":
        return bool(shutil.which("pacman"))
    if platform == "ubuntu":
        return bool(shutil.which("apt-get") and shutil.which("dpkg-query"))
    return False


def candidate_package_names() -> set[str]:
    """列出本机已配置的软件源索引中的包名，不刷新索引或添加软件源。"""
    platform = current_platform()
    if platform == "arch":
        argv = ["pacman", "-Slq"]
    elif platform == "ubuntu":
        argv = ["apt-cache", "pkgnames"]
    else:
        return set()
    if not shutil.which(argv[0]):
        return set()
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False,
                                timeout=30, env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return set(result.stdout.split()) if result.returncode == 0 else set()


def package_indexes_available() -> bool:
    """判断 APT 是否已有可用的软件源索引，不刷新或修改索引。"""
    if current_platform() != "ubuntu" or not shutil.which("apt-cache"):
        return False
    try:
        result = subprocess.run(["apt-cache", "policy"], capture_output=True,
                                text=True, check=False, timeout=30,
                                env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    return any(
        re.match(r"\s+\d+\s+[A-Za-z][A-Za-z0-9+.-]*:", line)
        for line in result.stdout.splitlines()
    )


def package_candidate_available(name: str) -> bool:
    """判断当前已配置的软件源是否提供包，不把本机已安装状态算作候选。"""
    if not name or name.startswith("-") or any(character.isspace() for character in name):
        return False
    platform = current_platform()
    if platform == "arch":
        argv = ["pacman", "-Si", "--", name]
        if not shutil.which(argv[0]):
            return False
        try:
            return subprocess.run(argv, capture_output=True, text=True, check=False,
                                  timeout=15, env={**os.environ, "LC_ALL": "C"}).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    if platform != "ubuntu" or not shutil.which("apt-cache"):
        return False
    # APT 接受 package:arch=version；先按包和架构查策略，再核对指定版本。
    package_name, separator, requested_version = name.partition("=")
    # APT 的 Candidate 也可能只是已安装版本，因此还要确认版本表里有来源行。
    try:
        result = subprocess.run(["apt-cache", "policy", package_name], capture_output=True,
                                text=True, check=False, timeout=15,
                                env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    candidate_match = re.search(r"^\s*Candidate:\s+(\S+)", result.stdout, re.MULTILINE)
    if candidate_match is None or candidate_match.group(1) == "(none)":
        return False
    wanted_version = requested_version if separator else candidate_match.group(1)
    candidate_block = False
    for line in result.stdout.splitlines():
        # 版本表先列版本与优先级，Ubuntu 渐进更新会追加 (phased N%)；
        # 该标记不改变 Candidate 的来源判定，后续仍须找到实际软件源索引。
        version_match = re.match(r"\s*(?:\*{3}\s+)?(\S+)\s+\d+(?:\s+\(phased \d+%\))?\s*$", line)
        if version_match:
            candidate_block = version_match.group(1) == wanted_version
            continue
        if candidate_block and re.match(
            r"\s+\d+\s+[A-Za-z][A-Za-z0-9+.-]*:", line,
        ):
            return True
    return False


def package_available(name: str) -> bool:
    """判断包是否已安装或当前软件源能提供，不改动 APT 索引。"""
    if not name or name.startswith("-") or any(character.isspace() for character in name):
        return False
    return name in installed_package_names() or package_candidate_available(name)


def native_package_version(name: str) -> str | None:
    """返回已安装包版本；包未安装或本机没有可用数据库时返回 None。"""
    platform = current_platform()
    if platform == "arch":
        argv = ["pacman", "-Q", "--", name]
    elif platform == "ubuntu":
        argv = ["dpkg-query", "-W", "-f=${db:Status-Abbrev}\\t${binary:Package}\\t${Version}\\n", "--", name]
    else:
        return None
    if not shutil.which(argv[0]):
        return None
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False,
                                timeout=15, env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    if platform == "arch":
        return result.stdout.split(maxsplit=1)[1] if len(result.stdout.split(maxsplit=1)) == 2 else None
    native_arch = _native_architecture()
    versions = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 3 or not fields[0].startswith("ii") or not fields[2]:
            continue
        package = fields[1]
        if package == name or (":" not in name and package == f"{name}:{native_arch}"):
            versions.append(fields[2])
    return versions[0] if versions else None
