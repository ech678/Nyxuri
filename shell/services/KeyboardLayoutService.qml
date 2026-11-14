pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.services

// Current keyboard layout for the bar indicator (Fork & Trim of iNiR's
// HyprlandXkb, Niri-only). The compositor surface is the sole IPC dialect: the
// driver seeds niri msg -j keyboard-layouts and folds the event stream's
// KeyboardLayoutsChanged / KeyboardLayoutSwitched into the same properties.
Singleton {
    id: root

    readonly property var names: CompositorDriver.keyboardLayoutNames
    readonly property string currentLayoutName: CompositorDriver.currentKeyboardLayoutName
    readonly property int currentIndex: CompositorDriver.currentKeyboardLayoutIndex
    readonly property bool hasMultipleLayouts: root.names.length > 1
    readonly property string currentLayoutCode: root.codeFor(root.currentLayoutName)

    property var _codes: ({})
    property bool _rulesLoaded: false

    signal layoutChanged

    function codeFor(name) {
        if (!name || name.length === 0)
            return "";
        if (root._codes.hasOwnProperty(name))
            return root._codes[name];
        // base.lst not read yet (or a name it does not know): keep the
        // indicator meaningful with a stable three-letter abbreviation.
        return name.slice(0, 3).toUpperCase();
    }

    function parseRules(text) {
        const codes = {};
        for (const line of String(text || "").split("\n")) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith("!"))
                continue;
            const matchLayout = trimmed.match(/^(\S+)\s+(.+)$/);
            if (matchLayout) {
                codes[matchLayout[2]] = matchLayout[1];
                continue;
            }
            const matchVariant = trimmed.match(/^(\S+)\s+(\S+)\s+(.+)$/);
            if (matchVariant)
                codes[matchVariant[3]] = matchVariant[2] + matchVariant[1];
        }
        root._codes = codes;
        root._rulesLoaded = true;
    }

    FileView {
        path: "/usr/share/X11/xkb/rules/base.lst"
        onLoaded: root.parseRules(text())
    }

    onCurrentLayoutNameChanged: root.layoutChanged()
}
