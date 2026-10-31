"""核对 Ubuntu 软件包提供的 Greeter 配置，不接管软件包的文件与运行数据。"""

import pwd
import re
import shlex
import subprocess
import tomllib
from pathlib import Path


UBUNTU_GREETER_CONFIG = Path("/etc/greetd/noctalia-greeter.toml")


def read_root_file(path: Path) -> tuple[bool, str | None]:
    """区分特权目录中的文件不存在与读取失败，供规则备份和撤回使用。

    Ubuntu 的 polkit rules.d 不允许普通用户遍历；Path.is_file() 会把权限不足
    当成不存在。固定的只读脚本使用独立退出码表示缺失，sudo 失败不能冒充缺失。
    """
    script = (
        "import pathlib, sys\n"
        "try:\n"
        "    sys.stdout.write(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
        "except FileNotFoundError:\n"
        "    sys.exit(3)\n"
    )
    try:
        result = subprocess.run(
            ["sudo", "/usr/bin/python3", "-I", "-c", script, str(path)],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return False, None
    return result.returncode in (0, 3), result.stdout if result.returncode == 0 else None


def ubuntu_display_manager() -> str | None:
    """读取真正选中的显示管理器，避免把 gdm3 的静态 alias 当成已启用服务。"""
    selected = Path("/etc/systemd/system/display-manager.service")
    if not selected.is_symlink() and not selected.exists():
        return None
    return selected.resolve(strict=True).stem


def ubuntu_greeter_error() -> str | None:
    """返回包布局或生效配置的问题；无问题时返回 None，整个检查不修改系统。

    Ubuntu 包以 `_greetd` 运行，并用 systemd drop-in 指定独立 TOML。
    仅检查文件存在不够：用户的 service override 可能使另一份配置生效。
    """
    try:
        # 1. 保留包内 VT 和用户选择，只接受实际指向包内会话入口的命令。
        config = tomllib.loads(UBUNTU_GREETER_CONFIG.read_text(encoding="utf-8"))
        session = config.get("default_session", {})
        command = shlex.split(session.get("command", ""))
        if not command or command[0] != "/usr/bin/noctalia-greeter-session":
            return f"{UBUNTU_GREETER_CONFIG}: expected /usr/bin/noctalia-greeter-session"
        if session.get("user") != "_greetd":
            return f"{UBUNTU_GREETER_CONFIG}: expected user _greetd"
        account = pwd.getpwnam("_greetd")
        state = Path("/var/lib/noctalia-greeter").stat()
        if account.pw_uid == 0 or state.st_uid != account.pw_uid:
            return "/var/lib/noctalia-greeter: expected owner _greetd"

        # 2. 查询 systemd 已加载的命令，避免配置正确但服务仍读取别的文件。
        result = subprocess.run(
            ["systemctl", "show", "greetd", "--property=ExecStart", "--value"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        match = re.search(r"argv\[\]=(.*?)\s*;", result.stdout)
        argv = shlex.split(match.group(1)) if match else []
        if result.returncode or not argv or Path(argv[0]).name != "greetd":
            return "greetd.service: cannot determine ExecStart"
        if argv[1:] not in (["--config", str(UBUNTU_GREETER_CONFIG)],
                            [f"--config={UBUNTU_GREETER_CONFIG}"]):
            return f"greetd.service: expected --config {UBUNTU_GREETER_CONFIG}"
    except (OSError, KeyError, ValueError, TypeError, AttributeError,
            subprocess.SubprocessError) as error:
        return str(error)
    return None
