.pragma library

function srgbToLinear(c) {
    c = c / 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function linearToSrgb(c) {
    return c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
}

function rgbToOklab(r, g, b) {
    var lr = srgbToLinear(r);
    var lg = srgbToLinear(g);
    var lb = srgbToLinear(b);
    var l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb;
    var m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb;
    var s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb;
    var l_ = Math.cbrt(l);
    var m_ = Math.cbrt(m);
    var s_ = Math.cbrt(s);
    return [
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    ];
}

function oklabToLinear(L, a, b) {
    var l_ = L + 0.3963377774 * a + 0.2158037573 * b;
    var m_ = L - 0.1055613458 * a - 0.0638541728 * b;
    var s_ = L - 0.0894841775 * a - 1.2914855480 * b;
    var l = l_ * l_ * l_;
    var m = m_ * m_ * m_;
    var s = s_ * s_ * s_;
    return [
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    ];
}

var WP = [0.9504559271, 1.0, 1.0890577508];

function linearToXyz(r, g, b) {
    return [
        0.4123907993 * r + 0.3575843394 * g + 0.1804807884 * b,
        0.2126390059 * r + 0.7151686788 * g + 0.0721923154 * b,
        0.0193308187 * r + 0.1191947798 * g + 0.9505321522 * b
    ];
}

function f(t) {
    return t > 0.008856451679 ? Math.cbrt(t) : (903.2962962963 * t + 16) / 116;
}

function xyzToLab(x, y, z) {
    var fx = f(x / WP[0]);
    var fy = f(y / WP[1]);
    var fz = f(z / WP[2]);
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

function inGamut(lin) {
    return lin[0] >= -0.0001 && lin[0] <= 1.0001
        && lin[1] >= -0.0001 && lin[1] <= 1.0001
        && lin[2] >= -0.0001 && lin[2] <= 1.0001;
}

function solveL(hue, chroma, tone) {
    var hr = hue * Math.PI / 180;
    var ca = chroma * Math.cos(hr);
    var cb = chroma * Math.sin(hr);
    var lo = 0.0;
    var hi = 1.0;
    for (var i = 0; i < 18; i++) {
        var L = (lo + hi) / 2;
        var lin = oklabToLinear(L, ca, cb);
        if (!inGamut(lin)) {
            hi = L;
            continue;
        }
        var xyz = linearToXyz(lin[0], lin[1], lin[2]);
        var lab = xyzToLab(xyz[0], xyz[1], xyz[2]);
        if (lab[0] < tone) lo = L;
        else hi = L;
    }
    var L2 = (lo + hi) / 2;
    var lin2 = oklabToLinear(L2, ca, cb);
    if (!inGamut(lin2)) return null;
    return [linearToSrgb(lin2[0]), linearToSrgb(lin2[1]), linearToSrgb(lin2[2])];
}

function clamp255(v) {
    return Math.max(0, Math.min(255, Math.round(v * 255)));
}

function lchToRgb(hue, chroma, tone) {
    var lo = 0.0;
    var hi = Math.max(chroma, 0.0001);
    for (var i = 0; i < 14; i++) {
        var mid = (lo + hi) / 2;
        if (solveL(hue, mid, tone) !== null) lo = mid;
        else hi = mid;
    }
    var res = solveL(hue, lo, tone);
    if (res === null) res = solveL(hue, 0, tone);
    if (res === null) return [128, 128, 128];
    return [clamp255(res[0]), clamp255(res[1]), clamp255(res[2])];
}

function toHex(rgb) {
    var s = "#";
    for (var i = 0; i < 3; i++) {
        var h = rgb[i].toString(16);
        if (h.length < 2) h = "0" + h;
        s += h;
    }
    return s;
}

function seedInfo(rgb) {
    var ok = rgbToOklab(rgb[0], rgb[1], rgb[2]);
    var hue = Math.atan2(ok[2], ok[1]) * 180 / Math.PI;
    if (hue < 0) hue += 360;
    var chroma = Math.sqrt(ok[1] * ok[1] + ok[2] * ok[2]) * 100;
    var xyz = linearToXyz(
        srgbToLinear(rgb[0]),
        srgbToLinear(rgb[1]),
        srgbToLinear(rgb[2])
    );
    var lab = xyzToLab(xyz[0], xyz[1], xyz[2]);
    return { hue: hue, chroma: chroma, tone: lab[0] };
}

function tonal(hue, chroma) {
    var out = {};
    for (var t = 0; t <= 100; t += 1) out[t] = toHex(lchToRgb(hue, chroma, t));
    return out;
}

var cacheKey = "";
var cacheVal = null;

function generateScheme(rgb, dark) {
    var key = rgb.join(",") + (dark ? "d" : "l");
    if (key === cacheKey && cacheVal !== null) return cacheVal;

    var info = seedInfo(rgb);
    var h = info.hue;
    var c = Math.max(info.chroma, 18);

    var p = tonal(h, c);
    var s = tonal(h, Math.max(c - 32, c * 0.5));
    var t = tonal((h + 60) % 360, Math.max(c - 32, c * 0.5));
    var n = tonal(h, 4);
    var nv = tonal(h, 8);
    var e = tonal(25, 84);

    var r = {};
    if (dark) {
        r.primary = p[80]; r.onPrimary = p[20];
        r.primaryContainer = p[30]; r.onPrimaryContainer = p[90];
        r.secondary = s[80]; r.onSecondary = s[20];
        r.secondaryContainer = s[30]; r.onSecondaryContainer = s[90];
        r.tertiary = t[80]; r.onTertiary = t[20];
        r.tertiaryContainer = t[30]; r.onTertiaryContainer = t[90];
        r.error = e[80]; r.onError = e[20];
        r.errorContainer = e[30]; r.onErrorContainer = e[90];
        r.background = n[10]; r.onBackground = n[90];
        r.surface = n[6]; r.onSurface = n[90];
        r.surfaceVariant = nv[30]; r.onSurfaceVariant = nv[80];
        r.outline = nv[60]; r.outlineVariant = nv[30];
        r.shadow = n[0]; r.scrim = n[0];
        r.inverseSurface = n[90]; r.inverseOnSurface = n[20];
        r.inversePrimary = p[40];
        r.surfaceDim = n[6]; r.surfaceBright = n[24];
        r.surfaceContainerLowest = n[4]; r.surfaceContainerLow = n[10];
        r.surfaceContainer = n[12]; r.surfaceContainerHigh = n[17];
        r.surfaceContainerHighest = n[22];
    } else {
        r.primary = p[40]; r.onPrimary = p[100];
        r.primaryContainer = p[90]; r.onPrimaryContainer = p[10];
        r.secondary = s[40]; r.onSecondary = s[100];
        r.secondaryContainer = s[90]; r.onSecondaryContainer = s[10];
        r.tertiary = t[40]; r.onTertiary = t[100];
        r.tertiaryContainer = t[90]; r.onTertiaryContainer = t[10];
        r.error = e[40]; r.onError = e[100];
        r.errorContainer = e[90]; r.onErrorContainer = e[10];
        r.background = n[99]; r.onBackground = n[10];
        r.surface = n[98]; r.onSurface = n[10];
        r.surfaceVariant = nv[90]; r.onSurfaceVariant = nv[30];
        r.outline = nv[50]; r.outlineVariant = nv[80];
        r.shadow = n[0]; r.scrim = n[0];
        r.inverseSurface = n[20]; r.inverseOnSurface = n[95];
        r.inversePrimary = p[80];
        r.surfaceDim = n[87]; r.surfaceBright = n[98];
        r.surfaceContainerLowest = n[100]; r.surfaceContainerLow = n[96];
        r.surfaceContainer = n[94]; r.surfaceContainerHigh = n[92];
        r.surfaceContainerHighest = n[90];
    }
    r.__hue = String(Math.round(h));
    r.__chroma = String(Math.round(c));

    cacheKey = key;
    cacheVal = r;
    return r;
}
