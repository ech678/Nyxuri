import QtQuick

QtObject {
    id: root
    property string sourceUrl: ""
    property string title: ""
    property string artist: ""

    readonly property bool ready: sourceUrl.length > 0
    readonly property string displaySource: sourceUrl
}
