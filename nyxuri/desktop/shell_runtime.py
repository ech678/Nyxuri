"""在停止旧桌面前验证 Nyxuri Shell 的实际运行时、声明依赖与 QML 导入。

探针只加载无窗口 ShellRoot 的外部模块，不装载 app 单例或业务域。它使用临时
HOME/XDG 与离屏平台，完成标记到达后回收自己创建的进程组，不连接当前桌面。
"""

import os
import json
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

from nyxuri.pkg.catalog import get_entry
from nyxuri.pkg.detection import DependencyProbe
from nyxuri.pkg.requirements import resolve_requirements

READY_MARKER = "NYXURI_RUNTIME_PREFLIGHT_READY"


def runtime_imports(shell_dir: Path) -> list[str]:
    """收集冷启动代码中的外部导入；tests夹具与未引用的实验资产不进探针。"""
    modules = {"QtQuick", "Quickshell", "Quickshell.Io"}
    paths = [shell_dir / "shell.qml"]
    for directory in ("app", "units", "shared"):
        paths.extend((shell_dir / directory).rglob("*.qml"))
    for path in paths:
        for module in re.findall(r"(?m)^\s*import\s+([A-Za-z][\w.]*)", path.read_text(encoding="utf-8")):
            if not module.startswith("qs."):
                modules.add(module)
    return sorted(modules)


def _stop_probe(process: subprocess.Popen) -> None:
    """只回收本次新建的进程组；失败后也不能留下探针实例或后台子进程。"""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.75)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=0.75)


def probe_qml_runtime(runtime: Path, shell_dir: Path, *, timeout: float = 8.0) -> str:
    """用真实qs的普通-p入口加载无窗口导入探针；返回空串表示组件完成实例化。"""
    imports = runtime_imports(shell_dir)
    with tempfile.TemporaryDirectory(prefix="nyxuri-runtime-probe-") as temporary:
        root = Path(temporary)
        runtime_home = root / "runtime"
        runtime_home.mkdir(mode=0o700)
        for name in ("config", "data", "state", "cache"):
            (root / name).mkdir()
        marker = root / "probe.ready"
        marker.write_text("", encoding="utf-8")
        source = "//@ pragma UseQApplication\n" + "\n".join("import " + module for module in imports)
        source += ('\nShellRoot {\n  FileView { id: ready; path: ' + json.dumps(str(marker))
                   + '; blockLoading: true; blockWrites: true }\n'
                   + '  Component.onCompleted: ready.setText("' + READY_MARKER + '")\n}\n')
        (root / "shell.qml").write_text(source, encoding="utf-8")
        environment = {key: value for key, value in os.environ.items()
                       if key not in {"DISPLAY", "WAYLAND_DISPLAY", "SESSION_MANAGER"}}
        environment.update({"HOME": str(root), "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"), "XDG_STATE_HOME": str(root / "state"),
            "XDG_CACHE_HOME": str(root / "cache"), "XDG_RUNTIME_DIR": str(runtime_home),
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + str(root / "unavailable-session-bus"),
            "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software",
            # Shell 本身导出的 Qt 缓存路径优先于 XDG；探针必须覆盖它，避免写入运行实例缓存。
            "QML_DISK_CACHE_PATH": str(root / "cache/qmlcache"),
            "NYXURI_PREFLIGHT_MARKER": str(marker),
            "QML_IMPORT_PATH": ":".join(filter(None, (os.environ.get("QML_IMPORT_PATH"), str(shell_dir / "shared/controls/shapes")))),
            "QML2_IMPORT_PATH": ":".join(filter(None, (os.environ.get("QML2_IMPORT_PATH"), str(shell_dir / "shared/controls/shapes"))))})
        log_path = root / "probe.log"
        with log_path.open("w", encoding="utf-8") as output:
            process = subprocess.Popen([str(runtime), "-p", str(root)], env=environment,
                stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    # 读取明确的组件完成产物；日志里的源码片段不能冒充ready标记。
                    if marker.read_text(encoding="utf-8") == READY_MARKER:
                        return ""
                    if process.poll() is not None:
                        break
                    time.sleep(0.05)
                details = log_path.read_text(encoding="utf-8", errors="replace").strip()
                return "Quickshell QML probe did not become ready: " + (details[-2000:] or "timeout or early exit")
            finally:
                _stop_probe(process)


def preflight_runtime(entry: Path) -> str:
    """依次检查真实入口、平台供给、字体和导入；任何一步失败均保留旧Shell。"""
    entry = entry.resolve()
    shell_dir = next((candidate for candidate in (entry.parent, entry.parent.parent)
                      if (candidate / "shell.qml").is_file()), None)
    if shell_dir is None:
        return "Nyxuri Shell entry must belong to a tree containing shell.qml"
    try:
        result = subprocess.run([str(entry), "--runtime-path"], timeout=3, check=False,
                                capture_output=True, text=True)
        runtime = Path(result.stdout.strip())
        if result.returncode or not runtime.is_absolute() or not runtime.is_file() or not os.access(runtime, os.X_OK):
            return "Nyxuri Shell runtime unavailable: " + (result.stderr.strip() or "wrapper did not resolve executable qs")
        catalog = get_entry("quickshell")
        if catalog is None:
            return "Quickshell runtime declaration is missing from catalog.toml"
        requirements = resolve_requirements(catalog)
        if not requirements.supported:
            return requirements.reason
        probe = DependencyProbe()
        # qs已由包装脚本解析并实际探测；其他平台包和手动资源仍按同一声明核对。
        names = [name for name in (*requirements.packages_repo, *requirements.packages_aur, *requirements.manual)
                 if name != "quickshell"]
        names.extend(["material-symbols-rounded-font", "material-symbols-outlined-font"])
        missing = [name for name in dict.fromkeys(names) if not probe.installed(name)]
        if missing:
            return "Missing Nyxuri Shell runtime dependencies: " + ", ".join(missing)
        return probe_qml_runtime(runtime, shell_dir)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return "Nyxuri Shell runtime preflight failed: " + str(error)
