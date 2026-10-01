import QtQuick
import QtQuick.Layouts
import qs.Common

ColumnLayout {
    id: root
    required property string title
    required property string description
    required property string integrationState
    property bool busy: false
    property bool blocked: false
    property string error: ""
    signal setupRequested
    visible: integrationState !== "ready" && (integrationState !== "loading" || error.length > 0)
    spacing: Metrics.spacingS

    SettingsRow {
        Layout.fillWidth: true
        title: qsTr("First-time setup")
        iconName: "warning"
        color: Appearance.applyAlpha(Appearance.colors.colPrimary, 0.1)
        supportingText: root.integrationState === "unsupported" ? qsTr("Available in a niri session") :
                                                                  root.description || root.title
        trailing: ActionButton {
            text: qsTr("Set up")
            enabled: !root.busy && !root.blocked && root.integrationState !== "unsupported"
                     && root.integrationState !== "loading"

            onClicked: root.setupRequested()
        }
    }
    InlineStatusBanner {
        Layout.fillWidth: true
        visible: root.error !== ""
        tone: "error"
        message: root.error
    }
}
