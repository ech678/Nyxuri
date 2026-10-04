pragma Singleton
import Quickshell

Singleton {
    // Global size scale. The bar/sidebar tokens below are logical pixels tuned
    // for 1.0; lower it to shrink the shell together with Metrics and
    // Typography. lockHeightMult and lockRatio are ratios, not sizes.
    readonly property real scale: 0.85

    readonly property real cornerRadius: 10 * scale
    readonly property real barVisualThickness: 44 * scale
    readonly property real barPillThickness: 36 * scale
    readonly property real barPillHorizontalPadding: 8 * scale
    // Pill content: 28px controls inside a 36px surface; 8px along its axis.
    readonly property real barItemSpacing: 4 * scale
    readonly property real barLabelSpacing: 6 * scale
    readonly property real barIconSize: 20 * scale
    readonly property real barControlCircleSize: 28 * scale
    readonly property real barOuterEdgeMargin: 8 * scale
    readonly property real barShadowBuffer: 36 * scale
    readonly property real barPopupGap: 8 * scale
    readonly property real barPopupScreenMargin: 10 * scale
    // Presentation compatibility aliases. Surface geometry must use the
    // semantic tokens above so margin, visuals, and shadow never mix.
    readonly property real barHeight: barVisualThickness
    readonly property real verticalBarWidth: barVisualThickness
    readonly property real sidebarScrollableListMaxHeight: 224 * scale
    // Concave transitions the notch surface style grows into the screen edge.
    // Tuned to sit alongside the Keystone tray curves (8/14 unscaled there).
    readonly property real notchCurveAlong: 10 * scale
    readonly property real notchCurveDepth: 16 * scale
    readonly property real lockHeightMult: 0.7
    readonly property real lockRatio: 16 / 9
}
