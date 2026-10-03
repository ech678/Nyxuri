pragma Singleton
import QtQuick

QtObject {
    id: root

    property string language: "en_US"
    readonly property string systemLanguage: {
        const l = (Quickshell.env("LANG") || Quickshell.env("LC_ALL") || "").toLowerCase();
        return l.startsWith("zh") ? "zh_CN" : "en_US";
    }
    property string lastError: ""

    signal languageChanged
    signal lastErrorChanged

    function normalizeLanguage(lang) {
        return String(lang || "").toLowerCase().startsWith("zh") ? "zh_CN" : "en_US";
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
        root.language = root.normalizeLanguage(lang);
        return false;
    }
}
