"""Atomic swap deployment + Dunder preservation + manifest-declared snapshots.

The atomic_replace_item swap-then-preserve is the heart of Nyxuri's deploy
(§7.1). Three preservation layers live here and stay deliberately separate
(§3.2): the Dunder __custom__ walk (magic filename), the manifest ``preserve``
snapshot (files referenced by name, e.g. niri/monitor.kdl), and the ownership
carry (#139): dest entries the engine cannot explain as its own template
output are carried into the new directory verbatim — a swap never destroys
what it cannot account for. The carry verdict is judged against the ledger
baseline injected by the caller; this module never reads the ledger itself
(star layering, unit-model.md §2).
"""

import fnmatch
import hashlib
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from nyxuri.core import get_env, log_msg, register_temp_path, remove_path
from nyxuri.core import msg


@dataclass(frozen=True)
class CarryPolicy:
    """Ownership-carry directive threaded from the transaction layer (#139).

    ``baselines`` maps plugin id → the ledger ``files`` snapshot (hashes of what
    the engine last laid) or None for plugins with no record (Ghost). ``unknown``
    decides the baseline-absent case: True = carry (update — 宁可错保), False =
    the engine claims its payload names (install/``on`` adoption). ``carried``
    is the out-map: plugin id → {rel path: "modified"|"user"|"unknown"} filled
    by the swap ("unknown" = Ghost-era content whose provenance cannot be
    judged; never counted as the user's edit in reports).
    """

    baselines: Dict[str, Optional[Dict[str, str]]] = field(default_factory=dict)
    unknown: bool = False
    carried: Dict[str, Dict[str, str]] = field(default_factory=dict)


_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_ASSIGN_RE = re.compile(r"^(\s*)([A-Za-z0-9_][A-Za-z0-9_-]*)(\s*=\s*)(.+?)\s*$")


def _toml_scalars(path: Path, keys: List[str]) -> Dict[Tuple[str, str], str]:
    """Read ``(section, key) -> raw value text`` for the named keys.

    Values are captured as written, so a carried-over value keeps its original
    spelling instead of being re-serialised by a TOML writer.
    """
    wanted = set(keys)
    found: Dict[Tuple[str, str], str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return found
    section = ""
    for line in text.splitlines():
        header = _SECTION_RE.match(line)
        if header is not None:
            section = header.group(1).strip()
            continue
        if line.lstrip().startswith("#"):
            continue
        assign = _ASSIGN_RE.match(line)
        if assign is None:
            continue
        name = assign.group(2)
        if name in wanted:
            found.setdefault((section, name), assign.group(4))
    return found


def _apply_toml_scalars(path: Path, values: Dict[Tuple[str, str], str]) -> int:
    """Overwrite the named keys in ``path`` in place, returning how many landed.

    Only the matched assignment lines are rewritten, so every other byte of the
    freshly deployed file — including comments and section order — is untouched.
    """
    if not values:
        return 0
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    lines = text.splitlines(keepends=True)
    section = ""
    applied = 0
    for index, line in enumerate(lines):
        body = line.rstrip("\r\n")
        header = _SECTION_RE.match(body)
        if header is not None:
            section = header.group(1).strip()
            continue
        if body.lstrip().startswith("#"):
            continue
        assign = _ASSIGN_RE.match(body)
        if assign is None:
            continue
        raw = values.get((section, assign.group(2)))
        if raw is None:
            continue
        lines[index] = "".join([assign.group(1), assign.group(2), assign.group(3), raw, "\n"])
        applied += 1
    if applied:
        path.write_text("".join(lines), encoding="utf-8")
    return applied


def _matches_pattern(rel_str: str, is_dir: bool, patterns: List[str]) -> bool:
    for pat in patterns:
        pat = pat.strip()
        if not pat:
            continue
        if fnmatch.fnmatch(rel_str, pat):
            return True
        name = rel_str.split("/")[-1]
        if fnmatch.fnmatch(name, pat):
            return True
        if pat.startswith("**/") and fnmatch.fnmatch(name, pat[3:]):
            return True
        parts = rel_str.split("/")
        base_pat = pat.rstrip("/*")
        for index in range(1, len(parts)):
            if fnmatch.fnmatch("/".join(parts[:index]), base_pat):
                return True
    return False


def _include_could_match(rel_str: str, patterns: List[str]) -> bool:
    for pat in patterns:
        pat = pat.strip()
        if not pat:
            continue
        if "/" not in pat or pat.startswith("**/"):
            return True
        prefix = pat.rstrip("/*")
        if rel_str == prefix or prefix.startswith(rel_str + "/") or rel_str.startswith(prefix + "/"):
            return True
    return False


def _base_deploy_ignore_factory(
    root_src: Path,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
):
    """copytree ignore for base overlay: drops repo-only entries and applies whitelists/blacklists."""
    root = root_src
    inc = [p for p in (include_patterns or []) if p and p.strip()]
    exc = [p for p in (exclude_patterns or []) if p and p.strip()]

    def _ignore(src_dir, names):
        skip = {n for n in names if n in ("__pycache__", "manifest.toml", "hooks")}
        if Path(src_dir) == root:
            if "presets" in names:
                skip.add("presets")
            if "__presets__" in names:
                skip.add("__presets__")

        cur_dir = Path(src_dir)
        for name in names:
            if name in skip:
                continue
            item_path = cur_dir / name
            try:
                rel_str = item_path.relative_to(root).as_posix()
            except ValueError:
                rel_str = name
            is_dir = item_path.is_dir() and not item_path.is_symlink()

            # 1. Whitelist (include)
            if inc and not _matches_pattern(rel_str, is_dir, inc):
                if not is_dir or not _include_could_match(rel_str, inc):
                    skip.add(name)
                    continue

            # 2. Blacklist (exclude)
            if exc and _matches_pattern(rel_str, is_dir, exc):
                skip.add(name)
                continue

        return skip

    return _ignore


def _deploy_ignore_factory(root_src: Path):
    """copytree ignore: drop repo-only entries that must not ship to ~/.config.

    - manifest.toml: self-describing manifest (Nyxuri metadata, §10.4 boundary)
    - __pycache__: bytecode cache, never user config
    - hooks/: plugin lifecycle hooks (declared side effects, run by transaction only)
    - presets/ & __presets__/: top-level variant source tree (only at app root, not nested)
    """
    root = root_src

    def _ignore(src_dir, names):
        skip = {n for n in names if n in ("__pycache__", "manifest.toml", "hooks")}
        if Path(src_dir) == root:
            if "presets" in names:
                skip.add("presets")
            if "__presets__" in names:
                skip.add("__presets__")
        return skip

    return _ignore


def _path_identity(path: Path) -> str:
    """Content identity in the ledger snapshot's encoding (symlink → ``link:``).

    Must stay byte-compatible with ``transaction._hash_file`` so carried
    verdicts compare equal against ledger baselines.
    """
    try:
        if path.is_symlink():
            return "link:" + os.readlink(path)
    except OSError:
        return ""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def _walk_rels(root: Path) -> Iterator[Tuple[str, Path]]:
    """Yield ``(rel_posix, path)`` for every file and symlink under ``root``.

    Dunder entries are pruned (the dedicated walk owns them); ``__pycache__``
    and ``*.pyc`` are pruned too — bytecode cache is neither template payload
    nor user content, it must never be carried nor reported (#139 field
    report). A symlinked directory is yielded as a leaf link instead of being
    descended into.
    """
    for dirpath, dirs, files in os.walk(root):
        keep = []
        for d in dirs:
            if "__custom__" in d or d == "__pycache__":
                continue
            p = Path(dirpath) / d
            if p.is_symlink():
                yield p.relative_to(root).as_posix(), p
            else:
                keep.append(d)
        dirs[:] = keep
        for name in files:
            if "__custom__" in name or name.endswith(".pyc"):
                continue
            p = Path(dirpath) / name
            yield p.relative_to(root).as_posix(), p


def atomic_replace_item(
    src: Path, dest: Path, preserved_log: Optional[List[str]] = None,
    test_mode: bool = False, preserve: Optional[List[str]] = None,
    preserve_values: Optional[Dict[str, List[str]]] = None,
    preserve_custom: bool = True,
    base_src: Optional[Path] = None,
    base_include: Optional[List[str]] = None,
    base_exclude: Optional[List[str]] = None,
    carry: bool = False,
    carry_baseline: Optional[Dict[str, str]] = None,
    carry_unknown: bool = False,
    carried_out: Optional[Dict[str, str]] = None,
) -> bool:
    """Atomic swap deployment via sibling temp directories with Dunder Protocol preservation.

    ``preserve`` injects manifest-declared files (e.g. monitor.kdl) into tmp_new
    *before* the rename, so the swapped-in directory is already complete — no
    post-rename restore window for inotify watchers to catch a half-state.

    ``preserve_values`` carries individual keys of a deployed text config across
    the swap (e.g. noctalia's brightness.enable_ddcutil, which the user may have
    turned on and which the shipped default would otherwise reset). Values are
    read from the outgoing file and written into the staged copy, so the same
    no-restore-window property holds.

    Ownership carry (#139): with ``carry=True``, dest entries outside the
    dunder/preserve/preserve_values sets are judged against ``carry_baseline``
    (the plugin's ledger ``files`` map — hashes of what the engine last laid).
    Untouched engine-laid files follow the new template; untouched engine-laid
    files this deploy no longer lays (hook products) retire with the swap and
    are re-laid by the hook replay; user-modified and user-placed files are
    carried verbatim and reported via ``carried_out``
    ({rel: "modified"|"user"|"unknown"}). ``carry_unknown`` rules the
    baseline-absent case: True carries (update — 宁可错保), False lets the
    engine claim its payload names (install / ``on`` adoption). Off by
    default: bare calls keep the plain template-swap semantics; workflows
    opt in explicitly.
    """
    pid = os.getpid()
    dest_parent = dest.parent
    home = get_env().home

    if src.is_file():
        tmp_file = dest.with_name(f"{dest.name}.new.{pid}")
        register_temp_path(tmp_file)
        old_dest = None
        try:
            dest_parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp_file)
            if dest.exists() or dest.is_symlink():
                # Ownership carry (#139), single-file shape: the payload is the
                # file itself, so the verdict table collapses to untouched /
                # identical / user-modified / unknown.
                keep_user = False
                kind = "modified"
                if carry:
                    d_ident = _path_identity(dest)
                    untouched = carry_baseline is not None and carry_baseline.get(dest.name) == d_ident
                    if not untouched and _path_identity(tmp_file) != d_ident:
                        if carry_baseline is not None and dest.name in carry_baseline:
                            keep_user = True
                        elif carry_unknown:
                            # Ghost (no record): provenance unknowable — carry,
                            # but report it honestly as unresolved.
                            keep_user = True
                            kind = "unknown"
                if keep_user:
                    try:
                        rel_display = str(dest.relative_to(home / ".config"))
                    except ValueError:
                        rel_display = str(dest)
                    print(msg(
                        "log_keep_modified_file" if kind == "modified"
                        else "log_keep_unresolved_file" if kind == "unknown"
                        else "log_keep_user_file",
                        rel_display,
                    ))
                    if preserved_log is not None:
                        preserved_log.append(f"~/.config/{rel_display}")
                    if carried_out is not None:
                        carried_out[dest.name] = kind
                    remove_path(tmp_file)
                    return True
                old_dest = dest.with_name(f"{dest.name}.old.{pid}")
                dest.rename(old_dest)
                tmp_file.rename(dest)
                remove_path(old_dest)
            else:
                tmp_file.rename(dest)
            return True
        except BaseException as e:
            remove_path(tmp_file)
            if old_dest is not None and old_dest.exists():
                try:
                    old_dest.rename(dest)
                except Exception:
                    pass
            log_msg("ERROR", f"Atomic replace failed for {dest}: {e}")
            return False

    tmp_new = dest.with_name(f"{dest.name}.new.{pid}")
    register_temp_path(tmp_new)

    old_dest = None
    try:
        dest_parent.mkdir(parents=True, exist_ok=True)
        if tmp_new.exists() or tmp_new.is_symlink():
            remove_path(tmp_new)
        if base_src is not None and base_src.is_dir() and base_src != src:
            shutil.copytree(
                base_src,
                tmp_new,
                symlinks=True,
                ignore=_base_deploy_ignore_factory(base_src, base_include, base_exclude),
            )
            shutil.copytree(
                src,
                tmp_new,
                symlinks=True,
                ignore=_deploy_ignore_factory(src),
                dirs_exist_ok=True,
            )
        else:
            shutil.copytree(src, tmp_new, symlinks=True, ignore=_deploy_ignore_factory(src))

        # Payload truth: identities of the incoming template, judged against
        # dest in the carry pass below. Computed before any injection so the
        # dunder/preserve copies never count as "template content".
        payload: Dict[str, str] = {}
        if carry and dest.is_dir():
            for rel, p in _walk_rels(tmp_new):
                payload[rel] = _path_identity(p)

        # Dunder Protocol: Scan and inherit *__custom__* files and directories
        if preserve_custom and dest.is_dir():
            preserve_entries = []
            for root, dirs, files in os.walk(dest):
                custom_dirs = [d for d in dirs if "__custom__" in d]
                for d in custom_dirs:
                    dirs.remove(d)
                    preserve_entries.append(("dir", root, d))
                for f in files:
                    if "__custom__" in f:
                        if test_mode and f in ("scratchpad-items__custom__.toml", "orbit-items__custom__.toml"):
                            continue
                        preserve_entries.append(("file", root, f))

            for entry_type, root, name in preserve_entries:
                rel_path = Path(root).relative_to(dest) / name
                src_item = dest / rel_path
                target_item = tmp_new / rel_path
                target_item.parent.mkdir(parents=True, exist_ok=True)
                if entry_type == "dir":
                    shutil.rmtree(target_item, ignore_errors=True)
                    shutil.copytree(src_item, target_item, symlinks=True)
                elif src_item.is_symlink():
                    target_item.unlink(missing_ok=True)
                    target_item.symlink_to(os.readlink(src_item))
                else:
                    shutil.copy2(src_item, target_item)
                try:
                    rel_display = str(dest.relative_to(home / ".config") / rel_path)
                except ValueError:
                    rel_display = str(dest / rel_path)
                suffix = "/" if entry_type == "dir" else ""
                print(msg("log_keep_custom_dir" if entry_type == "dir" else "log_keep_custom_file", rel_display + suffix))
                if preserved_log is not None:
                    preserved_log.append(f"~/.config/{rel_display}{suffix}")

        # Manifest-declared preserve: inject into tmp_new before swap so the
        # renamed directory is already complete (no post-rename restore window).
        # Symlinks are preserved as links (not dereferenced) so runtime link
        # state — e.g. niri/effects.kdl → effects_normal.kdl|effects_eyecare.kdl,
        # whose target encodes the EyeCare on/off state — survives deploys.
        if preserve and dest.is_dir():
            dest_root = dest.resolve()
            new_root = tmp_new.resolve()
            for rel in preserve:
                if not rel or os.path.isabs(rel):
                    continue
                src_p = dest / rel
                tgt_p = tmp_new / rel
                try:
                    src_p.resolve(strict=False).relative_to(dest_root)
                    tgt_p.resolve(strict=False).relative_to(new_root)
                except ValueError:
                    continue
                tgt_p.parent.mkdir(parents=True, exist_ok=True)
                if src_p.is_symlink():
                    tgt_p.unlink(missing_ok=True)
                    tgt_p.symlink_to(os.readlink(src_p))
                elif src_p.is_file():
                    shutil.copy2(src_p, tgt_p)
                elif src_p.is_dir():
                    # Directory preserve (#139 field report): a whole runtime-
                    # managed tree (e.g. fish/functions — Fisher's territory)
                    # is carried as one plugin, injected before the rename. The
                    # declaration is a promise: the template lays NOTHING in
                    # this directory (mixed payload would freeze forever).
                    shutil.rmtree(tgt_p, ignore_errors=True)
                    shutil.copytree(src_p, tgt_p, symlinks=True)
                else:
                    continue
                print(msg("log_keep_preserved_file", dest.name, rel))
                if preserved_log is not None:
                    preserved_log.append(f"~/.config/{dest.name}/{rel}")

        if preserve_values and dest.is_dir():
            dest_root = dest.resolve()
            new_root = tmp_new.resolve()
            for rel, keys in preserve_values.items():
                if not rel or os.path.isabs(rel) or not keys:
                    continue
                src_p = dest / rel
                tgt_p = tmp_new / rel
                try:
                    src_p.resolve(strict=False).relative_to(dest_root)
                    tgt_p.resolve(strict=False).relative_to(new_root)
                except ValueError:
                    continue
                if not src_p.is_file() or not tgt_p.is_file():
                    continue
                if not _apply_toml_scalars(tgt_p, _toml_scalars(src_p, keys)):
                    continue
                print(msg("log_keep_preserved_file", dest.name, rel))
                if preserved_log is not None:
                    preserved_log.append(f"~/.config/{dest.name}/{rel}")

        # Ownership carry (#139): a swap never destroys what the engine cannot
        # explain as its own output. Dunder / preserve / preserve_values
        # entries are exempt (their own mechanisms own them). The TENancy
        # boundary is the LEDGER, not the payload: a baseline path the engine
        # laid and the user never touched is engine-owned even when this
        # deploy no longer lays it (hook products) — it vanishes with the
        # swap and the hook replay re-lays it (KM3 restored).
        if carry and dest.is_dir():
            exempt = {rel for rel in (preserve or []) if rel and not os.path.isabs(rel)}
            exempt.update(rel for rel in (preserve_values or {}) if rel)
            exempt_prefixes = tuple(entry + "/" for entry in exempt)
            for rel, src_p in _walk_rels(dest):
                if rel in exempt or rel.startswith(exempt_prefixes):
                    continue  # dunder/preserve (incl. directory trees) are theirs
                d_ident = _path_identity(src_p)
                in_baseline = carry_baseline is not None and rel in carry_baseline
                untouched = in_baseline and carry_baseline.get(rel) == d_ident
                if rel not in payload:
                    if untouched:
                        continue  # engine-laid, untouched, not laid this time: retire
                    kind = "user" if not in_baseline else "modified"
                    carry_it = True
                elif untouched:
                    continue  # untouched since the last lay: template wins
                elif payload[rel] == d_ident:
                    continue  # already at target content: nothing user-owned
                elif in_baseline:
                    kind, carry_it = "modified", True
                elif carry_baseline is not None:
                    # Enabled plugin, engine never laid this name, dest has it:
                    # the dest copy is not ours to explain.
                    kind, carry_it = "unknown", carry_unknown
                else:
                    # Ghost dest: provenance unknowable (user edit OR last
                    # era's template render). Carry, but say so honestly.
                    kind, carry_it = "unknown", carry_unknown
                if not carry_it:
                    continue
                target = tmp_new / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if src_p.is_symlink():
                    remove_path(target)
                    target.symlink_to(os.readlink(src_p))
                elif src_p.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                    shutil.copytree(src_p, target, symlinks=True)
                else:
                    shutil.copy2(src_p, target)
                try:
                    rel_display = str(dest.relative_to(home / ".config") / rel)
                except ValueError:
                    rel_display = str(dest / rel)
                print(msg(
                    "log_keep_modified_file" if kind == "modified"
                    else "log_keep_unresolved_file" if kind == "unknown"
                    else "log_keep_user_file",
                    rel_display,
                ))
                if preserved_log is not None:
                    preserved_log.append(f"~/.config/{rel_display}")
                if carried_out is not None:
                    carried_out[rel] = kind

        if dest.exists() or dest.is_symlink():
            old_dest = dest.with_name(f"{dest.name}.old.{pid}")
            dest.rename(old_dest)
            try:
                tmp_new.rename(dest)
                remove_path(old_dest)
            except Exception:
                old_dest.rename(dest)
                raise
            return True
        else:
            tmp_new.rename(dest)
            return True
    except BaseException as e:
        remove_path(tmp_new)
        if old_dest is not None and old_dest.exists() and not dest.exists():
            try:
                old_dest.rename(dest)
            except OSError:
                pass
        log_msg("ERROR", f"Atomic replace failed for directory {dest}: {e}")
        return False
