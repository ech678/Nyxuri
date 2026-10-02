import QtQuick

Translate {
    required property var view
    property real order: 0

    // Free-positioned grids have no layout to allocate the extra row spacing.
    // Later rows travel farther, driven by the same eased distance as the header.
    y: view.motionEnabled ? view.contentTopInset + Math.max(0, order) * view.sectionExpansion : 0
}
