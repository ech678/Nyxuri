import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services

WidgetPanel {
    id: panelRoot

    property bool foreground: false
    property real pendingDimFraction: IdleService.dimFraction
    readonly property var timeoutPresetSeconds: [60, 120, 300, 600, 900, 1800, 3600, 7200]

    title: qsTr("Idle management")
    icon: "schedule"
    showBackButton: true
    backAction: () => WidgetState.quickSettingsView = "settings"

    function formatTimeout(seconds) {
        const value = Math.max(0, Number(seconds || 0));
        if (value < 60)
            return qsTr("%n second(s)", "", Math.round(value));
        const minutes = value / 60;
        return Math.abs(minutes - Math.round(minutes)) < 0.001 ? qsTr("%n minute(s)", "", Math.round(minutes)) :
                                                                 qsTr("%1 minutes").arg(minutes.toFixed(1));
    }

    function timeoutOptions(currentSeconds) {
        const values = timeoutPresetSeconds.slice();
        const current = Math.max(0, Number(currentSeconds || 0));
        if (current > 0 && values.indexOf(current) === -1)
            values.push(current);
        values.sort((a, b) => a - b);
        return values.map(value => ({
            "seconds": value,
            "label": panelRoot.formatTimeout(value)
        }));
    }

        Timer {
        id: dimFractionCommitTimer
        interval: 250
        repeat: false
        onTriggered: IdleService.setDimFraction(panelRoot.pendingDimFraction)
    }

        SidebarFlickable {
        id: sidebarScroll
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: width
        contentHeight: content.implicitHeight + sidebarScroll.contentTopInset

        ColumnLayout {
        id: content
        y: sidebarScroll.contentTopInset
        width: parent.width
        spacing: Metrics.spacingL

        InlineStatusBanner {
        Layout.topMargin: sidebarScroll.gapFor(0, 1)

        Layout.fillWidth: true
        visible: IdleService.lastError.length > 0
        tone: "error"
        message: IdleService.lastError
    }

        SettingsSection {
        pullExpansion: sidebarScroll.detailExpansion
        Layout.topMargin: sidebarScroll.gapFor(1, 1)

        Layout.fillWidth: true

        SettingsRow {
        Layout.fillWidth: true
        iconName: "coffee"
        title: qsTr("Keep awake")
        trailing: StyledSwitch {
        checked: IdleService.inhibited
        enabled: !IdleService.busy
        Accessible.name: qsTr("Keep awake")
        onToggled: IdleService.setInhibited(checked)
    }
    }

        SettingsRow {
        Layout.fillWidth: true
        iconName: "schedule"
        title: qsTr("Automatic idle")
        trailing: StyledSwitch {
        checked: IdleService.policyEnabled
        enabled: IdleService.policyReady
        Accessible.name: qsTr("Automatic idle")
        onToggled: IdleService.setPolicyEnabled(checked)
    }
    }
    }

        StageEditor {
        Layout.topMargin: sidebarScroll.gapFor(2, 1)

        Layout.fillWidth: true
        stageName: "dim"
        stageTitle: qsTr("Dim screen")
        stageIcon: "brightness_4"
        showDimFraction: true
    }
        StageEditor {
        Layout.topMargin: sidebarScroll.gapFor(3, 1)

        Layout.fillWidth: true
        stageName: "lock"
        stageTitle: qsTr("Lock session")
        stageIcon: "lock"
    }
        StageEditor {
        Layout.topMargin: sidebarScroll.gapFor(4, 1)

        Layout.fillWidth: true
        stageName: "displayOff"
        stageTitle: qsTr("Turn off displays")
        stageIcon: "display_settings"
    }
        StageEditor {
        Layout.topMargin: sidebarScroll.gapFor(5, 1)

        Layout.fillWidth: true
        stageName: "suspend"
        stageTitle: qsTr("Suspend system")
        stageIcon: "mode_standby"
    }
    }
    }

        component StageEditor: SettingsSection {
        id: stageEditor
        pullExpansion: sidebarScroll.detailExpansion

        required property string stageName
        required property string stageTitle
        required property string stageIcon
        property bool showDimFraction: false
        readonly property bool stageEnabled: !!IdleService[stageName + "Enabled"]
        readonly property real stageTimeout: Number(IdleService[stageName + "Timeout"] || 0)
        readonly property bool respectInhibitors: !!IdleService[stageName + "RespectInhibitors"]
        readonly property bool stageActive: IdleService.stages.some(stage => stage.name === stageName
        && stage.active)
        contentSpacing: Metrics.spacingS

        SettingsRow {
        Layout.fillWidth: true
        iconName: stageEditor.stageIcon
        title: stageEditor.stageTitle
        supportingText: stageEditor.stageActive ? qsTr("Triggered") : ""
        trailing: StyledSwitch {
        checked: stageEditor.stageEnabled
        enabled: IdleService.policyReady
        Accessible.name: stageEditor.stageTitle
        onToggled: IdleService.configureStage(stageEditor.stageName, checked, stageEditor.stageTimeout,
        stageEditor.respectInhibitors)
    }
    }

        SettingsRow {
        Layout.fillWidth: true
        title: qsTr("Wait time")
        trailing: SearchSelectMenuField {
        Layout.preferredWidth: 180
        options: panelRoot.timeoutOptions(stageEditor.stageTimeout)
        value: String(stageEditor.stageTimeout)
        textRole: "label"
        valueRole: "seconds"
        maxVisibleItems: 8
        popupBoundsItem: panelRoot
        closeOnAccept: true
        enabled: IdleService.policyReady
        Accessible.name: qsTr("%1 wait time").arg(stageEditor.stageTitle)
        onAccepted: value => IdleService.configureStage(stageEditor.stageName, stageEditor.stageEnabled,
        Number(value), stageEditor.respectInhibitors)
    }
    }

        ColumnLayout {
        Layout.fillWidth: true
        visible: stageEditor.showDimFraction
        spacing: Metrics.spacingS

        Text {
        text: qsTr("Dim percentage")
        color: Appearance.colors.colOnLayer2
        font.family: Typography.bodyMedium.family
        font.pixelSize: Typography.bodyMedium.pixelSize
    }

        MaterialSplitSlider {
        id: dimFractionSlider
        Layout.fillWidth: true
        enabled: IdleService.policyReady
        configuration: MaterialSplitSlider.Configuration.M
        from: 0.1
        to: 0.8
        stepSize: 0.05
        stopIndicatorValues: []
        showTooltipOnHover: true
        usePercentTooltip: false
        tooltipContent: Math.round(value * 100) + "%"
        Accessible.name: qsTr("Screen dim percentage")
        Binding {
        target: dimFractionSlider
        property: "value"
        value: IdleService.dimFraction
        when: !dimFractionSlider.pressed
    }
        onMoved: {
        panelRoot.pendingDimFraction = value;
        dimFractionCommitTimer.restart();
    }
    }
    }

        SettingsRow {
        Layout.fillWidth: true
        iconName: "coffee"
        title: qsTr("Skip while keeping awake")
        trailing: StyledSwitch {
        checked: stageEditor.respectInhibitors
        enabled: IdleService.policyReady
        Accessible.name: qsTr("%1: respect keep-awake").arg(stageEditor.stageTitle)
        onToggled: IdleService.configureStage(stageEditor.stageName, stageEditor.stageEnabled,
        stageEditor.stageTimeout, checked)
    }
    }
    }
    }
