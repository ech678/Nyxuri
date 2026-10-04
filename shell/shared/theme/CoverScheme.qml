import QtQuick
import qs.shared.theme

// A Material-ish palette derived from a cover colour.
//
// Ported from end4-pC's modules/common/models/AdaptedMaterialScheme.qml, which
// is what makes the media page take on the album art's colour instead of using
// the wallpaper theme. That page is the one place in the shell where the chrome
// follows the music rather than the desktop.
//
// Two things to know about the arithmetic, because both look arbitrary and are
// load-bearing:
//
//   1. Every colour is a *mix* between a theme colour and the cover colour,
//      never the cover colour used directly. Cover art is arbitrary; used raw
//      it produces unreadable text on roughly half of all albums. Mixing keeps
//      the theme's luminance relationships (which are what make the text
//      legible) while adopting the cover's hue.
//
//   2. `adaptToAccent` exists for the accent family. A plain mix would drag
//      `colPrimary` toward the cover's lightness as well as its hue, and the
//      primary is the one colour the shell guarantees contrast against
//      `colOnPrimary`. So the accent keeps its theme lightness and takes only
//      the cover's hue/saturation — the ratio at the call site then decides
//      how far to commit.
//
// Lives in shared/ because it is pure computation over injected colours: it
// reads no config, touches no service, and holds no state. Callers pass the
// cover colour and read the result.
QtObject {
    id: root

    // The colour to derive from. Consumers gate on `active` (or an equivalent)
    // and fall back to Appearance.colors themselves.
    required property color color

    // Dark art needs a different mix ratio for the base layer, or the surface
    // stays light while everything derived from it goes dark and the card ends
    // up unreadable. The darkmode check mirrors end4-pC: only compensate when
    // the shell itself is dark.
    readonly property bool colorIsDark: root.color.hslLightness < 0.5
    readonly property bool darkSurface: root.colorIsDark && Appearance.m3colors.darkmode

    // Keeps the theme colour's lightness and alpha, takes the accent's hue and
    // saturation. See note 2 above.
    function adaptToAccent(baseColor, accentColor) {
        const base = Qt.color(baseColor);
        const accent = Qt.color(accentColor);
        return Qt.hsla(accent.hslHue, accent.hslSaturation, base.hslLightness, base.a);
    }

    readonly property color colLayer0: Appearance.mix(Appearance.colors.colLayer0, root.color,
                                                      root.darkSurface ? 0.6 : 0.5)
    readonly property color colLayer1: Appearance.mix(Appearance.colors.colLayer1, root.color, 0.5)
    readonly property color colOnLayer0: Appearance.mix(Appearance.colors.colOnLayer0, root.color, 0.5)
    readonly property color colOnLayer1: Appearance.mix(Appearance.colors.colOnLayer1, root.color, 0.5)
    readonly property color colSubtext: Appearance.mix(Appearance.colors.colOnLayer1, root.color, 0.5)

    readonly property color colPrimary: Appearance.mix(root.adaptToAccent(Appearance.colors.colPrimary,
                                                                          root.color), root.color, 0.5)
    readonly property color colPrimaryHover: Appearance.mix(root.adaptToAccent(
                                                                Appearance.colors.colPrimaryHover, root.color),
                                                            root.color, 0.3)
    readonly property color colPrimaryActive: Appearance.mix(root.adaptToAccent(
                                                                 Appearance.colors.colPrimaryActive,
                                                                 root.color), root.color, 0.3)
    readonly property color colOnPrimary: Appearance.mix(root.adaptToAccent(Appearance.m3colors.m3onPrimary,
                                                                            root.color), root.color, 0.5)

    readonly property color colSecondary: Appearance.mix(root.adaptToAccent(Appearance.colors.colSecondary,
                                                                            root.color), root.color, 0.5)
    readonly property color colSecondaryContainer: Appearance.mix(Appearance.m3colors.m3secondaryContainer,
                                                                  root.color, 0.15)
    readonly property color colSecondaryContainerHover: Appearance.mix(
                                                            Appearance.colors.colSecondaryContainerHover,
                                                            root.color, 0.3)
    readonly property color colSecondaryContainerActive: Appearance.mix(
                                                             Appearance.colors.colSecondaryContainerActive,
                                                             root.color, 0.5)
    readonly property color colOnSecondaryContainer: Appearance.mix(Appearance.m3colors.m3onSecondaryContainer,
                                                                    root.color, 0.5)
}
