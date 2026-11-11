"""Offscreen behavior probe for the production ToolsContent Loader shell."""
import os
from pathlib import Path
import subprocess
import unittest

from tests.utils import TempEnv


class TestIslandToolsLoader(unittest.TestCase):
    def test_real_loader_retains_sessions_and_finishes_fades(self):
        runner = Path("/usr/lib/qt6/bin/qml")
        if not runner.exists():
            self.skipTest("Qt QML runtime unavailable")
        source = (Path(__file__).resolve().parents[2] / "shell/plugins/bar/island/styles/shared/IslandSurface.qml").read_text()
        start = source.index("                    FocusScope {\n                        id: toolsWidget")
        end = source.index("\n                }\n\n                Connections {", start)
        block = source[start:end]
        # Replace Audio first because its name contains RecordingService.
        for old, new in (("AudioRecordingService", "audioService"),
                         ("RecordingService", "videoService"),
                         ("Appearance", "appearance")):
            block = block.replace(old, new)
        stub = '''import QtQuick
Item {
    property bool keyboardActive: false
    property bool retainForRecording: false
    property bool vertical: false
    property string edge: "top"
    implicitWidth: vertical ? 72 : 480
    implicitHeight: vertical ? 480 : 72
    focus: keyboardActive
    signal requestHideIsland
    signal recordingRequested
    Component.onCompleted: root.created++
    Component.onDestruction: root.destroyed++
}
'''
        probe = '''import QtQuick
import QtQuick.Window
Window {
    id: root
    visible: true; width: 600; height: 600
    property bool isToolsMode: false
    property bool recordingLaunchPending: false
    property bool showTools: false
    property bool hoverOpened: false
    property int created: 0
    property int destroyed: 0
    property int replayed: 0
    function syncRecordingConsumer() { replayed++; }
    function syncAudioConsumer() { replayed++; }
    function requestKeyboardFocus() { toolsWidget.forceActiveFocus(); }
    QtObject { id: styleSurface; property bool elongated: true }
    QtObject { id: islandWindow; property bool horizontalEdge: true; property string edge: "top" }
    QtObject { id: hoverIntent; function cancel() {} }
    QtObject { id: appearance; property var animation: ({ expressiveEffects: {duration: 80, type: Easing.Linear, bezierCurve: []} }) }
    QtObject {
        id: videoService
        property string state: "idle"
        readonly property bool isActive: ["selecting", "starting", "recording", "paused", "stopping", "finalizing"].indexOf(state) >= 0
    }
    QtObject {
        id: audioService
        property string state: "idle"
        readonly property bool isActive: ["selecting", "starting", "recording", "stopping", "finalizing"].indexOf(state) >= 0
    }
    Item { width: 600; height: 600
__BLOCK__
    }
    function check(ok, label) {
        if (!ok) { console.error("FAIL " + label); Qt.exit(1); }
    }
    property int step: 0
    property var states: ["selecting", "starting", "recording", "stopping", "finalizing"]
    Timer {
        interval: 130; repeat: true; running: true
        onTriggered: {
            if (step === 0) {
                check(root.created === 0 && !toolsLoader.item, "cold start unloaded");
                check(toolsWidget.implicitWidth === 480, "cold geometry");
                root.isToolsMode = true;
            } else if (step === 1) {
                check(root.created === 1 && root.replayed === 2, "loaded replay");
                check(toolsLoader.item.keyboardActive && toolsLoader.item.activeFocus, "focus routing");
                root.isToolsMode = false;
                check(!!toolsLoader.item, "close retains fading instance");
                root.isToolsMode = true;
            } else if (step === 2) {
                check(root.created === 1 && root.destroyed === 0, "reopen reuses child");
                videoService.state = "selecting";
                root.isToolsMode = false;
            } else if (step >= 3 && step <= 7) {
                check(!!toolsLoader.item && root.destroyed === 0, "video " + videoService.state);
                if (step === 7) audioService.state = "selecting";
                videoService.state = step < 7 ? states[step - 2] : "idle";
            } else if (step >= 8 && step <= 12) {
                check(!!toolsLoader.item && root.destroyed === 0, "audio " + audioService.state);
                audioService.state = step < 12 ? states[step - 7] : "idle";
            } else if (step === 13) {
                check(!toolsLoader.item && root.destroyed === 1, "idle releases hidden child");
                root.isToolsMode = true;
                islandWindow.horizontalEdge = false;
            } else if (step === 14) {
                check(toolsWidget.implicitWidth === 72 && toolsWidget.implicitHeight === 480, "vertical geometry");
                root.isToolsMode = false;
                check(!!toolsLoader.item, "fade waits before destruction");
            } else if (step === 15) {
                check(!toolsLoader.item && root.destroyed === 2, "fade completion unloads");
                console.log("TOOLS_LOADER_PASS"); Qt.quit();
            }
            step++;
        }
    }
    Timer { interval: 8000; running: true; onTriggered: Qt.exit(2) }
}
'''.replace("__BLOCK__", block)
        with TempEnv() as env:
            (env.home / "ToolsContent.qml").write_text(stub)
            path = env.home / "probe.qml"
            path.write_text(probe)
            argv = [str(runner), str(path)]
            self.assertEqual(argv, ["/usr/lib/qt6/bin/qml", str(env.home / "probe.qml")])
            result = subprocess.run(argv, cwd=env.home, capture_output=True, text=True,
                                    timeout=12, env={**os.environ, "QT_QPA_PLATFORM": "offscreen",
                                                     "QT_QUICK_BACKEND": "software"})
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("TOOLS_LOADER_PASS", output)
        self.assertNotIn("ReferenceError", output)
        self.assertNotIn("TypeError", output)
