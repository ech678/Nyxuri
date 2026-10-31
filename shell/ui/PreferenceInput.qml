import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import qs.commons
import qs.ui
import qs.commons.i18n

// Text input row (Caelestia Nexus TextFieldRow): double-line label on the
// left, one compact rounded field on the right. The field border "breathes"
// to the primary colour on focus, validation failures flip it to the error
// colour and swap the subtext for `errorText`, and a clear button appears
// while the field holds text. Unflushed edits are flushed through
// editingFinished on destruction so closing a page never drops input.
ConnectedRect {
    id: root

    property alias label: titleLabel.text
    property string subtext: ""
    property string value: ""
    property alias placeholderText: input.placeholderText
    property string errorText: ""
    property alias maximumLength: input.maximumLength
    property var validate
    property bool emptyIsValid: true
    property bool smallField: false
    property real fieldWidth: 250 * Metrics.scale
    property real smallFieldWidth: 100 * Metrics.scale
    readonly property alias field: input
    readonly property bool valid: !validate || (!input.text && emptyIsValid) || (validate instanceof RegExp
                                                                                 ? validate.test(input.text) :
                                                                                   !!validate(input.text))

    property bool isError: false

    signal valueEdited(string value)
    signal editingFinished(string value)

    function clear(): void {
        input.clear();
    }

    Layout.fillWidth: true
    implicitHeight: column.implicitHeight + NexusStyle.padding.medium * 2

    Component.onDestruction: {
        if (value !== input.text)
            editingFinished(input.text);
    }

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.largeIncreased
        anchors.rightMargin: NexusStyle.padding.largeIncreased
        spacing: NexusStyle.padding.small

        ColumnLayout {
            id: column

            Layout.fillWidth: true
            spacing: 0

            StyledText {
                id: titleLabel

                Layout.fillWidth: true
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
                elide: Text.ElideRight
            }

            StyledText {
                Layout.fillWidth: true
                visible: root.subtext.length > 0 || (root.isError && root.errorText.length > 0)
                text: root.isError && root.errorText.length > 0 ? root.errorText : root.subtext
                color: root.isError && root.errorText.length > 0 ? Appearance.m3colors.m3error :
                                                                   Appearance.m3colors.m3outline
                font.pixelSize: NexusStyle.font.labelSmall
                elide: Text.ElideRight
            }
        }

        TextField {
            id: input

            Layout.preferredWidth: root.smallField ? root.smallFieldWidth : root.fieldWidth
            Layout.maximumWidth: root.width / 2
            Layout.alignment: Qt.AlignVCenter
            implicitHeight: NexusStyle.font.bodyMedium + NexusStyle.padding.small * 2
                            + NexusStyle.padding.extraSmall

            text: root.value
            color: Appearance.m3colors.m3onSurface
            selectionColor: Appearance.applyAlpha(Appearance.m3colors.m3primary, 0.4)
            selectedTextColor: color
            placeholderTextColor: Appearance.m3colors.m3onSurfaceVariant
            verticalAlignment: TextInput.AlignVCenter
            selectByMouse: true
            font.family: Fonts.ui
            font.pixelSize: NexusStyle.font.bodyMedium
            leftPadding: NexusStyle.padding.small
            rightPadding: NexusStyle.padding.small + (clearButton.visible ? clearButton.width : 0)

            onTextEdited: {
                if (root.isError)
                    root.isError = false;
                root.valueEdited(text);
            }
            onEditingFinished: {
                if (!root.valid)
                    root.isError = true;
                root.editingFinished(text);
            }

            background: Rectangle {
                radius: NexusStyle.rounding.small
                color: Appearance.m3colors.m3surfaceContainerHigh
                border.width: input.activeFocus ? 2 : 1
                border.color: root.isError ? Appearance.m3colors.m3error : input.activeFocus
                                             ? Appearance.m3colors.m3primary :
                                               Appearance.m3colors.m3outlineVariant

                // The breathing focus border.
                Behavior on border.color {
                    ColorAnimation {
                        duration: Appearance.animation.expressiveDefaultEffects.duration
                        easing.type: Appearance.animation.expressiveDefaultEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveDefaultEffects.bezierCurve
                    }
                }

                Behavior on border.width {
                    NumberAnimation {
                        duration: Appearance.animation.expressiveDefaultEffects.duration
                        easing.type: Appearance.animation.expressiveDefaultEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveDefaultEffects.bezierCurve
                    }
                }
            }

            IconButton {
                id: clearButton

                z: 1
                anchors.right: parent.right
                anchors.rightMargin: NexusStyle.padding.extraSmall
                anchors.verticalCenter: parent.verticalCenter
                width: NexusStyle.icon.small + NexusStyle.padding.small * 2
                height: NexusStyle.icon.small + NexusStyle.padding.small * 2
                controlSize: NexusStyle.icon.small + NexusStyle.padding.small * 2
                iconSize: NexusStyle.icon.small
                iconName: "clear"
                accessibleName: I18n.tr("Clear")
                showTooltip: false
                visible: input.text.length > 0 && input.enabled
                opacity: visible ? 1 : 0

                Behavior on opacity {
                    NumberAnimation {
                        duration: Appearance.animation.expressiveFastEffects.duration
                        easing.type: Appearance.animation.expressiveFastEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                    }
                }

                onClicked: {
                    input.clear();
                    input.forceActiveFocus();
                }
            }
        }
    }
}
