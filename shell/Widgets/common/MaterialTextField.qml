import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import qs.Common

// Keep the Material implementation responsible for the outlined container and
// floating label. In particular, its label position, scale, and outline notch
// share one geometry calculation, so the transition cannot drift or jitter.
TextField {
    id: root

    property bool error: false
    property string labelText: ""
    property bool compact: false
    property color containerColor: Appearance.colors.colLayer1
    property Component leadingContent
    property Component trailingContent
    property real leadingContentWidth: Metrics.iconM
    property real trailingContentWidth: Metrics.touchTarget
    readonly property bool hasLeadingContent: root.leadingContent !== null && root.leadingContent !== undefined
    readonly property bool hasTrailingContent: root.trailingContent !== null && root.trailingContent !== undefined
    readonly property color effectiveAccent: root.error ? Appearance.colors.colError : Appearance.colors.colPrimary

    Material.theme: Appearance.m3colors.darkmode ? Material.Dark : Material.Light
    Material.accent: root.effectiveAccent
    Material.primary: root.effectiveAccent
    Material.background: root.containerColor
    Material.foreground: Appearance.colors.colOnSurface
    Material.containerStyle: Material.Outlined
    renderType: Text.QtRendering
    selectByMouse: true
    wrapMode: TextInput.NoWrap
    activeFocusOnTab: true
    // The native outlined field owns its height and content rectangle. Keeping
    // it unclipped avoids adding a top inset for the floating label, so text
    // and our leading/trailing content share the control's true centre.
    clip: false
    color: root.enabled ? Appearance.colors.colOnSurface : Appearance.applyAlpha(Appearance.colors.colOnSurface, 0.38)
    selectedTextColor: Appearance.colors.colOnPrimaryContainer
    selectionColor: Appearance.colors.colPrimaryContainer
    placeholderTextColor: !root.enabled ? Appearance.applyAlpha(Appearance.colors.colOnSurface, 0.38) : root.activeFocus ? root.effectiveAccent : Appearance.colors.colOnSurfaceVariant
    leftPadding: Metrics.spacingL + (root.hasLeadingContent ? root.leadingContentWidth + Metrics.spacingXS : 0)
    rightPadding: Metrics.spacingL + (root.hasTrailingContent ? root.trailingContentWidth + Metrics.spacingXS : 0)

    font {
        family: Typography.bodyLarge.family
        pixelSize: Typography.bodyLarge.pixelSize
        weight: Typography.bodyLarge.weight
        hintingPreference: Font.PreferFullHinting
    }

    // Preserve the component API while passing the label to the native
    // Material placeholder implementation.
    Binding {
        target: root
        property: "placeholderText"
        value: root.labelText
        when: root.labelText.length > 0
        restoreMode: Binding.RestoreBindingOrValue
    }

    Loader {
        anchors.left: parent.left
        anchors.leftMargin: Metrics.spacingL
        anchors.verticalCenter: parent.verticalCenter
        width: root.hasLeadingContent ? root.leadingContentWidth : 0
        height: root.hasLeadingContent ? Math.min(root.height, Metrics.touchTarget) : 0
        sourceComponent: root.leadingContent
        z: 1
    }

    Loader {
        anchors.right: parent.right
        anchors.rightMargin: Metrics.spacingXS
        anchors.verticalCenter: parent.verticalCenter
        width: root.hasTrailingContent ? root.trailingContentWidth : 0
        height: root.hasTrailingContent ? Math.min(root.height, Metrics.touchTarget) : 0
        sourceComponent: root.trailingContent
        z: 1
    }

}
