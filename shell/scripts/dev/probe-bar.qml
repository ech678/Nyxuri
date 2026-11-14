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

ShellRoot {
    id: probeRoot

    property int probeWidth: 2560
    property real probeHeight: Appearance.sizes.barHeight
    readonly property string probeShell: String(Quickshell.env("NYXURI_PROBE_SHELL") || "")
    property bool reloading: false

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
            active: PersonalizationConfig.ready && !probeRoot.reloading
            source: probeRoot.probeShell !== "" ? "file://" + probeRoot.probeShell + "/plugins/bar/BarContent.qml" : ""
        }
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
            if (child.status !== undefined && child.source !== undefined && child.active === true) {
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
        const geometry = {
            "width": barContent.width,
            "height": barContent.height,
            "centerX": barContent.laneCenterX,
            "centerWidth": barContent.laneCenterWidth,
            "leftWidth": barContent.laneLeftWidth,
            "rightWidth": barContent.laneRightWidth,
            "centerPillX": barContent.centerPillX,
            "centerPillWidth": barContent.centerPillWidth
        };
        const values = [geometry.width, geometry.height, geometry.centerX, geometry.centerWidth];
        const finite = values.every(value => typeof value === "number" && isFinite(value));
        const centered = !barContent.effectiveMiddleLayout || barContent.effectiveMiddleLayout.length === 0 || Math.abs(geometry.centerX - (geometry.width - geometry.centerWidth) / 2) <= 1;
        return JSON.stringify({
            "ready": barLoader.status === Loader.Ready,
            "cornerStyle": PersonalizationConfig.barCornerStyle,
            "borderless": PersonalizationConfig.barBorderless,
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

        // Layout scenes: "mediaOnly" is the self-hiding-widget contract (an
        // empty lane must collapse to zero instead of keeping capsule
        // padding); "default" restores the shipped three-lane layout.
        function scene(name: string): string {
            if (name === "mediaOnly") {
                PersonalizationConfig.setBarLayouts(["media"], [], []);
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

        function osd(kind: string): string {
            GlobalStates.osdKind = kind;
            return "OK";
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

        function idleFace(): string {
            const face = probeRoot.findIdleFace(barLoader.item);
            const host = ActionGateway.islandHost;
            return JSON.stringify({
                "found": face !== null,
                "islandState": host ? String(host.invoke("state")) : "UNAVAILABLE",
                "idleWidth": host ? host.idleWidth : null,
                "idleTextContentWidth": host ? host.idleTextContentWidth : null,
                "satellite": PersonalizationConfig.islandSatellite,
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
    }
}
