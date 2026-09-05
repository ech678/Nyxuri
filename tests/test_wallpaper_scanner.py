"""Contract tests for the wallpaper picker scanner's thumbnail job queue.

Pins the submit-time in-flight guard: is_loading must flip True at the
submit site, not inside the worker — otherwise the scan() pre-warm and
the first display-order batch race and double-submit the same item
(two threads writing one thumbnail file, ffmpeg running twice).
Also pins the worker's disk-cache entry guard and the submit call shape.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.utils import TempEnv

_SCRIPTS = Path(__file__).resolve().parent.parent / "configs" / "niri" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

try:
    from wallpaper_picker import scanner as scanner_mod
except Exception:
    scanner_mod = None


@unittest.skipUnless(scanner_mod is not None, "gi/GdkPixbuf not available")
class TestThumbSubmitContract(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__)
        self._tmp = tempfile.TemporaryDirectory(dir=self._ctx.env.home)
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "Wallpapers"
        self.root.mkdir(parents=True)
        self.cache = self.tmp / "cache"
        patcher = patch.object(scanner_mod, "CACHE_DIR", str(self.cache))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _scanner(self):
        scn = scanner_mod.WallpaperScanner(on_thumb_ready_cb=None)
        self.addCleanup(scn.executor.shutdown, wait=False)
        return scn

    def test_submit_marks_loading_before_queueing(self):
        scn = self._scanner()
        (self.root / "a.jpg").write_bytes(b"")
        item = scanner_mod.WallpaperItem(str(self.root / "a.jpg"))
        seen = {}

        def record_submit(fn, *args):
            seen["loading_at_submit"] = item.is_loading
            seen["fn"] = fn
            seen["args"] = args

        with patch.object(scn.executor, "submit", side_effect=record_submit):
            scn._submit_thumb_job(item)

        self.assertTrue(seen["loading_at_submit"],
                        "is_loading must be True by the time the job is queued")
        self.assertEqual(seen["fn"], scn._generate_thumbnail_worker)
        self.assertEqual(seen["args"], (item,))

    def test_scan_prewarm_and_first_batch_submit_each_item_once(self):
        scn = self._scanner()
        for i in range(8):
            (self.root / f"w{i}.jpg").write_bytes(b"")
        with patch.object(scanner_mod, "get_wallpaper_search_roots",
                          return_value=[str(self.root)]), \
             patch.object(scn.executor, "submit") as mock_submit:
            items = scn.scan()
            scn.set_thumb_queue(items)
            scn.load_next_thumb_batch(24)

        submitted = [call.args[1] for call in mock_submit.call_args_list]
        self.assertEqual(len(submitted), 8)
        self.assertEqual(len({id(it) for it in submitted}), 8,
                         "pre-warm and first batch must not double-submit an item")

    def test_worker_skips_generation_when_thumb_cached(self):
        scn = self._scanner()
        (self.root / "a.jpg").write_bytes(b"")
        item = scanner_mod.WallpaperItem(str(self.root / "a.jpg"))
        self.cache.mkdir(parents=True, exist_ok=True)
        Path(item.thumb_path).write_bytes(b"cached")

        with patch.object(scanner_mod.GdkPixbuf.Pixbuf, "new_from_file_at_scale") as mock_pix, \
             patch.object(scanner_mod.GLib, "idle_add") as mock_idle:
            scn._generate_thumbnail_worker(item)

        mock_pix.assert_not_called()
        mock_idle.assert_called_once()
        self.assertFalse(item.is_loading)

    def test_video_worker_skips_ffmpeg_when_thumb_cached(self):
        scn = self._scanner()
        (self.root / "v.mp4").write_bytes(b"")
        item = scanner_mod.WallpaperItem(str(self.root / "v.mp4"))
        self.assertTrue(item.is_video)
        self.cache.mkdir(parents=True, exist_ok=True)
        Path(item.thumb_path).write_bytes(b"cached")

        with patch.object(scanner_mod.subprocess, "run") as mock_run:
            scn._generate_thumbnail_worker(item)

        mock_run.assert_not_called()
        self.assertFalse(item.is_loading)

    def test_search_key_prelowered_once(self):
        (self.root / "Aurora_Nights.jpg").write_bytes(b"")
        item = scanner_mod.WallpaperItem(str(self.root / "Aurora_Nights.jpg"))
        self.assertEqual(item.search_key, f"{item.title}\n{item.filename}".lower())
        self.assertEqual(item.search_key, item.search_key.lower())

    def test_worker_flattens_alpha_image_before_jpeg_save(self):
        scn = self._scanner()
        (self.root / "alpha.png").write_bytes(b"")
        item = scanner_mod.WallpaperItem(str(self.root / "alpha.png"))

        mock_pix = MagicMock()
        mock_pix.get_has_alpha.return_value = True
        mock_pix.get_width.return_value = 480
        mock_pix.get_height.return_value = 270

        mock_flat = MagicMock()
        mock_flat.get_width.return_value = 480
        mock_flat.get_height.return_value = 270

        with patch.object(scanner_mod.GdkPixbuf.Pixbuf, "new_from_file_at_scale", return_value=mock_pix), \
             patch.object(scanner_mod.GdkPixbuf.Pixbuf, "new", return_value=mock_flat) as mock_new, \
             patch.object(scanner_mod.GLib, "idle_add"):
            scn._generate_thumbnail_worker(item)

        mock_new.assert_called_once_with(
            scanner_mod.GdkPixbuf.Colorspace.RGB, False, 8, 480, 270
        )
        mock_flat.fill.assert_called_once_with(0x000000)
        mock_pix.composite.assert_called_once_with(
            mock_flat, 0, 0, 480, 270, 0, 0, 1, 1,
            scanner_mod.GdkPixbuf.InterpType.BILINEAR, 255
        )
        mock_flat.savev.assert_called_once_with(
            item.thumb_path, "jpeg", ["quality"], ["85"]
        )
        mock_pix.savev.assert_not_called()


if __name__ == "__main__":
    unittest.main()
