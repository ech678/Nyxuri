pragma Singleton

import QtQuick
import Quickshell
import qs.app.services

Singleton {
    id: root

    property bool visible: false
    property int selectedIndex: 0

    readonly property var entries: {
        const list = [];
        const seen = {};
        const windows = NiriService.liveWindows || [];
        const order = NiriService.mruWindowIds || [];
        for (let i = 0; i < order.length; ++i) {
            const id = order[i];
            if (seen[id])
                continue;
            for (let j = 0; j < windows.length; ++j) {
                if (windows[j].id === id) {
                    seen[id] = true;
                    list.push(windows[j]);
                    break;
                }
            }
        }
        for (let k = 0; k < windows.length; ++k) {
            if (!seen[windows[k].id]) {
                seen[windows[k].id] = true;
                list.push(windows[k]);
            }
        }
        return list;
    }

    function open() {
        if (root.entries.length === 0)
            return false;
        root.visible = true;
        root.selectedIndex = 0;
        return true;
    }

    function close() {
        root.visible = false;
    }

    function toggle() {
        if (root.visible) {
            root.close();
            return true;
        }
        return root.open();
    }

    function step(delta) {
        const count = root.entries.length;
        if (count === 0)
            return;
        if (!root.visible)
            root.open();
        root.selectedIndex = ((root.selectedIndex + delta) % count + count) % count;
    }

    function activate(index) {
        const position = index === undefined ? root.selectedIndex : index;
        const target = root.entries[position];
        root.close();
        if (target)
            NiriService.focusWindow(target.id);
    }
}
