.pragma library

function elapsed(milliseconds) {
    const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const twoDigits = value => String(value).padStart(2, "0");
    return hours > 0
        ? twoDigits(hours) + ":" + twoDigits(minutes) + ":" + twoDigits(seconds)
        : twoDigits(minutes) + ":" + twoDigits(seconds);
}
