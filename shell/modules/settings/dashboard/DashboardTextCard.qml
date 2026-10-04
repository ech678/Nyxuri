pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

// Free-text tile. Ported from end4-pC's DashboardTextCard.
DashboardCard {
    id: root

    property string controlKey: ""
    property string title: ""
    property string icon: "edit"
    property var tileShape: MaterialShapeCanvas.Shape.Slanted
    property var override: null
    property string placeholder: ""

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property string current: root.control ? String(root.control.get() ?? "") : ""

    tint: Appearance.colors.colSecondaryContainer

    onCurrentChanged: {
        if (!field.activeFocus)
            field.text = root.current;
    }

    Component.onCompleted: field.text = root.current

    Timer {
        id: debounce

        interval: 600
        onTriggered: {
            if (root.control && field.text !== root.current)
                root.control.set(field.text);
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            MaterialShapeWrappedMaterialSymbol {
                wrappedShape: root.tileShape
                text: root.icon
                iconSize: 22
                fill: 1
                padding: 9
                color: Appearance.colors.colSecondary
                colSymbol: Appearance.colors.colOnSecondary
            }

            StyledText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Typography.bodyLarge.pixelSize
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnSecondaryContainer
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
        }

        Item {
            Layout.fillHeight: true
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 40
            radius: 20
            color: Qt.rgba(1, 1, 1, 0.12)
            border.width: field.activeFocus ? 2 : 0
            border.color: Appearance.colors.colSecondary

            TextInput {
                id: field

                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                verticalAlignment: TextInput.AlignVCenter
                clip: true
                font.pixelSize: Typography.bodyLarge.pixelSize
                font.family: Fonts.ui
                color: Appearance.colors.colOnSecondaryContainer
                selectionColor: Appearance.colors.colSecondary
                onTextEdited: debounce.restart()
                onEditingFinished: {
                    debounce.stop();
                    if (root.control && text !== root.current)
                        root.control.set(text);
                }
                Keys.onEscapePressed: {
                    field.text = root.current;
                    field.focus = false;
                    root.pager.forceActiveFocus();
                }

                StyledText {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: field.text === "" && !field.activeFocus && root.placeholder !== ""
                    text: root.placeholder
                    color: Appearance.colors.colOnSecondaryContainer
                    opacity: 0.5
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
