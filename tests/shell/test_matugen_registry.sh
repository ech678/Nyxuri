#!/usr/bin/env bash
# Black-box registry and palette-generation contract (P4): only inspect JSON
# responses and resulting files. No source/layout assertions; all writes are
# isolated. matugen is the extraction slot; template rendering lives in the
# shell's TemplateService and is deliberately out of scope here.
# Literal path and hook syntax is deliberately passed to the implementation.
# shellcheck disable=SC2016,SC2088
set -euo pipefail
shell_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../shell" && pwd)
command -v matugen >/dev/null || exit 77
command -v jq >/dev/null || exit 77
test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT
export HOME="$test_root/home with spaces"
export XDG_CONFIG_HOME="$HOME/config"
export NYXURI_SHELL_CONFIG_HOME="$XDG_CONFIG_HOME/nyxuri"
export NYXURI_SHELL_RUNTIME_HOME="$test_root/runtime"
export NYXURI_SHELL_GENERATED_HOME="$test_root/generated"
# The sandbox exports explicit NYXURI_SHELL_* paths, so a developer session's
# stray overrides cannot redirect the generation target.
mkdir -p "$HOME" "$HOME/.config/nyxuri/templates"
# The shared template pool is deployed to ~/.config/nyxuri/templates by the
# `theme` unit (KM4/P5 neutral pool); the sandbox fakes it so the builtin
# registry entries resolve like on a real installation. The registry uses
# literal ~ paths (parser expands $HOME).
for f in gtk-3.0.css gtk-4.0.css niri-glow-material-you.kdl palette.toml; do
    printf '/* shared pool fixture */\n' > "$HOME/.config/nyxuri/templates/$f"
done
# Fcitx5 skin template fixtures deployed by fcitx5-rime unit
mkdir -p "$HOME/.local/share/fcitx5/themes/nyxmellow/templates"
for f in theme.conf panel.svg highlight.svg; do
    printf '/* fcitx5 skin fixture */\n' > "$HOME/.local/share/fcitx5/themes/nyxmellow/templates/$f"
done
manager="$shell_root/scripts/theme/manage-matugen-templates.sh"
generator="$shell_root/scripts/theme/generate-matugen-colors.sh"
manage() { bash "$manager" "$@"; }
generate() { bash "$generator" --color '#6750a4' "$@"; }
assert() { if ! "$@"; then printf 'Assertion failed: %s\n' "$*" >&2; exit 1; fi; }
reject() {
    if manage "$@" > "$test_root/rejected.json"; then
        printf 'Expected rejection: %s\n' "$*" >&2; exit 1
    fi
    jq -e '.schemaVersion == 1 and .ok == false and (.error | length > 0)' "$test_root/rejected.json" >/dev/null
}

manage list > "$test_root/list.json"
jq -e '.errors == [] and ([.templates[] | select(.origin == "builtin")] | length == 10)
    and all(.templates[]; .valid)
    and any(.templates[]; .id == "kitty" and (.inputPath | test("kitty/kitty\\.conf$")))
    and any(.templates[]; .id == "fcitx5_theme" and (.inputPath | test("fcitx5/themes/nyxmellow/templates/theme\\.conf$")))
    and any(.templates[]; .id == "gtk3" and (.inputPath | test("nyxuri/templates/gtk-3\\.0\\.css$")))' \
    "$test_root/list.json" >/dev/null
assert test ! -e "$NYXURI_SHELL_CONFIG_HOME/matugen"

# One extraction writes both contract files; no application template is
# rendered by the generator (the shell renders them from the palettes).
generate > "$test_root/generated.jsonl"
jq -se 'any(.[]; .event == "core-ready") and .[-1].event == "finished"' "$test_root/generated.jsonl" >/dev/null
assert test -s "$NYXURI_SHELL_GENERATED_HOME/nyxuri/colors.json"
assert test -s "$NYXURI_SHELL_GENERATED_HOME/nyxuri/palette-modes.json"
jq -e '(keys | length == 50) and (.primary | test("^#[0-9a-f]{6}$"))
    and (.source_color == "#6750a4")' \
    "$NYXURI_SHELL_GENERATED_HOME/nyxuri/colors.json" >/dev/null
jq -e '.schemaVersion == 1 and .mode == "dark" and (.dark.primary | length == 7)
    and (.light.primary | length == 7) and (.source_color | length == 7)' \
    "$NYXURI_SHELL_GENERATED_HOME/nyxuri/palette-modes.json" >/dev/null

# Registration is structural; rendering belongs to the shell. The generator
# must therefore never execute hooks or write template outputs.
printf 'background = {{colors.primary.default.hex}}\n' > "$test_root/ghostty.conf"
hook='printf "hook ran\n" >> "$HOME/hook-ran"'
manage validate ghostty "$test_root/ghostty.conf" '~/ghostty/theme' "$hook" > /dev/null
assert test ! -e "$NYXURI_SHELL_CONFIG_HOME/matugen"
assert test ! -e "$HOME/hook-ran"
manage add ghostty "$test_root/ghostty.conf" '~/ghostty/theme' "$hook" > /dev/null
assert cmp "$test_root/ghostty.conf" "$NYXURI_SHELL_CONFIG_HOME/matugen/templates/ghostty.conf"
manage list | jq -e '.templates[] | select(.id == "ghostty") | .origin == "user" and .valid and .hasPostHook' >/dev/null
assert test ! -e "$HOME/ghostty/theme"
generate > /dev/null
assert test ! -e "$HOME/ghostty/theme"
assert test ! -e "$HOME/hook-ran"
# The mode flip changes the active palette, not any template output.
generate --mode light --scheme scheme-expressive > /dev/null
jq -e '.mode == "light" and .scheme == "scheme-expressive"' \
    "$NYXURI_SHELL_GENERATED_HOME/nyxuri/palette-modes.json" >/dev/null

reject add kitty "$test_root/ghostty.conf" '~/another' ''
reject add ghostty "$test_root/ghostty.conf" '~/another' ''
reject add '../escape' "$test_root/ghostty.conf" '~/another' ''
reject add injection "$test_root/ghostty.conf" '$(touch /tmp/nyxuri-should-not-exist)' ''
reject add injection "$test_root/ghostty.conf" '$OTHER/target' ''
reject add directory "$test_root" '~/another' ''

# Dotted IDs are emitted as one quoted TOML key, not a nested table.
manage add editor.custom "$test_root/ghostty.conf" '$HOME/editor/theme' '' > /dev/null
manage list | jq -e '.templates[] | select(.id == "editor.custom") | .valid' >/dev/null

cat >> "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml" <<'TOML'
[templates.missing]
input_path = "templates/not-found"
output_path = "~/missing/theme"
TOML
manage list | jq -e '.templates[] | select(.id == "missing") | .valid == false and (.error | length > 0)' >/dev/null
# A fresh process sees a manually added registration immediately.
cat >> "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml" <<'TOML'
[templates.manual]
input_path = "templates/ghostty.conf"
output_path = "~/manual/theme"
TOML
manage list | jq -e '.templates[] | select(.id == "manual") | .valid and .origin == "user"' >/dev/null

# Unsupported registry syntax cannot silently become an active template.
cp "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml" "$test_root/before"
cat >> "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml" <<'TOML'
[templates.inline]
foo = { input_path = "templates/ghostty.conf", output_path = "~/bad" }
TOML
manage list | jq -e '(.errors | length > 0) and any(.templates[]; .id == "inline" and .valid == false)' >/dev/null
cp "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml" "$test_root/invalid"
reject add cannot-add "$test_root/ghostty.conf" '~/another' ''
assert cmp "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml" "$test_root/invalid"
cp "$test_root/before" "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml"

manage remove manual > /dev/null
manage remove ghostty > /dev/null
assert test ! -e "$NYXURI_SHELL_CONFIG_HOME/matugen/templates/ghostty.conf"
manage list | jq -e 'all(.templates[]; .id != "ghostty" and .id != "manual")' >/dev/null
reject remove kitty
# An installed-style shell root locates its own package resources, independent
# of the source checkout. This does not install anything on the host.
installed="$test_root/package/shell"
mkdir -p "$installed/scripts"
cp -r "$shell_root/scripts/lib" "$shell_root/scripts/theme" "$installed/scripts/"
mkdir -p "$installed/commons/assets"
cp -r "$shell_root/commons/assets/templates" "$installed/commons/assets/templates"
bash "$installed/scripts/theme/manage-matugen-templates.sh" list | jq -e --arg prefix "$installed/commons/assets/templates/" 'all(.templates[] | select(.origin == "builtin" and (.id == "kitty" or .id == "btop" or .id == "starship")); .inputPath | startswith($prefix))' >/dev/null
bash "$installed/scripts/theme/generate-matugen-colors.sh" --color '#aabbcc' --mode light > /dev/null
assert test -s "$NYXURI_SHELL_GENERATED_HOME/nyxuri/colors.json"

# Arbitrary newly registered IDs scale without app-specific code paths.
for number in $(seq 1 100); do
    printf '\n[templates.application-%s]\ninput_path = "%s"\noutput_path = "~/application-%s/theme"\n' "$number" "$test_root/ghostty.conf" "$number" >> "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml"
done
manage list | jq -e '[.templates[] | select(.id | startswith("application-"))] | length == 100 and all(.[]; .valid)' >/dev/null

python3 -c "import base64, pathlib; pathlib.Path('$test_root/test.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))"
bash "$generator" --image "$test_root/test.png" > /dev/null
assert test -s "$NYXURI_SHELL_GENERATED_HOME/nyxuri/colors.json"

# A registration with no input can still be removed without touching output.
cat >> "$NYXURI_SHELL_CONFIG_HOME/matugen/config.toml" <<'TOML'
[templates.no-input]
output_path = "~/keep-this-output"
TOML
printf 'keep' > "$HOME/keep-this-output"
manage remove no-input > /dev/null
assert test -s "$HOME/keep-this-output"

printf 'Palette registry integration passed\n'
