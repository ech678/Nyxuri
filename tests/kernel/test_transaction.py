"""Kernel transaction tests (KM2): on/off atomic closure, Vault in/out,
white-paper wipe, doctor three-state audit, and the frozen kernel layering.

Every test runs inside TempEnv — the real ~/.config is never touched.
"""

import ast
import hashlib
import importlib
import json
import unittest
from pathlib import Path
from unittest import mock

from nyxuri.kernel import ledger, transaction
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import os
import re
from unittest.mock import patch



def _stage(ctx, spec):
    """Create plugin dirs under a temp plugins_src and point the env at it.

    spec maps plugin id -> {"manifest": toml text | None, "files": {rel: content}}.
    """
    configs = ctx.home / "configs-src"
    configs.mkdir(exist_ok=True)
    for uid, entry in spec.items():
        plugin = configs / uid
        plugin.mkdir(exist_ok=True)
        if entry.get("manifest") is not None:
            (plugin / "manifest.toml").write_text(entry["manifest"], encoding="utf-8")
        for rel, content in entry.get("files", {}).items():
            p = plugin / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    ctx.env.plugins_src = configs


class TestPluginOn(unittest.TestCase):
    """Enable transaction: resolve → preflight → swap → ledger → event."""

    def setUp(self):
        # Package preflight must never depend on the host machine's package
        # state; the missing-package paths re-patch it explicitly.
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_on_deploys_and_records_five_fields(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"kitty.conf": "font_size 11\n"}}})
            steps = transaction.plugin_on("kitty")
            self.assertEqual([s.ok for s in steps], [True], str(steps))
            dest = ctx.home / ".config/kitty/kitty.conf"
            self.assertTrue(dest.is_file())
            rec = ledger.get_plugin("kitty")
            self.assertEqual(set(rec), {"state", "preset", "files", "vault", "updated"})
            self.assertEqual(rec["state"], "enabled")
            self.assertEqual(rec["preset"], "default")
            self.assertIsNone(rec["vault"])
            self.assertEqual(
                rec["files"], {"kitty.conf": hashlib.sha256(dest.read_bytes()).hexdigest()}
            )

    def test_on_dependency_closure_enabled_first(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "shell": {"manifest": 'dependencies = ["base"]\n', "files": {"s.conf": "s"}},
                "base": {"files": {"b.conf": "b"}},
            })
            order = []
            real = ledger.set_plugin

            def spy(plugin_id, **kw):
                order.append(plugin_id)
                return real(plugin_id, **kw)

            with mock.patch.object(ledger, "set_plugin", spy):
                steps = transaction.plugin_on("shell")
            self.assertTrue(all(s.ok for s in steps), str(steps))
            self.assertEqual(order, ["base", "shell"])
            self.assertTrue((ctx.home / ".config/base/b.conf").is_file())
            self.assertTrue((ctx.home / ".config/shell/s.conf").is_file())
            self.assertEqual(ledger.get_plugin("base")["state"], "enabled")

    def test_on_missing_packages_aborts_without_touching_machine(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'packages = ["missing-pkg"]\n',
                                 "files": {"a.conf": "a"}}})
            with mock.patch.object(transaction, "missing_packages",
                                   return_value=["missing-pkg"]):
                steps = transaction.plugin_on("app")
            self.assertFalse(steps[0].ok)
            self.assertIn("missing-packages", steps[0].detail)
            self.assertIn("missing-pkg", steps[0].detail)
            self.assertFalse((ctx.home / ".config/app").exists())
            self.assertIsNone(ledger.get_plugin("app"))

    def test_on_injected_installer_unblocks_preflight(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'packages = ["missing-pkg"]\n',
                                 "files": {"a.conf": "a"}}})
            calls = []

            def installer(uid, pkgs):
                calls.append((uid, pkgs))
                return True

            with mock.patch.object(transaction, "missing_packages",
                                   side_effect=[["missing-pkg"], []]):
                steps = transaction.plugin_on("app", install_packages=installer)
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual(calls, [("app", ["missing-pkg"])])
            self.assertTrue((ctx.home / ".config/app/a.conf").is_file())

    def test_on_already_enabled_is_noop(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"kitty.conf": "x"}}})
            transaction.plugin_on("kitty")
            with mock.patch.object(transaction, "_phase_atomic_deployment",
                                   wraps=transaction._phase_atomic_deployment) as dep:
                steps = transaction.plugin_on("kitty")
            self.assertEqual(steps[0].detail, "already-enabled")
            dep.assert_not_called()

    def test_on_single_file_unit_roundtrip(self):
        """target= plugins ride the same transaction (deploy.py result-binding fix)."""
        with TempEnv() as ctx:
            _stage(ctx, {"starship": {"manifest": 'target = "starship.toml"\n',
                                      "files": {"starship.toml": "$schema\n"}}})
            steps = transaction.plugin_on("starship")
            self.assertTrue(steps[0].ok, str(steps))
            dest = ctx.home / ".config/starship.toml"
            self.assertTrue(dest.is_file())
            rec = ledger.get_plugin("starship")
            self.assertEqual(set(rec["files"]), {"starship.toml"})
            self.assertEqual(transaction.audit_plugins("starship"), {"starship": "Synced"})
            steps = transaction.plugin_off("starship")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertFalse(dest.exists())
            self.assertEqual(ledger.get_plugin("starship")["state"], "disabled")

    def test_unknown_unit_raises(self):
        with TempEnv() as ctx:
            _stage(ctx, {})
            with self.assertRaises(KeyError):
                transaction.plugin_on("ghost")
            with self.assertRaises(KeyError):
                transaction.plugin_off("ghost")


class TestPluginOff(unittest.TestCase):
    """Disable transaction: guard → vault in → white-paper wipe → ledger."""

    def setUp(self):
        # plugin_on setup steps must not depend on host package state either.
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_off_archives_custom_and_preserve_then_wipes(self):
        with TempEnv() as ctx:
            _stage(ctx, {"niri": {
                "manifest": 'preserve = ["monitor.kdl"]\n',
                "files": {"niri.conf": "spawn {}\n", "monitor.kdl": "output eDP-1\n"},
            }})
            transaction.plugin_on("niri")
            dest = ctx.home / ".config/niri"
            (dest / "theme__custom__.conf").write_text("my own\n")
            (dest / "monitor.kdl").write_text("output eDP-1 position 0 0\n")
            steps = transaction.plugin_off("niri")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertFalse(dest.exists(), "enabled area must be wiped to white paper")
            vault = ctx.home / ".local/state/nyxuri/vault/niri"
            self.assertEqual((vault / "theme__custom__.conf").read_text(), "my own\n")
            self.assertEqual((vault / "monitor.kdl").read_text(), "output eDP-1 position 0 0\n")
            rec = ledger.get_plugin("niri")
            self.assertEqual(rec["state"], "disabled")
            self.assertEqual(rec["files"], {})
            self.assertTrue(rec["vault"].endswith("vault/niri"))

    def test_off_blocked_by_enabled_dependents_without_cascade(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "panel": {"manifest": 'dependencies = ["shell"]\n', "files": {"p.conf": "p"}},
                "shell": {"manifest": 'dependencies = ["base"]\n', "files": {"s.conf": "s"}},
                "base": {"files": {"b.conf": "b"}},
            })
            transaction.plugin_on("panel")
            steps = transaction.plugin_off("base")
            self.assertFalse(steps[0].ok)
            self.assertIn("blocked-by-enabled-dependents", steps[0].detail)
            self.assertIn("panel", steps[0].detail)
            self.assertIn("shell", steps[0].detail)
            self.assertEqual(ledger.get_plugin("base")["state"], "enabled")
            self.assertTrue((ctx.home / ".config/base/b.conf").is_file())

    def test_off_cascade_disables_dependents_first(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "panel": {"manifest": 'dependencies = ["shell"]\n', "files": {"p.conf": "p"}},
                "shell": {"manifest": 'dependencies = ["base"]\n', "files": {"s.conf": "s"}},
                "base": {"files": {"b.conf": "b"}},
            })
            transaction.plugin_on("panel")
            order = []
            real = ledger.set_plugin

            def spy(plugin_id, **kw):
                order.append(plugin_id)
                return real(plugin_id, **kw)

            with mock.patch.object(ledger, "set_plugin", spy):
                steps = transaction.plugin_off("base", cascade=True)
            self.assertTrue(all(s.ok for s in steps), str(steps))
            self.assertEqual(order, ["panel", "shell", "base"])
            for uid in ("panel", "shell", "base"):
                self.assertEqual(ledger.get_plugin(uid)["state"], "disabled")
                self.assertFalse((ctx.home / f".config/{uid}").exists())

    def test_off_survives_foreign_files_and_reports_them(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            transaction.plugin_on("kitty")
            dest = ctx.home / ".config/kitty"
            (dest / "my-notes.txt").write_text("keep me\n")
            steps = transaction.plugin_off("kitty")
            self.assertTrue(steps[0].ok)
            self.assertIn("foreign-left: my-notes.txt", steps[0].detail)
            self.assertTrue((dest / "my-notes.txt").is_file(), "user files must never be eaten")
            self.assertFalse((dest / "k.conf").exists())
            self.assertEqual(transaction.audit_plugins("kitty"), {"kitty": "Ghost"})

    def test_off_without_ledger_wipes_blueprint_keeps_foreign(self):
        """No snapshot: blueprint-named files are withdrawn, foreign survive.

        A pre-ledger (v3-era) dest must never lose the user's personal files
        to an `off` (#139) — ownership falls back to blueprint names, and
        everything else survives, reported as foreign-left.
        """
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            dest = ctx.home / ".config/kitty"
            dest.mkdir(parents=True)
            (dest / "k.conf").write_text("deployed by old installer\n")
            (dest / "my-notes.txt").write_text("keep me\n")
            steps = transaction.plugin_off("kitty")
            self.assertTrue(steps[0].ok)
            self.assertFalse((dest / "k.conf").exists(), "blueprint-named files are ours to withdraw")
            self.assertTrue((dest / "my-notes.txt").is_file(), "user files must never be eaten")
            self.assertIn("foreign-left: my-notes.txt", steps[0].detail)

    def test_off_never_eats_unregistered_single_file(self):
        """Single-file plugin: a dest file outside the managed snapshot survives."""
        with TempEnv() as ctx:
            _stage(ctx, {"starship": {"manifest": 'target = "starship.toml"\n',
                                      "files": {"starship.toml": "$schema\n"}}})
            dest = ctx.home / ".config/starship.toml"
            dest.write_text("user's own\n", encoding="utf-8")
            steps = transaction.plugin_off("starship")
            self.assertTrue(steps[0].ok)
            self.assertIn("foreign-left: starship.toml", steps[0].detail)
            self.assertEqual(dest.read_text(), "user's own\n")

    def test_off_vaults_preserve_directory_and_restores_it(self):
        """A preserve DIRECTORY rides the Vault both ways (#139 field report):
        archived whole on off, restored before the next on."""
        with TempEnv() as ctx:
            _stage(ctx, {"fish": {
                "manifest": 'preserve = ["functions"]\n',
                "files": {"config.fish": "set -x PATH\n"},
            }})
            transaction.plugin_on("fish")
            dest = ctx.home / ".config/fish"
            (dest / "functions/fisher.fish").parent.mkdir(parents=True)
            (dest / "functions/fisher.fish").write_text("plugin\n", encoding="utf-8")
            self.assertTrue(
                transaction._is_user_owned("functions/fisher.fish",
                                           transaction.registry.load_plugin("fish")),
                "every file under a preserved directory is user-owned by prefix")

            steps = transaction.plugin_off("fish")
            self.assertTrue(steps[0].ok, str(steps))
            vault = ctx.home / ".local/state/nyxuri/vault/fish"
            self.assertEqual((vault / "functions/fisher.fish").read_text(), "plugin\n")
            self.assertFalse(dest.exists())

            transaction.plugin_on("fish")
            self.assertEqual((dest / "functions/fisher.fish").read_text(), "plugin\n",
                             "the preserved tree must ride the Vault back")

    def test_off_then_on_restores_vault_and_consumes_it(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            dest = ctx.home / ".config/kitty"
            transaction.plugin_on("kitty")
            (dest / "theme__custom__.conf").write_text("v1\n")
            transaction.plugin_off("kitty")
            self.assertFalse((dest / "theme__custom__.conf").exists())
            steps = transaction.plugin_on("kitty")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual((dest / "theme__custom__.conf").read_text(), "v1\n")
            vault = ctx.home / ".local/state/nyxuri/vault/kitty"
            self.assertFalse(vault.exists(), "archive must be consumed on restore")
            rec = ledger.get_plugin("kitty")
            self.assertEqual(rec["state"], "enabled")
            self.assertIsNone(rec["vault"])
            # deleted customs stay deleted: an empty archive must not resurrect
            (dest / "theme__custom__.conf").unlink()
            transaction.plugin_off("kitty")
            transaction.plugin_on("kitty")
            self.assertFalse((dest / "theme__custom__.conf").exists())

    def test_off_never_enabled_is_noop(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            steps = transaction.plugin_off("kitty")
            self.assertEqual(steps[0].detail, "already-disabled")
            self.assertIsNone(ledger.get_plugin("kitty"))


class TestOwnershipCarryLedger(unittest.TestCase):
    """Ledger doctrine (#139): the ledger records what the engine laid,
    never what it carried. Update re-baselines through ``resnapshot_plugins``;
    ``on`` is adoption (payload names claimed, extras stay user-owned)."""

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _make_hook(self, plugin_dir: Path, name: str, body: str) -> Path:
        hooks = plugin_dir / "hooks"
        hooks.mkdir(exist_ok=True)
        script = hooks / name
        script.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    def test_carry_baselines_enabled_units_only(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "kitty": {"files": {"k.conf": "x"}},
                "fish": {"files": {"f.conf": "y"}},
            })
            transaction.plugin_on("kitty")
            baselines = transaction.carry_baselines(["kitty", "fish"])
            self.assertEqual(set(baselines["kitty"]), {"k.conf"})
            self.assertIsNone(baselines["fish"], "Ghost plugins have no baseline")

    def test_on_adopts_claiming_payload_and_keeps_extras(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "template\n"}}})
            dest = ctx.home / ".config/app"
            dest.mkdir(parents=True)
            (dest / "a.conf").write_text("user's own take\n", encoding="utf-8")
            (dest / "extra.conf").write_text("user's tool\n", encoding="utf-8")
            steps = transaction.plugin_on("app")
            self.assertTrue(steps[0].ok, str(steps))
            # Adoption: the engine claims its payload name…
            self.assertEqual((dest / "a.conf").read_text(), "template\n")
            # …and the user's extra file survives as user-owned.
            self.assertEqual((dest / "extra.conf").read_text(), "user's tool\n")
            rec = ledger.get_plugin("app")
            self.assertEqual(set(rec["files"]), {"a.conf"},
                             "carried extras must never enter the snapshot")
            self.assertEqual(transaction.audit_plugins("app"), {"app": "Synced"})

    def test_update_carry_then_resnapshot_rebaselines_laid_only(self):
        from nyxuri.deploy.atomic import CarryPolicy

        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "v1\n"}}})
            transaction.plugin_on("app")
            dest = ctx.home / ".config/app"
            (dest / "a.conf").write_text("my edit\n", encoding="utf-8")
            (dest / "extra.conf").write_text("user's tool\n", encoding="utf-8")
            # Template moves on (the repo pull).
            (ctx.env.plugins_src / "app" / "a.conf").write_text("v2\n", encoding="utf-8")

            policy = CarryPolicy(
                baselines=transaction.carry_baselines(["app"]), unknown=True
            )
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"], carry_policy=policy))
            # 宁可错保: the user's edit and extra file both survive the update.
            self.assertEqual((dest / "a.conf").read_text(), "my edit\n")
            self.assertEqual((dest / "extra.conf").read_text(), "user's tool\n")
            self.assertEqual(policy.carried["app"]["a.conf"], "modified")
            self.assertEqual(policy.carried["app"]["extra.conf"], "user")

            transaction.resnapshot_plugins(["app"], policy.carried)
            rec = ledger.get_plugin("app")
            self.assertNotIn("a.conf", rec["files"],
                             "a carried file must never read as engine-laid")
            self.assertNotIn("extra.conf", rec["files"])
            # Drift is judged per ledger entry, so carried files are not noise.
            self.assertEqual(transaction.audit_plugins("app"), {"app": "Synced"})

            # Force is the adopt verb: template side wins and is re-baselined.
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"]))
            transaction.resnapshot_plugins(["app"], carried={})
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")
            self.assertEqual(
                ledger.get_plugin("app")["files"]["a.conf"],
                hashlib.sha256((dest / "a.conf").read_bytes()).hexdigest(),
            )

    def test_hook_product_lifecycle_through_update(self):
        """KM3 restored under carry (#139 field report): hook products retire
        at the swap (engine didn't lay them), the hook replay re-lays them,
        and resnapshot puts them back under ledger ownership — `off` wipes
        them again instead of leaving foreign residue."""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'packages = []\npost_install = "seed"\n',
                                 "files": {"a.conf": "v1\n"}}})
            self._make_hook(
                ctx.env.plugins_src / "app", "seed",
                'printf "hooked\\n" > "$NYXURI_UNIT_DEST/hooked.conf"',
            )
            self.assertTrue(transaction.plugin_on("app")[0].ok)
            dest = ctx.home / ".config/app"
            self.assertIn("hooked.conf", ledger.get_plugin("app")["files"])

            # Template moves on; the payload still has no hooked.conf.
            (ctx.env.plugins_src / "app" / "a.conf").write_text("v2\n", encoding="utf-8")
            from nyxuri.deploy.atomic import CarryPolicy
            policy = CarryPolicy(
                baselines=transaction.carry_baselines(["app"]), unknown=True
            )
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"], carry_policy=policy))
            self.assertFalse((dest / "hooked.conf").exists(),
                             "retired hook product must not be carried as a user file")
            self.assertEqual(policy.carried.get("app"), {})

            # Hook replay re-lays it; resnapshot re-owns it.
            self.assertTrue(transaction._run_plugin_hook(
                "app", transaction.registry.load_plugin("app"), "seed"))
            transaction.resnapshot_plugins(["app"], policy.carried)
            self.assertIn("hooked.conf", ledger.get_plugin("app")["files"])
            self.assertEqual(transaction.audit_plugins("app"), {"app": "Synced"})

    def test_preset_switch_on_enabled_unit_respects_baseline(self):
        """A re-deploy over an enabled plugin carries edits made after `on`."""
        from nyxuri.deploy.atomic import CarryPolicy

        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "v1\n"}}})
            transaction.plugin_on("app")
            dest = ctx.home / ".config/app"
            (dest / "a.conf").write_text("tuned\n", encoding="utf-8")
            (ctx.env.plugins_src / "app" / "a.conf").write_text("v2\n", encoding="utf-8")
            policy = CarryPolicy(
                baselines=transaction.carry_baselines(["app"]), unknown=False
            )
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"], carry_policy=policy))
            self.assertEqual((dest / "a.conf").read_text(), "tuned\n")
            self.assertEqual(policy.carried["app"]["a.conf"], "modified")


class TestAudit(unittest.TestCase):
    """doctor three-state reconciliation: Synced / Drifted / Ghost."""

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_three_states(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "kitty": {"files": {"k.conf": "x"}},
                "fish": {"files": {"f.conf": "y"}},
            })
            transaction.plugin_on("kitty")
            (ctx.home / ".config/kitty/k.conf").write_text("tampered\n")
            fish_dir = ctx.home / ".config/fish"
            fish_dir.mkdir()
            (fish_dir / "f.conf").write_text("residue\n")
            report = transaction.audit_plugins()
            self.assertEqual(report["kitty"], "Drifted")
            self.assertEqual(report["fish"], "Ghost")
            # healed → Synced
            (ctx.home / ".config/kitty/k.conf").write_text("x")
            self.assertEqual(transaction.audit_plugins("kitty"), {"kitty": "Synced"})
            # off + white paper → declaration matches reality → Synced
            transaction.plugin_off("kitty")
            self.assertEqual(transaction.audit_plugins("kitty"), {"kitty": "Synced"})
            # never-switched white plugins have nothing to reconcile
            _stage(ctx, {"bare": {"files": {"b.conf": "b"}}})
            self.assertNotIn("bare", transaction.audit_plugins())

    def test_missing_managed_file_is_drifted(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            transaction.plugin_on("kitty")
            (ctx.home / ".config/kitty/k.conf").unlink()
            self.assertEqual(transaction.audit_plugins("kitty"), {"kitty": "Drifted"})

    def test_audit_unknown_unit_raises(self):
        with TempEnv() as ctx:
            _stage(ctx, {})
            with self.assertRaises(KeyError):
                transaction.audit_plugins("ghost")

    def test_audit_is_read_only(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            transaction.plugin_on("kitty")
            state_path = ctx.home / ".local/state/nyxuri/state.json"
            before = state_path.read_text()
            transaction.audit_plugins()
            self.assertEqual(state_path.read_text(), before)


class TestEventPort(unittest.TestCase):
    """One plugin-changed event per ledger landing; sink failure never fails."""

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_one_event_per_unit_transaction(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "shell": {"manifest": 'dependencies = ["base"]\n', "files": {"s": "s"}},
                "base": {"files": {"b": "b"}},
            })
            events = []
            transaction.set_event_sink(lambda uid, state: events.append((uid, state)))
            try:
                transaction.plugin_on("shell")
                transaction.plugin_off("base", cascade=True)
            finally:
                transaction.set_event_sink(None)
            self.assertEqual(events, [
                ("base", "enabled"),
                ("shell", "enabled"),
                ("shell", "disabled"),
                ("base", "disabled"),
            ])

    def test_failing_sink_never_fails_the_unit(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})

            def boom(uid, state):
                raise RuntimeError("ipc down")

            transaction.set_event_sink(boom)
            try:
                steps = transaction.plugin_on("kitty")
            finally:
                transaction.set_event_sink(None)
            self.assertTrue(steps[0].ok, str(steps))
            self.assertTrue((ctx.home / ".config/kitty/k.conf").is_file())
            self.assertEqual(ledger.get_plugin("kitty")["state"], "enabled")


def _imported_modules(text: str) -> set:
    tree = ast.parse(text)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            base = "." * node.level + node.module
            found.add(base)
            for alias in node.names:
                if alias.name != "*":
                    found.add(f"{base}.{alias.name}")
    return found


class TestKernelLayering(unittest.TestCase):
    """The frozen star layering (unit-model.md §2) holds on every commit."""

    def _source(self, name: str) -> str:
        kernel = Path(importlib.import_module("nyxuri").__file__).parent / "kernel"
        return (kernel / f"{name}.py").read_text(encoding="utf-8")

    def test_kernel_package_holds_the_four_modules(self):
        """KM3.5 正名: the kernel lives physically in nyxuri/kernel/."""
        kernel = Path(importlib.import_module("nyxuri").__file__).parent / "kernel"
        for name in ("registry", "resolver", "ledger", "transaction"):
            self.assertTrue((kernel / f"{name}.py").is_file(), name)
        # The flat top level must not keep ghosts of the old layout.
        top = kernel.parent
        for name in ("registry", "resolver", "ledger", "transaction"):
            self.assertFalse((top / f"{name}.py").exists(), name)

    def test_leaves_never_import_siblings_or_transaction(self):
        for leaf in ("registry", "resolver", "ledger"):
            mods = _imported_modules(self._source(leaf))
            for mod in mods:
                top = mod.lstrip(".").split(".")[0]
                self.assertNotEqual(top, "transaction", f"{leaf} must not import transaction")
            if leaf == "resolver":
                self.assertNotIn("nyxuri", {m.split(".")[0] for m in mods},
                                 "resolver must stay pure (zero nyxuri imports)")
            siblings = {"nyxuri.kernel.registry", "nyxuri.kernel.resolver", "nyxuri.kernel.ledger"}
            siblings.discard(f"nyxuri.kernel.{leaf}")
            self.assertFalse(siblings & mods, f"{leaf} must not import kernel siblings")

    def test_transaction_composes_all_three_leaves(self):
        mods = _imported_modules(self._source("transaction"))
        for leaf in ("nyxuri.kernel.registry", "nyxuri.kernel.resolver", "nyxuri.kernel.ledger"):
            self.assertIn(leaf, mods, f"transaction must compose {leaf}")

    def test_kernel_never_references_quickshell(self):
        """The event port is injected; imports and literals never name the delivery."""
        tree = ast.parse(self._source("transaction"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(
                    any("quickshell" in alias.name.lower() for alias in node.names)
                )
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn("quickshell", (node.module or "").lower())
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn("quickshell", node.value.lower())


class TestPluginHooks(unittest.TestCase):
    """KM3 hook contract: plugin-owned scripts, declared in the manifest.

    - post_install runs BEFORE the ledger snapshot, so products the hook
      lands inside the plugin's own living area become transaction-managed
      (``off`` wipes them through the normal white-paper path).
    - post_remove runs AFTER the wipe (effects outside the living area).
    - hooks never ship to the living area and never count as deployable.
    """

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _make_hook(self, plugin_dir: Path, name: str, body: str) -> Path:
        hooks = plugin_dir / "hooks"
        hooks.mkdir(exist_ok=True)
        script = hooks / name
        script.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    def test_on_runs_hook_and_snapshot_covers_living_area_products(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {
                "manifest": 'post_install = "seed"\n',
                "files": {"a.conf": "a"},
            }})
            self._make_hook(
                ctx.env.plugins_src / "app", "seed",
                'printf "hooked\\n" > "$NYXURI_UNIT_DEST/hooked.conf"',
            )
            steps = transaction.plugin_on("app")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertNotIn("hook-failed", steps[0].detail)
            dest = ctx.home / ".config/app"
            self.assertTrue((dest / "hooked.conf").is_file())
            rec = ledger.get_plugin("app")
            self.assertIn("hooked.conf", rec["files"], "hook products must enter the managed snapshot")

    def test_on_hook_failure_surfaces_in_detail_without_blocking(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'post_install = "nope"\n', "files": {"a.conf": "a"}}})
            steps = transaction.plugin_on("app")
            self.assertTrue(steps[0].ok)
            self.assertIn("hook-failed: nope", steps[0].detail)
            self.assertTrue((ctx.home / ".config/app/a.conf").is_file())

    def test_off_runs_post_remove_after_wipe(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {
                "manifest": 'post_remove = "clean"\n',
                "files": {"a.conf": "a"},
            }})
            calls = []
            original = transaction._run_plugin_hook

            def spy(uid, manifest, spec):
                calls.append((uid, spec, (ctx.home / ".config/app").exists()))
                return original(uid, manifest, spec)

            with mock.patch.object(transaction, "_run_plugin_hook", side_effect=spy):
                transaction.plugin_on("app")
                steps = transaction.plugin_off("app")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual(calls[-1], ("app", "clean", False),
                             "post_remove must run after the wipe")
            self.assertFalse((ctx.home / ".config/app").exists())

    def test_hook_env_exposes_unit_identity(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'post_install = "identity"\n', "files": {"a.conf": "a"}}})
            marker = ctx.home / "hook-env.txt"
            self._make_hook(
                ctx.env.plugins_src / "app", "identity",
                f'env | grep -E "^NYXURI_UNIT" > "{marker}"',
            )
            steps = transaction.plugin_on("app")
            self.assertTrue(steps[0].ok, str(steps))
            content = marker.read_text(encoding="utf-8")
            self.assertIn("NYXURI_UNIT=app", content)
            self.assertIn("NYXURI_UNIT_SRC=", content)
            self.assertIn("NYXURI_UNIT_DEST=", content)

    def test_hooks_never_count_as_deployable_config(self):
        from nyxuri.deploy.manifest import load_manifest

        with TempEnv() as ctx:
            _stage(ctx, {"ghost-plugin": {"manifest": 'packages = ["x"]\n'}})
            self._make_hook(ctx.env.plugins_src / "ghost-plugin", "hook", "true")
            m = load_manifest(ctx.env.plugins_src / "ghost-plugin")
            self.assertFalse(m.is_deployable, "manifest + hooks only must stay non-deployable")


if __name__ == "__main__":
    unittest.main()


class TestLedgerResilience(unittest.TestCase):

    def test_unhashable_active_shell_falls_back_to_default(self):
        from nyxuri.kernel import ledger
        with TempEnv():
            for bad in ([], {}, ["a"], 5, None, "weird"):
                ledger.update_ledger(active_shell=bad)
                self.assertEqual(ledger.active_shell(), "noctalia")

    def test_concurrent_updates_do_not_lose_keys(self):
        from nyxuri.kernel import ledger
        with TempEnv():
            ledger.update_ledger(seed="x")
            read_fd, write_fd = os.pipe()
            pids = []
            for index in range(6):
                pid = os.fork()
                if pid == 0:
                    try:
                        os.read(read_fd, 1)
                        ledger.update_ledger(**{f"k{index}": index})
                    finally:
                        os._exit(0)
                pids.append(pid)
            os.close(read_fd)
            for _ in range(6):
                os.write(write_fd, b"g")
            os.close(write_fd)
            for pid in pids:
                os.waitpid(pid, 0)
            data = ledger.read_ledger()
            self.assertEqual([data.get(f"k{i}") for i in range(6)], list(range(6)))
