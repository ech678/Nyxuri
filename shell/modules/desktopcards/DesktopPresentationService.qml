pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    // One fixed, output-local presentation coordinate space per output.
    // Values are QQuickItems owned by DesktopCardHost; cloning the map makes
    // host registration observable without taking ownership of those items.
    property var hosts: ({})

    function registerHost(screenName, item) {
        const name = String(screenName || "");
        if (name === "" || !item)
            return false;
        const next = Object.assign({}, root.hosts);
        next[name] = item;
        root.hosts = next;
        return true;
    }

    function unregisterHost(screenName, item) {
        const name = String(screenName || "");
        if (name === "" || root.hosts[name] !== item)
            return false;
        const next = Object.assign({}, root.hosts);
        delete next[name];
        root.hosts = next;
        return true;
    }

    function hostFor(screenName) {
        return root.hosts[String(screenName || "")] || null;
    }

    function geometry(screenName) {
        const host = root.hostFor(screenName);
        if (!host || host.width <= 1 || host.height <= 1)
            return null;
        return {
            width: Number(host.width),
            height: Number(host.height)
        };
    }

    // Map an arbitrary point from an item's local coordinate system into the
    // one output-local presentation coordinate system. Pointer movement and
    // the original grab point deliberately share this exact path.
    function mapItemPoint(screenName, item, localX, localY) {
        const host = root.hostFor(screenName);
        if (!host || !item)
            return null;
        const globalPoint = item.mapToGlobal(
            Number(localX), Number(localY));
        const localPoint = host.mapFromGlobal(globalPoint);
        return { x: Number(localPoint.x), y: Number(localPoint.y) };
    }

    function mapItemRect(screenName, item) {
        const host = root.hostFor(screenName);
        if (!host || !item)
            return null;
        const globalTopLeft = item.mapToGlobal(0, 0);
        const globalBottomRight = item.mapToGlobal(
            Number(item.width), Number(item.height));
        const localTopLeft = host.mapFromGlobal(globalTopLeft);
        const localBottomRight = host.mapFromGlobal(globalBottomRight);
        return {
            x: Number(localTopLeft.x),
            y: Number(localTopLeft.y),
            width: Math.abs(Number(localBottomRight.x)
                - Number(localTopLeft.x)),
            height: Math.abs(Number(localBottomRight.y)
                - Number(localTopLeft.y))
        };
    }

    // DesktopCardHost owns the live screen-space collision geometry. Keep
    // this bridge here so Sidebar code does not recreate a second placement
    // model or inspect another Window's local coordinates.
    function resolveDropCollision(screenName, tileId, x, y, width, height) {
        const host = root.hostFor(screenName);
        if (!host || typeof host.resolveDesktopDrop !== "function")
            return null;
        return host.resolveDesktopDrop(
            String(tileId), Number(x), Number(y),
            Number(width), Number(height));
    }
}
