import QtQuick
import QtQuick.Controls
import qs.commons
import qs.ui
import qs.commons.i18n

// Pill search bar (Caelestia Nexus SearchBar): one fully rounded capsule on
// the surface-container-lowest fill — no border, no focus outline — with a
// leading search glyph, a trailing clear button that fades in while there is
// text, and a press overlay while the field is not yet focused. Root is the
// TextField: consumers bind placeholderText and read text directly.
TextField {
    id: root

    // Caelestia rhythm: vertical padding 16, search glyph inset 20, clear
    // glyph inset 12, content inset 12 beyond the glyphs.
    topPadding: NexusStyle.padding.large
    bottomPadding: NexusStyle.padding.large
    leftPadding: searchIcon.width + searchIcon.anchors.leftMargin + NexusStyle.spacing.medium
    rightPadding: clearButton.width + clearButton.anchors.rightMargin + NexusStyle.spacing.medium

    implicitHeight: contentHeight + topPadding + bottomPadding

    color: Appearance.m3colors.m3onSurface
    selectionColor: Appearance.applyAlpha(Appearance.m3colors.m3primary, 0.4)
    selectedTextColor: color
    placeholderTextColor: Appearance.m3colors.m3onSurfaceVariant
    verticalAlignment: TextInput.AlignVCenter
    selectByMouse: true
    font.family: Fonts.ui
    font.pixelSize: NexusStyle.font.bodyLarge

    background: Rectangle {
        radius: NexusStyle.rounding.full
        color: Appearance.m3colors.m3surfaceContainerLowest

        Behavior on color {
            ColorAnimation {
                duration: Appearance.animation.expressiveDefaultEffects.duration
                easing.type: Appearance.animation.expressiveDefaultEffects.type
                easing.bezierCurve: Appearance.animation.expressiveDefaultEffects.bezierCurve
            }
        }

        // Press overlay while the field is unfocused; once focused the native
        // caret takes over and the overlay stays out of the way.
        StateLayer {
            anchors.fill: parent
            layerRadius: parent.radius
            color: Appearance.m3colors.m3onSurface
            pressed: !root.activeFocus && tapHandler.pressed
            hovered: !root.activeFocus && hoverHandler.hovered
        }
    }

    TapHandler {
        id: tapHandler

        onTapped: root.forceActiveFocus(Qt.MouseFocusReason)
    }

    HoverHandler {
        id: hoverHandler
    }

    MaterialSymbol {
        id: searchIcon

        z: 1
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.largeIncreased
        iconSize: NexusStyle.icon.medium * 0.9
        text: "search"
        color: Appearance.m3colors.m3onSurfaceVariant
    }

    IconButton {
        id: clearButton

        z: 1
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: NexusStyle.padding.medium
        width: NexusStyle.icon.small + NexusStyle.padding.small * 2
        height: NexusStyle.icon.small + NexusStyle.padding.small * 2
        controlSize: NexusStyle.icon.small + NexusStyle.padding.small * 2
        iconSize: NexusStyle.icon.small
        iconName: "clear"
        accessibleName: I18n.tr("Clear")
        showTooltip: false
        enabled: root.text.length > 0
        opacity: enabled ? 1 : 0

        Behavior on opacity {
            NumberAnimation {
                duration: Appearance.animation.expressiveFastEffects.duration
                easing.type: Appearance.animation.expressiveFastEffects.type
                easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
            }
        }

        onClicked: {
            root.clear();
            root.forceActiveFocus();
        }
    }
}
