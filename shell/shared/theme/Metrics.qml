pragma Singleton
import QtQuick

QtObject {
    id: root

    // Static logical-pixel design tokens. Qt/Wayland maps these values to the
    // output buffer; they are intentionally not user-scalable.
    //
    // Local fork: a scale factor is layered on top so the shell can be shrunk
    // on dense panels. Set it back to 1.0 to restore upstream geometry.
    readonly property real scale: 0.85

    readonly property real spacingXXS: 2 * root.scale
    readonly property real spacingXS: 4 * root.scale
    readonly property real spacingS: 8 * root.scale
    readonly property real spacingM: 12 * root.scale
    readonly property real spacingL: 16 * root.scale
    readonly property real spacingXL: 24 * root.scale
    readonly property real iconS: 16 * root.scale
    readonly property real iconM: 24 * root.scale
    readonly property real iconL: 32 * root.scale
    readonly property real controlHeightS: 32 * root.scale
    readonly property real controlHeightM: 40 * root.scale
    readonly property real controlHeightL: 48 * root.scale
    readonly property real controlHeightXL: 56 * root.scale
    readonly property real touchTarget: 48 * root.scale
    readonly property real cornerXS: 4 * root.scale
    readonly property real cornerS: 12 * root.scale
    readonly property real cornerM: 17 * root.scale
    readonly property real cornerL: 23 * root.scale
    readonly property real cornerXL: 28 * root.scale
    readonly property real cardPadding: spacingL
    readonly property real pageMargin: spacingXL
    readonly property real popupMargin: spacingL
    readonly property real dividerWidth: 1
    readonly property real sidebarWidthCompact: 420 * root.scale
    readonly property real sidebarWidthComfortable: 540 * root.scale
    readonly property real hotCornerSize: 8
    readonly property real barHeight: 44 * root.scale
    readonly property real avatarS: 32 * root.scale
    readonly property real avatarM: 48 * root.scale
    readonly property real avatarL: 64 * root.scale
    // Lock shell design rules. Runtime output geometry stays local to each
    // WlSessionLockSurface and is compared against these logical-pixel tokens.
    readonly property real lockCenterWidth: 600 * root.scale
    readonly property real lockColumnGap: 40 * root.scale
    readonly property real lockCardGap: spacingL
    readonly property real lockOuterPadding: 20 * root.scale
    readonly property real lockCardPadding: spacingXL
    readonly property real lockCardRadius: 33 * root.scale
    readonly property real lockCardRadiusSmall: cornerL
    readonly property real lockAuthHeight: 64 * root.scale
    readonly property real lockTimeFontSize: 112 * root.scale
    readonly property real lockTimeSuffixFontSize: 75 * root.scale
    readonly property real lockDateFontSize: 37 * root.scale
    readonly property real lockIconPanelSize: 213 * root.scale
    readonly property real lockCompactBreakpoint: 640
    readonly property real lockVeryCompactBreakpoint: 540
    readonly property real lockForecastBreakpoint: 680
    readonly property real lockFetchExpandedBreakpoint: 700
    readonly property real lockResourceProgressPadding: 60 * root.scale
    readonly property real lockResourceProgressStroke: 9 * root.scale
    readonly property real lockResourceProgressGap: 9 * root.scale
    readonly property real lockResourceIconScale: 0.82
}
