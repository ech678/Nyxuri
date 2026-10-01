.pragma library

function humanReadableSize(value) {
    if (value === null || value === undefined) return "";
    const bytes = Number(value);
    if (!isFinite(bytes) || bytes < 0)
        return "";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let amount = bytes;
    let unit = 0;
    while (amount >= 1024 && unit < units.length - 1) {
        amount /= 1024;
        unit += 1;
    }
    const digits = unit === 0 || amount >= 100 ? 0 : amount >= 10 ? 1 : 2;
    return amount.toFixed(digits) + " " + units[unit];
}

