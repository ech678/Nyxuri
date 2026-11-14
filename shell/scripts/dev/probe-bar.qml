// Runtime probe harness for scripts/dev/probe-bar.sh (B8.6).
// The script copies shell/ to a temp dir and installs this file as shell.qml,
// so the bar loads in isolation (no ledger, no panel window) and answers over
// the bar-probe IPC target. Keep the top-level imports: they synthesize the
// qs.* qmldirs that Loader-loaded bar files resolve (loader-form.md).
import QtQuick
import Quickshell
import Quickshell.Io
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
                "visible": host.visible
            };
        }
        const geometry = {
            "width": barContent.width,
            "height": barContent.height,
            "centerX": barContent.laneCenterX,
            "centerWidth": barContent.laneCenterWidth,
            "centerPillX": barContent.centerPillX,
            "centerPillWidth": barContent.centerPillWidth
        };
        const values = [geometry.width, geometry.height, geometry.centerX, geometry.centerWidth];
        const finite = values.every(value => typeof value === "number" && isFinite(value));
        const centered = !barContent.effectiveMiddleLayout || barContent.effectiveMiddleLayout.length === 0 || Math.abs(geometry.centerX - (geometry.width - geometry.centerWidth) / 2) <= 1;
        return JSON.stringify({
            "ready": barLoader.status === Loader.Ready,
            "cornerStyle": PersonalizationConfig.barCornerStyle,
            "lanes": {
                "left": Array.from(barContent.effectiveLeftLayout || []),
                "middle": Array.from(barContent.effectiveMiddleLayout || []),
                "right": Array.from(barContent.effectiveRightLayout || [])
            },
            "geometry": geometry,
            "island": island,
            "keyboard": {
                "available": KeyboardLockService.available,
                "caps": KeyboardLockService.capsLock,
                "num": KeyboardLockService.numLock
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

        function osd(kind: string): string {
            GlobalStates.osdKind = kind;
            return "OK";
        }

        function keyboardFlip(): string {
            KeyboardLockService.capsLock = !KeyboardLockService.capsLock;
            KeyboardLockService.lockStateChanged();
            return String(KeyboardLockService.capsLock);
        }

        function islandEnabled(value: bool): string {
            PersonalizationConfig.setIslandEnabled(value);
            return "OK";
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
