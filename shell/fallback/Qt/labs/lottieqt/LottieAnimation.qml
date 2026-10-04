import QtQuick

Item {
    id: root

    enum Status {
        Null,
        Ready,
        Loading,
        Error
    }

    property url source: ""
    property bool autoPlay: false
    property int loops: 1
    readonly property int status: LottieAnimation.Status.Null

    function play() {
    }
    function pause() {
    }
}
