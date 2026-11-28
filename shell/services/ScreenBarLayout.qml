pragma Singleton
import QtQuick
import Quickshell
import "BarDefaults.js" as BarDefaults
import "../commons/BarScreenLayout.js" as BarScreenLayout
import "../commons/BarGeometry.js" as BarGeometry

// D4g 批四b: the per-screen bar topology projection — the single source
// for every cross-surface avoidance inset and the bar windows' tuck
// margins. Derived ONLY from barConfigs + the connected screens (the
// config truth), never from window instances, so disabled units and
// cold starts resolve identically. Consumers: Bar.qml (corner tuck),
// NotificationPopupHost (popup insets), the sidebar panels (drawer
// insets) — none of them recompute bar geometry locally.
Singleton {
    id: root

    // One resolved layout per connected screen; the binding re-resolves
    // on screen changes AND on every barConfigs/axes mutation (resolve
    // reads them during evaluation).
    readonly property var layouts: Quickshell.screens.map(screen => root.resolve(screen))

    function resolve(screen) {
        const screens = Quickshell.screens;
        const screenNames = screens.map(candidate => candidate.name);
        const inputs = [];
        const configs = Array.isArray(PersonalizationConfig.barConfigs) ? PersonalizationConfig.barConfigs : [];
        configs.forEach(config => {
            if (!config || config.enabled === false)
                return;
            const axes = config.axes;
            if (!axes)
                return;
            if (!BarScreenLayout.coversScreen(axes, screen.name, screenNames))
                return;
            const vertical = axes.position === "left" || axes.position === "right";
            const style = BarDefaults.deriveStyle(axes, Config.options.bar.m3.gapsOut);
            // Total band distance from the screen edge: edgeMargin + thickness +
            // boost + innerMargin. autoHide entries slide away, so they reserve
            // nothing (dux `reserves` lineage).
            const zone = BarGeometry.screenReservation(vertical, axes.barThickness, axes.verticalThickness, BarDefaults.styleBoost(style), axes.edgeMargin, axes.innerMargin);
            inputs.push({
                id: config.id,
                edge: axes.position,
                reservation: axes.autoHide === true ? 0 : zone
            });
        });
        return BarScreenLayout.resolveScreen(inputs, screen.name);
    }

    function forScreen(screen) {
        const name = typeof screen === "string" ? screen : screen ? screen.name : "";
        return root.layouts.find(layout => layout.screenName === name) ?? null;
    }

    // The avoidance inset a surface on `edge` applies (0 when no shown
    // bar sits there — autoHide bars reserve nothing).
    function reservation(screen, edge) {
        return BarScreenLayout.reservation(root.forScreen(screen), edge);
    }

    // The corner-tuck insets for one bar entry (window margins).
    function tuckMargins(screen, barId) {
        return BarScreenLayout.tuckMargins(root.forScreen(screen), barId);
    }
}
