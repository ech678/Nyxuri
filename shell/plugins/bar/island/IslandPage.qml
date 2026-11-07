pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.ui

// Island page shell (T3 M4): overview renders as a NexusPageBase over the
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
        if (SettingsSearch.searchTarget && !SettingsSearch.applyingSearch && searchRequestSerial
                === SettingsSearch.searchSerial)
            SettingsSearch.cancelSearch();
        SettingsSearch.retrySearch();
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
        isSubPage: true
        title: SpotlightCatalog.title("bar.island")

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

                // Island style
                PreferenceHeader {
                    first: true
                    text: I18n.tr("Island style")
                }

                PreferenceToggle {
                    id: floatingToggle

                    first: true
                    text: I18n.tr("Floating")
                    checked: PersonalizationConfig.islandOverlay
                    onToggled: PersonalizationConfig.setValue("islandOverlay", checked)

                    SettingsSearchAnchor {
                        id: searchAnchor0
                        target: floatingToggle
                        anchorId: "bar.island.section.island-style"
                    }
                }

                PreferenceSelect {
                    label: I18n.tr("Style")
                    model: PersonalizationConfig.islandStyles
                    currentValue: PersonalizationConfig.islandStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandStyle(value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Screen edge")
                    model: PersonalizationConfig.edgePositions
                    currentValue: PersonalizationConfig.islandPosition
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandPosition(String(value))
                }

                // Mouse actions
                PreferenceHeader {
                    text: I18n.tr("Mouse actions")
                }

                PreferenceSelect {
                    id: hoverSelect

                    first: true
                    label: I18n.tr("Hover")
                    model: PersonalizationConfig.availableIslandHoverActionOptions
                    currentValue: PersonalizationConfig.effectiveIslandHoverAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandAction("hover", value)

                    SettingsSearchAnchor {
                        id: searchAnchor1
                        target: hoverSelect
                        anchorId: "bar.island.section.mouse-actions"
                    }
                }

                PreferenceSlider {
                    label: I18n.tr("Hover open delay")
                    enabled: PersonalizationConfig.effectiveIslandHoverAction !== "none"
                    valueLabel: Math.round(PersonalizationConfig.islandHoverOpenDelay) + I18n.tr(" ms")
                    value: PersonalizationConfig.islandHoverOpenDelay
                    from: 0
                    to: 500
                    stepSize: 25
                    onMoved: value => PersonalizationConfig.setIslandHoverOpenDelay(Math.round(value))
                }

                PreferenceSlider {
                    label: I18n.tr("Hover close delay")
                    enabled: PersonalizationConfig.effectiveIslandHoverAction !== "none"
                    valueLabel: Math.round(PersonalizationConfig.islandHoverCloseDelay) + I18n.tr(" ms")
                    value: PersonalizationConfig.islandHoverCloseDelay
                    from: 0
                    to: 600
                    stepSize: 25
                    onMoved: value => PersonalizationConfig.setIslandHoverCloseDelay(Math.round(value))
                }

                PreferenceSelect {
                    label: I18n.tr("Left click")
                    model: PersonalizationConfig.islandActionOptions
                    currentValue: PersonalizationConfig.islandLeftClickAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandAction("left", value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Middle click")
                    model: PersonalizationConfig.islandActionOptions
                    currentValue: PersonalizationConfig.islandMiddleClickAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandAction("middle", value)
                }

                // Media controls
                PreferenceHeader {
                    text: I18n.tr("Media controls")
                }

                PreferenceSelect {
                    id: progressSelect

                    first: true
                    label: I18n.tr("Progress bar")
                    model: PersonalizationConfig.islandMediaProgressOptions
                    currentValue: PersonalizationConfig.islandMediaProgressStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandMediaProgressStyle(value)

                    SettingsSearchAnchor {
                        id: mediaSearchAnchor
                        target: progressSelect
                        anchorId: "bar.island.section.media-controls"
                    }
                }

                PreferenceSelect {
                    label: I18n.tr("Cover style")
                    model: PersonalizationConfig.islandMediaCoverOptions
                    currentValue: PersonalizationConfig.islandMediaCoverStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandMediaCoverStyle(value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Colors")
                    model: PersonalizationConfig.islandMediaColorOptions
                    currentValue: PersonalizationConfig.islandMediaColorStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandMediaColorStyle(value)
                }

                // Status items (long bar only)
                PreferenceHeader {
                    visible: PersonalizationConfig.islandStyle === "long"
                    text: I18n.tr("Status items")
                }

                PreferenceToggle {
                    id: longNamesToggle

                    visible: PersonalizationConfig.islandStyle === "long"
                    first: true
                    text: I18n.tr("Show device names")
                    checked: PersonalizationConfig.keystoneLongShowNames
                    onToggled: PersonalizationConfig.setKeystoneLongShowNames(checked)
                }

                PreferenceToggle {
                    visible: PersonalizationConfig.islandStyle === "long"
                    text: I18n.tr("Show system monitor values")
                    checked: PersonalizationConfig.keystoneLongShowMonitorValues
                    onToggled: PersonalizationConfig.setKeystoneLongShowMonitorValues(checked)
                }

                PreferenceToggle {
                    visible: PersonalizationConfig.islandStyle === "long"
                    text: I18n.tr("Show numeric values")
                    checked: PersonalizationConfig.keystoneLongShowValues
                    onToggled: PersonalizationConfig.setKeystoneLongShowValues(checked)
                }

                ConnectedRect {
                    id: longLeadingZoneRow

                    visible: PersonalizationConfig.islandStyle === "long"
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

                            text: PersonalizationConfig.islandPosition === "top"
                                  || PersonalizationConfig.islandPosition === "bottom" ? I18n.tr("Left") :
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

                    visible: PersonalizationConfig.islandStyle === "long"
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

                            text: PersonalizationConfig.islandPosition === "top"
                                  || PersonalizationConfig.islandPosition === "bottom" ? I18n.tr("Right") :
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
                    checked: PersonalizationConfig.islandCapsLockOsd
                    onToggled: PersonalizationConfig.setIslandCapsLockOsd(checked)

                    SettingsSearchAnchor {
                        id: extraSearchAnchor0
                        target: capsLockToggle
                        anchorId: "bar.island.section.keyboard-indicators"
                    }
                }

                PreferenceToggle {
                    visible: KeyboardLockService.available
                    last: true
                    text: I18n.tr("Num Lock changes")
                    checked: PersonalizationConfig.islandNumLockOsd
                    onToggled: PersonalizationConfig.setIslandNumLockOsd(checked)
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
                    model: PersonalizationConfig.islandKeyholeCardOptions
                    currentValue: PersonalizationConfig.islandKeyholeCard
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandKeyholeCard(value)

                    SettingsSearchAnchor {
                        id: extraSearchAnchor1
                        target: keyholeCardSelect
                        anchorId: "bar.island.section.keyhole"
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
                        anchorId: "bar.island.section.horizontal-clock"
                    }
                }

                PreferenceToggle {
                    text: I18n.tr("Hide date")
                    checked: PersonalizationConfig.islandHideDate
                    onToggled: PersonalizationConfig.setIslandHideDate(checked)
                }

                PreferenceAction {
                    last: true
                    icon: "tune"
                    text: I18n.tr("Horizontal clock style")
                    subtext: I18n.tr("Font, digit positions, and colors")
                    onClicked: root.openSection("island-clock")
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
                        anchorId: "bar.island.section.recording"
                    }
                }
            }

            LayoutDragCoordinator {
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
            SettingsSearch.retrySearch();
            if (item && "parentModal" in item)
                item.parentModal = Qt.binding(() => root.parentModal);
            if (item && item.backRequested !== undefined)
                item.backRequested.connect(root.showOverview);
        }

        anchors.fill: parent
        visible: root.currentSection !== "overview"
        source: {
            const route = SpotlightCatalog.route("bar." + root.currentSection);
            return route && route.sourceUrl ? route.sourceUrl : "";
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
