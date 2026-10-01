import QtQuick
import QtQuick.Layouts
import qs.Services
import qs.Common
import qs.Widgets.common

ColumnLayout {
    id: root

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
        if (ControlCenterService.searchTarget && !ControlCenterService.applyingSearch && searchRequestSerial
                === ControlCenterService.searchSerial)
            ControlCenterService.cancelSearch();
        ControlCenterService.retrySearch();
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
        Layout.topMargin: Metrics.pageMargin
        currentValue: root.section
        model: [
            {
                value: "configuration",
                label: SpotlightCatalog.title("general.displays.configuration")
            },
            {
                value: "gamma",
                label: SpotlightCatalog.title("general.displays.gamma")
            }
        ]
        onValueSelected: value => root.section = value
    }
    Loader {
        id: pageLoader
        onLoaded: {
            ControlCenterService.retrySearch();
            if (item && "parentModal" in item)
                item.parentModal = Qt.binding(() => root.parentModal);
        }
        Layout.fillWidth: true
        Layout.fillHeight: true
        source: {
            const route = SpotlightCatalog.route("general.displays." + root.section);
            return route ? Qt.resolvedUrl(route.source) : "";
        }
    }
}
