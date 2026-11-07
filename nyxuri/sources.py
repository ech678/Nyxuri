"""Third-party plugin lifecycle (S1): add / remove / update.

Contract: plugin-model.md §5 + manifest-schema.md 第三方章. The engine is
its own plugin manager — git is mere transport, the ledger's ``sources``
key is the origin truth (never a sidecar inside the plugin directory), and
validation is literally the loader (``registry.load_plugin``), so add and
update can never drift from what the running engine accepts.

This module lives OUTSIDE ``nyxuri/kernel/`` on purpose: the kernel stays
four modules (transaction is the only orchestrator there); lifecycle verbs
are a command-flow domain like installer/theme, consuming the kernel from
above. Argument parsing and bilingual prose belong to the CLI layer.

Safety stance (ROADMAP S1): plugins are user-trusted code — no sandboxing,
no security theater. But installing never executes anything from the
package: no install hook, no sudo, and hooks are refused for third-party
plugins in v1 (the gate lives in ``registry.load_plugin``).
"""

import shutil
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nyxuri.core import get_env, log_msg, timed_run
from nyxuri.kernel import ledger, registry, transaction

# One level of dot-separated labels minimum on each side: reverse-DNS shape
# (manifest-schema.md 身份字段 id 行). Official bare names stay unclaimable
# because they don't parse as reverse-DNS.
_REVERSE_DNS_MIN_LABELS = 2
_STAGING_NAME = "staging"
_TRASH_NAME = "trash"


# --- shape checks -------------------------------------------------------------


def is_valid_plugin_id(name: str) -> bool:
    """True iff ``name`` is a safe, non-reserved plugin id (bare or dotted)."""
    if not isinstance(name, str) or not name or name != name.strip():
        return False
    if name.startswith("shell."):
        return False
    from nyxuri.core import is_safe_leaf_name
    return is_safe_leaf_name(name)


# Backward compatibility alias
is_reverse_dns = is_valid_plugin_id


def _git(dir_: Path, *args: str, timeout: float = 60):
    """Run a git command inside ``dir_``; None on timeout (timed_run 契约)."""
    return timed_run(
        ["git", "-C", str(dir_), *args],
        timeout, capture_output=True, text=True, check=False,
    )


def _git_ok(dir_: Path, *args: str, timeout: float = 60) -> bool:
    res = _git(dir_, *args, timeout=timeout)
    return res is not None and res.returncode == 0


def _git_out(dir_: Path, *args: str, timeout: float = 60) -> str:
    res = _git(dir_, *args, timeout=timeout)
    return (res.stdout or "").strip() if res is not None and res.returncode == 0 else ""


# --- shared guards ------------------------------------------------------------


def require_third_party(plugin_id: str) -> Path:
    """Resolve a third-party plugin dir or raise ValueError with the reason."""
    src = registry.plugin_dir(plugin_id)
    if src is None:
        raise KeyError(plugin_id)
    if registry.plugin_origin(plugin_id) != "third-party":
        raise ValueError(f"'{plugin_id}' is not a third-party plugin")
    return src


def _data_plugins() -> Path:
    return get_env().data_dir / "plugins"


def _stage_dir(tag: str) -> Path:
    d = get_env().data_dir / _STAGING_NAME / tag
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_manifest_id(src: Path) -> str:
    """Pre-read just the id from a candidate plugin's manifest.

    Full validation happens through the loader after landing; this only
    decides WHERE to land. A missing/invalid manifest fails here honestly.
    """
    mpath = src / "manifest.toml"
    if not mpath.is_file():
        raise ValueError(f"no manifest.toml found at the top of '{src.name}'")
    try:
        with open(mpath, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"manifest.toml does not parse: {exc}") from exc
    pid = data.get("id")
    if not isinstance(pid, str) or not pid:
        raise ValueError("manifest must declare a non-empty string id")
    if data.get("schemaVersion") != 1:
        raise ValueError("manifest must declare schemaVersion = 1 (new-form only)")
    if not is_valid_plugin_id(pid):
        raise ValueError(
            f"plugin id '{pid}' is not a valid safe name "
            "('shell.' prefix is reserved)"
        )
    return pid


def _origin_probe(src: Path) -> tuple[str, str]:
    """(ref, commit) of a landed plugin tree; ('', '') when not a git tree."""
    if not (src / ".git").exists():
        return "", ""
    ref = _git_out(src, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _git_out(src, "rev-parse", "HEAD")
    return ref, commit


def _invalidate() -> None:
    from nyxuri.deploy.manifest import invalidate_manifest_cache

    invalidate_manifest_cache()


# --- add ----------------------------------------------------------------------


def add(source: str) -> dict[str, str]:
    """Install a third-party plugin from a git URL or a local directory.

    clone/copy → staging → pre-read id → conflict check → land under
    ``~/.local/share/nyxuri/plugins/<id>/`` → validate through the loader →
    record origin. Never executes anything from the package. Returns
    ``{"id", "dir"}`` on success; raises ValueError with the user-facing
    reason on refusal. Default state is OFF — enabling is the caller's
    (``on`` / ``--enable``) business.
    """
    local = Path(source).expanduser()
    staged: Path | None = None
    try:
        if local.is_dir():
            origin_src = local.resolve()
            origin_url = str(origin_src)
            if origin_src.is_relative_to(_data_plugins()):
                raise ValueError("source is already inside the plugin data root")
        else:
            origin_url = source
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            staged = _stage_dir(f"add-{stamp}")
            res = timed_run(
                ["git", "clone", "--quiet", origin_url, str(staged)],
                120, capture_output=True, text=True, check=False,
            )
            if res is None or res.returncode != 0:
                detail = (res.stderr or "").strip().splitlines()[-1:] if res else ["timed out"]
                raise ValueError(
                    f"git clone failed: {detail[0] if detail else 'unknown error'}"
                )
            origin_src = staged

        pid = _read_manifest_id(origin_src)
        if pid in registry.plugin_ids():
            raise ValueError(
                f"plugin id '{pid}' already exists — third-party conflicts are "
                "refused, official plugins are never shadowed by install"
            )
        target = _data_plugins() / pid
        if target.exists():
            raise ValueError(f"target directory already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if staged is not None:
            shutil.move(str(staged), str(target))
            staged = None  # moved, not to be cleaned
        else:
            shutil.copytree(
                origin_src, target,
                ignore=shutil.ignore_patterns(".git", "__pycache__"),
            )
        try:
            registry.load_plugin(pid)
        except Exception as exc:
            shutil.rmtree(target, ignore_errors=True)
            raise ValueError(f"validation failed (the loader refused): {exc}") from exc
        ref, commit = _origin_probe(target)
        ledger.set_source(pid, url=origin_url, ref=ref, commit=commit)
        _invalidate()
        return {"id": pid, "dir": str(target)}
    finally:
        if staged is not None and staged.exists():
            shutil.rmtree(staged, ignore_errors=True)


# --- remove -------------------------------------------------------------------


def remove(plugin_id: str) -> dict[str, Any]:
    """Remove a third-party plugin: off → withdraw → timestamp backup.

    The off transaction withdraws exactly the files the ownership ledger
    recorded (living area back to white, customs to Vault). The plugin tree
    itself goes to a timestamped backup when it is not pristine git content
    (local install, or dirty worktree) — pristine trees just die. Ledger
    traces (record, origin, form slots) are erased: removal leaves no debris.
    """
    src = require_third_party(plugin_id)
    rec = ledger.get_plugin(plugin_id)
    if rec and rec.get("state") == "enabled":
        steps = transaction.plugin_off(plugin_id, cascade=False)
        if steps and not all(s.ok for s in steps):
            return {"id": plugin_id, "dir": None, "backup": None,
                    "off_failed": True}
    backup: Path | None = None
    is_git = (src / ".git").exists()
    dirty = is_git and bool(_git_out(src, "status", "--porcelain"))
    if not is_git or dirty:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup = get_env().data_dir / _TRASH_NAME / f"{plugin_id}-{stamp}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(backup))
        log_msg("WARN", f"non-pristine plugin tree backed up: {backup}")
    else:
        shutil.rmtree(src)
    ledger.forget_plugin(plugin_id)
    _invalidate()
    return {"id": plugin_id, "dir": str(src),
            "backup": str(backup) if backup else None, "off_failed": False}


# --- update -------------------------------------------------------------------


def update(plugin_id: str) -> dict[str, Any]:
    """Update a third-party plugin: diff preview → ff-only → loader validation.

    Any post-pull validation failure rolls the tree back to the previous
    commit — the engine never redeploys an unvalidated blueprint. An enabled
    plugin is re-applied through the single activation pipeline afterwards.
    """
    src = require_third_party(plugin_id)
    if not (src / ".git").exists():
        raise ValueError(
            f"'{plugin_id}' was installed from a local directory (no git "
            "transport) — remove and re-add to refresh it"
        )
    origin = ledger.get_source(plugin_id)
    if not origin:
        raise ValueError(f"no origin record for '{plugin_id}' in the ledger")
    ref = origin.get("ref") or _git_out(src, "rev-parse", "--abbrev-ref", "HEAD")
    if not ref:
        raise ValueError(f"cannot determine the update ref for '{plugin_id}'")

    old_commit = _git_out(src, "rev-parse", "HEAD")
    if not _git_ok(src, "fetch", "--quiet", "origin", ref, timeout=120):
        raise ValueError(f"git fetch failed for '{plugin_id}' (origin/{ref})")
    remote = f"origin/{ref}"
    # 拒绝非 fast-forward: upstream history rewritten → the safe path is
    # remove + re-add, never a merge commit the engine cannot reason about.
    if not _git_ok(src, "merge-base", "--is-ancestor", "HEAD", remote):
        raise ValueError(
            f"origin/{ref} is not a fast-forward of the installed commit — "
            "refusing; remove and re-add if you trust the new history"
        )
    diff = _git_out(src, "--no-pager", "diff", "--name-status", "HEAD", remote)
    return {"id": plugin_id, "dir": src, "ref": ref, "old_commit": old_commit,
            "diff": diff, "remote": remote}


def update_apply(plugin_id: str, preview: dict[str, Any]) -> dict[str, Any]:
    """Apply a previewed update: merge, validate through the loader, redeploy."""
    src: Path = preview["dir"]
    remote: str = preview["remote"]
    old_commit: str = preview["old_commit"]
    if not _git_ok(src, "merge", "--ff-only", "--quiet", remote):
        raise ValueError(f"fast-forward merge failed for '{plugin_id}'")
    try:
        registry.load_plugin(plugin_id)
    except Exception as exc:
        if not _git_ok(src, "reset", "--hard", old_commit):
            log_msg("ERROR", f"rollback also failed for '{plugin_id}'; manual fix needed")
            raise ValueError(f"validation failed AND rollback failed: {exc}") from exc
        raise ValueError(
            f"validation failed — rolled back to {old_commit[:8]}: {exc}"
        ) from exc
    origin = ledger.get_source(plugin_id) or {}
    ledger.set_source(
        plugin_id, url=str(origin.get("url", "")),
        ref=str(preview["ref"]), commit=_git_out(src, "rev-parse", "HEAD"),
    )
    _invalidate()
    redeployed = False
    rec = ledger.get_plugin(plugin_id)
    if rec and rec.get("state") == "enabled":
        from nyxuri.pkg.deps import plugin_package_installer

        # form=None short-circuits at "already-enabled"; re-apply means
        # replaying the transaction with the CURRENT form choice — the
        # single activation pipeline, never a private redeploy path.
        form = rec.get("form") or "default"
        transaction.plugin_on(
            plugin_id, form=form, install_packages=plugin_package_installer
        )
        redeployed = True
    return {"id": plugin_id, "applied": True, "redeployed": redeployed}
