pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.commons.i18n
import qs.ui

// Android-style master list (Caelestia Nexus NavPane + NavLocations): pill
// search on top, then a single flat column of two-line rows. Categories are
// purely geometric — an extra gap plus connected rounding — exactly like the
// original, which carries no section labels in the navigation. The two
// configuration quick actions stay pinned at the bottom (Nyxuri extension);
// activation is delegated to ControlCenterWindow.
ColumnLayout {
    id: root

    property int currentIndex: 0
    property var routes: []

    signal routeActivated(int index)

    // Routes arrive registry-sorted (manifest order, then id) and carry the
    // manifest's `group` key: consecutive same-group rows form one geometric
    // cluster (an extra gap plus connected first/last rounding). No section
    // labels, exactly like the original NavLocations — and no host-side
    // grouping table to keep in sync.
    readonly property var navModel: {
        const rows = [];
        let previousGroup = null;
        for (let index = 0; index < root.routes.length; ++index) {
            const route = root.routes[index];
            const groupStart = route.group !== previousGroup;
            rows.push({
                          route: route,
                          routeIndex: index,
                          groupStart: groupStart
                      });
            previousGroup = route.group;
        }
        for (let position = 0; position < rows.length; ++position) {
            const next = rows[position + 1];
            rows[position].first = position === 0 || rows[position].groupStart === true;
            rows[position].last = position === rows.length - 1 || (next !== undefined && next.groupStart
                                                                   === true);

        }
        return rows;
    }

    function ensureRowVisible(row) {
        if (!row)
            return;
        const top = row.mapToItem(navList.contentItem, 0, 0).y;
        const bottom = top + row.height;
        if (top < navList.contentY)
            navList.contentY = top;
        else if (bottom > navList.contentY + navList.height)
            navList.contentY = bottom - navList.height;
    }

    spacing: NexusStyle.spacing.large

    NexusSearchBar {
        id: searchBar

        Layout.fillWidth: true

        placeholderText: I18n.tr("Search settings")
    }

    VerticalFadeFlickable {
        id: navList

        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        contentWidth: width
        contentHeight: navColumn.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        topMargin: NexusStyle.padding.large
        bottomMargin: NexusStyle.padding.large

        ColumnLayout {
            id: navColumn

            width: navList.width
            spacing: NexusStyle.spacing.extraSmall

            Repeater {
                model: root.navModel

                NexusNavRow {
                    id: navRow

                    required property int index
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.topMargin: navRow.index !== 0 && navRow.modelData.groupStart === true
                                      ? NexusStyle.spacing.medium : 0
                    active: root.currentIndex === navRow.modelData.routeIndex
                    title: navRow.modelData.route.title
                    description: navRow.modelData.route.description
                    icon: navRow.modelData.route.icon
                    first: navRow.modelData.first
                    last: navRow.modelData.last
                    onActivated: root.routeActivated(navRow.modelData.routeIndex)
                    onActiveChanged: if (active)
                                         root.ensureRowVisible(navRow)
                }
            }
        }
    }
}
