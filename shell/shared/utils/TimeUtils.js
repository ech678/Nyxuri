.pragma library
.import "../i18n/Translations.js" as I18n


function getRelativeTime(timestampMs) {
    if (!timestampMs) return I18n.tr("Just now");

    var now = Date.now();
    var diffSeconds = Math.floor((now - timestampMs) / 1000);

    if (diffSeconds < 60) {
        return I18n.tr("Just now");
    }

    var diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) {
        return I18n.tr("%n minute(s) ago", diffMinutes);
    }

    var diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) {
        return I18n.tr("%n hour(s) ago", diffHours);
    }

    return I18n.tr("More than a day ago");
}
