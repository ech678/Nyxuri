"""B8.6 bar runtime probe gate.

The string-assertion suites cannot catch a NaN layout chain, a compiled-empty
widget or a Type/Reference storm. This test drives scripts/dev/probe-bar.sh,
which loads BarContent in an isolated shell and reports every active Loader
status plus the evaluated lane geometry for cornerStyle 1/3/4/5.

No Wayland compositor -> explicit skip (the probe exits 2). Weston, when
installed, runs headless; otherwise the probe uses the current session with a
private HOME/XDG tree and no windows.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

SHELL = Path(__file__).resolve().parents[2] / "shell"
PROBE = SHELL / "scripts" / "dev" / "probe-bar.sh"


class BarRuntimeProbeTest(unittest.TestCase):

    def test_probe_bar_reports_ready_layout_for_all_corner_styles(self):
        result = subprocess.run(
            ["bash", str(PROBE), "--json"],
            capture_output=True, text=True, timeout=240,
        )
        if result.returncode == 2:
            self.skipTest(result.stderr.strip() or "no Wayland compositor")
        self.assertEqual(
            result.returncode, 0,
            (result.stderr[-4000:] + "\n" + result.stdout[-4000:]),
        )
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"], report["logErrors"])
        self.assertEqual(report["osd"]["islandState"], "osd",
                         "the island OSD producer/provider chain did not engage")
        self.assertTrue(report["islandOff"]["ok"],
                        "islandEnabled=false did not remove the island from the middle lane")
        self.assertEqual(report["keyboardOsd"]["islandState"], "osd",
                         "caps/num lock changes did not reach the island OSD")
        keyboard = report["styles"][0].get("keyboard") or {}
        leds = sorted(Path("/sys/class/leds").glob("*::capslock")) + sorted(
            Path("/sys/class/leds").glob("*::numlock"))
        if leds:
            self.assertTrue(keyboard.get("available"),
                            "KeyboardLockService should be ready when LED class devices exist")
            caps = any((led / "brightness").read_text().strip() == "1"
                       for led in Path("/sys/class/leds").glob("*::capslock"))
            num = any((led / "brightness").read_text().strip() == "1"
                      for led in Path("/sys/class/leds").glob("*::numlock"))
            self.assertEqual(keyboard.get("caps"), caps)
            self.assertEqual(keyboard.get("num"), num)
        self.assertEqual(len(report["styles"]), 4)
        self.assertEqual([entry["cornerStyle"] for entry in report["styles"]], [1, 3, 4, 5])
        for entry in report["styles"]:
            with self.subTest(cornerStyle=entry["cornerStyle"]):
                self.assertTrue(entry["ready"])
                geometry = entry["geometry"]
                self.assertGreater(geometry["width"], 0)
                self.assertGreater(geometry["height"], 0)
                self.assertGreater(geometry["centerWidth"], 0)
                self.assertLessEqual(
                    abs(geometry["centerX"] - (geometry["width"] - geometry["centerWidth"]) / 2),
                    1.0, "middle lane is not optically centred",
                )
                self.assertEqual(entry["failed"], [])
                self.assertEqual(entry["pending"], [])
                island = entry["island"]
                self.assertIsNotNone(island, "island host never registered")
                self.assertGreater(island["width"], 0)
                self.assertTrue(island["visible"])


if __name__ == "__main__":
    unittest.main()
