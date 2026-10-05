pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.app
import qs.modules.filepicker
import "../../../shared/utils/SystemFormat.js" as Format
import "./WeatherIcons.js" as WeatherIcons
import qs.shared.i18n

// Dashboard "Home" page. Layout ported 1:1 from end4-pC's DashboardHomePage:
// header with greeting + uptime + four resource gauges, then a three-column card
// grid (profile + system info / calendar / clock + tasks).
//
// Content bindings point at nyxuri's own services:
//   ResourceUsage -> SystemMonitorService, Battery -> PowerService,
//   DateTime/SystemInfo -> TimeService + SystemIdentityService,
//   Weather -> WeatherService, Todo -> TodoService, profile -> AvatarService.
//
// end4-pC's "Updates" card is not ported: nyxuri has no update checker, and
// inventing one would be adding a feature this tree does not have.
Item {
    id: root

    required property Item pager
    property int staggerMs: 45

    readonly property date now: new Date(clockTimer.tick)
    property date viewMonth: new Date(root.now.getFullYear(), root.now.getMonth(), 1)
    property date selectedDate: new Date()

    readonly property int firstDay: Qt.locale().firstDayOfWeek % 7
    readonly property int daysInViewMonth: new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1,
                                                    0).getDate()
    readonly property int viewOffset: (viewMonth.getDay() - firstDay + 7) % 7
    readonly property int calendarRows: Math.ceil((viewOffset + daysInViewMonth) / 7)
    readonly property bool viewingCurrentMonth: viewMonth.getFullYear() === root.now.getFullYear()
                                                && viewMonth.getMonth() === root.now.getMonth()
    property var todoService: null
    readonly property var todoList: root.todoService ? root.todoService.list : []
    readonly property int pendingTasks: root.todoList.filter(t => !t.done).length
    // lspci supplies the marketing name ("Navi 33 [Radeon RX 7600/…]"); the
    // sysmon sample only carries vendor and driver ("AMD (amdgpu)"). Falling
    // back on the latter keeps the tile readable on a host without pciutils.
    readonly property string gpuLabel: {
        if (SystemIdentityService.gpuModelName !== "")
            return SystemIdentityService.gpuModelName;
        return SystemMonitorService.selectedGpuId !== "" ? String(SystemMonitorService.selectedGpu.name
                                                                  || "") : "";
    }
    // Derived rather than inlined at the label: the interpolated expression is
    // long enough that qmlformat wraps the template literal onto a second
    // source line, and the card then renders the count as "0/\n0".
    readonly property string taskProgressText: (root.todoList.length - root.pendingTasks) + "/"
                                               + root.todoList.length

    readonly property var rootDisk: Format.rootDisk(SystemMonitorService.disks)

    readonly property string greeting: {
        const h = root.now.getHours();
        if (h < 6)
            return I18n.tr("Good night");
        if (h < 12)
            return I18n.tr("Good morning");
        if (h < 19)
            return I18n.tr("Good afternoon");
        return I18n.tr("Good evening");
    }

    // The gauges mirror end4-pC's four-up row; each entry maps one nyxuri
    // service reading onto a 0..1 ratio. `show` keeps optional sources (battery
    // on a desktop) out of the row instead of rendering a dead ring.
    readonly property var gaugeModel: [
        {
            "ratio": Format.isNumber(SystemMonitorService.cpu.usagePercent)
                     ? SystemMonitorService.cpu.usagePercent / 100 : 0,
            "icon": "memory",
            "accent": Appearance.colors.colPrimary,
            "label": root.cpuTemperature > 0 ? I18n.tr("CPU") + " · " + Math.round(root.cpuTemperature)
                                               + "°C" : I18n.tr("CPU"),
            "show": true
        },
        {
            "ratio": Format.isNumber(SystemMonitorService.memory.usagePercent)
                     ? SystemMonitorService.memory.usagePercent / 100 : 0,
            "icon": "developer_board",
            "accent": Appearance.colors.colTertiary,
            "label": I18n.tr("RAM") + " · " + Format.bytes(SystemMonitorService.memory.usedBytes),
            "show": true
        },
        {
            "ratio": Format.isNumber(root.rootDisk.usagePercent) ? root.rootDisk.usagePercent / 100 : 0,
            "icon": "hard_drive",
            "accent": Appearance.colors.colSecondary,
            "label": I18n.tr("Disk") + " · " + Format.bytes(root.rootDisk.usedBytes),
            "show": true
        },
        {
            "ratio": PowerService.present ? PowerService.percentage / 100 : 0,
            "icon": PowerService.charging ? "battery_charging_full" : "battery_full",
            "accent": PowerService.discharging && PowerService.percentage < 20 ? Appearance.colors.colError :
                                                                                 Appearance.colors.colPrimary,
            "label": PowerService.charging ? I18n.tr("Charging") : I18n.tr("Battery"),
            "show": PowerService.present
        }
    ]

    readonly property real cpuTemperature: Format.isNumber(
                                               SystemMonitorService.cpu.packageTemperatureCelsius)
                                           ? SystemMonitorService.cpu.packageTemperatureCelsius :
                                             SystemMonitorService.cpu.temperatureCelsius

    // sysmon network is a per-interface map; sum it into one up/down rate.
    readonly property var net: SystemMonitorService.network || ({})
    readonly property real netDownBytes: (root.net.interfaces || []).reduce(function (sum, iface) {
        return sum + (Format.isNumber(iface.downloadBytesPerSecond) ? iface.downloadBytesPerSecond : 0);
    }, 0)
    readonly property real netUpBytes: (root.net.interfaces || []).reduce(function (sum, iface) {
        return sum + (Format.isNumber(iface.uploadBytesPerSecond) ? iface.uploadBytesPerSecond : 0);
    }, 0)

    Timer {
        id: clockTimer

        property double tick: Date.now()

        interval: 30000
        running: true
        repeat: true
        onTriggered: tick = Date.now()
    }

    // The clock tick is a long-lived repeating timer; stop it explicitly so the
    // page leaves nothing running when the dashboard tears down.
    Component.onDestruction: {
        clockTimer.stop();
        SystemMonitorService.clearConsumer("dashboard-home");
        // Without a registered consumer the uptime reader never starts and the
        // header would show "0 minutes" forever.
        SystemIdentityService.setUptimeConsumer("dashboard-home", false);
    }

    // Subscribe to the shared sysmon stream so the status card has live data;
    // the service unions owners into one process, so this never samples twice.
    Component.onCompleted: {
        SystemMonitorService.setConsumerModules("dashboard-home", ["cpu", "memory", "disk", "network"]);
        SystemIdentityService.setUptimeConsumer("dashboard-home", true);
    }

    function shiftMonth(delta) {
        root.viewMonth = new Date(root.viewMonth.getFullYear(), root.viewMonth.getMonth() + delta, 1);
    }

    function sameDay(a, b) {
        return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate()
                === b.getDate();
    }

    component InfoTile: RowLayout {
        id: tile

        property string icon: ""
        property string label: ""
        property string value: ""
        property color accent: Appearance.colors.colPrimaryContainer
        property color onAccent: Appearance.colors.colOnPrimaryContainer

        spacing: 8

        Rectangle {
            implicitWidth: 30
            implicitHeight: 30
            radius: 10
            color: tile.accent

            MaterialSymbol {
                anchors.centerIn: parent
                text: tile.icon
                iconSize: 18
                fill: 1
                color: tile.onAccent
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            StyledText {
                text: tile.label
                font.pixelSize: 10
                color: Appearance.colors.colSubtext
            }

            StyledText {
                Layout.fillWidth: true
                text: tile.value || "–"
                font.pixelSize: Typography.bodySmall.pixelSize
                font.weight: Font.Medium
                color: Appearance.colors.colOnLayer1
                elide: Text.ElideRight
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 24

            ColumnLayout {
                spacing: 0

                StyledText {
                    text: root.greeting
                    font.pixelSize: Typography.titleLarge.pixelSize
                    color: Appearance.colors.colSubtext
                }

                StyledText {
                    text: I18n.tr("Up since") + " • " + SystemIdentityService.uptimeText
                    font.pixelSize: 30
                    font.weight: Font.Light
                    color: Appearance.colors.colOnLayer0
                }
            }

            Item {
                Layout.fillWidth: true
            }

            Repeater {
                model: root.gaugeModel

                delegate: RowLayout {
                    required property var modelData

                    visible: modelData.show
                    spacing: 8

                    Item {
                        implicitWidth: 48
                        implicitHeight: 48

                        CircularProgress {
                            anchors.fill: parent
                            implicitSize: 48
                            lineWidth: 5
                            value: parent.parent.modelData.ratio
                            colPrimary: parent.parent.modelData.accent
                            colSecondary: Appearance.colors.colSecondaryContainer
                        }

                        MaterialSymbol {
                            anchors.centerIn: parent
                            text: parent.parent.modelData.icon
                            iconSize: 20
                            fill: 1
                            color: parent.parent.modelData.accent
                        }
                    }

                    ColumnLayout {
                        spacing: 0

                        StyledText {
                            text: Math.round(parent.parent.modelData.ratio * 100) + "%"
                            font.pixelSize: 30
                            font.weight: Font.Light
                            color: Appearance.colors.colOnLayer0
                        }

                        StyledText {
                            text: parent.parent.modelData.label
                            font.pixelSize: Typography.bodySmall.pixelSize
                            color: Appearance.colors.colSubtext
                        }
                    }
                }
            }
        }

        RowLayout {
            id: homeGrid

            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            ColumnLayout {
                Layout.fillHeight: true
                Layout.preferredWidth: (homeGrid.width - 24) / 3
                spacing: 12

                DashboardCard {
                    id: userCard

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    tint: Appearance.colors.colPrimaryContainer
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: 0
                    travelX: -300
                    travelY: 0

                    Item {
                        anchors.fill: parent
                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: userCard.width
                                height: userCard.height
                                radius: userCard.cardRadius
                            }
                        }

                        FlipCard {
                            id: flip

                            anchors.fill: parent
                            property bool showBack: false

                            onFlipped: showBack = !showBack

                            Item {
                                id: front

                                anchors.fill: parent
                                visible: !flip.showBack

                                Image {
                                    id: avatarImage

                                    anchors.fill: parent
                                    source: AvatarService.avatarUrl
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true
                                    cache: false
                                    sourceSize: Qt.size(userCard.width * 2, userCard.height * 2)
                                    visible: status === Image.Ready
                                }

                                MaterialSymbol {
                                    anchors.centerIn: parent
                                    visible: avatarImage.status !== Image.Ready
                                    text: "account_circle"
                                    fill: 1
                                    iconSize: 120
                                    color: Appearance.colors.colOnPrimaryContainer
                                }

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    height: parent.height * 0.5
                                    gradient: Gradient {
                                        GradientStop {
                                            position: 0
                                            color: "transparent"
                                        }
                                        GradientStop {
                                            position: 1
                                            color: Qt.rgba(0, 0, 0, 0.75)
                                        }
                                    }
                                }

                                ColumnLayout {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    anchors.margins: 16
                                    spacing: 2

                                    StyledText {
                                        Layout.fillWidth: true
                                        text: SystemIdentityService.accountName
                                        font.pixelSize: Typography.headlineSmall.pixelSize
                                        font.weight: Font.DemiBold
                                        color: "white"
                                        elide: Text.ElideRight
                                    }

                                    StyledText {
                                        Layout.fillWidth: true
                                        text: SystemIdentityService.accountIdentity
                                        font.pixelSize: Typography.bodyLarge.pixelSize
                                        color: Qt.rgba(1, 1, 1, 0.75)
                                        elide: Text.ElideRight
                                    }
                                }

                                RippleButton {
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 12
                                    implicitWidth: 38
                                    implicitHeight: 38
                                    buttonRadius: 19
                                    containerColor: Qt.rgba(0, 0, 0, 0.45)
                                    hoverStateLayerColor: Qt.rgba(1, 1, 1, 0.3)
                                    pressedStateLayerColor: Qt.rgba(1, 1, 1, 0.3)
                                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                                    downAction: () => Qt.callLater(() => flip.flip())

                                    contentItem: Item {
                                        MaterialSymbol {
                                            anchors.centerIn: parent
                                            text: "edit"
                                            iconSize: 20
                                            color: "white"
                                        }
                                    }
                                }
                            }

                            Item {
                                id: back

                                anchors.fill: parent
                                visible: flip.showBack

                                Rectangle {
                                    anchors.fill: parent
                                    color: Appearance.colors.colSecondaryContainer
                                }

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true

                                        StyledText {
                                            Layout.fillWidth: true
                                            text: I18n.tr("Profile")
                                            font.pixelSize: Typography.titleLarge.pixelSize
                                            font.weight: Font.DemiBold
                                            color: Appearance.colors.colOnSecondaryContainer
                                        }

                                        RippleButton {
                                            implicitWidth: 36
                                            implicitHeight: 36
                                            buttonRadius: 18
                                            containerColor: Appearance.colors.colPrimary
                                            stateLayerColor: Appearance.colors.colOnPrimary
                                            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                            hoverStateLayerOpacity:
                                                Appearance.interaction.hoverStateLayerOpacity
                                            pressedStateLayerOpacity:
                                                Appearance.interaction.pressedStateLayerOpacity
                                            downAction: () => Qt.callLater(() => flip.flip())

                                            contentItem: Item {
                                                MaterialSymbol {
                                                    anchors.centerIn: parent
                                                    text: "check"
                                                    iconSize: 20
                                                    color: Appearance.colors.colOnPrimary
                                                }
                                            }
                                        }
                                    }

                                    Repeater {
                                        model: [
                                            {
                                                "icon": "badge",
                                                "label": I18n.tr("User"),
                                                "value": SystemIdentityService.accountName
                                            },
                                            {
                                                "icon": "dns",
                                                "label": I18n.tr("Host"),
                                                "value": SystemIdentityService.hostName
                                            }
                                        ]

                                        delegate: RowLayout {
                                            id: fieldRow

                                            required property var modelData

                                            Layout.fillWidth: true
                                            spacing: 8

                                            MaterialSymbol {
                                                text: fieldRow.modelData.icon
                                                iconSize: 18
                                                color: Appearance.colors.colOnSecondaryContainer
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 0

                                                StyledText {
                                                    text: fieldRow.modelData.label
                                                    font.pixelSize: 10
                                                    color: Appearance.colors.colOnSecondaryContainer
                                                    opacity: 0.6
                                                }

                                                StyledText {
                                                    Layout.fillWidth: true
                                                    text: fieldRow.modelData.value
                                                    font.pixelSize: Typography.bodyLarge.pixelSize
                                                    color: Appearance.colors.colOnSecondaryContainer
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }
                                    }

                                    Item {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                    }

                                    // nyxuri has no avatar folder or thumbnail grid;
                                    // it edits one file through the shared picker, so
                                    // the back face offers exactly that action.
                                    RippleButton {
                                        Layout.fillWidth: true
                                        implicitHeight: 38
                                        buttonRadius: 19
                                        containerColor: Qt.rgba(1, 1, 1, 0.12)
                                        stateLayerColor: Appearance.colors.colOnSecondaryContainer
                                        stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                        hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                        pressedStateLayerOpacity:
                                            Appearance.interaction.pressedStateLayerOpacity
                                        downAction: () => avatarPicker.openAt(avatarPicker.picturesDir)

                                        contentItem: RowLayout {
                                            spacing: 6

                                            Item {
                                                Layout.fillWidth: true
                                            }

                                            MaterialSymbol {
                                                text: "image"
                                                iconSize: 18
                                                color: Appearance.colors.colOnSecondaryContainer
                                            }

                                            StyledText {
                                                text: I18n.tr("Choose avatar")
                                                font.weight: Font.Medium
                                                color: Appearance.colors.colOnSecondaryContainer
                                            }

                                            Item {
                                                Layout.fillWidth: true
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                DashboardCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    Layout.preferredHeight: infoGrid.implicitHeight + 24
                    Layout.maximumHeight: infoGrid.implicitHeight + 24
                    tint: Appearance.colors.colLayer1
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: 1
                    travelX: -300
                    travelY: 200

                    GridLayout {
                        id: infoGrid

                        anchors.fill: parent
                        anchors.margins: 12
                        columns: 2
                        rowSpacing: 6
                        columnSpacing: 10

                        InfoTile {
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            icon: "memory"
                            label: I18n.tr("CPU")
                            value: SystemIdentityService.cpuModelName
                            accent: Appearance.colors.colTertiaryContainer
                            onAccent: Appearance.colors.colOnTertiaryContainer
                        }

                        InfoTile {
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            icon: "videocam"
                            label: I18n.tr("GPU")
                            value: root.gpuLabel
                            accent: Appearance.colors.colTertiaryContainer
                            onAccent: Appearance.colors.colOnTertiaryContainer
                        }

                        InfoTile {
                            Layout.fillWidth: true
                            icon: "deployed_code"
                            label: I18n.tr("Kernel")
                            value: SystemIdentityService.kernelRelease
                            accent: Appearance.colors.colSecondaryContainer
                            onAccent: Appearance.colors.colOnSecondaryContainer
                        }

                        InfoTile {
                            Layout.fillWidth: true
                            icon: "terminal"
                            label: I18n.tr("Shell")
                            value: SystemIdentityService.shellName
                            accent: Appearance.colors.colSecondaryContainer
                            onAccent: Appearance.colors.colOnSecondaryContainer
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillHeight: true
                Layout.preferredWidth: (homeGrid.width - 24) / 3
                spacing: 12

                DashboardCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(90, (homeGrid.height - 12) * 0.3)
                    // Neutral on purpose: wallpaper-driven roles swing hue with
                    // every wallpaper (this card has been purple and brown).
                    tint: Appearance.colors.colLayer1
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: 2
                    travelX: 0
                    travelY: -260

                    GridLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        columns: 2
                        rowSpacing: 6
                        columnSpacing: 10

                        InfoTile {
                            Layout.fillWidth: true
                            icon: "network_speed"
                            label: I18n.tr("Network")
                            value: "↓ " + Format.bytesPerSecond(root.netDownBytes) + "   ↑ "
                                   + Format.bytesPerSecond(root.netUpBytes)
                            accent: Appearance.colors.colSecondaryContainer
                            onAccent: Appearance.colors.colOnSecondaryContainer
                        }

                        InfoTile {
                            Layout.fillWidth: true
                            icon: "thermostat"
                            label: I18n.tr("CPU temp")
                            value: root.cpuTemperature > 0 ? Math.round(root.cpuTemperature) + " °C" : Format.unavailable(
                                                                 )
                            accent: Appearance.colors.colSecondaryContainer
                            onAccent: Appearance.colors.colOnSecondaryContainer
                        }

                        InfoTile {
                            Layout.fillWidth: true
                            icon: "memory"
                            label: I18n.tr("Memory")
                            value: Format.bytes(SystemMonitorService.memory.usedBytes) + " / " + Format.bytes(
                                       SystemMonitorService.memory.totalBytes)
                            accent: Appearance.colors.colSecondaryContainer
                            onAccent: Appearance.colors.colOnSecondaryContainer
                        }

                        InfoTile {
                            Layout.fillWidth: true
                            icon: "hard_drive"
                            label: I18n.tr("Disk")
                            value: Format.bytes(root.rootDisk.usedBytes) + " / " + Format.bytes(
                                       root.rootDisk.totalBytes)

                            accent: Appearance.colors.colSecondaryContainer
                            onAccent: Appearance.colors.colOnSecondaryContainer
                        }
                    }
                }

                DashboardCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    tint: Appearance.colors.colLayer1
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: 3
                    travelX: 0
                    travelY: -260

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            ColumnLayout {
                                spacing: 0

                                StyledText {
                                    text: I18n.tr("Selected date")
                                    font.pixelSize: Typography.bodySmall.pixelSize
                                    color: Appearance.colors.colSubtext
                                }

                                StyledText {
                                    text: Qt.locale().toString(root.selectedDate, "ddd, d MMM")
                                    font.pixelSize: 28
                                    font.weight: Font.Medium
                                    color: Appearance.colors.colOnLayer1
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            RippleButton {
                                visible: !root.viewingCurrentMonth || !root.sameDay(root.selectedDate,
                                                                                    root.now)
                                implicitHeight: 34
                                horizontalPadding: 16
                                buttonRadius: 17
                                containerColor: Appearance.colors.colPrimaryContainer
                                stateLayerColor: Appearance.colors.colOnPrimaryContainer
                                stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                                downAction: () => {
                                    root.viewMonth = new Date(root.now.getFullYear(), root.now.getMonth(), 1);
                                    root.selectedDate = new Date();
                                }

                                contentItem: Item {
                                    implicitWidth: contentRow.implicitWidth
                                    implicitHeight: contentRow.implicitHeight

                                    RowLayout {
                                        id: contentRow

                                        anchors.centerIn: parent
                                        spacing: 6

                                        MaterialSymbol {
                                            text: "today"
                                            iconSize: 18
                                            color: Appearance.colors.colOnPrimaryContainer
                                        }

                                        StyledText {
                                            text: I18n.tr("Today")
                                            color: Appearance.colors.colOnPrimaryContainer
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 1
                            color: Appearance.colors.colOutlineVariant
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            StyledText {
                                Layout.fillWidth: true
                                text: Qt.locale().toString(root.viewMonth, "MMMM yyyy")
                                font.pixelSize: Typography.titleLarge.pixelSize
                                font.weight: Font.Medium
                                color: Appearance.colors.colOnLayer1
                            }

                            Repeater {
                                model: [
                                    {
                                        "icon": "chevron_left",
                                        "delta": -1
                                    },
                                    {
                                        "icon": "chevron_right",
                                        "delta": 1
                                    }
                                ]

                                delegate: RippleButton {
                                    required property var modelData

                                    implicitWidth: 36
                                    implicitHeight: 36
                                    buttonRadius: 18
                                    containerColor: "transparent"
                                    stateLayerColor: Appearance.colors.colOnLayer1
                                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                                    downAction: () => root.shiftMonth(modelData.delta)

                                    contentItem: Item {
                                        MaterialSymbol {
                                            anchors.centerIn: parent
                                            text: parent.parent.modelData.icon
                                            iconSize: 22
                                            color: Appearance.colors.colOnLayer1
                                        }
                                    }
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.topMargin: 4
                            Layout.bottomMargin: 4
                            columns: 7
                            rowSpacing: 4
                            columnSpacing: 2

                            Repeater {
                                model: 7

                                delegate: StyledText {
                                    required property int index

                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                    text: Qt.locale().dayName((root.firstDay + index) % 7,
                                                              Locale.ShortFormat).charAt(0).toUpperCase()
                                    font.pixelSize: Typography.bodyLarge.pixelSize
                                    font.weight: Font.Medium
                                    color: Appearance.colors.colSubtext
                                }
                            }

                            Repeater {
                                model: root.calendarRows * 7

                                delegate: Item {
                                    id: dayCell

                                    required property int index

                                    readonly property date cellDate: new Date(root.viewMonth.getFullYear(),
                                                                              root.viewMonth.getMonth(), 1
                                                                              - root.viewOffset + index)
                                    readonly property bool inMonth: cellDate.getMonth()
                                                                    === root.viewMonth.getMonth()
                                    readonly property bool isToday: root.sameDay(cellDate, root.now)
                                    readonly property bool isSelected: root.sameDay(cellDate,
                                                                                    root.selectedDate)
                                    readonly property bool isWeekend: cellDate.getDay() === 0
                                                                      || cellDate.getDay() === 6

                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.preferredHeight: 1

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: Math.min(parent.width, parent.height, 38)
                                        height: width
                                        radius: width / 2
                                        visible: dayCell.inMonth
                                        color: dayCell.isSelected ? Appearance.colors.colPrimary :
                                                                    dayMouse.containsMouse
                                                                    ? Appearance.colors.colLayer1Hover :
                                                                      "transparent"
                                        border.width: dayCell.isToday && !dayCell.isSelected ? 1.5 : 0
                                        border.color: Appearance.colors.colPrimary

                                        Behavior on color {
                                            ColorAnimation {
                                                duration: 150
                                            }
                                        }

                                        StyledText {
                                            anchors.centerIn: parent
                                            text: dayCell.cellDate.getDate()
                                            // 对齐上游 end4-pC 实际渲染值 15，跳过 0.85 缩放
                                            font.pixelSize: 15
                                            font.weight: dayCell.isSelected || dayCell.isToday ? Font.Bold :
                                                                                                 Font.Normal
                                            color: dayCell.isSelected ? Appearance.colors.colOnPrimary :
                                                                        dayCell.isToday
                                                                        ? Appearance.colors.colPrimary :
                                                                          dayCell.isWeekend
                                                                          ? Appearance.colors.colTertiary :
                                                                            Appearance.colors.colOnLayer1
                                        }
                                    }

                                    MouseArea {
                                        id: dayMouse

                                        anchors.fill: parent
                                        enabled: dayCell.inMonth
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectedDate = dayCell.cellDate
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillHeight: true
                Layout.preferredWidth: (homeGrid.width - 24) / 3
                spacing: 12

                DashboardCard {
                    id: clockCard

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 180
                    tint: Appearance.colors.colPrimaryContainer
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: 4
                    travelX: 300
                    travelY: -120

                    Item {
                        anchors.fill: parent
                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: clockCard.width
                                height: clockCard.height
                                radius: clockCard.cardRadius
                            }
                        }

                        MaterialShapeCanvas {
                            id: sunShape

                            shape: MaterialShapeCanvas.Shape.Sunny
                            implicitSize: Math.min(clockCard.height * 0.95, 210)
                            color: Appearance.colors.colPrimary
                            anchors.right: parent.right
                            anchors.rightMargin: -sunShape.implicitSize * 0.35
                            anchors.top: parent.top
                            anchors.topMargin: -sunShape.implicitSize * 0.15
                        }

                        ColumnLayout {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 0

                            StyledText {
                                text: Qt.locale().toString(root.now, "dddd MMMM d")
                                font.pixelSize: Typography.bodyLarge.pixelSize
                                font.weight: Font.Medium
                                color: Appearance.colors.colPrimary
                            }

                            StyledText {
                                text: Qt.locale().toString(root.now, "HH:mm")
                                color: Appearance.colors.colOnPrimaryContainer
                                font.pixelSize: 56
                                font.weight: Font.Light
                            }
                        }

                        ColumnLayout {
                            anchors.left: parent.left
                            anchors.bottom: parent.bottom
                            anchors.margins: 16
                            spacing: 0

                            StyledText {
                                text: WeatherService.locationName
                                font.pixelSize: Typography.bodyLarge.pixelSize
                                font.weight: Font.DemiBold
                                color: Appearance.colors.colOnPrimaryContainer
                            }

                            StyledText {
                                text: WeatherService.currentWeatherText
                                font.pixelSize: Typography.bodyLarge.pixelSize
                                color: Appearance.colors.colOnPrimaryContainer
                                opacity: 0.75
                            }

                            RowLayout {
                                Layout.topMargin: 2
                                spacing: 8

                                MaterialSymbol {
                                    text: WeatherIcons.symbolFor(WeatherService.currentIconName)
                                    iconSize: 30
                                    fill: 1
                                    color: Appearance.colors.colPrimary
                                }

                                StyledText {
                                    text: WeatherService.hasValidData ? Math.round(
                                                                            WeatherService.currentTemperatureC)
                                                                        + "°C" : "--"
                                    font.pixelSize: 28
                                    font.weight: Font.DemiBold
                                    color: Appearance.colors.colPrimary
                                }
                            }
                        }
                    }
                }

                DashboardCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: tasksContent.implicitHeight + 28
                    tint: Appearance.colors.colSecondaryContainer
                    pager: root.pager
                    staggerMs: root.staggerMs
                    animIndex: 5
                    travelX: 300
                    travelY: 200

                    ColumnLayout {
                        id: tasksContent

                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            MaterialShapeWrappedMaterialSymbol {
                                wrappedShape: MaterialShapeCanvas.Shape.Clover4Leaf
                                text: root.pendingTasks === 0 && root.todoList.length > 0 ? "celebration" :
                                                                                            "checklist"

                                iconSize: 26
                                fill: 1
                                padding: 11
                                color: Appearance.colors.colSecondary
                                colSymbol: Appearance.colors.colOnSecondary
                            }

                            ColumnLayout {
                                spacing: 0

                                StyledText {
                                    text: I18n.tr("Tasks")
                                    font.pixelSize: Typography.titleLarge.pixelSize
                                    font.weight: Font.DemiBold
                                    color: Appearance.colors.colOnSecondaryContainer
                                }

                                StyledText {
                                    text: root.todoList.length === 0 ? I18n.tr("Nothing to do") :
                                                                       root.pendingTasks === 0 ? I18n.tr(
                                                                                                     "All done") :
                                                                                                 root.pendingTasks
                                                                                                 + " " + I18n.tr(
                                                                                                     "left")
                                    font.pixelSize: Typography.bodySmall.pixelSize
                                    color: Appearance.colors.colOnSecondaryContainer
                                    opacity: 0.75
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            StyledText {
                                text: root.taskProgressText
                                font.pixelSize: Typography.titleLarge.pixelSize
                                font.weight: Font.Light
                                color: Appearance.colors.colOnSecondaryContainer
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 8
                            radius: 4
                            color: Qt.rgba(1, 1, 1, 0.12)

                            Rectangle {
                                height: parent.height
                                radius: 4
                                color: Appearance.colors.colSecondary
                                width: root.todoList.length === 0 ? 0 : parent.width * (root.todoList.length
                                                                                        - root.pendingTasks)
                                                                    / root.todoList.length

                                Behavior on width {
                                    NumberAnimation {
                                        duration: 350
                                        easing.type: Easing.OutCubic
                                    }
                                }
                            }
                        }

                        ListView {
                            id: todoList

                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: 3 * 40 + 2 * 6
                            Layout.minimumHeight: 3 * 40 + 2 * 6
                            clip: true
                            spacing: 6
                            ScrollBar.vertical: StyledScrollBar {}

                            WheelScrollController {
                                flickable: todoList
                            }

                            model: root.todoList.map((t, i) => ({
                                "content": t.content,
                                "done": t.done,
                                "origIndex": i
                            }))

                            delegate: RippleButton {
                                id: taskDelegate

                                required property var modelData

                                width: ListView.view.width
                                implicitHeight: 40
                                buttonRadius: 20
                                containerColor: Qt.rgba(1, 1, 1, taskDelegate.modelData.done ? 0.05 : 0.1)
                                stateLayerColor: Appearance.colors.colOnSecondaryContainer
                                stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                                downAction: () => {
                                    const index = taskDelegate.modelData.origIndex;
                                    const done = taskDelegate.modelData.done;
                                    Qt.callLater(() => {
                                        if (done)
                                            root.todoService.markUnfinished(index);
                                        else
                                            root.todoService.markDone(index);
                                    });
                                }
                                altAction: () => {
                                    const index = taskDelegate.modelData.origIndex;
                                    Qt.callLater(() => root.todoService.deleteItem(index));
                                }

                                contentItem: Item {
                                    implicitWidth: todoRow.implicitWidth
                                    implicitHeight: todoRow.implicitHeight

                                    RowLayout {
                                        id: todoRow

                                        anchors.centerIn: parent
                                        spacing: 10

                                        Rectangle {
                                            Layout.leftMargin: 4
                                            implicitWidth: 24
                                            implicitHeight: 24
                                            radius: 12
                                            color: taskDelegate.modelData.done
                                                   ? Appearance.colors.colSecondary : "transparent"
                                            border.width: taskDelegate.modelData.done ? 0 : 2
                                            border.color: Appearance.colors.colOnSecondaryContainer

                                            MaterialSymbol {
                                                anchors.centerIn: parent
                                                visible: taskDelegate.modelData.done
                                                text: "check"
                                                iconSize: 16
                                                color: Appearance.colors.colOnSecondary
                                            }
                                        }
                                        StyledText {
                                            Layout.fillWidth: true
                                            text: taskDelegate.modelData.content
                                            font.pixelSize: Typography.bodyLarge.pixelSize
                                            font.strikeout: taskDelegate.modelData.done
                                            color: Appearance.colors.colOnSecondaryContainer
                                            opacity: taskDelegate.modelData.done ? 0.5 : 1
                                            elide: Text.ElideRight
                                        }

                                        RippleButton {
                                            implicitWidth: 28
                                            implicitHeight: 28
                                            buttonRadius: 14
                                            Layout.rightMargin: 6
                                            containerColor: "transparent"
                                            stateLayerColor: Appearance.colors.colOnSecondaryContainer
                                            stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                                            hoverStateLayerOpacity:
                                                Appearance.interaction.hoverStateLayerOpacity
                                            pressedStateLayerOpacity:
                                                Appearance.interaction.pressedStateLayerOpacity
                                            downAction: () => {
                                                const index = taskDelegate.modelData.origIndex;
                                                Qt.callLater(() => root.todoService.deleteItem(index));
                                            }

                                            contentItem: Item {
                                                MaterialSymbol {
                                                    anchors.centerIn: parent
                                                    text: "close"
                                                    iconSize: 18
                                                    color: Appearance.colors.colOnSecondaryContainer
                                                    opacity: 0.6
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        FilePickerWindow {
            id: avatarPicker

            dialogTitle: I18n.tr("Choose avatar")
            onAccepted: (path, isDirectory) => {
                if (!isDirectory)
                    AvatarService.setAvatar(path);
            }
        }

        function closeChildWindows() {
            if (avatarPicker)
                avatarPicker.dismiss();
        }
    }
}
