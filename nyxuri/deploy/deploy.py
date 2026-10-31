"""Deploy orchestrator — config discovery, atomic-deploy phase, post-install
services, completion screen, fisher uninstall, and the deploy/test entry points.

Coordinates the deploy/ siblings: atomic (swap+preserve), templates (render),
assets (wallpapers), manifest (app discovery), preset
(active variant). Modules/state/deps are lazy-imported to avoid cycles.
"""

import os
import shutil
import sys
import time
from contextlib import ExitStack
from typing import List, Optional

from nyxuri.core import Colors, REPO_URL, THEME_ENGINE
from nyxuri.core import get_env, log_msg, timed_run
from nyxuri.core import msg
from nyxuri.tui import read_key, responsive_hint, show_logo, raw_input_mode, _drain_pending

from nyxuri.deploy.atomic import (
    CarryPolicy,
    atomic_replace_item,
)
from nyxuri.deploy.manifest import (
    ModuleManifest,
    discover_deployable_apps,
    load_manifest,
    living_path,
)
from nyxuri.deploy.preset import (
    InvalidActivePresetError,
    PresetSrcResult,
    read_active_preset,
    resolve_preset_src,
    write_active_preset,
)
from nyxuri.deploy.templates import _phase_render_templates, prepare_screenshot_directory

_CONFIG_ITEMS_CACHE: List[str] = []
USER_HOOK_TIMEOUT = 30

def discover_config_items() -> List[str]:
    """Deployable config app names (manifest-only dirs like nautilus/ are excluded)."""
    global _CONFIG_ITEMS_CACHE
    if _CONFIG_ITEMS_CACHE:
        return _CONFIG_ITEMS_CACHE
    # Honest empty when nothing is discoverable (broken/unreadable configs/);
    # install.sh's engine_is_complete guards configs/ exists before we run,
    # so a real empty here is an edge case — downstream degrades to "0 configs".
    _CONFIG_ITEMS_CACHE = discover_deployable_apps()
    return _CONFIG_ITEMS_CACHE


def config_item_dest(item: str) -> Path:
    """Living-space path for a unit: ``~/.config/<target>`` for single-file
    units, else ``~/.config/<item>`` (unit-model.md §4 target exception)."""
    from nyxuri.core import get_env
    m = load_manifest(get_env().units_src / item)
    return living_path(m, get_env().config_dir)


def config_item_src(item: str) -> Path:
    """Blueprint payload path for a unit: the target file itself for
    single-file units, else the unit directory."""
    from nyxuri.core import get_env
    m = load_manifest(get_env().units_src / item)
    src = get_env().units_src / item
    return src / m.target if m.target else src

def _phase_atomic_deployment(
    items_to_deploy: List[str],
    keep_preserved: bool = True,
    preserved_log: Optional[List[str]] = None,
    test_mode: bool = False,
    carry_policy: Optional[CarryPolicy] = None,
    preset_overrides: Optional[dict] = None,
    reconcile_parts: bool = True,
) -> List[str]:
    """Execute atomic copy for selected configuration units.

    Per-app manifest drives: the preserve list (files kept across deploys,
    e.g. niri/monitor.kdl), and the chmod globs (executable scripts). The
    Dunder __custom__ walk inside atomic_replace_item is untouched.

    ``carry_policy`` (issue #139) threads the transaction layer's ownership
    verdict per unit: baselines from the ledger, the unknown-provenance
    stance, and the out-map of carried files. None = plain template swap.
    """
    env = get_env()
    config_dir = env.config_dir
    config_dir.mkdir(parents=True, exist_ok=True)

    failed_items: List[str] = []
    for item in items_to_deploy:
        # Manifest always loaded from the app root (not the preset dir):
        # preserve/chmod describe the app, independent of which variant ships.
        manifest = load_manifest(env.units_src / item)

        if manifest.target:
            # Single-file unit (§4 target exception): one file inside the
            # unit dir lands at ~/.config/<target>. Presets and parts are
            # directory affordances and do not apply.
            src = env.units_src / item / manifest.target
            dest = config_dir / manifest.target
            if not src.is_file():
                failed_items.append(item)
                print(msg("log_deploy_config_failed", item), file=sys.stderr)
                log_msg("ERROR", f"Missing target file for unit '{item}': {src}")
                continue
            # No preset/base resolution applies; a concrete result keeps the
            # atomic call below bound (a stale loop iteration must never leak).
            result = PresetSrcResult(src=src, reset_active=None)
        else:
            dest = config_dir / item

            # Resolve which source tree to deploy: default config, an official
            # preset, or a user preset — based on the app's active state file.
            try:
                active = read_active_preset(item)
            except InvalidActivePresetError:
                print(msg("preset_warn_invalid_active", item))
                log_msg("WARN", f"Invalid active preset state for {item}; dest frozen, skipped")
                failed_items.append(item)
                continue
            if preset_overrides and item in preset_overrides:
                # 显式选择已在事务预检；缺失生活区不能把选择静默改回 default。
                from nyxuri.deploy.preset import _find_preset_src, resolve_preset_inheritance
                active = preset_overrides[item]
                selected = _find_preset_src(item, active)
                base, include, exclude = resolve_preset_inheritance(item, active)
                result = PresetSrcResult(src=selected, reset_active=None,
                    base_src=base, base_include=include, base_exclude=exclude)
            else:
                result = resolve_preset_src(item, active, dest)
            for w in result.warnings:
                print(w)
            if result.src is None:
                # Preset not found anywhere — freeze dest, do not fall back to
                # default (would silently wipe the user's config). §3.2
                log_msg("WARN", f"Preset '{active}' for {item} not found; dest frozen, skipped")
                failed_items.append(item)
                continue
            src = result.src
            # dest-missing reset: sanctioned write-before-deploy (dest is empty,
            # so a half-written state self-heals next run). §3.2
            if result.reset_active is not None:
                try:
                    write_active_preset(item, result.reset_active)
                except Exception as e:
                    log_msg("ERROR", f"Failed to write active preset for {item}: {e}")

            if not src.exists():
                failed_items.append(item)
                print(msg("log_deploy_config_failed", item), file=sys.stderr)
                log_msg("ERROR", f"Missing config source: {src}")
                continue

        preserve = manifest.preserve if keep_preserved else None
        preserve_values = manifest.preserve_values if keep_preserved else None

        carry_kwargs = {}
        if carry_policy is not None:
            carry_kwargs = dict(
                carry=True,
                carry_baseline=carry_policy.baselines.get(item),
                carry_unknown=carry_policy.unknown,
                carried_out=carry_policy.carried.setdefault(item, {}),
            )

        if not atomic_replace_item(
            src,
            dest,
            preserved_log=preserved_log,
            test_mode=test_mode,
            preserve=preserve,
            preserve_values=preserve_values,
            base_src=result.base_src,
            base_include=result.base_include,
            base_exclude=result.base_exclude,
            **carry_kwargs,
        ):
            failed_items.append(item)
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            continue

        # Executable permissions — manifest chmod globs, relative to app dir
        for pattern in manifest.chmod:
            if not pattern or os.path.isabs(pattern):
                continue
            for p in dest.glob(pattern):
                if p.is_file():
                    try:
                        p.chmod(0o755)
                    except OSError:
                        pass

        reconcile_failures = _reconcile_active_parts(item, manifest) if reconcile_parts else []
        if reconcile_failures:
            failed_items.append(item)
            print(msg("log_part_reconcile_failed", item, ", ".join(reconcile_failures)), file=sys.stderr)

        print(msg("log_deploy_config_item", item))
        log_msg("INFO", f"Deployed config {dest.relative_to(config_dir).as_posix()} (unit {item})")

    return failed_items


def merge_deploy_unit(item: str, manifest: ModuleManifest, *,
                      baseline: Optional[dict] = None, force: bool = False,
                      include_rels: Optional[set[str]] = None) -> Optional[List[str]]:
    """共享目录逐文件刷新；只更新未修改受管文件，新文件落地，外来内容保留。"""
    from nyxuri.deploy.atomic import _path_identity
    env = get_env()
    src_root = env.units_src / item
    dest = living_path(manifest, env.config_dir)
    baseline = baseline or {}
    laid = []
    incoming = set()
    try:
        for path in sorted(src_root.rglob("*")):
            rel = path.relative_to(src_root)
            if path.is_dir() or path.name == "manifest.toml" or any(p in ("hooks", "presets", "__presets__", "__pycache__") for p in rel.parts):
                continue
            name = rel.as_posix()
            if include_rels is not None and name not in include_rels:
                continue
            if "__custom__" in name or any(name == p or name.startswith(p + "/") for p in manifest.preserve):
                if (dest / rel).exists():
                    continue
            incoming.add(name)
            target = dest / rel
            if not target.parent.resolve().is_relative_to(dest.resolve()):
                raise ValueError(f"Merge path escapes target: {target}")
            if target.exists() or target.is_symlink():
                if not force and baseline.get(name) != _path_identity(target):
                    continue
            if not atomic_replace_item(path, target):
                return None
            laid.append(name)
        # 源码删除只撤回内容仍与历史基线一致的文件，修改过的旧文件仍留给用户。
        for rel, digest in baseline.items():
            target = dest / rel
            if rel not in incoming and _path_identity(target) == digest:
                target.unlink()
        for pattern in manifest.chmod:
            if pattern and not os.path.isabs(pattern):
                for path in dest.glob(pattern):
                    if path.is_file():
                        path.chmod(0o755)
    except (OSError, ValueError) as exc:
        log_msg("ERROR", f"Merge deploy failed for '{item}': {exc}")
        return None
    return laid


WALLPAPER_VIDEO_SUFFIXES = frozenset({".mp4", ".webm"})


def wallpapers_pack_present() -> bool:
    """Whether the external wallpaper pack lives in the shared living area.

    Validated by requiring at least one deployed video file. The pack is
    user-domain content (installed via the unit's ``install-pack`` script),
    never ledger-tracked.
    """
    from nyxuri.core import get_pics_dir

    video_dir = get_pics_dir() / "Wallpapers" / "video"
    try:
        return video_dir.is_dir() and any(
            path.is_file() and path.suffix.lower() in WALLPAPER_VIDEO_SUFFIXES
            for path in video_dir.rglob("*")
        )
    except OSError:
        return False


def _reconcile_active_parts(app: str, manifest: ModuleManifest) -> List[str]:
    """Ensure ledger-recorded active parts are realized in dest."""
    if not manifest.parts:
        return []
    from nyxuri.kernel.ledger import read_ledger
    from nyxuri.deploy.preset import apply_part
    parts_state = read_ledger().get("parts", {})
    if not isinstance(parts_state, dict):
        return []
    failures: List[str] = []
    for slot, cfg in manifest.parts.items():
        var = parts_state.get(f"{app}:{slot}")
        if var and var != cfg.get("default", "default"):
            if not apply_part(app, slot, var, _preserve_conflicts=True):
                failures.append(f"{app}:{slot}={var}")
    return failures

def run_user_hooks() -> List[str]:
    """Run user-owned scripts and return non-blocking diagnostics."""
    hooks_dir = get_env().nyx_dir / "hooks"
    if not hooks_dir.is_dir():
        return []

    diagnostics: List[str] = []
    hooks = sorted(
        (path for path in hooks_dir.glob("*.sh") if path.is_file()),
        key=lambda path: path.name,
    )
    for hook in hooks:
        result = timed_run(["bash", str(hook)], USER_HOOK_TIMEOUT, check=False)
        if result is None:
            log_msg("WARN", f"User deploy hook {hook.name} timed out after {USER_HOOK_TIMEOUT}s")
            diagnostic = msg("user_hook_timeout", hook.name, USER_HOOK_TIMEOUT)
            print(diagnostic, file=sys.stderr)
            diagnostics.append(diagnostic)
        elif result.returncode != 0:
            log_msg("WARN", f"User deploy hook {hook.name} exited with {result.returncode}")
            diagnostic = msg("user_hook_failed", hook.name, result.returncode)
            print(diagnostic, file=sys.stderr)
            diagnostics.append(diagnostic)
    return diagnostics


def _phase_post_install_services() -> None:
    """Run built-in post-deployment work (theme sync).

    Unit activation is user policy, not a deploy side effect: enabled units
    replay their declared hooks via ``transaction.replay_enabled_hooks()``
    in the workflow; the retired module direct-calls are gone (KM3).
    """
    try:
        from nyxuri.desktop.theme import sync
        sync()
        print(msg("log_gtk_theme_init"))
    except Exception as e:
        log_msg("WARN", f"Theme sync failed during deploy: {e}")

def render_completion_screen(
    mode: str = "install",
    chosen_items: Optional[List[str]] = None,
    preserved_lines: Optional[List[str]] = None,
    wallpaper_ok: Optional[bool] = None,
    failed_items: Optional[List[str]] = None,
    hook_diagnostics: Optional[List[str]] = None,
    notice_lines: Optional[List[str]] = None,
    carried_groups: Optional[Dict[str, List[str]]] = None,
    wallpaper_selected: Optional[bool] = None,
) -> None:
    """Render completion state, including non-blocking hook diagnostics.

    壁纸状态来自本轮选择及事务结果：未选择与已选择但尚未执行分开显示，
    不用外部手动视频包的存在情况推断成功。

    ``carried_groups`` (#139): carried files keyed by verdict — "modified"
    (user edits, template has newer), "user" (user-placed), "unknown"
    (unregistered unit). Different verdicts, different sections: one bucket
    would read as "all of this is yours" and erode trust in the report.
    """
    if chosen_items is None:
        chosen_items = discover_config_items()
    if wallpaper_selected is None:
        wallpaper_selected = "wallpapers" in chosen_items or wallpaper_ok is not None
    if preserved_lines is None:
        preserved_lines = []
    if failed_items is None:
        failed_items = []
    if hook_diagnostics is None:
        hook_diagnostics = []
    if notice_lines is None:
        notice_lines = []
    if carried_groups is None:
        carried_groups = {}

    from nyxuri.pkg.deps import get_missing_deps

    title_key = "summary_title_failed" if failed_items else ("summary_title_update" if mode == "update" else ("summary_title_test" if mode == "test" else "summary_title_install"))
    missing_deps = get_missing_deps() if mode == "full" else []

    def _render_body():
        title_color = Colors.BOLD_RED if failed_items else Colors.BOLD_GREEN
        sys.stdout.write(f"  {title_color}{msg(title_key)}{Colors.RESET}\n\n")
        sys.stdout.write(f"  {Colors.BOLD_WHITE}{msg('summary_section_details')}{Colors.RESET}\n")

        if failed_items:
            sys.stdout.write(f"    {Colors.BOLD_RED}[✗]{Colors.RESET} {msg('summary_item_configs_failed', ', '.join(failed_items))}\n")
        elif chosen_items or mode == "test":
            sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_configs_ok', len(chosen_items))}\n")
        else:
            sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_configs_skip')}\n")

        if mode in ("full", "update", "test"):
            if not wallpaper_selected:
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_skip", Colors.BOLD_YELLOW, "[!]"
            elif wallpaper_ok is True:
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_existing", Colors.BOLD_GREEN, "[✓]"
            elif wallpaper_ok is False:
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_failed", Colors.BOLD_RED, "[✗]"
            else:
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_not_run", Colors.BOLD_YELLOW, "[!]"
            sys.stdout.write(f"    {wallpaper_color}{wallpaper_icon}{Colors.RESET} {msg(wallpaper_key)}\n")

        if mode == "full":
            if not missing_deps:
                sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_deps_ok')}\n")
            else:
                sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_deps_skip')}\n")

        if hook_diagnostics:
            sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_hooks')}{Colors.RESET}\n")
            for diagnostic in hook_diagnostics:
                sys.stdout.write(f"    {diagnostic}\n")

        if preserved_lines:
            sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_preserved')}{Colors.RESET}\n")
            for pline in sorted(set(preserved_lines)):
                sys.stdout.write(f"    {pline}\n")

        if carried_groups:
            section_keys = (
                ("modified", "summary_section_modified"),
                ("user", "summary_section_user_files"),
                ("unknown", "summary_section_unknown"),
            )
            for kind, key in section_keys:
                lines = carried_groups.get(kind) or []
                if not lines:
                    continue
                sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg(key)}{Colors.RESET}\n")
                for cline in sorted(set(lines)):
                    sys.stdout.write(f"    {cline}\n")

        if notice_lines:
            sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_notice')}{Colors.RESET}\n")
            for nline in notice_lines:
                sys.stdout.write(f"    {nline}\n")

    if not sys.stdin.isatty() or mode == "test":
        sys.stdout.write(Colors.CLEAR_SCREEN)
        show_logo()
        _render_body()
        sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_next')}{Colors.RESET}\n")
        sys.stdout.write(f"    {msg('summary_next_start')}\n")
        sys.stdout.write(f"    {msg('summary_next_manual')}\n")
        sys.stdout.write(f"    {msg('summary_next_panel')}\n\n")
        return

    # Interactive Next Steps Menu
    from nyxuri.pkg.deps import run_optional_apps_menu_loop
    focus = 0
    sys.stdout.write(Colors.CURSOR_HIDE)
    fd = sys.stdin.fileno()
    stack = ExitStack()
    stack.enter_context(raw_input_mode(fd))
    try:
        _drain_pending(fd)
        while True:
            sys.stdout.write(Colors.CLEAR_SCREEN)
            show_logo()
            _render_body()

            sys.stdout.write(msg("summary_action_title"))
            from nyxuri.tui import render_menu_item
            render_menu_item(0, msg("summary_action_apps"), focus)
            render_menu_item(1, msg("summary_action_star"), focus)
            render_menu_item(2, msg("summary_action_exit"), focus, style="subtle")

            sys.stdout.write(f"\n{responsive_hint('summary_action_hint')}\n")
            sys.stdout.flush()

            key = read_key()
            if key in ("UP", "k", "K"):
                focus = 2 if focus <= 0 else focus - 1
            elif key in ("DOWN", "j", "J"):
                focus = 0 if focus >= 2 else focus + 1
            elif key in ("ENTER", "SPACE"):
                if focus == 0:
                    run_optional_apps_menu_loop()
                elif focus == 1:
                    star_url = REPO_URL.removesuffix(".git")
                    if shutil.which("xdg-open"):
                        timed_run(["xdg-open", star_url], 5, check=False)
                    print(msg("msg_star_opened", star_url))
                    time.sleep(1.2)
                elif focus == 2:
                    break
            elif key in ("0", "q", "Q", "ESC", "EXIT"):
                break
    finally:
        _drain_pending(fd, debounce=True)
        stack.close()
        sys.stdout.write(Colors.CURSOR_SHOW)
        sys.stdout.flush()

def deploy_selected_configs(
    do_backup: bool = False,
    items_to_deploy: Optional[List[str]] = None,
    preserved_log: Optional[List[str]] = None,
    carry_policy: Optional[CarryPolicy] = None,
) -> List[str]:
    """Deploy selected dotfile items with optional backup and template rendering.

    ``carry_policy`` (#139) forwards the ownership-carry directive; None keeps
    the plain template-swap semantics (rollback/force paths).
    """
    if isinstance(items_to_deploy, str):
        items_to_deploy = [items_to_deploy]
    if items_to_deploy is None:
        items_to_deploy = discover_config_items()
    if preserved_log is None:
        preserved_log = []

    if do_backup:
        from nyxuri.state.backup import backup_configs
        backup_configs(note="auto_snapshot_before_deploy", interactive=False)

    print(msg("copying_configs"))
    failed_items = _phase_atomic_deployment(
        items_to_deploy, keep_preserved=True, preserved_log=preserved_log, carry_policy=carry_policy
    )
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        return failed_items
    for item in items_to_deploy:
        excluded = set(carry_policy.carried.get(item, {})) if carry_policy else set()
        _phase_render_templates(only_app=item, exclude=excluded)
        prepare_screenshot_directory(only_app=item, exclude=excluded)
    _phase_post_install_services()
    print(msg("copy_done"))
    return []

def enable_wallpapers_unit() -> Optional[bool]:
    """Best-effort ``on wallpapers`` for deploy flows: True / False / None
    (skipped). The pack itself is user-domain (install-pack script); only
    the blueprint fallback goes through the transaction."""
    try:
        from nyxuri.kernel import transaction
        steps = transaction.unit_on("wallpapers")
        return bool(steps) and all(s.ok for s in steps)
    except Exception as exc:
        log_msg("WARN", f"wallpapers unit enable failed: {exc}")
        return False


def enable_theme_unit() -> Optional[bool]:
    """Best-effort ``on theme`` for deploy flows: the shared template pool is
    load-bearing for both shells' gtk/niri/palette renders (KM4/P5 neutral
    pool). No-clobber merge — user-edited templates survive redeploys."""
    try:
        from nyxuri.kernel import transaction
        steps = transaction.unit_on("theme")
        return bool(steps) and all(s.ok for s in steps)
    except Exception as exc:
        log_msg("WARN", f"theme unit enable failed: {exc}")
        return False


def _carry_baselines(items: List[str]) -> Dict[str, Optional[Dict[str, str]]]:
    """Ledger baselines for ``nyxuri test``'s update-grade carry (lazy kernel read)."""
    try:
        from nyxuri.kernel import transaction
        return transaction.carry_baselines(items)
    except Exception:
        return {}


def test_deploy() -> bool:
    """Developer test command: fast idempotent re-deploy in current environment."""
    print(msg("test_start"))

    preserved_log: List[str] = []
    items = discover_config_items()
    failed_items = _phase_atomic_deployment(
        items, keep_preserved=True, preserved_log=preserved_log, test_mode=True,
        # `nyxuri test` means "make it match the repo" (hardware-neutrality
        # scrub included): adoption semantics, not update-grade carry.
        carry_policy=CarryPolicy(baselines=_carry_baselines(items), unknown=False),
    )
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        render_completion_screen(mode="test", chosen_items=items, preserved_lines=preserved_log, failed_items=failed_items)
        return False
    _phase_render_templates()
    prepare_screenshot_directory()
    wallpaper_ok = enable_wallpapers_unit()
    enable_theme_unit()
    render_completion_screen(
        mode="test",
        chosen_items=items,
        preserved_lines=preserved_log,
        wallpaper_ok=wallpaper_ok,
    )
    return True
