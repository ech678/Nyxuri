// Pure parsing and math for the shell self-sampler (R11). No Qt, no I/O: the
// service feeds /proc text in and consumes plain numbers out, which keeps the
// sampler behavior testable without a live process tree.
//
// CPU% follows ps(1) %cpu semantics: unnormalized against core count, so a
// busy thread on one core reads up to 100 while a multi-threaded process can
// exceed 100. Linux exports USER_HZ as a fixed 100 from userspace.

.pragma library

function parseVmRssKb(statusText) {
    var match = String(statusText || "").match(/^VmRSS:\s+(\d+)\s+kB/m);
    return match ? Number(match[1]) : -1;
}

function parseCpuJiffies(statText) {
    // /proc/<pid>/stat fields 14-17 (utime, stime, cutime, cstime). comm may
    // contain spaces inside parentheses, so split after the last ")" and use
    // 1-based field offsets from there: state is tail[0] (field 3), utime is
    // field 14 → tail[11].
    var text = String(statText || "");
    var separator = text.lastIndexOf(")");
    if (separator < 0)
        return -1;
    var tail = text.substring(separator + 1).trim().split(/\s+/);
    if (tail.length < 14)
        return -1;
    var utime = Number(tail[11]);
    var stime = Number(tail[12]);
    if (!isFinite(utime) || !isFinite(stime) || utime < 0 || stime < 0)
        return -1;
    return utime + stime;
}

function percentFromJiffies(currentJiffies, previousJiffies, elapsedMs) {
    var current = Number(currentJiffies);
    var previous = Number(previousJiffies);
    var elapsed = Number(elapsedMs);
    if (!isFinite(current) || !isFinite(previous) || !isFinite(elapsed))
        return -1;
    if (current < 0 || previous < 0 || elapsed <= 0)
        return -1;
    var cpuSeconds = (current - previous) / 100;
    var percent = cpuSeconds / (elapsed / 1000) * 100;
    if (!isFinite(percent) || percent < 0)
        return -1;
    return Math.min(percent, 10000);
}
