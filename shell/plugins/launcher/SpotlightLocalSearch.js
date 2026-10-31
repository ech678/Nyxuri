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

function appResults(source, query, order, history, now) {
    const needle = normalized(query);
    const next = [];
    source.forEach(app => {
        if (!app) return;
        const score = appScore(app, needle);
        if (score < 0) return;
        next.push({provider: "apps", id: String(app.id), title: String(app.name || app.id),
            subtitle: String(app.genericName || app.comment || app.id || ""),
            icon: String(app.icon || ""), symbol: String(app.symbol || ""), score: score, appObject: app, actions: app.dragOnly ? [] : ["launch"]});
    });
    return AppOrder.sortedResults(next, order, history, now);
}

function wallpaperPaths(source, query, basename) {
    const needle = normalized(query);
    return source.filter(path => path && normalized(basename(path)).indexOf(needle) >= 0).slice().sort((a,b) => {
        const left = basename(a), right = basename(b);
        if (needle) {
            const difference = Number(normalized(right).startsWith(needle)) - Number(normalized(left).startsWith(needle));
            if (difference) return difference;
        }
        return left.localeCompare(right);
    });
}

function catalogScore(entry, needle) {
    const titles = [entry.title, entry.sourceTitle].map(normalized);
    if (titles.some(title => title === needle)) return 4;
    if (titles.some(title => title.startsWith(needle))) return 3;
    const aliases = (entry.aliases || []).map(normalized);
    if (titles.concat(aliases).some(title => isWordStart(title, needle))) return 2;
    return titles.concat(aliases).some(title => title.indexOf(needle) >= 0) ? 1 : -1;
}
function matchCatalog(entries, query) {
    const needle = normalized(query);
    if (!needle) return [];
    return entries.map(entry => ({entry: entry, score: catalogScore(entry, needle)}))
        .filter(item => item.score >= 0)
        .sort((a,b) => b.score - a.score || a.entry.title.localeCompare(b.entry.title) || a.entry.id.localeCompare(b.entry.id))
        .map(item => item.entry);
}

var budgets = {apps: 6, settings: 2, actions: 2, wallpapers: 4};
var groups = ["apps", "settings", "actions", "wallpapers"];
function horizontalGroup(group) {
    return group === "apps" || group === "wallpapers";
}
function groupCapacity(group, capacities) {
    return horizontalGroup(group) ? Math.max(2, Math.floor(Number((capacities || {})[group]) || budgets[group]))
                                  : budgets[group];
}
function groupedResults(matches, query, labels, capacities, retainedId) {
    if (!normalized(query)) return [];
    const results = [];
    groups.forEach(group => {
        const entries = matches[group] || [];
        const capacity = groupCapacity(group, capacities);
        const visible = entries.slice(0, capacity);
        // Keep an existing selection visible without expanding the compact budget.
        const retained = entries.findIndex(entry => group + ":" + entry.id === retainedId);
        if (retained >= capacity) visible[capacity - 1] = entries[retained];
        for (let i = 0; i < visible.length; ++i) {
            results.push(Object.assign({}, visible[i], {id: group + ":" + visible[i].id,
                sourceId: visible[i].id, provider: group, query: query,
                group: group, groupTitle: i === 0 ? labels[group] : ""}));
        }
    });
    ["files", "web"].forEach((kind, index) => results.push({id: "extension:" + kind, provider: "extension",
        sourceId: kind, query: query, title: labels[kind], subtitle: "", iconKind: "symbol",
        symbol: kind === "files" ? "draft" : "travel_explore", groupTitle: "", separator: index === 0}));
    return results;
}

// Pack selectable identities into visual rows; activation still uses flat IDs.
function visualRows(results, capacities) {
    const rows = [];
    results.forEach((result, index) => {
        const group = result.group || result.provider;
        const horizontal = horizontalGroup(group);
        const previous = rows[rows.length - 1];
        const cell = {result: result, index: index};
        if (horizontal && previous && previous.kind === group
                && previous.cells.length < groupCapacity(group, capacities)) {
            previous.cells.push(cell);
        } else {
            rows.push({kind: horizontal ? group : result.provider, groupTitle: result.groupTitle || "",
                separator: !!result.separator, cells: [cell]});
        }
    });
    return rows;
}

function visualRowIndex(rows, selectedIndex) {
    return rows.findIndex(row => row.cells.some(cell => cell.index === selectedIndex));
}

function navigationIndex(rows, selectedIndex, direction) {
    if (!rows.length) return -1;
    const rowIndex = visualRowIndex(rows, selectedIndex);
    if (rowIndex < 0) return rows[0].cells[0].index;
    const row = rows[rowIndex];
    const column = row.cells.findIndex(cell => cell.index === selectedIndex);
    if (direction === "left" || direction === "right") {
        const next = Math.max(0, Math.min(row.cells.length - 1, column + (direction === "left" ? -1 : 1)));
        return row.cells[next].index;
    }
    const nextRow = rows[Math.max(0, Math.min(rows.length - 1, rowIndex + (direction === "up" ? -1 : 1)))];
    return nextRow.cells[Math.min(column, nextRow.cells.length - 1)].index;
}

// A stale row or a forged ID cannot dispatch a previous query's result.
function activation(results, id, query) {
    const row = results.find(entry => entry.id === id);
    return row && row.query === query ? {provider: row.provider, sourceId: row.sourceId, query: row.query} : null;
}
