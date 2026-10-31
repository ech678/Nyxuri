pragma Singleton
import QtQuick
import Quickshell

Singleton {
    property string ui: "sans-serif"
    property string mono: "monospace"
    property string numeric: "monospace"
    property string expressive: "sans-serif"
    property string systemClock: "Google Sans Flex"
    property string bundledFamilyName: "Google Sans Flex"
    property bool bundledFamilyAvailable: false
    readonly property string materialSymbolsRounded: "Material Symbols Rounded"
    readonly property string materialSymbolsOutlined: "Material Symbols Outlined"

    // Canvas accepts a CSS font-family string rather than a QML family
    // property. Keep the quoting in one place so a family selected by the
    // user cannot break the drawing command.
    function cssFamily(family) {
        return "\"" + String(family || "").replace(/\\/g, "\\\\").replace(/\"/g, "\\\"") + "\"";
    }
}
