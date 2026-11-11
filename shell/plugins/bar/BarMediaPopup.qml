import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

Rectangle {
    id: root

    signal closeRequested()
    property bool presented: false

    width: 320
    height: 100
    radius: Appearance.rounding.normal
    color: Appearance.colors.colLayer1
    border.color: Appearance.colors.colOutlineVariant
    border.width: 1

    property var player: MediaService.active
    property bool isPlaying: player && player.isPlaying

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 64
            Layout.preferredHeight: 64
            radius: Appearance.rounding.small
            color: Appearance.colors.colLayer2
            clip: true

            Image {
                anchors.fill: parent
                source: root.player?.trackArtUrl ?? ""
                fillMode: Image.PreserveAspectCrop
                visible: source !== "" && status === Image.Ready
            }

            MaterialSymbol {
                anchors.centerIn: parent
                text: "music_note"
                iconSize: 28
                color: Appearance.colors.colOnLayer2
                visible: !root.player?.trackArtUrl
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 2

            Text {
                Layout.fillWidth: true
                text: root.player?.trackTitle || I18n.tr("No media")
                font.family: Appearance.font.main
                font.pixelSize: 13
                font.bold: true
                color: Appearance.colors.colOnLayer1
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: root.player?.trackArtist || I18n.tr("Not playing")
                font.family: Appearance.font.main
                font.pixelSize: 11
                color: Appearance.colors.colOnLayer2
                elide: Text.ElideRight
            }

            RowLayout {
                spacing: 8

                RippleButton {
                    implicitWidth: 28
                    implicitHeight: 28
                    onClicked: if (root.player?.canGoPrevious) root.player.previous()
                    MaterialSymbol {
                        anchors.centerIn: parent
                        text: "skip_previous"
                        iconSize: 18
                        color: Appearance.colors.colOnLayer1
                    }
                }

                RippleButton {
                    implicitWidth: 28
                    implicitHeight: 28
                    onClicked: if (root.player?.canControl) root.player.playPause()
                    MaterialSymbol {
                        anchors.centerIn: parent
                        text: root.isPlaying ? "pause" : "play_arrow"
                        iconSize: 20
                        color: Appearance.colors.colPrimary
                    }
                }

                RippleButton {
                    implicitWidth: 28
                    implicitHeight: 28
                    onClicked: if (root.player?.canGoNext) root.player.next()
                    MaterialSymbol {
                        anchors.centerIn: parent
                        text: "skip_next"
                        iconSize: 18
                        color: Appearance.colors.colOnLayer1
                    }
                }
            }
        }
    }
}
