pragma Singleton
import QtQuick
import qs.services

// D4c: the barConfigs fontScale axis (multiplier over the NexusStyle type
// scale, default 1.0 = the type scale untouched). Bar-surface files
// multiply their NexusStyle font-size reads through here; settings pages
// and dual-surface cards (dashboard weather/resources) never do — their
// text is not bar surface. Weight enums do not scale (only sizes).
// The icon twin is D4e density material (bar icon slots are end4
// literals, not type-scale reads).
QtObject {
    readonly property real font: {
        const value = Number(PersonalizationConfig.barAxes.fontScale);
        return isFinite(value) && value > 0 ? value : 1;
    }
}
