import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import qs.Services
import qs.Common
import qs.Components
import qs.Widgets.common

Item {
    id: root

    required property SpotlightStyle style
    required property SpotlightCurrencyController currencyController
    required property SpotlightTemplateController templateController
    readonly property bool structuredInput: mode === "currency" || templateController.editing
    onStructuredInputChanged: Qt.callLater(root.focusInput)
    signal currencyExitRequested
    required property string mode
    required property bool modeRailExpanded
    required property int modeFocusIndex
    required property real railProgress
    required property real webProgress

    property alias text: searchInput.text
    property alias cursorPosition: searchInput.cursorPosition
    readonly property bool hasSelection: searchInput.selectionStart !== searchInput.selectionEnd
    property var pillEntries: []
    property var displayedPills: []
    property string pillError: ""
    property real errorStrength: 0
    function flashError() {
        errorPulse.restart();
    }
    onPillErrorChanged: if (!pillError.length) {
                            errorPulse.stop();
                            errorStrength = 0;
                        }
    SequentialAnimation {
        id: errorPulse
        NumberAnimation {
            target: root
            property: "errorStrength"
            from: 0
            to: 1
            duration: 90
        }
        PauseAnimation {
            duration: 500
        }
        NumberAnimation {
            target: root
            property: "errorStrength"
            to: 0
            duration: 240
        }
    }
    readonly property real pillWidth: Math.min(220, Math.max(64, root.mainWidth - 180),
                                               pillLabel.implicitWidth + pillLabel.anchors.leftMargin
                                               + pillLabel.anchors.rightMargin)
    signal pillClosed
    property string pillSignature: ""
    signal pillTransitionRequested(real target)
    function commitPills() {
        displayedPills = pillEntries;
    }
    onPillEntriesChanged: {
        const signature = pillEntries.map(entry => entry ? entry.id : "").join("|");
        if (signature === pillSignature)
            return;
        pillSignature = signature;
        if (!displayedPills.length || webProgress === 0) {
            commitPills();
            pillTransitionRequested(pillEntries.length ? 1 : 0);
        } else
            pillTransitionRequested(0);
    }
    onWebProgressChanged: {
        if (webProgress === 0 && !pillEntries.length)
            displayedPills = [];
    }
    property real requestedMainWidth: style.searchWidth
    readonly property real buttonDiameter: Math.min(style.modeButtonDiameter, Math.max(24, (requestedMainWidth
                                                                                            - 160) / style.modeButtonCount
                                                                                       - style.modeButtonGap))
    readonly property real expandedMainWidth: Math.max(0, requestedMainWidth - style.modeButtonCount * (
                                                           buttonDiameter + style.modeButtonGap))
    readonly property real stableMainLeft: (width - requestedMainWidth) / 2
    readonly property real mainCenterX: morphSurface.mainCenterX
    readonly property real mainWidth: morphSurface.mainWidth
    readonly property real mainLeft: stableMainLeft
    readonly property real mainRight: mainLeft + mainWidth
    readonly property real webEngineProgress: style.smoothstep((webProgress - 0.36) / 0.44)
    readonly property real webTextProgress: style.smoothstep((webProgress - 0.5) / 0.5)
    readonly property real pressDepth: pressDepthForProgress(webProgress)
    readonly property real pressScaleX: pressScaleXForProgress(webProgress)
    readonly property real pressScaleY: pressScaleYForProgress(webProgress)
    readonly property real pressShadowBlur: shadowBlurForProgress(webProgress)
    readonly property real pressShadowVerticalOffset: shadowVerticalOffsetForProgress(webProgress)
    readonly property bool inputActiveFocus: structuredInput ? currencyEditor.activeFocus :
                                                               searchInput.activeFocus
    readonly property var blurRegionItems: morphSurface.blurRegionItems

    // Qt also treats cursor/format-only input-method attributes as composing.
    // Fcitx5's Wayland commit can leave those attributes after preedit is empty;
    // only pending text should suspend Spotlight's key routing.
    readonly property bool inputComposing: structuredInput ? currencyEditor.composing :
                                                             searchInput.preeditText.length > 0
    signal releasedKey(var event)
    signal routedKey(var event)
    signal modeClicked(int index)
    signal searchRequested

    height: style.searchHeight + style.effectBleed * 2

    transform: Scale {
        origin.x: root.width / 2
        origin.y: root.height / 2
        xScale: root.pressScaleX
        yScale: root.pressScaleY
    }

    function pressDepthForProgress(progress) {
        if (progress <= 0.25)
            return style.smoothstep(progress / 0.25);
        if (progress <= 0.62)
            return 1 - style.smoothstep((progress - 0.25) / 0.37);
        return 0;
    }

    function pressScaleXForProgress(progress) {
        return 1 - 0.015 * pressDepthForProgress(progress);
    }

    function pressScaleYForProgress(progress) {
        return 1 - 0.055 * pressDepthForProgress(progress);
    }

    function shadowBlurForProgress(progress) {
        return style.shadowBlur * (1 - 0.28 * pressDepthForProgress(progress));
    }

    function shadowVerticalOffsetForProgress(progress) {
        return style.shadowVerticalOffset - 3 * pressDepthForProgress(progress);
    }

    function selectText(start, end) {
        searchInput.select(start, end);
    }

    function focusInput() {
        if (root.structuredInput)
            currencyEditor.focusSlot(false);
        else
            searchInput.forceActiveFocus();
    }

    function buttonCenterX(index) {
        return morphSurface.buttonCenterX(index);
    }

    function iconProgress(index) {
        return morphSurface.iconProgress(index);
    }

    SpotlightModeMorphSurface {
        id: morphSurface

        anchors.fill: parent
        railProgress: root.railProgress
        mainLeft: root.stableMainLeft
        collapsedMainWidth: root.requestedMainWidth
        expandedMainWidth: root.expandedMainWidth
        shapeCenterY: height / 2
        shapeHeight: root.style.searchHeight
        buttonDiameter: root.buttonDiameter
        buttonGap: root.style.modeButtonGap
        blurEdgeInset: root.style.blurEdgeInset
        surfaceColor: root.style.surfaceColor
        shadowColor: root.style.shadowColor
        shadowBlur: root.pressShadowBlur
        shadowVerticalOffset: root.pressShadowVerticalOffset
    }

    Item {
        id: mainContent

        x: root.mainLeft
        y: root.style.effectBleed
        width: root.mainWidth
        height: root.style.searchHeight
        clip: true

        MaterialSymbol {
            id: searchIcon

            x: root.style.searchHorizontalPadding
            anchors.verticalCenter: parent.verticalCenter
            width: root.style.searchIconSize
            height: width
            text: root.mode === "commands" ? "chevron_right" : "search"
            iconSize: root.style.searchIconSize
            color: Appearance.colors.colOnSurfaceVariant
        }
        MouseArea {
            id: returnSearchMouse
            x: searchIcon.x - 8
            y: searchIcon.y - 8
            width: searchIcon.width + 16
            height: searchIcon.height + 16
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Search (Ctrl+0)")
            onClicked: root.searchRequested()
            Accessible.onPressAction: root.searchRequested()
            StyledToolTip {
                extraVisibleCondition: returnSearchMouse.containsMouse
                text: qsTr("Search (Ctrl+0)")
            }
        }

        Rectangle {
            id: enginePill

            x: searchIcon.x + searchIcon.width + 12
            anchors.verticalCenter: parent.verticalCenter
            width: root.pillWidth * root.webEngineProgress
            height: root.style.enginePillHeight
            radius: Appearance.rounding.full
            color: Appearance.colors.colSecondaryContainer
            opacity: root.webEngineProgress
            scale: 0.92 + 0.08 * root.webEngineProgress
            clip: true

            Text {
                id: pillLabel
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: parent.right
                anchors.rightMargin: 30
                anchors.verticalCenter: parent.verticalCenter
                text: root.displayedPills.map(entry => entry && entry.value === "web"
                                                       ? SpotlightSearchService.searchEngineName :
                                                         SpotlightCatalog.commandTitle(entry)).join(" · ")
                textFormat: Text.PlainText
                elide: Text.ElideRight
                color: Appearance.colors.colOnSecondaryContainer
                font.family: Fonts.ui
                font.pixelSize: 14
                font.weight: Font.DemiBold
                opacity: root.webEngineProgress
            }
        }

        MouseArea {
            id: pillClose
            x: enginePill.x + Math.max(0, enginePill.width - 30)
            y: enginePill.y
            width: 30
            height: enginePill.height
            enabled: root.pillEntries.length > 0
            visible: root.webEngineProgress > 0.01
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Return to previous context (Backspace)")
            onClicked: {
                root.pillClosed();
                root.focusInput();
            }
            MaterialSymbol {
                anchors.centerIn: parent
                text: "close"
                iconSize: 16
                color: Appearance.colors.colOnSecondaryContainer
                opacity: root.webEngineProgress
            }
            StyledToolTip {
                extraVisibleCondition: pillClose.containsMouse
                text: qsTr("Return to previous context (Backspace)")
            }
        }

        Item {
            id: inputArea

            x: searchIcon.x + searchIcon.width + 14 + (root.pillWidth + 10) * root.webTextProgress
            width: Math.max(0, parent.width - x - root.style.searchHorizontalPadding)
            height: parent.height

            SpotlightConversionEditor {
                id: currencyEditor
                anchors.fill: parent
                visible: root.structuredInput
                enabled: visible
                controller: root.mode === "time" ? root.templateController : root.currencyController
                timeMode: root.mode === "time"
                style: root.style
                railExpanded: root.modeRailExpanded
                onRoutedKey: event => root.routedKey(event)
                onReleasedKey: event => root.releasedKey(event)
                onExitRequested: root.currencyExitRequested()
            }

            Text {
                anchors.fill: parent
                text: {
                    if (root.mode === "commands")
                        return qsTr("Search commands");
                    if (root.mode === "search")
                        return qsTr("Search");
                    if (root.mode === "files")
                        return qsTr("Search files and folders");
                    if (root.mode === "clipboard")
                        return qsTr("Search clipboard history");
                    if (root.mode === "wallpapers")
                        return qsTr("Search wallpapers");
                    return qsTr("Search apps");
                }
                color: Appearance.applyAlpha(Appearance.colors.colOnSurfaceVariant, 0.72)
                font.family: Fonts.ui
                font.pixelSize: 20
                verticalAlignment: Text.AlignVCenter
                opacity: !root.structuredInput && searchInput.text.length === 0 ? 1 - root.webTextProgress : 0
                elide: Text.ElideRight
            }

            Text {
                anchors.fill: parent
                text: root.mode === "calculator" ? qsTr("Enter an expression") : root.mode === "currency"
                                                   ? qsTr("Amount and currency") : root.mode === "time" ? qsTr(
                                                                                                              "Choose a time conversion template") :
                                                                                                          root.mode
                                                                                                          === "settings"
                                                                                                          ? qsTr("Search settings") :
                                                                                                            root.mode
                                                                                                            === "actions"
                                                                                                            ? qsTr("Search actions") :
                                                                                                              root.mode
                                                                                                              === "web"
                                                                                                              ? qsTr("Search the web") :
                                                                                                                qsTr("Search")
                color: Appearance.applyAlpha(Appearance.colors.colOnSurfaceVariant, 0.72)
                font.family: Fonts.ui
                font.pixelSize: 20
                verticalAlignment: Text.AlignVCenter
                opacity: !root.structuredInput && searchInput.text.length === 0 ? root.webTextProgress : 0
                elide: Text.ElideRight
            }

            TextInput {
                id: searchInput
                visible: !root.structuredInput
                enabled: visible

                anchors.fill: parent
                color: Qt.tint(Appearance.colors.colOnSurface, Appearance.applyAlpha(
                                   Appearance.colors.colError, root.errorStrength))
                selectionColor: Appearance.colors.colPrimary
                selectedTextColor: Appearance.colors.colOnPrimary
                font.family: Fonts.ui
                font.pixelSize: 20
                verticalAlignment: TextInput.AlignVCenter
                selectByMouse: true
                clip: true
                focus: true
                activeFocusOnTab: false

                Accessible.name: root.mode === "web" ? qsTr("Web search") : qsTr("Spotlight search")
                Accessible.role: Accessible.EditableText
                Accessible.description: root.pillError || qsTr("Tab to show and cycle modes")
                HoverHandler {
                    id: inputHover
                }
                StyledToolTip {
                    extraVisibleCondition: inputHover.hovered && root.pillError.length > 0
                    text: root.pillError
                }

                Keys.priority: Keys.BeforeItem
                Keys.onPressed: event => root.routedKey(event)
                Keys.onReleased: event => root.releasedKey(event)
            }
        }

        MouseArea {
            anchors.fill: parent
            z: -1
            acceptedButtons: Qt.LeftButton
            propagateComposedEvents: true
            onPressed: mouse => {
                root.focusInput();
                mouse.accepted = false;
            }
        }
    }

    Repeater {
        model: [
            {
                icon: "grid_view",
                label: qsTr("Apply")
            },
            {
                icon: "image",
                label: qsTr("Wallpaper")
            },
            {
                icon: "content_paste",
                label: qsTr("Clipboard")
            },
            {
                icon: "draft",
                label: qsTr("Files")
            }
        ]

        delegate: Item {
            id: modeButton

            required property int index
            required property var modelData
            readonly property real reveal: root.iconProgress(index)
            readonly property bool logicalFocus: root.modeRailExpanded && root.modeFocusIndex === index
            readonly property bool iconSelected: root.modeRailExpanded && root.modeFocusIndex >= 0
                                                 ? logicalFocus : activeMode
            readonly property bool activeMode: (index === 0 && root.mode === "apps") || (index === 1
                                                                                         && root.mode
                                                                                         === "wallpapers") || (
                                                   index === 2 && root.mode === "clipboard") || (index === 3
                                                                                                 && root.mode
                                                                                                 === "files")

            x: root.buttonCenterX(index) - root.buttonDiameter / 2
            y: root.height / 2 - root.buttonDiameter / 2
            width: root.buttonDiameter
            height: width
            opacity: reveal
            scale: 0.9 + reveal * 0.1

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: modeMouse.pressed || modeMouse.containsMouse ? Appearance.applyAlpha(
                                                                          root.style.hoverColor, 0.42) :
                                                                      "transparent"
            }

            MaterialSymbol {
                anchors.centerIn: parent
                text: modeButton.modelData.icon
                iconSize: 23
                // Selection changes only FILL, keeping font metrics and the
                // centered icon box stable across outlined and filled states.
                width: iconSize
                height: iconSize
                font.weight: Font.Normal
                fill: modeButton.iconSelected ? 1 : 0
                color: Appearance.colors.colOnSurfaceVariant
            }

            MouseArea {
                id: modeMouse

                anchors.fill: parent
                enabled: modeButton.reveal > 0.55
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                Accessible.name: modeButton.modelData.label
                Accessible.role: Accessible.Button

                onClicked: {
                    root.modeClicked(modeButton.index);
                    root.focusInput();
                }
            }

            StyledToolTip {
                extraVisibleCondition: modeMouse.containsMouse && modeMouse.enabled
                text: qsTr("%1 (Ctrl+%2)").arg(modeButton.modelData.label).arg(modeButton.index + 1)
            }
        }
    }
}
