pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Keystone page shell (T3 M4): overview renders as a NexusPageBase over the
// M1 atom suite; the horizontal-clock subpage loads through the routed Loader
// and renders its own subpage title + back arrow, so the pre-M4 external
// subpage header is gone. Directory pickers and the long-bar drag overlay
// ride inside the page content — a root-level child would break the
// single-content-child contract of the Nexus scaffold.
Item {
    id: root

    readonly property bool rendersPageTitle: true

    property int searchRequestSerial: -1
    readonly property var searchLeaf: currentSection === "overview" ? overviewPage.flickable :
                                                                      pageLoader.item ? (
                                                                                            pageLoader.item.searchLeaf
                                                                                            || pageLoader.item) :
                                                                                        root
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
        return typeof pageLoader.item.openSearchPath === "function" ? pageLoader.item.openSearchPath(
                                                                          path.slice(1), serial) : "ready";
    }

    property var parentModal: null
    onCurrentSectionChanged: {
        if (SettingsBackend.searchTarget && !SettingsBackend.applyingSearch && searchRequestSerial
                === SettingsBackend.searchSerial)
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

    NexusPageBase {
        id: overviewPage

        anchors.fill: parent
        visible: root.currentSection === "overview"
        title: SpotlightCatalog.title("keystone")

        Item {
            id: overviewContent

            width: parent.width
            implicitHeight: overviewColumn.implicitHeight

            ColumnLayout {
                id: overviewColumn

                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                width: overviewPage.cappedWidth
                spacing: NexusStyle.padding.extraSmall / 2

                // Keystone style
                PreferenceHeader {
                    first: true
                    text: I18n.tr("Keystone style")
                }

                PreferenceToggle {
                    id: floatingToggle

                    first: true
                    text: I18n.tr("Floating")
                    checked: PersonalizationConfig.keystoneOverlay
                    onToggled: PersonalizationConfig.setValue("keystoneOverlay", checked)

                    SettingsSearchAnchor {
                        id: searchAnchor0
                        target: floatingToggle
                        declaration:
                            '{"id":"keystone.section.keystone-style","route":"keystone","title":"Keystone style","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                    }
                }

                PreferenceSelect {
                    label: I18n.tr("Style")
                    model: PersonalizationConfig.keystoneStyles
                    currentValue: PersonalizationConfig.keystoneStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneStyle(value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Screen edge")
                    model: PersonalizationConfig.edgePositions
                    currentValue: PersonalizationConfig.keystonePosition
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystonePosition(String(value))
                }

                // Mouse actions
                PreferenceHeader {
                    text: I18n.tr("Mouse actions")
                }

                PreferenceSelect {
                    id: hoverSelect

                    first: true
                    label: I18n.tr("Hover")
                    model: PersonalizationConfig.availableKeystoneHoverActionOptions
                    currentValue: PersonalizationConfig.effectiveKeystoneHoverAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneAction("hover", value)

                    SettingsSearchAnchor {
                        id: searchAnchor1
                        target: hoverSelect
                        declaration:
                            '{"id":"keystone.section.mouse-actions","route":"keystone","title":"Mouse actions","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                    }
                }

                PreferenceSlider {
                    label: I18n.tr("Hover open delay")
                    enabled: PersonalizationConfig.effectiveKeystoneHoverAction !== "none"
                    valueLabel: Math.round(PersonalizationConfig.keystoneHoverOpenDelay) + I18n.tr(" ms")
                    value: PersonalizationConfig.keystoneHoverOpenDelay
                    from: 0
                    to: 500
                    stepSize: 25
                    onMoved: value => PersonalizationConfig.setKeystoneHoverOpenDelay(Math.round(value))
                }

                PreferenceSlider {
                    label: I18n.tr("Hover close delay")
                    enabled: PersonalizationConfig.effectiveKeystoneHoverAction !== "none"
                    valueLabel: Math.round(PersonalizationConfig.keystoneHoverCloseDelay) + I18n.tr(" ms")
                    value: PersonalizationConfig.keystoneHoverCloseDelay
                    from: 0
                    to: 600
                    stepSize: 25
                    onMoved: value => PersonalizationConfig.setKeystoneHoverCloseDelay(Math.round(value))
                }

                PreferenceSelect {
                    label: I18n.tr("Left click")
                    model: PersonalizationConfig.keystoneActionOptions
                    currentValue: PersonalizationConfig.keystoneLeftClickAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneAction("left", value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Middle click")
                    model: PersonalizationConfig.keystoneActionOptions
                    currentValue: PersonalizationConfig.keystoneMiddleClickAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneAction("middle", value)
                }

                // Media controls
                PreferenceHeader {
                    text: I18n.tr("Media controls")
                }

                PreferenceSelect {
                    id: progressSelect

                    first: true
                    label: I18n.tr("Progress bar")
                    model: PersonalizationConfig.keystoneMediaProgressOptions
                    currentValue: PersonalizationConfig.keystoneMediaProgressStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneMediaProgressStyle(value)

                    SettingsSearchAnchor {
                        id: mediaSearchAnchor
                        target: progressSelect
                        declaration:
                            '{"id":"keystone.section.media-controls","route":"keystone","title":"Media controls","context":"KeystonePage","icon":"music_note","aliases":[]}'
                    }
                }

                PreferenceSelect {
                    label: I18n.tr("Cover style")
                    model: PersonalizationConfig.keystoneMediaCoverOptions
                    currentValue: PersonalizationConfig.keystoneMediaCoverStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneMediaCoverStyle(value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Colors")
                    model: PersonalizationConfig.keystoneMediaColorOptions
                    currentValue: PersonalizationConfig.keystoneMediaColorStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneMediaColorStyle(value)
                }

                // Status items (long bar only)
                PreferenceHeader {
                    visible: PersonalizationConfig.keystoneStyle === "long"
                    text: I18n.tr("Status items")
                }

                PreferenceToggle {
                    id: longNamesToggle

                    visible: PersonalizationConfig.keystoneStyle === "long"
                    first: true
                    text: I18n.tr("Show device names")
                    checked: PersonalizationConfig.keystoneLongShowNames
                    onToggled: PersonalizationConfig.setKeystoneLongShowNames(checked)
                }

                PreferenceToggle {
                    visible: PersonalizationConfig.keystoneStyle === "long"
                    text: I18n.tr("Show system monitor values")
                    checked: PersonalizationConfig.keystoneLongShowMonitorValues
                    onToggled: PersonalizationConfig.setKeystoneLongShowMonitorValues(checked)
                }

                PreferenceToggle {
                    visible: PersonalizationConfig.keystoneStyle === "long"
                    text: I18n.tr("Show numeric values")
                    checked: PersonalizationConfig.keystoneLongShowValues
                    onToggled: PersonalizationConfig.setKeystoneLongShowValues(checked)
                }

                ConnectedRect {
                    id: longLeadingZoneRow

                    visible: PersonalizationConfig.keystoneStyle === "long"
                    Layout.fillWidth: true
                    implicitHeight: Math.max(longLeadingLabel.implicitHeight,
                                             longLeadingField.implicitHeight) + NexusStyle.padding.medium * 2

                    RowLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.largeIncreased
                        anchors.rightMargin: NexusStyle.padding.largeIncreased
                        spacing: NexusStyle.padding.small

                        StyledText {
                            id: longLeadingLabel

                            text: PersonalizationConfig.keystonePosition === "top"
                                  || PersonalizationConfig.keystonePosition === "bottom" ? I18n.tr("Left") :
                                                                                           I18n.tr("Top")
                            color: Appearance.m3colors.m3onSurface
                            font.pixelSize: NexusStyle.font.bodyMedium
                        }

                        SortableMultiSelectField {
                            id: longLeadingField

                            Layout.fillWidth: true
                            values: PersonalizationConfig.keystoneLongLeading
                            options: PersonalizationConfig.keystoneLongItemOptions
                            zone: "leading"
                            dragCoordinator: longDragCoordinator
                            onToggled: itemId => PersonalizationConfig.toggleKeystoneLongItem(itemId, zone)
                            onRemoved: itemId => PersonalizationConfig.removeKeystoneLongItem(itemId)
                        }
                    }
                }

                ConnectedRect {
                    id: longTrailingZoneRow

                    visible: PersonalizationConfig.keystoneStyle === "long"
                    last: true
                    Layout.fillWidth: true
                    implicitHeight: Math.max(longTrailingLabel.implicitHeight,
                                             longTrailingField.implicitHeight) + NexusStyle.padding.medium * 2

                    RowLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.largeIncreased
                        anchors.rightMargin: NexusStyle.padding.largeIncreased
                        spacing: NexusStyle.padding.small

                        StyledText {
                            id: longTrailingLabel

                            text: PersonalizationConfig.keystonePosition === "top"
                                  || PersonalizationConfig.keystonePosition === "bottom" ? I18n.tr("Right") :
                                                                                           I18n.tr("Bottom")
                            color: Appearance.m3colors.m3onSurface
                            font.pixelSize: NexusStyle.font.bodyMedium
                        }

                        SortableMultiSelectField {
                            id: longTrailingField

                            Layout.fillWidth: true
                            values: PersonalizationConfig.keystoneLongTrailing
                            options: PersonalizationConfig.keystoneLongItemOptions
                            zone: "trailing"
                            dragCoordinator: longDragCoordinator
                            onToggled: itemId => PersonalizationConfig.toggleKeystoneLongItem(itemId, zone)
                            onRemoved: itemId => PersonalizationConfig.removeKeystoneLongItem(itemId)
                        }
                    }
                }

                // Keyboard indicators
                PreferenceHeader {
                    visible: KeyboardLockService.available
                    text: I18n.tr("Keyboard indicators")
                }

                PreferenceToggle {
                    id: capsLockToggle

                    visible: KeyboardLockService.available
                    first: true
                    text: I18n.tr("Caps Lock changes")
                    checked: PersonalizationConfig.keystoneCapsLockOsd
                    onToggled: PersonalizationConfig.setKeystoneCapsLockOsd(checked)

                    SettingsSearchAnchor {
                        id: extraSearchAnchor0
                        target: capsLockToggle
                        declaration:
                            '{"id":"keystone.section.keyboard-indicators","route":"keystone","title":"Keyboard indicators","context":"KeystonePage","icon":"settings","aliases":[],"availability":"keyboard-lock"}'
                    }
                }

                PreferenceToggle {
                    visible: KeyboardLockService.available
                    last: true
                    text: I18n.tr("Num Lock changes")
                    checked: PersonalizationConfig.keystoneNumLockOsd
                    onToggled: PersonalizationConfig.setKeystoneNumLockOsd(checked)
                }

                // Keyhole
                PreferenceHeader {
                    text: I18n.tr("Keyhole")
                }

                PreferenceSelect {
                    id: keyholeCardSelect

                    first: true
                    last: true
                    label: I18n.tr("Card")
                    model: PersonalizationConfig.keystoneKeyholeCardOptions
                    currentValue: PersonalizationConfig.keystoneKeyholeCard
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setKeystoneKeyholeCard(value)

                    SettingsSearchAnchor {
                        id: extraSearchAnchor1
                        target: keyholeCardSelect
                        declaration:
                            '{"id":"keystone.section.keyhole","route":"keystone","title":"Keyhole","context":"KeystonePage","icon":"settings","aliases":[]}'
                    }
                }

                // Horizontal clock
                PreferenceHeader {
                    text: I18n.tr("Horizontal clock")
                }

                ConnectedRect {
                    id: clockPreviewCard

                    first: true
                    Layout.fillWidth: true
                    implicitHeight: clockPreview.implicitHeight + NexusStyle.padding.medium * 2

                    HorizontalClockPreview {
                        id: clockPreview

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.small
                        anchors.rightMargin: NexusStyle.padding.small
                        implicitHeight: Math.max(42, width * 42 / 220)
                    }

                    SettingsSearchAnchor {
                        id: searchAnchor2
                        target: clockPreviewCard
                        declaration:
                            '{"id":"keystone.section.horizontal-clock","route":"keystone","title":"Horizontal clock","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                    }
                }

                PreferenceToggle {
                    text: I18n.tr("Hide date")
                    checked: PersonalizationConfig.keystoneHideDate
                    onToggled: PersonalizationConfig.setKeystoneHideDate(checked)
                }

                PreferenceAction {
                    last: true
                    icon: "tune"
                    text: I18n.tr("Horizontal clock style")
                    subtext: I18n.tr("Font, digit positions, and colors")
                    onClicked: root.openSection("horizontal-clock")
                }

                // Recording
                PreferenceHeader {
                    text: I18n.tr("Recording")
                }

                ConnectedRect {
                    id: recordingCard

                    first: true
                    last: true
                    Layout.fillWidth: true
                    implicitHeight: recordingColumn.implicitHeight + NexusStyle.padding.medium * 2

                    ColumnLayout {
                        id: recordingColumn

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.largeIncreased
                        anchors.rightMargin: NexusStyle.padding.largeIncreased
                        spacing: NexusStyle.padding.medium

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

                    SettingsSearchAnchor {
                        id: searchAnchor3
                        target: recordingCard
                        declaration:
                            '{"id":"keystone.section.recording","route":"keystone","title":"Recording","context":"KeystonePage","icon":"toggle_off","aliases":[]}'
                    }
                }
            }

            BarLayoutDragCoordinator {
                id: longDragCoordinator

                anchors.fill: parent
                z: 1001
                fields: [longLeadingField, longTrailingField]
                onDropped: (itemId, targetZone, targetIndex) => PersonalizationConfig.moveKeystoneLongItem(
                                                                    itemId, targetZone, targetIndex)
            }
        }
    }

    Loader {
        id: pageLoader

        onLoaded: {
            SettingsBackend.retrySearch();
            if (item && "parentModal" in item)
                item.parentModal = Qt.binding(() => root.parentModal);
            if (item && item.backRequested !== undefined)
                item.backRequested.connect(root.showOverview);
        }

        anchors.fill: parent
        visible: root.currentSection !== "overview"
        source: {
            const route = SpotlightCatalog.route("keystone." + root.currentSection);
            return route ? Qt.resolvedUrl(route.source) : "";
        }
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
        spacing: NexusStyle.padding.extraSmall

        StyledText {
            Layout.fillWidth: true
            text: directorySetting.settingTitle
            color: Appearance.m3colors.m3onSurface
            font.pixelSize: NexusStyle.font.bodyMedium
            elide: Text.ElideRight
        }

        MaterialFilledTextField {
            id: directoryField

            Layout.fillWidth: true
            labelText: I18n.tr("Save location")
            text: directorySetting.value
            trailingContentWidth: NexusStyle.icon.medium + NexusStyle.padding.small * 2
            onAccepted: root.saveDirectory(directorySetting.settingKey, text, directoryField)
            onEditingFinished: root.saveDirectory(directorySetting.settingKey, text, directoryField)

            trailingContent: Component {
                IconButton {
                    anchors.centerIn: parent
                    iconName: "folder_open"
                    accessibleName: I18n.tr("Choose folder")
                    tooltipText: I18n.tr("Choose folder")
                    controlSize: NexusStyle.icon.medium + NexusStyle.padding.small * 2
                    iconSize: NexusStyle.icon.medium
                    onClicked: root.openDirectoryPicker(directorySetting.settingKey, directoryField)
                }
            }
        }
    }
}
