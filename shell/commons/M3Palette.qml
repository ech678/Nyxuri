pragma Singleton

import QtQuick
import Quickshell

// Fork & Trim: iNiR modules/common/m3/M3Palette.qml
// Bridges Nyxuri Appearance.m3colors to Material 3 tokens & pill color functions.
Singleton {
    id: root

    readonly property color surface: Appearance.m3colors.m3surface
    readonly property color surfaceContainerLow: Appearance.m3colors.m3surfaceContainerLow
    readonly property color surfaceContainer: Appearance.m3colors.m3surfaceContainer
    readonly property color surfaceContainerHigh: Appearance.m3colors.m3surfaceContainerHigh
    readonly property color surfaceContainerHighest: Appearance.m3colors.m3surfaceContainerHighest
    readonly property color surfaceForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onSurface, surface, 4.5)
    readonly property color surfaceVariantForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onSurfaceVariant, surfaceContainer, 3.0)

    readonly property color outline: Appearance.m3colors.m3outline
    readonly property color outlineVariant: Appearance.m3colors.m3outlineVariant

    readonly property color primary: Appearance.m3colors.m3primary
    readonly property color primaryForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onPrimary, primary, 4.5)
    readonly property color primaryContainer: Appearance.m3colors.m3primaryContainer
    readonly property color primaryContainerForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onPrimaryContainer, primaryContainer, 4.5)

    readonly property color secondary: Appearance.m3colors.m3secondary
    readonly property color secondaryForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onSecondary, secondary, 4.5)
    readonly property color secondaryContainer: Appearance.m3colors.m3secondaryContainer
    readonly property color secondaryContainerForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onSecondaryContainer, secondaryContainer, 4.5)

    readonly property color tertiary: Appearance.m3colors.m3tertiary
    readonly property color tertiaryForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onTertiary, tertiary, 4.5)
    readonly property color tertiaryContainer: Appearance.m3colors.m3tertiaryContainer
    readonly property color tertiaryContainerForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onTertiaryContainer, tertiaryContainer, 4.5)

    readonly property color error: Appearance.m3colors.m3error
    readonly property color errorForeground: ColorUtils.ensureReadable(Appearance.m3colors.m3onError, error, 4.5)

    readonly property color tooltip: surfaceContainerHighest
    readonly property color tooltipForeground: ColorUtils.ensureReadable(surfaceForeground, tooltip, 4.5)

    readonly property color primaryContainerHover: ColorUtils.mix(primaryContainer, primaryContainerForeground, 0.90)
    readonly property color primaryContainerActive: ColorUtils.mix(primaryContainer, primaryContainerForeground, 0.80)
    readonly property color secondaryContainerHover: ColorUtils.mix(secondaryContainer, secondaryContainerForeground, 0.90)
    readonly property color secondaryContainerActive: ColorUtils.mix(secondaryContainer, secondaryContainerForeground, 0.80)

    function pillContainer(name: string): color {
        switch (name) {
        case "media":
        case "sysTray":
        case "tray":
        case "sidebarToggle":
            return secondaryContainer;
        case "resources":
        case "systemMonitor":
            return tertiaryContainer;
        case "systemIcons":
            return primary;
        default:
            return primaryContainer;
        }
    }

    function pillInk(name: string): color {
        switch (name) {
        case "media":
        case "sysTray":
        case "tray":
        case "sidebarToggle":
            return ColorUtils.ensureReadable(secondaryContainerForeground, pillContainer(name), 4.5);
        case "resources":
        case "systemMonitor":
            return ColorUtils.ensureReadable(tertiaryContainerForeground, pillContainer(name), 4.5);
        case "systemIcons":
            return ColorUtils.ensureReadable(primaryForeground, pillContainer(name), 4.5);
        default:
            return ColorUtils.ensureReadable(primaryContainerForeground, pillContainer(name), 4.5);
        }
    }

    function pillAccent(name: string, accent: color): color {
        return ColorUtils.readableAccentInk(accent, pillContainer(name), 3.0);
    }
}
