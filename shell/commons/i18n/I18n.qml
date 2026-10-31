pragma Singleton

import QtQuick
import Quickshell
import "Translations.js" as Trans

Singleton {
    id: root

    readonly property var supportedLanguages: [({
                                                    code: "en_US",
                                                    label: "English"
                                                }), ({
                                                         code: "zh_CN",
                                                         label: "简体中文"
                                                     })]
    property string language: "en_US"
    property int revision: 0
    property bool ready: true
    property string lastError: ""

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

    function loadTranslations(lang, dict) {
        Trans.loadTranslations(lang, dict);
        root.revision++;
    }

    function setLanguage(lang) {
        const normalized = root.normalizeLanguage(lang);
        root.language = normalized;
        Trans.setLanguage(normalized);
        root.revision++;
        if (Qt.uiLanguage === normalized)
            Qt.uiLanguage = normalized + "_refresh";
        Qt.uiLanguage = normalized;
        return true;
    }

    function tr(text, ctxOrCount, maybeCount) {
        var _rev = root.revision;
        if (root.language === "en_US" || !text)
            return text;
        return Trans.tr(text, ctxOrCount, maybeCount);
    }

    function t(text, ctxOrCount, maybeCount) {
        return root.tr(text, ctxOrCount, maybeCount);
    }

    onLanguageChanged: {
        Trans.setLanguage(root.language);
        root.revision++;
    }
}
