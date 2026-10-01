import QtQuick
import qs.Common

Item {
    id: root
    
    implicitWidth: 32
    implicitHeight: 32

    property real angle: 0 // 0 to 360
    property color moonColor: "#fff5cc"
    property color shadowColor: Appearance.colors.colSurfaceContainerHigh

    onAngleChanged: canvas.requestPaint()
    onMoonColorChanged: canvas.requestPaint()
    onShadowColorChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent
        onWidthChanged: requestPaint()

        onPaint: {
            const ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            
            const cx = width / 2;
            const cy = height / 2;
            const r = Math.min(width, height) / 2;

            // Draw full moon base
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fillStyle = root.moonColor;
            ctx.fill();

            // Calculate shadow
            // 0 = New Moon (Fully covered)
            // 90 = First Quarter (Left half covered)
            // 180 = Full Moon (Fully exposed)
            // 270 = Last Quarter (Right half covered)

            const a = root.angle;
            
            ctx.fillStyle = root.shadowColor;
            
            // Draw left half shadow
            if (a < 180) {
                ctx.beginPath();
                ctx.arc(cx, cy, r, Math.PI / 2, Math.PI * 1.5);
                ctx.fill();
            }
            // Draw right half shadow
            if (a > 180 && a < 360) {
                ctx.beginPath();
                ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2);
                ctx.fill();
            }

            // Draw terminator ellipse
            ctx.save();
            ctx.translate(cx, cy);
            
            let cosA = Math.cos(a * Math.PI / 180);
            
            // The terminator scales horizontally by cosA
            ctx.scale(Math.abs(cosA), 1);
            
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2);
            
            // If waxing (a < 180), cosA goes from 1 to -1.
            // When cosA > 0 (0-90), terminator is shadow. When cosA < 0 (90-180), terminator is bright.
            // If waning (a > 180), cosA goes from -1 to 1.
            // When cosA < 0 (180-270), terminator is shadow. When cosA > 0 (270-360), terminator is bright.
            
            if (a < 180) {
                ctx.fillStyle = cosA > 0 ? root.shadowColor : root.moonColor;
            } else {
                ctx.fillStyle = cosA < 0 ? root.shadowColor : root.moonColor;
            }
            
            ctx.fill();
            ctx.restore();
        }
    }
}
