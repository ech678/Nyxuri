"""Contract tests for the plugin model.

Dependency resolution is tested against ``nyxuri.deploy.catalog``,
blueprint access against ``nyxuri.deploy.catalog``, and the plugin
record shape against ``nyxuri.state.store``.
"""

import json
import os
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

import nyxuri.system.env as core
from nyxuri.state import store
from nyxuri.deploy import catalog
from nyxuri.deploy.manifest import (
    discover_manifest_apps,
    invalidate_manifest_cache,
    load_manifest,
)
from nyxuri.deploy.catalog import resolve_order
from tests.utils import TempEnv


class TestPluginModelContract(unittest.TestCase):
    """KM0 contract integrity: ensures the plugin model invariants are verified."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.plugin_model_md = self.root_dir / "llms-wiki" / "plugin-model.md"

    def test_plugin_model_doc_exists_and_contains_canonical_terms(self):
        """llms-wiki/plugin-model.md must exist and carry the 3 canonical terms
        (vision §1 术语纪律: 插件 · manifest · 账本; the「源」concept is deleted)."""
        self.assertTrue(self.plugin_model_md.is_file(), "plugin-model.md must exist")
        content = self.plugin_model_md.read_text(encoding="utf-8")
        for term in ("插件", "内核", "manifest", "账本"):
            self.assertIn(term, content, f"Canonical term '{term}' missing in plugin-model.md")
        self.assertNotIn("| **源** |", content,
                         "the Source concept must stay deleted (R0-2: git URL 即源)")

    def test_four_canonical_verbs_documented(self):
        """The 4 minimal verbs (list, on, off, doctor) must be documented."""
        content = self.plugin_model_md.read_text(encoding="utf-8")
        for verb in ("list", "on", "off", "doctor"):
            self.assertIn(f"`{verb}`", content, f"Core verb '{verb}' must be documented")

    def test_vault_path_invariants(self):
        """Vault must point to ~/.local/state/nyxuri/vault/<plugin>/ as flat directory."""
        content = self.plugin_model_md.read_text(encoding="utf-8")
        self.assertIn("vault/<plugin>/", content)
        self.assertIn("纯文件平铺", content)

    def test_shell_coordination_invariants(self):
        """Kernel side keeps three facts; slot taxonomy lives in shell/AGENTS.md (KM4)."""
        content = self.plugin_model_md.read_text(encoding="utf-8")
        # The three kernel-side facts (§6, KM4 trim).
        self.assertIn("同一账本", content)
        self.assertIn("单一事件通道", content)
        self.assertIn("点分 ID", content)
        self.assertIn("quickshell ipc unit reload", content)
        self.assertIn("shell.<domain>", content)
        self.assertIn("只读投影", content)
        self.assertIn("绝对绝缘", content)
        # KM4 enforcement rows on the death list.
        self.assertIn("StateProjection", content)
        self.assertIn("plugins/theme/", content)
        # The migrated microkernel taxonomy now lives on the shell side.
        shell_agents = (self.plugin_model_md.parent.parent / "shell" / "AGENTS.md").read_text(
            encoding="utf-8")
        for term in ("微内核宿主", "六大几何插槽", "SlotHost", "Loader", "ActionGateway"):
            self.assertIn(term, shell_agents,
                          f"slot taxonomy must live in shell/AGENTS.md: {term}")


class TestKernelResolver(unittest.TestCase):
    """Pure topological resolution against the real nyxuri.resolver."""

    def test_dependency_resolver_topological_sort(self):
        """DAG resolution orders dependencies before dependents."""
        graph = {
            "waybar": ["niri"],
            "niri": [],
            "orbit-translate": ["wl-clipboard"],
            "wl-clipboard": [],
        }
        order = resolve_order(graph)
        self.assertLess(order.index("niri"), order.index("waybar"))
        self.assertLess(order.index("wl-clipboard"), order.index("orbit-translate"))

    def test_dependency_resolver_detects_cycles(self):
        """Cyclic plugin dependencies must raise ValueError."""
        cyclic_graph = {
            "a": ["b"],
            "b": ["a"],
        }
        with self.assertRaises(ValueError):
            resolve_order(cyclic_graph)

    def test_foreign_dependency_is_ignored(self):
        """Frozen behavior: deps pointing outside the graph don't stall resolution."""
        order = resolve_order({"app": ["not-a-plugin-yet"]})
        self.assertEqual(order, ["app"])


class TestKernelRegistry(unittest.TestCase):
    """Blueprint domain: add a directory, get a plugin — zero kernel code."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent

    def _stage_configs(self, ctx, spec: dict[str, str | None]) -> None:
        """Create plugin dirs under a temp plugins_src and point the env at it.

        spec maps plugin id -> manifest TOML text (None = bare dir, no manifest).
        The manifest name is ``manifest.toml`` (KM1 step-② cutover: the
        ``.module.toml`` sidecar is physically gone).
        """
        configs = ctx.home / "configs-src"
        configs.mkdir()
        for uid, toml_text in spec.items():
            plugin = configs / uid
            plugin.mkdir()
            if toml_text is not None:
                text = f'schemaVersion = 1\nid = "{uid}"\nkinds = ["config"]\n' + toml_text
                (plugin / "manifest.toml").write_text(text, encoding="utf-8")
        ctx.env.plugins_src = configs

    def test_zero_config_discovery(self):
        """A bare directory with no manifest is a first-class plugin."""
        with TempEnv() as ctx:
            self._stage_configs(ctx, {"bare-plugin": None})
            self.assertIn("bare-plugin", catalog.plugin_ids())
            m = catalog.load_plugin("bare-plugin")
            self.assertEqual(m.id, "bare-plugin")
            self.assertEqual(m.packages_repo, ["bare-plugin"])
            self.assertEqual(m.preserve, [])

    def test_real_repo_units_discovered(self):
        """The repo blueprint is scanned through the same registry."""
        with TempEnv() as ctx:
            ctx.env.plugins_src = self.root_dir / "plugins"
            ids = catalog.plugin_ids()
            self.assertIn("kitty", ids)
            self.assertEqual(catalog.load_plugin("kitty").id, "kitty")

    def test_manifest_dependencies_parsed(self):
        """Top-level `dependencies` is the plugin-dependency declaration."""
        with TempEnv() as ctx:
            self._stage_configs(ctx, {"shell": 'dependencies = ["base"]\n', "base": None})
            self.assertEqual(catalog.load_plugin("shell").dependencies, ["base"])
            self.assertEqual(catalog.load_plugin("base").dependencies, [])

    def test_dependency_graph_feeds_resolver(self):
        """Kernel integration: catalog graph -> resolver order, no coupling."""
        with TempEnv() as ctx:
            self._stage_configs(ctx, {"shell": 'dependencies = ["base"]\n', "base": None})
            order = resolve_order(catalog.dependency_graph())
            self.assertLess(order.index("base"), order.index("shell"))

    def test_unknown_unit_raises(self):
        with TempEnv() as ctx:
            self._stage_configs(ctx, {})
            with self.assertRaises(KeyError):
                catalog.load_plugin("ghost")


class TestThirdPartyRoot(unittest.TestCase):
    """S1 third-party data root: ~/.local/share/nyxuri/plugins/<id>/ (H4/H8).

    plugin-model.md §8 + manifest-schema.md 第三方章: ids derive from the raw
    directory name (full reverse-DNS), official blueprints shadow third-party
    ones, reserved namespaces are unclaimable, symlinks are rejected at the
    scan layer.
    """

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent

    def _stage_third_party(self, ctx, spec: dict[str, str | None]) -> Path:
        """Create plugin dirs under the temp third-party data root.

        spec maps plugin id -> manifest TOML body (None = bare dir).
        """
        data_plugins = ctx.env.data_dir / "plugins"
        data_plugins.mkdir(parents=True, exist_ok=True)
        for uid, toml_text in spec.items():
            plugin = data_plugins / uid
            plugin.mkdir()
            if toml_text is not None:
                text = f'schemaVersion = 1\nid = "{uid}"\nkinds = ["config"]\n' + toml_text
                (plugin / "manifest.toml").write_text(text, encoding="utf-8")
        return data_plugins

    def test_data_dir_xdg_policy(self):
        """data_dir follows XDG_DATA_HOME under home; outside-home falls back."""
        with TempEnv() as ctx:
            self.assertEqual(
                ctx.env.data_dir, ctx.home / ".local" / "share" / "nyxuri"
            )
            with patch.dict(
                os.environ, {"XDG_DATA_HOME": str(ctx.home / "xdg-data")}
            ):
                self.assertEqual(
                    core.Environment().data_dir, ctx.home / "xdg-data" / "nyxuri"
                )
            with patch.dict(os.environ, {"XDG_DATA_HOME": "/opt/elsewhere"}):
                self.assertEqual(
                    core.Environment().data_dir,
                    ctx.home / ".local" / "share" / "nyxuri",
                )

    def test_third_party_discovered_and_loaded(self):
        """A directory under the data root is a registry plugin, id = dirname."""
        with TempEnv() as ctx:
            data_plugins = self._stage_third_party(
                ctx, {"io.github.test.cool": None}
            )
            self.assertIn("io.github.test.cool", catalog.plugin_ids())
            self.assertEqual(catalog.load_plugin("io.github.test.cool").id,
                             "io.github.test.cool")
            self.assertEqual(
                catalog.plugin_dir("io.github.test.cool"),
                data_plugins / "io.github.test.cool",
            )

    def test_third_party_manifest_id_must_match_dir(self):
        """Same root-derived id rule as official roots: drift is a parse error."""
        with TempEnv() as ctx:
            self._stage_third_party(ctx, {"io.github.test.cool": None})
            mpath = (ctx.env.data_dir / "plugins" / "io.github.test.cool"
                     / "manifest.toml")
            mpath.write_text(
                'schemaVersion = 1\nid = "someone.else"\nkinds = ["config"]\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                catalog.load_plugin("io.github.test.cool")

    def test_official_blueprint_wins_shadow(self):
        """A same-named official blueprint shadows the third-party entry."""
        with TempEnv() as ctx:
            self._stage_third_party(ctx, {"kitty": None})
            self.assertEqual(
                catalog.plugin_dir("kitty"), ctx.env.plugins_src / "kitty"
            )

    def test_symlinked_plugin_is_invisible(self):
        """禁软链 at the scan layer: a symlinked plugin dir does not exist."""
        with TempEnv() as ctx:
            real = ctx.home / "outside-real-plugin"
            real.mkdir()
            (real / "manifest.toml").write_text(
                'schemaVersion = 1\nid = "io.github.test.link"\nkinds = ["config"]\n',
                encoding="utf-8",
            )
            link = self._stage_third_party(ctx, {}) / "io.github.test.link"
            link.symlink_to(real)
            self.assertNotIn("io.github.test.link", catalog.plugin_ids())
            self.assertIsNone(catalog.plugin_dir("io.github.test.link"))
            with self.assertRaises(KeyError):
                catalog.load_plugin("io.github.test.link")

    def test_reserved_prefix_invisible_in_data_root(self):
        """Reserved namespaces are unclaimable from the third-party root."""
        with TempEnv() as ctx:
            self._stage_third_party(ctx, {"shell.evil": None, "nyxuri.evil": None})
            self.assertNotIn("shell.evil", catalog.plugin_ids())
            self.assertNotIn("nyxuri.evil", catalog.plugin_ids())

    def test_shell_namespace_still_decisive(self):
        """Regression: longest-prefix rule survives the third root."""
        with TempEnv() as ctx:
            self._stage_third_party(ctx, {"shell.fake": None})
            self.assertEqual(catalog.load_plugin("shell.bar").id, "shell.bar")
            self.assertNotIn("shell.fake", catalog.plugin_ids())

    def test_manifest_cache_invalidation(self):
        """invalidate_manifest_cache() makes the next discovery see new truth."""
        with TempEnv() as ctx:
            src = ctx.home / "cache-probe-src"
            src.mkdir()
            ctx.env.plugins_src = src
            # Populate the cache on an empty root, then add the plugin: the
            # second discovery must still serve the stale snapshot.
            self.assertEqual(discover_manifest_apps(), [])
            (src / "cache-probe").mkdir()
            self.assertEqual(discover_manifest_apps(), [])
            invalidate_manifest_cache()
            self.assertIn(
                "cache-probe", [name for name, _ in discover_manifest_apps()]
            )


class TestPluginStore(unittest.TestCase):
    """State domain: the five-field frozen plugin record (plugin-model.md §3)."""

    def test_unit_record_frozen_shape(self):
        """A record carries exactly the five frozen fields and persists."""
        with TempEnv() as ctx:
            rec = store.set_plugin("kitty", state="enabled", form="default",
                                  files={"kitty.conf": "abc123"})
            self.assertEqual(
                set(rec),
                {"state", "form", "files", "vault", "updated"},
                "plugin records must not grow a sixth field",
            )
            self.assertEqual(rec["state"], "enabled")
            self.assertEqual(rec["files"], {"kitty.conf": "abc123"})
            self.assertIsNone(rec["vault"])
            self.assertTrue(rec["updated"])
            # persisted under the top-level `plugins` key (R0-1 rename)
            on_disk = json.loads((ctx.home / ".local/state/nyxuri/state.json").read_text())
            self.assertEqual(on_disk["plugins"]["kitty"]["form"], "default")
            self.assertEqual(store.get_plugin("kitty"), rec)
            self.assertEqual(store.all_plugins(), {"kitty": rec})

    def test_disabled_record_holds_vault_only_when_archived(self):
        """Amended rule (R0-2): a disabled record names its vault when — and
        only when — an archive exists. A `use`-only record (never enabled,
        nothing archived) is honest with vault=null; a real `off` always
        names the archive dir."""
        with TempEnv():
            rec = store.set_plugin("kitty", state="disabled")
            self.assertIsNone(rec["vault"], "never-enabled records have nothing archived")
            rec = store.set_plugin("kitty", state="disabled",
                                  vault="/state/nyxuri/vault/kitty")
            self.assertEqual(rec["state"], "disabled")

    def test_invalid_state_rejected(self):
        with TempEnv():
            with self.assertRaises(ValueError):
                store.set_plugin("kitty", state="half-open")

    def test_upsert_keeps_sibling_records(self):
        with TempEnv():
            store.set_plugin("kitty", state="enabled")
            store.set_plugin("fish", state="enabled")
            store.set_plugin("kitty", state="disabled", vault="/vault/kitty")
            self.assertEqual(store.get_plugin("fish")["state"], "enabled")
            self.assertEqual(store.get_plugin("kitty")["state"], "disabled")

    def test_legacy_shapes_migration_swept_at_r0_3(self):
        """R0-3 sweep: legacy ledger migration shims (units/presets/parts) are gone."""
        with TempEnv() as ctx:
            path = ctx.home / ".local/state/nyxuri/state.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "units": {
                    "kitty": {"state": "enabled", "preset": "default", "files": {}, "vault": None,
                              "updated": "2026-01-01T00:00:00+00:00"},
                },
                "presets": {"kitty": "transparent"},
            }, indent=2) + "\n", encoding="utf-8")

            # Canonical reader finds no 'plugins' key, returns None without rewrites
            self.assertIsNone(store.get_plugin("kitty"))
            on_disk = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("plugins", on_disk)
            self.assertIn("units", on_disk)

    def test_fresh_store_only_carries_new_shape(self):
        """New installs never produce the legacy keys or field names."""
        with TempEnv() as ctx:
            store.set_plugin("kitty", state="enabled")
            store.set_form_slot("kitty", "effects", "xray")
            on_disk = json.loads(
                (ctx.home / ".local/state/nyxuri/state.json").read_text(encoding="utf-8")
            )
            self.assertIn("plugins", on_disk)
            self.assertIn("forms", on_disk)
            self.assertNotIn("units", on_disk)
            self.assertNotIn("presets", on_disk)
            self.assertNotIn("parts", on_disk)

    def test_form_slot_choices_round_trip(self):
        with TempEnv():
            store.set_form_slot("niri", "effects", "xray")
            store.set_form_slot("niri", "glow", "glow")
            store.set_form_slot("kitty", "effects", "off")
            self.assertEqual(store.get_form_slots("niri"), {"effects": "xray", "glow": "glow"})
            self.assertEqual(store.get_form_slots("kitty"), {"effects": "off"})
            self.assertEqual(store.get_form_slots("ghost"), {})


if __name__ == "__main__":
    unittest.main()
