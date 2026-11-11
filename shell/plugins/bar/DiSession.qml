import QtQuick
import QtQuick.Layouts
import qs.services
import qs.commons
import qs.ui

Item {
    id: diSessionRoot
    required property Item di
    anchors.fill: parent
    
    readonly property var actions: [
        { icon: "lock",              label: Translation.tr("Lock"),     action: () => ActionGateway.powerAction("lock", "island:session") },
        { icon: "dark_mode",         label: Translation.tr("Sleep"),    action: () => ActionGateway.powerAction("suspend", "island:session") },
        { icon: "restart_alt",       label: Translation.tr("Reboot"),   action: () => ActionGateway.powerAction("reboot", "island:session") },
        { icon: "power_settings_new", label: Translation.tr("Shutdown"), action: () => ActionGateway.powerAction("poweroff", "island:session") }
    ]

    property int focusedIndex: 0

    function confirmCurrent() {
        diSessionRoot.actions[diSessionRoot.focusedIndex].action()
        GlobalStates.diSessionOpen = false
    }

    function close() {
        GlobalStates.diSessionOpen = false
    }

    onVisibleChanged: if (visible) diSessionRoot.forceActiveFocus()
    Component.onCompleted: if (diSessionRoot.visible) diSessionRoot.forceActiveFocus()

    RowLayout {
        anchors.centerIn: parent
        spacing: 8

        Repeater {
            model: diSessionRoot.actions
            delegate: Item {
                id: actionDelegate
                required property var modelData
                required property int index
                implicitWidth: 34
                implicitHeight: 34

                readonly property bool isFocused: diSessionRoot.focusedIndex === actionDelegate.index

                MaterialShapeWrappedMaterialSymbol {
                    anchors.fill: parent
                    wrappedShape: MaterialShapeCanvas.Shape.Cookie12Sided
                    text: actionDelegate.modelData.icon
                    iconSize: 18
                    fill: actionDelegate.isFocused ? 1 : 0
                    padding: 4
                    color: actionDelegate.isFocused ? Appearance.colors.colPrimary : Appearance.colors.colLayer1
                    colSymbol: actionDelegate.isFocused ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1

                    Behavior on color { ColorAnimation { duration: 150 } }
                    Behavior on colSymbol { ColorAnimation { duration: 150 } }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: diSessionRoot.focusedIndex = actionDelegate.index
                    onClicked: {
                        diSessionRoot.focusedIndex = actionDelegate.index
                        diSessionRoot.confirmCurrent()
                    }
                }
            }
        }
    }
}
