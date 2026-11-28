// Runtime probe harness for scripts/dev/probe-bar.sh (B8.6).
// The script copies shell/ to a temp dir and installs this file as shell.qml,
// so the bar loads in isolation (no ledger, no panel window) and answers over
// the bar-probe IPC target. Keep the top-level imports: they synthesize the
// qs.* qmldirs that Loader-loaded bar files resolve (loader-form.md).
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.SystemTray
import Quickshell.Services.UPower
import qs.commons
import qs.commons.cards
import qs.commons.i18n
import qs.services
import qs.ui
import "commons/BarGeometry.js" as BarGeometry
import "services/ConfigMigrations.js" as ConfigMigrations
import "services/BarWidgetDefaults.js" as BarWidgetDefaults
import "services/BarDefaults.js" as BarDefaults
import "services/BarStylePresets.js" as BarStylePresets
import "plugins/bar" as BarPlugin
import "plugins/bar/SegmentRoles.js" as SegmentRoles
import "plugins/bar/OverflowLayout.js" as OverflowLayout

ShellRoot {
    id: probeRoot

    // The harness stages a 2560-wide horizontal bar or a 1440-tall vertical
    // one, so lane geometry is evaluated against a realistic screen axis.
    readonly property bool probeVertical: Config.options.bar.vertical
    property int probeWidth: probeVertical ? Appearance.sizes.verticalBarWidth : 2560
    property real probeHeight: probeVertical ? 1440 : Appearance.sizes.barHeight
    readonly property string probeShell: String(Quickshell.env("NYXURI_PROBE_SHELL") || "")
    property bool reloading: false
    // Window phase: loads the real Bar.qml (PanelWindow + content) so the
    // probe can assert orientation switching at the window level. The content
    // phase must stand down first (one production instance at a time).
    property bool windowMode: false

    // D4g batch two: the capability catalog the settings faces consume.
    BarWidgetCatalog {
        id: catalogProbe
    }

    Item {
        id: stage

        width: probeRoot.probeWidth
        height: probeRoot.probeHeight

        Loader {
            id: barLoader

            anchors.fill: parent
            // file:// matters: the qs: scheme cannot resolve implicit sibling
            // types in this Quickshell runtime (loader-form.md). The real shell
            // also feeds PluginRegistry.fileUrl() to its slot Loaders.
            // Wait for the settings store before first load: BarContent reads
            // PersonalizationConfig and a later preset flip would leave
            // layout sizes stale in a windowless harness.
            // D4g: one host file — the orientation follows the staged bar's
            // axes.position (BarContent builds its AxisContext off it).
            active: !probeRoot.windowMode && PersonalizationConfig.ready && !probeRoot.reloading
            source: probeRoot.probeShell !== "" ? "file://" + probeRoot.probeShell + "/plugins/bar/BarContent.qml" : ""
        }

        // D1 B-10: the island media face probed with a stub host — the real
        // face needs an MPRIS player, but its control matrix (controls ×
        // visualizer style, cava lease) is config-driven and evaluates with
        // a null player. Hidden, but instantiated on demand so bindings run.
        Item {
            id: islandMediaStub
            // opacity (not visible:false): an invisible parent freezes the
            // children's visible bindings at creation values, which would
            // wreck the control matrix the stub exists to measure.
            opacity: 0
            width: 220
            height: 32
            property real pillHeight: 32
            property bool vertical: false
            property bool isMaterial: PersonalizationConfig.barTint
            property var widgetBar: null
            property var activePlayer: null
            property bool mediaTrackInfoVisible: false
            property real mediaTextContentWidth: 0
            function option(key) {
                if (key === "showMediaControls")
                    return PersonalizationConfig.islandShowMediaControls;
                if (key === "visualizerStyle")
                    return PersonalizationConfig.islandVisualizerStyle;
                return BarWidgetDefaults.option("island", PersonalizationConfig.islandEntry(), key);
            }

            Loader {
                id: islandMediaLoader
                anchors.fill: parent
                active: false
                // setSource carries the required `di` property — a plain
                // source string cannot initialize required properties.
                Component.onCompleted: {
                    if (probeRoot.probeShell !== "")
                        setSource("file://" + probeRoot.probeShell + "/plugins/bar/DiMedia.qml", {
                            "di": islandMediaStub
                        });
                }
            }
        }
    }

    Loader {
        id: windowLoader

        active: probeRoot.windowMode && PersonalizationConfig.ready
        source: probeRoot.probeShell !== "" ? "file://" + probeRoot.probeShell + "/plugins/bar/Bar.qml" : ""
    }

    // Tray telemetry needs the live SysTray widget: walk the loaded bar tree for
    // the object that exposes the probe surface (pinned/unpinned counts).
    function findTrayWidget(node): var {
        if (!node)
            return null;
        if (node.unpinnedCount !== undefined && node.overflowVisible !== undefined)
            return node;
        const kids = node.children ?? [];
        for (let i = 0; i < kids.length; i += 1) {
            const found = probeRoot.findTrayWidget(kids[i]);
            if (found)
                return found;
        }
        return null;
    }

    // SystemIcons telemetry: every status lives in a fixed 26px slot. The
    // widget exposes its Flow as `slotContainer`, so the probe can report the
    // evaluated slot geometry instead of re-deriving it.
    function findSystemIconsWidget(node): var {
        if (!node)
            return null;
        if (node.slotContainer !== undefined)
            return node;
        const kids = node.children ?? [];
        for (let i = 0; i < kids.length; i += 1) {
            const found = probeRoot.findSystemIconsWidget(kids[i]);
            if (found)
                return found;
        }
        return null;
    }

    function findIdleFace(node): var {
        if (!node)
            return null;
        if (node.probeClockFace !== undefined)
            return node;
        const kids = node.children ?? [];
        for (let i = 0; i < kids.length; i += 1) {
            const found = probeRoot.findIdleFace(kids[i]);
            if (found)
                return found;
        }
        return null;
    }

    // D1: duck-typed walks for the media widget (bar lane) and the island's
    // media face (island internals) — both identified by their probe markers.
    function findMediaWidget(node): var {
        if (!node)
            return null;
        if (node.probeMediaSurface === true)
            return node;
        const kids = node.children ?? [];
        for (let i = 0; i < kids.length; i += 1) {
            const found = probeRoot.findMediaWidget(kids[i]);
            if (found)
                return found;
        }
        return null;
    }

    // D1: the bar Visualizer, identified by its own public props (no probe
    // marker needed on the widget itself).
    function findVisualizerWidget(node): var {
        if (!node)
            return null;
        if (node.sharedPoints !== undefined && node.barCount !== undefined)
            return node;
        const kids = node.children ?? [];
        for (let i = 0; i < kids.length; i += 1) {
            const found = probeRoot.findVisualizerWidget(kids[i]);
            if (found)
                return found;
        }
        return null;
    }

    // B9.7: generic duck-typed walk for the settled-settings consumers.
    function findNodes(item, predicate, out): var {
        if (!item || !item.children)
            return out;
        for (let i = 0; i < item.children.length; i += 1) {
            const child = item.children[i];
            if (!child)
                continue;
            if (predicate(child))
                out.push(child);
            probeRoot.findNodes(child, predicate, out);
        }
        return out;
    }

    function systemIconsReport(): string {
        const widget = probeRoot.findSystemIconsWidget(barLoader.item);
        if (!widget)
            return JSON.stringify({
                "found": false
            });
        const flow = widget.slotContainer;
        const slots = [];
        for (let i = 0; i < flow.children.length; i += 1) {
            const slot = flow.children[i];
            if (!slot || slot.slotSize === undefined)
                continue;
            slots.push({
                "key": String(slot.slotKey ?? ""),
                "visible": slot.visible,
                "x": slot.x,
                "width": slot.width,
                "implicitWidth": slot.implicitWidth,
                "slotSize": slot.slotSize,
                "icon": String(slot.iconText ?? ""),
                "tooltip": String(slot.toolTipText ?? ""),
                "critical": slot.critical === true,
                "dataText": String(slot.dataText ?? ""),
                "expanded": slot.expanded === true,
                "intentHovered": slot.intentHovered === true,
                "expandable": slot.expandable === true
            });
        }
        return JSON.stringify({
            "found": true,
            "material": widget.isMaterial,
            "groupWidth": widget.implicitWidth,
            "groupHeight": widget.implicitHeight,
            "slots": slots
        });
    }

    function collectLoaders(item, out) {
        if (!item || !item.children)
            return out;
        for (let i = 0; i < item.children.length; i += 1) {
            const child = item.children[i];
            if (!child)
                continue;
            // B9.6: end4's FadeLoader idiom wraps an inline child Loader, so a
            // Loader with neither `source` nor `sourceComponent` set is a fade
            // container, not an async load. Only real loads can hang.
            const isRealLoad = !!child.sourceComponent || String(child.source ?? "") !== "";
            if (child.status !== undefined && isRealLoad && child.active === true) {
                out.push({
                    "source": String(child.source || (child.sourceComponent ? "<component>" : "")),
                    "status": child.status,
                    "error": child.status === Loader.Error ? String(child.errorString || "") : ""
                });
            }
            if (child.children !== undefined && child.children !== null)
                probeRoot.collectLoaders(child, out);
        }
        return out;
    }

    // B9.6: duck-typed finds for the style-editor chain (BarGroup by widget
    // name) and the fixed-slot workspaces model (fakeWorkspace+shownCount are
    // unique to that widget in the bar tree). Both bar branches (material /
    // non-material) declare groups with the same widgetName, so an unloaded
    // twin must not shadow the live one.
    function findGroup(item, name) {
        let fallback = null;
        let out = null;
        const walk = item => {
            if (!item || !item.children || out !== null)
                return;
            for (let i = 0; i < item.children.length; i += 1) {
                const child = item.children[i];
                if (!child)
                    continue;
                if (child.widgetName === name && child.loadedWidget !== undefined) {
                    if (child.loadedWidget !== null) {
                        out = child;
                        return;
                    }
                    if (fallback === null)
                        fallback = child;
                }
                walk(child);
            }
        };
        walk(item);
        return out ?? fallback;
    }

    // Lane-filled probe helper: the raw lane arrays before BarContent's
    // system filters, so a collapse failure can be attributed to the filter
    // or to the geometry chain.
    function rootLaneFilled(content) {
        const lanes = {
            "left": PersonalizationConfig.barLayoutEntriesLeft,
            "middle": PersonalizationConfig.barLayoutEntriesMiddle,
            "right": PersonalizationConfig.barLayoutEntriesRight
        };
        return {
            "store": {
                "left": lanes.left.map(entry => entry.widgetId + (entry.enabled === false ? ":off" : "")),
                "middle": lanes.middle.map(entry => entry.widgetId + (entry.enabled === false ? ":off" : "")),
                "right": lanes.right.map(entry => entry.widgetId + (entry.enabled === false ? ":off" : ""))
            },
            "effective": {
                "left": (content.effectiveLeftLayout || []).map(entry => entry.widgetId),
                "middle": (content.effectiveMiddleLayout || []).map(entry => entry.widgetId),
                "right": (content.effectiveRightLayout || []).map(entry => entry.widgetId)
            }
        };
    }

    function findWorkspace(item) {
        if (!item || !item.children)
            return null;
        for (let i = 0; i < item.children.length; i += 1) {
            const child = item.children[i];
            if (!child)
                continue;
            if (child.fakeWorkspace !== undefined && child.shownCount !== undefined)
                return child;
            const nested = probeRoot.findWorkspace(child);
            if (nested)
                return nested;
        }
        return null;
    }

    // D4b: first live lane entry of a widget id (entry-override reads and
    // writes address one instance).
    function findWidgetEntry(widgetId): var {
        const lanes = PersonalizationConfig.barLayoutEntriesLeft.concat(PersonalizationConfig.barLayoutEntriesMiddle, PersonalizationConfig.barLayoutEntriesRight);
        for (let i = 0; i < lanes.length; i += 1) {
            if (lanes[i].widgetId === widgetId)
                return lanes[i];
        }
        return null;
    }

    // D4a: every loaded group carrying the widget name (duplicate ids are
    // legal — spacers), in tree order.
    function findGroups(item, name) {
        const out = [];
        const walk = current => {
            if (!current || !current.children)
                return;
            for (let i = 0; i < current.children.length; i += 1) {
                const child = current.children[i];
                if (!child)
                    continue;
                if (child.widgetName === name && child.loadedWidget !== undefined && child.loadedWidget !== null)
                    out.push(child);
                walk(child);
            }
        };
        walk(item);
        return out;
    }

    function layout(): string {
        const barContent = barLoader.item;
        if (!barContent)
            return JSON.stringify({
                "ready": false,
                "status": barLoader.status,
                "error": String(barLoader.errorString || "")
            });
        const loaders = probeRoot.collectLoaders(barContent, []);
        const failed = loaders.filter(entry => entry.status === Loader.Error);
        const pending = loaders.filter(entry => entry.status === Loader.Null || entry.status === Loader.Loading);
        const host = ActionGateway.islandHost;
        let island = null;
        if (host) {
            const point = host.mapToItem(barContent, 0, 0);
            island = {
                "x": point.x,
                "y": point.y,
                "width": host.implicitWidth,
                "height": host.implicitHeight,
                "visible": host.visible,
                "idleWidth": host.idleWidth,
                "idleTextContentWidth": host.idleTextContentWidth,
                "activeContent": String(host.activeContentId ?? "")
            };
        }
        const vertical = barContent.vertical === true;
        const geometry = vertical ? {
            "width": barContent.width,
            "height": barContent.height,
            "centerY": barContent.laneCenterY,
            "centerHeight": barContent.laneCenterHeight,
            "topHeight": barContent.laneTopHeight,
            "bottomHeight": barContent.laneBottomHeight,
            "centerPillY": barContent.centerPillY,
            "centerPillHeight": barContent.centerPillHeight
        } : {
            "width": barContent.width,
            "height": barContent.height,
            "centerX": barContent.laneCenterX,
            "centerWidth": barContent.laneCenterWidth,
            "leftWidth": barContent.laneLeftWidth,
            "rightWidth": barContent.laneRightWidth,
            "centerPillX": barContent.centerPillX,
            "centerPillWidth": barContent.centerPillWidth
        };
        const values = vertical ? [geometry.width, geometry.height, geometry.centerY, geometry.centerHeight] : [geometry.width, geometry.height, geometry.centerX, geometry.centerWidth];
        const finite = values.every(value => typeof value === "number" && isFinite(value));
        const centered = !barContent.effectiveMiddleLayout || barContent.effectiveMiddleLayout.length === 0 || (vertical ? Math.abs(geometry.centerY - (geometry.height - geometry.centerHeight) / 2) <= 1 : Math.abs(geometry.centerX - (geometry.width - geometry.centerWidth) / 2) <= 1);
        return JSON.stringify({
            "ready": barLoader.status === Loader.Ready,
            "preset": BarStylePresets.currentPreset(PersonalizationConfig.barAxes),
            "widgetStyle": PersonalizationConfig.barWidgetStyle,
            "vertical": vertical,
            "edge": PersonalizationConfig.barPosition,
            "lanes": {
                "left": (barContent.effectiveLeftLayout || []).map(entry => entry.widgetId),
                "middle": (barContent.effectiveMiddleLayout || []).map(entry => entry.widgetId),
                "right": (barContent.effectiveRightLayout || []).map(entry => entry.widgetId)
            },
            "geometry": geometry,
            "island": island,
            "islandInLayout": PersonalizationConfig.islandInLayout,
            "keyboard": {
                "available": KeyboardIndicators.available,
                "caps": KeyboardIndicators.capsLock,
                "num": KeyboardIndicators.numLock
            },
            "islandState": host ? String(host.invoke("state")) : "UNAVAILABLE",
            "loaders": loaders,
            "failed": failed,
            "pending": pending,
            "ok": barLoader.status === Loader.Ready && failed.length === 0 && pending.length === 0 && finite && centered && (island === null || (isFinite(island.x) && island.width > 0))
        });
    }

    IpcHandler {
        target: "bar-probe"

        function ping(): string {
            return "PONG";
        }

        // D4a boot diagnostics: raw store state for fresh-file tracing.
        function d4aBootState(): string {
            return JSON.stringify({
                "storeReady": ConfigService.storeReady,
                "rawBar": ConfigService.rawConfig ? ConfigService.rawConfig.bar : null,
                "configVersionDirty": PersonalizationConfig.configVersionDirty,
                "barConfigs": PersonalizationConfig.barConfigs,
                "laneViewLeft": PersonalizationConfig.barLayoutLeft
            });
        }

        function windowMode(value: bool): string {
            probeRoot.windowMode = value;
            GlobalStates.barOpen = value;
            return String(probeRoot.windowMode);
        }

        // Window-level evidence (B9.4): the real window and content geometry.
        // Conditional anchors used to leave the content 2519 wide after a
        // top->left switch and 1440 tall after switching back, so this probe
        // watches both axes on every edge change.
        function windowDump(): string {
            const window = windowLoader.item ? windowLoader.item.windowProbe : null;
            if (!window)
                return JSON.stringify({
                    "found": false
                });
            const content = window.barContent;
            return JSON.stringify({
                "found": true,
                "edge": String(window.edge),
                "vertical": window.vertical === true,
                // B9.7: autohide collapses the reservation to zero.
                "exclusiveZone": Math.round(window.exclusiveZone),
                "autoHide": window.autoHideEnabled === true,
                "screenList": Array.from(Config.options.bar.screenList ?? []),
                "window": {
                    "w": Math.round(window.width),
                    "h": Math.round(window.height)
                },
                "content": content ? {
                    "w": Math.round(content.width),
                    "h": Math.round(content.height),
                    "x": Math.round(content.x),
                    "y": Math.round(content.y),
                    "offsetX": Math.round(window.contentOffsetX),
                    "offsetY": Math.round(window.contentOffsetY)
                } : null,
                "lanes": content && content.vertical ? {
                    "top": Math.round(content.laneTopHeight),
                    "centerH": Math.round(content.laneCenterHeight),
                    "bottom": Math.round(content.laneBottomHeight)
                } : null,
                "middle": content ? Array.from(content.effectiveMiddleLayout ?? []) : null,
                "expected": {
                    "barHeight": Appearance.sizes.barHeight,
                    "verticalBarWidth": Appearance.sizes.verticalBarWidth,
                    "screenRounding": Appearance.rounding.screenRounding
                }
            });
        }

        function layout(): string {
            return probeRoot.layout();
        }

        function stylePreset(key: string): string {
            PersonalizationConfig.applyBarStylePreset(key);
            return BarStylePresets.currentPreset(PersonalizationConfig.barAxes);
        }

        function widgetStyle(value: string): string {
            PersonalizationConfig.setBarWidgetStyle(value);
            return String(PersonalizationConfig.barWidgetStyle);
        }

        // B9.4: switching the screen edge swaps the content component, so the
        // probe reloads after the store write.
        function edge(value: string): string {
            PersonalizationConfig.setBarPosition(value);
            probeRoot.reloading = true;
            Qt.callLater(function () {
                probeRoot.reloading = false;
            });
            return String(PersonalizationConfig.barPosition);
        }

        // Layout scenes: "mediaOnly" is the self-hiding-widget contract (an
        // empty lane must collapse to zero instead of keeping capsule
        // padding); "default" restores the shipped three-lane layout.
        // B9.7 scenes single out the widgets whose settings rows need
        // runtime evidence (util buttons, resources, the divider).
        function scene(name: string): string {
            if (name === "mediaOnly") {
                PersonalizationConfig.setBarLayouts(["media"], [], []);
            } else if (name === "centerOnly") {
                PersonalizationConfig.setBarLayouts([], ["clock"], []);
            } else if (name === "centerIsland") {
                // B9.6: island-only middle lane in center-only mode, so the
                // frame-hug branch (row - 4 / + 8) is observable.
                PersonalizationConfig.setBarLayouts([], ["island"], []);
            } else if (name === "utilOnly") {
                PersonalizationConfig.setBarLayouts([], [], ["utilButtons"]);
            } else if (name === "monitorOnly") {
                PersonalizationConfig.setBarLayouts([], [], ["systemMonitor"]);
            } else if (name === "divisorLeft") {
                PersonalizationConfig.setBarLayouts(["divisor"], [], []);
            } else {
                const left = PersonalizationConfig.defaultBarLayoutLeft.slice();
                const middle = PersonalizationConfig.defaultBarLayoutMiddle.slice();
                const right = PersonalizationConfig.defaultBarLayoutRight.slice();
                PersonalizationConfig.setBarLayouts(left, middle, right);
            }
            return JSON.stringify({
                "left": Array.from(PersonalizationConfig.barLayoutLeft),
                "middle": Array.from(PersonalizationConfig.barLayoutMiddle),
                "right": Array.from(PersonalizationConfig.barLayoutRight)
            });
        }

        // B9.5: the pure outer-margin / exclusive-zone math for every edge and
        // the 0/12/24 margin tiers (Bar.qml binds the same functions).
        function margins(): string {
            const cases = [];
            const boost = PersonalizationConfig.barStyleBoostFor(PersonalizationConfig.barAxes);
            for (const edge of ["top", "bottom", "left", "right"]) {
                const vertical = edge === "left" || edge === "right";
                for (const tier of [0, 12, 24]) {
                    cases.push({
                        "edge": edge,
                        "vertical": vertical,
                        "tier": tier,
                        "box": BarGeometry.margins(edge, vertical, tier, tier, false, false),
                        "exclusiveZone": BarGeometry.exclusiveZone(vertical, Appearance.sizes.baseBarHeight, Appearance.sizes.baseVerticalBarWidth, boost, tier)
                    });
                }
            }
            return JSON.stringify({
                "baseBarHeight": Appearance.sizes.baseBarHeight,
                "baseVerticalBarWidth": Appearance.sizes.baseVerticalBarWidth,
                "verticalBarWidth": Appearance.sizes.verticalBarWidth,
                "styleBoost": boost,
                "cases": cases
            });
        }

        function osd(kind: string): string {
            GlobalStates.osdKind = kind;
            return "OK";
        }

        // B9.6: right-click style editor chain end-to-end. The write goes
        // through the same store setter the popup uses; the dump reads the
        // BarGroup binding and the bound widget property. D4c: the style
        // keys ride the lane entry (uid addressed).
        function b96Style(on: bool): string {
            const zones = ["left", "middle", "right"];
            let uid = "";
            for (let z = 0; z < zones.length; z += 1) {
                const lane = PersonalizationConfig.laneEntries(zones[z]);
                for (let i = 0; i < lane.length; i += 1) {
                    if (lane[i].widgetId === "workspaces")
                        uid = lane[i].uid;
                }
            }
            if (uid === "")
                return "NO-ENTRY";
            if (on)
                PersonalizationConfig.setBarEntryStyle(uid, "color", "primary");
            else
                PersonalizationConfig.resetBarEntryStyle(uid);
            return "OK";
        }

        function b96Dump(): string {
            const content = barLoader.item;
            if (!content)
                return JSON.stringify({
                    "ready": false
                });
            const group = probeRoot.findGroup(content, "workspaces");
            const ws = probeRoot.findWorkspace(content);
            // The global island host wins when set (it is the one consuming
            // services); otherwise resolve from the content tree — an
            // unloaded material-branch twin must not shadow the live island.
            const islandGroup = probeRoot.findGroup(content, "island");
            const host = ActionGateway.islandHost ?? (islandGroup ? islandGroup.loadedWidget : null);
            return JSON.stringify({
                "ready": true,
                "preset": BarStylePresets.currentPreset(PersonalizationConfig.barAxes),
                "centerPill": {
                    "width": content.centerPillWidth,
                    "middleRowWidth": content.middleRowImplicitWidth
                },
                "style": group ? {
                    "hasOverride": group.hasContentOverride === true,
                    "groupContentColor": String(group.contentColor),
                    "expectedOnPrimary": String(Appearance.colors.colOnPrimary)
                } : null,
                "widget": ws ? {
                    "hasContentColorProps": ("contentColor" in ws) && ("contentColorOverridden" in ws),
                    "contentColorOverridden": ws.contentColorOverridden === true,
                    "contentColor": String(ws.contentColor),
                    "existingMaxIdx": ws.existingMaxIdx,
                    "shown": ws.shownCount,
                    "slotWidth": ws.workspaceButtonWidth,
                    "implicitWidth": ws.implicitWidth,
                    "style": String(ws.style),
                    "slotLength": ws.slotLength,
                    "fakeWorkspace": ws.fakeWorkspace
                } : null,
                "islandCapsule": host ? {
                    "transparent": String(host.probeCapsuleColor) === "transparent" || String(host.probeCapsuleColor) === "#00000000",
                    "layer0": String(host.probeCapsuleColor) === String(Appearance.colors.colLayer0)
                } : null
            });
        }

        function keyboardFlip(): string {
            KeyboardIndicators.popupKind = "caps";
            KeyboardIndicators.popupActive = true;
            KeyboardIndicators.popupText = "Caps Lock on";
            KeyboardIndicators.popupSequence += 1;
            return "OK";
        }

        function islandInLayout(value: bool): string {
            PersonalizationConfig.setIslandInLayout(value);
            return JSON.stringify({
                "islandInLayout": PersonalizationConfig.islandInLayout,
                "middle": Array.from(PersonalizationConfig.barLayoutMiddle)
            });
        }

        // B9.3 migration: pure layout resolution with a saved config that has
        // an empty middle lane. `layoutMigrated=true` must not re-seed the
        // island; a config missing the key seeds it once; a legacy
        // `enabled=false` drops it.
        function islandLayoutMigration(): string {
            const base = {
                "barLayoutLeft": [],
                "barLayoutMiddle": [],
                "barLayoutRight": []
            };
            return JSON.stringify({
                "seeded": PersonalizationConfig.resolveBarLayouts(base, {}, true),
                "keptEmpty": PersonalizationConfig.resolveBarLayouts(base, {
                    "layoutMigrated": true
                }, true),
                "legacyOff": PersonalizationConfig.resolveBarLayouts({
                    "barLayoutLeft": [],
                    "barLayoutMiddle": ["island"],
                    "barLayoutRight": []
                }, {
                    "layoutMigrated": true
                }, false)
            });
        }

        // D4a: the version chain on a legacy v2 shape. The legacy keys fold
        // into [[bar.configs]], the divisor alias canonicalizes, the island
        // seed spends itself exactly once, and a second run changes nothing.
        function d4aMigration(): string {
            const legacy = {
                "bar": {
                    "barLayoutLeft": ["launcherButton", "divisor"],
                    "barLayoutMiddle": [],
                    "barLayoutRight": ["clock"]
                }
            };
            const seed = {
                "lanes": PersonalizationConfig.resolveBarLayouts(legacy.bar, {}, true),
                "barDefaults": BarDefaults.DEFAULTS
            };
            const first = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(legacy)), seed);
            const second = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(first.config)), {
                "lanes": PersonalizationConfig.resolveBarLayouts({}, {}, true),
                "barDefaults": BarDefaults.DEFAULTS
            });
            const bar = first.config.bar;
            return JSON.stringify({
                "changed": first.changed,
                "version": first.config.configVersion,
                "lanes": bar.configs[0].lanes,
                "aliasResolved": bar.configs[0].lanes.left.indexOf("separator") !== -1,
                "islandSeeded": bar.configs[0].lanes.middle.indexOf("island") !== -1,
                "legacyStripped": ["barLayoutLeft", "barLayoutMiddle", "barLayoutRight", "barLeadingComponents", "barTrailingComponents"].every(key => bar[key] === undefined),
                "idempotent": second.changed === false && JSON.stringify(second.config.bar.configs) === JSON.stringify(bar.configs)
            });
        }

        // D4a: minimal write. A defaults-equal [bar] serializes to nothing,
        // one axis change writes exactly that key, and a disabled entry
        // serializes as {id, enabled=false} while its default-equal sibling
        // lane collapses to plain strings (or disappears).
        function d4aPersistence(): string {
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            const barDefault = PersonalizationConfig.toJson().bar;
            PersonalizationConfig.setBarThickness(40);
            const barOneKey = PersonalizationConfig.toJson().bar;
            PersonalizationConfig.setBarThickness(PersonalizationConfig.defaultBarThickness);
            const barRestored = PersonalizationConfig.toJson().bar;
            PersonalizationConfig.setBarLayouts(["clock", "workspaces"], [], []);
            PersonalizationConfig.toggleBarEntryEnabled(PersonalizationConfig.barLayoutEntriesLeft[0].uid);
            const disabledSparse = PersonalizationConfig.sparseBarConfigs();
            const disabledIds = PersonalizationConfig.barLayoutEnabledIds("left");
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            return JSON.stringify({
                "defaultEmpty": barDefault === undefined || Object.keys(barDefault).length === 0,
                "singleKey": barOneKey !== undefined && Object.keys(barOneKey).length === 1 && barOneKey.configs !== undefined && barOneKey.configs.length === 1 && Object.keys(barOneKey.configs[0]).length === 2 && barOneKey.configs[0].barThickness === 40,
                "restoredEmpty": barRestored === undefined || Object.keys(barRestored).length === 0,
                "disabledSparse": disabledSparse,
                "enabledViewDropsDisabled": JSON.stringify(disabledIds) === JSON.stringify(["workspaces"]),
                "configVersion": PersonalizationConfig.toJson().configVersion
            });
        }

        // D4a: entry objects drive the live bar, measured after the lane
        // settles (set and dump are separate IPC calls — delegate rebuild
        // must not race the measurement).
        // Scene "spacers": disabled clock + two spacers (one with a size
        // override). Scene "disabledOnly": a lane whose only entry is
        // disabled must collapse like a self-hiding widget.
        function d4aEntriesSet(scene: string): string {
            if (scene === "disabledOnly") {
                PersonalizationConfig.setBarLaneEntries("left", [
                    {
                        "widgetId": "clock",
                        "enabled": false,
                        "overrides": {}
                    }
                ]);
            } else {
                PersonalizationConfig.setBarLaneEntries("left", [
                    {
                        "widgetId": "clock",
                        "enabled": false,
                        "overrides": {}
                    },
                    {
                        "widgetId": "spacer",
                        "enabled": true,
                        "overrides": {
                            "size": 40
                        }
                    },
                    {
                        "widgetId": "spacer",
                        "enabled": true,
                        "overrides": {}
                    }
                ]);
            }
            PersonalizationConfig.setBarLaneEntries("middle", []);
            PersonalizationConfig.setBarLaneEntries("right", []);
            return "OK";
        }

        function d4aEntriesDump(): string {
            const content = barLoader.item;
            const clockGroups = content ? probeRoot.findGroups(content, "clock") : [];
            const spacerGroups = content ? probeRoot.findGroups(content, "spacer") : [];
            const spacerWidths = spacerGroups.map(group => Math.round(group.loadedWidget.width));
            const result = JSON.stringify({
                "disabledNotInstantiated": clockGroups.length === 0,
                "laneCollapsed": content ? Math.round(content.laneLeftWidth) === 0 : false,
                "laneLeftWidthRaw": content ? content.laneLeftWidth : null,
                "laneLeftFilledRaw": content ? probeRoot.rootLaneFilled(content) : null,
                "spacerCount": spacerGroups.length,
                "spacerWidths": spacerWidths,
                "overrideInjected": spacerWidths.indexOf(40) !== -1,
                "defaultSize": spacerWidths.indexOf(20) !== -1
            });
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            return result;
        }

        // D4a: duplicate singleton ids drop during normalize.
        function d4aSingletons(): string {
            const dropped = PersonalizationConfig.setBarLayouts([], ["island", "island", "clock"], []) && PersonalizationConfig.barLayoutMiddle.filter(id => id === "island").length === 1;
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            return JSON.stringify({
                "singletonDropped": dropped
            });
        }

        function islandAvatar(value: bool): string {
            PersonalizationConfig.setIslandShowAvatar(value);
            return JSON.stringify({
                "showAvatar": PersonalizationConfig.islandShowAvatar
            });
        }

        function idleFace(): string {
            const face = probeRoot.findIdleFace(barLoader.item);
            const host = ActionGateway.islandHost;
            return JSON.stringify({
                "found": face !== null,
                "islandState": host ? String(host.invoke("state")) : "UNAVAILABLE",
                "idleWidth": host ? host.idleWidth : null,
                "idleTextContentWidth": host ? host.idleTextContentWidth : null,
                "satellite": PersonalizationConfig.islandSatellite,
                "showAvatar": face ? face.probeAvatarVisible : false,
                "clockVisible": face ? face.probeClockFace !== null && face.probeClockFace.visible : false,
                "clockWidth": face && face.probeClockFace ? face.probeClockFace.implicitWidth : 0,
                "clockHeight": face && face.probeClockFace ? face.probeClockFace.implicitHeight : 0,
                "avatarReady": face ? face.probeAvatarReady : false,
                "avatarFallback": face ? face.probeAvatarFallback : false,
                // D1 three-segment geometry: the clock cluster sits in the
                // pill's optical centre, status cluster right-anchored.
                "clockCenterX": face ? face.probeClockCenterX : null,
                "faceWidth": face ? face.probeFaceWidth : null,
                "statusWidth": face ? face.probeStatusWidth : null
            });
        }

        // D1 quick-fix validation: the media widget's material row must never
        // paint wider than the widget's clamped box (the overflow bug).
        function mediaGeometry(): string {
            const widget = probeRoot.findMediaWidget(barLoader.item);
            if (!widget)
                return JSON.stringify({
                    "found": false
                });
            return JSON.stringify({
                "found": true,
                "visible": widget.barWidgetVisible,
                "widgetWidth": widget.probeWidgetWidth,
                "rowImplicitWidth": widget.probeRowImplicitWidth,
                "rowAssignedWidth": widget.probeRowAssignedWidth,
                "overflow": widget.probeRowAssignedWidth > widget.probeWidgetWidth + 0.5
            });
        }

        // D1 B-10: the island media face control matrix (controls x style),
        // probed through the stub host above (no MPRIS player in the harness;
        // the matrix is config-driven and a null player is exactly the
        // no-lease state worth pinning).
        function islandMediaFace(showControls: string, style: string): string {
            PersonalizationConfig.setIslandShowMediaControls(showControls === "true" || showControls === true);
            PersonalizationConfig.setIslandVisualizerStyle(String(style));
            islandMediaLoader.active = true;
            const face = islandMediaLoader.item;
            return JSON.stringify({
                "found": face !== null && face !== undefined,
                "showControls": PersonalizationConfig.islandShowMediaControls,
                "style": PersonalizationConfig.islandVisualizerStyle,
                "controlsVisible": face ? face.probeControlsVisible : null,
                "waveVisible": face ? face.probeWaveVisible : null,
                "dotsVisible": face ? face.probeDotsVisible : null,
                "waveCavaActive": face ? face.probeWaveCavaActive : null,
                "cavaSubscribers": IslandVisualizerService.subscribers
            });
        }

        // D1: weather wiring — the widget holds a WeatherService lease while
        // it is in a lane and releases it on removal; no data renders "--".
        function weatherLease(mode: string): string {
            if (mode === "on")
                PersonalizationConfig.setBarLayouts(["weather"], [], []);
            else
                PersonalizationConfig.setBarLayouts([], [], []);
            return JSON.stringify({
                "mode": mode,
                "leaseCount": WeatherService.leaseCount,
                "hasData": WeatherService.hasValidData
            });
        }

        // D1: the visualizer widget mounts in a lane without acquiring the
        // cava lease — the process is play-gated, so a playerless harness
        // pins exactly the idle-discipline half (play-lease proof rides the
        // real-machine pass).
        function visualizerLease(mode: string): string {
            try {
                if (mode === "on")
                    PersonalizationConfig.setBarLayouts(["visualizer"], [], []);
                else
                    PersonalizationConfig.setBarLayouts([], [], []);
                const widget = probeRoot.findVisualizerWidget(barLoader.item);
                return JSON.stringify({
                    "mode": mode,
                    "found": widget !== null,
                    "subscribers": IslandVisualizerService.subscribers
                });
            } catch (e) {
                return JSON.stringify({
                    "mode": mode,
                    "error": String(e)
                });
            }
        }

        // D4b: dateFormat is the clock entry's axis — write an override on
        // the live clock entry and read the effective form back through
        // option() (the pre-D4b global [time] key is gone). The default
        // lanes carry no clock, so the probe stages one when absent and
        // restores the lanes afterwards.
        function dateFormatProbe(fmt: string): string {
            let staged = false;
            if (!probeRoot.findWidgetEntry("clock")) {
                const right = PersonalizationConfig.barLayoutEntriesRight.map(entry => ({
                            "widgetId": entry.widgetId,
                            "uid": entry.uid,
                            "enabled": entry.enabled,
                            "overrides": entry.overrides
                        }));
                right.push({
                    "widgetId": "clock",
                    "enabled": true,
                    "overrides": {}
                });
                PersonalizationConfig.setBarLaneEntries("right", right);
                staged = true;
            }
            const entry = probeRoot.findWidgetEntry("clock");
            if (!entry)
                return JSON.stringify({
                    "found": false
                });
            PersonalizationConfig.setBarEntryOverride(entry.uid, "dateFormat", String(fmt || "").trim() || undefined);
            const fresh = probeRoot.findWidgetEntry("clock");
            const pattern = BarWidgetDefaults.option("clock", fresh, "dateFormat");
            const result = JSON.stringify({
                "found": true,
                "format": pattern,
                "date": pattern !== "" ? Qt.formatDateTime(new Date(), pattern) : Qt.formatDateTime(new Date(), "dddd, dd/MM"),
                "shortDate": DateTime.shortDate
            });
            if (staged)
                PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            return result;
        }

        // B9.2 status cluster: read the fixed slot geometry, then swap two fake
        // low/critical peripherals into the service to prove the repeat slots.
        function systemIcons(): string {
            return probeRoot.systemIconsReport();
        }

        function systemIconsFakeDevices(): string {
            PeripheralBattery.deviceSource = [
                {
                    "nativePath": "/probe/mouse",
                    "model": "Probe Mouse",
                    "type": UPowerDeviceType.Mouse,
                    "percentage": 0.15,
                    "state": UPowerDeviceState.Discharging,
                    "isPresent": true
                },
                {
                    "nativePath": "/probe/headset",
                    "model": "Probe Headset",
                    "type": UPowerDeviceType.Headset,
                    "percentage": 0.03,
                    "state": UPowerDeviceState.Discharging,
                    "isPresent": true
                }
            ];
            return "OK";
        }

        function systemIconsResetDevices(): string {
            PeripheralBattery.deviceSource = UPower.devices.values;
            return "OK";
        }

        // D2 SystemIcons QS expansion probe hooks
        function systemIconsHoverSlot(slotKey: string): string {
            const widget = probeRoot.findSystemIconsWidget(barLoader.item);
            if (!widget)
                return "NOT_FOUND";
            const flow = widget.slotContainer;
            for (let i = 0; i < flow.children.length; i += 1) {
                const slot = flow.children[i];
                if (slot && String(slot.slotKey ?? "") === slotKey) {
                    slot.forceHovered = true;
                    return "OK";
                }
            }
            return "SLOT_NOT_FOUND";
        }

        function systemIconsUnhoverSlot(slotKey: string): string {
            const widget = probeRoot.findSystemIconsWidget(barLoader.item);
            if (!widget)
                return "NOT_FOUND";
            const flow = widget.slotContainer;
            for (let i = 0; i < flow.children.length; i += 1) {
                const slot = flow.children[i];
                if (slot && String(slot.slotKey ?? "") === slotKey) {
                    slot.forceHovered = false;
                    slot.forceExpanded = false;
                    return "OK";
                }
            }
            return "SLOT_NOT_FOUND";
        }

        function systemIconsExpandSlot(slotKey: string): string {
            const widget = probeRoot.findSystemIconsWidget(barLoader.item);
            if (!widget)
                return "NOT_FOUND";
            const flow = widget.slotContainer;
            for (let i = 0; i < flow.children.length; i += 1) {
                const slot = flow.children[i];
                if (slot && String(slot.slotKey ?? "") === slotKey) {
                    slot.forceExpanded = true;
                    return "OK";
                }
            }
            return "SLOT_NOT_FOUND";
        }

        // Tray surface (B9.1). The harness publishes fake StatusNotifierItems
        // through scripts/dev/fake-sni.py, then pins/unpins through the same
        // store the widget uses, so the overflow arrow has to react for real.
        function tray(): string {
            const bar = barLoader.item;
            const widget = probeRoot.findTrayWidget(bar);
            const items = SystemTray.items.values.map(item => ({
                        "id": String(item.id ?? ""),
                        "title": String(item.title ?? ""),
                        "status": Number(item.status ?? 0)
                    }));
            return JSON.stringify({
                "items": items,
                "stored": Array.from(PersonalizationConfig.barTrayPinnedItems),
                "invert": PersonalizationConfig.barTrayInvertPinnedItems,
                "filterPassive": BarWidgetDefaults.option("tray", widget ? widget.widgetEntry : null, "hidePassive"),
                "widget": widget ? {
                    "pinned": Array.from(widget.pinnedItems).map(item => String(item.id)),
                    "unpinned": Array.from(widget.unpinnedItems).map(item => String(item.id)),
                    "pinnedCount": widget.pinnedCount,
                    "unpinnedCount": widget.unpinnedCount,
                    "overflowVisible": widget.overflowVisible,
                    "overflowOpen": widget.trayOverflowOpen
                } : null
            });
        }

        function trayHide(id: string): string {
            const stored = Array.from(PersonalizationConfig.barTrayPinnedItems);
            if (!stored.includes(id))
                stored.push(id);
            PersonalizationConfig.setBarTrayPinnedItems(stored);
            return "OK";
        }

        function trayReset(): string {
            PersonalizationConfig.setBarTrayPinnedItems([]);
            return "OK";
        }

        function trayOpen(value: bool): string {
            const widget = probeRoot.findTrayWidget(barLoader.item);
            if (widget)
                widget.trayOverflowOpen = value;
            return "OK";
        }

        function trayClose(): string {
            const widget = probeRoot.findTrayWidget(barLoader.item);
            if (widget) {
                widget.trayOverflowOpen = true;
                widget.closeOverflowMenu();
                return String(widget.trayOverflowOpen);
            }
            return "NO_WIDGET";
        }

        function reload(): string {
            probeRoot.reloading = true;
            Qt.callLater(function () {
                probeRoot.reloading = false;
            });
            return "OK";
        }

        // B9.7 settled-settings sweep: generic store passthrough (values are
        // JSON-parsed so bools/numbers/arrays arrive typed) plus a duck-typed
        // dump of every wired consumer. D4c: the bar-frame keys became
        // derived views (writable only through the named axis setters), so
        // they route through the writer map before the generic path.
        function b97Set(key: string, value: string): string {
            let parsed = value;
            try {
                parsed = JSON.parse(value);
            } catch (e) {
                parsed = value;
            }
            // D4c: the bar-frame keys are derived views now — only the
            // named axis setters can write them.
            if (key === "barBackplate")
                PersonalizationConfig.setBarBackplate(parsed === true);
            else if (key === "barScreenList")
                PersonalizationConfig.setBarScreenList(Array.isArray(parsed) ? parsed : []);
            else if (key === "barAutoHide")
                PersonalizationConfig.setBarAutoHide(parsed === true);
            else
                PersonalizationConfig.setValue(key, parsed);
            return "OK";
        }

        // D4b: write one axis onto the first live entry of a widget (the
        // per-instance settings path — an equal-to-default value removes
        // the override and collapses the entry back to its id string).
        function d4bSet(widgetId: string, key: string, value: string): string {
            let parsed = value;
            try {
                parsed = JSON.parse(value);
            } catch (e) {
                parsed = value;
            }
            const entry = probeRoot.findWidgetEntry(widgetId);
            if (!entry)
                return "NO_ENTRY";
            PersonalizationConfig.setBarEntryOverride(entry.uid, key, parsed === null ? undefined : parsed);
            return "OK";
        }

        // D4b: the v4 migration on a settled v3 shape — flat [bar] keys and
        // [time].dateFormat fold onto the entries (deviations only), the
        // globals strip, and a second run changes nothing.
        function d4bMigration(): string {
            const legacy = {
                "configVersion": 3,
                "time": {
                    "dateFormat": "ddd, dd/MM"
                },
                "bar": {
                    "configs": [
                        {
                            "id": "default",
                            "name": "Bar",
                            "lanes": {
                                "left": ["launcherButton", "workspaces", "activeWindow", "separator"],
                                "middle": ["island"],
                                "right": ["tray", "quickSettings", "systemMonitor", "systemIcons", "powerButton"]
                            }
                        }
                    ],
                    "showAppIcons": true,
                    "numberStyle": "han",
                    "dividerStyle": "space",
                    "dividerSpacing": 24,
                    "utilButtons": {
                        "showScreenSnip": false
                    },
                    "resources": {
                        "alwaysShowSwap": true
                    },
                    "tray": {
                        "filterPassive": false,
                        "pinnedItems": ["probe:keep"]
                    }
                }
            };
            const seed = {
                "defaults": BarWidgetDefaults.DEFAULTS,
                "barDefaults": BarDefaults.DEFAULTS
            };
            const first = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(legacy)), seed);
            const second = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(first.config)), seed);
            const bar = first.config.bar;
            const left = bar.configs[0].lanes.left;
            const workspaces = left.find(entry => typeof entry === "object" && entry.id === "workspaces") ?? {};
            const separator = left.find(entry => typeof entry === "object" && entry.id === "separator") ?? {};
            const right = bar.configs[0].lanes.right;
            const quickSettings = right.find(entry => typeof entry === "object" && entry.id === "quickSettings") ?? {};
            const tray = right.find(entry => typeof entry === "object" && entry.id === "tray") ?? {};
            // The default bar carries no clock: the dateFormat fold needs a
            // clock entry to prove, so run a second shape with one.
            const clockLegacy = {
                "configVersion": 3,
                "time": {
                    "dateFormat": "ddd, dd/MM"
                },
                "bar": {
                    "configs": [
                        {
                            "id": "default",
                            "name": "Bar",
                            "lanes": {
                                "left": ["clock"],
                                "middle": [],
                                "right": []
                            }
                        }
                    ]
                }
            };
            const clockRun = ConfigMigrations.migrateConfig(clockLegacy, seed);
            const clockEntry = clockRun.config.bar.configs[0].lanes.left[0];
            return JSON.stringify({
                "changed": first.changed,
                "version": first.config.configVersion,
                "workspacesFolded": workspaces.showAppIcons === true && workspaces.numberStyle === "han",
                "workspacesDefaultsSkipped": workspaces.shown === undefined && workspaces.style === undefined,
                "separatorFolded": separator.style === "space" && separator.spacing === 24,
                "utilButtonsFolded": quickSettings.screenSnip === false,
                "systemMonitorFolded": (bar.configs[0].lanes.right.find(entry => typeof entry === "object" && entry.id === "systemMonitor") ?? {}).swap === true,
                "trayFolded": tray.hidePassive === false,
                "trayPinListKept": JSON.stringify(bar.tray.pinnedItems) === JSON.stringify(["probe:keep"]),
                "clockDateFormatFolded": typeof clockEntry === "object" && clockEntry.dateFormat === "ddd, dd/MM",
                "globalsStripped": bar.showAppIcons === undefined && bar.numberStyle === undefined && bar.dividerStyle === undefined && (bar.utilButtons === undefined || bar.utilButtons.showScreenSnip === undefined) && (bar.resources === undefined || bar.resources.alwaysShowSwap === undefined) && (bar.tray === undefined || bar.tray.filterPassive === undefined) && first.config.time?.dateFormat === undefined,
                "idempotent": second.changed === false && JSON.stringify(second.config.bar.configs) === JSON.stringify(bar.configs)
            });
        }

        // D4b: per-instance isolation — two clock entries with different
        // dateFormat overrides resolve independently through option(), and
        // the minimal write only carries the deviating entry.
        function d4bInstances(): string {
            PersonalizationConfig.setBarLaneEntries("left", [
                {
                    "widgetId": "clock",
                    "enabled": true,
                    "overrides": {
                        "dateFormat": "ddd"
                    }
                },
                {
                    "widgetId": "clock",
                    "enabled": true,
                    "overrides": {}
                },
                {
                    "widgetId": "clock",
                    "enabled": true,
                    "overrides": {
                        "dateFormat": "dd/MM"
                    }
                }
            ]);
            PersonalizationConfig.setBarLaneEntries("middle", []);
            PersonalizationConfig.setBarLaneEntries("right", []);
            const lanes = PersonalizationConfig.barLayoutEntriesLeft;
            const first = BarWidgetDefaults.option("clock", lanes[0], "dateFormat");
            const second = BarWidgetDefaults.option("clock", lanes[1], "dateFormat");
            const third = BarWidgetDefaults.option("clock", lanes[2], "dateFormat");
            const sparse = PersonalizationConfig.sparseBarConfigs();
            const serialized = sparse ? sparse[0].lanes.left : [];
            const result = JSON.stringify({
                "firstFormat": first,
                "secondFormat": second,
                "thirdFormat": third,
                "isolated": first === "ddd" && second === "" && third === "dd/MM",
                "sparseLeft": serialized,
                "defaultCollapsedToString": serialized.length === 3 && serialized[1] === "clock"
            });
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            return result;
        }

        // D4b: click-action vocabulary — the preset ids stay closed, the
        // argv shape is enforced (empty arrays and blank parts are refused;
        // no shell-string form exists to test), and an unknown id falls
        // back to the built-in behavior.
        function d4bClickVocabulary(): string {
            const BarWidgetActions = BarPlugin.BarWidgetActions;
            const ids = BarWidgetActions.ids;
            const dispatchUnknown = BarWidgetActions.dispatch("bogus-action", [], "probe");
            const dispatchNone = BarWidgetActions.dispatch("none", [], "probe");
            const dispatchBadCommand = BarWidgetActions.dispatch("command", [], "probe") === false && BarWidgetActions.dispatch("command", [""], "probe") === false && BarWidgetActions.dispatch("command", "gnome-clocks", "probe") === false;
            return JSON.stringify({
                "ids": ids,
                "closed": JSON.stringify(ids) === JSON.stringify(["default", "none", "dashboard", "quicksettings", "launcher", "overview", "power-menu", "lock", "command"]),
                "unknownFallsBack": dispatchUnknown === false,
                "noneConsumes": dispatchNone === true,
                "commandNeedsArgv": dispatchBadCommand,
                "axisForButtons": [BarWidgetActions.axisForButton(Qt.LeftButton), BarWidgetActions.axisForButton(Qt.MiddleButton), BarWidgetActions.axisForButton(Qt.RightButton)]
            });
        }

        // D4c: the v5 migration — flat [bar] globals fold onto the configs
        // entry (deviations only), the per-(mode, widget) widgetStyles fold
        // onto the entries of the ACTIVE borderless mode, both strip, and a
        // second run changes nothing.
        function d4cMigration(): string {
            const legacy = {
                "configVersion": 4,
                "bar": {
                    "configs": [
                        {
                            "id": "default",
                            "name": "Bar",
                            "lanes": {
                                "left": ["launcherButton", "workspaces", "activeWindow"],
                                "middle": ["island"],
                                "right": ["tray", "quickSettings", "systemIcons", "powerButton"]
                            }
                        }
                    ],
                    "position": "bottom",
                    "cornerStyle": 2,
                    "borderless": "segmented",
                    "barThickness": 44,
                    "edgeMargin": 12,
                    "showValues": true,
                    "widgetStyles": [
                        {
                            "mode": "segmented",
                            "widget": "workspaces",
                            "color": "primary",
                            "padding": 9
                        },
                        {
                            "mode": "pills",
                            "widget": "clock",
                            "color": "error"
                        }
                    ],
                    "tray": {
                        "pinnedItems": ["probe:keep"]
                    }
                }
            };
            const seed = {
                "defaults": BarWidgetDefaults.DEFAULTS,
                "barDefaults": BarDefaults.DEFAULTS
            };
            const first = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(legacy)), seed);
            const second = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(first.config)), seed);
            const entry = first.config.bar.configs[0];
            const workspaces = entry.lanes.left.find(e => typeof e === "object" && e.id === "workspaces") ?? {};
            return JSON.stringify({
                "changed": first.changed,
                "version": first.config.configVersion,
                "positionFolded": entry.position === "bottom",
                "cornerStyleFolded": entry.backplate === false && entry.lanePill === undefined && entry.tint === undefined && entry.cornerStyle === undefined,
                "borderlessFolded": entry.widgetStyle === undefined && entry.groupColor === "layer0" && entry.widgetOutlineEnabled === true && entry.borderless === undefined,
                "thicknessFolded": entry.barThickness === 44,
                "edgeMarginFolded": entry.edgeMargin === 12,
                "defaultsSkipped": entry.sideMargin === undefined && entry.autoHide === undefined && entry.capsuleRadius === undefined,
                "activeModeStyleFolded": workspaces.color === "primary" && workspaces.padding === 9,
                "otherModeStyleDropped": JSON.stringify(first.config.bar.configs).indexOf("error") === -1,
                "flatStripped": first.config.bar.position === undefined && first.config.bar.widgetStyles === undefined && first.config.bar.cornerStyle === undefined,
                "trayKept": JSON.stringify(first.config.bar.tray.pinnedItems) === JSON.stringify(["probe:keep"]),
                "idempotent": second.changed === false && JSON.stringify(second.config.bar.configs[0]) === JSON.stringify(entry)
            });
        }

        // D4c: sentinel resolution + the live lane geometry. Baselines come
        // from BarDefaults (per-style), an explicit axis overrides, and the
        // reset returns to the baseline. Fonts scale through BarScale.
        function d4cSentinels(): string {
            const baseline = PersonalizationConfig.resolvedBarSpacing(false);
            PersonalizationConfig.setBarSpacing(0);
            const explicit = PersonalizationConfig.resolvedBarSpacing(false);
            PersonalizationConfig.setBarSpacing(-1);
            const restored = PersonalizationConfig.resolvedBarSpacing(false);
            const baselineInset = PersonalizationConfig.resolvedBarInnerPadding();
            const baselinePadding = PersonalizationConfig.resolvedBarWidgetPadding(false);
            const radiusAuto = PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding);
            PersonalizationConfig.setBarSquareCorners(true);
            const radiusSquare = PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding);
            PersonalizationConfig.setBarRadius(20);
            const radiusOverride = PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding);
            PersonalizationConfig.setBarSquareCorners(false);
            PersonalizationConfig.setBarRadius(-1);
            PersonalizationConfig.setBarFontScale(1.25);
            const scaledFont = PersonalizationConfig.barAxes.fontScale;
            PersonalizationConfig.setBarFontScale(1);
            const resetFont = PersonalizationConfig.barAxes.fontScale;
            return JSON.stringify({
                "baselinePositive": baseline > 0 || baseline < 0,
                "explicitOverrides": explicit === 0,
                "restoredBaseline": restored === baseline,
                "insetBaseline": baselineInset === 4,
                "widgetPaddingBaseline": baselinePadding === 5,
                "radiusAuto": radiusAuto === Appearance.rounding.screenRounding,
                "radiusSquare": radiusSquare === 0,
                "radiusOverride": radiusOverride === 20,
                "fontScaleLive": scaledFont === 1.25 && resetFont === 1
            });
        }

        // D4c: SegmentRoles fusion — hidden widgets re-shape the run,
        // spacer/separator break it, and the live lanes resolve through it.
        function d4cRoles(): string {
            const entries = [
                {
                    widgetId: "a"
                },
                {
                    widgetId: "media"
                },
                {
                    widgetId: "b"
                }
            ];
            const allShown = SegmentRoles.resolve(entries, [true, true, true]);
            const lastHidden = SegmentRoles.resolve(entries, [true, false, true]);
            const broken = SegmentRoles.resolve([
                {
                    widgetId: "a"
                },
                {
                    widgetId: "spacer"
                },
                {
                    widgetId: "b"
                }
            ], [true, true, true]);
            const content = barLoader.item;
            return JSON.stringify({
                "runFused": JSON.stringify(allShown) === JSON.stringify(["first", "middle", "last"]),
                "hiddenReShapes": JSON.stringify(lastHidden) === JSON.stringify(["solo", "solo", "solo"]),
                "spacerBreaks": JSON.stringify(broken) === JSON.stringify(["solo", "solo", "solo"]),
                "liveRoles": content ? {
                    "left": content.leftSegmentRoles,
                    "right": content.rightSegmentRoles
                } : null
            });
        }

        // D4d: behavior axes round-trip through the named setters — every
        // default preserves the pre-D4d behavior and the sparse writer only
        // persists deviations.
        function d4dBehavior(): string {
            const before = PersonalizationConfig.barAxes;
            PersonalizationConfig.setBarAutoHideDelay(300);
            PersonalizationConfig.setBarAutoHideStrict(true);
            PersonalizationConfig.setBarHideOnFullscreen(true);
            PersonalizationConfig.setBarClickThrough(true);
            PersonalizationConfig.setBarHoverPopoutDelay(250);
            const axes = PersonalizationConfig.barAxes;
            const sparse = JSON.stringify(PersonalizationConfig.sparseBarConfigs());
            PersonalizationConfig.setBarAutoHideDelay(0);
            PersonalizationConfig.setBarAutoHideStrict(false);
            PersonalizationConfig.setBarHideOnFullscreen(false);
            PersonalizationConfig.setBarClickThrough(false);
            PersonalizationConfig.setBarHoverPopoutDelay(150);
            const after = PersonalizationConfig.barAxes;
            return JSON.stringify({
                "defaultsPreserved": before.autoHideDelay === 0 && before.autoHideStrict === false && before.hideOnFullscreen === false && before.clickThrough === false && before.hoverPopouts === true && before.hoverPopoutDelay === 150,
                "delayLive": axes.autoHideDelay === 300,
                "strictLive": axes.autoHideStrict === true,
                "fullscreenLive": axes.hideOnFullscreen === true,
                "clickThroughLive": axes.clickThrough === true,
                "hoverDelayLive": axes.hoverPopoutDelay === 250,
                "sparseDeviationsOnly": sparse.indexOf("autoHideDelay") !== -1 && sparse.indexOf("hoverPopouts") === -1,
                "reset": after.autoHideDelay === 0 && after.autoHideStrict === false && after.hideOnFullscreen === false && after.clickThrough === false && after.hoverPopoutDelay === 150
            });
        }

        // D4d: the forked dux resolver, unit-run against hand-computed
        // expectations (placement vocabulary, priority yield, flexible
        // shrink, pinned/always semantics, hysteresis restore).
        function d4dOverflowResolve(): string {
            const placementPinned = OverflowLayout.placement({
                widgetId: "island"
            });
            const placementSection = OverflowLayout.placement({
                widgetId: "clock",
                overflowMode: "section"
            }, "bar");
            const placementAuto = OverflowLayout.placement({
                widgetId: "clock"
            }, "auto");
            const placementAlways = OverflowLayout.placement({
                widgetId: "clock",
                overflowMode: "always"
            });
            const sections = {
                left: [
                    {
                        size: 100,
                        min: 100,
                        mode: "bar",
                        priority: 0
                    },
                    {
                        size: 200,
                        min: 100,
                        mode: "auto",
                        priority: -5
                    },
                    {
                        size: 120,
                        min: 120,
                        mode: "auto",
                        priority: 5
                    }
                ],
                center: [
                    {
                        size: 80,
                        min: 80,
                        mode: "auto",
                        priority: 0
                    }
                ],
                right: [
                    {
                        size: 90,
                        min: 90,
                        mode: "always",
                        priority: 0
                    },
                    {
                        size: 70,
                        min: 70,
                        mode: "auto",
                        priority: 0
                    }
                ]
            };
            const options = {
                length: 400,
                start: 0,
                end: 0,
                spacing: 4,
                triggerSize: 28,
                positions: {
                    left: 3,
                    center: 1,
                    right: 0
                },
                restoreMargin: 4
            };
            const cramped = OverflowLayout.resolve(JSON.parse(JSON.stringify(sections)), options);
            const roomy = OverflowLayout.resolve(JSON.parse(JSON.stringify(sections)), Object.assign({}, options, {
                length: 2000
            }), cramped.hidden);
            return JSON.stringify({
                "pinnedStays": placementPinned === "bar" && placementSection === "bar",
                "autoDefault": placementAuto === "auto",
                "alwaysVocabulary": placementAlways === "always",
                "priorityFallback": OverflowLayout.priority({}) === 0 && OverflowLayout.priority({
                    overflowPriority: 3
                }) === 3,
                "alwaysHidden": cramped.hidden.right.indexOf(0) !== -1,
                "barNeverHides": cramped.hidden.left.indexOf(0) === -1,
                // The LOWER priority value yields (hides) first; at this
                // crush the -5 entry is guaranteed hidden (the +5 may join
                // it — membership order is unobservable, hidden sorts).
                "lowPriorityYieldsFirst": cramped.hidden.left.indexOf(1) !== -1,
                "hysteresisRestores": roomy.hidden.left.length === 0 && roomy.hidden.center.length === 0,
                "alwaysStaysHidden": roomy.hidden.right.indexOf(0) !== -1
            });
        }

        // D4d: the live engine on the staged content — shrink the stage so
        // the lanes cannot fit, then dump the resolver output and cycle the
        // lane overflow popup (relocation in both directions). Separate IPC
        // calls on purpose: the resolver debounces on a 1ms timer.
        function d4dOverflowScene(width: int, height: int): string {
            stage.width = width;
            stage.height = height;
            return "SCENE";
        }

        function d4dOverflowDump(): string {
            const content = barLoader.item;
            if (!content)
                return JSON.stringify({
                    "ready": false
                });
            const hiddenIds = content.overflowHiddenIds;
            // The active branch's host only: both branch hosts share the
            // hidden groups, and the inactive one's own `visible` stays
            // true (its parent row hides instead).
            const host = probeRoot.findNodes(content, child => child.overflowGroups !== undefined && typeof child.toggle === "function" && child.visible && child.parent && child.parent.visible && child.overflowGroups.length > 0, [])[0] ?? null;
            let popupCycle = null;
            if (host && host.overflowGroups.length > 0) {
                const group = host.overflowGroups[0];
                const homeParent = group.widgetLoader ? group.widgetLoader.parent : null;
                host.toggle();
                const relocatedParent = group.widgetLoader ? group.widgetLoader.parent : null;
                const opened = host.open && relocatedParent !== null && relocatedParent !== homeParent;
                host.toggle();
                const restoredParent = group.widgetLoader ? group.widgetLoader.parent : null;
                const closed = !host.open && restoredParent !== null && restoredParent === homeParent;
                popupCycle = {
                    "relocated": opened,
                    "restored": closed,
                    "debug": {
                        "hostOpen": host.open,
                        "loader": group.widgetLoader !== null,
                        "home": homeParent ? homeParent.toString().slice(0, 40) : null,
                        "relocated": relocatedParent ? relocatedParent.toString().slice(0, 40) : null
                    }
                };
            }
            return JSON.stringify({
                "ready": true,
                "hiddenIds": hiddenIds,
                "buttonFound": host !== null,
                "popupCycle": popupCycle
            });
        }

        function d4dOverflowReset(): string {
            stage.width = Qt.binding(() => probeRoot.probeWidth);
            stage.height = Qt.binding(() => probeRoot.probeHeight);
            return "RESET";
        }

        // D4e e1: multi-bar storage. Self-contained (resets to the factory
        // bar first, restores at the end): a second entry survives with a
        // generated id, its default lanes carry no island (the shared
        // singleton bucket), uids stay unique across bars, per-id mutations
        // stay isolated (selection routes the setters), the sparse section
        // carries every entry while multi (a pristine sibling persists as
        // its id — dropping it would delete that bar), sparse -> normalize
        // round-trips, the island cannot be re-added from a foreign editor,
        // and delete protects the factory entry and the last bar.
        function d4eStore(): string {
            PersonalizationConfig.selectedBarId = "";
            PersonalizationConfig.barConfigs.map(config => config.id).filter(id => id !== "default").forEach(id => PersonalizationConfig.deleteBarConfig(id));
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            const singleSparse = PersonalizationConfig.sparseBarConfigs();
            const secondId = PersonalizationConfig.addBarConfig();
            const twoCount = PersonalizationConfig.barConfigs.length;
            const second = PersonalizationConfig.barConfigs[1];
            const secondMiddle = second.lanes.middle.map(entry => entry.widgetId);
            const islandOwners = PersonalizationConfig.barConfigs.filter(config => ["left", "middle", "right"].some(zone => config.lanes[zone].some(entry => entry.widgetId === "island"))).map(config => config.id);
            const uids = [];
            PersonalizationConfig.barConfigs.forEach(config => ["left", "middle", "right"].forEach(zone => config.lanes[zone].forEach(entry => uids.push(entry.uid))));
            const uniqueUids = uids.filter((uid, index) => uids.indexOf(uid) === index);
            // Route the editor to bar 2: entry + override + a position flip
            // land on bar 2 only.
            PersonalizationConfig.selectedBarId = secondId;
            PersonalizationConfig.addBarEntry("right", "clock");
            const clockUid = PersonalizationConfig.barLayoutEntriesRight.find(entry => entry.widgetId === "clock").uid;
            PersonalizationConfig.setBarEntryOverride(clockUid, "dateFormat", "ddd");
            PersonalizationConfig.setBarPosition("left");
            const islandBlockedMove = PersonalizationConfig.moveBarComponent("island", "left", 0) === false;
            const islandBlockedAdd = PersonalizationConfig.addBarEntry("left", "island") === false;
            const sparseTwo = PersonalizationConfig.sparseBarConfigs();
            const roundTrip = PersonalizationConfig.normalizeBarConfigs(sparseTwo);
            // Back on bar 1 the views show the untouched factory state.
            PersonalizationConfig.selectedBarId = "default";
            const defaultRight = PersonalizationConfig.barLayoutEntriesRight.map(entry => entry.widgetId);
            const defaultPosition = String(PersonalizationConfig.barPosition);
            const refusedDefault = PersonalizationConfig.deleteBarConfig("default") === false;
            PersonalizationConfig.deleteBarConfig(secondId);
            const backToOne = PersonalizationConfig.barConfigs.length === 1;
            const refusedLast = PersonalizationConfig.deleteBarConfig("default") === false;
            const result = JSON.stringify({
                "singleNull": singleSparse === null,
                "secondId": secondId,
                "twoCount": twoCount,
                "secondMiddle": secondMiddle,
                "islandOwners": islandOwners,
                "uidUnique": uids.length === uniqueUids.length,
                "sparseIds": sparseTwo.map(entry => entry.id),
                "bar1PristineIdentity": JSON.stringify(sparseTwo[0]) === JSON.stringify({
                    "id": "default"
                }),
                "bar2HasPosition": sparseTwo[1].position === "left",
                "bar2HasClockOverride": JSON.stringify(sparseTwo[1].lanes.right).indexOf("dateFormat") !== -1,
                "roundTripIds": roundTrip.map(config => config.id),
                "roundTripIslandOwners": roundTrip.filter(config => ["left", "middle", "right"].some(zone => config.lanes[zone].some(entry => entry.widgetId === "island"))).map(config => config.id),
                "islandBlockedMove": islandBlockedMove,
                "islandBlockedAdd": islandBlockedAdd,
                "defaultRightUntouched": JSON.stringify(defaultRight) === JSON.stringify(PersonalizationConfig.defaultBarLayoutRight),
                "defaultPositionUntouched": defaultPosition === "top",
                "refusedDefault": refusedDefault,
                "backToOne": backToOne,
                "refusedLast": refusedLast
            });
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            return result;
        }

        // D4e e5: v5 -> v6 migration folds non-default [island] widget
        // appearance axes onto the singleton "island" lane entry, preserves
        // [island.horizontalClock], strips legacy island keys + layoutMigrated,
        // deletes emptied [island], and stays idempotent on repeat runs.
        function d4eMigrationV6(): string {
            const legacy = {
                "configVersion": 5,
                "bar": {
                    "configs": [
                        {
                            "id": "default",
                            "lanes": {
                                "left": ["workspaces"],
                                "middle": ["island"],
                                "right": ["clock"]
                            }
                        }
                    ]
                },
                "island": {
                    "satellite": "weather",
                    "showAvatar": false,
                    "visualizerStyle": "dots",
                    "hideDate": true,
                    "layoutMigrated": true,
                    "horizontalClock": {
                        "hourFormat": "hh"
                    }
                }
            };
            const seed = {
                "defaults": BarWidgetDefaults.DEFAULTS,
                "barDefaults": BarDefaults.DEFAULTS
            };
            const first = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(legacy)), seed);
            const second = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(first.config)), seed);
            const entry = first.config.bar.configs[0].lanes.middle[0] ?? {};
            const strippedLegacy = Object.assign({}, legacy);
            delete strippedLegacy.island.horizontalClock;
            const emptiedRun = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(strippedLegacy)), seed);
            return JSON.stringify({
                "changed": first.changed,
                "version": first.config.configVersion,
                "foldedOnEntry": entry.id === "island" && entry.satellite === "weather" && entry.showAvatar === false && entry.hideDate === true,
                "defaultsSkipped": entry.visualizerStyle === undefined,
                "clockKept": Boolean(first.config.island && first.config.island.horizontalClock && first.config.island.horizontalClock.hourFormat === "hh"),
                "flatStripped": Boolean(first.config.island && first.config.island.satellite === undefined && first.config.island.showAvatar === undefined && first.config.island.hideDate === undefined && first.config.island.layoutMigrated === undefined),
                "emptyIslandDeleted": emptiedRun.config.island === undefined,
                "idempotent": second.changed === false && JSON.stringify(second.config) === JSON.stringify(first.config)
            });
        }

        // D4f: atomic bar style axes, write-only starter presets, v7 migration,
        // D-8 retired bonuses, capsule radius, and transparent group chrome.
        function d4fStyle(): string {
            const legacy = {
                "configVersion": 6,
                "bar": {
                    "cornerStyle": 1,
                    "configs": [
                        {
                            "id": "default",
                            "position": "bottom",
                            "cornerStyle": 3,
                            "borderless": "transparent",
                            "showBackground": false
                        }
                    ]
                }
            };
            const seed = {
                "defaults": BarWidgetDefaults.DEFAULTS,
                "barDefaults": BarDefaults.DEFAULTS
            };
            const first = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(legacy)), seed);
            const second = ConfigMigrations.migrateConfig(JSON.parse(JSON.stringify(first.config)), seed);
            const migratedEntry = first.config.bar.configs[0];
            const v7Migrated = first.changed === true && first.config.configVersion === 7 && migratedEntry.backplate === false && migratedEntry.lanePill === true && migratedEntry.tint === true && migratedEntry.edgeMargin === undefined && migratedEntry.widgetStyle === undefined && migratedEntry.groupColor === "transparent" && migratedEntry.widgetOutlineEnabled === undefined && migratedEntry.cornerStyle === undefined && migratedEntry.borderless === undefined && migratedEntry.showBackground === undefined && migratedEntry.position === "bottom" && first.config.bar.cornerStyle === undefined && second.changed === false;

            PersonalizationConfig.applyBarStylePreset("islands");
            const islandsPreset = BarStylePresets.currentPreset(PersonalizationConfig.barAxes);
            const islandsAxes = PersonalizationConfig.barAxes.backplate === false && PersonalizationConfig.barAxes.lanePill === false && PersonalizationConfig.barAxes.edgeMargin === 0;
            PersonalizationConfig.setBarTint(true);
            const customAfterTweak = BarStylePresets.currentPreset(PersonalizationConfig.barAxes) === "";
            PersonalizationConfig.setBarCapsuleRadius("rounded");
            PersonalizationConfig.setBarGroupColor("transparent");
            const roundedAxis = PersonalizationConfig.barAxes.capsuleRadius === "rounded" && PersonalizationConfig.barAxes.groupColor === "transparent";
            PersonalizationConfig.applyBarStylePreset("floating");

            const d8BonusesRetired = BarDefaults.styleBoost(BarDefaults.deriveStyle({
                backplate: false,
                lanePill: true,
                tint: false,
                edgeMargin: 0
            }, 5)) === 4 && BarDefaults.styleBoost(BarDefaults.deriveStyle({
                backplate: false,
                lanePill: false,
                tint: false,
                edgeMargin: 5
            }, 5)) === 0 && BarDefaults.styleBoost(BarDefaults.deriveStyle({
                backplate: true,
                lanePill: false,
                tint: false,
                edgeMargin: 0,
                squareCorners: true
            }, 5)) === 0 && BarGeometry.exclusiveZone(false, 40, 44, 0, 5) === 45;

            const radiusVocabulary = BarDefaults.capsuleFullRadius({
                capsuleRadius: "pill"
            }, 26, 8, 12) === 13 && BarDefaults.capsuleFullRadius({
                capsuleRadius: "rounded"
            }, 26, 8, 12) === 8 && BarDefaults.capsuleFullRadius({
                capsuleRadius: "px"
            }, 26, 8, 12) === 12 && BarDefaults.GROUP_COLORS.indexOf("transparent") !== -1;

            return JSON.stringify({
                "v7Migrated": v7Migrated,
                "presetCount": BarStylePresets.ORDER.length,
                "islandsPreset": islandsPreset === "islands" && islandsAxes,
                "customAfterTweak": customAfterTweak,
                "roundedAndTransparent": roundedAxis,
                "d8BonusesRetired": d8BonusesRetired,
                "radiusVocabulary": radiusVocabulary,
                "restoredFloating": BarStylePresets.currentPreset(PersonalizationConfig.barAxes) === "floating"
            });
        }

        // D4g batch three: the rail face is the compact pill growing along
        // the track — every widget id is rail-capable now (clock and
        // systemMonitor always had B9.4-era rail faces; the roadmap claim
        // was wrong and 批二 pinned it, so this verdict corrects it).
        function d4gCatalog(): string {
            const ids = BarWidgetDefaults.IDS;
            const rows = {};
            let capable = 0;
            for (let i = 0; i < ids.length; i += 1) {
                const id = ids[i];
                const supported = catalogProbe.supportsVertical(id);
                if (supported)
                    capable += 1;
                rows[id] = {
                    "vertical": supported,
                    "mode": catalogProbe.verticalMode(id)
                };
            }
            return JSON.stringify({
                "count": ids.length,
                "capable": capable,
                "modes": catalogProbe.verticalModes,
                "rows": rows,
                "vocabularyClosed": catalogProbe.verticalModes.join(",") === "stack,rotate,iconPopup",
                "auditVerdict": catalogProbe.supportsVertical("clock") && catalogProbe.supportsVertical("island") && catalogProbe.supportsVertical("systemMonitor") && catalogProbe.verticalMode("battery") === "rotate" && catalogProbe.verticalMode("tray") === "stack" && catalogProbe.verticalMode("activeWindow") === "iconPopup" && catalogProbe.verticalMode("media") === "iconPopup"
            });
        }

        // D4e e2 + e6: the window host topology and per-bar thickness/scales
        // (window mode). Scene "two" adds a second bottom bar with clock-only
        // lanes plus custom thickness (50), fontScale (1.1), iconScale (1.25).
        // Scene "off" disables the second entry (windows drop to zero).
        // Scene "clean" restores the factory single bar.
        function d4eWindowsSet(scene: string): string {
            PersonalizationConfig.selectedBarId = "";
            PersonalizationConfig.barConfigs.map(config => config.id).filter(id => id !== "default").forEach(id => PersonalizationConfig.deleteBarConfig(id));
            if (scene === "two" || scene === "off") {
                const secondId = PersonalizationConfig.addBarConfig();
                PersonalizationConfig.selectedBarId = secondId;
                PersonalizationConfig.setBarPosition("bottom");
                PersonalizationConfig.setBarThickness(50);
                PersonalizationConfig.setBarFontScale(1.1);
                PersonalizationConfig.setBarIconScale(1.25);
                PersonalizationConfig.setBarLayouts(["clock"], [], []);
                if (scene === "off")
                    PersonalizationConfig.setBarEnabled(secondId, false);
            }
            return "OK";
        }

        function d4eWindowsDump(): string {
            const barScope = windowLoader.item;
            const report = barScope && barScope.probeHostReport ? JSON.parse(barScope.probeHostReport()) : [];
            const first = barScope && barScope.probeHostWindow ? barScope.probeHostWindow("default") : null;
            const second = barScope && barScope.probeHostWindow ? barScope.probeHostWindow("bar2") : null;
            const content = second ? second.barContent : null;
            return JSON.stringify({
                "hosts": report,
                "firstHeight": first ? Math.round(first.height) : 0,
                "firstFontScale": first && first.barConfig ? first.barConfig.axes.fontScale : 0,
                "firstIconScale": first && first.barConfig ? first.barConfig.axes.iconScale : 0,
                "secondEdge": second ? String(second.edge) : "",
                "secondHeight": second ? Math.round(second.height) : 0,
                "secondFontScale": second && second.barConfig ? second.barConfig.axes.fontScale : 0,
                "secondIconScale": second && second.barConfig ? second.barConfig.axes.iconScale : 0,
                "secondLeftIds": content ? content.effectiveLeftLayout.map(entry => entry.widgetId) : [],
                "secondRightIds": content ? content.effectiveRightLayout.map(entry => entry.widgetId) : []
            });
        }

        // D4e e1: the rebuild signature moves ONLY on routing changes — a
        // style axis edit keeps it byte-identical, a position flip and an
        // enable toggle move it.
        function d4eSignature(): string {
            PersonalizationConfig.selectedBarId = "";
            PersonalizationConfig.barConfigs.map(config => config.id).filter(id => id !== "default").forEach(id => PersonalizationConfig.deleteBarConfig(id));
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            const secondId = PersonalizationConfig.addBarConfig();
            PersonalizationConfig.selectedBarId = secondId;
            const base = PersonalizationConfig.barLayoutStateJson();
            PersonalizationConfig.setBarThickness(40);
            const afterStyle = PersonalizationConfig.barLayoutStateJson();
            PersonalizationConfig.setBarPosition("bottom");
            const afterPosition = PersonalizationConfig.barLayoutStateJson();
            PersonalizationConfig.setBarEnabled(secondId, false);
            const afterDisable = PersonalizationConfig.barLayoutStateJson();
            const result = JSON.stringify({
                "styleStable": afterStyle === base,
                "positionMoved": afterPosition !== base,
                "disableMoved": afterDisable !== afterPosition,
                "twoEntries": JSON.parse(base).length === 2
            });
            PersonalizationConfig.setBarEnabled(secondId, true);
            PersonalizationConfig.deleteBarConfig(secondId);
            PersonalizationConfig.setBarLayouts(PersonalizationConfig.defaultBarLayoutLeft.slice(), PersonalizationConfig.defaultBarLayoutMiddle.slice(), PersonalizationConfig.defaultBarLayoutRight.slice());
            PersonalizationConfig.selectedBarId = "";
            return result;
        }

        function b97Dump(): string {
            const content = barLoader.item;
            if (!content)
                return JSON.stringify({
                    "ready": false
                });
            const backgrounds = probeRoot.findNodes(content, node => node.objectName === "barBackground", []);
            const divisors = probeRoot.findNodes(content, node => node.dividerSpacing !== undefined, []);
            const layer0 = String(Appearance.colors.colLayer0);
            // B9.7 number presets: only the Workspaces subtree speaks the
            // preset labels — the island clock can render its own digits.
            const wsNode = probeRoot.findWorkspace(content);
            const wsTexts = probeRoot.findNodes(wsNode, node => typeof node.text === "string" && node.font !== undefined, []);
            const wsHan = [];
            const wsRoman = [];
            for (const node of wsTexts) {
                const label = String(node.text);
                if (/^[一二三四五六七八九十]{1,3}$/.test(label)) {
                    if (!wsHan.includes(label))
                        wsHan.push(label);
                } else if (/^[IVXLC]{1,6}$/.test(label) && label !== "" && !/^\d+$/.test(label)) {
                    if (!wsRoman.includes(label))
                        wsRoman.push(label);
                }
            }
            const resources = probeRoot.findNodes(content, node => node.iconName !== undefined && node.shown !== undefined, []);
            const buttons = probeRoot.findNodes(content, node => node.toolTipText !== undefined, []);
            const buttonIcons = probeRoot.findNodes(content, node => node.iconText !== undefined, []);
            return JSON.stringify({
                "ready": true,
                "preset": BarStylePresets.currentPreset(PersonalizationConfig.barAxes),
                "colLayer0": layer0,
                "bridge": {
                    "backplate": PersonalizationConfig.barBackplate,
                    "autoHide": Config.options.bar.autoHide.enable,
                    "screenList": Array.from(Config.options.bar.screenList ?? []),
                    // D4b: the migrated per-widget axes read through the
                    // entry chain (option()), never the retired flat keys.
                    "dividerStyle": String(BarWidgetDefaults.option("separator", probeRoot.findWidgetEntry("separator"), "style")),
                    "dividerSpacing": BarWidgetDefaults.option("separator", probeRoot.findWidgetEntry("separator"), "spacing"),
                    "utilKeyboard": BarWidgetDefaults.option("utilButtons", probeRoot.findWidgetEntry("utilButtons") || probeRoot.findWidgetEntry("quickSettings"), "keyboardToggle"),
                    "resourceSwap": BarWidgetDefaults.option("systemMonitor", probeRoot.findWidgetEntry("systemMonitor"), "swap"),
                    "resourceStyle": String(BarWidgetDefaults.option("systemMonitor", probeRoot.findWidgetEntry("systemMonitor"), "iconStyle")),
                    "numberStyle": BarWidgetDefaults.option("workspaces", probeRoot.findWidgetEntry("workspaces"), "numberStyle"),
                    "numberMap": Array.from(BarWidgetDefaults.workspaceNumberMap(BarWidgetDefaults.option("workspaces", probeRoot.findWidgetEntry("workspaces"), "numberStyle"))),
                    "trayFilterPassive": BarWidgetDefaults.option("tray", probeRoot.findWidgetEntry("tray"), "hidePassive")
                },
                "background": backgrounds.length ? {
                    "color": String(backgrounds[0].color),
                    "isLayer0": Qt.color(String(backgrounds[0].color)).rgba === Qt.color(String(Appearance.colors.colLayer0)).rgba
                } : null,
                "divisor": divisors.length ? {
                    "spacing": divisors[0].dividerSpacing,
                    "style": String(divisors[0].style),
                    "width": Math.round(divisors[0].width),
                    "height": Math.round(divisors[0].height)
                } : null,
                "resourceNodes": resources.map(node => ({
                            "icon": String(node.iconName),
                            "shown": node.shown === true,
                            "visible": node.visible !== false
                        })),
                "swapNodes": resources.filter(node => String(node.iconName) === "swap_horiz").map(node => ({
                            "shown": node.shown === true,
                            "visible": node.visible !== false
                        })),
                "buttonIcons": buttonIcons.map(node => String(node.iconText)),
                "buttons": buttons.map(node => String(node.toolTipText)),
                "han": wsHan,
                "roman": wsRoman
            });
        }
    }
}
