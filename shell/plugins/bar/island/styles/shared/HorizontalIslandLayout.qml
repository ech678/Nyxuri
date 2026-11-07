import QtQuick
import "../.."

QtObject {
    required property bool recordingActive
    required property bool audioActive
    required property bool lyricsActive
    required property bool expandedActive
    required property bool volumeActive
    required property bool notificationsActive
    required property bool collapsedHovered
    required property real recordingWidth
    required property real recordingHeight
    required property real lyricsWidth
    required property real lyricsHeight
    required property real notificationsWidth
    required property real notificationsHeight
    readonly property real audioWidth: IslandMotion.audioRecordingWidth
    readonly property real audioHeight: IslandMotion.audioRecordingHeight
    property real expandedWidth: 540
    property real expandedHeight: 210
    readonly property real volumeWidth: 320
    readonly property real volumeHeight: 64
    readonly property real collapsedWidth: 220
    readonly property real collapsedHeight: 42
    readonly property real attachedRecordingWidth: 220
    readonly property real attachedRecordingHeight: 42
    readonly property real targetWidth: recordingActive ? recordingWidth : audioActive ? audioWidth : lyricsActive ? lyricsWidth : expandedActive ? expandedWidth : volumeActive ? volumeWidth : notificationsActive ? notificationsWidth : collapsedWidth + (collapsedHovered ? 16 : 0)
    readonly property real targetHeight: recordingActive ? recordingHeight : audioActive ? audioHeight : lyricsActive ? lyricsHeight : expandedActive ? expandedHeight : volumeActive ? volumeHeight : notificationsActive ? notificationsHeight : collapsedHeight + (collapsedHovered ? 6 : 0)
}
