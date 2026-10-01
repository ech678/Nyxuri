pragma ComponentBehavior: Bound

import QtQuick
import qs.Widgets.common
import qs.Common
import qs.Services

Item {
    id: root

    property int searchRequestSerial: -1
    readonly property var searchLeaf: pageLoader.item ? (pageLoader.item.searchLeaf || pageLoader.item) : root
    function openSearchPath(path, serial) {
        const section = path.length ? path[0] : "overview";
        if (searchRequestSerial !== serial) {
            searchRequestSerial = serial;
            root.currentSection = section;
        }
        if (root.currentSection !== section)
            return "cancelled";
        if (!(pageLoader.ready) || !pageLoader.item)
            return "loading";
        return typeof pageLoader.item.openSearchPath === "function" ? pageLoader.item.openSearchPath(
                                                                          path.slice(1), serial) : "ready";
    }

    property var parentModal: null
    property string currentSection: "overview"
    property bool presentationActive: false
    property string selectedBluetoothAddress: ""
    property string selectedBluetoothAdapterId: ""

    onCurrentSectionChanged: {
        if (ControlCenterService.searchTarget && !ControlCenterService.applyingSearch && searchRequestSerial
                === ControlCenterService.searchSerial)
            ControlCenterService.cancelSearch();
        ControlCenterService.retrySearch();
    }

    signal navigateRequested(string pageId)

    function selectedBluetoothDevice() {
        return BluetoothService.devices.find(device => {
            return device.address === root.selectedBluetoothAddress && (
                        root.selectedBluetoothAdapterId.length === 0 || device.adapterId
                        === root.selectedBluetoothAdapterId);
        }) || null;
    }

    function openSection(section) {
        root.closeChildWindows();
        BluetoothService.clearError();
        root.currentSection = section;
    }

    function showOverview() {
        root.closeChildWindows();
        BluetoothService.clearError();
        root.currentSection = "overview";
    }

    function showConnectedDevices() {
        root.openSection("connected-devices");
    }

    function openBluetoothDevice(address, adapterId) {
        root.selectedBluetoothAddress = address;
        root.selectedBluetoothAdapterId = adapterId;
        root.openSection("bluetooth-device");
    }

    function goBack() {
        if (root.currentSection === "bluetooth-pairing" || root.currentSection === "bluetooth-device")
            root.showConnectedDevices();
        else
            root.showOverview();
    }

    function closeChildWindows() {
        if (pageLoader.item && typeof pageLoader.item.closeChildWindows === "function")
            pageLoader.item.closeChildWindows();
    }

    Component {
        id: subpageHeader

        GeneralSubpageHeader {
            readonly property string section: parent.route

            anchors.left: parent.left
            anchors.right: parent.right
            title: {
                const route = SpotlightCatalog.route("general." + section);
                if (route)
                    return SpotlightCatalog.title(route.id);
                if (section === "bluetooth-device") {
                    const device = root.selectedBluetoothDevice();
                    return device ? device.name : qsTr("Bluetooth device");
                }
                return SpotlightCatalog.title("general");
            }
            iconName: {
                const route = SpotlightCatalog.route("general." + section);
                if (route)
                    return route.icon;
                return section === "bluetooth-device" ? BluetoothDeviceIcon.iconName(
                                                            root.selectedBluetoothDevice()) : "settings";
            }
            onBackRequested: root.goBack()
        }
    }

    SettingsPageHost {
        id: pageLoader

        anchors.fill: parent
        route: root.currentSection
        navigationDepth: root.currentSection === "overview" ? 0 : (root.currentSection === "bluetooth-device"
                                                                   || root.currentSection
                                                                   === "bluetooth-pairing" ? 2 : 1)
        presentationActive: root.presentationActive
        headerComponent: root.currentSection === "overview" ? null : subpageHeader
        source: {
            const route = SpotlightCatalog.route("general." + root.currentSection);
            if (route)
                return Qt.resolvedUrl(route.source);
            return Qt.resolvedUrl(root.currentSection === "bluetooth-device" ? "BluetoothDevicePage.qml" :
                                                                               "GeneralOverviewPage.qml");
        }
        onLoaded: {
            ControlCenterService.retrySearch();
            if (!item)
                return;

            if ("parentModal" in item)
                item.parentModal = root.parentModal;

            const page = item;
            if ("presentationActive" in page)
                page.presentationActive = Qt.binding(function () {
                    return root.presentationActive && pageLoader.item === page;
                });

            if ("deviceAddress" in item)
                item.deviceAddress = root.selectedBluetoothAddress;

            if ("deviceAdapterId" in item)
                item.deviceAdapterId = root.selectedBluetoothAdapterId;
        }
    }

    Connections {
        function onSectionRequested(section) {
            root.openSection(section);
        }

        function onPairingRequested() {
            root.openSection("bluetooth-pairing");
        }

        function onDeviceRequested(address, adapterId) {
            root.openBluetoothDevice(address, adapterId);
        }

        function onReturnRequested() {
            root.showConnectedDevices();
        }

        function onNavigateRequested(pageId) {
            root.navigateRequested(pageId);
        }

        target: pageLoader.item
        ignoreUnknownSignals: true
    }
}
