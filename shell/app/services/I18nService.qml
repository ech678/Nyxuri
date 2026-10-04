pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import qs.shared.i18n
import "../../shared/utils/Toml.js" as Toml

Singleton {
    id: root

    readonly property var supportedLanguages: [
        {
            code: "en_US",
            label: "English"
        },
        {
            code: "zh_CN",
            label: "简体中文"
        }
    ]
    readonly property string language: UiPreferences.language || "en_US"
    property bool ready: true
    property string lastError: ""

    readonly property string systemLanguage: {
        const l = (Quickshell.env("LANG") || Quickshell.env("LC_ALL") || "").toLowerCase();
        return l.startsWith("zh") ? "zh_CN" : "en_US";
    }

    FileView {
        id: tomlFileView
        path: root.language === "en_US" ? "" : (Paths.assetsDir + "/i18n/" + root.language + ".toml")

        onLoaded: {
            if (root.language === "en_US")
                return;
            try {
                const text = tomlFileView.text();
                if (text && text.length > 0) {
                    const parsed = Toml.parse(text);
                    I18n.loadTranslations(root.language, parsed);
                }
            } catch (e) {
                root.lastError = String(e);
                console.warn("[I18nService] Failed to parse TOML translations for", root.language, e);
            }
        }
    }

    function normalizeLanguage(lang) {
        return I18n.normalizeLanguage(lang);
    }

    function preferredLanguage(languages) {
        return I18n.preferredLanguage(languages);
    }

    function setLanguage(lang) {
        const normalized = root.normalizeLanguage(lang);
        if (typeof UiPreferences.setLanguage === "function")
            UiPreferences.setLanguage(normalized);
        else
            UiPreferences.language = normalized;
        I18n.setLanguage(normalized);
        return root.initialize();
    }

    function initialize() {
        const lang = root.language || "en_US";
        root.ready = true;
        root.lastError = "";
        I18n.setLanguage(lang);
        if (lang !== "en_US") {
            const targetPath = Paths.assetsDir + "/i18n/" + lang + ".toml";
            if (tomlFileView.path !== targetPath) {
                tomlFileView.path = targetPath;
            } else if (tomlFileView.text().length > 0) {
                try {
                    const parsed = Toml.parse(tomlFileView.text());
                    I18n.loadTranslations(lang, parsed);
                } catch (e) {
                    root.lastError = String(e);
                }
            }
        }
        if (Qt.uiLanguage === lang)
            Qt.uiLanguage = lang + "_refresh";
        Qt.uiLanguage = lang;
        return true;
    }

    function tr(text, ctx, count) {
        return I18n.tr(text, ctx, count);
    }

    function t(text, ctx, count) {
        return I18n.t(text, ctx, count);
    }

    Component.onCompleted: initialize()

    Connections {
        target: UiPreferences

        function onLanguageChanged() {
            root.initialize();
        }
    }
}
