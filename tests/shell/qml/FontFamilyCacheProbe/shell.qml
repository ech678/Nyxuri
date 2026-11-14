import QtQuick
import Quickshell
import qs.app
import qs.commons
import qs.services
import qs.ui

ShellRoot {
    id: root

    function fail(reason) {
        console.error("FONT_FAMILY_CACHE_FAIL " + reason);
        Qt.exit(1);
    }

    function capture() {
        const families = Qt.fontFamilies();
        const localeCandidates = FontService.uiFallbackFamilies;
        let expectedLocale = "locale-generic-fallback";
        for (let index = 0; index < localeCandidates.length; index += 1) {
            const candidate = localeCandidates[index];
            if (families.indexOf(candidate) !== -1) {
                expectedLocale = candidate;
                break;
            }
        }

        const rolesBeforeConfiguredMissing = {
            "ui": FontService.ui,
            "mono": FontService.mono,
            "numeric": FontService.numeric,
            "expressive": FontService.expressive,
            "systemClock": FontService.systemClock
        };
        if (FontService.resolveFirstAvailable(localeCandidates, "locale-generic-fallback") !== expectedLocale)
            return root.fail("locale fallback priority changed");
        if (FontService.resolveFirstAvailable(["NyxuriCacheProbeMissing"], "monospace") !== "monospace")
            return root.fail("generic fallback changed");
        for (let index = 0; index < families.length; index += 1) {
            const family = families[index];
            if (!FontService.familyAvailable(family))
                return root.fail("a family disappeared from membership cache after refresh: " + family);
        }
        const availableFamilies = FontService.availableFamilies.slice();
        const fontOptions = FontService.fontOptions.map(option => option.value);
        if (JSON.stringify(availableFamilies) !== JSON.stringify(availableFamilies.slice().sort()))
            return root.fail("availableFamilies is not sorted");
        const stats = Object.assign({}, FontService._fontCacheProbeStats);

        const localeFixture = ["JetBrains Mono", "LXGW WenKai GB Screen", "霞鹜文楷 GB 屏幕阅读版"];
        FontService._fontCacheProbeFamilies = localeFixture;
        FontService._fontCacheProbeFamilySet = new Set(localeFixture);
        if (FontService.resolveFirstAvailable(FontService.uiFallbackFamilies, "locale-generic-fallback")
                !== "霞鹜文楷 GB 屏幕阅读版")
            return root.fail("Chinese locale candidate order changed");
        const fixtureRoles = {
            "ui": FontService.ui,
            "mono": FontService.mono,
            "numeric": FontService.numeric,
            "expressive": FontService.expressive,
            "systemClock": FontService.systemClock
        };
        if (fixtureRoles.ui !== "霞鹜文楷 GB 屏幕阅读版" || fixtureRoles.mono !== "JetBrains Mono"
                || fixtureRoles.numeric !== "JetBrains Mono"
                || fixtureRoles.expressive !== "霞鹜文楷 GB 屏幕阅读版"
                || fixtureRoles.systemClock !== "霞鹜文楷 GB 屏幕阅读版")
            return root.fail("font role priorities changed for the locale fixture: " + JSON.stringify(fixtureRoles));

        FontService.setConfiguredFamilies("NyxuriMissingUi", "NyxuriMissingMono",
                                          "NyxuriMissingNumeric", "NyxuriMissingExpressive");
        if (FontService.configuredUi !== "NyxuriMissingUi"
                || FontService.configuredMono !== "NyxuriMissingMono"
                || FontService.configuredNumeric !== "NyxuriMissingNumeric"
                || FontService.configuredExpressive !== "NyxuriMissingExpressive")
            return root.fail("unavailable configured families were not retained");
        if (FontService.ui === "NyxuriMissingUi" || FontService.mono === "NyxuriMissingMono"
                || FontService.numeric === "NyxuriMissingNumeric"
                || FontService.expressive === "NyxuriMissingExpressive")
            return root.fail("unavailable configured family did not fall back");

        console.log("FONT_FAMILY_CACHE_RESULT " + JSON.stringify({
            "roles": rolesBeforeConfiguredMissing,
            "fixtureRoles": fixtureRoles,
            "availableFamilies": availableFamilies,
            "fontOptionFamilies": fontOptions,
            "localeFallback": expectedLocale,
            "localePriorityFixture": "霞鹜文楷 GB 屏幕阅读版",
            "configuredMissingRetained": true,
            "genericFallback": "monospace",
            "stats": stats
        }));
        console.log("FONT_FAMILY_CACHE_PASS cold_start=true");
        Qt.quit();
    }

    Component.onCompleted: {
        Qt.callLater(root.capture);
    }

    Timer {
        interval: 30000
        running: true
        onTriggered: root.fail("timed out during FontService cold startup")
    }
}
