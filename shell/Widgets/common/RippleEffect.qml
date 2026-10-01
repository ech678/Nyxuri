import QtQuick
import qs.Common

Item {
    id: root

    property color color: Appearance.colors.colOnSurface
    property real effectOpacity: Appearance.interaction.rippleOpacity
    property int duration: Appearance.interaction.rippleDuration
    property int easingType: Appearance.interaction.rippleEasing
    property real shapeRadius: 0
    property real targetDiameter: 0
    readonly property bool active: rippleAnimation.running || ripple.progress > 0

    function clear() {
        rippleAnimation.stop();
        ripple.progress = 0;
        root.targetDiameter = 0;
    }

    function startAt(x, y) {
        root.clear();
        ripple.centerX = x;
        ripple.centerY = y;
        root.targetDiameter = Math.sqrt(root.width * root.width + root.height * root.height) * 2.2;
        rippleAnimation.restart();
    }

    function finish() {
        if (!rippleAnimation.running)
            root.clear();

    }

    onColorChanged: rippleCanvas.requestPaint()
    onEffectOpacityChanged: rippleCanvas.requestPaint()
    onShapeRadiusChanged: rippleCanvas.requestPaint()
    onTargetDiameterChanged: rippleCanvas.requestPaint()
    clip: true

    Item {
        id: ripple

        property real centerX: root.width / 2
        property real centerY: root.height / 2
        property real progress: 0
        readonly property real diameter: root.targetDiameter * progress
        readonly property real rippleOpacity: root.effectOpacity * (1 - progress)

        visible: false
        onCenterXChanged: rippleCanvas.requestPaint()
        onCenterYChanged: rippleCanvas.requestPaint()
        onProgressChanged: rippleCanvas.requestPaint()
    }

    Canvas {
        id: rippleCanvas

        anchors.fill: parent
        visible: root.active
        renderStrategy: Canvas.Immediate
        antialiasing: true
        onVisibleChanged: {
            if (visible)
                requestPaint();

        }
        onPaint: {
            const context = getContext("2d");
            context.reset();
            context.clearRect(0, 0, width, height);
            if (!root.active || width <= 0 || height <= 0)
                return ;

            const cornerRadius = Math.min(root.shapeRadius, width / 2, height / 2);
            context.beginPath();
            context.moveTo(cornerRadius, 0);
            context.lineTo(width - cornerRadius, 0);
            context.quadraticCurveTo(width, 0, width, cornerRadius);
            context.lineTo(width, height - cornerRadius);
            context.quadraticCurveTo(width, height, width - cornerRadius, height);
            context.lineTo(cornerRadius, height);
            context.quadraticCurveTo(0, height, 0, height - cornerRadius);
            context.lineTo(0, cornerRadius);
            context.quadraticCurveTo(0, 0, cornerRadius, 0);
            context.closePath();
            context.clip();
            context.globalAlpha = ripple.rippleOpacity;
            context.fillStyle = String(root.color);
            context.beginPath();
            context.arc(ripple.centerX, ripple.centerY, ripple.diameter / 2, 0, Math.PI * 2);
            context.fill();
        }
    }

    NumberAnimation {
        id: rippleAnimation

        onFinished: root.clear()
        target: ripple
        property: "progress"
        from: 0
        to: 1
        duration: root.duration
        easing.type: root.easingType
    }

}
