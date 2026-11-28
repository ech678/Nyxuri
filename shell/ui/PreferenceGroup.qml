import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Connected-card group container: lays out Preference* rows with Nexus
// spacing and dynamically maintains `first` / `last` on whichever
// `isPreferenceRow` children are currently visible, so conditional rows
// never break the outer extraLarge rounding.
ColumnLayout {
    id: root

    function syncEdges(): void {
        const visibleRows = [];
        for (let i = 0; i < children.length; i += 1) {
            const child = children[i];
            if (child && child.isPreferenceRow === true && child.visible)
                visibleRows.push(child);
        }
        for (let i = 0; i < visibleRows.length; i += 1) {
            visibleRows[i].first = (i === 0);
            visibleRows[i].last = (i === visibleRows.length - 1);
        }
    }

    Layout.fillWidth: true
    spacing: NexusStyle.padding.extraSmall / 2

    onChildrenChanged: Qt.callLater(root.syncEdges)
    Component.onCompleted: root.syncEdges()

    Repeater {
        // Observe visibility changes on direct row children without polling.
        model: root.children.length
        delegate: Connections {
            required property int index
            target: index >= 0 && index < root.children.length && root.children[index] && root.children[index].isPreferenceRow === true ? root.children[index] : null
            function onVisibleChanged(): void {
                root.syncEdges();
            }
        }
    }
}
