import QtQuick 2.15
import QtTest 1.3
import "../../shared/utils/ThemeColor.js" as ThemeColor
import "../../shared/utils/ThemePalette.js" as ThemePalette
import "../../shared/utils/TemplateExpr.js" as TemplateExpr

// P4 theme-contract golden master. Fixtures under tests/fixtures/theme are
// deterministic ffmpeg images plus Noctalia 5.2.1 (MIT) reference outputs;
// regeneration commands live in fixtures/theme/README.md.
TestCase {
    name: "ThemeContract"

    readonly property var goldenFiles: ["solid-tonal-spot", "gradient-tonal-spot", "solid-content",
        "gradient-content"]
    property var _cache: ({})

    function loadGolden(name) {
        if (!_cache[name]) {
            const xhr = new XMLHttpRequest();
            xhr.open("GET", "../fixtures/theme/golden/" + name + ".json", false);
            xhr.send();
            _cache[name] = JSON.parse(xhr.responseText);
        }
        return _cache[name];
    }

    function strippedPalette(section) {
        const out = {};
        for (const k in section) {
            if (!k.startsWith("terminal") && k !== "hover" && k !== "on_hover")
                out[k] = section[k];
        }
        return out;
    }

    // CIEDE2000 (Sharma et al. implementation) — the tolerance unit of the
    // computed-token contract.
    function deltaE00(hexA, hexB) {
        function lab(hex) {
            const argb = ThemeColor.argbFromHex(hex);
            const r = ThemeColor.linearized((argb >> 16) & 255);
            const g = ThemeColor.linearized((argb >> 8) & 255);
            const b = ThemeColor.linearized(argb & 255);
            const x = 0.41233895 * r + 0.35762064 * g + 0.18051042 * b;
            const y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            const z = 0.01932141 * r + 0.11916382 * g + 0.95034478 * b;
            const f = t => t > 0.008856 ? Math.pow(t, 1 / 3) : 7.787 * t + 16 / 116;
            const fx = f(x / 95.047), fy = f(y / 100.0), fz = f(z / 108.883);
            return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
        }
        const a = lab(hexA), b = lab(hexB);
        const C1 = Math.hypot(a[1], a[2]), C2 = Math.hypot(b[1], b[2]);
        const Cb = (C1 + C2) / 2;
        const G = 0.5 * (1 - Math.sqrt(Math.pow(Cb, 7) / (Math.pow(Cb, 7) + Math.pow(25, 7))));
        const a1p = (1 + G) * a[1], a2p = (1 + G) * b[1];
        const C1p = Math.hypot(a1p, a[2]), C2p = Math.hypot(a2p, b[2]);
        const h1p = C1p ? (Math.atan2(a[2], a1p) * 180 / Math.PI + 360) % 360 : 0;
        const h2p = C2p ? (Math.atan2(b[2], a2p) * 180 / Math.PI + 360) % 360 : 0;
        const dLp = b[0] - a[0], dCp = C2p - C1p;
        let dhp = 0;
        if (C1p * C2p) {
            const d = h2p - h1p;
            dhp = Math.abs(d) <= 180 ? d : (d > 180 ? d - 360 : d + 360);
        }
        const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin(dhp * Math.PI / 360);
        const Lbp = (a[0] + b[0]) / 2, Cbp = (C1p + C2p) / 2;
        let hbp;
        if (C1p * C2p === 0) {
            hbp = h1p + h2p;
        } else if (Math.abs(h1p - h2p) <= 180) {
            hbp = (h1p + h2p) / 2;
        } else if (h1p + h2p < 360) {
            hbp = (h1p + h2p + 360) / 2;
        } else {
            hbp = (h1p + h2p - 360) / 2;
        }
        const T = 1 - 0.17 * Math.cos((hbp - 30) * Math.PI / 180) + 0.24 * Math.cos(2 * hbp * Math.PI / 180)
              + 0.32 * Math.cos((3 * hbp + 6) * Math.PI / 180) - 0.20 * Math.cos((4 * hbp - 63) * Math.PI
                                                                                 / 180);
        const dTheta = 30 * Math.exp(-Math.pow((hbp - 275) / 25, 2));
        const Rc = 2 * Math.sqrt(Math.pow(Cbp, 7) / (Math.pow(Cbp, 7) + Math.pow(25, 7)));
        const Sl = 1 + 0.015 * Math.pow(Lbp - 50, 2) / Math.sqrt(20 + Math.pow(Lbp - 50, 2));
        const Sc = 1 + 0.045 * Cbp;
        const Sh = 1 + 0.015 * Cbp * T;
        const Rt = -Math.sin(2 * dTheta * Math.PI / 180) * Rc;
        return Math.sqrt(Math.pow(dLp / Sl, 2) + Math.pow(dCp / Sc, 2) + Math.pow(dHp / Sh, 2) + Rt * (dCp
                                                                                                       / Sc) * (dHp
                                                                                                                / Sh));
    }

    function test_terminal_derivation_matches_golden() {
        for (let i = 0; i < goldenFiles.length; i++) {
            const golden = loadGolden(goldenFiles[i]);
            const modes = ["dark", "light"];
            for (let m = 0; m < modes.length; m++) {
                const mode = modes[m];
                const palette = strippedPalette(golden[mode]);
                const derived = ThemePalette.terminalTokens(palette, mode);
                // Every golden terminal token is derived; direct tokens are
                // byte-identical, computed light tokens within tolerance.
                for (const token in golden[mode]) {
                    if (!token.startsWith("terminal"))
                        continue;
                    verify(token in derived, goldenFiles[i] + "/" + mode + " missing " + token);
                    if (derived[token] === golden[mode][token])
                        continue;
                    const de = deltaE00(derived[token], golden[mode][token]);
                    verify(de <= 1.5, goldenFiles[i] + "/" + mode + "/" + token + " dE00=" + de.toFixed(3)
                           + " got " + derived[token] + " want " + golden[mode][token]);
                }
            }
        }
    }

    function test_noctalia_palette_roles_match_golden() {
        for (let i = 0; i < goldenFiles.length; i++) {
            const golden = loadGolden(goldenFiles[i]);
            const body = ThemePalette.noctaliaPaletteJson(strippedPalette(golden.dark), strippedPalette(
                                                              golden.light));
            const roles = {
                "mPrimary": "primary",
                "mOnPrimary": "on_primary",
                "mSecondary": "secondary",
                "mOnSecondary": "on_secondary",
                "mTertiary": "tertiary",
                "mOnTertiary": "on_tertiary",
                "mError": "error",
                "mOnError": "on_error",
                "mSurface": "surface",
                "mOnSurface": "on_surface",
                "mSurfaceVariant": "surface_variant",
                "mOnSurfaceVariant": "on_surface_variant",
                "mOutline": "outline",
                "mShadow": "shadow",
                "mHover": "hover",
                "mOnHover": "on_hover"
            };
            const modes = ["dark", "light"];
            for (let m = 0; m < modes.length; m++) {
                const mode = modes[m];
                for (const role in roles) {
                    compare(body[mode][role], golden[mode][roles[role]], goldenFiles[i] + "/" + mode + "/"
                            + role);

                }
                const terminal = body[mode]["terminal"];
                let count = 0;
                for (const token in terminal) {
                    const got = terminal[token];
                    const want = golden[mode]["terminal_" + token];
                    if (got === want) {
                        count++;
                        continue;
                    }
                    // Computed light variants (magenta/cyan) sit within the
                    // documented solver tolerance instead of byte equality.
                    verify(deltaE00(got, want) <= 1.5, goldenFiles[i] + "/" + mode + "/terminal/" + token
                           + " dE00=" + deltaE00(got, want).toFixed(3));
                    count++;
                }
                compare(count, 22, goldenFiles[i] + "/" + mode + " terminal count");
            }
        }
    }

    function tokenModel() {
        const golden = loadGolden("solid-tonal-spot");
        const colors = {};
        const modes = ["dark", "light"];
        for (let m = 0; m < modes.length; m++) {
            const mode = modes[m];
            const withTerminals = ThemePalette.paletteWithTerminals(strippedPalette(golden[mode]), mode);
            for (const token in withTerminals) {
                if (!colors[token])
                    colors[token] = {};
                colors[token][mode] = withTerminals[token];
            }
        }
        return colors;
    }

    function test_expression_formats() {
        const colors = tokenModel();
        compare(TemplateExpr.render("t", "{{colors.primary.default.hex}}", colors, "dark"),
                colors.primary.dark);
        compare(TemplateExpr.render("t", "{{ colors.surface.light.hex_stripped }}", colors, "dark"),
                colors.surface.light.replace("#", ""));
        compare(TemplateExpr.render("t", "{{colors.primary.dark.rgb_csv}}", colors, "dark"), "{{RGB}}".replace(
                    "{{RGB}}", rgbCsv(colors.primary.dark)));
        compare(TemplateExpr.render("t", "x{{colors.error.default.hex}}y", colors, "light"), "x"
                + colors.error.light + "y");
        compare(TemplateExpr.render("t", "color \"{{colors.primary.default.hex}}80\"", colors, "light"),
                "color \"" + colors.primary.light + "80\"");
        compare(TemplateExpr.render("t", "{{colors.terminal_normal_blue.default.hex}}", colors, "dark"),
                colors.terminal_normal_blue.dark);
    }

    function rgbCsv(hex) {
        const argb = ThemeColor.argbFromHex(hex);
        return ((argb >> 16) & 255) + "," + ((argb >> 8) & 255) + "," + (argb & 255);
    }

    function test_expression_rejects_out_of_subset() {
        const colors = tokenModel();
        const cases = [["<* for x in y *>{{colors.primary.default.hex}}<* endfor *>", "block directives"],
                       ["{{colors.primary.default.hex | lighten 10}}", "filters"],
                       ["{{palettes.primary.40.hex}}", "expected colors."], ["{{colors.nonsense.default.hex}}",
                                                                             "unknown color token"],
                       ["{{colors.primary.default.hsl_plus}}", "unknown format"],
                       ["{{colors.primary.default.hex", "unclosed"], ["{{mode}}", "expected colors."]];
        for (let i = 0; i < cases.length; i++) {
            let threw = "";
            try {
                TemplateExpr.render("t", cases[i][0], colors, "dark");
            } catch (e) {
                threw = String(e);
            }
            verify(threw !== "", "expression must fail loudly: " + cases[i][0]);
            verify(threw.indexOf(cases[i][1]) !== -1, "unexpected error for " + cases[i][0] + ": " + threw);
        }
    }
}
