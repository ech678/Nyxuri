pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

Rectangle {
    id: root
    required property SpotlightStyle style
    required property SpotlightTemplateController templateController
    required property SpotlightCurrencyController currencyController
    readonly property bool currencyMode: service.tool === "currency"
    readonly property bool timeMode: service.tool === "time"
    readonly property bool structuredMode: currencyMode || timeMode
    readonly property var choices: currencyMode ? currencyController.choices : templateController.choices
    readonly property int candidateRowHeight: 52
    property real availableHeight: 360
    property int selectedCandidate: 0
    signal inputFocusRequested
    readonly property var service: SpotlightToolService
    height: visible ? Math.min(Math.max(root.structuredMode ? 40 : 120, content.implicitHeight + 48),
                               root.structuredMode ? 360 : 320, Math.max(0, availableHeight)) : 0
    radius: style.resultRadius
    color: style.panelColor
    clip: true
    Text {
        id: currencyNote
        x: 20
        y: 8
        width: parent.width - 40
        visible: root.structuredMode
        text: {
            const value = root.service.result;
            if (!root.service.canCopy || !value)
                return "";
            if (root.timeMode && value.source && value.target)
                return qsTr("UTC%1 → UTC%2 · Day difference: %3").arg(value.source.offset).arg(
                            value.target.offset).arg(value.dayDelta);
            if (!root.currencyMode || !value.approximate)
                return "";
            return qsTr("Approximate · ECB · %1 · %2").arg(value.date).arg(value.cache === "stale" ? qsTr(
                                                                                                         "Older cached rate") :
                                                                                                     qsTr("Reference rate"));
        }
        textFormat: Text.PlainText
        elide: Text.ElideRight
        font.family: Fonts.ui
        font.pixelSize: 12
        color: Appearance.colors.colOnSurfaceVariant
    }
    StyledFlickable {
        anchors.fill: parent
        anchors.margins: 24
        anchors.topMargin: root.structuredMode ? 32 : 24
        anchors.bottomMargin: root.structuredMode ? 16 : 24
        contentWidth: width
        contentHeight: content.implicitHeight
        ScrollBar.vertical: StyledScrollBar {}
        ColumnLayout {
            id: content
            width: parent.width
            spacing: 16
            ListView {
                id: templateList
                Layout.fillWidth: true
                Layout.preferredHeight: !visible ? 0 : Math.min(Math.min(root.choices.length, 6) * root.candidateRowHeight,
                                                                Math.max(0, root.availableHeight - 48))
                visible: root.choices.length > 0
                model: root.choices
                currentIndex: root.currencyMode ? root.currencyController.selected :
                                                  root.templateController.selected
                clip: true
                keyNavigationEnabled: false
                onCurrentIndexChanged: if (currentIndex >= 0)
                                           positionViewAtIndex(currentIndex, ListView.Contain)
                ScrollBar.vertical: StyledScrollBar {}
                delegate: Rectangle {
                    id: choiceRow
                    required property var modelData
                    required property int index
                    width: templateList.width
                    height: root.candidateRowHeight
                    radius: Appearance.rounding.small
                    color: index === templateList.currentIndex ? root.style.selectedColor : "transparent"
                    Text {
                        anchors.fill: parent
                        anchors.margins: 14
                        verticalAlignment: Text.AlignVCenter
                        text: choiceRow.modelData.text + (choiceRow.modelData.name
                                                          && choiceRow.modelData.name
                                                          !== choiceRow.modelData.text ? " · "
                                                                                         + choiceRow.modelData.name :
                                                                                         "")
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        color: Appearance.colors.colOnSurface
                        font.family: Fonts.ui
                        font.pixelSize: 16
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (root.currencyMode)
                                root.currencyController.choose(choiceRow.index);
                            else
                                root.templateController.choose(choiceRow.index);
                            root.inputFocusRequested();
                        }
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                text: root.currencyMode ? (root.currencyController.amountError || root.service.error || (
                                               root.currencyController.choosing && !root.choices.length ? qsTr(
                                                                                                              "No matching currencies") :
                                                                                                          "")) : root.timeMode
                                          && root.templateController.choosing && !root.choices.length ? qsTr(
                                                                                                            "No matching time zones") :
                                                                                                        root.service.state
                                                                                                        === "loading"
                                                                                                        ? qsTr("Calculating…") :
                                                                                                          root.service.state
                                                                                                          === "empty"
                                                                                                          || root.service.state
                                                                                                          === "incomplete"
                                                                                                          ? qsTr("Enter an expression to begin") :
                                                                                                            root.service.state
                                                                                                            === "ambiguous"
                                                                                                            ? qsTr("This time occurs twice. Choose a UTC offset.") :
                                                                                                              root.service.error
                visible: text.length > 0 && (!root.templateController.active
                                             || root.templateController.choosing || (root.service.state
                                                                                     !== "empty"
                                                                                     && root.service.state
                                                                                     !== "incomplete"))
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: root.service.state === "error" || root.service.state === "unavailable"
                       ? Appearance.colors.colError : Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
                font.pixelSize: 16
            }
            Text {
                Layout.fillWidth: true
                visible: root.service.canCopy && !root.structuredMode
                text: root.service.canCopy ? root.service.result.answer : ""
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                color: Appearance.colors.colOnSurface
                font.family: Fonts.ui
                font.pixelSize: 28
            }
            Repeater {
                model: root.service.state === "ambiguous" && root.service.result ? root.service.result.candidates :
                                                                                   []
                delegate: ActionButton {
                    required property var modelData
                    required property int index
                    filled: index === root.selectedCandidate
                    text: "UTC" + modelData.offset
                    onClicked: {
                        root.service.confirmFold(modelData.fold);
                        root.inputFocusRequested();
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: !root.structuredMode && text.length > 0
                text: root.service.feedback || (root.service.canCopy ? qsTr("Enter to copy") : "")
                textFormat: Text.PlainText
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
                font.pixelSize: 14
            }
        }
    }
}
