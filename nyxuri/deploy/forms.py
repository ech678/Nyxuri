"""Form mechanism — switch a plugin's active variant (default / official / user).

Two axes, one verb (R0-2 杀词并轨：预设 + 零件并轨为形态轴)::

    整型形态轴 (whole axis)   默认 config  ←  官方 __forms__/<名>/  ←  __custom__ 文件
    槽位形态轴 (slot axes)    [forms.<slot>] 声明的单文件热插拔（如 niri effects / glow）

The whole-axis choice lives in the plugin's ledger record (``form`` field,
single truth); slot choices live under the ledger's top-level ``forms`` key.
The retired ``~/.config/nyxuri/forms/<app>.active`` marker files were read-only
compat swept at R0-3 (the ledger is the single truth).

Write timing (iron law): apply flows deploy first, then land the ledger
choice. The dest-missing reset is the only sanctioned write-before-deploy
(dest is empty, so a half-written state self-heals next run).

One apply path serves both axes (:func:`use_form`) — the preset/part dual
path and the ``_reconcile_active_parts`` bypass are retired; deploys replay
active slots through the same function (:func:`replay_active_forms`).
"""

import fnmatch
import os
import secrets
import stat
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from nyxuri.core import STORAGE_NAME
from nyxuri.core import get_env, log_msg, timed_run
from nyxuri.core import msg


_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC

# The blueprint's official form directories (whole-axis variants and slot
# source trees both live here; engine + blueprint ship from the same repo,
# so no legacy name is honoured).
_OFFICIAL_FORMS_DIRNAME = "__forms__"


class InvalidActiveFormError(ValueError):
    """The form choice is present but cannot be safely used."""


def _is_safe_component(value: str) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if value in (".", "..") or Path(value).is_absolute():
        return False
    if os.sep in value or (os.altsep and os.altsep in value):
        return False
    try:
        return len(os.fsencode(value)) <= 255 and all(
            unicodedata.category(char) not in ("Cc", "Cs") for char in value
        )
    except UnicodeEncodeError:
        return False


def _safe_child(root: Path, *parts: str) -> Optional[Path]:
    """Return a non-symlink child contained below root, if it is safe."""
    if not all(_is_safe_component(part) for part in parts):
        return None
    try:
        if root.exists() and root.is_symlink():
            return None
        candidate = root.joinpath(*parts)
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
        current = root
        for part in parts:
            current /= part
            if current.exists() and current.is_symlink():
                return None
        return candidate
    except (OSError, RuntimeError, ValueError):
        return None


def _is_deployable_app(app: str) -> bool:
    if not _is_safe_component(app):
        return False
    from nyxuri.deploy.manifest import discover_deployable_apps

    source = _safe_child(get_env().plugins_src, app)
    try:
        return source is not None and app in discover_deployable_apps() and (
            source.is_dir() or source.is_file()
        )
    except OSError:
        return False


def _open_dir(path: Path, *, create: bool = False) -> int:
    try:
        return os.open(path, _DIR_FLAGS)
    except FileNotFoundError:
        if not create:
            raise
    path.mkdir(parents=True, exist_ok=True)
    return os.open(path, _DIR_FLAGS)


def _open_child_dir(parent_fd: int, name: str, *, create: bool = False) -> int:
    try:
        return os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
    os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    return os.open(name, _DIR_FLAGS, dir_fd=parent_fd)


def _open_forms_dir(*, create: bool = False) -> int:
    """Open the user-forms storage dir (``~/.config/nyxuri/forms/``)."""
    config_fd = _open_dir(get_env().config_dir, create=create)
    try:
        nyx_fd = _open_child_dir(config_fd, STORAGE_NAME, create=create)
    finally:
        os.close(config_fd)
    try:
        return _open_child_dir(nyx_fd, "forms", create=create)
    finally:
        os.close(nyx_fd)


def _remove_tree_at(parent_fd: int, name: str) -> None:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        raise OSError("unsafe form target")
    child_fd = os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
    try:
        child_info = os.fstat(child_fd)
        if (child_info.st_dev, child_info.st_ino) != (info.st_dev, info.st_ino):
            raise OSError("form target changed while binding")
        for entry in os.listdir(child_fd):
            entry_info = os.stat(entry, dir_fd=child_fd, follow_symlinks=False)
            if stat.S_ISDIR(entry_info.st_mode):
                _remove_tree_at(child_fd, entry)
            else:
                os.unlink(entry, dir_fd=child_fd)
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise OSError("form target changed while deleting")
        os.rmdir(name, dir_fd=parent_fd)
    finally:
        os.close(child_fd)


def read_active_form(app: str) -> str:
    """Return the active whole-axis form, or ``"default"`` when unrecorded.

    The ledger record is the single truth.
    """
    if not _is_deployable_app(app):
        raise InvalidActiveFormError("invalid form app")
    from nyxuri.kernel.ledger import get_plugin

    rec = get_plugin(app)
    if rec and isinstance(rec.get("form"), str) and rec["form"]:
        return rec["form"]
    return "default"


def write_active_form(app: str, name: str) -> None:
    """Land the whole-axis choice in the ledger record.

    An existing record keeps its state/files/vault; a never-switched plugin
    gets a ``disabled`` record (nothing archived, so ``vault`` stays null —
    the choice itself is the point).
    """
    if not _is_deployable_app(app):
        raise ValueError("invalid form app")
    if not _is_safe_component(name):
        raise ValueError("invalid form name")
    from nyxuri.kernel.ledger import get_plugin, set_plugin

    rec = get_plugin(app)
    if rec:
        set_plugin(
            app,
            state=rec.get("state", "disabled"),
            form=name,
            files=rec.get("files") or {},
            vault=rec.get("vault"),
            updated=rec.get("updated"),
        )
    else:
        set_plugin(app, state="disabled", form=name)


@dataclass
class FormSrcResult:
    """Outcome of resolving a plugin's active form to a deploy source."""

    src: Optional[Path]          # None → freeze dest, skip deploy (form not found)
    reset_form: Optional[str]    # write this before deploy (dest-missing reset to default)
    warnings: List[str] = field(default_factory=list)
    base_src: Optional[Path] = None
    base_include: List[str] = field(default_factory=list)
    base_exclude: List[str] = field(default_factory=list)


def resolve_form_inheritance(
    app: str, name: str
) -> tuple[Optional[Path], List[str], List[str]]:
    """Determine whether whole-axis form ``name`` of ``app`` inherits its base.

    Returns (base_src, include_patterns, exclude_patterns).
    If inheritance is not applicable or not enabled, returns (None, [], []).
    Simultaneously enforces blacklist veto and whitelist match.
    """
    if name == "default":
        return None, [], []

    env = get_env()
    app_root = _safe_child(env.plugins_src, app)
    if app_root is None or not (app_root.is_dir() and not app_root.is_symlink()):
        return None, [], []

    try:
        from nyxuri.deploy.manifest import load_manifest_for
        manifest = load_manifest_for(app)
    except Exception:
        return None, [], []

    # 1. Blacklist has absolute veto power
    if manifest.form_standalone:
        if any(fnmatch.fnmatch(name, pat.strip()) for pat in manifest.form_standalone if pat.strip()):
            return None, [], []

    # 2. Whitelist requirement (if declared)
    if manifest.form_allow:
        if not any(fnmatch.fnmatch(name, pat.strip()) for pat in manifest.form_allow if pat.strip()):
            return None, [], []
    elif not manifest.form_inherit:
        return None, [], []

    return app_root, list(manifest.form_include), list(manifest.form_exclude)


def _find_official_forms_dir(app_root: Optional[Path]) -> Optional[Path]:
    """The plugin's official form dir, as a safe path (may not exist yet).

    Existence is deliberately NOT checked here: callers decide per branch,
    and a missing ``__forms__/`` must not freeze a default deploy.
    """
    if app_root is None:
        return None
    return _safe_child(app_root, _OFFICIAL_FORMS_DIRNAME)


def resolve_form_src(app: str, active: str, dest: Path) -> FormSrcResult:
    """Resolve which source dir to deploy for ``app`` given its ``active`` form.

    Four branches: dest-missing reset; default; official form;
    user form. If none matches, src is None (freeze + warn) — we never
    silently fall back to default, which would wipe the user's frozen state.
    """
    env = get_env()
    app_root = _safe_child(env.plugins_src, app)
    repo_forms = _find_official_forms_dir(app_root)
    user_forms = _safe_child(env.forms_dir, app)
    expected_dest = _safe_child(env.config_dir, app)
    if (
        not _is_deployable_app(app)
        or not _is_safe_component(active)
        or app_root is None
        or repo_forms is None
        or user_forms is None
        or expected_dest is None
        or dest != expected_dest
    ):
        return FormSrcResult(
            src=None,
            reset_form=None,
            warnings=[msg("form_warn_frozen", app, active)],
        )

    def is_safe_dir(path: Path) -> bool:
        return path.is_dir() and not path.is_symlink()

    # Boundary: user rm -rf'd ~/.config/<app> but the active form still points
    # at a (possibly upstream-removed) variant. Nothing to freeze — reset to
    # default so the next deploy reinstalls defaults. If the original variant
    # is also gone from repo+user, surface an extra warning (upstream
    # rename/remove info must not be swallowed by the dest-missing rule).
    if not dest.exists() and active != "default":
        official = _safe_child(repo_forms, active)
        user = _safe_child(user_forms, active)
        upstream_removed = not (
            official is not None and is_safe_dir(official)
        ) and not (user is not None and is_safe_dir(user))
        warnings: List[str] = []
        if upstream_removed:
            warnings.append(msg("form_warn_upstream_removed", app, active))
        return FormSrcResult(src=app_root, reset_form="default", warnings=warnings)

    if active == "default":
        return FormSrcResult(src=app_root, reset_form=None)

    official = _safe_child(repo_forms, active)
    if official is not None and is_safe_dir(official):
        base_src, base_inc, base_exc = resolve_form_inheritance(app, active)
        return FormSrcResult(
            src=official,
            reset_form=None,
            base_src=base_src,
            base_include=base_inc,
            base_exclude=base_exc,
        )

    user = _safe_child(user_forms, active)
    if user is not None and is_safe_dir(user):
        base_src, base_inc, base_exc = resolve_form_inheritance(app, active)
        return FormSrcResult(
            src=user,
            reset_form=None,
            base_src=base_src,
            base_include=base_inc,
            base_exclude=base_exc,
        )

    # Active points at a variant that no longer exists anywhere — freeze dest,
    # do NOT fall back to default (would silently wipe the user's config).
    return FormSrcResult(
        src=None,
        reset_form=None,
        warnings=[msg("form_warn_frozen", app, active)],
    )


# --- slot axes ----------------------------------------------------------------


def list_slots(app: str) -> dict:
    """Return declared slot axes and available variant options for a plugin."""
    from nyxuri.deploy.manifest import load_manifest_for
    try:
        manifest = load_manifest_for(app)
    except Exception:
        return {}
    if not manifest.forms:
        return {}
    env = get_env()
    app_root = _safe_child(env.plugins_src, app)
    official_dir = _find_official_forms_dir(app_root)
    result = {}
    for slot, cfg in manifest.forms.items():
        slot_info = dict(cfg)
        variants = []
        source_dir_name = cfg.get("source_dir", slot)
        if official_dir:
            src_slot_dir = _safe_child(official_dir, source_dir_name)
            if src_slot_dir and src_slot_dir.is_dir():
                for item in sorted(src_slot_dir.iterdir()):
                    if not item.name.startswith(".") and not item.is_symlink():
                        variants.append(item.stem if item.is_file() else item.name)
        slot_info["variants"] = variants
        result[slot] = slot_info
    return result


def get_active_slot(app: str, slot: str) -> str:
    """Return the currently active variant for a plugin's slot axis."""
    from nyxuri.kernel.ledger import get_form_slots
    value = get_form_slots(app).get(slot)
    if value:
        return value
    try:
        from nyxuri.deploy.manifest import load_manifest_for
        m = load_manifest_for(app)
        if slot in m.forms:
            return m.forms[slot].get("default", "default")
    except Exception:
        pass
    return "default"


def _apply_slot(app: str, slot: str, variant: str) -> bool:
    """Hot-swap one declared slot axis (single-file atomic swap + ledger)."""
    from nyxuri.deploy.manifest import load_manifest_for
    from nyxuri.deploy.atomic import atomic_replace_item
    from nyxuri.kernel.ledger import set_form_slot

    try:
        manifest = load_manifest_for(app)
    except Exception as e:
        log_msg("ERROR", f"Failed to load manifest for {app}: {e}")
        return False
    if slot not in manifest.forms:
        log_msg("WARN", f"No slot axis '{slot}' declared for {app}")
        return False

    cfg = manifest.forms[slot]
    target_rel = cfg.get("target")
    if not isinstance(target_rel, str) or not target_rel:
        log_msg("WARN", f"Refused invalid slot target for '{slot}' in {app}")
        return False

    env = get_env()
    app_root = _safe_child(env.plugins_src, app)
    official_dir = _find_official_forms_dir(app_root)
    source_dir_name = cfg.get("source_dir", slot)

    src_candidate = None
    if official_dir:
        src_slot_dir = _safe_child(official_dir, source_dir_name)
        if src_slot_dir and src_slot_dir.is_dir():
            for item in src_slot_dir.iterdir():
                if item.name == variant or item.stem == variant:
                    src_candidate = item
                    break

    if src_candidate is None or not src_candidate.exists():
        log_msg("WARN", f"Variant '{variant}' not found in {source_dir_name}")
        return False

    dest = _safe_child(env.config_dir / app, *Path(target_rel).parts)
    if dest is None:
        log_msg("WARN", f"Refused unsafe slot target '{target_rel}' for {app}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not atomic_replace_item(src_candidate, dest):
        return False

    set_form_slot(app, slot, variant)

    if manifest.form_reload:
        timed_run(manifest.form_reload, 5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return True


def use_form(app: str, axis: Optional[str], value: str,
             preserved_log: Optional[List[str]] = None) -> bool:
    """The single form-switch path (R0-2): whole axis when ``axis`` is None.

    Whole axis: narrow deploy (atomic swap + template render for this app,
    no post-install services) then the ledger record — switching kitty must
    not rerun fisher, and the manifest ``preserve`` list is honoured exactly
    like the full deploy. Slot axis: single-file swap + slot ledger entry.
    Both land the ledger choice only after their deploy succeeded (iron law).
    ``preserved_log`` collects the swap's preserved-file lines for callers
    that render a report.
    """
    if not axis:
        from nyxuri.deploy.templates import _phase_render_templates
        from nyxuri.deploy.atomic import atomic_replace_item
        from nyxuri.deploy.manifest import load_manifest_for

        env = get_env()
        dest = _safe_child(env.config_dir, app)
        if not _is_deployable_app(app) or not _is_safe_component(value) or dest is None:
            return False
        src = _find_form_src(app, value)
        if src is None:
            return False

        # Preserve the same manifest-declared files the full deploy would; a
        # form switch is otherwise indistinguishable to runtime state.
        preserve = None
        preserve_values = None
        chmod: List[str] = []
        try:
            m = load_manifest_for(app)
            preserve = m.preserve or None
            preserve_values = m.preserve_values or None
            chmod = m.chmod
        except Exception:
            pass

        base_src, base_inc, base_exc = resolve_form_inheritance(app, value)
        if not atomic_replace_item(
            src,
            dest,
            preserved_log=preserved_log,
            preserve=preserve,
            preserve_values=preserve_values,
            base_src=base_src,
            base_include=base_inc,
            base_exclude=base_exc,
        ):
            return False

        _phase_render_templates(only_app=app)
        for pattern in chmod:
            for path in dest.glob(pattern):
                if path.is_file():
                    try:
                        path.chmod(0o755)
                    except OSError:
                        pass
        # The swap just reset every slot target to the new variant's template:
        # replay ledger-recorded slot choices on top through the same path.
        try:
            m = load_manifest_for(app)
            for failure in replay_active_forms(app, m):
                log_msg("WARN", f"Failed to replay active slot {failure}")
        except Exception as e:
            log_msg("WARN", f"Failed to replay active slots for {app}: {e}")
        # deploy-then-write: a crash mid-flow must not leave the choice
        # pointing at a deploy that didn't complete (§ iron law).
        try:
            write_active_form(app, value)
        except OSError as e:
            log_msg("ERROR", f"Deployed form '{value}' to {app} but recording it failed: {e}")
            return False
        try:
            m = load_manifest_for(app)
            if m.form_reload:
                timed_run(m.form_reload, 2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception as e:
            log_msg("WARN", f"Failed to reload form for {app}: {e}")
        return True
    return _apply_slot(app, axis, value)


def _find_form_src(app: str, name: str) -> Optional[Path]:
    """Direct lookup of a named whole-axis form (apply flow). No dest-missing reset.

    Distinct from resolve_form_src (update flow): apply is an explicit user
    choice, so a missing dest does not silently reset to default — the named
    variant is deployed as-is. 'default' resolves to the app root.
    """
    if not _is_deployable_app(app) or not _is_safe_component(name):
        return None
    try:
        from nyxuri.deploy.manifest import load_manifest_for
        manifest = load_manifest_for(app)
        if manifest.forms and name in {cfg.get("source_dir", slot) for slot, cfg in manifest.forms.items()}:
            return None
    except Exception:
        pass
    env = get_env()
    app_root = _safe_child(env.plugins_src, app)
    repo_forms = _find_official_forms_dir(app_root)
    user_forms = _safe_child(env.forms_dir, app)
    if app_root is None or repo_forms is None or user_forms is None:
        return None
    if name == "default":
        return app_root if (app_root.is_dir() or app_root.is_file()) and not app_root.is_symlink() else None
    official = _safe_child(repo_forms, name)
    if official is not None and official.is_dir() and not official.is_symlink():
        return official
    user = _safe_child(user_forms, name)
    if user is not None and user.is_dir() and not user.is_symlink():
        return user
    return None


def replay_active_forms(app: str, manifest) -> List[str]:
    """Ensure ledger-recorded slot choices are realized in dest.

    The deploy pipeline's replay of active slot axes — the retired
    ``_reconcile_active_parts`` bypass now runs through the same apply path
    as ``use``. Returns failing ``app:slot=value`` entries, if any.
    """
    if not manifest.forms:
        return []
    from nyxuri.kernel.ledger import get_form_slots
    slot_state = get_form_slots(app)
    if not slot_state:
        return []
    failures: List[str] = []
    for slot, cfg in manifest.forms.items():
        value = slot_state.get(slot)
        if value and value != cfg.get("default", "default"):
            if not _apply_slot(app, slot, value):
                failures.append(f"{app}:{slot}={value}")
    return failures
