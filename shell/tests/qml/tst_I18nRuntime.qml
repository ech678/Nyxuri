import QtQuick
import QtTest
import "../../shared/i18n/Translations.js" as Trans

TestCase {
    name: "I18nRuntime"

    function init() {
        Trans.setLanguage("en_US");
        Trans.loadTranslations("en_US", {});
        Trans.loadTranslations("zh_CN", {});
    }

    function test_sourceLanguageReturnsInput() {
        Trans.setLanguage("en_US");
        compare(Trans.tr("Settings"), "Settings");
        compare(Trans.tr(""), "");
        compare(Trans.tr(null), "");
    }

    function test_translatedLanguageResolvesDictionary() {
        Trans.loadTranslations("zh_CN", {
            "Settings": "设置",
            "Space": "空格"
        });
        Trans.setLanguage("zh_CN");
        compare(Trans.tr("Settings"), "设置");
        compare(Trans.tr("Space"), "空格");
    }

    function test_missingKeyFallsBackToSource() {
        Trans.setLanguage("zh_CN");
        compare(Trans.tr("Not translated yet"), "Not translated yet");
    }

    function test_contextOverrideWinsOverGlobal() {
        Trans.loadTranslations("zh_CN", {
            "Clear": "清除",
            "ControlCenterWindow": {
                "Clear": "清空"
            }
        });
        Trans.setLanguage("zh_CN");
        compare(Trans.tr("Clear", "ControlCenterWindow"), "清空");
        compare(Trans.tr("Clear", "UnknownContext"), "清除");
    }

    function test_pluralCountReplacement() {
        Trans.loadTranslations("zh_CN", {
            "%n minutes": "%n 分钟"
        });
        Trans.setLanguage("zh_CN");
        compare(Trans.tr("%n minutes", 5), "5 分钟");
    }

    function test_languageSwitchIsImmediate() {
        Trans.loadTranslations("zh_CN", {
            "Volume": "音量"
        });
        Trans.setLanguage("zh_CN");
        compare(Trans.tr("Volume"), "音量");
        Trans.setLanguage("en_US");
        compare(Trans.tr("Volume"), "Volume");
        Trans.setLanguage("zh_CN");
        compare(Trans.tr("Volume"), "音量");
    }

    function test_emptyDictionaryDoesNotThrow() {
        Trans.setLanguage("zh_CN");
        compare(Trans.tr("Anything"), "Anything");
        Trans.loadTranslations("zh_CN", null);
        compare(Trans.tr("Anything"), "Anything");
    }
}