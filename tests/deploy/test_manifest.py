"""Contract tests for manifest.toml plugin manifests and plugin discovery.

Covers the schemaVersion-1 vocabulary (manifest-schema.md): schema defaults
(no file), the closed word table, identity fields, ui kinds / entryPoints,
settings & actions declarations, target plugins, and discovery filters.
"""

import tempfile
import unittest
import unittest.mock
from pathlib import Path

import tomllib

import nyxuri.deploy.manifest as manifest
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import io


def _newform(plugin_id: str, body: str = "", kinds: str = '["config"]') -> str:
    """New-form manifest text: identity block + plugin-specific body."""
    return f'schemaVersion = 1\nid = "{plugin_id}"\nkinds = {kinds}\n' + body


class TestManifestDefaults(unittest.TestCase):
    """No manifest file → every default derived from the plugin dir name."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        # Synthetic configs tree so we control layout precisely.
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def _write(self, rel: str, content: str = "") -> Path:
        p = self.env.plugins_src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def _mkdir(self, rel: str) -> Path:
        d = self.env.plugins_src / rel
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_dir_unit_no_manifest_full_defaults(self):
        kitty = self._mkdir("kitty")
        (kitty / "kitty.conf").write_text("# conf")
        m = manifest.load_manifest(kitty)
        self.assertEqual(m.id, "kitty")
        self.assertEqual(m.kinds, ["config"])
        self.assertEqual(m.packages_repo, ["kitty"])
        self.assertEqual(m.packages_aur, [])
        self.assertEqual(m.preserve, [])
        self.assertEqual(m.chmod, [])
        self.assertEqual(m.label, "kitty")
        self.assertFalse(m.is_optional)
        self.assertEqual(m.target, "")
        self.assertTrue(m.is_deployable)

    def test_manifest_only_dir_not_deployable(self):
        # A dir whose only entry is manifest.toml → declaration-only unit
        # (greeter 形态：装包 + hooks + 落账，磁盘上没有生活区).
        plugin = self._mkdir("someunit")
        (plugin / "manifest.toml").write_text(_newform("someunit", "optional = true\n"))
        m = manifest.load_manifest(plugin)
        self.assertFalse(m.is_deployable)
        self.assertTrue(m.is_optional)
        self.assertEqual(m.packages_repo, ["someunit"])

    def test_dir_with_manifest_plus_config_is_deployable(self):
        niri = self._mkdir("niri")
        (niri / "config.kdl").write_text("# conf")
        (niri / "manifest.toml").write_text(_newform("niri", 'preserve = ["monitor.kdl"]\n'))
        m = manifest.load_manifest(niri)
        self.assertTrue(m.is_deployable)
        self.assertEqual(m.preserve, ["monitor.kdl"])

    def test_stray_top_level_file_is_not_a_unit(self):
        # configs/ is flat: every plugin is a directory. Stray files are ignored.
        self._write("stray.toml", "# junk")
        names = [n for n, _ in manifest.discover_manifest_apps()]
        self.assertNotIn("stray.toml", names)


class TestSchemaGate(unittest.TestCase):
    """S0-2 word table: identity fields, closed vocabulary, ui kinds."""

    def setUp(self):
        self._sandbox = tempfile.TemporaryDirectory()
        self.root = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()

    def _plugin(self, rel: str, text: str, entry: str = "") -> Path:
        plugin = self.root / rel
        plugin.mkdir(parents=True)
        (plugin / "manifest.toml").write_text(text, encoding="utf-8")
        if entry:
            (plugin / entry).write_text("// entry\n", encoding="utf-8")
        return plugin

    def test_schema_version_is_required_and_exact(self):
        plugin = self._plugin("bare", 'id = "bare"\nkinds = ["config"]\n')
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            manifest.load_manifest(plugin)
        plugin = self._plugin("future", 'schemaVersion = 2\nid = "future"\nkinds = ["config"]\n')
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            manifest.load_manifest(plugin)

    def test_id_must_match_the_registry_id(self):
        plugin = self._plugin("drift", _newform("other"))
        with self.assertRaisesRegex(ValueError, "registry id"):
            manifest.load_manifest(plugin)
        # The namespace prefix is part of the derived id (shell.* roots).
        (plugin / "manifest.toml").write_text(_newform("shell.drift"), encoding="utf-8")
        m = manifest.load_manifest(plugin, namespace="shell.")
        self.assertEqual(m.id, "shell.drift")

    def test_unknown_keys_are_a_parse_error(self):
        plugin = self._plugin("alien", _newform("alien", "warp = true\n"))
        with self.assertRaisesRegex(ValueError, "closed vocabulary"):
            manifest.load_manifest(plugin)

    def test_retired_keys_raise_on_parse(self):
        # 执法断言（KM1：删除不寄生于新增）：供给面处决的 ``deploy``/``detect``
        # 与杀词并轨的 ``runtime``/``merge`` 退役后，声明即解析错误。
        for key, value in (("deploy", "false"), ("detect", '"foo"'),
                           ("runtime", "true"), ("merge", "true")):
            plugin = self._plugin(f"dead-{key}", f"{key} = {value}\n")
            with self.assertRaises(ValueError, msg=key):
                manifest.load_manifest(plugin)

    def test_kinds_are_required_and_closed(self):
        plugin = self._plugin("nokinds", "schemaVersion = 1\nid = \"nokinds\"\n")
        with self.assertRaisesRegex(ValueError, "kinds"):
            manifest.load_manifest(plugin)
        plugin = self._plugin("alien-kind", _newform("alien-kind", kinds='["warp"]'))
        with self.assertRaisesRegex(ValueError, "unknown kind"):
            manifest.load_manifest(plugin)
        plugin = self._plugin("dup-kind", _newform("dup-kind", kinds='["config", "config"]'))
        with self.assertRaisesRegex(ValueError, "duplicate kinds"):
            manifest.load_manifest(plugin)

    def test_entry_points_cover_exactly_the_ui_kinds(self):
        plugin = self._plugin("panel", _newform("panel", "", kinds='["overlay"]'),
                              entry="Panel.qml")
        with self.assertRaisesRegex(ValueError, "entryPoints"):
            manifest.load_manifest(plugin)  # declared no entry point
        plugin = self._plugin(
            "panel2",
            _newform("panel2", '[entryPoints]\noverlay = "Panel.qml"\n', kinds='["overlay"]'),
            entry="Panel.qml")
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.entry_points, {"overlay": "Panel.qml"})
        self.assertTrue(m.is_runtime, "ui kinds carry the ledger form")
        self.assertEqual(m.packages_repo, [], "ui kinds default to no packages")

    def test_entry_points_reject_escapes_and_missing_files(self):
        plugin = self._plugin(
            "escape",
            _newform("escape", '[entryPoints]\noverlay = "../../victim.qml"\n', kinds='["overlay"]'))
        with self.assertRaisesRegex(ValueError, "unsafe"):
            manifest.load_manifest(plugin)
        plugin = self._plugin(
            "ghost",
            _newform("ghost", '[entryPoints]\noverlay = "Ghost.qml"\n', kinds='["overlay"]'))
        with self.assertRaisesRegex(ValueError, "does not exist"):
            manifest.load_manifest(plugin)

    def test_morphology_is_config_only_vocabulary(self):
        plugin = self._plugin(
            "ui-morph",
            _newform("ui-morph", 'morphology = "merge"\n[entryPoints]\noverlay = "U.qml"\n',
                     kinds='["overlay"]'),
            entry="U.qml")
        with self.assertRaisesRegex(ValueError, "morphology"):
            manifest.load_manifest(plugin)
        plugin = self._plugin("config-morph",
                              _newform("config-morph", 'morphology = "merge"\n'))
        self.assertTrue(manifest.load_manifest(plugin).is_merge)

    def test_order_must_be_an_integer(self):
        plugin = self._plugin("bad-order", _newform("bad-order", 'order = "ten"\n'))
        with self.assertRaisesRegex(ValueError, "order"):
            manifest.load_manifest(plugin)

    def test_settings_declarations_weld_anchors_to_routes(self):
        body = (
            '[[settings]]\n'
            'id = "panel"\ntitle = "Panel"\ncontext = "PanelPage"\nicon = "widgets"\n'
            'source = "PanelPage.qml"\ndescription = "Panel options"\n'
            'group = "shell-ui"\norder = 10\n'
            '[[settings]]\n'
            'id = "panel.section.main"\nroute = "panel"\ntitle = "Main"\n'
            'context = "PanelPage"\nicon = "widgets"\n'
        )
        plugin = self._plugin("panel3", _newform("panel3", body), entry="PanelPage.qml")
        m = manifest.load_manifest(plugin)
        self.assertEqual([s["id"] for s in m.settings], ["panel", "panel.section.main"])
        self.assertEqual(m.settings[1]["route"], "panel")

    def test_settings_reject_orphans_duplicates_and_escapes(self):
        orphan = (
            '[[settings]]\n'
            'id = "panel.section"\nroute = "nowhere"\ntitle = "S"\n'
            'context = "C"\nicon = "i"\n'
        )
        plugin = self._plugin("orphan", _newform("orphan", orphan))
        with self.assertRaisesRegex(ValueError, "unknown route"):
            manifest.load_manifest(plugin)
        deep = (
            '[[settings]]\n'
            'id = "a"\ntitle = "A"\ncontext = "C"\nicon = "i"\n'
            'source = "A.qml"\ndescription = "d"\ngroup = "g"\n'
            '[[settings]]\n'
            'id = "a.b.c"\ntitle = "B"\ncontext = "C"\nicon = "i"\n'
            'source = "B.qml"\ndescription = "d"\ngroup = "g"\n'
        )
        plugin = self._plugin("deep", _newform("deep", deep), entry="A.qml")
        (plugin / "B.qml").write_text("// b\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "nests deeper"):
            manifest.load_manifest(plugin)

    def test_actions_declarations_carry_search_metadata(self):
        body = (
            '[[actions]]\n'
            'id = "nyxuri:panel:open"\ntarget = "panel"\nmethod = "open"\n'
            'args = []\nconfirmation = "none"\navailability = "always"\n'
            '[actions.search]\n'
            'title = "Open panel"\ndescription = "Show the panel"\n'
            'context = "Actions"\nicon = "widgets"\naliases = ["panel"]\n'
        )
        plugin = self._plugin("panel4", _newform("panel4", body))
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.actions[0]["args"], [])
        self.assertEqual(m.actions[0]["search"]["aliases"], ["panel"])

    def test_actions_reject_unsafe_presets(self):
        base = (
            '[[actions]]\n'
            'id = "nyxuri:power-menu:off"\ntarget = "power-menu"\nmethod = "off"\n'
            'args = []\nconfirmation = "none"\n'
            '[actions.search]\n'
            'title = "Power off"\ndescription = "Shut down"\n'
            'context = "Actions"\nicon = "power"\n'
        )
        plugin = self._plugin("power", _newform("power", base))
        with self.assertRaisesRegex(ValueError, "confirmation"):
            manifest.load_manifest(plugin)
        bad = base.replace('confirmation = "none"', 'confirmation = "maybe"')
        plugin = self._plugin("power2", _newform("power2", bad))
        with self.assertRaises(ValueError):
            manifest.load_manifest(plugin)


class TestManifestOverrides(unittest.TestCase):
    """Each field can be overridden; fields are flat at the top level."""

    def setUp(self):
        self._sandbox = tempfile.TemporaryDirectory()
        self.root = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()

    def test_full_override(self):
        plugin = self.root / "xdp"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform(
            "xdp",
            'packages = ["xdg-desktop-portal"]\n'
            'preserve = ["portals.conf"]\n'
            'chmod = ["*.sh"]\n'
            'label = "XDG Portals"\n'))
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.packages_repo, ["xdg-desktop-portal"])
        self.assertEqual(m.packages_aur, [])
        self.assertEqual(m.preserve, ["portals.conf"])
        self.assertEqual(m.chmod, ["*.sh"])
        self.assertEqual(m.label, "XDG Portals")

    def test_optional_flag_parsed(self):
        plugin = self.root / "lutris"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform(
            "lutris",
            'optional = true\npackages = ["lutris"]\nlabel = "Lutris"\ncategory = "game"\n'))
        m = manifest.load_manifest(plugin)
        self.assertTrue(m.is_optional)
        self.assertEqual(m.category, "game")

    def test_flatpak_axis_survives_parsing(self):
        # The Flathub channel is transaction-level schema (qq/wechat/spotify
        # 供给面已处决，通道保留): an explicit empty repo list plus flatpak IDs
        # must survive parsing, or pacman would be handed a nonexistent name.
        plugin = self.root / "someflatpak"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform(
            "someflatpak",
            'packages = []\npackages_flatpak = ["com.example.App"]\n'))
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.packages_repo, [])
        self.assertEqual(m.packages_flatpak, ["com.example.App"])

    def test_target_single_file_unit(self):
        plugin = self.root / "starship"
        plugin.mkdir()
        (plugin / "starship.toml").write_text("# conf")
        (plugin / "manifest.toml").write_text(_newform("starship", 'target = "starship.toml"\n'))
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.target, "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertTrue(m.is_deployable)

    def test_xdg_target_resolves_through_pics_dir(self):
        """#144: `xdg:PICTURES/<rest>` resolves via the XDG Pictures dir."""
        plugin = self.root / "wallpapers"
        plugin.mkdir()
        (plugin / "fallback.webp").write_bytes(b"img")
        (plugin / "manifest.toml").write_text(_newform(
            "wallpapers",
            'target = "xdg:PICTURES/Wallpapers"\nmorphology = "merge"\n'))
        m = manifest.load_manifest(plugin)
        pics = self.root / "MyPictures"
        with unittest.mock.patch("nyxuri.core.get_pics_dir", return_value=pics):
            resolved = manifest.living_path(m, Path("/sandbox/.config"))
        self.assertEqual(resolved, pics / "Wallpapers")

    def test_xdg_target_resolves_all_standard_categories(self):
        """R0-4: xdg:<KIND>/<rest> resolves against any standard XDG user dir."""
        plugin = self.root / "media"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform("media", 'target = "xdg:MUSIC/Playlists"\n'))
        m = manifest.load_manifest(plugin)
        music = self.root / "MyMusic"
        with unittest.mock.patch("nyxuri.core.get_xdg_user_dir", return_value=music):
            resolved = manifest.living_path(m, Path("/sandbox/.config"))
        self.assertEqual(resolved, music / "Playlists")

    def test_xdg_target_rejects_unknown_kind(self):
        """R0-4: an unknown xdg: category is refused, never guessed."""
        plugin = self.root / "weird"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform("weird", 'target = "xdg:UNKNOWN_CAT/Playlists"\n'))
        m = manifest.load_manifest(plugin)
        with self.assertRaises(ValueError):
            manifest.living_path(m, Path("/sandbox/.config"))

    def test_xdg_target_rejects_path_traversal(self):
        """R0-4: xdg: targets attempting path traversal are rejected."""
        plugin = self.root / "escaped"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform("escaped", 'target = "xdg:PICTURES/../../etc/shadow"\n'))
        m = manifest.load_manifest(plugin)
        with self.assertRaises(ValueError):
            manifest.living_path(m, Path("/sandbox/.config"))

    def test_living_path_rejects_relative_containment_violation(self):
        """R0-4: target escaping ~/.config is rejected."""
        plugin = self.root / "escaped"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform("escaped", 'target = "../../escaped"\n'))
        with self.assertRaises(ValueError):
            manifest.load_manifest(plugin)

    def test_manifest_rejects_unsafe_preserve_and_hooks(self):
        """R0-4: preserve paths and hook filenames cannot traverse outside boundaries."""
        plugin = self.root / "bad"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform("bad", 'preserve = ["../../victim"]\n'))
        with self.assertRaises(ValueError):
            manifest.load_manifest(plugin)

        (plugin / "manifest.toml").write_text(_newform("bad", 'post_install = "../bad_hook"\n'))
        with self.assertRaises(ValueError):
            manifest.load_manifest(plugin)

    def test_preserve_values_parsed(self):
        plugin = self.root / "noctalia"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform(
            "noctalia",
            'preserve_values = { "noctalia-config.toml" = ["enable_ddcutil"] }\n'))
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.preserve_values, {"noctalia-config.toml": ["enable_ddcutil"]})
        self.assertEqual(m.preserve, [])

    def test_preserve_values_defaults_to_empty(self):
        plugin = self.root / "kitty"
        plugin.mkdir()
        (plugin / "kitty.conf").write_text("conf")
        self.assertEqual(manifest.load_manifest(plugin).preserve_values, {})

    def test_preserve_values_rejects_hostile_shapes(self):
        plugin = self.root / "weird2"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform(
            "weird2",
            'preserve_values = { "a.toml" = [], "b.toml" = "k", "c.toml" = [1, "k"] }\n'))
        self.assertEqual(manifest.load_manifest(plugin).preserve_values,
                         {"b.toml": ["k"], "c.toml": ["k"]})

    def test_preserve_values_non_table_falls_back(self):
        plugin = self.root / "odd"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform("odd", 'preserve_values = "nope"\n'))
        self.assertEqual(manifest.load_manifest(plugin).preserve_values, {})

    def test_aur_packages(self):
        plugin = self.root / "fcitx5-rime"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(_newform(
            "fcitx5-rime",
            'packages = ["fcitx5", "fcitx5-rime"]\npackages_aur = ["rime-ice-git"]\n'))
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.packages_repo, ["fcitx5", "fcitx5-rime"])
        self.assertEqual(m.packages_aur, ["rime-ice-git"])

    def test_bad_toml_raises(self):
        plugin = self.root / "bad"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text("this is = = not toml [[[\n")
        with self.assertRaises(tomllib.TOMLDecodeError):
            manifest.load_manifest(plugin)


class TestRealRepoManifests(unittest.TestCase):
    """The shipped manifests in the real configs/ tree parse as designed."""

    def setUp(self):
        manifest._MANIFEST_CACHE = None
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()
        manifest._MANIFEST_CACHE = None

    def test_niri_manifest(self):
        m = manifest.load_manifest(self.env.plugins_src / "niri")
        self.assertEqual(m.preserve, ["monitor.kdl", "effects.kdl", "effects_normal.kdl", "glow.kdl", "colors.kdl", "noctalia.kdl", "eyecare_temp"])
        self.assertEqual(m.chmod, ["scripts/*.sh", "scripts/*.py"])
        self.assertTrue(m.is_deployable)
        self.assertIn("effects", m.forms)
        self.assertIn("glow", m.forms)
        # dir name = package = binary → no packages override needed
        self.assertEqual(m.packages_repo, ["niri"])

    def test_noctalia_manifest_preserves_ddcutil(self):
        m = manifest.load_manifest(self.env.plugins_src / "noctalia")
        self.assertEqual(m.preserve_values,
                         {"noctalia-config.toml": ["enable_ddcutil"]})
        self.assertEqual(m.preserve, [])

    def test_starship_target_unit(self):
        m = manifest.load_manifest(self.env.plugins_src / "starship")
        self.assertEqual(m.target, "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertTrue(m.is_deployable)

    def test_retired_keys_are_dead_on_arrival(self):
        # 执法断言（KM1：删除不寄生于新增）：退役键不得再出现在任何在库
        # manifest——供给面处决的 ``deploy``/``detect`` 与杀词并轨的
        # ``runtime``/``merge`` 一并快照。
        roots = [self.env.plugins_src, self.env.shell_units_src]
        shipped = [p for root in roots for p in root.glob("*/manifest.toml")]
        self.assertTrue(shipped)
        for mpath in shipped:
            text = mpath.read_text()
            for dead in ("deploy", "detect", "runtime", "merge"):
                self.assertNotRegex(
                    text, rf"^\s*{dead}\s*=",
                    f"{mpath} still declares the retired key '{dead}'",
                )

    def test_every_shipped_manifest_is_new_form(self):
        """旧形态一处不留：两个蓝图根的 manifest 全部 schemaVersion 1 可解析。"""
        for root in (self.env.plugins_src, self.env.shell_units_src):
            for mpath in sorted(root.glob("*/manifest.toml")):
                namespace = "" if root == self.env.plugins_src else "shell."
                with self.subTest(manifest=str(mpath)):
                    m = manifest.load_manifest(mpath.parent, namespace=namespace)
                    self.assertEqual(m.id, namespace + mpath.parent.name)

    def test_optional_units_keep_manifest_declaration(self):
        opts = manifest.discover_optional_apps()
        for name in ("fcitx5-rime", "greeter", "mango", "zed"):
            self.assertIn(name, opts)

    def test_deployable_excludes_manifest_only(self):
        deployable = manifest.discover_deployable_apps()
        # The shipped config plugins are all present. `theme` is a merge plugin
        # (shared living area) — it deploys only through the transaction's
        # no-clobber path and never joins the atomic batch.
        for name in ("fastfetch", "fish", "kitty", "niri", "noctalia",
                     "starship", "xdg-desktop-portal", "zed", "mango",
                     "fcitx5-rime"):
            self.assertIn(name, deployable)
        self.assertNotIn("theme", deployable)
        merge_units = {name for name, m in manifest.discover_manifest_apps() if m.merge}
        self.assertIn("theme", merge_units)

    def test_stray_sidecar_files_are_gone(self):
        # KM1 ② enforcement: configs/ is a flat plugin directory — no sidecars.
        src = self.env.plugins_src
        self.assertFalse((src / ".optional-apps.toml").exists())
        self.assertFalse((src / "starship.toml").exists())
        self.assertEqual(list(src.glob("**/*.module.toml")), [])

    def test_fcitx5_rime_aur_packages(self):
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["fcitx5-rime"]
        self.assertEqual(m.packages_aur, ["rime-ice-git"])
        self.assertIn("fcitx5-rime", m.packages_repo)
        self.assertTrue(m.is_optional)
        # KM3: skin + profile live in the blueprint; hooks run the side domains.
        self.assertEqual(m.post_install, "activate")
        self.assertEqual(m.post_remove, "deactivate")
        self.assertIn("conf/classicui.conf", m.preserve)
        self.assertIn("profile", m.preserve)

    def test_privilege_declaration_parsed(self):
        """[privilege] declares root-level side effects (KM3: the greeter case)."""
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["greeter"]
        self.assertTrue(m.requires_root)
        self.assertTrue(any(p.startswith("/etc/greetd") for p in m.system_paths))
        self.assertEqual(m.post_install, "activate")
        self.assertEqual(m.post_remove, "deactivate")
        self.assertFalse(m.is_deployable, "manifest-only plugin stays non-deployable")
        # Plugins without the table default to unprivileged.
        self.assertFalse(manifests["kitty"].requires_root)
        self.assertEqual(manifests["kitty"].system_paths, [])

    def test_zed_optional_and_deployable(self):
        # zed ships config AND stays optional — both axes true at once.
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["zed"]
        self.assertTrue(m.is_optional)
        self.assertTrue(m.is_deployable)
        self.assertEqual(m.category, "dev")
        self.assertEqual(m.packages_repo, ["zed"])
        self.assertIn("zed", manifest.discover_optional_apps())
        self.assertIn("zed", manifest.discover_deployable_apps())

    def test_all_optional_units_categorized(self):
        known = {"dev", "system"}
        for _name, m in manifest.discover_manifest_apps():
            if m.is_optional:
                self.assertIn(m.category, known, f"{_name} has unknown category")

    def test_merge_unit_excluded_from_atomic_batch(self):
        # The wallpapers plugin is a shared living area: it must never join
        # the atomic swap batch (a swap would clobber user content).
        names = [name for name, _m in manifest.discover_manifest_apps()]
        self.assertIn("wallpapers", names)
        self.assertNotIn("wallpapers", manifest.discover_deployable_apps())

    def test_wallpaper_target_and_hook_resolve_xdg(self):
        """#144: manifest target and the pack hook share the XDG Pictures dir."""
        m = manifest.load_manifest_for("wallpapers")
        self.assertEqual(m.target, "xdg:PICTURES/Wallpapers")
        self.assertTrue(m.merge)

        hook = (self.env.plugins_src / "wallpapers" / "hooks" / "install-pack").read_text()
        self.assertIn('NYXURI_UNIT_DEST', hook)
        self.assertIn("xdg-user-dir PICTURES", hook)
        self.assertNotIn("$HOME/Pictures/Wallpapers", hook)

    def test_theme_declares_adw_gtk3_package(self):
        """#146: the GTK3 theme Nyxuri sets must ship with its provider package."""
        m = manifest.load_manifest_for("theme")
        self.assertIn("adw-gtk-theme", m.packages_repo)

    def test_real_niri_manifest_has_slot_axes(self):
        m = manifest.load_manifest_for("niri")
        self.assertIn("effects", m.forms)
        self.assertEqual(m.forms["effects"]["target"], "effects_normal.kdl")
        self.assertIn("glow", m.forms)
        self.assertEqual(m.forms["glow"]["target"], "glow.kdl")


class TestManifestForms(unittest.TestCase):
    """Forms table parsing in manifest.toml (allow/standalone/inheritance)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def _mkdir(self, rel: str) -> Path:
        d = self.env.plugins_src / rel
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_no_forms_table_defaults_to_safe(self):
        plugin = self._mkdir("myapp")
        (plugin / "config.conf").write_text("# conf")
        m = manifest.load_manifest(plugin)
        self.assertFalse(m.form_inherit)
        self.assertEqual(m.form_allow, [])
        self.assertEqual(m.form_standalone, [])
        self.assertEqual(m.form_include, [])
        self.assertEqual(m.form_exclude, [])

    def test_forms_table_parsed_correctly(self):
        plugin = self._mkdir("niri_test")
        (plugin / "config.kdl").write_text("# conf")
        (plugin / "manifest.toml").write_text(_newform("niri_test", """
preserve = ["monitor.kdl"]

[forms]
inherit = true
allow = ["glow", "compact"]
standalone = ["isolated"]
include = ["scripts/**", "*.kdl"]
exclude = ["scripts/debug.sh"]
"""))
        m = manifest.load_manifest(plugin)
        self.assertTrue(m.form_inherit)
        self.assertEqual(m.form_allow, ["glow", "compact"])
        self.assertEqual(m.form_standalone, ["isolated"])
        self.assertEqual(m.form_include, ["scripts/**", "*.kdl"])
        self.assertEqual(m.form_exclude, ["scripts/debug.sh"])

    def test_slot_targets_auto_included_in_preserve(self):
        plugin = self._mkdir("part_unit")
        (plugin / "config.kdl").write_text("# conf")
        (plugin / "manifest.toml").write_text(_newform("part_unit", """
preserve = ["explicit.kdl"]

[forms.theme]
target = "theme.kdl"

[forms.effects]
target = "effects.kdl"
"""))
        m = manifest.load_manifest(plugin)
        self.assertIn("explicit.kdl", m.preserve)
        self.assertIn("theme.kdl", m.preserve)
        self.assertIn("effects.kdl", m.preserve)
        # Ensure no duplicates if target was already explicitly declared
        (plugin / "manifest.toml").write_text(_newform("part_unit", """
preserve = ["theme.kdl"]

[forms.theme]
target = "theme.kdl"
"""))
        m2 = manifest.load_manifest(plugin)
        self.assertEqual(m2.preserve, ["theme.kdl"])


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestManifestCoercion(unittest.TestCase):

    def _sandbox(self, ctx):
        ctx.env.plugins_src = Path(tempfile.mkdtemp())
        return ctx.env.plugins_src

    def test_scalar_package_fields_become_single_element_lists(self):
        from nyxuri.deploy.manifest import load_manifest
        with TempEnv() as ctx:
            src = self._sandbox(ctx) / "demo"
            src.mkdir(parents=True)
            (src / "config.conf").write_text("# conf\n", encoding="utf-8")
            (src / "manifest.toml").write_text(_newform(
                "demo",
                'packages = "kitty"\npackages_aur = "foo-bar"\npreserve = "single.conf"\n',
            ), encoding="utf-8")
            m = _quiet(load_manifest, src)
            self.assertEqual(m.packages_repo, ["kitty"])
            self.assertEqual(m.packages_aur, ["foo-bar"])
            self.assertEqual(m.preserve, ["single.conf"])

    def test_scalar_forms_entry_is_dropped(self):
        from nyxuri.deploy.manifest import load_manifest
        with TempEnv() as ctx:
            src = self._sandbox(ctx) / "demo2"
            src.mkdir(parents=True)
            (src / "config.conf").write_text("# conf\n", encoding="utf-8")
            (src / "manifest.toml").write_text(_newform(
                "demo2", '[forms]\ngood = { target = "a.conf" }\nbad = "oops"\n'
            ), encoding="utf-8")
            m = _quiet(load_manifest, src)
            self.assertEqual(sorted(m.forms), ["good"])

    def test_empty_packages_list_stays_empty(self):
        from nyxuri.deploy.manifest import load_manifest
        with TempEnv() as ctx:
            src = self._sandbox(ctx) / "flatpak-only"
            src.mkdir(parents=True)
            (src / "manifest.toml").write_text(_newform(
                "flatpak-only", 'packages = []\npackages_flatpak = ["com.example.App"]\n'
            ), encoding="utf-8")
            m = _quiet(load_manifest, src)
            self.assertEqual(m.packages_repo, [])

    def test_malformed_manifest_does_not_break_discovery(self):
        from nyxuri.deploy.manifest import discover_manifest_apps
        with TempEnv() as ctx:
            sandbox = self._sandbox(ctx)
            bad = sandbox / "bad-plugin"
            bad.mkdir()
            (bad / "manifest.toml").write_text("not = = toml\n", encoding="utf-8")
            good = sandbox / "good-plugin"
            good.mkdir()
            (good / "config.conf").write_text("# conf\n", encoding="utf-8")
            apps = _quiet(discover_manifest_apps)
            self.assertIsInstance(apps, list)
            self.assertEqual([n for n, _ in apps], ["good-plugin"])


class TestMorphologyMatrix(unittest.TestCase):
    """R0-3 morphology matrix: runtime / merge / atomic / hook-only."""

    def test_morphology_auto_inference(self):
        with TempEnv() as ctx:
            sandbox = ctx.home / "plugins_sandbox"
            # 1. atomic
            p_atomic = sandbox / "p_atomic"
            p_atomic.mkdir(parents=True)
            (p_atomic / "config.conf").write_text("x = 1\n", encoding="utf-8")
            m_atomic = manifest.load_manifest(p_atomic)
            self.assertEqual(m_atomic.morphology, manifest.MORPHOLOGY_ATOMIC)
            self.assertTrue(m_atomic.is_atomic)
            self.assertFalse(m_atomic.is_hook_only)

            # 2. hook-only (no deployable files, only hooks/ or manifest)
            p_hook = sandbox / "p_hook"
            p_hook.mkdir(parents=True)
            (p_hook / "hooks").mkdir()
            (p_hook / "hooks" / "activate").write_text("#!/bin/sh\n", encoding="utf-8")
            (p_hook / "manifest.toml").write_text(_newform("p_hook", "optional = true\n"),
                                                  encoding="utf-8")
            m_hook = manifest.load_manifest(p_hook)
            self.assertEqual(m_hook.morphology, manifest.MORPHOLOGY_HOOK_ONLY)
            self.assertTrue(m_hook.is_hook_only)
            self.assertFalse(m_hook.is_atomic)

            # 3. merge (shared living area — the morphology word, no merge key)
            p_merge = sandbox / "p_merge"
            p_merge.mkdir(parents=True)
            (p_merge / "manifest.toml").write_text(_newform("p_merge", 'morphology = "merge"\n'),
                                                   encoding="utf-8")
            m_merge = manifest.load_manifest(p_merge)
            self.assertEqual(m_merge.morphology, manifest.MORPHOLOGY_MERGE)
            self.assertTrue(m_merge.is_merge)

            # 4. runtime (ui kinds carry the ledger form in their kinds)
            p_runtime = sandbox / "p_runtime"
            p_runtime.mkdir(parents=True)
            (p_runtime / "Unit.qml").write_text("// u\n", encoding="utf-8")
            (p_runtime / "manifest.toml").write_text(_newform(
                "p_runtime", '[entryPoints]\noverlay = "Unit.qml"\n', kinds='["overlay"]'),
                encoding="utf-8")
            m_runtime = manifest.load_manifest(p_runtime)
            self.assertEqual(m_runtime.morphology, manifest.MORPHOLOGY_RUNTIME)
            self.assertTrue(m_runtime.is_runtime)

    def test_explicit_morphology_declaration(self):
        with TempEnv() as ctx:
            sandbox = ctx.home / "plugins_sandbox"
            p = sandbox / "explicit"
            p.mkdir(parents=True)
            (p / "manifest.toml").write_text(_newform("explicit", 'morphology = "hook-only"\n'),
                                             encoding="utf-8")
            m = manifest.load_manifest(p)
            self.assertEqual(m.morphology, "hook-only")
            self.assertTrue(m.is_hook_only)

    def test_unsupported_morphology_raises(self):
        with TempEnv() as ctx:
            sandbox = ctx.home / "plugins_sandbox"
            p = sandbox / "bad_morph"
            p.mkdir(parents=True)
            (p / "manifest.toml").write_text(_newform("bad_morph", 'morphology = "alien"\n'),
                                             encoding="utf-8")
            with self.assertRaises(ValueError):
                manifest.load_manifest(p)


if __name__ == "__main__":
    unittest.main()
