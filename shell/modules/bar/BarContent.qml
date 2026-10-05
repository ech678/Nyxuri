import QtQuick
import QtQuick.Layouts
import qs.app.services

Item {
    id: root

    required property var screen
    required property var axis
    property bool vertical: false
    property string popupEdge: axis.edge
    property int itemRevision: 0
    readonly property Item leadingInputRegionItem: leadingSection
    readonly property Item centerInputRegionItem: centerSection
    readonly property Item trailingInputRegionItem: trailingSection
    readonly property var backgroundItems: {
        const revision = root.itemRevision;
        const items = [];
        function collect(repeater) {
            for (let index = 0; index < repeater.count; index += 1) {
                const loader = repeater.itemAt(index);
                if (loader && loader.item)
                    items.push(loader.item);
            }
        }
        collect(leadingRepeater);
        collect(centerRepeater);
        collect(trailingRepeater);
        return items;
    }

    BarSection {
        id: leadingSection

        vertical: root.vertical
        compact: (root.vertical ? root.height : root.width) < 1000
        componentCount: PersonalizationConfig.barLayoutLeft.length

        anchors {
            left: root.vertical ? undefined : parent.left
            top: root.vertical ? parent.top : undefined
            leftMargin: root.vertical ? 0 : 10
            topMargin: root.vertical ? 10 : 0
            verticalCenter: root.vertical ? undefined : parent.verticalCenter
            horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
        }

        Repeater {
            id: leadingRepeater

            model: PersonalizationConfig.barLayoutLeft
            onItemAdded: root.itemRevision += 1
            onItemRemoved: root.itemRevision += 1

            delegate: BarComponentLoader {
                required property string modelData
                required property int index

                componentId: modelData
                screen: root.screen
                axis: root.axis
                barVisualItem: root
                vertical: root.vertical
                Layout.row: root.vertical ? index : 0
                Layout.column: root.vertical ? 0 : index
                Layout.alignment: Qt.AlignCenter
                onItemChanged: root.itemRevision += 1
            }
        }
    }

    BarSection {
        id: centerSection

        vertical: root.vertical
        compact: (root.vertical ? root.height : root.width) < 1000
        componentCount: PersonalizationConfig.barLayoutMiddle.length

        anchors {
            verticalCenter: parent.verticalCenter
            horizontalCenter: parent.horizontalCenter
        }

        Repeater {
            id: centerRepeater

            model: PersonalizationConfig.barLayoutMiddle
            onItemAdded: root.itemRevision += 1
            onItemRemoved: root.itemRevision += 1

            delegate: BarComponentLoader {
                required property string modelData
                required property int index

                componentId: modelData
                screen: root.screen
                axis: root.axis
                barVisualItem: root
                vertical: root.vertical
                Layout.row: root.vertical ? index : 0
                Layout.column: root.vertical ? 0 : index
                Layout.alignment: Qt.AlignCenter
                onItemChanged: root.itemRevision += 1
            }
        }
    }

    BarSection {
        id: trailingSection

        vertical: root.vertical
        compact: (root.vertical ? root.height : root.width) < 1000
        componentCount: PersonalizationConfig.barLayoutRight.length

        anchors {
            right: root.vertical ? undefined : parent.right
            bottom: root.vertical ? parent.bottom : undefined
            rightMargin: root.vertical ? 0 : 10
            bottomMargin: root.vertical ? 10 : 0
            verticalCenter: root.vertical ? undefined : parent.verticalCenter
            horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
        }

        Repeater {
            id: trailingRepeater

            model: PersonalizationConfig.barLayoutRight
            onItemAdded: root.itemRevision += 1
            onItemRemoved: root.itemRevision += 1

            delegate: BarComponentLoader {
                required property string modelData
                required property int index

                componentId: modelData
                screen: root.screen
                axis: root.axis
                barVisualItem: root
                vertical: root.vertical
                Layout.row: root.vertical ? index : 0
                Layout.column: root.vertical ? 0 : index
                Layout.alignment: Qt.AlignCenter
                onItemChanged: root.itemRevision += 1
            }
        }
    }
}
