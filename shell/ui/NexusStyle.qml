pragma Singleton
import QtQuick
import qs.commons

// Caelestia Config tokens, ported 1:1 (plugin/src/Caelestia/Config/tokens.hpp
// + font defaults from appearanceconfig.hpp). The settings surface runs
// UNSCALED: pixel parity with the original trumps the fork-wide 0.85
// dense-panel scale baked into Metrics/Typography. Colors stay in Appearance
// (m3colors / solved overlays) — this object owns geometry, rhythm and type
// sizes only, and the contract tests pin every value against the header.
QtObject {
    readonly property QtObject rounding: QtObject {
        readonly property int extraSmall: 4
        readonly property int small: 8
        readonly property int medium: 12
        readonly property int large: 16
        readonly property int largeIncreased: 20
        readonly property int extraLarge: 28
        readonly property int extraLargeIncreased: 32
        readonly property int extraExtraLarge: 48
        readonly property int full: 9999
    }

    // PaddingTokens and SpacingTokens share the same ladder in the original.
    readonly property QtObject padding: QtObject {
        readonly property int extraSmall: 4
        readonly property int small: 8
        readonly property int medium: 12
        readonly property int large: 16
        readonly property int largeIncreased: 20
        readonly property int extraLarge: 28
        readonly property int extraLargeIncreased: 32
        readonly property int extraExtraLarge: 48
    }

    readonly property QtObject spacing: QtObject {
        readonly property int extraSmall: 4
        readonly property int small: 8
        readonly property int medium: 12
        readonly property int large: 16
        readonly property int largeIncreased: 20
        readonly property int extraLarge: 28
        readonly property int extraLargeIncreased: 32
        readonly property int extraExtraLarge: 48
    }

    // FontSizeTokens plus the weights each style carries in
    // appearanceconfig.hpp (Title/Headline/Label.medium+ Medium; Body and
    // Label.small Normal).
    readonly property QtObject font: QtObject {
        readonly property int labelSmall: 11
        readonly property int labelMedium: 12
        readonly property int labelMediumWeight: Font.Medium
        readonly property int bodySmall: 12
        readonly property int bodyMedium: 14
        readonly property int bodyLarge: 16
        readonly property int titleMedium: 16
        readonly property int titleLarge: 22
        readonly property int titleWeight: Font.Medium
        readonly property int headlineMedium: 24
        readonly property int headlineLarge: 28
        readonly property int headlineWeight: Font.Medium
    }

    // IconSizeTokens in rendered pixels (the header stores them as 24/1.33
    // font sizes; MaterialSymbol takes optical pixels directly).
    readonly property QtObject icon: QtObject {
        readonly property int extraLarge: 48
        readonly property int large: 32
        readonly property int medium: 24
        readonly property int small: 20
    }

    // NexusTokens (window proportions and caps). maxNavWidth deviates from
    // the original 600 by author decision (2026-10-25): a stable quarter of
    // the window reads calmer than the original third.
    readonly property real heightMult: 0.7
    readonly property real ratio: 16 / 9
    readonly property int minWidth: 800
    readonly property int minHeight: 500
    readonly property int maxNavWidth: 480
    readonly property int maxContentWidth: 800

    // Window chrome geometry derived in Nexus.qml: the left zone spans the
    // nav pane plus 16px margins on both sides; the surface frame band is
    // 12px; page content clears the frame by 16px (28 from the window edge).
    readonly property int frameBand: 12
    readonly property int chromeInset: 16
    readonly property int navMargin: 16
}
