"""Contract tests for shell/commons/Toml.js (pure QML/JS TOML parser and serializer)."""

import json
import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOML_JS_PATH = REPO_ROOT / "shell" / "commons" / "Toml.js"


def eval_toml_js(code_to_run: str) -> str:
    """Evaluate JavaScript using Node.js with Toml.js loaded."""
    wrapper = f"""
    const fs = require('fs');
    let code = fs.readFileSync({json.dumps(str(TOML_JS_PATH))}, 'utf-8');
    code = code.replace(/^\\.pragma\\s+library\\s*$/m, '');
    const Toml = new Function(code + '\\nreturn {{ parse, stringify }};')();
    {code_to_run}
    """
    res = subprocess.run(["node", "-e", wrapper], capture_output=True, text=True, check=True)
    return res.stdout


class TestTomlJs(unittest.TestCase):
    def test_toml_js_file_exists(self):
        self.assertTrue(TOML_JS_PATH.is_file(), "shell/commons/Toml.js must exist")

    def test_exports_parse_and_stringify(self):
        out = eval_toml_js("""
        console.log(JSON.stringify({
            hasParse: typeof Toml.parse === 'function',
            hasStringify: typeof Toml.stringify === 'function'
        }));
        """)
        data = json.loads(out)
        self.assertTrue(data.get("hasParse"))
        self.assertTrue(data.get("hasStringify"))

    def test_parse_valid_toml(self):
        out = eval_toml_js("""
        const tomlStr = `
        [theme]
        mode = "dark"
        cursorSize = 24
        enabled = true

        [theme.fonts]
        ui = "Google Sans Flex"
        mono = "JetBrains Mono"

        [dock]
        pinned = ["firefox", "kitty"]
        `;
        const res = Toml.parse(tomlStr);
        console.log(JSON.stringify(res));
        """)
        parsed = json.loads(out)
        self.assertEqual(parsed["theme"]["mode"], "dark")
        self.assertEqual(parsed["theme"]["cursorSize"], 24)
        self.assertTrue(parsed["theme"]["enabled"])
        self.assertEqual(parsed["theme"]["fonts"]["ui"], "Google Sans Flex")
        self.assertEqual(parsed["dock"]["pinned"], ["firefox", "kitty"])

    def test_stringify_and_roundtrip(self):
        out = eval_toml_js("""
        const sample = {
            theme: {
                mode: "dark",
                cursorSize: 24,
                fonts: {
                    ui: "Google Sans Flex",
                    mono: "JetBrains Mono"
                }
            },
            dock: {
                position: "bottom",
                iconSize: 48,
                magnification: true,
                pinned: ["firefox", "foot", "thunar"]
            },
            bar: {
                showValues: true,
                tray: {
                    pinnedItems: ["Fcitx"],
                    filterPassive: true
                }
            }
        };

        const serialized = Toml.stringify(sample);
        const reparsed = Toml.parse(serialized);
        console.log(JSON.stringify({
            serialized: serialized,
            matched: JSON.stringify(sample) === JSON.stringify(reparsed)
        }));
        """)
        data = json.loads(out)
        self.assertTrue(data.get("matched"), f"Roundtrip failed:\n{data.get('serialized')}")
        self.assertIn('[theme]', data["serialized"])
        self.assertIn('[dock]', data["serialized"])
        self.assertIn('[bar.tray]', data["serialized"])

    def test_parse_error_handling(self):
        out = eval_toml_js("""
        let caught = false;
        try {
            Toml.parse("invalid = [1, 2,");
        } catch (e) {
            caught = true;
        }
        console.log(JSON.stringify({ caught }));
        """)
        data = json.loads(out)
        self.assertTrue(data.get("caught"), "Syntax error must throw an exception")


if __name__ == "__main__":
    unittest.main()
