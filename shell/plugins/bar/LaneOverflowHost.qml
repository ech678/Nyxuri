// Fork & Trim: dux-shell quickshell/Modules/DBar/SectionOverflow.qml
// (references/dux-shell, MIT, D4d). Kept from dux: the per-lane expander
// semantics — a chevron capsule at the lane's inner end, click toggles a
// popout that HOSTS the lane's overflowed widget instances (the widget
// Loader relocates lane group <-> popup column, never destroyed, state
// preserved), expanderIcon direction follows the bar edge.
// Replaced for Nyxuri (D4d-3 decision): the button body is our BarGroup
// capsule (fusion chrome + padding axes for free) and the popout is the
// shared StyledPopup (anchored to the bar edge like every other bar
// popup), not dux's DPopout. No scrolling: a lane's hidden set is small
// by construction (registered boundary).
//
// The host is declared once per lane per branch row; only the active
// branch instance can be clicked, so its popup is the live one.

import QtQuick
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import "OverflowLayout.js" as OverflowLayout

Item {
    id: root

    // Hidden groups of this lane (the engine's resolver output, active
    // branch, lane order). Empty = no button.
    property var overflowGroups: []
    property bool vertical: false
    // D4e: the owning bar rides along for the popup's routing/delay axes.
    property var widgetBar: null
    property bool open: popup.pinnedOpen
    // dux SectionOverflow closes on membership changes: a refit while open
    // re-parents widgets back before the set mutates.
    onOverflowGroupsChanged: {
        if (open)
            root.close();
    }

    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    function toggle(): void {
        if (open)
            root.close();
        else
            root.show();
    }

    function show(): void {
        if (!root.overflowGroups.length || open)
            return;
        popup.pinnedOpen = true;
        for (let i = 0; i < root.overflowGroups.length; i += 1) {
            const group = root.overflowGroups[i];
            group.setWidgetHost(popupColumn);
            // The loader's width/height were Layout-managed in the lane row;
            // pin them to the natural size so the popup column lays the
            // widget out at what it actually wants to be.
            const loader = group.widgetLoader;
            if (loader) {
                loader.width = loader.implicitWidth;
                loader.height = loader.implicitHeight;
            }
        }
    }

    // Restore every hosted loader BEFORE the popup deactivates — the popup
    // window (and its content tree) is destroyed on deactivate.
    function close(): void {
        for (let i = 0; i < root.overflowGroups.length; i += 1) {
            const group = root.overflowGroups[i];
            if (group.widgetLoader && group.widgetLoader.parent === popupColumn)
                group.restoreWidget();
        }
        popup.pinnedOpen = false;
    }

    BarGroup {
        id: button
        // Explicit geometry, not anchors: the host item is layout-managed
        // (RowLayout/ColumnLayout child), and anchoring inside one is
        // flagged as undefined behavior by the layout runtime.
        x: 0
        y: 0
        width: root.width
        height: root.height
        segmentRole: "solo"
        vertical: root.vertical
        widgetName: ""

        Item {
            implicitWidth: symbol.width
            implicitHeight: symbol.height

            MaterialSymbol {
                id: symbol
                anchors.centerIn: parent
                text: OverflowLayout.expanderIcon(Config.options.bar.edge, root.open)
                iconSize: Appearance.sizes.barUtilIconSize
                fill: hover.hovered ? 1 : 0
                color: Appearance.colors.colOnLayer1

                Behavior on fill {
                    NumberAnimation {
                        duration: Appearance.animation.elementMoveFast.duration
                    }
                }
            }

            HoverHandler {
                id: hover
            }
        }
    }

    Item {
        anchors.fill: parent
        z: 1

        TapHandler {
            acceptedButtons: Qt.LeftButton
            gesturePolicy: TapHandler.ReleaseWithinBounds
            onTapped: root.toggle()
        }
    }

    StyledPopup {
        id: popup

        widgetBar: root.widgetBar
        hoverTarget: root
        hoverActivates: false
        closeOnOutsideClick: true
        onRequestClose: root.close()

        Column {
            id: popupColumn
            spacing: 4
        }
    }
}
