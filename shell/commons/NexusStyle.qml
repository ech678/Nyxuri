pragma Singleton
import QtQuick
import qs.commons

// Design-system L1 token source (llms-wiki/shell/design-system.md). Numbers
// port 1:1 from references/caelestia/plugin/src/Caelestia/Config/tokens.hpp
// + appearanceconfig.hpp; D-1 promoted this table to the single library-wide
// type scale, so every surface (bar included) reads type from here — the
// end4 Appearance.font ladder and the old commons/Typography singleton are
// retired. Colors stay in Appearance/M3Palette; this object owns geometry,
// rhythm and type sizes only, and the contract tests pin every value.
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

    // The M3 type scale (D-1): label 11/12/14 · body 12/14/16 ·
    // title 14/16/22 · headline 24/28/32 · display 36/45/57 (M3 spec tier;
    // Caelestia never consumed it, lock/clock numerals do) · mono 12/14/16.
    // Weights follow appearanceconfig.hpp: Title/Headline/Label.medium+
    // carry Medium; Body, Label.small and Mono stay Regular.
    readonly property QtObject font: QtObject {
        readonly property int labelSmall: 11
        readonly property int labelMedium: 12
        readonly property int labelMediumWeight: Font.Medium
        readonly property int labelLarge: 14
        readonly property int labelLargeWeight: Font.Medium
        readonly property int bodySmall: 12
        readonly property int bodyMedium: 14
        readonly property int bodyLarge: 16
        readonly property int titleSmall: 14
        readonly property int titleMedium: 16
        readonly property int titleLarge: 22
        readonly property int titleWeight: Font.Medium
        readonly property int headlineSmall: 24
        readonly property int headlineMedium: 28
        readonly property int headlineLarge: 32
        readonly property int headlineWeight: Font.Medium
        readonly property int displaySmall: 36
        readonly property int displayMedium: 45
        readonly property int displayLarge: 57
        readonly property int monoSmall: 12
        readonly property int monoMedium: 14
        readonly property int monoLarge: 16
    }

    // IconSizeTokens in rendered pixels (the header stores them as 24/1.33
    // font sizes; MaterialSymbol takes optical pixels directly). Glyph
    // geometry flows through iconSize properties, not the type scale.
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
