pragma Singleton

import QtQuick
import Quickshell
import Clavis.I18n

Singleton {
    id: root

    readonly property var supportedLanguages: [({
                                                    code: "en_US",
                                                    label: "English"
                                                }), ({
                                                         code: "zh_CN",
                                                         label: "简体中文"
                                                     })]
    readonly property string language: UiPreferences.language
    property bool ready: false
    property string lastError: ""

    function initialize() {
        const lang = root.language || "en_US";
        const hasManager = typeof I18nManager !== "undefined" && I18nManager;
        const success = hasManager ? I18nManager.setLanguage(lang) : false;
        root.ready = success;
        root.lastError = success ? "" : (hasManager ? I18nManager.lastError : "I18nManager unavailable");
        if (Qt.uiLanguage === lang)
            Qt.uiLanguage = lang + "_refresh";
        Qt.uiLanguage = lang;
        return success;
    }

    Component.onCompleted: initialize()

    Connections {
        target: UiPreferences

        function onLanguageChanged() {
            root.initialize();
        }
    }
}
