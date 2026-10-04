pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

// Dropdown tile. Ported from end4-pC's DashboardComboCard; the dropdown is
// nyxuri's SearchSelectMenuField.
DashboardCard {
    id: root

    property string controlKey: ""
    property string title: ""
    property string icon: "tune"
    property var tileShape: MaterialShapeCanvas.Shape.Puffy
    property var override: null

    readonly property var control: root.override ?? SettingsControlCatalog.controlFor(root.controlKey)
    readonly property var options: root.control ? root.control.options ?? [] : []
    readonly property var currentValue: root.control ? root.control.get() : null

    tint: Appearance.colors.colPrimaryContainer

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
                iconSize: 24
                fill: 1
                padding: 10
                color: Appearance.colors.colPrimary
                colSymbol: Appearance.colors.colOnPrimary
            }

            StyledText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Typography.titleLarge.pixelSize
                font.weight: Font.DemiBold
                color: Appearance.colors.colOnPrimaryContainer
                elide: Text.ElideRight
            }
        }

        Item {
            Layout.fillHeight: true
        }

        SearchSelectMenuField {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            options: root.options
            value: root.currentValue ?? ""
            textRole: "label"
            valueRole: "value"
            onAccepted: value => {
                if (root.control)
                    Qt.callLater(() => root.control.set(value));
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
