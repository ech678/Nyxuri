/*
 * Noctalia-compatible template renderer — expression subset.
 *
 * Covers exactly the syntax the shipped and user templates need:
 *   {{ colors.<name>.<mode>.<format> }}
 * with mode in {default, dark, light} and format in {hex, hex_stripped, rgb,
 * rgb_csv, rgba, hsl, hsla, red, green, blue, alpha, hue, saturation,
 * lightness}. Block directives (<* *>), filters (|) and tonal palette
 * access (palettes.*) are OUT of the subset and fail loudly with a precise
 * error instead of rendering garbage (P4 contract: no silent misrender).
 *
 * Pure computation: no I/O, no environment access. Token model is injected:
 *   colors[tokenName] = { "dark": "#rrggbb", "light": "#rrggbb" }
 */
.pragma library

.import "ThemeColor.js" as ThemeColor

var BLOCK_MARKER = "<*";
var FILTER_MARKER = "|";
var PALETTES_MARKER = "palettes.";

var MODES = ["default", "dark", "light"];
var FORMATS = ["hex", "hex_stripped", "rgb", "rgb_csv", "rgba", "hsl", "hsla",
               "red", "green", "blue", "alpha", "hue", "saturation", "lightness"];

function fail(templateName, detail) {
    throw new Error("Template '" + templateName + "': " + detail);
}

/**
 * Renders template text against the token model. activeMode is "dark" or
 * "light" and resolves the `.default.` mode selector. Throws on any syntax
 * outside the expression subset or on unknown tokens/formats.
 */
function render(templateName, text, colors, activeMode) {
    if (typeof text !== "string") {
        fail(templateName, "template body is not text");
    }
    if (text.indexOf(BLOCK_MARKER) !== -1) {
        fail(templateName,
             "block directives (<* *>) are not supported by the expression subset");
    }
    if (text.indexOf(PALETTES_MARKER) !== -1) {
        fail(templateName, "tonal palette access (palettes.*) is not supported");
    }
    let out = "";
    let index = 0;
    while (true) {
        const start = text.indexOf("{{", index);
        if (start === -1) {
            out += text.substring(index);
            break;
        }
        const end = text.indexOf("}}", start + 2);
        if (end === -1) {
            fail(templateName, "unclosed expression at offset " + start);
        }
        out += text.substring(index, start);
        const expression = text.substring(start + 2, end);
        out += evaluate(templateName, expression, colors, activeMode);
        index = end + 2;
    }
    return out;
}

function evaluate(templateName, expression, colors, activeMode) {
    const body = expression.trim();
    if (body === "") {
        fail(templateName, "empty expression");
    }
    if (body.indexOf(FILTER_MARKER) !== -1) {
        fail(templateName, "filters (|) are not supported: '" + body + "'");
    }
    const parts = body.split(".").map(part => part.trim());
    if (parts.length !== 4 || parts[0] !== "colors") {
        fail(templateName,
             "unsupported expression '" + body + "' (expected colors.<name>.<mode>.<format>)");
    }
    const name = parts[1];
    const mode = parts[2];
    const format = parts[3];
    if (MODES.indexOf(mode) === -1) {
        fail(templateName, "unknown mode '" + mode + "'");
    }
    if (FORMATS.indexOf(format) === -1) {
        fail(templateName, "unknown format '" + format + "'");
    }
    const token = colors[name];
    if (!token) {
        fail(templateName, "unknown color token '" + name + "'");
    }
    const resolvedMode = mode === "default" ? activeMode : mode;
    const hex = token[resolvedMode];
    if (!ThemeColor.argbFromHex(hex)) {
        fail(templateName, "missing " + resolvedMode + " color for token '" + name + "'");
    }
    return formatValue(hex, format);
}

function formatValue(hex, format) {
    const argb = ThemeColor.argbFromHex(hex);
    const r = (argb >> 16) & 255;
    const g = (argb >> 8) & 255;
    const b = argb & 255;
    switch (format) {
        case "hex":
            return hex.toLowerCase();
        case "hex_stripped":
            return hex.replace("#", "").toLowerCase();
        case "rgb":
            return "rgb(" + r + ", " + g + ", " + b + ")";
        case "rgb_csv":
            return r + "," + g + "," + b;
        case "rgba":
            return "rgba(" + r + ", " + g + ", " + b + ", 1.0)";
        case "red":
            return String(r);
        case "green":
            return String(g);
        case "blue":
            return String(b);
        case "alpha":
            return "1.0";
        default:
            return hslValue(hex, format);
    }
}

function hslValue(hex, format) {
    const argb = ThemeColor.argbFromHex(hex);
    const r = ((argb >> 16) & 255) / 255;
    const g = ((argb >> 8) & 255) / 255;
    const b = (argb & 255) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    let h = 0;
    let s = 0;
    if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        if (max === r) {
            h = (g - b) / d + (g < b ? 6 : 0);
        } else if (max === g) {
            h = (b - r) / d + 2;
        } else {
            h = (r - g) / d + 4;
        }
        h *= 60;
    }
    switch (format) {
        case "hsl":
            return "hsl(" + Math.round(h) + ", " + Math.round(s * 100) + "%, "
                    + Math.round(l * 100) + "%)";
        case "hsla":
            return "hsla(" + Math.round(h) + ", " + Math.round(s * 100) + "%, "
                    + Math.round(l * 100) + "%, 1.0)";
        case "hue":
            return String(Math.round(h));
        case "saturation":
            return String(Math.round(s * 100));
        case "lightness":
            return String(Math.round(l * 100));
        default:
            throw new Error("Unreachable format '" + format + "'");
    }
}
