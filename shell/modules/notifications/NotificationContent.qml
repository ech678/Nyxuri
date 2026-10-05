import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    required property var manager

    visible: !UiPreferences.dndEnabled && manager.hasNotifs

    StyledListView {
        anchors.fill: parent
        model: root.manager.popupList
        spacing: 10
        clip: true
        interactive: false
        animateMovement: true
        showVerticalScrollBar: false

        delegate: Item {
            id: delegateRoot

            required property var modelData
            readonly property var normalActions: root.manager.normalActions(delegateRoot.modelData)
            readonly property bool hasDefaultAction: root.manager.defaultAction(delegateRoot.modelData) !== null
            readonly property bool hasExpiry: delegateRoot.modelData && delegateRoot.modelData.popupExpiresAt > 0
            readonly property bool replyable: root.manager.replyable(delegateRoot.modelData)
            property bool replying: false
            property string replyText: ""
            onReplyingChanged: {
                if (delegateRoot.modelData)
                    delegateRoot.modelData.replyOpen = delegateRoot.replying;
            }
            property real expiryProgress: 0

            function sanitizedBody() {
                return (modelData ? modelData.body : "").replace(/<img\b[^>]*>/gi, "");
            }

            function restartProgress() {
                progressAnimation.stop();
                if (!delegateRoot.hasExpiry) {
                    delegateRoot.expiryProgress = 0;
                    return;
                }
                const total = Math.max(1, delegateRoot.modelData.popupExpiresAt - delegateRoot.modelData.popupStartedAt);
                const remaining = Math.max(0, delegateRoot.modelData.popupExpiresAt - Date.now());
                delegateRoot.expiryProgress = Math.min(1, remaining / total);
                progressAnimation.duration = remaining;
                progressAnimation.restart();
            }

            width: ListView.view.width
            height: (normalActions.length > 0 ? 104 : 64) + (delegateRoot.replying ? 46 : 0)
            Component.onCompleted: restartProgress()
            onModelDataChanged: restartProgress()

            NumberAnimation {
                id: progressAnimation

                target: delegateRoot
                property: "expiryProgress"
                to: 0
                easing.type: Easing.Linear
            }

            MouseArea {
                anchors.fill: card
                enabled: delegateRoot.hasDefaultAction
                cursorShape: Qt.PointingHandCursor
                onClicked: root.manager.invokeDefaultAction(delegateRoot.modelData.notificationId)
            }

            RowLayout {
                id: card

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: progressTrack.top
                anchors.bottomMargin: 4
                spacing: 12

                NotificationVisual {
                    resolvedAppIcon: ThemeService.resolveIcon(appIcon)
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 44
                    Layout.alignment: Qt.AlignTop
                    appIcon: delegateRoot.modelData ? delegateRoot.modelData.appIcon : ""
                    image: delegateRoot.modelData ? delegateRoot.modelData.image : ""
                    summary: delegateRoot.modelData ? delegateRoot.modelData.summary : ""
                    urgency: delegateRoot.modelData ? delegateRoot.modelData.urgency : ""
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 2

                    Text {
                        text: delegateRoot.modelData ? delegateRoot.modelData.summary : ""
                        color: Appearance.colors.colOnSurface
                        font.family: Fonts.ui
                        font.bold: true
                        font.pixelSize: Appearance.scaledFont(14)
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: delegateRoot.sanitizedBody()
                        textFormat: Text.StyledText
                        color: Appearance.colors.colOnSurfaceVariant
                        font.family: Fonts.ui
                        font.pixelSize: Appearance.scaledFont(12)
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        maximumLineCount: delegateRoot.normalActions.length > 0 ? 1 : 2
                        onLinkActivated: link => {
                            return ApplicationService.openUrl(link);
                        }
                    }

                    StyledFlickable {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        visible: delegateRoot.normalActions.length > 0
                        contentWidth: actionRow.implicitWidth
                        contentHeight: height
                        flickableDirection: Flickable.HorizontalFlick
                        boundsBehavior: Flickable.StopAtBounds
                        showVerticalScrollBar: false

                        RowLayout {
                            id: actionRow

                            height: parent.height
                            spacing: 6

                            Repeater {
                                model: delegateRoot.normalActions

                                RippleButton {
                                    id: actionButton

                                    required property var modelData

                                    implicitHeight: 34
                                    implicitWidth: Math.max(64, actionLabel.implicitWidth + 24)
                                    buttonRadius: Appearance.rounding.full
                                    containerColor: "transparent"
                                    stateLayerColor: Appearance.colors.colOnSurfaceVariant
                                    hoverStateLayerOpacity: 0.08
                                    focusStateLayerOpacity: 0.1
                                    pressedStateLayerOpacity: 0.12
                                    rippleColor: Appearance.colors.colOnSurfaceVariant
                                    Accessible.name: actionButton.modelData.text
                                    onClicked: root.manager.invokeAction(actionButton.modelData)

                                    contentItem: Text {
                                        id: actionLabel

                                        text: actionButton.modelData.text
                                        color: Appearance.colors.colOnSurfaceVariant
                                        font.family: Fonts.ui
                                        font.pixelSize: Appearance.scaledFont(12)
                                        font.weight: Font.Medium
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }
                    }
                }

                RippleButton {
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    Layout.alignment: Qt.AlignTop
                    visible: delegateRoot.replyable
                    buttonRadius: Appearance.rounding.full
                    containerColor: "transparent"
                    stateLayerColor: Appearance.colors.colOnSurfaceVariant
                    hoverStateLayerOpacity: 0.08
                    focusStateLayerOpacity: 0.1
                    pressedStateLayerOpacity: 0.12
                    rippleColor: Appearance.colors.colOnSurfaceVariant
                    Accessible.name: I18n.tr("Reply")
                    onClicked: {
                        delegateRoot.replying = !delegateRoot.replying;
                        if (delegateRoot.replying)
                            replyInput.forceActiveFocus(Qt.OtherFocusReason);
                    }
                    contentItem: Text {
                        text: "reply"
                        color: Appearance.colors.colOnSurfaceVariant
                        font.family: Fonts.materialSymbolsRounded
                        font.pixelSize: Appearance.scaledFont(20)
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                RippleButton {
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    Layout.alignment: Qt.AlignTop
                    buttonRadius: Appearance.rounding.full
                    containerColor: "transparent"
                    stateLayerColor: Appearance.colors.colOnSurfaceVariant
                    hoverStateLayerOpacity: 0.08
                    focusStateLayerOpacity: 0.1
                    pressedStateLayerOpacity: 0.12
                    rippleColor: Appearance.colors.colOnSurfaceVariant
                    Accessible.name: I18n.tr("Close")
                    onClicked: root.manager.dismissPopup(delegateRoot.modelData.notificationId)

                    contentItem: Text {
                        text: "close"
                        color: Appearance.colors.colOnSurfaceVariant
                        font.family: Fonts.materialSymbolsRounded
                        font.pixelSize: Appearance.scaledFont(20)
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Rectangle {
                id: replyBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: progressTrack.top
                anchors.bottomMargin: 6
                height: 40
                visible: delegateRoot.replying
                radius: Appearance.rounding.full
                color: Appearance.colors.colLayer2
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 6
                    spacing: 8
                    TextInput {
                        id: replyInput
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        color: Appearance.colors.colOnSurface
                        font.family: Fonts.ui
                        font.pixelSize: Appearance.scaledFont(12)
                        clip: true
                        selectByMouse: true
                        Accessible.name: root.manager.inlineReplyPlaceholder(delegateRoot.modelData)
                        onTextChanged: delegateRoot.replyText = text
                        onAccepted: replySend.activate()
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: replyInput.text.length === 0
                            text: root.manager.inlineReplyPlaceholder(delegateRoot.modelData)
                            color: Appearance.colors.colOnSurfaceVariant
                            font.family: Fonts.ui
                            font.pixelSize: Appearance.scaledFont(12)
                        }
                    }
                    RippleButton {
                        id: replySend
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        buttonRadius: Appearance.rounding.full
                        containerColor: "transparent"
                        stateLayerColor: Appearance.colors.colPrimary
                        rippleColor: Appearance.colors.colPrimary
                        Accessible.name: I18n.tr("Send")
                        function activate() {
                            if (delegateRoot.replyText.length === 0)
                                return;
                            if (root.manager.sendInlineReply(delegateRoot.modelData.notificationId, delegateRoot.replyText)) {
                                delegateRoot.replying = false;
                                delegateRoot.replyText = "";
                                replyInput.text = "";
                            }
                        }
                        onClicked: activate()
                        contentItem: Text {
                            text: "send"
                            color: Appearance.colors.colPrimary
                            font.family: Fonts.materialSymbolsRounded
                            font.pixelSize: Appearance.scaledFont(18)
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
            Rectangle {
                id: progressTrack

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: delegateRoot.hasExpiry ? 2 : 0
                radius: 1
                color: Appearance.colors.colLayer2
                visible: delegateRoot.hasExpiry

                Rectangle {
                    width: parent.width * delegateRoot.expiryProgress
                    height: parent.height
                    radius: parent.radius
                    color: Appearance.colors.colPrimary
                }
            }
        }
    }
}
