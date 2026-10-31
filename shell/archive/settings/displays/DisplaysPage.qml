pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.app.services
import qs.shared.theme
import qs.shared.controls
import qs.units.settings

// Displays page shell (M3): keeps the section switch and the routed Loader
// that hosts the two subpages (configuration / gamma). The subpages render
// their own NexusPageBase titles, so the shell claims rendersPageTitle and
// the hosting window's interim route-title shim stays hidden.
ColumnLayout {
    id: root

    readonly property bool rendersPageTitle: true

    property int searchRequestSerial: -1
    readonly property var searchLeaf: pageLoader.item ? (pageLoader.item.searchLeaf || pageLoader.item) : root
    function openSearchPath(path, serial) {
        const section = path.length ? path[0] : "configuration";
        if (searchRequestSerial !== serial) {
            searchRequestSerial = serial;
            root.section = section;
        }
        if (root.section !== section)
            return "cancelled";
        if (!(pageLoader.status === Loader.Ready) || !pageLoader.item)
            return "loading";
        return typeof pageLoader.item.openSearchPath === "function" ? pageLoader.item.openSearchPath(
                                                                          path.slice(1), serial) : "ready";
    }
    property string section: "configuration"
    property bool presentationActive: false
    property var parentModal: null
    function closeChildWindows() {
        if (pageLoader.item && typeof pageLoader.item.closeChildWindows === "function")
            pageLoader.item.closeChildWindows();
    }
    onSectionChanged: {
        if (SettingsBackend.searchTarget && !SettingsBackend.applyingSearch && searchRequestSerial
                === SettingsBackend.searchSerial)
            SettingsBackend.cancelSearch();
        SettingsBackend.retrySearch();
        closeChildWindows();
        DisplayConfigService.clearCompletionNotice();
    }
    onPresentationActiveChanged: {
        if (!presentationActive) {
            closeChildWindows();
            DisplayConfigService.clearCompletionNotice();
        }
    }
    onVisibleChanged: {
        if (!visible)
            DisplayConfigService.clearCompletionNotice();
    }
    Component.onDestruction: DisplayConfigService.clearCompletionNotice()
    spacing: 0

    StyledButtonGroup {
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: NexusStyle.padding.small
        currentValue: root.section
        model: [
            {
                value: "configuration",
                label: SpotlightCatalog.title("displays.configuration")
            },
            {
                value: "gamma",
                label: SpotlightCatalog.title("displays.gamma")
            }
        ]
        onValueSelected: value => root.section = value
    }

    Loader {
        id: pageLoader
        onLoaded: {
            SettingsBackend.retrySearch();
            if (item && "parentModal" in item)
                item.parentModal = Qt.binding(() => root.parentModal);
        }
        Layout.fillWidth: true
        Layout.fillHeight: true
        source: {
            const route = SpotlightCatalog.route("displays." + root.section);
            return route ? Qt.resolvedUrl(route.source) : "";
        }
    }
}
