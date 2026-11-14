"""B8.6 bar runtime probe gate.

The string-assertion suites cannot catch a NaN layout chain, a compiled-empty
widget or a Type/Reference storm. This test drives scripts/dev/probe-bar.sh,
which loads BarContent in an isolated shell and reports every active Loader
status plus the evaluated lane geometry for all six corner styles, the four
borderless modes, the self-hiding widget lane (Media with no track), and the
tray surface (fake SNI items -> pin -> overflow arrow -> persisted config).

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
                        "removing the island from the layout did not empty the middle lane")
        self.assertTrue(report["islandRestored"]["ok"],
                        "re-adding the island to the layout did not restore it")
        self.assertTrue(report["islandMigration"]["ok"], report["islandMigration"])
        self.assertEqual(report["islandMigration"]["seeded"], ["island"])
        self.assertEqual(report["islandMigration"]["keptEmpty"], [])
        self.assertEqual(report["islandMigration"]["legacyOff"], [])
        self.assertTrue(report["idleFace"]["ok"], report["idleFace"])
        self.assertGreater(report["idleFace"]["idleWidth"], 0)
        self.assertTrue(report["idleFace"]["avatarOptional"], report["idleFace"])
        self.assertLess(report["idleFace"]["noAvatarWidth"], report["idleFace"]["idleWidth"])
        if report["idleFace"]["satellite"] == "clock":
            self.assertTrue(report["idleFace"]["clockVisible"],
                            "the horizontal clock satellite did not render")
            self.assertGreater(report["idleFace"]["clockWidth"], 0)
        if report["idleFace"]["showAvatar"]:
            self.assertTrue(report["idleFace"]["avatarReady"] or report["idleFace"]["avatarFallback"],
                            "idle avatar has neither an image nor the fallback glyph")
        self.assertEqual(report["keyboardOsd"]["islandState"], "osd",
                         "caps/num lock changes did not reach the island OSD")
        keyboard = report["styles"][-1].get("keyboard") or {}
        leds = sorted(Path("/sys/class/leds").glob("*::capslock")) + sorted(
            Path("/sys/class/leds").glob("*::numlock"))
        if leds:
            self.assertTrue(keyboard.get("available"),
                            "KeyboardIndicators should be ready when LED class devices exist")
            caps = any((led / "brightness").read_text().strip() == "1"
                       for led in Path("/sys/class/leds").glob("*::capslock"))
            self.assertEqual(keyboard.get("caps"), caps)
            # iNiR deliberately keeps Num unreliable until its first transition,
            # so only require a boolean here.
            self.assertIsInstance(keyboard.get("num"), bool)
        self.assertEqual(len(report["styles"]), 6)
        self.assertEqual([entry["cornerStyle"] for entry in report["styles"]],
                         [0, 1, 2, 3, 4, 5])
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

        self.assertTrue(report["borderless"]["ok"], report["borderless"])
        self.assertEqual(report["borderless"]["modes"],
                         ["pills", "separated", "segmented", "transparent"])

        self.assertTrue(report["mediaHidden"]["ok"], report["mediaHidden"])
        cases = report["mediaHidden"]["cases"]
        self.assertEqual([case["cornerStyle"] for case in cases], ["1", "3"])
        for case in cases:
            with self.subTest(mediaHiddenStyle=case["cornerStyle"]):
                self.assertLessEqual(abs(case["leftWidth"]), 0.5,
                                     "a lane whose only widget is hidden kept capsule padding")
                self.assertLessEqual(abs(case["centerWidth"]), 0.5)

        # B9.1 tray surface: fake StatusNotifierItems prove the overflow arrow
        # reacts to pin state and that the choice lands in config.toml. Without
        # this the probe would still pass on a `unpinnedItems = []` stub.
        tray = report["tray"]
        self.assertTrue(tray["ok"], tray)
        self.assertEqual(len(tray["items"]), 3, tray["items"])
        self.assertEqual(tray["initial"]["unpinnedCount"], 0,
                         "pin-by-default should leave nothing behind the arrow")
        self.assertGreaterEqual(tray["initial"]["pinnedCount"], 2)
        self.assertFalse(tray["initial"]["overflowVisible"])
        self.assertEqual(len(tray["hidden"]["unpinned"]), 1,
                         "hiding an item must move it into the overflow group")
        self.assertTrue(tray["hidden"]["overflowVisible"],
                        "the overflow arrow never appeared after unpin")
        self.assertFalse(tray["closed"], "closeOverflowMenu did not close the popup")
        self.assertTrue(tray["persisted"], "the pin choice was not written to config.toml")
        self.assertEqual(tray["reset"]["unpinnedCount"], 0)

        # B9.2 status cluster: fixed 26px slots, tooltips on every visible
        # status, and two injected peripherals (one critical).
        icons = report["systemIcons"]
        self.assertTrue(icons["ok"], icons)
        self.assertGreaterEqual(icons["slotCount"], 5)
        self.assertLessEqual(abs(icons["groupWidth"] - icons["expectedGroupWidth"]), 0.5)
        self.assertIn("mouse", icons["fakeIcons"])
        self.assertIn("headphones", icons["fakeIcons"])
        self.assertEqual(icons["fakeCritical"], 1)

        # B9.4 vertical bar: both edges evaluate real geometry with the island
        # filtered out, and the Float style boost lands on the vertical axis.
        vertical = report["vertical"]
        self.assertTrue(vertical["ok"], vertical)
        self.assertTrue(vertical["boost"], vertical)
        self.assertEqual(len(vertical["cases"]), 6)
        for case in vertical["cases"]:
            with self.subTest(verticalEdge=case["edge"], scene=case["scene"]):
                self.assertTrue(case["ok"], case)
                self.assertGreater(case["width"], 0)
                self.assertEqual(case["pending"], [])
                self.assertEqual(case["failed"], [])
                if case["scene"] == "default":
                    self.assertEqual(case["middle"], [],
                                     "the island must be filtered out of the vertical layout")
                    self.assertGreater(case["topHeight"], 0)
                    self.assertGreater(case["bottomHeight"], 0)
                else:
                    self.assertEqual(case["middle"], ["clock"])
                    self.assertGreater(case["centerHeight"], 0)

        # B9.5 outer margins: the same pure math the window binds, for every
        # edge and the 0/12/24 tiers, including the reserved exclusive zone.
        margins = report["margins"]
        self.assertTrue(margins["ok"], margins)
        self.assertEqual(len(margins["cases"]), 12)
        self.assertGreater(margins["baseBarHeight"], 0)
        self.assertGreater(margins["baseVerticalBarWidth"], 0)

        # B9.4 window geometry: the real Bar.qml window, walked through every
        # edge. The top->left->top round trip is the regression gate for the
        # conditional-anchor bug that left the bar invisible after switching
        # back (content kept the screen width/height).
        window_probe = report["windowProbe"]
        self.assertTrue(window_probe["ok"], window_probe)
        self.assertTrue(window_probe["roundTrip"],
                        "top -> left -> ... -> top changed the evaluated geometry")
        cases = window_probe["cases"]
        self.assertEqual([case["edge"] for case in cases],
                         ["top", "left", "right", "bottom", "top"])
        for case in cases:
            with self.subTest(windowEdge=case["edge"]):
                self.assertTrue(case["ok"], case)
                self.assertGreater(case["window"]["w"], 0)
                self.assertGreater(case["window"]["h"], 0)
                self.assertGreater(case["content"]["w"], 0)
                self.assertGreater(case["content"]["h"], 0)
                if case["vertical"]:
                    self.assertEqual(case["middle"], [],
                                     "the vertical layout must filter the island")


if __name__ == "__main__":
    unittest.main()
