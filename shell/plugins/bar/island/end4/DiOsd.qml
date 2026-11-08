// Fork & Trim: end4-pC modules/ii/bar/DiOsd.qml (GPL-3, see shell/LICENSE
// appendix end-4-dots-hyprland-GPL-3.0.txt). Trimmed per the B volume four
// classes: upstream singletons -> tree services / DynamicIsland bindings
// (di.iconForProviderId("osd") / di.osdValueText()), Appearance tokens,
// dead upstream paths dropped (Hyprsunset/Hyprland).
import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.commons
import qs.ui

RowLayout {
    id: diOsdRoot
    required property Item di
    anchors {
        fill: parent
        leftMargin: di.isMaterial ? 0 : 4
        rightMargin: 10
    }
    spacing: 6

    MouseArea {
        anchors.fill: parent
        cursorShape: di.osdType === "volume" || di.osdType === "mic" ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (di.osdType === "volume" && VolumeService.sink?.audio) {
                VolumeService.sink.audio.muted = !VolumeService.sink.audio.muted;
            } else if (di.osdType === "mic" && VolumeService.source?.audio) {
                VolumeService.source.audio.muted = !VolumeService.source.audio.muted;
            }
        }
    }

    MaterialShapeWrappedMaterialSymbol {
        Layout.alignment: Qt.AlignVCenter
        wrappedShape: MaterialShapeCanvas.Shape.Cookie12Sided
        color: Appearance.colors.colPrimary
        colSymbol: Appearance.colors.colOnPrimary
        text: di.iconForProviderId("osd")
        iconSize: di.isMaterial ? 20 : 16
        fill: 1
        padding: 4
    }

    Item {
        Layout.fillWidth: true
    }

    StyledText {
        Layout.alignment: Qt.AlignVCenter
        text: di.osdValueText()
        font.pixelSize: di.isMaterial ? Appearance.font.pixelSize.normal : Appearance.font.pixelSize.small
        font.features: {
            "tnum": 1
        }
        color: Appearance.colors.colOnLayer0
    }
}
