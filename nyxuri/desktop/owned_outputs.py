"""为跨单元主题与钩子产物保存原值和最后写入身份。

元数据只认本模块记录的绝对路径；文件名、CSS 内容或旧的 owned 标记都不能
成为清理凭据。渲染器先写状态区暂存文件，再经本模块提交，避免覆盖后才发现漂移。
"""

import base64
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import shutil
import subprocess
import sys
import tomllib

from nyxuri.core import get_env
from nyxuri.kernel import ledger


def metadata_path() -> Path:
    """返回独立的版本化外部产物清单；不扩展单元的五字段记录。"""
    return get_env().state_dir / "external-outputs.json"


@contextlib.contextmanager
def _locked():
    path = metadata_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def _read() -> dict:
    path = metadata_path()
    if not path.exists():
        return {"version": 1, "outputs": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    _validate_metadata(data)
    return data


def _save(data: dict) -> None:
    path = metadata_path()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    # 原值可能含应用私密设置，清单只允许当前用户读取。
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def _safe(path: Path) -> Path:
    """仅允许当前 HOME 内的普通目标，拒绝父目录软链逃逸。"""
    path = Path(os.path.abspath(path))
    home = get_env().home.resolve()
    if not path.is_relative_to(home) or not path.parent.resolve().is_relative_to(home):
        raise ValueError(f"External output escapes HOME: {path}")
    return path


def _capture(path: Path) -> dict:
    if path.is_symlink():
        return {"kind": "symlink", "value": os.readlink(path)}
    if path.is_file():
        return {"kind": "file", "value": base64.b64encode(path.read_bytes()).decode("ascii"),
                "mode": path.stat().st_mode & 0o777}
    if path.exists():
        raise ValueError(f"External output is not a file: {path}")
    return {"kind": "missing"}


def _identity(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _restore(path: Path, value: dict) -> None:
    """先准备新内容，再原子替换；准备失败不能提前删掉原文件。"""
    path = _safe(path)
    if value["kind"] == "missing":
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_file() and not path.is_symlink():
        raise ValueError(f"External output is not a file: {path}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if value["kind"] == "file":
        temporary.write_bytes(base64.b64decode(value["value"], validate=True))
        temporary.chmod(value.get("mode", 0o644))
        os.replace(temporary, path)
    elif value["kind"] == "symlink":
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(value["value"])
        os.replace(temporary, path)
    else:
        raise ValueError("Invalid external output content")


def write_output(producer: str, consumer: str, path: Path, content: bytes, *, require_enabled: bool = False, force: bool = False) -> bool:
    """提交产物并保留首次原值；后续个人修改会阻断自动覆盖。"""
    path = _safe(path)
    with _locked():
        if require_enabled and not _can_render(producer, consumer):
            return True
        data = _read()
        current = _capture(path)
        record = data["outputs"].get(str(path))
        desired = {"kind": "file", "value": base64.b64encode(content).decode("ascii"), "mode": 0o644}
        if not record and current.get("kind") == "file" and current.get("value") == desired["value"]:
            desired = current  # 相同字节的陌生文件可以登记，但不能顺带修改原权限。
        grant = _consume_authorization(path, producer, consumer, current)
        conflict = (_identity(current) != record["last"] if record
                    else current["kind"] != "missing" and current != desired)
        if conflict and not (force or grant):
            print(f"[!] external output conflict; preserved: {path}", file=sys.stderr)
            return False
        original = record["original"] if record else current
        # 先持久保存原值，再写生效文件；失败记录保留原来的身份，可安全重试。
        data["outputs"][str(path)] = {"producer": producer, "consumer": consumer,
                                     "original": original, "last": _identity(current)}
        _save(data)
        _restore(path, desired)
        data["outputs"][str(path)]["last"] = _identity(desired)
        _save(data)
    return True


def _authorization_path() -> Path:
    return get_env().state_dir / "external-output-authorizations.json"


def _read_authorizations() -> dict:
    path = _authorization_path()
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Invalid external output authorizations")
    for raw, grant in value.items():
        if not isinstance(raw, str) or not isinstance(grant, dict):
            raise ValueError("Invalid external output authorization")
        _safe(Path(raw))
        if (not isinstance(grant.get("identity"), str) or not re.fullmatch(r"[0-9a-f]{64}", grant["identity"])
                or not all(isinstance(grant.get(key), str) and grant[key] for key in ("consumer", "unit", "backup"))
                or not isinstance(grant.get("producers"), list)
                or not all(isinstance(item, str) for item in grant["producers"])):
            raise ValueError("Invalid external output authorization fields")
    return value


def _save_authorizations(value: dict) -> None:
    path = _authorization_path()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False)
    os.replace(temporary, path)


def _consume_authorization(path: Path, producer: str, consumer: str, current: dict) -> bool:
    """持锁消费一次性许可；目标变化、不同消费者或不同生产者均使许可失效。"""
    grants = _read_authorizations()
    grant = grants.pop(str(path), None)
    if grant is None:
        return False
    _save_authorizations(grants)
    return (grant.get("identity") == _identity(current) and grant.get("consumer") == consumer
            and producer in grant.get("producers", []) and Path(grant.get("backup", "")).is_dir())


def register_deployed_outputs(unit_id: str, created_paths: set[Path]) -> None:
    """登记事务确认本轮新铺设的运行时插槽，绝不认领部署前已存在的文件。

    preserve插槽可能有初始蓝图但不入普通files；只有事务的「部署前不存在」
    证据允许将其交给渲染器继续写，首次原值明确记为missing。
    """
    candidates = {target for consumer, _, target in _specs().values() if consumer == unit_id}
    with _locked():
        data = _read()
        for path in candidates & {Path(value) for value in created_paths}:
            path = _safe(path)
            current = _capture(path)
            if str(path) not in data["outputs"] and current["kind"] != "missing":
                data["outputs"][str(path)] = {"producer": "deployment", "consumer": unit_id,
                    "original": {"kind": "missing"}, "last": _identity(current)}
        _save(data)


def authorize_output_overwrites(unit_id: str, backup: Path) -> None:
    """仅在事务的完整快照成功后，授权本次具名输出覆盖当前确定的内容。

    守护进程不能继承CLI的force变量；许可绑定当前目标身份并仅消费一次，
    不保存到可回滚快照中，避免恢复状态重新激活旧覆盖授权。
    """
    backup = Path(backup)
    if not backup.is_dir() or not (backup / "snapshot.json").is_file():
        raise ValueError("External output force requires a completed managed snapshot")
    value = json.loads((backup / "snapshot.json").read_text(encoding="utf-8"))
    if value.get("version") != 2:
        raise ValueError("External output force requires snapshot version 2")
    with _locked():
        grants = _read_authorizations()
        for consumer, _, target in _specs().values():
            if unit_id != "noctalia" and consumer != unit_id:
                continue
            if unit_id == "noctalia" and not _enabled(consumer):
                continue
            path = _safe(target)
            grants[str(path)] = {"identity": _identity(_capture(path)), "consumer": consumer, "unit": unit_id,
                                 "producers": ["noctalia", "nyxuri-shell"], "backup": str(backup)}
        _save_authorizations(grants)


def _unit_file_record(consumer: str, path: Path) -> tuple[dict | None, str]:
    """从历史落地点定位普通files键；没有精确记录就不给主配置变换授权。"""
    record = ledger.get_unit(consumer)
    if not record or record.get("state") != "enabled":
        return None, ""
    meta = ledger.get_deployment(consumer)
    if not meta.get("target"):
        return None, ""
    target = Path(meta["target"])
    if target == path:
        relative = path.name
    elif path.is_relative_to(target):
        relative = path.relative_to(target).as_posix()
    else:
        return None, ""
    return record, relative


def _file_digest(value: dict) -> str | None:
    return hashlib.sha256(base64.b64decode(value["value"])).hexdigest() if value["kind"] == "file" else None


def _update_file_baseline(consumer: str, path: Path, before: dict, after: dict) -> bool:
    """只在旧哈希精确相符时更新一个files键，保留其余字段和个人漂移证据。"""
    record, relative = _unit_file_record(consumer, path)
    if _file_digest(before) is None or not record or record.get("files", {}).get(relative) != _file_digest(before):
        return False
    digest = _file_digest(after)
    if digest is None:
        return False
    files = dict(record["files"])
    files[relative] = digest
    ledger.set_unit(consumer, state=record["state"], preset=record["preset"], files=files,
                    vault=record["vault"], updated=record["updated"])
    return True


def write_transformation(producer: str, consumer: str, path: Path, content: bytes) -> bool:
    """把受管主配置变换为运行态，并保留可逆的本次源部署原值。

    主配置仍在单元files中：基线随实际受管变换更新，日常refresh因此仍可升级。
    锁顺序固定为ledger→external，和单元事务一致，避免daemon与off互相等待。
    """
    path = _safe(path)
    with ledger.mutation_lock(), _locked():
        if not _can_render(producer, consumer):
            return True
        current = _capture(path)
        record, relative = _unit_file_record(consumer, path)
        if _file_digest(current) is None or not record or record.get("files", {}).get(relative) != _file_digest(current):
            print(f"[!] managed transformation conflict; preserved: {path}", file=sys.stderr)
            return False
        data = _read()
        previous = data["outputs"].get(str(path))
        original = (previous["original"] if previous and previous.get("kind") == "transform"
                    and previous["last"] == _identity(current) else current)
        desired = {"kind": "file", "value": base64.b64encode(content).decode("ascii"),
                   "mode": current.get("mode", 0o644)}
        data["outputs"][str(path)] = {"producer": producer, "consumer": consumer, "kind": "transform",
                                     "original": original, "last": _identity(current)}
        _save(data)
        _restore(path, desired)
        _update_file_baseline(consumer, path, current, desired)
        data["outputs"][str(path)]["last"] = _identity(desired)
        _save(data)
    return True


def rebase_transformations(consumer: str) -> None:
    """模板部署提交后，只给当前精确匹配新基线的主文件重建可逆原值。"""
    with ledger.mutation_lock(), _locked():
        data = _read()
        for raw, output in data["outputs"].items():
            if output.get("kind") != "transform" or output["consumer"] != consumer:
                continue
            path = _safe(Path(raw))
            current = _capture(path)
            record, relative = _unit_file_record(consumer, path)
            if _file_digest(current) is not None and record and record.get("files", {}).get(relative) == _file_digest(current):
                output["original"] = current
                output["last"] = _identity(current)
        _save(data)


def withdraw_outputs(producer: str | None = None, consumer: str | None = None, *, ordinary_only: bool = False) -> None:
    """按最后身份撤回产物；子进程hook只能清理不需要改账本的普通产物。

    父事务持有ledger锁等待hook退出，子进程不能再次申请同一把锁。普通产物
    只需要external锁；主文件可逆变换仍由父事务按ledger→external顺序撤回，
    并同步其普通files基线。hook意外遇到变换时立即报错，不能等待父锁或漏改基线。
    """
    ledger_context = contextlib.nullcontext() if ordinary_only else ledger.mutation_lock()
    with ledger_context, _locked():
        data = _read()
        if ordinary_only and any(record.get("kind") == "transform"
                and (producer is None or record["producer"] == producer)
                and (consumer is None or record["consumer"] == consumer)
                for record in data["outputs"].values()):
            raise RuntimeError("Managed transformations must be withdrawn by the parent unit transaction")
        for raw, record in list(data["outputs"].items()):
            if producer is not None and record["producer"] != producer:
                continue
            if consumer is not None and record["consumer"] != consumer:
                continue
            path = _safe(Path(raw))
            if _identity(_capture(path)) != record["last"]:
                print(f"[!] external output changed; preserved: {path}", file=sys.stderr)
                continue
            current = _capture(path)
            _restore(path, record["original"])
            if record.get("kind") == "transform":
                _update_file_baseline(record["consumer"], path, current, record["original"])
            del data["outputs"][raw]
        _save(data)


def _enabled(unit_id: str, overrides: dict | None = None) -> bool:
    if overrides and unit_id in overrides:
        return overrides[unit_id]
    return (ledger.get_unit(unit_id) or {}).get("state") == "enabled"


def _can_render(producer: str, consumer: str) -> bool:
    """持锁读取门控，使 off 与在途渲染的最终写入有确定先后关系。"""
    gate = get_env().state_dir / "template-consumers.json"
    states = json.loads(gate.read_text()) if gate.is_file() else None
    producer_enabled = (ledger.active_shell() == "nyxuri-shell" if producer == "nyxuri-shell"
                        else _enabled(producer, states))
    return producer_enabled and _enabled(consumer, states) and _enabled("theme", states)


def _specs() -> dict:
    """集中描述内置模板的消费者，避免把可选消费者变成强依赖。"""
    env = get_env()
    pool = env.config_dir / "nyxuri/templates"
    skin = env.home / ".local/share/fcitx5/themes/nyxmellow"
    return {
        "nyxuri_gtk3": ("theme", pool / "gtk-3.0.css", env.config_dir / "gtk-3.0/gtk.css"),
        "nyxuri_gtk4": ("theme", pool / "gtk-4.0.css", env.config_dir / "gtk-4.0/gtk.css"),
        "nyxuri_niri_glow_material_you": ("niri", pool / "niri-glow-material-you.kdl", env.config_dir / "niri/colors.kdl"),
        "palette": ("theme", pool / "palette.toml", env.cache_dir / "palette.toml"),
        "nyxuri_mango": ("mango", pool / "mango.conf", env.config_dir / "mango/noctalia.conf"),
        "nyxmellow_theme": ("fcitx5-rime", skin / "templates/theme.conf", skin / "theme.conf"),
        "nyxmellow_panel": ("fcitx5-rime", skin / "templates/panel.svg", skin / "panel.svg"),
        "nyxmellow_highlight": ("fcitx5-rime", skin / "templates/highlight.svg", skin / "highlight.svg"),
        "nyxuri_qt5": ("theme", pool / "qtct.conf", env.config_dir / "qt5ct/colors/noctalia.conf"),
        "nyxuri_qt6": ("theme", pool / "qtct.conf", env.config_dir / "qt6ct/colors/noctalia.conf"),
        "nyxuri_kitty": ("kitty", pool / "kitty.conf", env.config_dir / "kitty/themes/noctalia.conf"),
    }


def _noctalia_instance_running() -> bool:
    """只识别同UID的实际Noctalia实例，安装状态、账本开关和Shell偏好都不是运行证明。"""
    # 延迟导入，避免桌面切换模块与产物模块在初始化时形成循环依赖。
    from nyxuri.desktop.shell_switcher import probe_running_shells
    for kind, pid in probe_running_shells():
        if kind != "noctalia":
            continue
        process = Path("/proc") / str(pid)
        try:
            if process.stat().st_uid != os.getuid():
                continue
            arguments = process.joinpath("cmdline").read_bytes().split(b"\0")
            # 进程清单可能正好看见短暂的IPC客户端；它不提供重载服务。
            if any(argument in (b"msg", b"--help", b"--version", b"-h", b"-V") for argument in arguments[1:]):
                continue
            return True
        except (OSError, ProcessLookupError):
            continue
    return False


def refresh_consumer_outputs(overrides: dict[str, bool] | None = None) -> None:
    """在事务提交边界重建内置模板表；off 的覆盖状态在文件撤回前生效。

    只替换本项目具名模板表，其他用户模板原样保留。Noctalia 尚未落地时无写入；
    仅安装软件包也不代表生产者已启用。
    """
    env = get_env()
    # 开关覆盖先落门控：旧守护进程中排队的post hook也会重新读取它。
    states = {uid: record.get("state") == "enabled" for uid, record in ledger.all_units().items()}
    states.update(overrides or {})
    gate = env.state_dir / "template-consumers.json"
    gate.parent.mkdir(parents=True, exist_ok=True)
    with _locked():
        gate_temporary = gate.with_name(f".{gate.name}.{os.getpid()}.tmp")
        gate_temporary.write_text(json.dumps(states), encoding="utf-8")
        os.replace(gate_temporary, gate)
        disabled = {uid for uid, enabled in (overrides or {}).items() if not enabled}
        if disabled:
            grants = {raw: grant for raw, grant in _read_authorizations().items()
                      if grant["consumer"] not in disabled and grant["unit"] not in disabled}
            _save_authorizations(grants)
    # 1. 所有开关都更新门控，但只有主题生产者和消费者需要重建模板表。
    # Greeter 等无关单元不能借这一步迁移桌面主题或触发 Noctalia 的撤回钩子。
    specs = _specs()
    related = {"noctalia", "theme", *(consumer for consumer, _, _ in specs.values())}
    if overrides and related.isdisjoint(overrides):
        return
    (env.state_dir / "template-staging/nyxuri-shell").mkdir(parents=True, exist_ok=True)
    path = env.config_dir / "noctalia/noctalia-config.toml"
    if not path.is_file() or not _enabled("noctalia", overrides):
        return
    original_text = path.read_text(encoding="utf-8")
    text = original_text
    previous_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    # 2. 保留已有内置模板。清空 builtin_ids 会执行 Noctalia 的 undo_hook，
    # 删除旧主题文件和 Kitty include；即使替代模板可读，也不能把这当成无损迁移。
    # 新部署使用暂存模板；旧部署继续使用原生模板，避免两个生产者写同一个目标。
    builtins = tomllib.loads(original_text).get("theme", {}).get("templates", {}).get("builtin_ids", [])
    retained = list(builtins)
    for builtin, consumer in (("kitty", "kitty"), ("qt", "theme")):
        if overrides and (overrides.get(consumer) is False or overrides.get("theme") is False):
            retained = [name for name in retained if name != builtin]
    for name in specs:
        text = re.sub(r"(?m)^\[theme\.templates\.user\." + re.escape(name)
                      + r"\]\s*\n(?:(?!^\[).*(?:\n|$))*", "", text)
    if retained != builtins:
        # 仅改主题表中的键，避免误碰插件或其他同名配置项。
        text = re.sub(r'(?m)(^\[theme\.templates\]\s*\n)((?:(?!^\[).*(?:\n|$))*)',
                      lambda match: match[1] + re.sub(r'(?m)^builtin_ids\s*=.*$',
                          'builtin_ids = ' + json.dumps(retained), match[2]), text)
    command = env.repo_dir / "units/noctalia/hooks/commit-output"
    staging = env.state_dir / "template-staging/noctalia"
    staging.mkdir(parents=True, exist_ok=True)
    native_templates = {"nyxuri_kitty": "kitty", "nyxuri_qt5": "qt", "nyxuri_qt6": "qt"}
    for index, (name, (consumer, source, target)) in enumerate(specs.items()):
        if not _enabled(consumer, overrides) or not _enabled("theme", overrides):
            continue
        if native_templates.get(name) in retained:
            # 旧模板仍工作时，不登记可能尚未部署的替代输入；停用消费者时上面才撤回。
            continue
        # 3. 只登记已经部署且可读的输入。缺少模板时保留原配置和主题，事务保持
        # consumer-sync 待重试；不能先撤回旧输出，再让守护进程发现替代输入不存在。
        try:
            source.read_bytes()
        except OSError as error:
            raise RuntimeError(f"Theme template is not ready: {source}; refresh its owning unit before retrying") from error
        stage = staging / name
        hook = " ".join(shlex.quote(str(value)) for value in (command, name))
        text += (f'\n[theme.templates.user.{name}]\nindex = {index}\n'
                 f'input_path = {json.dumps(str(source))}\noutput_path = {json.dumps(str(stage))}\n'
                 f'post_hook = {json.dumps(hook)}\n')
    # 当前文件未知或已有个人修改时，只更新外置门控，绝不借其他单元开关改写个人配置。
    record = ledger.get_unit("noctalia")
    relative = "noctalia-config.toml"
    if text != original_text and (not record or record.get("files", {}).get(relative) != previous_hash):
        print(f"[!] Noctalia template configuration conflict; preserved: {path}", file=sys.stderr)
        raise RuntimeError("Noctalia template configuration conflict; refresh noctalia after review")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
    # 仅刷新本次受管变换对应的基线；若变换前已有个人修改，保留原基线供doctor报告。
    record = ledger.get_unit("noctalia")
    relative = "noctalia-config.toml"
    if record and record.get("files", {}).get(relative) == previous_hash:
        files = dict(record["files"])
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        ledger.set_unit("noctalia", state=record["state"], preset=record["preset"], files=files,
                        vault=record["vault"], updated=record["updated"])
    # 非Noctalia会话也可能保留其enabled配置。只有同用户的实际实例在运行才请求重载；
    # 当前偏好不能替代进程事实，真实实例拒绝重载时仍应报告partial供重试。
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("noctalia") and _noctalia_instance_running():
        result = subprocess.run(["noctalia", "msg", "config-reload"], timeout=15, check=False,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode:
            raise RuntimeError("Noctalia template configuration reload failed")


def _kitty_instances() -> list[int]:
    """只选择当前UID的GUI Kitty进程，排除runpy/kitten等短暂命令。"""
    result = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != os.getuid() or process.joinpath("comm").read_text().strip() != "kitty":
                continue
            arguments = process.joinpath("cmdline").read_bytes().split(b"\0")
            if not arguments or Path(os.fsdecode(arguments[0])).name != "kitty":
                continue
            if any(argument in (b"+runpy", b"+kitten", b"+complete", b"--help", b"--version") for argument in arguments[1:]):
                continue
            result.append(int(process.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return result


def _reload_kitty_after_commit(producer: str, target: Path) -> bool:
    """受管主题已经落盘后再通知现有Kitty，避免主题事件的早期USR1读到旧色板。

    只由主要themes/noctalia.conf模板调用一次，不在current-theme.conf保留槽另发
    一次全局通知。没有图形会话或实例均为正常情况；发送失败返回False供post hook重试。
    """
    if not os.environ.get("WAYLAND_DISPLAY"):
        return True
    with _locked():
        # off门控可能在文件提交之后到达；持同一把external锁再次检查，不能停用后重载。
        if not _can_render(producer, "kitty"):
            return True
        record = _read()["outputs"].get(str(target))
        if record is None or _identity(_capture(target)) != record["last"]:
            print(f"[!] Kitty theme changed before reload; preserved: {target}", file=sys.stderr)
            return False
        try:
            instances = _kitty_instances()
        except OSError as error:
            print(f"[!] Kitty reload process probe failed: {error}", file=sys.stderr)
            return False
        succeeded = True
        for pid in instances:
            try:
                # 精确PID和信号代替全局pkill，只影响上述同UID GUI实例。
                os.kill(pid, signal.SIGUSR1)
            except ProcessLookupError:
                continue
            except OSError as error:
                print(f"[!] Kitty reload failed for PID {pid}: {error}", file=sys.stderr)
                succeeded = False
        return succeeded


def commit_template(name: str, producer: str = "noctalia") -> bool:
    """暂存渲染结果提交时再核对开关，阻止 off 之前排队的旧渲染复活文件。"""
    consumer, _, target = _specs()[name]
    gate = get_env().state_dir / "template-consumers.json"
    states = json.loads(gate.read_text()) if gate.is_file() else None
    if not _enabled(consumer, states) or not _enabled("theme", states) or not _enabled(producer, states):
        return True
    stage = get_env().state_dir / "template-staging" / producer / name
    if not write_output(producer, consumer, target, stage.read_bytes(), require_enabled=True):
        return False
    return _reload_kitty_after_commit(producer, target) if consumer == "kitty" else True


def _validate_content(value: dict) -> None:
    """先检查恢复载荷的类型和编码，再允许任何生效文件变化。"""
    if not isinstance(value, dict):
        raise ValueError("Invalid external output content")
    kind = value.get("kind")
    if kind == "file":
        if not isinstance(value.get("value"), str) or not isinstance(value.get("mode"), int):
            raise ValueError("Invalid external file content")
        base64.b64decode(value["value"], validate=True)
        if not 0 <= value["mode"] <= 0o777:
            raise ValueError("Invalid external file mode")
    elif kind == "symlink":
        if not isinstance(value.get("value"), str) or "\x00" in value["value"]:
            raise ValueError("Invalid external symlink")
    elif kind != "missing":
        raise ValueError("Invalid external output kind")


def _validate_metadata(data: dict) -> None:
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("outputs"), dict):
        raise ValueError("Invalid external output metadata")
    for raw, record in data["outputs"].items():
        if not isinstance(raw, str) or not isinstance(record, dict):
            raise ValueError("Invalid external output record")
        _safe(Path(raw))
        if not all(isinstance(record.get(key), str) and record[key] for key in ("producer", "consumer", "last")):
            raise ValueError("Invalid external output owner")
        if not re.fullmatch(r"[0-9a-f]{64}", record["last"]):
            raise ValueError("Invalid external output identity")
        if record.get("kind") not in (None, "transform"):
            raise ValueError("Invalid external output record kind")
        _validate_content(record.get("original"))


def validate_snapshot_state(source: Path, manifest: dict) -> None:
    """在停用当前单元前验证外部快照，不消费或改写任何目标。"""
    if not manifest:
        return
    if manifest != {"version": 1, "file": "outputs.json"}:
        raise ValueError("Invalid external snapshot manifest")
    value = json.loads((source / "outputs.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("version") != 1 or value.get("home") != str(get_env().home):
        raise ValueError("External output snapshot HOME/version mismatch")
    _validate_metadata(value.get("metadata"))
    targets = value.get("targets")
    if not isinstance(targets, dict) or targets.keys() != value["metadata"]["outputs"].keys():
        raise ValueError("External output snapshot targets mismatch")
    for raw, content in targets.items():
        _safe(Path(raw))
        _validate_content(content)
    unmanaged = value.get("unmanaged_targets", {})
    if not isinstance(unmanaged, dict) or set(unmanaged) & set(targets):
        raise ValueError("Invalid external unmanaged snapshot targets")
    for raw, content in unmanaged.items():
        if not isinstance(raw, str):
            raise ValueError("Invalid external unmanaged target path")
        _safe(Path(raw))
        _validate_content(content)


def _declared_output_paths() -> set[Path]:
    """列出可被主题/Fcitx写入的边界，仅用于预先备份，不构成所有权。"""
    env = get_env()
    paths = {target for _, _, target in _specs().values()}
    skin = env.home / ".local/share/fcitx5/themes/nyxmellow/templates"
    paths.update(skin / name for name in ("theme.conf", "panel.svg", "highlight.svg"))
    rime = env.home / ".local/share/fcitx5/rime"
    # user.yaml归librime维护，会追加构建时间等运行态；不能把它当可恢复的模板目标。
    paths.add(rime / "default.custom.yaml")
    return paths


def snapshot_state(destination: Path) -> dict:
    """保存归属、原值与当前登记目标，快照携带HOME供跨环境校验。"""
    with _locked():
        data = _read()
        targets = {raw: _capture(_safe(Path(raw))) for raw in data["outputs"]}
        unmanaged = {str(path): _capture(_safe(path)) for path in _declared_output_paths()
                     if str(path) not in targets}
        result = {"version": 1, "home": str(get_env().home), "metadata": data,
                  "targets": targets, "unmanaged_targets": unmanaged}
        destination.mkdir(parents=True, exist_ok=True)
        snapshot = destination / "outputs.json"
        snapshot.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        snapshot.chmod(0o600)
        return {"version": 1, "file": "outputs.json"}


def restore_state(source: Path, manifest: dict) -> None:
    """还原明确登记的目标，先安全撤回快照之后的产物，不猜测目录归属。"""
    validate_snapshot_state(source, manifest)
    if not manifest:
        withdraw_outputs()
        with _locked():
            _save_authorizations({})
        return
    value = json.loads((source / "outputs.json").read_text(encoding="utf-8"))
    if value.get("version") != 1 or value.get("home") != str(get_env().home):
        raise ValueError("External output snapshot HOME/version mismatch")
    for raw in value["targets"]:
        _safe(Path(raw))
    withdraw_outputs()
    with _locked():
        current = _read()
        for raw, content in value["targets"].items():
            existing = _capture(Path(raw))
            # 旧产物可能被应用运行时追加内容，而快照已保存同一份内容。精确相等无需
            # 改文件，也不能因此把旧last重基成当前值；原归属证据仍从快照原样恢复。
            if existing == content:
                continue
            # 真正晚于快照的不同内容仍必须保留，不能借旧claim绕过冲突保护。
            if raw in current["outputs"] and existing["kind"] != "missing":
                raise RuntimeError(f"External output conflict during restore: {raw}")
            original = value["metadata"]["outputs"][raw]["original"]
            if existing["kind"] != "missing" and existing not in (content, original):
                raise RuntimeError(f"Untracked external output conflict during restore: {raw}")
            _restore(Path(raw), content)
        for raw, content in value.get("unmanaged_targets", {}).items():
            existing = _capture(Path(raw))
            if existing == content:
                continue
            if existing["kind"] != "missing":
                raise RuntimeError(f"Unmanaged external snapshot conflict: {raw}")
            _restore(Path(raw), content)
        _save(value["metadata"])
        _save_authorizations({})


SHELL_TEMPLATES = {
    "gtk3": "nyxuri_gtk3", "gtk4": "nyxuri_gtk4", "niri_glow": "nyxuri_niri_glow_material_you",
    "palette_toml": "palette", "fcitx5_theme": "nyxmellow_theme", "fcitx5_panel": "nyxmellow_panel",
    "fcitx5_highlight": "nyxmellow_highlight", "kitty": "nyxuri_kitty",
}


def commit_shell_template(name: str, stage: Path) -> bool:
    """Shell 内置模板走同一归属提交；用户自建模板仍遵循其显式输出配置。"""
    env = get_env()
    if ledger.active_shell() != "nyxuri-shell" or not _enabled("theme"):
        return True
    if name == "noctalia_mirror":
        consumer, target = "noctalia", env.config_dir / "noctalia/palettes/nyxuri.json"
    elif name in SHELL_TEMPLATES:
        consumer, _, target = _specs()[SHELL_TEMPLATES[name]]
    elif name == "btop":
        consumer, target = "btop", env.config_dir / "btop/themes/nyxuri.theme"
    elif name == "starship":
        consumer, target = "starship", env.cache_dir / "starship-palette.toml"
    else:
        raise ValueError(f"Unknown managed shell template: {name}")
    gate = env.state_dir / "template-consumers.json"
    states = json.loads(gate.read_text()) if gate.is_file() else None
    if not _enabled(consumer, states):
        return True
    stage = _safe(stage)
    if not stage.is_relative_to(env.state_dir / "template-staging/nyxuri-shell"):
        raise ValueError("Invalid shell template staging path")
    if not write_output("nyxuri-shell", consumer, target, stage.read_bytes(), require_enabled=True):
        return False
    if name == "kitty":
        return _reload_kitty_after_commit("nyxuri-shell", target)
    # 应用接线同样保存原值，不能由旧shell hook直接改写个人配置。
    if name == "btop":
        config = env.config_dir / "btop/btop.conf"
        if config.is_file():
            text = config.read_text()
            text = re.sub(r'(?m)^color_theme\s*=.*$', 'color_theme = "nyxuri"', text) if re.search(r'(?m)^color_theme\s*=', text) else text.rstrip() + '\ncolor_theme = "nyxuri"\n'
            return write_transformation("nyxuri-shell", consumer, config, text.encode())
    if name == "starship":
        config = env.config_dir / "starship.toml"
        text = config.read_text() if config.is_file() else ""
        text = re.sub(r'(?ms)^# >>> (?:NYXURI|NOCTALIA) STARSHIP PALETTE >>>.*?^# <<< (?:NYXURI|NOCTALIA) STARSHIP PALETTE <<<\n?', '', text)
        text = re.sub(r'(?m)^palette\s*=.*\n?', '', text)
        text = 'palette = "nyxuri"\n' + text.rstrip() + '\n\n# >>> NYXURI STARSHIP PALETTE >>>\n' + stage.read_text() + '\n# <<< NYXURI STARSHIP PALETTE <<<\n'
        return write_transformation("nyxuri-shell", consumer, config, text.encode())
    return True


def managed_paths() -> set[Path]:
    """供事务在钩子前后取并集，排除外部归属路径的双重快照认领。"""
    with _locked():
        return {Path(raw) for raw, record in _read()["outputs"].items() if record.get("kind") != "transform"}


def write_output_set(producer: str, consumer: str, outputs: dict[Path, bytes], *, force: bool = False) -> list[str]:
    """整组预检固定插件产物，仅在无冲突或已有强制备份授权时提交。

    与主题首次渲染不同，插件不能自动接管同名陌生文件。相同内容可登记，
    不同内容默认整组保留；force只覆盖本组具名路径，不遍历清理应用目录。
    """
    desired = {str(_safe(path)): {"kind": "file", "value": base64.b64encode(content).decode("ascii"),
                                 "mode": 0o644} for path, content in outputs.items()}
    with _locked():
        data = _read()
        conflicts = []
        retired = {raw: record for raw, record in data["outputs"].items()
                   if record["producer"] == producer and record["consumer"] == consumer and raw not in desired}
        for raw, record in retired.items():
            if _identity(_capture(Path(raw))) != record["last"]:
                conflicts.append(raw)
        for raw, value in desired.items():
            current = _capture(Path(raw))
            record = data["outputs"].get(raw)
            if record:
                changed = _identity(current) != record["last"]
            else:
                changed = current["kind"] != "missing" and current != value
            if changed:
                conflicts.append(raw)
        if conflicts and not force:
            return conflicts
        # 全组原值先写入状态区；此后任一提交失败仍有恢复证据。
        for raw in desired:
            current = _capture(Path(raw))
            record = data["outputs"].get(raw)
            data["outputs"][raw] = {"producer": producer, "consumer": consumer,
                "original": record["original"] if record else current, "last": _identity(current)}
        _save(data)
        for raw, value in desired.items():
            _restore(Path(raw), value)
            data["outputs"][raw]["last"] = _identity(value)
            _save(data)
        # 新固定集合不再提供的旧产物只按记录退役；外来插件不在这个集合内。
        for raw, record in retired.items():
            _restore(Path(raw), record["original"])
            del data["outputs"][raw]
            _save(data)
    return []
