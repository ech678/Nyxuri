pragma Singleton

import QtQuick

QtObject {
    id: root

    // Global type scale. Material 3 sizes below are tuned for 1.0; lower it
    // when the panel is already dense (2K output at scale 1.0 reads oversized).
    readonly property real scale: 0.85

    // Material 3 type scale. Family is bound to Fonts.ui so changing the UI
    // family immediately updates every standard style.
    readonly property QtObject displaySmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(36 * root.scale)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject headlineMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(28 * root.scale)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject headlineSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(24 * root.scale)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(22 * root.scale)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(16 * root.scale)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(14 * root.scale)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodyLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(16 * root.scale)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodyMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(14 * root.scale)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodySmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(12 * root.scale)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(14 * root.scale)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(12 * root.scale)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: Math.round(11 * root.scale)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
}
