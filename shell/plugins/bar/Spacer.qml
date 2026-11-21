import QtQuick
import qs.services
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

// First-class spacer (D4a): an empty lane slot with a configurable size.
// The first consumer of the widgetEntry injection protocol — the lane host
// injects the entry object and the size axis resolves through the single
// option() fallback chain (entry override -> DEFAULTS.spacer.size), never
// through a direct storage read. Geometry follows Divisor's contract: the
// slot sizes along the bar axis, the cross axis is stretched by the lane
// layout.
Item {
    id: root

    // Injected by the bar lane hosts (D4a property-injection protocol).
    property var widgetEntry: null

    property bool vertical: Config.options.bar.vertical

    readonly property real spacerSize: BarWidgetDefaults.option("spacer", root.widgetEntry, "size")

    width: root.vertical ? 1 : root.spacerSize
    height: root.vertical ? root.spacerSize : 1
}
