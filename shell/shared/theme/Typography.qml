pragma Singleton

import QtQuick

QtObject {
    id: root

    function scaled(value) {
        const numeric = Number(value);
        if (!isFinite(numeric) || numeric <= 0)
            return 0;
        return Math.max(1, Math.round(numeric * Appearance.fontScale));
    }

    readonly property QtObject displaySmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(36)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject headlineMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(28)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject headlineSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(24)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(22)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(16)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject titleSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(14)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodyLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(16)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodyMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(14)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject bodySmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(12)
        readonly property int weight: Font.Normal
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelLarge: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(14)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelMedium: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(12)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
    readonly property QtObject labelSmall: QtObject {
        readonly property string family: Fonts.ui
        readonly property int pixelSize: root.scaled(11)
        readonly property int weight: Font.Medium
        readonly property real letterSpacing: 0
    }
}
