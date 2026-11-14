pragma Singleton
import QtQuick
import Quickshell
import qs.commons

Singleton {
    id: root

    // User-configurable family defaults. Keep all family literals in this
    // singleton so components only depend on semantic roles.
    readonly property string defaultUi: "Noto Sans"
    readonly property string defaultMono: "JetBrainsMono Nerd Font"
    readonly property string defaultNumeric: root.defaultMono
    readonly property string bundledFamilyName: "Google Sans Flex"
    // These preferences are deliberately separate from the effective family
    // properties below. An unavailable saved family is retained for the next
    // run while rendering falls back safely.
    property string configuredUi: ""
    property string configuredMono: ""
    property string configuredNumeric: ""
    property string configuredExpressive: ""
    property var _initialFamilyList: Qt.fontFamilies()
    property var _familySet: new Set(root._initialFamilyList)
    property bool _initialRefreshPending: true
    // Candidate fallback families to ensure smooth rendering across varied environments
    // LXGW fonts register their Chinese family name first in fontconfig and
    // Qt6 only reads FC_FAMILY[0], so the English aliases alone never resolve.
    readonly property var uiFallbackFamilies: ["MiSans", "Noto Sans", "Noto Sans CJK SC", "Noto Sans CJK",
        "霞鹜文楷 GB 屏幕阅读版", "LXGW WenKai GB Screen", "霞鹜文楷等宽", "LXGW WenKai Mono", "sans-serif"]
    readonly property var monoFallbackFamilies: ["JetBrainsMono Nerd Font", "JetBrains Mono", "monospace"]
    readonly property var expressiveFallbackFamilies: ["Google Sans Flex", "Google Sans", "Inter", "Roboto",
        "Noto Sans", "sans-serif"]

    readonly property string ui: root.resolveFirstAvailable([root.configuredUi, root.defaultUi].concat(
                                                                root.uiFallbackFamilies), "")
    readonly property string mono: root.resolveFirstAvailable([root.configuredMono, root.defaultMono].concat(
                                                                  root.monoFallbackFamilies), "monospace")
    readonly property string numeric: root.resolveFirstAvailable([root.configuredNumeric, root.defaultNumeric,
                                                                  root.mono].concat(root.monoFallbackFamilies),
                                                                 "monospace")
    readonly property string expressive: root.resolveFirstAvailable([root.configuredExpressive,
                                                                     root.bundledFamilyName].concat(
                                                                        root.expressiveFallbackFamilies),
                                                                    root.ui)
    // This role resolves cleanly from the expressive fallback stack to root.ui.
    readonly property string systemClock: root.resolveFirstAvailable([root.bundledFamilyName].concat(
                                                                         root.expressiveFallbackFamilies),
                                                                     root.ui)

    function familyAvailable(family) {
        const value = String(family || "").trim();
        if (value === "")
            return false;

        return root._familySet.has(value);
    }

    function resolveFamily(preferred, fallback, genericFallback) {
        const selected = String(preferred || "").trim();
        if (root.familyAvailable(selected))
            return selected;

        const defaultValue = String(fallback || "").trim();
        if (root.familyAvailable(defaultValue))
            return defaultValue;

        return genericFallback || "";
    }

    function resolveFirstAvailable(candidates, genericFallback) {
        for (let i = 0; i < candidates.length; ++i) {
            const family = String(candidates[i] || "").trim();
            if (family !== "" && root.familyAvailable(family))
                return family;
        }
        return genericFallback || "";
    }

    function setConfiguredFamily(role, family) {
        const value = String(family || "").trim();
        if (role === "ui")
            root.configuredUi = value;
        else if (role === "mono")
            root.configuredMono = value;
        else if (role === "numeric")
            root.configuredNumeric = value;
        else if (role === "expressive")
            root.configuredExpressive = value;
        else
            return false;
        return true;
    }

    function setConfiguredFamilies(ui, mono, numeric, expressive) {
        root.configuredUi = String(ui || "").trim();
        root.configuredMono = String(mono || "").trim();
        root.configuredNumeric = String(numeric || "").trim();
        root.configuredExpressive = String(expressive || "").trim();
    }

    Binding {
        target: Fonts
        property: "ui"
        value: root.ui
    }
    Binding {
        target: Fonts
        property: "mono"
        value: root.mono
    }
    Binding {
        target: Fonts
        property: "numeric"
        value: root.numeric
    }
    Binding {
        target: Fonts
        property: "expressive"
        value: root.expressive
    }
    Binding {
        target: Fonts
        property: "systemClock"
        value: root.systemClock
    }
    Binding {
        target: Fonts
        property: "bundledFamilyName"
        value: root.bundledFamilyName
    }
    Binding {
        target: Fonts
        property: "bundledFamilyAvailable"
        value: root.familyAvailable(root.bundledFamilyName)
    }

    readonly property string bundledExpressiveFamily: root.bundledFamilyName
    readonly property var technicalFamilies: [Fonts.materialSymbolsRounded, Fonts.materialSymbolsOutlined]
    property var availableFamilies: []
    readonly property var fontOptions: root.availableFamilies.map(family => {
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
        // Keep the expensive enumeration visible in startup logs so repeated
        // cold-start work can be diagnosed from a real shell process.
        console.log("[FontService] refresh");
        const result = [];
        const firstRefresh = root._initialRefreshPending;
        const source = firstRefresh ? root._initialFamilyList : Qt.fontFamilies();
        root._initialRefreshPending = false;
        if (!firstRefresh)
            root._familySet = new Set(source);
        const seenFamilies = new Set();
        for (let i = 0; i < source.length; i += 1) {
            const family = String(source[i] || "").trim();
            if (family === "" || family.startsWith(".") || root.isTechnicalFamily(family)
                    || seenFamilies.has(family))
                continue;

            seenFamilies.add(family);
            result.push(family);
        }
        if (root.familyAvailable(root.bundledExpressiveFamily)
                && !seenFamilies.has(root.bundledExpressiveFamily))
            result.push(root.bundledExpressiveFamily);

        result.sort();
        root.availableFamilies = result;
    }

    function containsFamily(family) {
        // A programmatic font change can arrive before the queued settings
        // model is ready. Preserve validation without delaying that action.
        if (root._initialRefreshPending)
            root.refresh();
        return root.availableFamilies.indexOf(String(family || "").trim()) !== -1;
    }

    Component.onCompleted: ShellStartupService.scheduleBackground("font-options", () => {
        // An early explicit refresh/selection may already have built the model.
        // Family enumeration and the rendering roles above stay synchronous.
        if (root._initialRefreshPending)
            root.refresh();
    })
}
