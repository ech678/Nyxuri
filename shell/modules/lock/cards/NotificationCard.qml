import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.app
import qs.shared.i18n

Rectangle {
    id: root

    property bool compact: false
    property bool veryCompact: false
    readonly property var notifications: NotificationService.list.slice().sort((a, b) => {
        return b.receivedAt - a.receivedAt;
    })
    readonly property int notificationCount: notifications.length
    readonly property int cardMargin: Metrics.lockOuterPadding

    function formatTime(timestamp) {
        const date = new Date(Number(timestamp));
        if (isNaN(date.getTime()))
            return "";

        const now = new Date();
        if (date.toDateString() === now.toDateString())
            return UiPreferences.shortTime(date);

        return Qt.formatDate(date, "MM/dd") + " " + UiPreferences.shortTime(date);
    }

    function sanitizedBody(body) {
        return (body || "").replace(/<img\b[^>]*>/gi, "");
    }

    Layout.fillWidth: true
    Layout.fillHeight: true
    color: Appearance.colors.colLayer2
    radius: Metrics.lockCardRadius
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.cardMargin
        spacing: Metrics.spacingM

        Text {
            Layout.fillWidth: true
            text: root.notificationCount > 0 ? I18n.tr("%1 notifications").arg(root.notificationCount) : I18n.tr(
                                                   "Notifications")

            color: Appearance.colors.colOutline
            font.family: Fonts.numeric
            font.pixelSize: 17
            font.weight: 500
            elide: Text.ElideRight
        }

        Item {
            id: clipRect

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: !root.veryCompact

            ColumnLayout {
                anchors.centerIn: parent
                width: parent.width
                spacing: Metrics.spacingXL
                opacity: root.notificationCount > 0 ? 0 : 1
                scale: root.notificationCount > 0 ? 0.96 : 1
                visible: opacity > 0

                MaterialSymbol {
                    Layout.alignment: Qt.AlignHCenter
                    text: "notifications_off"
                    iconSize: 48
                    color: Appearance.colors.colOutlineVariant
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: I18n.tr("No notifications")
                    color: Appearance.colors.colOutlineVariant
                    font.family: Fonts.numeric
                    font.pixelSize: 24
                    font.weight: 500
                }

                Behavior on opacity {
                    NumberAnimation {
                        duration: Appearance.animation.standardExtraLarge.duration
                        easing.type: Appearance.animation.standardExtraLarge.type
                        easing.bezierCurve: Appearance.animation.standardExtraLarge.bezierCurve
                    }
                }

                Behavior on scale {
                    NumberAnimation {
                        duration: Appearance.animation.expressiveDefaultSpatial.duration
                        easing.type: Appearance.animation.expressiveDefaultSpatial.type
                        easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                    }
                }
            }

            StyledListView {
                id: listView

                anchors.fill: parent
                visible: root.notificationCount > 0
                clip: true
                spacing: Metrics.spacingS
                animateMovement: true
                model: root.notifications

                delegate: Rectangle {
                    id: delegateRoot

                    required property var modelData

                    width: ListView.view ? ListView.view.width : 0
                    height: Math.max(84, contentRow.implicitHeight + 14)
                    radius: Metrics.lockCardRadiusSmall
                    color: Appearance.colors.colLayer3

                    RowLayout {
                        id: contentRow

                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 12

                        NotificationVisual {
                            resolvedAppIcon: ThemeService.resolveIcon(appIcon)
                            Layout.preferredWidth: 56
                            Layout.preferredHeight: 56
                            Layout.alignment: Qt.AlignTop
                            appIcon: delegateRoot.modelData ? delegateRoot.modelData.appIcon : ""
                            image: delegateRoot.modelData ? delegateRoot.modelData.image : ""
                            summary: delegateRoot.modelData ? delegateRoot.modelData.summary : ""
                            urgency: delegateRoot.modelData ? delegateRoot.modelData.urgency : ""
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Text {
                                    text: delegateRoot.modelData ? delegateRoot.modelData.appName : ""
                                    color: Appearance.colors.colPrimary
                                    font.family: Fonts.numeric
                                    font.pixelSize: 13
                                    font.bold: true
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }

                                Text {
                                    Layout.alignment: Qt.AlignVCenter
                                    text: delegateRoot.modelData ? root.formatTime(
                                                                       delegateRoot.modelData.receivedAt) : ""
                                    color: Appearance.colors.colOnSurfaceVariant
                                    font.family: Fonts.numeric
                                    font.pixelSize: 13
                                    opacity: 0.7
                                }
                            }

                            Text {
                                text: delegateRoot.modelData ? delegateRoot.modelData.summary : ""
                                color: Appearance.colors.colOnSurface
                                font.family: Fonts.ui
                                font.pixelSize: 17
                                font.bold: true
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Text {
                                text: delegateRoot.modelData ? root.sanitizedBody(
                                                                   delegateRoot.modelData.body) : ""
                                textFormat: Text.StyledText
                                color: Appearance.colors.colOnSurfaceVariant
                                font.family: Fonts.ui
                                font.pixelSize: 16
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                                maximumLineCount: 2
                                visible: !root.compact
                                opacity: 0.8
                            }
                        }
                    }
                }

                add: Transition {
                    ParallelAnimation {
                        NumberAnimation {
                            property: "opacity"
                            from: 0
                            to: 1
                            duration: Appearance.animation.expressiveEffects.duration
                            easing.type: Appearance.animation.expressiveEffects.type
                            easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                        }

                        NumberAnimation {
                            property: "scale"
                            from: 0.92
                            to: 1
                            duration: Appearance.animation.expressiveDefaultSpatial.duration
                            easing.type: Appearance.animation.expressiveDefaultSpatial.type
                            easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                        }
                    }
                }

                remove: Transition {
                    ParallelAnimation {
                        NumberAnimation {
                            property: "opacity"
                            to: 0
                            duration: Appearance.animation.expressiveEffects.duration
                            easing.type: Appearance.animation.expressiveEffects.type
                            easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                        }

                        NumberAnimation {
                            property: "scale"
                            to: 0.6
                            duration: Appearance.animation.expressiveEffects.duration
                            easing.type: Appearance.animation.expressiveEffects.type
                            easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                        }
                    }
                }

                displaced: Transition {
                    NumberAnimation {
                        property: "y"
                        duration: Appearance.animation.expressiveDefaultSpatial.duration
                        easing.type: Appearance.animation.expressiveDefaultSpatial.type
                        easing.bezierCurve: Appearance.animation.expressiveDefaultSpatial.bezierCurve
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.veryCompact
            text: root.notificationCount > 0 ? I18n.tr("%1 notifications").arg(root.notificationCount) : I18n.tr(
                                                   "No notifications")

            color: Appearance.colors.colOnSurfaceVariant
            font.family: Fonts.numeric
            font.pixelSize: 20
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
}
