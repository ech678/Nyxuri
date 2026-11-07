.pragma library
.import "SpotlightAppOrder.js" as AppOrder

function normalized(value) {
    return String(value || "").trim().toLocaleLowerCase();
}

function isWordStart(text, query) {
    if (text.startsWith(query))
        return true;
    for (let index = 1; index < text.length; index += 1) {
        const previous = text.charAt(index - 1);
        if ((previous === " " || previous === "-" || previous === "_" || previous === "." || previous
             === "/") && text.indexOf(query, index) === index)
            return true;
    }
    return false;
}

function subsequencePenalty(text, query) {
    let queryIndex = 0;
    let firstIndex = -1;
    let lastIndex = -1;
    for (let index = 0; index < text.length && queryIndex < query.length; index += 1) {
        if (text.charAt(index) !== query.charAt(queryIndex))
            continue;
        if (firstIndex < 0)
            firstIndex = index;
        lastIndex = index;
        queryIndex += 1;
    }
    if (queryIndex !== query.length)
        return -1;
    return Math.max(0, lastIndex - firstIndex - query.length + 1);
}

function fieldScore(value, needle, weight) {
    const text = normalized(value);
    if (text === "" || needle === "")
        return needle === "" ? weight : -1;
    if (text === needle)
        return 5000 + weight;
    if (text.startsWith(needle))
        return 4000 + weight - Math.min(99, text.length - needle.length);
    if (isWordStart(text, needle))
        return 3000 + weight;
    const substringIndex = text.indexOf(needle);
    if (substringIndex >= 0)
        return 2000 + weight - Math.min(99, substringIndex);
    const penalty = subsequencePenalty(text, needle);
    return penalty >= 0 ? 1000 + weight - Math.min(99, penalty) : -1;
}

function appScore(app, needle) {
    if (needle === "")
        return 0;
    let best = -1;
    best = Math.max(best, fieldScore(app.name, needle, 80));
    best = Math.max(best, fieldScore(app.genericName, needle, 60));
    best = Math.max(best, fieldScore(Array.from(app.keywords || []).join(" "), needle, 40));
    best = Math.max(best, fieldScore(app.id, needle, 20));
    return best;
}

function compareAppCandidates(left, right, stats) {
    if (stats) stats.orderComparisons += 1;
    if (left.score !== right.score)
        return right.score - left.score;
    if (left.usageScore !== right.usageScore)
        return right.usageScore - left.usageScore;
    const byName = left.title.localeCompare(right.title);
    if (byName !== 0)
        return byName;
    const byId = left.id.localeCompare(right.id);
    return byId !== 0 ? byId : left.sourceIndex - right.sourceIndex;
}

function siftWorstDown(heap, index, stats) {
    while (true) {
        const left = index * 2 + 1;
        if (left >= heap.length)
            return;
        const right = left + 1;
        let worse = left;
        if (right < heap.length && compareAppCandidates(heap[right], heap[left], stats) > 0)
            worse = right;
        if (compareAppCandidates(heap[index], heap[worse], stats) >= 0)
            return;
        const value = heap[index];
        heap[index] = heap[worse];
        heap[worse] = value;
        index = worse;
    }
}

function appResult(candidate, stats) {
    if (stats) stats.uiResultRecordsBuilt += 1;
    const app = candidate.app;
    return {provider: "apps", id: candidate.id, title: candidate.title,
        subtitle: String(app.genericName || app.comment || app.id || ""),
        icon: String(app.icon || ""), symbol: String(app.symbol || ""), score: candidate.score,
        appObject: app, actions: app.dragOnly ? [] : ["launch"]};
}

function copyCandidate(target, source, stats) {
    if (!target) {
        target = {};
        if (stats) stats.rankingRecordsBuilt += 1;
    }
    target.app = source.app;
    target.id = source.id;
    target.title = source.title;
    target.score = source.score;
    target.usageScore = source.usageScore;
    target.sourceIndex = source.sourceIndex;
    return target;
}

function appResults(source, query, options) {
    const settings = options || {};
    const order = settings.order;
    const history = settings.history;
    const now = settings.now;
    const limit = settings.limit;
    const retainedId = settings.retainedId;
    const stats = settings.stats;
    const needle = normalized(query);
    const bounded = typeof limit === "number" && isFinite(limit) && limit > 0;
    const capacity = bounded ? Math.max(1, Math.floor(limit)) : 0;
    if (stats) {
        stats.appScoreCalls = 0;
        stats.orderComparisons = 0;
        stats.rankingRecordsBuilt = 0;
        stats.uiResultRecordsBuilt = 0;
    }
    if (bounded && capacity < source.length) {
        // Reuse one probe while the max-heap retains only the visible slice.
        const selectedOrder = AppOrder.normalizedOrder(order);
        const heap = [];
        const probe = {};
        let retained = null;
        source.forEach((app, sourceIndex) => {
            if (!app) return;
            if (stats) stats.appScoreCalls += 1;
            const score = appScore(app, needle);
            if (score < 0) return;
            const id = String(app.id);
            probe.app = app;
            probe.id = id;
            probe.title = String(app.name || app.id);
            probe.score = score;
            probe.usageScore = AppOrder.usageScore(selectedOrder, history && history[id], now);
            probe.sourceIndex = sourceIndex;
            if (id === String(retainedId || "")
                    && (!retained || compareAppCandidates(probe, retained, stats) < 0))
                retained = copyCandidate(retained, probe, stats);
            if (heap.length < capacity) {
                heap.push(copyCandidate(null, probe, stats));
                let index = heap.length - 1;
                while (index > 0) {
                    const parent = Math.floor((index - 1) / 2);
                    if (compareAppCandidates(heap[parent], heap[index], stats) >= 0)
                        break;
                    const value = heap[parent];
                    heap[parent] = heap[index];
                    heap[index] = value;
                    index = parent;
                }
            } else if (compareAppCandidates(probe, heap[0], stats) < 0) {
                copyCandidate(heap[0], probe, stats);
                siftWorstDown(heap, 0, stats);
            }
        });
        heap.sort((left, right) => compareAppCandidates(left, right, stats));
        if (retained && !heap.some(candidate => candidate.sourceIndex === retained.sourceIndex))
            heap.push(retained);
        return heap.map(candidate => appResult(candidate, stats));
    }

    const next = [];
    source.forEach((app, sourceIndex) => {
        if (!app) return;
        if (stats) stats.appScoreCalls += 1;
        const score = appScore(app, needle);
        if (score < 0) return;
        next.push({provider: "apps", id: String(app.id), title: String(app.name || app.id),
            subtitle: String(app.genericName || app.comment || app.id || ""),
            icon: String(app.icon || ""), symbol: String(app.symbol || ""), score: score, appObject: app,
            sourceIndex: sourceIndex, actions: app.dragOnly ? [] : ["launch"]});
    });
    const sorted = AppOrder.sortedResults(next, order, history, now);
    if (stats) {
        const selectedOrder = AppOrder.normalizedOrder(order);
        next.slice().sort((left, right) => {
            stats.orderComparisons += 1;
            if (left.score !== right.score)
                return right.score - left.score;
            const usage = AppOrder.usageScore(selectedOrder, history && history[right.id], now)
                        - AppOrder.usageScore(selectedOrder, history && history[left.id], now);
            if (usage !== 0)
                return usage;
            const byName = left.title.localeCompare(right.title);
            if (byName !== 0)
                return byName;
            return left.id.localeCompare(right.id);
        });
        stats.rankingRecordsBuilt = 0;
        stats.uiResultRecordsBuilt = next.length;
    }
    return sorted;
}
