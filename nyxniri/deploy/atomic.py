"""Atomic swap deployment + Dunder preservation + manifest-declared snapshots.

The atomic_replace_item swap-then-preserve is the heart of NyxNiri's deploy
(§7.1). Two preserve mechanisms live here and stay deliberately separate
(§3.2): the Dunder __custom__ walk (magic filename) and the manifest
``preserve`` snapshot (files referenced by name, e.g. niri/monitor.kdl).
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional

from nyxniri.core import get_env, log_msg, register_temp_path, remove_path
from nyxniri.i18n import msg


def _deploy_ignore_factory(root_src: Path):
    """copytree ignore: drop repo-only entries that must not ship to ~/.config.

    - .module.toml: self-describing manifest (NyxNiri metadata, §10.4 boundary)
    - __pycache__: bytecode cache, never user config
    - presets/: top-level variant source tree (only at app root, not nested)
    """
    root = root_src

    def _ignore(src_dir, names):
        skip = {n for n in names if n in ("__pycache__", ".module.toml")}
        if Path(src_dir) == root and "presets" in names:
            skip.add("presets")
        return skip

    return _ignore


def atomic_replace_item(
    src: Path, dest: Path, preserved_log: Optional[List[str]] = None,
    test_mode: bool = False, preserve: Optional[List[str]] = None,
    preserve_custom: bool = True,
) -> bool:
    """Atomic swap deployment via sibling temp directories with Dunder Protocol preservation.

    ``preserve`` injects manifest-declared files (e.g. monitor.kdl) into tmp_new
    *before* the rename, so the swapped-in directory is already complete — no
    post-rename restore window for inotify watchers to catch a half-state.
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
                old_dest = dest.with_name(f"{dest.name}.old.{pid}")
                dest.rename(old_dest)
                tmp_file.rename(dest)
                remove_path(old_dest)
            else:
                tmp_file.rename(dest)
            return True
        except Exception as e:
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

    try:
        dest_parent.mkdir(parents=True, exist_ok=True)
        if tmp_new.exists() or tmp_new.is_symlink():
            remove_path(tmp_new)
        shutil.copytree(src, tmp_new, symlinks=True, ignore=_deploy_ignore_factory(src))

        # Dunder Protocol: Scan and inherit *__custom__* files and directories
        if preserve_custom and dest.is_dir():
            # 1. Custom files
            for root, dirs, files in os.walk(dest):
                # Prune custom directories from file search to handle them in step 2
                dirs[:] = [d for d in dirs if "__custom__" not in d]
                for f in files:
                    if "__custom__" in f:
                        if test_mode and f in ("scratchpad-items__custom__.toml", "orbit-items__custom__.toml"):
                            continue
                        rel_path = Path(root).relative_to(dest) / f
                        src_custom = dest / rel_path
                        target_custom = tmp_new / rel_path
                        target_custom.parent.mkdir(parents=True, exist_ok=True)
                        if src_custom.is_symlink():
                            target_custom.unlink(missing_ok=True)
                            target_custom.symlink_to(os.readlink(src_custom))
                        else:
                            shutil.copy2(src_custom, target_custom)

                        rel_display = str(dest.relative_to(home / ".config") / rel_path)
                        print(msg("log_keep_custom_file", rel_display))
                        if preserved_log is not None:
                            preserved_log.append(f"~/.config/{rel_display}")

            # 2. Custom directories
            for root, dirs, _ in os.walk(dest):
                for d in list(dirs):
                    if "__custom__" in d:
                        dirs.remove(d)  # Don't recurse further into pruned dir
                        rel_dir = Path(root).relative_to(dest) / d
                        src_custom_dir = dest / rel_dir
                        target_custom_dir = tmp_new / rel_dir
                        target_custom_dir.parent.mkdir(parents=True, exist_ok=True)
                        shutil.rmtree(target_custom_dir, ignore_errors=True)
                        shutil.copytree(src_custom_dir, target_custom_dir, symlinks=True)

                        rel_display = str(dest.relative_to(home / ".config") / rel_dir)
                        print(msg("log_keep_custom_dir", rel_display))
                        if preserved_log is not None:
                            preserved_log.append(f"~/.config/{rel_display}/")

        # Manifest-declared preserve: inject into tmp_new before swap so the
        # renamed directory is already complete (no post-rename restore window).
        # Symlinks are preserved as links (not dereferenced) so runtime link
        # state — e.g. niri/effects.kdl → effects_normal.kdl|effects_eyecare.kdl,
        # whose target encodes the EyeCare on/off state — survives deploys.
        if preserve and dest.is_dir():
            for rel in preserve:
                src_p = dest / rel
                tgt_p = tmp_new / rel
                tgt_p.parent.mkdir(parents=True, exist_ok=True)
                if src_p.is_symlink():
                    tgt_p.unlink(missing_ok=True)
                    tgt_p.symlink_to(os.readlink(src_p))
                elif src_p.is_file():
                    shutil.copy2(src_p, tgt_p)
                else:
                    continue
                print(msg("log_keep_preserved_file", dest.name, rel))
                if preserved_log is not None:
                    preserved_log.append(f"~/.config/{dest.name}/{rel}")

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
    except Exception as e:
        remove_path(tmp_new)
        log_msg("ERROR", f"Atomic replace failed for directory {dest}: {e}")
        return False
