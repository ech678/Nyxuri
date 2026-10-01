import QtQuick
import QtTest
import "../../Common/functions/SpotlightAppOrder.js" as AppOrder

TestCase {
    name: "SpotlightAppOrder"
    readonly property real now: 1800000000000
    readonly property real hour: 3600000

    function results() {
        return [
                    {
                        id: "old",
                        title: "Alpha",
                        score: 0
                    },
                    {
                        id: "daily",
                        title: "Beta",
                        score: 0
                    },
                    {
                        id: "new",
                        title: "Gamma",
                        score: 0
                    },
                    {
                        id: "unused",
                        title: "Delta",
                        score: 0
                    }
                ];
    }
    function history() {
        return {
            old: {
                launchCount: 100,
                lastLaunchedAt: now - 1000 * hour
            },
            daily: {
                launchCount: 20,
                lastLaunchedAt: now - 2 * hour
            },
            new: {
                launchCount: 1,
                lastLaunchedAt: now - hour / 2
            }
        };
    }
    function ids(rows) {
        return rows.map(row => row.id).join(",");
    }

    function test_orderModes() {
        compare(ids(AppOrder.sortedResults(results(), "name", history(), now)), "old,daily,unused,new");
        compare(ids(AppOrder.sortedResults(results(), "most-used", history(), now)), "old,daily,new,unused");
        compare(ids(AppOrder.sortedResults(results(), "recently-used", history(), now)),
                "new,daily,old,unused");
        compare(ids(AppOrder.sortedResults(results(), "smart", history(), now)), "daily,new,old,unused");
    }
    function test_noHistoryAndInvalidPreference() {
        ["smart", "most-used", "recently-used", "name", "unknown", undefined].forEach(order => {
            compare(ids(AppOrder.sortedResults(results(), order, {}, now)), "old,daily,unused,new");
        });
        compare(AppOrder.normalizedOrder("unknown"), "name");
        compare(AppOrder.normalizedOrder("smart"), "smart");
    }
    function test_searchRelevanceAlwaysFirst() {
        const rows = results();
        rows[3].score = 4001;
        rows[0].score = 4000;
        ["smart", "most-used", "recently-used", "name"].forEach(order => {
            const ordered = AppOrder.sortedResults(rows, order, history(), now);
            compare(ordered[0].id, "unused");
            compare(ordered[1].id, "old");
        });
        compare(rows[0].id, "old"); // Sorting never mutates provider input.
    }
    function test_stableTieById() {
        const rows = [
                  {
                      id: "b",
                      title: "Same",
                      score: 0
                  },
                  {
                      id: "a",
                      title: "Same",
                      score: 0
                  }
              ];
        compare(ids(AppOrder.sortedResults(rows, "smart", {}, now)), "a,b");
    }
    function test_recencyBoundariesAndClockRollback() {
        const ages = [0, 1, 24, 168, 720];
        const bonuses = [8, 6, 4, 2, 0];
        for (let index = 0; index < ages.length; index++) {
            compare(AppOrder.usageScore("smart", {
                                            launchCount: 1,
                                            lastLaunchedAt: now - ages[index] * hour
                                        }, now), 1 + bonuses[index]);
        }
        compare(AppOrder.usageScore("smart", {
                                        launchCount: 1,
                                        lastLaunchedAt: now + hour
                                    }, now), 9);
        compare(AppOrder.usageScore("smart", {
                                        launchCount: 1,
                                        lastLaunchedAt: 0
                                    }, now), 1);
    }
    function test_launchHistoryRoundTripAndPendingMerge() {
        const saved = AppOrder.addLaunch({}, "desktop.id", now - hour);
        const pending = AppOrder.addLaunch(AppOrder.addLaunch({}, "desktop.id", now), "second", now);
        const merged = AppOrder.mergePending(saved, pending);
        compare(merged["desktop.id"].launchCount, 2);
        compare(merged["desktop.id"].lastLaunchedAt, now);
        compare(saved["desktop.id"].launchCount, 1);
        const decoded = AppOrder.decodeHistory(JSON.stringify({
                                                                  schemaVersion: 1,
                                                                  applications: merged
                                                              }));
        compare(decoded["desktop.id"].launchCount, 2);
        compare(decoded.second.lastLaunchedAt, now);
        compare(AppOrder.addLaunch(decoded, "desktop.id", now - hour)["desktop.id"].lastLaunchedAt, now);
        compare(Object.keys(AppOrder.addLaunch({}, "", now)).length, 0);
    }
    function test_malformedHistoryPreservedAsInvalid() {
        ["", "invalid", "null", "[]", '{"schemaVersion":2,"applications":{}}',
        '{"schemaVersion":1,"applications":[]}'].forEach(text => compare(AppOrder.decodeHistory(text), null));
        const value = AppOrder.decodeHistory(JSON.stringify({
                                                                schemaVersion: 1,
                                                                applications: {
                                                                    good: {
                                                                        launchCount: 4,
                                                                        lastLaunchedAt: now
                                                                    },
                                                                    negative: {
                                                                        launchCount: -2
                                                                    },
                                                                    bad: {
                                                                        launchCount: "many"
                                                                    },
                                                                    nullEntry: null,
                                                                    overflow: {
                                                                        launchCount: 1e100,
                                                                        lastLaunchedAt: "bad"
                                                                    }
                                                                }
                                                            }));
        compare(Object.keys(value).sort().join(","), "good,overflow");
        compare(value.overflow.launchCount, Number.MAX_SAFE_INTEGER);
        compare(value.overflow.lastLaunchedAt, 0);
        const unusual = AppOrder.addLaunch({}, "__proto__", now);
        compare(unusual["__proto__"].launchCount, 1);
    }
}
