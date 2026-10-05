import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.modules.filepicker
import qs.shared.i18n

Item {
    id: root

    property int searchRequestSerial: -1
    readonly property var searchLeaf: currentSection === "overview" ? overviewFlickable : pageLoader.item ? (pageLoader.item.searchLeaf || pageLoader.item) : root
    function openSearchPath(path, serial) {
        const section = path.length ? path[0] : "overview";
        if (searchRequestSerial !== serial) {
            searchRequestSerial = serial;
            root.currentSection = section;
        }
        if (root.currentSection !== section)
            return "cancelled";
        if (section === "overview")
            return "ready";
        if (!(pageLoader.status === Loader.Ready) || !pageLoader.item)
            return "loading";
        return typeof pageLoader.item.openSearchPath === "function" ? pageLoader.item.openSearchPath(path.slice(1), serial) : "ready";
    }

    property var parentModal: null
    onCurrentSectionChanged: {
        if (SettingsBackend.searchTarget && !SettingsBackend.applyingSearch && searchRequestSerial === SettingsBackend.searchSerial)
            SettingsBackend.cancelSearch();
        SettingsBackend.retrySearch();
    }
    property string currentSection: "overview"
    property string editingDirectoryKey: ""
    property var editingDirectoryField: null

    function directoryValue(key) {
        return String(UiPreferences[key] || "");
    }

    function saveDirectory(key, value, field) {
        UiPreferences.setRecordingDirectory(key, value);
        if (field)
            field.text = root.directoryValue(key);
    }

    function openDirectoryPicker(key, field) {
        root.saveDirectory(key, field.text, field);
        root.editingDirectoryKey = key;
        root.editingDirectoryField = field;
        directoryPicker.openAt(root.directoryValue(key));
    }

    function openSection(section) {
        root.currentSection = String(section || "overview");
    }

    function showOverview() {
        root.currentSection = "overview";
    }

    function closeChildWindows() {
        root.showOverview();
        directoryPicker.dismiss();
    }

    GeneralSubpageHeader {
        id: subpageHeader

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        visible: root.currentSection !== "overview"
        title: SpotlightCatalog.title("keystone." + root.currentSection)
        backAccessibleName: I18n.tr("Back to Keystone settings")
        z: 2
        onBackRequested: root.showOverview()
    }

    StyledFlickable {
        id: overviewFlickable

        anchors.fill: parent
        visible: root.currentSection === "overview"
        contentWidth: width
        contentHeight: contentColumn.y + contentColumn.implicitHeight + 24

        ColumnLayout {
            id: contentColumn

            width: Math.min(600, Math.max(1, overviewFlickable.width - 48))
            x: Math.max(24, (overviewFlickable.width - width) / 2)
            y: 28
            spacing: 30

            KeystoneSection {
                id: searchSection0
                title: searchAnchor0.title
                SettingsSearchAnchor {
                    id: searchAnchor0
                    target: searchSection0
                    declaration: '{"id":"keystone.section.keystone-style","route":"keystone","title":"Keystone style","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                }
                iconName: "toggle_off"

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Show Keystone")
                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneEnabled
                        Accessible.name: I18n.tr("Show Keystone")
                        onToggled: PersonalizationConfig.setValue("keystoneEnabled", checked)
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Floating")
                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneOverlay
                        Accessible.name: I18n.tr("Floating")
                        onToggled: PersonalizationConfig.setValue("keystoneOverlay", checked)
                    }
                }

                SearchSelectSettingRow {
                    title: I18n.tr("Style")
                    options: PersonalizationConfig.keystoneStyles
                    value: PersonalizationConfig.keystoneStyle
                    placeholder: I18n.tr("Choose Keystone style")
                    onAccepted: value => {
                        return PersonalizationConfig.setKeystoneStyle(value);
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Screen edge")

                    trailing: EdgePositionSelector {
                        position: PersonalizationConfig.keystonePosition
                        onPositionSelected: position => {
                            return PersonalizationConfig.setKeystonePosition(position);
                        }
                    }
                }
            }

            KeystoneSection {
                id: searchSection1
                title: searchAnchor1.title
                SettingsSearchAnchor {
                    id: searchAnchor1
                    target: searchSection1
                    declaration: '{"id":"keystone.section.mouse-actions","route":"keystone","title":"Mouse actions","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                }
                iconName: "mouse"

                SearchSelectSettingRow {
                    title: I18n.tr("Hover")
                    options: PersonalizationConfig.availableKeystoneHoverActionOptions
                    value: PersonalizationConfig.effectiveKeystoneHoverAction
                    onAccepted: value => PersonalizationConfig.setKeystoneAction("hover", value)
                }

                GeneralSliderSetting {
                    title: I18n.tr("Hover open delay")
                    value: PersonalizationConfig.keystoneHoverOpenDelay
                    from: 0
                    to: 500
                    stepSize: 25
                    suffix: I18n.tr(" ms")
                    enabled: PersonalizationConfig.effectiveKeystoneHoverAction !== "none"
                    onMoved: value => PersonalizationConfig.setKeystoneHoverOpenDelay(value)
                }

                GeneralSliderSetting {
                    title: I18n.tr("Hover close delay")
                    value: PersonalizationConfig.keystoneHoverCloseDelay
                    from: 0
                    to: 600
                    stepSize: 25
                    suffix: I18n.tr(" ms")
                    enabled: PersonalizationConfig.effectiveKeystoneHoverAction !== "none"
                    onMoved: value => PersonalizationConfig.setKeystoneHoverCloseDelay(value)
                }

                SearchSelectSettingRow {
                    title: I18n.tr("Left click")
                    options: PersonalizationConfig.keystoneActionOptions
                    value: PersonalizationConfig.keystoneLeftClickAction
                    onAccepted: value => PersonalizationConfig.setKeystoneAction("left", value)
                }

                SearchSelectSettingRow {
                    title: I18n.tr("Middle click")
                    options: PersonalizationConfig.keystoneActionOptions
                    value: PersonalizationConfig.keystoneMiddleClickAction
                    onAccepted: value => PersonalizationConfig.setKeystoneAction("middle", value)
                }
            }

            KeystoneSection {
                id: mediaSection
                title: mediaSearchAnchor.title
                iconName: "music_note"

                SettingsSearchAnchor {
                    id: mediaSearchAnchor
                    target: mediaSection
                    declaration: '{"id":"keystone.section.media-controls","route":"keystone","title":"Media controls","context":"KeystonePage","icon":"music_note","aliases":[]}'
                }

                SearchSelectSettingRow {
                    title: I18n.tr("Progress bar")
                    options: PersonalizationConfig.keystoneMediaProgressOptions
                    value: PersonalizationConfig.keystoneMediaProgressStyle
                    onAccepted: value => PersonalizationConfig.setKeystoneMediaProgressStyle(value)
                }

                SearchSelectSettingRow {
                    title: I18n.tr("Cover style")
                    options: PersonalizationConfig.keystoneMediaCoverOptions
                    value: PersonalizationConfig.keystoneMediaCoverStyle
                    onAccepted: value => PersonalizationConfig.setKeystoneMediaCoverStyle(value)
                }

                SearchSelectSettingRow {
                    title: I18n.tr("Colors")
                    options: PersonalizationConfig.keystoneMediaColorOptions
                    value: PersonalizationConfig.keystoneMediaColorStyle
                    onAccepted: value => PersonalizationConfig.setKeystoneMediaColorStyle(value)
                }
            }

            KeystoneSection {
                visible: PersonalizationConfig.keystoneStyle === "long"
                title: I18n.tr("Status items")
                iconName: "view_week"

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Show device names")
                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneLongShowNames
                        Accessible.name: I18n.tr("Show device names")
                        onToggled: PersonalizationConfig.setKeystoneLongShowNames(checked)
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Show system monitor values")
                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneLongShowMonitorValues
                        Accessible.name: I18n.tr("Show system monitor values")
                        onToggled: PersonalizationConfig.setKeystoneLongShowMonitorValues(checked)
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Show numeric values")
                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneLongShowValues
                        Accessible.name: I18n.tr("Show numeric values")
                        onToggled: PersonalizationConfig.setKeystoneLongShowValues(checked)
                    }
                }

                SettingsRow {
                    id: longLeadingFieldRow
                    Layout.fillWidth: true
                    title: PersonalizationConfig.keystonePosition === "top" || PersonalizationConfig.keystonePosition === "bottom" ? I18n.tr("Left") : I18n.tr("Top")
                    trailing: SortableMultiSelectField {
                        id: longLeadingField
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: Math.max(0, longLeadingFieldRow.width - 96 - 3 * Metrics.spacingS)
                        values: PersonalizationConfig.keystoneLongLeading
                        options: PersonalizationConfig.keystoneLongItemOptions
                        zone: "leading"
                        dragCoordinator: longDragCoordinator
                        onToggled: itemId => PersonalizationConfig.toggleKeystoneLongItem(itemId, zone)
                        onRemoved: itemId => PersonalizationConfig.removeKeystoneLongItem(itemId)
                    }
                }

                SettingsRow {
                    id: longTrailingFieldRow
                    Layout.fillWidth: true
                    title: PersonalizationConfig.keystonePosition === "top" || PersonalizationConfig.keystonePosition === "bottom" ? I18n.tr("Right") : I18n.tr("Bottom")
                    trailing: SortableMultiSelectField {
                        id: longTrailingField
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: Math.max(0, longTrailingFieldRow.width - 96 - 3 * Metrics.spacingS)
                        values: PersonalizationConfig.keystoneLongTrailing
                        options: PersonalizationConfig.keystoneLongItemOptions
                        zone: "trailing"
                        dragCoordinator: longDragCoordinator
                        onToggled: itemId => PersonalizationConfig.toggleKeystoneLongItem(itemId, zone)
                        onRemoved: itemId => PersonalizationConfig.removeKeystoneLongItem(itemId)
                    }
                }
            }

            KeystoneSection {
                id: extraSearchSection0
                visible: KeyboardLockService.available
                title: extraSearchAnchor0.title
                SettingsSearchAnchor {
                    id: extraSearchAnchor0
                    target: extraSearchSection0
                    declaration: '{"id":"keystone.section.keyboard-indicators","route":"keystone","title":"Keyboard indicators","context":"KeystonePage","icon":"settings","aliases":[],"availability":"keyboard-lock"}'
                }
                iconName: "keyboard"

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Caps Lock changes")
                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneCapsLockOsd
                        Accessible.name: I18n.tr("Caps Lock changes")
                        onToggled: PersonalizationConfig.setKeystoneCapsLockOsd(checked)
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Num Lock changes")
                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneNumLockOsd
                        Accessible.name: I18n.tr("Num Lock changes")
                        onToggled: PersonalizationConfig.setKeystoneNumLockOsd(checked)
                    }
                }
            }

            KeystoneSection {
                id: extraSearchSection1
                title: extraSearchAnchor1.title
                SettingsSearchAnchor {
                    id: extraSearchAnchor1
                    target: extraSearchSection1
                    declaration: '{"id":"keystone.section.keyhole","route":"keystone","title":"Keyhole","context":"KeystonePage","icon":"settings","aliases":[]}'
                }
                iconName: "dashboard"

                SearchSelectSettingRow {
                    title: I18n.tr("Card")
                    closeOnAccept: true
                    options: PersonalizationConfig.keystoneKeyholeCardOptions
                    value: PersonalizationConfig.keystoneKeyholeCard
                    onAccepted: value => PersonalizationConfig.setKeystoneKeyholeCard(value)
                }
            }

            KeystoneSection {
                id: searchSection2
                title: searchAnchor2.title
                SettingsSearchAnchor {
                    id: searchAnchor2
                    target: searchSection2
                    declaration: '{"id":"keystone.section.horizontal-clock","route":"keystone","title":"Horizontal clock","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                }
                iconName: "schedule"

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(66, (width - 8) * 42 / 220 + 12)

                    HorizontalClockPreview {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 4
                        anchors.rightMargin: 4
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 6
                        anchors.bottomMargin: 6
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Hide date")

                    trailing: StyledSwitch {
                        checked: PersonalizationConfig.keystoneHideDate
                        Accessible.name: I18n.tr("Hide date")
                        onToggled: PersonalizationConfig.setKeystoneHideDate(checked)
                    }
                }

                SettingsActionRow {
                    Layout.fillWidth: true
                    iconName: "tune"
                    text: I18n.tr("Horizontal clock style")
                    description: I18n.tr("Font, digit positions, and colors")
                    trailingIconName: "chevron_right"
                    onClicked: root.openSection("horizontal-clock")
                }
            }

            KeystoneSection {
                id: searchSection3
                title: searchAnchor3.title
                SettingsSearchAnchor {
                    id: searchAnchor3
                    target: searchSection3
                    declaration: '{"id":"keystone.section.recording","route":"keystone","title":"Recording","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                }
                iconName: "video_camera_front"

                RecordingDirectoryField {
                    settingTitle: I18n.tr("Video recording")
                    settingKey: "recordingVideoDirectory"
                    value: UiPreferences.recordingVideoDirectory
                }

                RecordingDirectoryField {
                    settingTitle: I18n.tr("GIF recording")
                    settingKey: "recordingGifDirectory"
                    value: UiPreferences.recordingGifDirectory
                }

                RecordingDirectoryField {
                    settingTitle: I18n.tr("Microphone recording")
                    settingKey: "recordingMicrophoneDirectory"
                    value: UiPreferences.recordingMicrophoneDirectory
                }

                RecordingDirectoryField {
                    settingTitle: I18n.tr("System audio recording")
                    settingKey: "recordingSystemAudioDirectory"
                    value: UiPreferences.recordingSystemAudioDirectory
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 24
            }
        }
    }

    Loader {
        id: pageLoader
        onLoaded: SettingsBackend.retrySearch()

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: subpageHeader.bottom
        anchors.bottom: parent.bottom
        visible: root.currentSection !== "overview"
        source: {
            const route = SpotlightCatalog.route("keystone." + root.currentSection);
            return route ? Qt.resolvedUrl(route.source) : "";
        }
    }

    BarLayoutDragCoordinator {
        id: longDragCoordinator
        anchors.fill: parent
        z: 1001
        fields: [longLeadingField, longTrailingField]
        onDropped: (itemId, targetZone, targetIndex) => PersonalizationConfig.moveKeystoneLongItem(itemId, targetZone, targetIndex)
    }

    FilePickerWindow {
        id: directoryPicker

        parentModal: root.parentModal
        requiresParentWindow: true
        selectionMode: FilePickerWindow.Folders
        allowCurrentFolderSelection: true
        dialogTitle: I18n.tr("Save location")
        description: root.editingDirectoryField ? root.editingDirectoryField.settingTitle : ""
        nameFilters: []
        windowIconName: "folder_open"
        emptyStateText: I18n.tr("This folder is empty")
        selectionPrompt: I18n.tr("Choose folder")
        acceptLabel: I18n.tr("Choose")
        formatSummary: I18n.tr("Choose the current folder or a selected subfolder")
        onAccepted: function (path, isDirectory) {
            if (isDirectory && root.editingDirectoryKey !== "")
                root.saveDirectory(root.editingDirectoryKey, path, root.editingDirectoryField);

            root.editingDirectoryKey = "";
            root.editingDirectoryField = null;
        }
        onRejected: {
            root.editingDirectoryKey = "";
            root.editingDirectoryField = null;
        }
    }

    component RecordingDirectoryField: ColumnLayout {
        id: directorySetting

        property string settingTitle: ""
        property string settingKey: ""
        property string value: ""

        Layout.fillWidth: true
        Layout.leftMargin: Metrics.spacingS
        Layout.rightMargin: Metrics.spacingS
        spacing: Metrics.spacingXS

        Text {
            Layout.fillWidth: true
            text: directorySetting.settingTitle
            color: Appearance.colors.colOnSurface
            font.family: Typography.titleSmall.family
            font.pixelSize: Typography.titleSmall.pixelSize
            font.weight: Typography.titleSmall.weight
            elide: Text.ElideRight
        }

        MaterialFilledTextField {
            id: directoryField

            Layout.fillWidth: true
            labelText: I18n.tr("Save location")
            text: directorySetting.value
            trailingContentWidth: Metrics.touchTarget
            onAccepted: root.saveDirectory(directorySetting.settingKey, text, directoryField)
            onEditingFinished: root.saveDirectory(directorySetting.settingKey, text, directoryField)

            trailingContent: Component {
                IconButton {
                    anchors.centerIn: parent
                    iconName: "folder_open"
                    accessibleName: I18n.tr("Choose folder")
                    tooltipText: I18n.tr("Choose folder")
                    controlSize: Metrics.touchTarget
                    onClicked: root.openDirectoryPicker(directorySetting.settingKey, directoryField)
                }
            }
        }
    }

    component SearchSelectSettingRow: Item {
        id: selectRow

        property string title: ""
        property string description: ""
        property var options: []
        property string value: ""
        property string placeholder: ""
        property int fieldWidth: 240
        property bool closeOnAccept: true

        signal accepted(string value)

        Layout.fillWidth: true
        Layout.preferredHeight: Math.max(58, selectLabelColumn.implicitHeight + 16)

        RowLayout {
            anchors.fill: parent
            spacing: 16

            Column {
                id: selectLabelColumn

                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 3

                Text {
                    width: parent.width
                    text: selectRow.title
                    color: Appearance.colors.colOnSurface
                    font.family: Fonts.ui
                    font.pixelSize: Appearance.scaledFont(15)
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }

                Text {
                    width: parent.width
                    text: selectRow.description
                    color: Appearance.colors.colSubtext
                    font.family: Fonts.ui
                    font.pixelSize: Appearance.scaledFont(12)
                    wrapMode: Text.WordWrap
                }
            }

            SearchSelectMenuField {
                Layout.preferredWidth: selectRow.fieldWidth
                Layout.preferredHeight: 40
                Layout.alignment: Qt.AlignVCenter
                options: selectRow.options
                closeOnAccept: selectRow.closeOnAccept
                value: selectRow.value
                placeholder: selectRow.placeholder
                textRole: "label"
                valueRole: "value"
                onAccepted: value => {
                    return selectRow.accepted(value);
                }
            }
        }
    }
}
