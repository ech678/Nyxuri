pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property var supportedLanguages: [({
                                                    code: "en_US",
                                                    label: "English"
                                                }), ({
                                                         code: "zh_CN",
                                                         label: "简体中文"
                                                     })]
    readonly property string language: UiPreferences.language || "en_US"
    property bool ready: true
    property string lastError: ""

    readonly property string systemLanguage: {
        const l = (Quickshell.env("LANG") || Quickshell.env("LC_ALL") || "").toLowerCase();
        return l.startsWith("zh") ? "zh_CN" : "en_US";
    }

    function normalizeLanguage(lang) {
        const s = String(lang || "").trim().toLowerCase();
        return s.startsWith("zh") ? "zh_CN" : "en_US";
    }

    function preferredLanguage(languages) {
        if (!languages || languages.length === 0)
            return "en_US";
        for (let i = 0; i < languages.length; ++i) {
            const s = String(languages[i] || "").toLowerCase();
            if (s.startsWith("zh"))
                return "zh_CN";
            if (s.startsWith("en"))
                return "en_US";
        }
        return "en_US";
    }

    function setLanguage(lang) {
        const normalized = root.normalizeLanguage(lang);
        if (typeof UiPreferences.setLanguage === "function")
            UiPreferences.setLanguage(normalized);
        else
            UiPreferences.language = normalized;
        return root.initialize();
    }

    function initialize() {
        const lang = root.language || "en_US";
        root.ready = true;
        root.lastError = "";
        if (Qt.uiLanguage === lang)
            Qt.uiLanguage = lang + "_refresh";
        Qt.uiLanguage = lang;
        return true;
    }

    Component.onCompleted: initialize()

    Connections {
        target: UiPreferences

        function onLanguageChanged() {
            root.initialize();
        }
    }
}
