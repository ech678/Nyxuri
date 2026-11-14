// Fork & Trim: end4-pC modules/ii/bar/DiOsd.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// B8.4 trim: the OSD producer now lives in DynamicIsland, which defines
// osdKind/osdValueText; this face only renders. The root is an Item so the
// click overlay is not a layout child (anchors inside RowLayout are undefined
// behavior and Qt warns at runtime).

import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.commons
import qs.ui

Item {
    id: diOsdRoot

    required property Item di
    anchors.fill: parent

    MouseArea {
        anchors.fill: parent
        cursorShape: di.osdKind === "volume" ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (di.osdKind === "volume" && VolumeService.sink?.audio) {
                VolumeService.sink.audio.muted = !VolumeService.sink.audio.muted;
            }
        }
    }

    RowLayout {
        anchors {
            fill: parent
            leftMargin: di.isMaterial ? 0 : 4
            rightMargin: 10
        }
        spacing: 6

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
}
