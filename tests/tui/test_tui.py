"""T2 Textual TUI: isolation contract + pilot tests for the M1 surface."""

import ast
import asyncio
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE = REPO_ROOT / "nyxuri"
TUI = ENGINE / "tui"


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module


class TestTextualIsolation(unittest.TestCase):
    def test_textual_only_under_nyxuri_tui(self):
        leaks = []
        for path in ENGINE.rglob("*.py"):
            if path.is_relative_to(TUI) or "_vendor" in path.parts:
                continue
            for name in _imports(path):
                if name.split(".")[0] in ("textual", "rich") or name.startswith("nyxuri.tui"):
                    leaks.append(f"{path.relative_to(REPO_ROOT)}: {name}")
        self.assertEqual(leaks, [])

    def test_engine_imports_without_site_packages(self):
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]);"
            "import nyxuri.cli, nyxuri.deploy.engine;"
            "assert 'textual' not in sys.modules"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-c", code, str(REPO_ROOT)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class TestRecordColumn(unittest.TestCase):
    def test_column_matches_textual_centering(self):
        from nyxuri.tui.record import column

        self.assertEqual(column(100), (14, 72))
        self.assertEqual(column(75), (1, 72))
        self.assertEqual(column(50), (1, 48))

    def test_record_lines_share_the_left_edge(self):
        from nyxuri.tui.record import Record

        out = io.StringIO()
        with patch("shutil.get_terminal_size", return_value=__import__("os").terminal_size((100, 40))):
            rec = Record(out)
            rec.step("插件工坊")
            rec.result("ok", "done")
        lines = [l for l in out.getvalue().splitlines() if l]
        self.assertEqual(lines[0], " " * 14 + "● 插件工坊")
        self.assertTrue(lines[1].startswith(" " * 16 + "└ "))


class TestPilot(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def _run(self, app, keys, size=(100, 30)):
        async def drive():
            async with app.run_test(size=size) as pilot:
                await pilot.pause()
                for key in keys:
                    await pilot.press(key)
                    await pilot.pause()
            return app.return_value

        return asyncio.run(drive())

    def test_workshop_column_is_centered(self):
        from nyxuri.tui.workshop import Workshop

        async def drive():
            app = Workshop()
            async with app.run_test(size=(100, 30)) as pilot:
                await pilot.pause()
                return app.query_one("#column").region

        region = asyncio.run(drive())
        self.assertEqual((region.x, region.width), (14, 72))

    def test_wordmark_is_centered_and_redrawn_with_the_area(self):
        from nyxuri.tui.app import WORDMARK
        from nyxuri.tui.workshop import Workshop

        art_width = len(WORDMARK.splitlines()[0])

        async def drive(size):
            app = Workshop()
            async with app.run_test(size=size) as pilot:
                await pilot.pause()
                art = app.query_one("#wordmark-art")
                return art.display, art.content_region, app.query_one("#column").region

        shown, art, col = asyncio.run(drive((100, 40)))
        self.assertTrue(shown)
        pad_left = art.x - col.x + (art.width - art_width) // 2
        self.assertLessEqual(abs(pad_left - (col.width - art_width - pad_left)), 1)
        for size in ((56, 40), (100, 18)):
            self.assertFalse(asyncio.run(drive(size))[0], size)

    def test_workshop_switch_keys(self):
        from nyxuri.deploy import catalog
        from nyxuri.tui.workshop import Workshop

        ids = sorted(catalog.plugin_ids())
        self.assertEqual(self._run(Workshop(), ["j", "o"]), ("on", ids[1]))
        self.assertEqual(self._run(Workshop(), ["f"]), ("off", ids[0]))
        self.assertEqual(self._run(Workshop(), ["enter"]), ("on", ids[0]))

    def test_escape_and_ctrl_c(self):
        from nyxuri.tui.app import CANCEL
        from nyxuri.tui.workshop import Workshop

        self.assertIsNone(self._run(Workshop(), ["escape"]))
        self.assertEqual(self._run(Workshop(), ["ctrl+c"]), CANCEL)

    def test_destructive_confirm_defaults_to_cancel(self):
        from nyxuri.tui.app import Confirm

        self.assertEqual(self._run(Confirm(["body"], ["取消", "停用"]), ["enter"]), 0)
        self.assertEqual(self._run(Confirm(["body"], ["取消", "停用"]), ["2"]), 1)

    def test_switch_off_cancel_never_touches_engine(self):
        from nyxuri.tui import flow
        from nyxuri.tui.record import Record

        out = io.StringIO()
        with patch.object(flow, "_confirm", return_value=0), \
                patch("nyxuri.deploy.engine.plugin_off") as off:
            self.assertTrue(flow._switch_off(Record(out), "kitty"))
        off.assert_not_called()

    def test_switch_on_reports_engine_steps(self):
        from nyxuri.deploy.engine import Step
        from nyxuri.tui import flow
        from nyxuri.tui.record import Record

        out = io.StringIO()
        with patch("nyxuri.deploy.engine.missing_packages", return_value=[]), \
                patch("nyxuri.deploy.engine.plugin_on", return_value=[Step("kitty", True, "enabled")]) as on:
            self.assertTrue(flow._switch_on(Record(out), "kitty"))
        self.assertEqual(on.call_args.args, ("kitty",))
        self.assertIn("install_packages", on.call_args.kwargs)
        self.assertIn("✓", out.getvalue())


if __name__ == "__main__":
    unittest.main()
