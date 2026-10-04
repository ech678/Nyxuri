import QtQuick
import qs.shared.theme
import qs.shared.i18n

Rectangle {
    id: root

    property bool active: true
    property color surfaceColor: Appearance.colors.colSurfaceContainerHigh
    property date currentDate: new Date()
    readonly property var monthNames: [I18n.tr("January"), I18n.tr("February"), I18n.tr("March"), I18n.tr(
            "April"), I18n.tr("May"), I18n.tr("June"), I18n.tr("July"), I18n.tr("August"), I18n.tr(
            "September"), I18n.tr("October"), I18n.tr("November"), I18n.tr("December")]
    readonly property var weekdayNames: [I18n.tr("Sun"), I18n.tr("Mon"), I18n.tr("Tue"), I18n.tr("Wed"),
        I18n.tr("Thu"), I18n.tr("Fri"), I18n.tr("Sat")]
    readonly property var accessibleWeekdayNames: [I18n.tr("Sunday"), I18n.tr("Monday"), I18n.tr("Tuesday"),
        I18n.tr("Wednesday"), I18n.tr("Thursday"), I18n.tr("Friday"), I18n.tr("Saturday")]
    readonly property string calendarFamily: Fonts.expressive
    readonly property var calendarAxes: Fonts.bundledFamilyAvailable && Fonts.expressive
                                        === Fonts.bundledFamilyName ? ({
                                                                           "ROND": 45,
                                                                           "wdth": 78
                                                                       }) : ({})

    radius: Appearance.rounding.extraLarge
    color: root.surfaceColor
    clip: true
    Accessible.name: currentDate.getFullYear() + I18n.tr(" ") + (currentDate.getMonth() + 1) + I18n.tr("/")
                     + currentDate.getDate() + I18n.tr(", ") + accessibleWeekdayNames[currentDate.getDay()]

    Timer {
        interval: 30000
        repeat: true
        running: root.active
        triggeredOnStart: true
        onTriggered: root.currentDate = new Date()
    }

    Rectangle {
        id: headingBand

        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
        }
        height: Math.max(42, root.height * 0.36)
        color: Appearance.colors.colSecondaryContainer
        topLeftRadius: root.radius
        topRightRadius: root.radius
        bottomLeftRadius: 0
        bottomRightRadius: 0

        Text {
            anchors.centerIn: parent
            text: root.monthNames[root.currentDate.getMonth()] + "  "
                  + root.weekdayNames[root.currentDate.getDay()]
            color: Appearance.colors.colOnSecondaryContainer
            renderType: Text.NativeRendering
            font {
                family: root.calendarFamily
                pixelSize: Math.min(Typography.titleMedium.pixelSize, headingBand.height * 0.36)
                weight: Font.Bold
                letterSpacing: 0.8
                variableAxes: root.calendarAxes
            }
        }
    }

    Text {
        anchors {
            top: headingBand.bottom
            bottom: parent.bottom
            left: parent.left
            right: parent.right
        }
        text: String(root.currentDate.getDate())
        color: Appearance.colors.colOnSurface
        renderType: Text.NativeRendering
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font {
            family: root.calendarFamily
            pixelSize: Math.min(root.width * 0.52, root.height * 0.5)
            weight: Font.Medium
            variableAxes: root.calendarAxes
        }
    }
}
