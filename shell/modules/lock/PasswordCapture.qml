import QtQuick
import qs.shared.i18n

// Raw keyboard password capture for the session-lock surface.
//
// The lock surface must never instantiate TextInput/TextField: with
// QT_IM_MODULE=fcitx the Qt input context activates on focus, and fcitx5-qt
// can raise a parentless xdg_popup from the session-lock surface, which niri
// rejects with a fatal protocol error ("xdg_popup must have parent before
// mapping"). The shell then dies while the session stays locked and niri
// falls back to its solid red dead-locker screen. Key events are accumulated
// here instead, so the input method is never engaged on the lock surface.
FocusScope {
    id: root

    required property var context
    readonly property bool busy: context && context.unlockInProgress
    readonly property int maxLength: 512

    // Emitted for every key press after processing, so styles can layer their
    // own reactions (auth reveal, escape-to-clock) on top of shared handling.
    signal keyPressed(var event)

    function forceAuthFocus() {
        root.forceActiveFocus();
    }

    function focusAuth() {
        forceAuthFocus();
    }

    Keys.onPressed: event => {
        if (event.key === Qt.Key_Backspace) {
            if (!root.busy && root.context.currentText.length > 0)
                root.context.currentText = root.context.currentText.slice(0, -1);
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (!root.busy && root.context.currentText !== "")
                root.context.tryUnlock();
        } else if (event.key === Qt.Key_Escape) {
            if (!root.busy) {
                root.context.currentText = "";
                root.context.showFailure = false;
            }
        } else if (event.modifiers & (Qt.ControlModifier | Qt.MetaModifier | Qt.AltModifier)) {
            // Swallow shortcuts: no clipboard or command access on the lock surface.
        } else {
            const character = event.text;
            if (!root.busy && character.length === 1 && character.charCodeAt(0) >= 32
                    && root.context.currentText.length < root.maxLength)
                root.context.currentText += character;
        }
        event.accepted = true;
        root.keyPressed(event);
    }

    Component.onCompleted: root.forceActiveFocus()

    Accessible.role: Accessible.EditableText
    Accessible.name: I18n.tr("Password")
    Accessible.description: root.context && root.context.showFailure ? I18n.tr("Incorrect password") : ""
}
