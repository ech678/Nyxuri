"""
NyxNiri Wallpaper Picker Scanner Engine
Recursive directory traversal, asynchronous thumbnail generation, and active wallpaper detection.

Thumbnails live on disk; the UI mounts each one lazily as a CSS
background-image (window.py). Note GTK3 keeps the decoded bitmap of every
painted background cached until process exit — scrolling away does NOT
release it — so runtime memory grows with the thumbs actually viewed,
not with library size.
"""

import os
import sys
import hashlib
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
import gi
gi.require_version("GLib", "2.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GLib, GdkPixbuf

from .config import (
    STATIC_EXTENSIONS, VIDEO_EXTENSIONS, ALL_SUPPORTED_EXTENSIONS,
    CACHE_DIR, get_wallpaper_search_roots
)


class WallpaperItem:
    """Represents a single static or live wallpaper item."""

    def __init__(self, path: str, category: str = "Wallpapers"):
        self.path = os.path.realpath(path)
        self.filename = os.path.basename(path)
        self.ext = os.path.splitext(self.filename)[1].lower()
        self.is_video = self.ext in VIDEO_EXTENSIONS
        self.title = os.path.splitext(self.filename)[0].replace("_", " ").replace("-", " ").strip()
        self.category = category
        # Lowercase once; the filter runs against every item per keystroke
        self.search_key = f"{self.title}\n{self.filename}".lower()

        try:
            stat = os.stat(self.path)
            self.mtime = stat.st_mtime
            self.size = stat.st_size
        except Exception:
            self.mtime = 0.0
            self.size = 0

        # Unique cache key derived from path + mtime + size
        raw_key = f"{self.path}:{self.mtime}:{self.size}".encode("utf-8")
        self.hash_id = hashlib.md5(raw_key).hexdigest()
        self.thumb_path = os.path.join(CACHE_DIR, f"{self.hash_id}.jpg")
        self.is_loading = False


class WallpaperScanner:
    """Manages wallpaper discovery, category grouping, and on-disk thumbnail generation."""

    def __init__(self, on_thumb_ready_cb=None):
        self.on_thumb_ready_cb = on_thumb_ready_cb
        self.items = []
        self.categories = ["All", "Static", "Live"]
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="wp_thumb")
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._thumb_queue = []
        self._thumb_queue_pos = 0

    def scan(self) -> list:
        """Scan all resolved search roots and subdirectories."""
        roots = get_wallpaper_search_roots()
        seen_paths = set()
        discovered_items = []
        custom_subfolders = set()

        for root in roots:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip hidden directories
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]

                rel_dir = os.path.relpath(dirpath, root)
                if rel_dir == ".":
                    cat_name = os.path.basename(root)
                else:
                    cat_name = os.path.basename(dirpath)

                for fname in filenames:
                    if fname.startswith("."):
                        continue
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in ALL_SUPPORTED_EXTENSIONS:
                        full_path = os.path.join(dirpath, fname)
                        real_path = os.path.realpath(full_path)
                        if real_path not in seen_paths:
                            seen_paths.add(real_path)
                            item = WallpaperItem(real_path, category=cat_name)
                            discovered_items.append(item)
                            # Ignore format/system folder names that map to primary tabs
                            if cat_name.lower() not in (
                                "all", "static", "live", "wallpapers", "pictures", "图片",
                                "video", "videos", "mpvpaper", "livewallpaper", "livewallpapers"
                            ):
                                custom_subfolders.add(cat_name)

        # Sort naturally by title
        discovered_items.sort(key=lambda x: x.title.lower())
        self.items = discovered_items

        # Build categories list: primary tabs + actual custom user subfolders
        sorted_subfolders = sorted(list(custom_subfolders), key=lambda x: x.lower())
        self.categories = ["All", "Static", "Live"] + sorted_subfolders

        for it in self.items[:6]:
            if os.path.isfile(it.thumb_path):
                self._thumb_ready(it)
            else:
                self._submit_thumb_job(it)

        return self.items

    def set_thumb_queue(self, items: list):
        """Set the display-order queue that drives incremental thumbnail loading."""
        self._thumb_queue = list(items)
        self._thumb_queue_pos = 0

    def has_pending_thumbs(self) -> bool:
        """True while the display-order queue still has unloaded items."""
        return self._thumb_queue_pos < len(self._thumb_queue)

    def load_next_thumb_batch(self, count: int = 24):
        """Load the next queue batch: cached thumbs notify now, the rest get jobs."""
        batch = self._thumb_queue[self._thumb_queue_pos:self._thumb_queue_pos + count]
        self._thumb_queue_pos += len(batch)
        for item in batch:
            if os.path.isfile(item.thumb_path):
                self._thumb_ready(item)
            elif not item.is_loading:
                self._submit_thumb_job(item)

    def _submit_thumb_job(self, item: WallpaperItem):
        """Queue thumbnail generation, marking in-flight at submit time.

        The guard must live here, not inside the worker: between submit and
        worker pickup there is a window where is_loading would still read
        False, letting the pre-warm in scan() and the first queue batch
        double-submit the same item (two threads racing savev onto one
        file, ffmpeg running twice).
        """
        item.is_loading = True
        self.executor.submit(self._generate_thumbnail_worker, item)

    def _thumb_ready(self, item: WallpaperItem):
        """Notify the UI (on main thread) that a thumbnail file is available."""
        if self.on_thumb_ready_cb:
            self.on_thumb_ready_cb(item)

    def _generate_thumbnail_worker(self, item: WallpaperItem):
        try:
            if not os.path.isfile(item.thumb_path):
                if item.is_video:
                    tmp_thumb = f"{item.thumb_path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}.jpg"
                    cmd = [
                        "ffmpeg", "-y", "-ss", "00:00:01", "-i", item.path,
                        "-vframes", "1", "-vf", "scale=480:-2", tmp_thumb
                    ]
                    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
                    if res.returncode != 0 or not os.path.isfile(tmp_thumb):
                        # Fallback for very short videos
                        cmd = [
                            "ffmpeg", "-y", "-ss", "00:00:00.1", "-i", item.path,
                            "-vframes", "1", "-vf", "scale=480:-2", tmp_thumb
                        ]
                        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)

                    if res.returncode == 0 and os.path.isfile(tmp_thumb):
                        os.replace(tmp_thumb, item.thumb_path)
                    elif os.path.isfile(tmp_thumb):
                        os.remove(tmp_thumb)
                else:
                    try:
                        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(item.path, 480, 270, True)
                        # JPEG 不支持 alpha 通道（glycin 编码器会拒绝 Rgba8），
                        # 带透明的图先合成到不透明黑底上再存
                        if pix.get_has_alpha():
                            flat = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8,
                                                        pix.get_width(), pix.get_height())
                            flat.fill(0x000000)
                            pix.composite(flat, 0, 0, flat.get_width(), flat.get_height(),
                                          0, 0, 1, 1, GdkPixbuf.InterpType.BILINEAR, 255)
                            pix = flat
                        pix.savev(item.thumb_path, "jpeg", ["quality"], ["85"])
                    except Exception as e:
                        print(f"Thumbnail generation error on {item.filename}: {e}", file=sys.stderr)

            if os.path.isfile(item.thumb_path):
                GLib.idle_add(self._thumb_ready, item)
        except Exception as e:
            print(f"Thumbnail generation error on {item.filename}: {e}", file=sys.stderr)
        finally:
            item.is_loading = False

    def get_current_wallpaper(self) -> str:
        """Query Noctalia IPC for the currently active wallpaper path."""
        try:
            res = subprocess.run(["noctalia", "msg", "wallpaper-get"], capture_output=True, text=True, timeout=0.3)
            wp = res.stdout.strip()
            if wp and os.path.isfile(wp):
                return os.path.realpath(wp)
        except Exception:
            pass
        return ""
