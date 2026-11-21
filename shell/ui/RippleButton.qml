import QtQuick
import QtQuick.Controls
import qs.commons

Button {
    id: root

    property bool toggled: false
    property string buttonText: ""
    property bool pointingHandCursor: true
    property real buttonRadius: Appearance.rounding.small
    property real buttonRadiusPressed: root.buttonRadius
    property alias backgroundContent: backgroundContentHost.data
    property var downAction
    property var releaseAction
    property var doubleClickAction
    property var altAction
    property var middleClickAction
    property var wheelAction
    property color containerColor: "transparent"
    property color rippleColor: Appearance.colors.colOnSurface
    property alias colBackground: root.containerColor
    property alias colRipple: root.rippleColor
    property alias colBackgroundHover: root.hoverStateLayerColor
    // Toggled trio (D0): these used to be plain properties whose assignments
    // never reached the background — the tray-arrow hover bug. They are live
    // now: toggled swaps the background fill (and the ripple), the state layer
    // keeps painting its own ink states on top.
    property color colBackgroundToggled: root.containerColor
    property color colBackgroundToggledHover: root.colBackgroundToggled
    property color colRippleToggled: root.rippleColor
    property bool stateLayerEnabled: true
    property color stateLayerColor: Appearance.colors.colOnSurface
    property color hoverStateLayerColor: root.stateLayerColor
    property color focusStateLayerColor: root.stateLayerColor
    property color pressedStateLayerColor: root.stateLayerColor
    property color selectedStateLayerColor: root.stateLayerColor
    property bool selectedStateLayerEnabled: false
    // D0 state-layer contract: every opacity defaults to the M3 values in
    // Appearance.interaction (hover 8% / focus 10% / press 10% / selected
    // 10%) instead of the old `stateLayerOpacity: 1` chain that silently
    // defeated them — full-opacity ink fills (the near-black tray-arrow
    // hover) were the default escape. Consumers that want a solid
    // pre-mixed fill set the colors *and* the opacities explicitly.
    property real selectedStateLayerOpacity: Appearance.interaction.selectedStateLayerOpacity
    property real hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
    property real pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
    property real focusStateLayerOpacity: Appearance.interaction.focusStateLayerOpacity
    property bool pointerPressActive: false
    readonly property bool pointerHovered: pointerArea.containsMouse
    readonly property real buttonEffectiveRadius: root.down ? root.buttonRadiusPressed : root.buttonRadius

    function clearRipple() {
        rippleEffect.clear();
    }

    function beginRipple(x, y) {
        rippleEffect.startAt(x, y);
    }

    function finishRipple() {
        rippleEffect.finish();
    }

    opacity: root.enabled ? 1 : 0.4
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: root.text.length > 0 ? root.text : root.buttonText
    Accessible.role: Accessible.Button
    onPressedChanged: {
        if (root.pressed && !root.pointerPressActive)
            root.beginRipple(root.width / 2, root.height / 2);
        else if (!root.pressed && rippleEffect.active)
            root.finishRipple();
    }
    onClicked: {
        const action = root.releaseAction;
        if (action)
            action(null);
    }

    MouseArea {
        id: pointerArea

        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: root.pointingHandCursor ? Qt.PointingHandCursor : Qt.ArrowCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        onPressed: event => {
            if (event.button === Qt.RightButton) {
                if (root.altAction)
                    root.altAction(event);

                return;
            }
            if (event.button === Qt.MiddleButton) {
                if (root.middleClickAction)
                    root.middleClickAction(event);

                return;
            }
            root.pointerPressActive = true;
            root.down = true;
            root.beginRipple(event.x, event.y);
            if (root.downAction)
                root.downAction(event);
        }
        onReleased: event => {
            root.down = false;
            root.pointerPressActive = false;
            if (event.button === Qt.LeftButton)
                root.finishRipple();
        }
        onClicked: event => {
            if (event.button === Qt.LeftButton)
                root.clicked();
        }
        onDoubleClicked: event => {
            if (event.button === Qt.LeftButton && root.doubleClickAction)
                root.doubleClickAction(event);
        }
        onCanceled: {
            root.down = false;
            root.pointerPressActive = false;
            root.finishRipple();
        }
        onWheel: wheel => {
            if (root.wheelAction) {
                root.wheelAction(wheel);
            } else {
                wheel.accepted = false;
            }
        }
    }

    background: Rectangle {
        id: surface

        radius: root.buttonEffectiveRadius
        color: root.toggled ? (root.pointerHovered ? root.colBackgroundToggledHover : root.colBackgroundToggled) : root.containerColor
        clip: true

        Item {
            id: backgroundContentHost

            anchors.fill: parent
            z: 0
        }

        StateLayer {
            anchors.fill: parent
            z: 1
            enabled: root.stateLayerEnabled
            hovered: root.pointerHovered
            focused: root.visualFocus
            pressed: false
            selected: root.toggled
            selectedEnabled: root.selectedStateLayerEnabled
            color: root.stateLayerColor
            hoverColor: root.hoverStateLayerColor
            focusColor: root.focusStateLayerColor
            pressedColor: root.pressedStateLayerColor
            selectedColor: root.selectedStateLayerColor
            hoverOpacity: root.hoverStateLayerOpacity
            focusOpacity: root.focusStateLayerOpacity
            pressedOpacity: root.pressedStateLayerOpacity
            selectedOpacity: root.selectedStateLayerOpacity
            layerRadius: root.buttonEffectiveRadius
        }

        RippleEffect {
            id: rippleEffect

            anchors.fill: parent
            z: 2
            color: root.toggled ? root.colRippleToggled : root.rippleColor
            shapeRadius: root.buttonEffectiveRadius
        }
    }

    contentItem: Text {
        text: root.buttonText.length > 0 ? root.buttonText : root.text
        color: Appearance.colors.colOnSurface
        font.family: Fonts.ui
        font.pixelSize: NexusStyle.font.bodySmall
        verticalAlignment: Text.AlignVCenter
    }
}
