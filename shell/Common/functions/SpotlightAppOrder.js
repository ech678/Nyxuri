.pragma library

function normalizedOrder(value) {
    return ["smart", "most-used", "recently-used", "name"].indexOf(value) >= 0 ? value : "name";
}

function safeNumber(value) {
    return typeof value === "number" && isFinite(value) && value >= 0
        ? Math.min(Number.MAX_SAFE_INTEGER, Math.floor(value)) : 0;
}

function record(value) {
    return {
        launchCount: safeNumber(value && value.launchCount),
        lastLaunchedAt: safeNumber(value && value.lastLaunchedAt)
    };
}

function normalizeHistory(value) {
    const result = Object.create(null);
    if (!value || typeof value !== "object" || Array.isArray(value)) return result;
    Object.keys(value).forEach(id => {
        if (id.trim() === "") return;
        const entry = record(value[id]);
        if (entry.launchCount > 0) result[id] = entry;
    });
    return result;
}

function decodeHistory(text) {
    try {
        const value = JSON.parse(text);
        if (!value || value.schemaVersion !== 1 || !value.applications
            || typeof value.applications !== "object" || Array.isArray(value.applications)) return null;
        return normalizeHistory(value.applications);
    } catch (error) {
        return null;
    }
}

function addLaunch(history, id, now) {
    const next = normalizeHistory(history);
    if (typeof id !== "string" || id.trim() === "") return next;
    const previous = record(next[id]);
    next[id] = {
        launchCount: Math.min(Number.MAX_SAFE_INTEGER, previous.launchCount + 1),
        lastLaunchedAt: Math.max(previous.lastLaunchedAt, safeNumber(now))
    };
    return next;
}

// Launches can arrive before the asynchronous initial read completes.
function mergePending(history, pending) {
    const next = normalizeHistory(history);
    Object.keys(pending).forEach(id => {
        const previous = record(next[id]);
        const extra = record(pending[id]);
        next[id] = {
            launchCount: Math.min(Number.MAX_SAFE_INTEGER, previous.launchCount + extra.launchCount),
            lastLaunchedAt: Math.max(previous.lastLaunchedAt, extra.lastLaunchedAt)
        };
    });
    return next;
}

function usageScore(order, value, now) {
    const entry = record(value);
    if (order === "most-used") return entry.launchCount;
    if (order === "recently-used") return entry.lastLaunchedAt;
    if (order !== "smart" || entry.launchCount === 0) return 0;
    const hours = Math.max(0, now - entry.lastLaunchedAt) / 3600000;
    const bonus = entry.lastLaunchedAt === 0 ? 0 : hours < 1 ? 8 : hours < 24 ? 6
        : hours < 168 ? 4 : hours < 720 ? 2 : 0;
    return Math.log2(entry.launchCount + 1) + bonus;
}

function sortedResults(results, order, history, now) {
    const selectedOrder = normalizedOrder(order);
    return results.slice().sort((left, right) => {
        // Usage never overrides the existing keyword relevance score.
        if (left.score !== right.score) return right.score - left.score;
        const usage = usageScore(selectedOrder, history[right.id], now)
                    - usageScore(selectedOrder, history[left.id], now);
        if (usage !== 0) return usage;
        const byName = left.title.localeCompare(right.title);
        return byName !== 0 ? byName : left.id.localeCompare(right.id);
    });
}
