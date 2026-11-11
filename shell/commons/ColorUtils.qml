pragma Singleton

import QtQuick
import Quickshell

// Fork & Trim: iNiR modules/common/functions/ColorUtils.qml
// Pure color math singleton, zero process/file/network IO.
Singleton {
    id: root

    function colorWithHueOf(color1, color2) {
        var c1 = Qt.color(color1);
        var c2 = Qt.color(color2);
        return Qt.hsva(c2.hsvHue, c1.hsvSaturation, c1.hsvValue, c1.a);
    }

    function colorWithSaturationOf(color1, color2) {
        var c1 = Qt.color(color1);
        var c2 = Qt.color(color2);
        return Qt.hsva(c1.hsvHue, c2.hsvSaturation, c1.hsvValue, c1.a);
    }

    function colorWithLightness(color, lightness) {
        var c = Qt.color(color);
        return Qt.hsla(c.hslHue, c.hslSaturation, lightness, c.a);
    }

    function colorWithLightnessOf(color1, color2) {
        var c2 = Qt.color(color2);
        return colorWithLightness(color1, c2.hslLightness);
    }

    function adaptToAccent(color1, color2) {
        var c1 = Qt.color(color1);
        var c2 = Qt.color(color2);
        return Qt.hsla(c2.hslHue, c2.hslSaturation, c1.hslLightness, c1.a);
    }

    function mix(color1, color2, percentage = 0.5) {
        var c1 = Qt.color(color1);
        var c2 = Qt.color(color2);
        return Qt.rgba(percentage * c1.r + (1 - percentage) * c2.r,
                       percentage * c1.g + (1 - percentage) * c2.g,
                       percentage * c1.b + (1 - percentage) * c2.b,
                       percentage * c1.a + (1 - percentage) * c2.a);
    }

    function transparentize(color, percentage = 1) {
        if (!color || color === "") return Qt.rgba(0, 0, 0, 0);
        var c = Qt.color(color);
        if (!c.valid) return Qt.rgba(0, 0, 0, 0);
        return Qt.rgba(c.r, c.g, c.b, c.a * (1 - percentage));
    }

    function applyAlpha(color, alpha) {
        var c = Qt.color(color);
        var a = Math.max(0, Math.min(1, alpha));
        return Qt.rgba(c.r, c.g, c.b, a);
    }

    function contrastColor(color) {
        var c = Qt.color(color);
        var r = c.r <= 0.03928 ? c.r / 12.92 : Math.pow((c.r + 0.055) / 1.055, 2.4);
        var g = c.g <= 0.03928 ? c.g / 12.92 : Math.pow((c.g + 0.055) / 1.055, 2.4);
        var b = c.b <= 0.03928 ? c.b / 12.92 : Math.pow((c.b + 0.055) / 1.055, 2.4);
        var luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        return luminance > 0.179 ? Qt.rgba(0, 0, 0, 1) : Qt.rgba(1, 1, 1, 1);
    }

    function lighten(color, amount = 0.1) {
        var c = Qt.color(color);
        var newL = Math.min(1, c.hslLightness + amount);
        return Qt.hsla(c.hslHue, c.hslSaturation, newL, c.a);
    }

    function darken(color, amount = 0.1) {
        var c = Qt.color(color);
        var newL = Math.max(0, c.hslLightness - amount);
        return Qt.hsla(c.hslHue, c.hslSaturation, newL, c.a);
    }

    function isDark(color) {
        var c = Qt.color(color);
        return c.hslLightness < 0.5;
    }

    function clamp01(x) {
        return Math.min(1, Math.max(0, x));
    }

    function solveOverlayColor(baseColor, targetColor, overlayOpacity) {
        let invA = 1.0 - overlayOpacity;
        let r = (targetColor.r - baseColor.r * invA) / overlayOpacity;
        let g = (targetColor.g - baseColor.g * invA) / overlayOpacity;
        let b = (targetColor.b - baseColor.b * invA) / overlayOpacity;
        return Qt.rgba(clamp01(r), clamp01(g), clamp01(b), overlayOpacity);
    }

    function relativeLuminance(color) {
        var c = Qt.color(color);
        var r = c.r <= 0.03928 ? c.r / 12.92 : Math.pow((c.r + 0.055) / 1.055, 2.4);
        var g = c.g <= 0.03928 ? c.g / 12.92 : Math.pow((c.g + 0.055) / 1.055, 2.4);
        var b = c.b <= 0.03928 ? c.b / 12.92 : Math.pow((c.b + 0.055) / 1.055, 2.4);
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }

    function contrastRatio(fg, bg) {
        var l1 = relativeLuminance(fg);
        var l2 = relativeLuminance(bg);
        var lighter = Math.max(l1, l2);
        var darker = Math.min(l1, l2);
        return (lighter + 0.05) / (darker + 0.05);
    }

    function meetsWcagAA(fg, bg) {
        return contrastRatio(fg, bg) >= 4.5;
    }

    function adjustSaturation(color, factor) {
        var c = Qt.color(color);
        var newSat = clamp01(c.hslSaturation * factor);
        return Qt.hsla(c.hslHue, newSat, c.hslLightness, c.a);
    }

    function shiftHue(color, degrees) {
        var c = Qt.color(color);
        var newHue = (c.hslHue + degrees / 360 + 1) % 1;
        return Qt.hsla(newHue, c.hslSaturation, c.hslLightness, c.a);
    }

    function complementary(color) {
        return shiftHue(color, 180);
    }

    function ensureReadable(textColor, bgColor, minRatio = 4.5) {
        if (textColor === undefined || textColor === null || String(textColor).length === 0)
            textColor = Qt.rgba(1, 1, 1, 1);
        if (bgColor === undefined || bgColor === null || String(bgColor).length === 0)
            bgColor = Qt.rgba(0, 0, 0, 1);
        var fg = Qt.color(textColor);
        var bg = Qt.color(bgColor);
        var ratio = contrastRatio(fg, bg);
        if (ratio >= minRatio) return fg;

        var white = Qt.rgba(1, 1, 1, fg.a);
        var black = Qt.rgba(0, 0, 0, fg.a);
        var whiteRatio = contrastRatio(white, bg);
        var blackRatio = contrastRatio(black, bg);
        var targetLightness = whiteRatio >= blackRatio ? 1.0 : 0.0;
        var target = targetLightness > 0.5 ? white : black;

        if (Math.max(whiteRatio, blackRatio) < minRatio)
            return target;

        var failingLightness = fg.hslLightness;
        var passingLightness = targetLightness;
        for (var i = 0; i < 18; i++) {
            var candidateLightness = (failingLightness + passingLightness) / 2;
            var candidate = Qt.hsla(fg.hslHue, fg.hslSaturation, candidateLightness, fg.a);
            if (contrastRatio(candidate, bg) >= minRatio)
                passingLightness = candidateLightness;
            else
                failingLightness = candidateLightness;
        }
        return Qt.hsla(fg.hslHue, fg.hslSaturation, passingLightness, fg.a);
    }

    function readableSubtext(mainTextColor, bgColor, dimFactor = 0.7) {
        var main = Qt.color(mainTextColor);
        var bg = Qt.color(bgColor);
        var dimmed = mix(main, bg, dimFactor);
        return ensureReadable(dimmed, bg, 3.0);
    }

    function readableAccentInk(accentColor, bgColor, target = 4.0, towardColor = null) {
        if (accentColor === undefined || accentColor === null || String(accentColor).length === 0)
            return accentColor;
        if (bgColor === undefined || bgColor === null || String(bgColor).length === 0)
            return accentColor;

        var fg = Qt.color(accentColor);
        var bg = Qt.color(bgColor);
        if (!fg.valid || !bg.valid || contrastRatio(fg, bg) >= target)
            return fg;

        var endpoint = Qt.rgba(0, 0, 0, fg.a);
        if (towardColor !== undefined && towardColor !== null && String(towardColor).length > 0) {
            var hinted = Qt.color(towardColor);
            if (hinted.valid)
                endpoint = Qt.rgba(hinted.r, hinted.g, hinted.b, fg.a);
        }

        if (contrastRatio(endpoint, bg) < target) {
            var white = Qt.rgba(1, 1, 1, fg.a);
            var black = Qt.rgba(0, 0, 0, fg.a);
            endpoint = contrastRatio(white, bg) >= contrastRatio(black, bg) ? white : black;
        }
        if (contrastRatio(endpoint, bg) < target)
            return endpoint;

        var passingRetention = 0.0;
        var failingRetention = 1.0;
        for (var i = 0; i < 20; i++) {
            var retention = (passingRetention + failingRetention) / 2;
            var candidate = mix(fg, endpoint, retention);
            if (contrastRatio(candidate, bg) >= target)
                passingRetention = retention;
            else
                failingRetention = retention;
        }
        return mix(fg, endpoint, passingRetention);
    }
}
