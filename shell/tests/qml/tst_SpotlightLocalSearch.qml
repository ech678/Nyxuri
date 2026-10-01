import QtQuick
import QtTest
import "../../Common/functions/SpotlightLocalSearch.js" as Search

TestCase {
    name: "SpotlightLocalSearch"
    function labels() {
        return {
            apps: "Apps",
            settings: "Settings",
            actions: "Actions",
            wallpapers: "Wallpapers",
            files: "Files",
            web: "Web"
        };
    }
    function test_empty_and_extensions_preserve_literal_query() {
        compare(Search.groupedResults({}, " \t", labels()), []);
        const query = "  A/B 中文 & ?\"  ";
        const results = Search.groupedResults({}, query, labels());
        compare(results.length, 2);
        compare(Search.activation(results, "extension:files", query), {
                    provider: "extension",
                    sourceId: "files",
                    query: query
                });
        compare(Search.activation(results, "extension:web", query).query, query);
        compare(Search.activation(results, "extension:web", "different"), null);
        compare(Search.activation(results, "eval:query", query), null);
    }
    function test_group_order_budgets_and_namespaced_identity() {
        const apps = [];
        for (let i = 0; i < 8; ++i)
            apps.push({
                          id: "app" + i,
                          title: "App " + i
                      });
        const matches = {
            apps: apps,
            settings: [
                {
                    id: "app0",
                    title: "Setting"
                }
            ],
            actions: [
                {
                    id: "open",
                    title: "Open"
                }
            ]
        };
        let rows = Search.groupedResults(matches, "a", labels());
        compare(rows[0].id, "apps:app0");
        compare(rows[5].id, "apps:app5");
        compare(rows[6].id, "settings:app0");
        compare(rows[7].id, "actions:open");
        compare(rows.filter(row => row.groupTitle).length, 3);
        compare(matches.apps.length, 8);
    }
    function test_catalog_localized_english_alias_and_deterministic_order() {
        const entries = [
                  {
                      id: "b",
                      title: "界面语言",
                      sourceTitle: "Interface language",
                      aliases: ["locale"]
                  },
                  {
                      id: "a",
                      title: "语言",
                      sourceTitle: "Language",
                      aliases: []
                  },
                  {
                      id: "c",
                      title: "外观",
                      sourceTitle: "Appearance",
                      aliases: []
                  }
              ];
        compare(Search.matchCatalog(entries, "语").map(e => e.id), ["a", "b"]);
        compare(Search.matchCatalog(entries, "Interface").map(e => e.id), ["b"]);
        compare(Search.matchCatalog(entries, "locale").map(e => e.id), ["b"]);
        compare(Search.matchCatalog(entries, "").length, 0);
        compare(Search.matchCatalog(entries, "$(shutdown)").length, 0);
    }
    function test_compact_budgets_and_retained_selection() {
        const entries = Array.from({
                                       length: 9
                                   }, (_, i) => ({
                                       id: "item" + i,
                                       title: "Item " + i
                                   }));
        const matches = {
            apps: entries,
            settings: entries,
            actions: entries,
            wallpapers: entries
        };
        const capacities = {
            apps: 4,
            wallpapers: 3
        };
        let results = Search.groupedResults(matches, "item", labels(), capacities);
        compare(results.filter(r => r.provider === "apps").length, 4);
        compare(results.filter(r => r.provider === "wallpapers").length, 3);
        compare(results.filter(r => r.provider === "settings").length, 2);
        compare(results.filter(r => r.provider === "actions").length, 2);
        compare(results.length, 13);
        compare(Search.visualRows(results, capacities).filter(r => r.kind === "apps").length, 1);
        compare(Search.visualRows(results, capacities).filter(r => r.kind === "wallpapers").length, 1);
        for (const group of ["apps", "settings", "actions", "wallpapers"])
            compare(Search.activation(results, "more:" + group, "item"), null);

        // A resize keeps the selected identity without adding rows or hiding the top match.
        results = Search.groupedResults(matches, "item", labels(), {
                                            apps: 2,
                                            wallpapers: 2
                                        }, "apps:item6");
        compare(results.filter(r => r.provider === "apps").map(r => r.id), ["apps:item0", "apps:item6"]);
        compare(results.filter(r => r.provider === "wallpapers").length, 2);
        compare(Search.activation(results, "apps:item6", "item").sourceId, "item6");
        results = Search.groupedResults(matches, "item", labels(), capacities, "settings:item6");
        compare(results.filter(r => r.provider === "settings").map(r => r.id), ["settings:item0",
                                                                                "settings:item6"]);
        // Without a retained selection, only the leading matches are exposed.
        results = Search.groupedResults(matches, "item", labels(), capacities);
        compare(Search.activation(results, "apps:item6", "item"), null);
        compare(entries.length, 9);
    }
    function test_mixed_navigation_keeps_all_actions_reachable() {
        const entries = Array.from({
                                       length: 7
                                   }, (_, i) => ({
                                       id: "item" + i,
                                       title: "Item " + i
                                   }));
        const capacities = {
            apps: 4,
            wallpapers: 3
        };
        const results = Search.groupedResults({
                                                  apps: entries,
                                                  settings: entries,
                                                  wallpapers: entries
                                              }, "item", labels(), capacities);
        const rows = Search.visualRows(results, capacities);
        const index = id => results.findIndex(r => r.id === id);
        compare(Search.navigationIndex(rows, index("apps:item0"), "left"), index("apps:item0"));
        compare(Search.navigationIndex(rows, index("apps:item2"), "right"), index("apps:item3"));
        compare(Search.navigationIndex(rows, index("apps:item3"), "right"), index("apps:item3"));
        compare(Search.navigationIndex(rows, index("apps:item2"), "down"), index("settings:item0"));
        compare(Search.navigationIndex(rows, index("settings:item0"), "up"), index("apps:item0"));
        compare(Search.navigationIndex(rows, index("settings:item1"), "down"), index("wallpapers:item0"));
        compare(Search.navigationIndex(rows, index("wallpapers:item1"), "right"), index("wallpapers:item2"));
        compare(Search.navigationIndex(rows, index("wallpapers:item2"), "down"), index("extension:files"));
        compare(Search.navigationIndex(rows, index("extension:files"), "down"), index("extension:web"));
        compare(Search.navigationIndex(rows, index("extension:web"), "down"), index("extension:web"));
        compare(Search.navigationIndex([], -1, "down"), -1);
        // Every selectable result occurs exactly once in the packed rows.
        compare(rows.reduce((ids, row) => ids.concat(row.cells.map(c => c.result.id)), []), results.map(r
                                                                                                        => r.id));
    }
    function test_apps_keep_relevance_usage_and_stable_id() {
        const apps = [
                  {
                      id: "x",
                      name: "Browser",
                      icon: "x"
                  },
                  {
                      id: "y",
                      name: "Browser tools",
                      icon: "y"
                  }
              ];
        const history = {
            y: {
                launchCount: 1000,
                lastLaunchedAt: 1000
            }
        };
        compare(Search.appResults(apps, "browser", "most-used", history, 2000).map(e => e.id), ["x", "y"]);
        compare(Search.appResults(apps, "", "most-used", history, 2000).map(e => e.id), ["y", "x"]);
        compare(Search.appResults(apps, "", "name", history, 2000).map(e => e.id), ["x", "y"]);
        compare(apps[0].id, "x");
    }
    function test_wallpaper_existing_name_rules() {
        const basename = path => path.slice(path.lastIndexOf("/") + 1);
        const paths = ["/a/z-moon.png", "/b/moon.png", "/c/sun.png"];
        compare(Search.wallpaperPaths(paths, "MOON", basename), ["/b/moon.png", "/a/z-moon.png"]);
        compare(paths.length, 3);
    }
}
