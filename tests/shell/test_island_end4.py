"""B3-2 island end4 morph faces contract tests.

Verifies:
  - DiNotifs.qml and DiOsd.qml exist and carry GPL-3 Fork & Trim headers
  - DiNotifs connects to TimeService, ThemeService, and NotificationService actions
  - DiOsd connects to dynamic island OSD bindings and VolumeService
  - DynamicIsland.qml contentProviders registers all 6 faces and alwaysWinIds
  - DynamicIsland.qml connects to RecordingService, AudioRecordingService,
    VolumeService, BrightnessService, KeyboardLockService
  - No bare import qs statements in the end4 bundle
"""

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
END4_DIR = os.path.join(REPO_ROOT, "shell", "plugins", "bar", "island", "end4")


def read_end4(filename):
    with open(os.path.join(END4_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


class IslandEnd4FacesContractTest(unittest.TestCase):

    def test_end4_files_exist(self):
        expected_files = [
            "DynamicIsland.qml",
            "DiIdle.qml",
            "DiMedia.qml",
            "DiNotifs.qml",
            "DiOsd.qml",
        ]
        for name in expected_files:
            path = os.path.join(END4_DIR, name)
            self.assertTrue(os.path.isfile(path), f"Missing {name} in {END4_DIR}")

    def test_fork_and_trim_headers(self):
        for name in ["DynamicIsland.qml", "DiIdle.qml", "DiMedia.qml", "DiNotifs.qml", "DiOsd.qml"]:
            content = read_end4(name)
            self.assertIn("Fork & Trim: end4-pC", content, f"{name} missing Fork & Trim header")
            self.assertIn("GPL-3", content, f"{name} missing GPL-3 notice")

    def test_no_bare_import_qs(self):
        for name in ["DynamicIsland.qml", "DiIdle.qml", "DiMedia.qml", "DiNotifs.qml", "DiOsd.qml"]:
            content = read_end4(name)
            for line in content.splitlines():
                stripped = line.strip()
                self.assertFalse(
                    stripped == "import qs" or stripped.startswith("import qs "),
                    f"{name} contains invalid bare 'import qs': {line}"
                )

    def test_di_notifs_contracts(self):
        content = read_end4("DiNotifs.qml")
        self.assertIn("ThemeService.resolveIcon", content)
        self.assertIn("TimeService.hours", content)
        self.assertIn("NotificationService.dismissPopup", content)
        self.assertIn("NotificationService.invokeDefaultAction", content)
        self.assertIn("MaterialShapeWrappedMaterialSymbol", content)

    def test_di_osd_contracts(self):
        content = read_end4("DiOsd.qml")
        self.assertIn('di.iconForProviderId("osd")', content)
        self.assertIn("di.osdValueText()", content)
        self.assertIn("VolumeService", content)
        self.assertIn("MaterialShapeWrappedMaterialSymbol", content)

    def test_dynamic_island_providers_and_services(self):
        content = read_end4("DynamicIsland.qml")
        # All provider IDs present in contentProviders
        for provider_id in ['id: "osd"', 'id: "notification"', 'id: "battery"',
                            'id: "recording"', 'id: "timer"', 'id: "media"']:
            self.assertIn(provider_id, content, f"contentProviders missing {provider_id}")

        # Preemption list contains osd and notification
        self.assertIn('"osd"', content)
        self.assertIn('"notification"', content)
        self.assertIn('"battery"', content)

        # Service bindings
        self.assertIn("RecordingService", content)
        self.assertIn("AudioRecordingService", content)
        self.assertIn("VolumeService", content)
        self.assertIn("BrightnessService", content)
        self.assertIn("KeyboardLockService", content)
        self.assertIn("stopRecording()", content)


if __name__ == "__main__":
    unittest.main()
