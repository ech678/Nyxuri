"""Contract tests for the KM0 plugin model and the KM1 kernel modules.

The Kahn reference copy is retired (plugin-model.md §7, KM1 step ①):
dependency resolution is tested against the real ``nyxuri.kernel.resolver``,
blueprint access against ``nyxuri.kernel.registry``, and the five-field plugin
record shape against ``nyxuri.kernel.ledger``.
"""

import json
import tomllib
import unittest
from pathlib import Path

from nyxuri.kernel import ledger, registry
from nyxuri.deploy.manifest import load_manifest
from nyxuri.kernel.resolver import resolve_order
from tests.utils import TempEnv


class TestPluginModelContract(unittest.TestCase):
    """KM0 contract integrity: ensures the plugin model invariants are verified."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.plugin_model_md = self.root_dir / "llms-wiki" / "plugin-model.md"

    def test_unit_model_doc_exists_and_contains_canonical_terms(self):
        """llms-wiki/plugin-model.md must exist and contain the 4 canonical terms."""
        self.assertTrue(self.plugin_model_md.is_file(), "plugin-model.md must exist")
        content = self.plugin_model_md.read_text(encoding="utf-8")
        for term in ("插件", "内核", "源", "manifest"):
            self.assertIn(term, content, f"Canonical term '{term}' missing in plugin-model.md")

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
        self.assertIn("units/theme/", content)
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
                (plugin / "manifest.toml").write_text(toml_text, encoding="utf-8")
        ctx.env.plugins_src = configs

    def test_zero_config_discovery(self):
        """A bare directory with no manifest is a first-class plugin."""
        with TempEnv() as ctx:
            self._stage_configs(ctx, {"bare-plugin": None})
            self.assertIn("bare-plugin", registry.plugin_ids())
            m = registry.load_plugin("bare-plugin")
            self.assertEqual(m.name, "bare-plugin")
            self.assertEqual(m.packages_repo, ["bare-plugin"])
            self.assertEqual(m.preserve, [])

    def test_real_repo_units_discovered(self):
        """The repo blueprint is scanned through the same registry."""
        with TempEnv() as ctx:
            ctx.env.plugins_src = self.root_dir / "plugins"
            ids = registry.plugin_ids()
            self.assertIn("kitty", ids)
            self.assertEqual(registry.load_plugin("kitty").name, "kitty")

    def test_manifest_dependencies_parsed(self):
        """Top-level `dependencies` is the plugin-dependency declaration."""
        with TempEnv() as ctx:
            self._stage_configs(ctx, {"shell": 'dependencies = ["base"]\n', "base": None})
            self.assertEqual(registry.load_plugin("shell").dependencies, ["base"])
            self.assertEqual(registry.load_plugin("base").dependencies, [])

    def test_dependency_graph_feeds_resolver(self):
        """Kernel integration: registry graph -> resolver order, no coupling."""
        with TempEnv() as ctx:
            self._stage_configs(ctx, {"shell": 'dependencies = ["base"]\n', "base": None})
            order = resolve_order(registry.dependency_graph())
            self.assertLess(order.index("base"), order.index("shell"))

    def test_unknown_unit_raises(self):
        with TempEnv() as ctx:
            self._stage_configs(ctx, {})
            with self.assertRaises(KeyError):
                registry.load_plugin("ghost")


class TestKernelLedger(unittest.TestCase):
    """State domain: the five-field frozen plugin record (plugin-model.md §3)."""

    def test_unit_record_frozen_shape(self):
        """A record carries exactly the five frozen fields and persists."""
        with TempEnv() as ctx:
            rec = ledger.set_plugin("kitty", state="enabled", form="default",
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
            self.assertEqual(ledger.get_plugin("kitty"), rec)
            self.assertEqual(ledger.all_plugins(), {"kitty": rec})

    def test_disabled_record_holds_vault_only_when_archived(self):
        """Amended rule (R0-2): a disabled record names its vault when — and
        only when — an archive exists. A `use`-only record (never enabled,
        nothing archived) is honest with vault=null; a real `off` always
        names the archive dir."""
        with TempEnv():
            rec = ledger.set_plugin("kitty", state="disabled")
            self.assertIsNone(rec["vault"], "never-enabled records have nothing archived")
            rec = ledger.set_plugin("kitty", state="disabled",
                                  vault="/state/nyxuri/vault/kitty")
            self.assertEqual(rec["state"], "disabled")

    def test_invalid_state_rejected(self):
        with TempEnv():
            with self.assertRaises(ValueError):
                ledger.set_plugin("kitty", state="half-open")

    def test_upsert_keeps_sibling_records(self):
        with TempEnv():
            ledger.set_plugin("kitty", state="enabled")
            ledger.set_plugin("fish", state="enabled")
            ledger.set_plugin("kitty", state="disabled", vault="/vault/kitty")
            self.assertEqual(ledger.get_plugin("fish")["state"], "enabled")
            self.assertEqual(ledger.get_plugin("kitty")["state"], "disabled")

    def test_legacy_shapes_migrate_on_first_read(self):
        """A pre-R0-2 ledger converges in one atomic write, exactly once.

        Covers all three legacy shapes: the R0-1 ``units`` top key, the
        per-record ``preset`` field, and the ``presets``/``parts`` top dicts
        (the whole-axis mirror folds into records — synthesizing a disabled
        record for never-switched plugins — and slot choices regroup under
        ``forms``).
        """
        with TempEnv() as ctx:
            path = ctx.home / ".local/state/nyxuri/state.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "units": {
                    "kitty": {"state": "enabled", "preset": "default", "files": {}, "vault": None,
                              "updated": "2026-01-01T00:00:00+00:00"},
                    "fish": {"state": "enabled", "preset": "default", "files": {}, "vault": None,
                             "updated": "2026-01-01T00:00:00+00:00"},
                },
                "presets": {"kitty": "transparent", "starship": "plain"},
                "parts": {"niri:effects": "xray-blur", "niri:glow": "glow"},
            }, indent=2) + "\n", encoding="utf-8")

            rec = ledger.get_plugin("kitty")
            self.assertEqual(rec["state"], "enabled")
            self.assertEqual(rec["form"], "transparent",
                             "the legacy whole-axis mirror lands in the record")
            # never-switched plugins get an honest synthesized record
            starship = ledger.get_plugin("starship")
            self.assertEqual(starship["state"], "disabled")
            self.assertEqual(starship["form"], "plain")
            self.assertIsNone(starship["vault"])
            # slot choices regroup under `forms`
            self.assertEqual(ledger.get_form_slots("niri"),
                             {"effects": "xray-blur", "glow": "glow"})

            on_disk = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("units", on_disk)
            self.assertNotIn("presets", on_disk, "legacy top dicts must be gone after migration")
            self.assertNotIn("parts", on_disk)
            self.assertEqual(on_disk["plugins"]["kitty"]["form"], "transparent")
            self.assertIn("forms", on_disk)
            for rec in on_disk["plugins"].values():
                self.assertNotIn("preset", rec, "per-record preset field must be renamed")

            # idempotent: further writes neither resurrect nor re-rename
            ledger.set_plugin("kitty", state="disabled", vault="/vault/kitty")
            on_disk = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("units", on_disk)
            self.assertNotIn("presets", on_disk)
            self.assertEqual(on_disk["plugins"]["kitty"]["state"], "disabled")
            self.assertEqual(ledger.get_form_slots("niri")["effects"], "xray-blur")

    def test_fresh_ledger_only_carries_new_shape(self):
        """New installs never produce the legacy keys or field names."""
        with TempEnv() as ctx:
            ledger.set_plugin("kitty", state="enabled")
            ledger.set_form_slot("kitty", "effects", "xray")
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
            ledger.set_form_slot("niri", "effects", "xray")
            ledger.set_form_slot("niri", "glow", "glow")
            ledger.set_form_slot("kitty", "effects", "off")
            self.assertEqual(ledger.get_form_slots("niri"), {"effects": "xray", "glow": "glow"})
            self.assertEqual(ledger.get_form_slots("kitty"), {"effects": "off"})
            self.assertEqual(ledger.get_form_slots("ghost"), {})


if __name__ == "__main__":
    unittest.main()
