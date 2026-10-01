pragma Singleton

import QtQuick

QtObject {
    id: root

    // Material 3 type scale. Family is bound to Fonts.ui so changing the UI
    // family immediately updates every standard style.
    readonly property QtObject displaySmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 36
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject headlineMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 28
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject headlineSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 24
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 22
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 16
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 14
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodyLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 16
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodyMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 14
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodySmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 12
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 14
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 12
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: 11
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
}
