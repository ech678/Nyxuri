"""Wallpaper assets — offline fallback + optional external pack download.

``deploy_wallpapers`` is a no-clobber sync: existing user files are never
overwritten, only missing ones are added. ``WallpaperDeployResult`` exposes
the outcome so the completion screen can render the right status line.
"""

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from nyxniri.constants import Colors, WALLPAPER_MIRRORS
from nyxniri.core import get_env, get_pics_dir, log_msg, register_temp_path
from nyxniri.i18n import msg
from nyxniri.network import git_clone_timeout


@dataclass(frozen=True)
class WallpaperDeployResult:
    """Observable outcome of an optional wallpaper pack deployment."""

    download_attempted: bool
    downloaded: bool
    pack_present: bool
    fallback_synced: bool

    @property
    def download_failed(self) -> bool:
        return self.download_attempted and not self.downloaded

    def status_line(self, pack_present_now: bool) -> Tuple[str, str, str]:
        """(i18n key, color, icon) for the completion screen's wallpaper row.

        ``pack_present_now`` is the live disk check (``wallpapers_pack_present()``)
        passed by the caller: the "existing pack" branch must fall back to a fresh
        on-disk probe when this result is silent about it (e.g. result is None or
        a no-download install). Keeps the 8-branch status enum with the data.
        """
        if self.downloaded:
            return "summary_item_wallpapers_downloaded", Colors.BOLD_GREEN, "[✓]"
        if self.download_failed and self.pack_present:
            return "summary_item_wallpapers_refresh_failed", Colors.BOLD_YELLOW, "[!]"
        if self.download_failed and self.fallback_synced:
            return "summary_item_wallpapers_failed_fallback", Colors.BOLD_YELLOW, "[!]"
        if self.download_failed:
            return "summary_item_wallpapers_failed", Colors.BOLD_RED, "[✗]"
        if self.pack_present or pack_present_now:
            return "summary_item_wallpapers_existing", Colors.BOLD_GREEN, "[✓]"
        if self.fallback_synced:
            return "summary_item_wallpapers_fallback", Colors.BOLD_YELLOW, "[!]"
        return "summary_item_wallpapers_skip", Colors.BOLD_YELLOW, "[!]"


def _wallpaper_pack_present_at(root: Path) -> bool:
    """Validate a wallpaper pack by requiring at least one deployed video file."""
    video_dir = root / "video"
    try:
        return video_dir.is_dir() and any(path.is_file() for path in video_dir.rglob("*"))
    except OSError:
        return False


def wallpapers_pack_present() -> bool:
    """Check whether the external wallpaper pack is deployed."""
    return _wallpaper_pack_present_at(get_pics_dir() / "Wallpapers")


def deploy_wallpapers(do_download: bool = False) -> WallpaperDeployResult:
    """Deploy wallpaper assets (offline fallback + optional full external pack)."""
    wp_dest = get_pics_dir() / "Wallpapers"
    wp_dest.mkdir(parents=True, exist_ok=True)
    env = get_env()
    downloaded = False
    fallback_synced = False

    if do_download:
        print(msg("msg_downloading_wallpapers"))
        if not shutil.which("git"):
            failure_key = "msg_wallpapers_refresh_failed" if wallpapers_pack_present() else "msg_wallpapers_download_failed"
            print(msg(failure_key))
            log_msg("WARN", "Wallpaper pack download skipped: git not installed")
        else:
            tmp_clone = Path(tempfile.mkdtemp())
            register_temp_path(tmp_clone)
            success = False
            for idx, (tag, url) in enumerate(WALLPAPER_MIRRORS, start=1):
                print(msg("msg_downloading_wallpapers_node", f"{idx}/{len(WALLPAPER_MIRRORS)}", tag))
                if git_clone_timeout(url, tmp_clone, cancellable=sys.stdin.isatty()):
                    if _wallpaper_pack_present_at(tmp_clone):
                        success = True
                        break
                    log_msg("WARN", f"Wallpaper mirror [{tag}] returned an incomplete pack")
                shutil.rmtree(tmp_clone, ignore_errors=True)

            if success:
                shutil.rmtree(tmp_clone / ".git", ignore_errors=True)
                (tmp_clone / "preview.webp").unlink(missing_ok=True)
                (tmp_clone / "README.md").unlink(missing_ok=True)
                # Copy into wp_dest (no-clobber: never overwrite existing files)
                for item in tmp_clone.iterdir():
                    target = wp_dest / item.name
                    if target.exists():
                        continue
                    if item.is_dir():
                        shutil.copytree(item, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target)
                downloaded = True
                print(msg("msg_wallpapers_download_success"))
                log_msg("INFO", f"Wallpaper pack deployed to {wp_dest}")
                shutil.rmtree(tmp_clone, ignore_errors=True)
            else:
                failure_key = "msg_wallpapers_refresh_failed" if wallpapers_pack_present() else "msg_wallpapers_download_failed"
                print(msg(failure_key))
                log_msg("WARN", "Wallpaper pack download failed on all mirrors")

    # Incremental fallback sync
    fallback_src = env.assets_src / "wallpapers"
    if fallback_src.is_dir():
        for f in fallback_src.iterdir():
            target = wp_dest / f.name
            if not target.exists():
                shutil.copy2(f, target)
        fallback_synced = True
        print(msg("log_sync_wallpapers", str(wp_dest)))

    return WallpaperDeployResult(
        download_attempted=do_download,
        downloaded=downloaded,
        pack_present=wallpapers_pack_present(),
        fallback_synced=fallback_synced,
    )
