.pragma library

// ==============================================================================
// Nyxuri Shell - Pure QML/JS Translation Catalog & State
// Managed dynamically at runtime from shell/assets/i18n/*.toml via Toml.js
// ==============================================================================

var currentLanguage = "en_US";
var dictionaries = {};

function setLanguage(lang) {
    currentLanguage = lang || "en_US";
}

function getLanguage() {
    return currentLanguage;
}

function loadTranslations(lang, dict) {
    if (!lang) return;
    dictionaries[lang] = dict || {};
}

function tr(text, ctxOrCount, maybeCount) {
    if (!text) return "";
    if (currentLanguage === "en_US") {
        if (typeof ctxOrCount === "number") {
            return String(text).replace(/%n/g, ctxOrCount);
        }
        if (typeof maybeCount === "number") {
            return String(text).replace(/%n/g, maybeCount);
        }
        return String(text);
    }

    var ctx = "";
    var count = undefined;

    if (typeof ctxOrCount === "string") {
        ctx = ctxOrCount;
        if (typeof maybeCount === "number") {
            count = maybeCount;
        }
    } else if (typeof ctxOrCount === "number") {
        count = ctxOrCount;
    }

    var dict = dictionaries[currentLanguage] || {};
    var translation = undefined;

    if (ctx && dict[ctx] && typeof dict[ctx] === "object" && dict[ctx][text] !== undefined) {
        translation = dict[ctx][text];
    } else if (dict[text] !== undefined) {
        translation = dict[text];
    }

    if (translation === undefined) {
        translation = text;
    }

    if (count !== undefined) {
        translation = String(translation).replace(/%n/g, count);
    }

    return String(translation);
}

function t(text, ctxOrCount, maybeCount) {
    return tr(text, ctxOrCount, maybeCount);
}
