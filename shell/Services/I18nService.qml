pragma Singleton

import QtQuick
import Quickshell
import Clavis.I18n

Singleton {
    id: root

    readonly property var supportedLanguages: [
        ({ code: "en_US", label: "English" }),
        ({ code: "zh_CN", label: "\u7b80\u4f53\u4e2d\u6587" }),
        ({ code: "zh_TW", label: "\u7e41\u9ad4\u4e2d\u6587" })
    ]
    readonly property string language: UiPreferences.language
    property bool ready: false
    property string lastError: ""

    function initialize() {
        const success = I18nManager.setLanguage(root.language);
        root.ready = success;
        root.lastError = success ? "" : I18nManager.lastError;
        if (success) {
            if (Qt.uiLanguage === root.language)
                Qt.uiLanguage = root.language + "_refresh";
            Qt.uiLanguage = root.language;
        }
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
