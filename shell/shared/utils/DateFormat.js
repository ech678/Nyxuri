.pragma library

function isChinese(language) {
    return String(language || "").toLowerCase().startsWith("zh");
}

function isTraditionalChinese(language) {
    return String(language || "").toLowerCase() === "zh_tw";
}

function shortWeekdays(language) {
    const prefix = isTraditionalChinese(language) ? "\u9031" : "\u5468";
    return [
        prefix + "\u65e5",
        prefix + "\u4e00",
        prefix + "\u4e8c",
        prefix + "\u4e09",
        prefix + "\u56db",
        prefix + "\u4e94",
        prefix + "\u516d"
    ];
}

function compactDate(date, language, locale, fallbackPattern) {
    if (isChinese(language)) {
        return (date.getMonth() + 1)
            + "\u6708"
            + date.getDate()
            + "\u65e5"
            + shortWeekdays(language)[date.getDay()];
    }
    return date.toLocaleDateString(locale, fallbackPattern);
}

function calendarWeekdays(language) {
    if (isChinese(language)) {
        return [
            "\u4e00", "\u4e8c", "\u4e09", "\u56db",
            "\u4e94", "\u516d", "\u65e5"
        ];
    }
    return ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
}

function monthTitle(date, language, locale) {
    if (isChinese(language)) {
        return date.getFullYear()
            + "\u5e74"
            + (date.getMonth() + 1)
            + "\u6708";
    }
    return date.toLocaleDateString(locale, "MMMM yyyy");
}
