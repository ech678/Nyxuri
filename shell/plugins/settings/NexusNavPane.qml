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

    // Presentation-only category table over stable route ids: it drives the
    // geometric grouping (extra gap + connected first/last rounding). Ids
    // missing from the table join a trailing group so no page can be
    // orphaned by a rename.
    readonly property var groupTable: [
        {
            ids: ["account", "theme", "wallpaper"]
        },
        {
            ids: ["bar", "dock", "sidebar", "keystone"]
        },
        {
            ids: ["network", "connected-devices"]
        },
        {
            ids: ["shortcuts", "spotlight"]
        },
        {
            ids: ["language-region", "shell"]
        },
        {
            ids: ["about"]
        }
    ]

    function routeIndexById(id) {
        for (let index = 0; index < root.routes.length; ++index) {
            if (root.routes[index].id === id)
                return index;
        }
        return -1;
    }

    readonly property var navModel: {
        const rows = [];
        const grouped = [];
        for (let g = 0; g < root.groupTable.length; ++g) {
            const ids = root.groupTable[g].ids;
            let groupStart = -1;
            for (let i = 0; i < ids.length; ++i) {
                const routeIndex = root.routeIndexById(ids[i]);
                if (routeIndex < 0)
                    continue;
                if (groupStart < 0)
                    groupStart = rows.length;
                rows.push({
                              route: root.routes[routeIndex],
                              routeIndex: routeIndex
                          });
                grouped.push(routeIndex);
            }
            if (groupStart >= 0)
                rows[groupStart].groupStart = true;
        }
        const leftovers = [];
        for (let index = 0; index < root.routes.length; ++index) {
            if (grouped.indexOf(index) < 0)
                leftovers.push(index);
        }
        if (leftovers.length > 0) {
            for (let i = 0; i < leftovers.length; ++i)
                rows.push({
                              route: root.routes[leftovers[i]],
                              routeIndex: leftovers[i]
                          });
            rows[rows.length - leftovers.length].groupStart = true;
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
