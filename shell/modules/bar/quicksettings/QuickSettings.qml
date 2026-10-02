import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services as Services
import qs.shared.controls

TopBarPill {
    id: root

    property var screen: null
    property bool vertical: false

    function componentFor(componentId) {
        switch (componentId) {
        case "network":
            return networkComponent;
        case "bluetooth":
            return bluetoothComponent;
        case "brightness":
            return brightnessComponent;
        case "volume":
            return volumeComponent;
        case "microphone":
            return microphoneComponent;
        case "battery":
            return batteryComponent;
        case "settings":
            return settingsComponent;
        case "power":
            return powerComponent;
        default:
            return null;
        }
    }

    implicitHeight: vertical ? layout.implicitHeight + 2 * Sizes.barPillHorizontalPadding :
                               Sizes.barPillThickness
    implicitWidth: vertical ? Sizes.barPillThickness : layout.implicitWidth + 2
                              * Sizes.barPillHorizontalPadding

    GridLayout {
        id: layout

        anchors.centerIn: parent
        rowSpacing: Sizes.barItemSpacing
        columnSpacing: Sizes.barItemSpacing
        columns: root.vertical ? 1 : 8

        Repeater {
            id: componentRepeater
            model: Services.PersonalizationConfig.quickSettingsComponents

            Loader {
                id: componentLoader

                required property string modelData

                sourceComponent: root.componentFor(componentLoader.modelData)
            }
        }
    }

    Component {
        id: networkComponent

        Network {
            screen: root.screen
            vertical: root.vertical
        }
    }

    Component {
        id: bluetoothComponent

        BluetoothButton {
            vertical: root.vertical
            screen: root.screen
        }
    }

    Component {
        id: brightnessComponent

        Brightness {
            vertical: root.vertical
            screen: root.screen
        }
    }

    Component {
        id: volumeComponent

        Volume {
            vertical: root.vertical
            screen: root.screen
        }
    }

    Component {
        id: microphoneComponent

        Microphone {
            vertical: root.vertical
            screen: root.screen
        }
    }

    Component {
        id: batteryComponent

        Battery {
            vertical: root.vertical
        }
    }

    Component {
        id: settingsComponent

        SettingsButton {
            screen: root.screen
        }
    }

    Component {
        id: powerComponent

        PowerButton {
            screen: root.screen
        }
    }
}
