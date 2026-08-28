"""Deploy orchestrator — config discovery, atomic-deploy phase, post-install
services, completion screen, fisher uninstall, and the deploy/test entry points.

Coordinates the deploy/ siblings: atomic (swap+preserve), templates (render),
assets (wallpapers), hardware (NVIDIA patch), manifest (app discovery), preset
(active variant). Modules/state/deps are lazy-imported to avoid cycles.
"""

import shutil
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from typing import List, Optional

from nyxniri.constants import Colors, MAIN_WM, REPO_URL, THEME_ENGINE
from nyxniri.core import get_env, log_msg, timed_run
from nyxniri.i18n import msg
from nyxniri.tui import read_key, responsive_hint, show_logo, raw_input_mode, _drain_pending

from nyxniri.deploy.atomic import (
    atomic_replace_item,
)
from nyxniri.deploy.assets import WallpaperDeployResult, deploy_wallpapers, wallpapers_pack_present
from nyxniri.deploy.hardware import _phase_hardware_patches
from nyxniri.deploy.manifest import discover_deployable_apps, load_manifest
from nyxniri.deploy.preset import (
    InvalidActivePresetError,
    read_active_preset,
    resolve_preset_src,
    write_active_preset,
)
from nyxniri.deploy.templates import _phase_render_templates

_CONFIG_ITEMS_CACHE: List[str] = []

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

def _phase_atomic_deployment(
    items_to_deploy: List[str],
    keep_preserved: bool = True,
    preserved_log: Optional[List[str]] = None,
    test_mode: bool = False,
) -> List[str]:
    """Execute atomic copy for selected configuration units.

    Per-app manifest drives: the preserve list (files kept across deploys,
    e.g. niri/monitor.kdl), and the chmod globs (executable scripts). The
    Dunder __custom__ walk inside atomic_replace_item is untouched.
    """
    env = get_env()
    config_dir = env.config_dir
    config_dir.mkdir(parents=True, exist_ok=True)

    failed_items: List[str] = []
    for item in items_to_deploy:
        dest = config_dir / item

        # Resolve which source tree to deploy: default config, an official
        # preset, or a user preset — based on the app's active state file.
        try:
            active = read_active_preset(item)
        except InvalidActivePresetError:
            print(msg("preset_warn_invalid_active", item))
            log_msg("WARN", f"Invalid active preset state for {item}; dest frozen, skipped")
            continue
        result = resolve_preset_src(item, active, dest)
        for w in result.warnings:
            print(w)
        if result.src is None:
            # Preset not found anywhere — freeze dest, do not fall back to
            # default (would silently wipe the user's config). §3.2
            log_msg("WARN", f"Preset '{active}' for {item} not found; dest frozen, skipped")
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

        # Manifest always loaded from the app root (not the preset dir):
        # preserve/chmod describe the app, independent of which variant ships.
        manifest = load_manifest(env.configs_src / item)
        preserve = manifest.preserve if keep_preserved else None

        if not atomic_replace_item(src, dest, preserved_log=preserved_log, test_mode=test_mode, preserve=preserve):
            failed_items.append(item)
            print(msg("log_deploy_config_failed", item), file=sys.stderr)
            continue

        # Executable permissions — manifest chmod globs, relative to app dir
        for pattern in manifest.chmod:
            for p in dest.glob(pattern):
                if p.is_file():
                    try:
                        p.chmod(0o755)
                    except OSError:
                        pass

        print(msg("log_deploy_config_item", item))
        log_msg("INFO", f"Deployed config ~/.config/{item}")

    # Initial EyeCare symlink (niri one-off, not manifest-driven)
    effects_normal = config_dir / MAIN_WM / "effects_normal.kdl"
    effects_sym = config_dir / MAIN_WM / "effects.kdl"
    if effects_normal.is_file() and not effects_sym.exists():
        try:
            effects_sym.symlink_to(effects_normal)
        except Exception:
            pass

    return failed_items

def _phase_post_install_services() -> None:
    """Run post-deployment hooks (theme-sync, mpvpaper enable, Fisher plugins)."""
    env = get_env()
    config_dir = env.config_dir

    sync_script = config_dir / THEME_ENGINE / "theme-sync.sh"
    if sync_script.is_file():
        sync_script.chmod(0o755)
        timed_run(["bash", str(sync_script)], 30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        print(msg("log_gtk_theme_init"))

    if shutil.which(THEME_ENGINE):
        from nyxniri.modules.gtktheme import gtktheme_trigger_render
        gtktheme_trigger_render()
        print(msg("log_enable_mpvpaper"))
        timed_run([THEME_ENGINE, "msg", "plugins", "enable", f"{THEME_ENGINE}/mpvpaper"], 15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    if shutil.which("fish"):
        from nyxniri.modules.fisher import fisher_install
        fisher_install()

def render_completion_screen(
    mode: str = "install",
    chosen_items: Optional[List[str]] = None,
    preserved_lines: Optional[List[str]] = None,
    wallpaper_result: Optional[WallpaperDeployResult] = None,
    do_fcitx: bool = False,
    do_greeter: bool = False,
    failed_items: Optional[List[str]] = None,
) -> None:
    """Render minimal, zero-entropy TUI Completion Screen according to TUI Design Charter."""
    if chosen_items is None:
        chosen_items = discover_config_items()
    if preserved_lines is None:
        preserved_lines = []
    if failed_items is None:
        failed_items = []

    from nyxniri.modules.fcitx import fcitx5_installed, fcitx_enabled
    from nyxniri.deps import get_missing_deps

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
            if wallpaper_result is not None:
                wallpaper_key, wallpaper_color, wallpaper_icon = wallpaper_result.status_line(wallpapers_pack_present())
            elif wallpapers_pack_present():
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_existing", Colors.BOLD_GREEN, "[✓]"
            else:
                wallpaper_key, wallpaper_color, wallpaper_icon = "summary_item_wallpapers_skip", Colors.BOLD_YELLOW, "[!]"
            sys.stdout.write(f"    {wallpaper_color}{wallpaper_icon}{Colors.RESET} {msg(wallpaper_key)}\n")

        if mode in ("full", "update", "test") and fcitx5_installed():
            if do_fcitx or fcitx_enabled():
                sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_fcitx_ok')}\n")
            else:
                sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_fcitx_skip')}\n")

        if mode == "full":
            if not missing_deps:
                sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_deps_ok')}\n")
            else:
                sys.stdout.write(f"    {Colors.BOLD_YELLOW}[!]{Colors.RESET} {msg('summary_item_deps_skip')}\n")

        if do_greeter:
            sys.stdout.write(f"    {Colors.BOLD_GREEN}[✓]{Colors.RESET} {msg('summary_item_greeter_ok')}\n")

        if preserved_lines:
            sys.stdout.write(f"\n  {Colors.BOLD_WHITE}{msg('summary_section_preserved')}{Colors.RESET}\n")
            for pline in sorted(set(preserved_lines)):
                sys.stdout.write(f"    {pline}\n")

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
    from nyxniri.deps import run_optional_apps_menu_loop
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
            from nyxniri.tui import render_menu_item
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
) -> List[str]:
    """Deploy selected dotfile items with optional backup, template rendering, and hardware patches."""
    if items_to_deploy is None:
        items_to_deploy = discover_config_items()
    if preserved_log is None:
        preserved_log = []

    if do_backup:
        from nyxniri.state.backup import backup_configs
        backup_configs(note="auto_snapshot_before_deploy", interactive=False)

    print(msg("copying_configs"))
    failed_items = _phase_atomic_deployment(items_to_deploy, keep_preserved=True, preserved_log=preserved_log)
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        return failed_items
    _phase_render_templates()
    _phase_hardware_patches()
    _phase_post_install_services()
    print(msg("copy_done"))
    return []

def test_deploy() -> bool:
    """Developer test command: fast idempotent re-deploy in current environment."""
    print(msg("test_start"))

    preserved_log: List[str] = []
    items = discover_config_items()
    failed_items = _phase_atomic_deployment(items, keep_preserved=True, preserved_log=preserved_log, test_mode=True)
    if failed_items:
        print(msg("deploy_failed", ", ".join(failed_items)), file=sys.stderr)
        render_completion_screen(mode="test", chosen_items=items, preserved_lines=preserved_log, failed_items=failed_items)
        return False
    _phase_render_templates()
    _phase_hardware_patches()
    wallpaper_result = deploy_wallpapers(do_download=False)
    render_completion_screen(
        mode="test",
        chosen_items=items,
        preserved_lines=preserved_log,
        wallpaper_result=wallpaper_result,
    )
    return True
