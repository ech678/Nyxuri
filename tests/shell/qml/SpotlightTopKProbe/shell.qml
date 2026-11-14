import QtQuick
import Quickshell
import "./plugins/launcher/SpotlightLocalSearch.js" as LocalSearch

ShellRoot {
    id: root

    function fail(reason) {
        console.error("SPOTLIGHT_TOPK_PROBE_FAIL", reason);
        Qt.exit(1);
        return false;
    }

    function assertEqual(actual, expected, label) {
        if (actual !== expected)
            return fail(label + ": expected " + expected + ", got " + actual);
        return true;
    }

    function compareIds(actual, expected, label) {
        if (!assertEqual(actual.length, expected.length, label + " length"))
            return false;
        for (let index = 0; index < expected.length; ++index) {
            if (!assertEqual(actual[index], expected[index], label + "[" + index + "]"))
                return false;
        }
        return true;
    }

    function compareRecords(actual, expected, label) {
        if (!compareIds(actual.map(entry => entry.id), expected.map(entry => entry.id), label + " IDs"))
            return false;
        for (let index = 0; index < expected.length; ++index) {
            const left = actual[index];
            const right = expected[index];
            if (!assertEqual(left.title, right.title, label + " title[" + index + "]")
                    || !assertEqual(left.subtitle, right.subtitle, label + " subtitle[" + index + "]")
                    || !assertEqual(left.score, right.score, label + " score[" + index + "]")
                    || !assertEqual(left.appObject, right.appObject, label + " app[" + index + "]"))
                return false;
        }
        return true;
    }

    function applications() {
        return [
            {id: "alpha.desktop", name: "Alpha", genericName: "Editor", keywords: ["write"]},
            {id: "alpha.desktop", name: "Alpha", genericName: "Editor duplicate", keywords: ["write"]},
            {id: "beta.desktop", name: "Beta Alpha", genericName: "Editor", keywords: ["write"]},
            {id: "gamma.desktop", name: "Alpha", genericName: "Viewer", keywords: ["read"]},
            {id: "delta.desktop", name: "Delta", genericName: "Alpha Tools", keywords: ["write"]},
            {id: "epsilon.desktop", name: "Epsilon", genericName: "Writer", keywords: ["alpha"]},
            {id: "zeta.desktop", name: "Zeta", genericName: "Writer", keywords: ["write"]},
            {id: "eta.desktop", name: "Eta", genericName: "Writer", keywords: ["alpha"]},
            {id: "theta.desktop", name: "Theta", genericName: "Writer", keywords: ["write"]},
            {id: "iota.desktop", name: "Iota", genericName: "Writer", keywords: ["alpha"]},
            {id: "kappa.desktop", name: "Kappa", genericName: "Writer", keywords: ["write"]},
            null
        ];
    }

    function history() {
        return {
            "alpha.desktop": {launchCount: 2, lastLaunchedAt: 100},
            "gamma.desktop": {launchCount: 8, lastLaunchedAt: 900},
            "delta.desktop": {launchCount: 8, lastLaunchedAt: 900},
            "theta.desktop": {launchCount: 5, lastLaunchedAt: 500}
        };
    }

    function expectedVisible(full, capacity, retainedId) {
        const visible = full.slice(0, capacity);
        const retained = full.findIndex(entry => entry.id === retainedId);
        if (retained >= capacity && visible.length > 0)
            visible[capacity - 1] = full[retained];
        return visible;
    }

    function compareBounded(source, query, order, capacity, retainedId) {
        const full = LocalSearch.appResults(source, query, {
            order: order, history: history(), now: 1000
        });
        const bounded = LocalSearch.appResults(source, query, {
            order: order, history: history(), now: 1000, limit: capacity, retainedId: retainedId
        });
        if (!compareIds(bounded.slice(0, Math.min(capacity, full.length)).map(entry => entry.id),
                        full.slice(0, capacity).map(entry => entry.id), "top K"))
            return false;
        const expectedLength = Math.min(capacity, full.length)
                    + (retainedId && full.findIndex(entry => entry.id === retainedId) >= capacity ? 1 : 0);
        if (!assertEqual(bounded.length, expectedLength, "bounded result length"))
            return false;
        if (capacity >= 2 && query.trim()) {
            const grouped = LocalSearch.groupedResults({apps: bounded}, query, {apps: "Apps"},
                                                       {apps: capacity}, retainedId ? "apps:" + retainedId : "");
            const actualVisible = grouped.filter(entry => entry.provider === "apps");
            const expected = expectedVisible(full, capacity, retainedId);
            if (!compareIds(actualVisible.map(entry => entry.sourceId), expected.map(entry => entry.id),
                            "grouped retained results"))
                return false;
            for (let index = 0; index < expected.length; ++index) {
                if (!assertEqual(actualVisible[index].title, expected[index].title, "retained title")
                        || !assertEqual(actualVisible[index].subtitle, expected[index].subtitle,
                                        "retained subtitle query=" + query + " order=" + order
                                        + " capacity=" + capacity + " retained=" + retainedId
                                        + " index=" + index))
                    return false;
            }
        }
        return true;
    }

    function runMatrix() {
        const source = applications();
        const queries = ["alpha", "", "write", "missing"];
        const orders = ["name", "smart", "most-used", "recently-used"];
        const capacities = [1, 2, 4, 8, 20];
        const retainedIds = ["", "gamma.desktop", "kappa.desktop", "alpha.desktop"];
        for (const query of queries) {
            for (const order of orders) {
                for (const capacity of capacities) {
                    for (const retainedId of retainedIds) {
                        if (!compareBounded(source, query, order, capacity, retainedId))
                            return false;
                    }
                }
            }
        }
        const full = LocalSearch.appResults(applications(), "", {order: "name", history: {}, now: 0});
        for (const limit of [0, -1]) {
            const all = LocalSearch.appResults(applications(), "", {order: "name", history: {}, now: 0,
                                                                         limit: limit});
            if (!compareIds(all.map(entry => entry.id), full.map(entry => entry.id), "nonpositive limit"))
                return false;
        }
        return true;
    }

    function runLargeProbe() {
        const source = [];
        const history = {};
        for (let index = 0; index < 12000; ++index) {
            const id = "synthetic-" + String(index).padStart(5, "0") + ".desktop";
            source.push({id: id, name: "Synthetic App " + index, genericName: "Utility", keywords: ["synthetic"]});
            if (index % 3 === 0)
                history[id] = {launchCount: index % 17 + 1, lastLaunchedAt: index * 10};
        }
        const queries = ["synthetic", "utility", "synthetic app", "synthetic-11999"];
        const retainedId = "synthetic-11999.desktop";
        const resultOrders = [];
        let firstQuery = null;
        let warmFieldNormalizations = 0;
        let warmKeywordJoins = 0;
        let coldFieldNormalizations = 0;
        let coldKeywordJoins = 0;
        let warmHits = 0;
        LocalSearch.clearAppSearchCache();
        for (let queryIndex = 0; queryIndex < queries.length; ++queryIndex) {
            const query = queries[queryIndex];
            const fullStats = {};
            const full = LocalSearch.appResults(source, query, {
                order: "smart", history: history, now: 120000, stats: fullStats
            });
            if (queryIndex === 0) {
                firstQuery = fullStats;
                coldFieldNormalizations += fullStats.fieldNormalizations;
                coldKeywordJoins += fullStats.keywordListsJoined;
            } else {
                warmFieldNormalizations += fullStats.fieldNormalizations;
                warmKeywordJoins += fullStats.keywordListsJoined;
            }
            warmHits += fullStats.fieldCacheHits;
            const boundedStats = {};
            const limited = LocalSearch.appResults(source, query, {
                order: "smart", history: history, now: 120000, limit: 6,
                retainedId: retainedId, stats: boundedStats
            });
            const repeatedStats = {};
            const repeated = LocalSearch.appResults(source, query, {
                order: "smart", history: history, now: 120000, limit: 6,
                retainedId: retainedId, stats: repeatedStats
            });
            warmFieldNormalizations += boundedStats.fieldNormalizations + repeatedStats.fieldNormalizations;
            warmKeywordJoins += boundedStats.keywordListsJoined + repeatedStats.keywordListsJoined;
            warmHits += boundedStats.fieldCacheHits + repeatedStats.fieldCacheHits;
            const retainedRank = full.findIndex(entry => entry.id === retainedId);
            const expectedLength = Math.min(6, full.length) + (retainedRank >= 6 ? 1 : 0);
            if (!compareRecords(limited.slice(0, Math.min(6, full.length)), full.slice(0, 6),
                                "large top K " + query)
                    || !assertEqual(limited.length, expectedLength, "large result limit " + query)
                    || !assertEqual(limited.find(entry => entry.id === retainedId)?.id, retainedId,
                                    "large retained selection " + query)
                    || !compareRecords(repeated, limited, "warm repeated search " + query)
                    || !assertEqual(fullStats.appScoreCalls, 12000, "full score calls " + query)
                    || !assertEqual(boundedStats.appScoreCalls, 12000, "bounded score calls " + query)
                    || !assertEqual(fullStats.uiResultRecordsBuilt, full.length, "full UI records " + query)
                    || !assertEqual(boundedStats.uiResultRecordsBuilt, limited.length, "bounded UI records " + query)
                    || !assertEqual(fullStats.fieldNormalizations, queryIndex === 0 ? 48000 : 0,
                                    "query field normalizations " + query)
                    || !assertEqual(fullStats.keywordListsJoined, queryIndex === 0 ? 12000 : 0,
                                    "query keyword joins " + query)
                    || !assertEqual(boundedStats.fieldNormalizations, 0, "bounded warm field normalizations " + query)
                    || !assertEqual(boundedStats.keywordListsJoined, 0, "bounded warm keyword joins " + query)
                    || !assertEqual(repeatedStats.fieldNormalizations, 0, "repeat field normalizations " + query)
                    || !assertEqual(repeatedStats.keywordListsJoined, 0, "repeat keyword joins " + query))
                return false;
            if (queryIndex === 0) {
                if (!assertEqual(firstQuery.fieldNormalizations, 48000, "cold field normalizations")
                        || !assertEqual(firstQuery.keywordListsJoined, 12000, "cold keyword joins")
                        || !assertEqual(firstQuery.fieldCacheMisses, 12000, "cold cache misses")
                        || !assertEqual(firstQuery.appScoreCalls, 12000, "full score calls")
                        || !assertEqual(firstQuery.uiResultRecordsBuilt, 12000, "full UI records")
                        || !assertEqual(firstQuery.rankingRecordsBuilt, 0, "full ranking records")
                        || !assertEqual(boundedStats.rankingRecordsBuilt, 7, "bounded ranking records")
                        || boundedStats.orderComparisons >= firstQuery.orderComparisons)
                    return false;
            }
            resultOrders.push({query: query, fullTopIds: full.slice(0, 6).map(entry => entry.id),
                               boundedIds: limited.map(entry => entry.id), retained: retainedId});
        }
        if (!firstQuery || firstQuery.appScoreCalls !== 12000)
            return fail("cold full search did not score the catalog");
        return {
            catalogSize: source.length,
            queries: queries,
            legacyFieldNormalizationsAcrossQueries: 4 * source.length * queries.length * 3,
            measuredFieldNormalizationsAcrossQueries: coldFieldNormalizations + warmFieldNormalizations,
            legacyWarmFieldNormalizations: 4 * source.length * (queries.length * 3 - 1),
            actualWarmFieldNormalizations: warmFieldNormalizations,
            legacyKeywordJoinsAcrossQueries: source.length * queries.length * 3,
            measuredKeywordJoinsAcrossQueries: coldKeywordJoins + warmKeywordJoins,
            legacyWarmKeywordJoins: source.length * (queries.length * 3 - 1),
            actualWarmKeywordJoins: warmKeywordJoins,
            coldFieldNormalizations: coldFieldNormalizations,
            coldKeywordJoins: coldKeywordJoins,
            cachedApplicationHits: warmHits,
            resultOrders: resultOrders
        };
    }

    function runCacheSemanticsProbe() {
        const source = [
            {id: "duplicate.desktop", name: "Cafe Writer", genericName: "Editor", keywords: ["utility"]},
            {id: "duplicate.desktop", name: "Café Reader", genericName: "Viewer", keywords: ["notes"]},
            {id: "snow.desktop", name: "Snow 雪 Viewer", genericName: "Reader", keywords: ["weather"]}
        ];
        const queries = ["caf", "café", "雪", "", "missing"];
        LocalSearch.clearAppSearchCache();
        const results = [];
        for (const query of queries) {
            const stats = {};
            const full = LocalSearch.appResults(source, query, {order: "name", history: {}, now: 0,
                                                                   stats: stats});
            const warmStats = {};
            const warm = LocalSearch.appResults(source, query, {order: "name", history: {}, now: 0,
                                                                  stats: warmStats});
            if (!compareRecords(warm, full, "cache semantics " + query))
                return false;
            if (query === "" && (stats.fieldCacheMisses !== 0 || stats.fieldNormalizations !== 0
                                  || stats.keywordListsJoined !== 0))
                return fail("empty query unexpectedly normalized app fields");
            if (!assertEqual(warmStats.fieldNormalizations, 0, "semantic warm normalizations " + query)
                    || !assertEqual(warmStats.keywordListsJoined, 0, "semantic warm keyword joins " + query))
                return false;
            results.push({query: query, ids: full.map(entry => entry.id), titles: full.map(entry => entry.title)});
        }
        if (!assertEqual(results[0].ids.length, 2, "duplicate IDs remain distinct")
                || !assertEqual(results[2].ids[0], "snow.desktop", "unicode query")
                || !assertEqual(results[3].ids.length, source.length, "empty query result count"))
            return false;

        const mutable = {id: "mutable.desktop", name: "Before", genericName: "", keywords: ["legacy"]};
        LocalSearch.clearAppSearchCache();
        const before = LocalSearch.appResults([mutable], "legacy", {order: "name", history: {}, now: 0});
        mutable.name = "After";
        mutable.keywords = ["modern"];
        LocalSearch.clearAppSearchCache();
        const stale = LocalSearch.appResults([mutable], "legacy", {order: "name", history: {}, now: 0});
        const refreshed = LocalSearch.appResults([mutable], "modern", {order: "name", history: {}, now: 0});
        if (!assertEqual(before.length, 1, "catalog mutation baseline")
                || !assertEqual(stale.length, 0, "catalog mutation clears stale fields")
                || !assertEqual(refreshed[0].id, "mutable.desktop", "catalog mutation refreshed fields"))
            return false;

        const oldCatalog = [{id: "replace.desktop", name: "Old Catalog", genericName: "", keywords: []}];
        LocalSearch.appResults(oldCatalog, "old", {order: "name", history: {}, now: 0});
        const newCatalog = [{id: "replace.desktop", name: "New Catalog", genericName: "", keywords: []}];
        const replacementStats = {};
        const replacement = LocalSearch.appResults(newCatalog, "new", {order: "name", history: {}, now: 0,
                                                                         stats: replacementStats});
        if (!assertEqual(replacement[0].id, "replace.desktop", "replacement catalog result")
                || !assertEqual(replacementStats.fieldCacheMisses, 1, "replacement catalog cache miss"))
            return false;
        return {queries: results, replacementCatalogMisses: replacementStats.fieldCacheMisses};
    }

    function runWeakCacheProbe() {
        const app = {id: "weak.desktop", name: "Weak Cache", genericName: "", keywords: []};
        LocalSearch.clearAppSearchCache();
        LocalSearch.appResults([app], "weak", {order: "name", history: {}, now: 0});
        if (typeof WeakMap !== "function")
            return fail("runtime does not provide WeakMap");
        return {weakMapAvailable: true, weakRefAvailable: typeof WeakRef === "function",
                finalizationRegistryAvailable: typeof FinalizationRegistry === "function",
                cacheKeyKind: "WeakMap object key"};
    }

    Component.onCompleted: Qt.callLater(() => {
        if (!root.runMatrix())
            return;
        const semantics = root.runCacheSemanticsProbe();
        if (!semantics)
            return;
        const metrics = root.runLargeProbe();
        if (!metrics)
            return;
        const weakCache = root.runWeakCacheProbe();
        if (!weakCache)
            return;
        console.log("SPOTLIGHT_TOPK_PROBE_PASS " + JSON.stringify({
            cacheSemantics: semantics,
            fieldCache: metrics,
            weakCache: weakCache
        }));
        Qt.quit();
    })
}
