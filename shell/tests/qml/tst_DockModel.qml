import QtQuick
import QtTest
import "../../Common/functions/DockModel.js" as DockModel

TestCase {
    name: "DockModel"

    readonly property var applications: [
        {
            id: "org.example.Editor",
            name: "Editor",
            startupClass: "EditorWindow"
        },
        {
            id: "org.example.Browser.desktop",
            name: "Browser",
            startupClass: "Browser"
        },
        {
            id: "org.clavis.Settings",
            name: "Settings"
        }
    ]

    ListModel {
        id: rows
    }

    function init() {
        rows.clear();
    }

    function test_minimizedWindowsStayRunningAndActivateIndividually() {
        const hidden = {
            id: 42,
            appId: "EditorWindow",
            title: "Same title",
            isMinimized: true
        };
        const other = {
            id: 43,
            appId: "EditorWindow",
            title: "Same title",
            isMinimized: true
        };
        const groups = DockModel.groupWindows([hidden, other], applications, ({}));
        const group = groups[Object.keys(groups)[0]];
        compare(group.windows.length, 2);
        const choice = DockModel.activation(group.windows, true);
        compare(choice.action, "restore");
        verify(choice.id === 42 || choice.id === 43);
        compare(DockModel.activation([], true).action, "launch");
        compare(DockModel.activation([
                                         {
                                             id: 42,
                                             isFocused: true
                                         }
                                     ], true).action, "minimize");
        compare(DockModel.activation([
                                         {
                                             id: 42,
                                             isFocused: true
                                         }
                                     ], false).action, "focus");
        compare(DockModel.activation([
                                         {
                                             id: 42,
                                             isFocused: true
                                         },
                                         other], true).action, "focus");
    }

    function encodedConfig(pinned, options) {
        return JSON.stringify({
                                  schemaVersion: 1,
                                  pinned: pinned,
                                  options: options || {}
                              });
    }

    function test_fileReferencesSurviveConfigRoundTrip() {
        const pins = [
                  {
                      kind: "folder",
                      url: "file:///tmp/Folder%20%23%25",
                      view: "list",
                      sort: "created",
                      display: "stack"
                  },
                  {
                      kind: "app",
                      desktopId: "org.example.App"
                  },
                  {
                      kind: "file",
                      url: "file:///tmp/%E4%B8%AD%E6%96%87.txt"
                  }
              ];
        const config = DockModel.decodeConfig(JSON.stringify({
                                                                 schemaVersion: 1,
                                                                 options: {},
                                                                 pinned: pins
                                                             }));
        verify(config !== null);
        compare(config.pinned[0].kind, "app");
        compare(config.pinned[1].view, "list");
        compare(config.pinned[1].sort, "created");
        compare(config.pinned[1].display, "stack");
        compare(config.pinned[2].url, pins[2].url);
        compare(DockModel.pinnedKey(config.pinned[1]), "file:" + pins[0].url);
        verify(!DockModel.validFileUrl("file:///tmp/%00"));
        verify(!DockModel.validFileUrl("file://host/path"));
        verify(!DockModel.validFileUrl("file:///tmp/%ZZ"));
    }

    function test_configRoundTripAndBounds() {
        const decoded = DockModel.decodeConfig(encodedConfig([
                                                                 {
                                                                     kind: "app",
                                                                     desktopId: "org.example.Editor.desktop"
                                                                 },
                                                                 {
                                                                     kind: "spacer",
                                                                     id: "first"
                                                                 }
                                                             ], {
                                                                 iconSize: 500,
                                                                 magnificationScale: 0,
                                                                 separatorSize: 1,
                                                                 position: "right"
                                                             }));
        verify(decoded !== null);
        compare(decoded.pinned[0].desktopId, "org.example.Editor");
        compare(decoded.pinned[1].id, "first");
        compare(decoded.options.iconSize, 80);
        compare(decoded.options.magnificationScale, 1);
        compare(decoded.options.separatorSize, undefined);
        compare(decoded.pinned[1].kind, "spacer");
        compare(decoded.options.position, "right");
        compare(decoded.options.showRecent, true);
        compare(decoded.options.showThumbnails, true);
        compare(decoded.options.previewSize, 160);
        compare(DockModel.decodeConfig(JSON.stringify(decoded)), decoded);
        compare(DockModel.option("enabled", "false"), undefined);
        compare(DockModel.option("position", "top"), undefined);
        compare(DockModel.option("iconSize", NaN), undefined);
        compare(DockModel.option("showThumbnails", "true"), undefined);
        compare(DockModel.option("previewSize", NaN), undefined);
        const previews = DockModel.decodeConfig(encodedConfig([], {
                                                                  showThumbnails: false,
                                                                  previewSize: 1000
                                                              }));
        compare(previews.options.showThumbnails, false);
        compare(previews.options.previewSize, 240);
        compare(DockModel.decodeConfig(JSON.stringify(previews)), previews);
        compare(DockModel.option("previewSize", 0), 96);
    }

    function test_legacySeparatorsKeepTheirPositionAndIdentity() {
        const config = DockModel.decodeConfig(encodedConfig([
                                                                {
                                                                    kind: "app",
                                                                    desktopId: "a"
                                                                },
                                                                {
                                                                    kind: "separator",
                                                                    id: "old_gap"
                                                                },
                                                                {
                                                                    kind: "spacer",
                                                                    id: "new_gap"
                                                                },
                                                                {
                                                                    kind: "app",
                                                                    desktopId: "b"
                                                                }
                                                            ], {
                                                                separatorSize: 24
                                                            }));
        compare(config.pinned.map(DockModel.pinnedKey).join(","),
                "app:a,spacer:old_gap,spacer:new_gap,app:b");
        compare(DockModel.decodeConfig(JSON.stringify(config)), config);
        compare(DockModel.decodeConfig(encodedConfig([
                                                         {
                                                             kind: "separator",
                                                             id: "duplicate"
                                                         },
                                                         {
                                                             kind: "spacer",
                                                             id: "duplicate"
                                                         }
                                                     ])), null);
    }

    function test_invalidConfigMustNotReplaceSavedData() {
        const invalid = ["", "invalid", "null", "[]", '{"schemaVersion":2,"pinned":[],"options":{}}',
                         encodedConfig([
                                           {
                                               kind: "app",
                                               desktopId: "../../run.desktop"
                                           }
                                       ]), encodedConfig([
                                                             {
                                                                 kind: "app",
                                                                 desktopId: ".desktop"
                                                             }
                                                         ]), encodedConfig([
                                                                               {
                                                                                   kind: "spacer",
                                                                                   id: "bad/id"
                                                                               }
                                                                           ]), encodedConfig([
                                                                                                 {
                                                                                                     kind: "app",
                                                                                                     desktopId:
                                                                                                     "x"
                                                                                                 },
                                                                                                 {
                                                                                                     kind: "app",
                                                                                                     desktopId:
                                                                                                     "x.desktop"
                                                                                                 }
                                                                                             ]), encodedConfig(
                             [
                                 {
                                     kind: "spacer",
                                     id: "same"
                                 },
                                 {
                                     kind: "spacer",
                                     id: "same"
                                 }
                             ]), encodedConfig([], {
                                                   autoHide: "true"
                                               }), encodedConfig([], {
                                                                     unknownOption: true
                                                                 })];
        for (const text of invalid)
            compare(DockModel.decodeConfig(text), null);
        verify(DockModel.decodeConfig(encodedConfig([])) !== null);
    }

    function test_exactDesktopAndStartupClassIdentity() {
        compare(DockModel.applicationForWindow({
                                                   appId: "org.example.Editor"
                                               }, applications).id, "org.example.Editor");
        compare(DockModel.applicationForWindow({
                                                   appId: "EditorWindow"
                                               }, applications).id, "org.example.Editor");
        compare(DockModel.applicationForWindow({
                                                   appId: "org.example.Browser.desktop"
                                               }, applications).id, "org.example.Browser.desktop");
        compare(DockModel.applicationForWindow({
                                                   appId: "editorwindow"
                                               }, applications).id, "org.example.Editor");
        compare(DockModel.applicationForWindow({
                                                   appId: "Editor"
                                               }, applications), null);
        compare(DockModel.applicationForWindow({
                                                   appId: "whatever",
                                                   title: "clavis-control-center"
                                               }, applications).id, "org.clavis.Settings");
        const ambiguous = applications.concat([
                                                  {
                                                      id: "other",
                                                      startupClass: "EditorWindow"
                                                  }
                                              ]);
        compare(DockModel.applicationForWindow({
                                                   appId: "EditorWindow"
                                               }, ambiguous), null);
        // A class collision cannot override an exact desktop identity.
        const collision = applications.concat([
                                                  {
                                                      id: "third",
                                                      startupClass: "org.example.Editor"
                                                  }
                                              ]);
        compare(DockModel.applicationForWindow({
                                                   appId: "org.example.Editor"
                                               }, collision).id, "org.example.Editor");
    }

    function test_groupingKeepsUnknownWindowsAndMruSeparate() {
        const windows = [
                  {
                      id: 1,
                      appId: "org.example.Editor",
                      isFocused: false
                  },
                  {
                      id: 2,
                      appId: "EditorWindow",
                      isFocused: false
                  },
                  {
                      id: 3,
                      appId: "EditorWindow",
                      isFocused: true
                  },
                  {
                      id: 4,
                      appId: "unknown"
                  },
                  {
                      id: 5,
                      appId: "unknown"
                  },
                  {
                      id: 6,
                      appId: "uninstalled-app"
                  },
                  {
                      id: 7,
                      appId: "uninstalled-app"
                  }
              ];
        const grouped = DockModel.groupWindows(windows, applications, {
                                                   1: 5,
                                                   2: 8
                                               });
        compare(Object.keys(grouped).length, 4);
        compare(grouped["app:org.example.Editor"].windows.map(window => window.id).join(","), "3,2,1");
        compare(grouped["window:4"].windows.length, 1);
        compare(grouped["window:5"].windows.length, 1);
        compare(grouped["window-app:uninstalled-app"].windows.length, 2);
        compare(windows[0].id, 1);
    }

    function test_recentApplicationsDeduplicatePinnedAndRunning() {
        const available = applications.concat([
                                                  {
                                                      id: "extra"
                                                  },
                                                  {
                                                      id: "fourth"
                                                  },
                                                  {
                                                      id: "fifth"
                                                  }
                                              ]);
        const history = {
            "org.example.Editor": {
                lastLaunchedAt: 100
            },
            "org.example.Browser": {
                lastLaunchedAt: 40
            },
            "org.example.Browser.desktop": {
                lastLaunchedAt: 50
            },
            "org.clavis.Settings": {
                lastLaunchedAt: 30
            },
            extra: {
                lastLaunchedAt: 20
            },
            fourth: {
                lastLaunchedAt: 10
            },
            fifth: {
                lastLaunchedAt: 1
            },
            uninstalled: {
                lastLaunchedAt: 1000
            }
        };
        compare(DockModel.recentIds(history, available, new Set(["app:org.example.Editor"]), 3).join(","),
                "org.example.Browser,org.clavis.Settings,extra");
        compare(DockModel.recentIds(history, available, new Set(["app:org.example.Editor",
                                                                 "app:org.example.Browser"]), 3).join(","),
                "org.clavis.Settings,extra,fourth");
    }

    function test_smallSpacerDropAndConfigRoundTrip() {
        const payload = DockModel.dropPayload('{"schemaVersion":1,"kind":"small-spacer"}');
        compare(payload.kind, "small-spacer");
        const decoded = DockModel.decodeConfig(encodedConfig([
                                                                 {
                                                                     kind: "app",
                                                                     desktopId: "example"
                                                                 },
                                                                 {
                                                                     kind: payload.kind,
                                                                     id: "small"
                                                                 },
                                                                 {
                                                                     kind: "spacer",
                                                                     id: "regular"
                                                                 }
                                                             ], {}));
        verify(decoded !== null);
        compare(decoded.pinned[1].kind, "small-spacer");
        compare(DockModel.pinnedKey(decoded.pinned[1]), "spacer:small");
        compare(DockModel.decodeConfig(JSON.stringify(decoded)), decoded);
        const moved = DockModel.movePinned(decoded.pinned, "spacer:small", 0);
        compare(moved[0].kind, "small-spacer");
        compare(moved[2].kind, "spacer");
    }

    function test_dropProtocolAndInstalledPathBoundaries() {
        compare(DockModel.dropPayload(
                    '{"schemaVersion":1,"kind":"app","desktopId":"org.example.Editor.desktop"}').desktopId,
                "org.example.Editor");
        compare(DockModel.dropPayload('{"schemaVersion":1,"kind":"spacer"}').kind, "spacer");
        for (const text of ["org.example.Editor", "{}", '{"schemaVersion":2,"kind":"spacer"}',
                            '{"schemaVersion":1,"kind":"app","desktopId":"/tmp/app.desktop"}'])
            compare(DockModel.dropPayload(text), null);
        const roots = ["/home/example/.local/share", "/usr/share"];
        compare(DockModel.desktopIdForPath("/usr/share/applications/org.example.Editor.desktop", roots),
                "org.example.Editor");
        compare(DockModel.desktopIdForPath("/home/example/.local/share/applications/vendor/editor.desktop",
                                           roots), "vendor-editor");
        for (const path of ["/tmp/org.example.Editor.desktop", "/usr/share/fake/applications/editor.desktop",
                            "/usr/share/applications/../editor.desktop", "/usr/share/applications/editor.sh"])
            compare(DockModel.desktopIdForPath(path, roots), "");
    }

    function test_reconcilePreservesLiveRowsThroughUpdatesAndReordering() {
        DockModel.reconcile(rows, [
                                {
                                    key: "a",
                                    name: "A",
                                    count: 1
                                },
                                {
                                    key: "b",
                                    name: "B",
                                    count: 2
                                }
                            ]);
        const a = rows.get(0);
        const b = rows.get(1);
        DockModel.reconcile(rows, [
                                {
                                    key: "b",
                                    name: "Renamed",
                                    count: 3
                                },
                                {
                                    key: "a",
                                    name: "A",
                                    count: 1
                                },
                                {
                                    key: "c",
                                    name: "C",
                                    count: 1
                                }
                            ]);
        compare(rows.count, 3);
        compare(rows.get(0), b);
        compare(rows.get(1), a);
        compare(b.name, "Renamed");
        compare(b.count, 3);
        DockModel.reconcile(rows, [
                                {
                                    key: "c",
                                    name: "C",
                                    count: 1
                                },
                                {
                                    key: "a",
                                    name: "A",
                                    count: 2
                                }
                            ]);
        compare(rows.count, 2);
        compare(rows.get(1), a);
        compare(a.count, 2);
        compare(rows.get(0).key, "c");
    }

    function test_pinMoveUsesVisibleInsertionGap() {
        const pinned = [
                  {
                      kind: "app",
                      desktopId: "a"
                  },
                  {
                      kind: "spacer",
                      id: "gap"
                  },
                  {
                      kind: "app",
                      desktopId: "b"
                  }
              ];
        const ids = entries => entries.map(entry => DockModel.pinnedKey(entry)).join(",");
        compare(ids(DockModel.movePinned(pinned, "app:a", 0)), "app:a,spacer:gap,app:b");
        compare(ids(DockModel.movePinned(pinned, "app:a", 1)), "app:a,spacer:gap,app:b");
        compare(ids(DockModel.movePinned(pinned, "app:a", 2)), "spacer:gap,app:a,app:b");
        compare(ids(DockModel.movePinned(pinned, "app:a", 3)), "spacer:gap,app:b,app:a");
        compare(ids(DockModel.movePinned(pinned, "app:b", 0)), "app:b,app:a,spacer:gap");
        compare(ids(DockModel.movePinned(pinned, "app:b", 99)), "app:a,spacer:gap,app:b");
        compare(DockModel.movePinned(pinned, "missing", 0), null);
        compare(ids(pinned), "app:a,spacer:gap,app:b");
    }

    function test_launchWaitsForNewMatchingWindowOrTimeout() {
        const pending = {
            "app:editor": {
                deadline: 500,
                windowIds: ["1"]
            }
        };
        verify(DockModel.pendingLaunches(pending, {}, 100)["app:editor"] !== undefined);
        verify(DockModel.pendingLaunches(pending, {
                                             "app:editor": {
                                                 windows: [
                                                     {
                                                         id: 1
                                                     }
                                                 ]
                                             }
                                         }, 100)["app:editor"] !== undefined);
        compare(Object.keys(DockModel.pendingLaunches(pending, {
                                                          "app:editor": {
                                                              windows: [
                                                                  {
                                                                      id: 1
                                                                  },
                                                                  {
                                                                      id: 2
                                                                  }
                                                              ]
                                                          }
                                                      }, 100)).length, 0);
        compare(Object.keys(DockModel.pendingLaunches(pending, {}, 500)).length, 0);
        verify(DockModel.pendingLaunches(pending, {
                                             "app:other": {
                                                 windows: [
                                                     {
                                                         id: 2
                                                     }
                                                 ]
                                             }
                                         }, 100)["app:editor"] !== undefined);
    }
}
