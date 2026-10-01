import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Clavis.WindowPreview

ApplicationWindow {
    id: root
    required property WindowCaptureProbe capture
    width: 780
    height: 600
    visible: true
    title: qsTr("Window capture probe")
    onClosing: capture.close()

    Connections {
        target: root.capture
        function onChanged() {
            for (let i = 0; i < root.capture.windows.length; ++i) {
                if (root.capture.windows[i].identifier === root.capture.identifier) {
                    selector.currentIndex = i;
                    break;
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        ComboBox {
            id: selector
            Layout.fillWidth: true
            model: root.capture.windows
            textRole: "title"
            valueRole: "identifier"
            onActivated: {
                if (root.capture.active)
                    root.capture.start(String(currentValue));
            }
        }
        RowLayout {
            Button {
                text: qsTr("Start")
                enabled: root.capture.supported && selector.currentIndex >= 0
                onClicked: root.capture.start(String(selector.currentValue))
            }
            Button {
                text: qsTr("Stop")
                enabled: root.capture.active
                onClicked: root.capture.stop()
            }
            Label {
                text: qsTr("Identifier: %1").arg(root.capture.identifier)
            }
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: qsTr("Frames: %1 · First frame: %2 ms · Source: %3 × %4").arg(root.capture.frameCount).arg(
                      root.capture.firstFrameMs).arg(root.capture.sourceSize.width).arg(
                      root.capture.sourceSize.height)
        }
        Label {
            Layout.fillWidth: true
            visible: root.capture.error !== ""
            text: root.capture.error
            wrapMode: Text.WrapAnywhere
            color: "#c53030"
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#20242b"
            CaptureImage {
                anchors.fill: parent
                capture: root.capture
            }
        }
    }
}
