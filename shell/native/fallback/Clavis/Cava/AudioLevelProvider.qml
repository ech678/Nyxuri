import QtQuick

QtObject {
    property bool active: false
    property string sourceNodeName: ""
    property bool captureSink: false
    readonly property bool available: false
    readonly property double timestampMs: 0
    readonly property double rms: 0
    readonly property double peak: 0
    readonly property double normalizedAmplitude: 0
    readonly property double visualTimestampMs: 0
    readonly property double visualAmplitude: 0
    readonly property string errorString: ""
}
