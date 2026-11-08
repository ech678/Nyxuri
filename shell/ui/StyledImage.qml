import QtQuick
import qs.commons

// Fork & Trim: iNiR modules/common/widgets/StyledImage.qml
// Asynchronous image with fade-in and fallbacks
Image {
    asynchronous: true
    retainWhileLoading: true
    visible: opacity > 0
    opacity: (status === Image.Ready) ? 1 : 0
    Behavior on opacity {
        NumberAnimation {
            duration: Appearance.animation.elementMoveEnter.duration
            easing.type: Appearance.animation.elementMoveEnter.type
            easing.bezierCurve: Appearance.animation.elementMoveEnter.bezierCurve
        }
    }

    property list<string> fallbacks: []
    property int currentFallbackIndex: 0

    onStatusChanged: {
        if (status === Image.Error && currentFallbackIndex < fallbacks.length) {
            source = fallbacks[currentFallbackIndex];
            currentFallbackIndex += 1;
        }
    }
}
