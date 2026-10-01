pragma Singleton
import QtQuick
import Quickshell
import qs.Common

Singleton {
    id: root

    readonly property string bundledExpressiveFamily: Fonts.bundledFamilyName
    readonly property var technicalFamilies: [Fonts.materialSymbolsRounded, Fonts.materialSymbolsOutlined]
    property var availableFamilies: []
    readonly property var fontOptions: root.availableFamilies.map((family) => {
        return ({
            "value": family,
            "label": family
        });
    })

    function isTechnicalFamily(family) {
        const value = String(family || "").trim();
        const lower = value.toLowerCase();
        return root.technicalFamilies.indexOf(value) !== -1 || lower.indexOf("material symbols") !== -1;
    }

    function refresh() {
        const result = [];
        const source = Qt.fontFamilies();
        for (let i = 0; i < source.length; i += 1) {
            const family = String(source[i] || "").trim();
            if (family === "" || family.startsWith(".") || root.isTechnicalFamily(family) || result.indexOf(family) !== -1)
                continue;

            result.push(family);
        }
        if (result.indexOf(root.bundledExpressiveFamily) === -1)
            result.push(root.bundledExpressiveFamily);

        result.sort();
        root.availableFamilies = result;
    }

    function containsFamily(family) {
        return root.availableFamilies.indexOf(String(family || "").trim()) !== -1;
    }

    Component.onCompleted: root.refresh()
}
