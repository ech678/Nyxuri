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
            // PersonalizationConfig and a later cornerStyle flip would leave
            // layout sizes stale in a windowless harness.
            active: !probeRoot.windowMode && PersonalizationConfig.ready && !probeRoot.reloading
            source: probeRoot.probeShell !== "" ? "file://" + probeRoot.probeShell + "/plugins/bar/" + (probeRoot.probeVertical ? "VerticalBarContent.qml" : "BarContent.qml") : ""
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
                "critical": slot.critical === true
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
            "cornerStyle": PersonalizationConfig.barCornerStyle,
            "borderless": PersonalizationConfig.barBorderless,
            "vertical": vertical,
            "edge": PersonalizationConfig.barPosition,
            "lanes": {
                "left": Array.from(barContent.effectiveLeftLayout || []),
                "middle": Array.from(barContent.effectiveMiddleLayout || []),
                "right": Array.from(barContent.effectiveRightLayout || [])
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

        function cornerStyle(value: int): string {
            PersonalizationConfig.setBarCornerStyle(value);
            return String(PersonalizationConfig.barCornerStyle);
        }

        function borderless(value: string): string {
            PersonalizationConfig.setBarBorderless(value);
            return String(PersonalizationConfig.barBorderless);
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
            for (const edge of ["top", "bottom", "left", "right"]) {
                const vertical = edge === "left" || edge === "right";
                for (const tier of [0, 12, 24]) {
                    cases.push({
                        "edge": edge,
                        "vertical": vertical,
                        "tier": tier,
                        "box": BarGeometry.margins(edge, vertical, tier, tier, 0, false, false),
                        "exclusiveZone": BarGeometry.exclusiveZone(vertical, Appearance.sizes.baseBarHeight, Appearance.sizes.baseVerticalBarWidth, PersonalizationConfig.barCornerStyle, 5, tier)
                    });
                }
            }
            return JSON.stringify({
                "baseBarHeight": Appearance.sizes.baseBarHeight,
                "baseVerticalBarWidth": Appearance.sizes.baseVerticalBarWidth,
                "verticalBarWidth": Appearance.sizes.verticalBarWidth,
                "cornerStyle": PersonalizationConfig.barCornerStyle,
                "cases": cases
            });
        }

        function osd(kind: string): string {
            GlobalStates.osdKind = kind;
            return "OK";
        }

        // B9.6: right-click style editor chain end-to-end. The write goes
        // through the same store setter the popup uses; the dump reads the
        // BarGroup binding and the bound widget property.
        function b96Style(on: bool): string {
            if (on)
                PersonalizationConfig.setBarWidgetStyle("pills", "workspaces", "color", "primary");
            else
                PersonalizationConfig.resetBarWidgetStyle("pills", "workspaces");
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
                "cornerStyle": PersonalizationConfig.barCornerStyle,
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
                "avatarFallback": face ? face.probeAvatarFallback : false
            });
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
                "filterPassive": PersonalizationConfig.barTrayFilterPassive,
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
        // dump of every wired consumer.
        function b97Set(key: string, value: string): string {
            let parsed = value;
            try {
                parsed = JSON.parse(value);
            } catch (e) {
                parsed = value;
            }
            PersonalizationConfig.setValue(key, parsed);
            return "OK";
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
                "cornerStyle": PersonalizationConfig.barCornerStyle,
                "colLayer0": layer0,
                "bridge": {
                    "showBackground": Config.options.bar.m3.showBackground,
                    "autoHide": Config.options.bar.autoHide.enable,
                    "screenList": Array.from(Config.options.bar.screenList ?? []),
                    "dividerStyle": String(Config.options.bar.m3.divider.style),
                    "dividerSpacing": Config.options.bar.m3.divider.spacing,
                    "utilKeyboard": Config.options.bar.m3.utilButtons.showKeyboardToggle,
                    "resourceSwap": Config.options.bar.m3.resources.alwaysShowSwap,
                    "resourceStyle": String(Config.options.bar.m3.resources.style),
                    "numberStyle": PersonalizationConfig.barWorkspaceNumberStyle,
                    "numberMap": Array.from(Config.options.bar.m3.workspaces.numberMap ?? [])
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
