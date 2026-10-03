pragma Singleton

import QtQuick
import Quickshell
import qs.shared.theme

Singleton {
    id: root

    property color primary: Appearance.colors.colPrimary
    property color onPrimary: Appearance.colors.colOnPrimary
    property color track: Appearance.colors.colPrimaryContainer

    function extract(artUrl, fallback) {
        const safeFallback = (fallback !== undefined && fallback !== null && Qt.color(fallback).valid)
              ? fallback : Appearance.colors.colPrimary;
        root.primary = safeFallback;
        root.onPrimary = Appearance.colors.colOnPrimary;
        root.track = Appearance.colors.colPrimaryContainer;
    }
}
