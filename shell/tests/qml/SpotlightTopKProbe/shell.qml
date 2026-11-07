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

    function compareBounded(query, order, capacity, retainedId) {
        const source = applications();
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
        const queries = ["alpha", "", "write", "missing"];
        const orders = ["name", "smart", "most-used", "recently-used"];
        const capacities = [1, 2, 4, 8, 20];
        const retainedIds = ["", "gamma.desktop", "kappa.desktop", "alpha.desktop"];
        for (const query of queries) {
            for (const order of orders) {
                for (const capacity of capacities) {
                    for (const retainedId of retainedIds) {
                        if (!compareBounded(query, order, capacity, retainedId))
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
        const baseline = {};
        const bounded = {};
        const complete = LocalSearch.appResults(source, "synthetic", {
            order: "smart", history: history, now: 120000, stats: baseline
        });
        const limited = LocalSearch.appResults(source, "synthetic", {
            order: "smart", history: history, now: 120000, limit: 6,
            retainedId: "synthetic-11999.desktop", stats: bounded
        });
        if (!compareIds(limited.slice(0, 5).map(entry => entry.id), complete.slice(0, 5).map(entry => entry.id),
                        "large top K")
                || !assertEqual(limited[6].id, "synthetic-11999.desktop", "large retained id")
                || !assertEqual(baseline.appScoreCalls, 12000, "full score calls")
                || !assertEqual(bounded.appScoreCalls, 12000, "bounded score calls")
                || !assertEqual(baseline.uiResultRecordsBuilt, 12000, "full UI records")
                || !assertEqual(bounded.uiResultRecordsBuilt, 7, "bounded UI records")
                || !assertEqual(baseline.rankingRecordsBuilt, 0, "full ranking records")
                || !assertEqual(bounded.rankingRecordsBuilt, 7, "bounded ranking records"))
            return false;
        if (bounded.orderComparisons >= baseline.orderComparisons)
            return fail("bounded comparison count did not beat full sort");
        return {
            appScoreCalls: bounded.appScoreCalls,
            baselineUiResultRecords: baseline.uiResultRecordsBuilt,
            boundedUiResultRecords: bounded.uiResultRecordsBuilt,
            boundedRankingRecords: bounded.rankingRecordsBuilt,
            boundedOrderComparisons: bounded.orderComparisons,
            fullSortOrderComparisons: baseline.orderComparisons,
            retainedOutsideTopK: limited[6].id
        };
    }

    Component.onCompleted: Qt.callLater(() => {
        if (!root.runMatrix())
            return;
        const metrics = root.runLargeProbe();
        if (!metrics)
            return;
        console.log("SPOTLIGHT_TOPK_PROBE_PASS " + JSON.stringify(metrics));
        Qt.quit();
    })
}
