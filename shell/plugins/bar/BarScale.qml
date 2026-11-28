pragma Singleton
import QtQuick
import qs.services

// D4c/D4e: barConfigs fontScale & iconScale multipliers (default 1.0 = the
// NexusStyle type scale and end4 icon baselines untouched). Multi-bar surfaces
// pass their injected `widgetBar` through fontFor()/iconFor() so each bar
// scales independently; settings/uninjected callers fall back to activeBarConfig.
QtObject {
    readonly property real font: fontFor(null)
    readonly property real icon: iconFor(null)

    function fontFor(widgetBar): real {
        const axes = widgetBar && widgetBar.axes ? widgetBar.axes : PersonalizationConfig.barAxes;
        const value = Number(axes ? axes.fontScale : 1);
        return isFinite(value) && value > 0 ? value : 1;
    }

    function iconFor(widgetBar): real {
        const axes = widgetBar && widgetBar.axes ? widgetBar.axes : PersonalizationConfig.barAxes;
        const value = Number(axes ? axes.iconScale : 1);
        return isFinite(value) && value > 0 ? value : 1;
    }
}
