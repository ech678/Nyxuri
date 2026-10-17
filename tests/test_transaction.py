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

from nyxuri import ledger, transaction
from tests.utils import TempEnv


def _stage(ctx, spec):
    """Create unit dirs under a temp configs_src and point the env at it.

    spec maps unit id -> {"manifest": toml text | None, "files": {rel: content}}.
    """
    configs = ctx.home / "configs-src"
    configs.mkdir(exist_ok=True)
    for uid, entry in spec.items():
        unit = configs / uid
        unit.mkdir(exist_ok=True)
        if entry.get("manifest") is not None:
            (unit / "manifest.toml").write_text(entry["manifest"], encoding="utf-8")
        for rel, content in entry.get("files", {}).items():
            p = unit / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    ctx.env.configs_src = configs


class TestUnitOn(unittest.TestCase):
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
            steps = transaction.unit_on("kitty")
            self.assertEqual([s.ok for s in steps], [True], str(steps))
            dest = ctx.home / ".config/kitty/kitty.conf"
            self.assertTrue(dest.is_file())
            rec = ledger.get_unit("kitty")
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
            real = ledger.set_unit

            def spy(unit_id, **kw):
                order.append(unit_id)
                return real(unit_id, **kw)

            with mock.patch.object(ledger, "set_unit", spy):
                steps = transaction.unit_on("shell")
            self.assertTrue(all(s.ok for s in steps), str(steps))
            self.assertEqual(order, ["base", "shell"])
            self.assertTrue((ctx.home / ".config/base/b.conf").is_file())
            self.assertTrue((ctx.home / ".config/shell/s.conf").is_file())
            self.assertEqual(ledger.get_unit("base")["state"], "enabled")

    def test_on_missing_packages_aborts_without_touching_machine(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'packages = ["missing-pkg"]\n',
                                 "files": {"a.conf": "a"}}})
            with mock.patch.object(transaction, "missing_packages",
                                   return_value=["missing-pkg"]):
                steps = transaction.unit_on("app")
            self.assertFalse(steps[0].ok)
            self.assertIn("missing-packages", steps[0].detail)
            self.assertIn("missing-pkg", steps[0].detail)
            self.assertFalse((ctx.home / ".config/app").exists())
            self.assertIsNone(ledger.get_unit("app"))

    def test_on_injected_installer_unblocks_preflight(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'packages = ["missing-pkg"]\n',
                                 "files": {"a.conf": "a"}}})
            calls = []

            def installer(pkgs):
                calls.append(pkgs)
                return True

            with mock.patch.object(transaction, "missing_packages",
                                   side_effect=[["missing-pkg"], []]):
                steps = transaction.unit_on("app", install_packages=installer)
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual(calls, [["missing-pkg"]])
            self.assertTrue((ctx.home / ".config/app/a.conf").is_file())

    def test_on_already_enabled_is_noop(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"kitty.conf": "x"}}})
            transaction.unit_on("kitty")
            with mock.patch.object(transaction, "_phase_atomic_deployment",
                                   wraps=transaction._phase_atomic_deployment) as dep:
                steps = transaction.unit_on("kitty")
            self.assertEqual(steps[0].detail, "already-enabled")
            dep.assert_not_called()

    def test_on_single_file_unit_roundtrip(self):
        """target= units ride the same transaction (deploy.py result-binding fix)."""
        with TempEnv() as ctx:
            _stage(ctx, {"starship": {"manifest": 'target = "starship.toml"\n',
                                      "files": {"starship.toml": "$schema\n"}}})
            steps = transaction.unit_on("starship")
            self.assertTrue(steps[0].ok, str(steps))
            dest = ctx.home / ".config/starship.toml"
            self.assertTrue(dest.is_file())
            rec = ledger.get_unit("starship")
            self.assertEqual(set(rec["files"]), {"starship.toml"})
            self.assertEqual(transaction.audit_units("starship"), {"starship": "Synced"})
            steps = transaction.unit_off("starship")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertFalse(dest.exists())
            self.assertEqual(ledger.get_unit("starship")["state"], "disabled")

    def test_unknown_unit_raises(self):
        with TempEnv() as ctx:
            _stage(ctx, {})
            with self.assertRaises(KeyError):
                transaction.unit_on("ghost")
            with self.assertRaises(KeyError):
                transaction.unit_off("ghost")

    def test_declared_dependency_without_a_unit_is_ignored(self):
        """A dependency on a not-yet-existing unit must not crash the enable.

        The resolver contract ignores edges that leave the graph, so the
        closure walk has to tolerate the same shape instead of indexing it.
        """
        with TempEnv() as ctx:
            _stage(ctx, {
                "shell": {"manifest": 'dependencies = ["ghostdep"]\n', "files": {"s.conf": "s"}},
            })
            steps = transaction.unit_on("shell")
            self.assertTrue(all(s.ok for s in steps), str(steps))
            self.assertEqual(ledger.get_unit("shell")["state"], "enabled")
            self.assertTrue((ctx.home / ".config/shell/s.conf").is_file())

    def test_preset_marker_follows_a_successful_swap(self):
        """A failed deploy must not leave the preset marker pointing at the new form."""
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"kitty.conf": "k"}}})
            transaction.unit_on("kitty")
            marker = _marker_path(ctx, "kitty")
            before = marker.read_text(encoding="utf-8") if marker.is_file() else None
            with mock.patch.object(
                transaction, "_phase_atomic_deployment", return_value=["kitty"]
            ):
                steps = transaction.unit_on("kitty", preset="dark")
            self.assertFalse(steps[0].ok, str(steps))
            self.assertEqual(steps[0].detail, "deploy-failed")
            after = marker.read_text(encoding="utf-8") if marker.is_file() else None
            self.assertEqual(after, before)

    def test_preset_marker_is_written_once_the_swap_lands(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"kitty.conf": "k"}}})
            steps = transaction.unit_on("kitty", preset="dark")
            self.assertTrue(all(s.ok for s in steps), str(steps))
            marker = _marker_path(ctx, "kitty")
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.read_text(encoding="utf-8").strip(), "dark")


def _marker_path(ctx, unit_id):
    return ctx.home / ".config/nyxuri/presets" / f"{unit_id}.active"


class TestUnitOff(unittest.TestCase):
    """Disable transaction: guard → vault in → white-paper wipe → ledger."""

    def setUp(self):
        # unit_on setup steps must not depend on host package state either.
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_off_archives_custom_and_preserve_then_wipes(self):
        with TempEnv() as ctx:
            _stage(ctx, {"niri": {
                "manifest": 'preserve = ["monitor.kdl"]\n',
                "files": {"niri.conf": "spawn {}\n", "monitor.kdl": "output eDP-1\n"},
            }})
            transaction.unit_on("niri")
            dest = ctx.home / ".config/niri"
            (dest / "theme__custom__.conf").write_text("my own\n")
            (dest / "monitor.kdl").write_text("output eDP-1 position 0 0\n")
            steps = transaction.unit_off("niri")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertFalse(dest.exists(), "enabled area must be wiped to white paper")
            vault = ctx.home / ".local/state/nyxuri/vault/niri"
            self.assertEqual((vault / "theme__custom__.conf").read_text(), "my own\n")
            self.assertEqual((vault / "monitor.kdl").read_text(), "output eDP-1 position 0 0\n")
            rec = ledger.get_unit("niri")
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
            transaction.unit_on("panel")
            steps = transaction.unit_off("base")
            self.assertFalse(steps[0].ok)
            self.assertIn("blocked-by-enabled-dependents", steps[0].detail)
            self.assertIn("panel", steps[0].detail)
            self.assertIn("shell", steps[0].detail)
            self.assertEqual(ledger.get_unit("base")["state"], "enabled")
            self.assertTrue((ctx.home / ".config/base/b.conf").is_file())

    def test_off_cascade_disables_dependents_first(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "panel": {"manifest": 'dependencies = ["shell"]\n', "files": {"p.conf": "p"}},
                "shell": {"manifest": 'dependencies = ["base"]\n', "files": {"s.conf": "s"}},
                "base": {"files": {"b.conf": "b"}},
            })
            transaction.unit_on("panel")
            order = []
            real = ledger.set_unit

            def spy(unit_id, **kw):
                order.append(unit_id)
                return real(unit_id, **kw)

            with mock.patch.object(ledger, "set_unit", spy):
                steps = transaction.unit_off("base", cascade=True)
            self.assertTrue(all(s.ok for s in steps), str(steps))
            self.assertEqual(order, ["panel", "shell", "base"])
            for uid in ("panel", "shell", "base"):
                self.assertEqual(ledger.get_unit(uid)["state"], "disabled")
                self.assertFalse((ctx.home / f".config/{uid}").exists())

    def test_off_survives_foreign_files_and_reports_them(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            transaction.unit_on("kitty")
            dest = ctx.home / ".config/kitty"
            (dest / "my-notes.txt").write_text("keep me\n")
            steps = transaction.unit_off("kitty")
            self.assertTrue(steps[0].ok)
            self.assertIn("foreign-left: my-notes.txt", steps[0].detail)
            self.assertTrue((dest / "my-notes.txt").is_file(), "user files must never be eaten")
            self.assertFalse((dest / "k.conf").exists())
            self.assertEqual(transaction.audit_units("kitty"), {"kitty": "Ghost"})

    def test_off_without_ledger_snapshot_wipes_blueprint_area(self):
        """Files deployed outside the transaction (pre-KM2 install) are all managed."""
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            dest = ctx.home / ".config/kitty"
            dest.mkdir(parents=True)
            (dest / "k.conf").write_text("deployed by old installer\n")
            steps = transaction.unit_off("kitty")
            self.assertTrue(steps[0].ok)
            self.assertFalse(dest.exists())

    def test_off_then_on_restores_vault_and_consumes_it(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            dest = ctx.home / ".config/kitty"
            transaction.unit_on("kitty")
            (dest / "theme__custom__.conf").write_text("v1\n")
            transaction.unit_off("kitty")
            self.assertFalse((dest / "theme__custom__.conf").exists())
            steps = transaction.unit_on("kitty")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual((dest / "theme__custom__.conf").read_text(), "v1\n")
            vault = ctx.home / ".local/state/nyxuri/vault/kitty"
            self.assertFalse(vault.exists(), "archive must be consumed on restore")
            rec = ledger.get_unit("kitty")
            self.assertEqual(rec["state"], "enabled")
            self.assertIsNone(rec["vault"])
            # deleted customs stay deleted: an empty archive must not resurrect
            (dest / "theme__custom__.conf").unlink()
            transaction.unit_off("kitty")
            transaction.unit_on("kitty")
            self.assertFalse((dest / "theme__custom__.conf").exists())

    def test_off_never_enabled_is_noop(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            steps = transaction.unit_off("kitty")
            self.assertEqual(steps[0].detail, "already-disabled")
            self.assertIsNone(ledger.get_unit("kitty"))


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
            transaction.unit_on("kitty")
            (ctx.home / ".config/kitty/k.conf").write_text("tampered\n")
            fish_dir = ctx.home / ".config/fish"
            fish_dir.mkdir()
            (fish_dir / "f.conf").write_text("residue\n")
            report = transaction.audit_units()
            self.assertEqual(report["kitty"], "Drifted")
            self.assertEqual(report["fish"], "Ghost")
            # healed → Synced
            (ctx.home / ".config/kitty/k.conf").write_text("x")
            self.assertEqual(transaction.audit_units("kitty"), {"kitty": "Synced"})
            # off + white paper → declaration matches reality → Synced
            transaction.unit_off("kitty")
            self.assertEqual(transaction.audit_units("kitty"), {"kitty": "Synced"})
            # never-switched white units have nothing to reconcile
            _stage(ctx, {"bare": {"files": {"b.conf": "b"}}})
            self.assertNotIn("bare", transaction.audit_units())

    def test_missing_managed_file_is_drifted(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            transaction.unit_on("kitty")
            (ctx.home / ".config/kitty/k.conf").unlink()
            self.assertEqual(transaction.audit_units("kitty"), {"kitty": "Drifted"})

    def test_audit_unknown_unit_raises(self):
        with TempEnv() as ctx:
            _stage(ctx, {})
            with self.assertRaises(KeyError):
                transaction.audit_units("ghost")

    def test_audit_is_read_only(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            transaction.unit_on("kitty")
            state_path = ctx.home / ".local/state/nyxuri/state.json"
            before = state_path.read_text()
            transaction.audit_units()
            self.assertEqual(state_path.read_text(), before)


class TestEventPort(unittest.TestCase):
    """One unit-changed event per ledger landing; sink failure never fails."""

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
                transaction.unit_on("shell")
                transaction.unit_off("base", cascade=True)
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
                steps = transaction.unit_on("kitty")
            finally:
                transaction.set_event_sink(None)
            self.assertTrue(steps[0].ok, str(steps))
            self.assertTrue((ctx.home / ".config/kitty/k.conf").is_file())
            self.assertEqual(ledger.get_unit("kitty")["state"], "enabled")


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
        kernel = Path(importlib.import_module("nyxuri").__file__).parent
        return (kernel / f"{name}.py").read_text(encoding="utf-8")

    def test_leaves_never_import_siblings_or_transaction(self):
        for leaf in ("registry", "resolver", "ledger"):
            mods = _imported_modules(self._source(leaf))
            for mod in mods:
                top = mod.lstrip(".").split(".")[0]
                self.assertNotEqual(top, "transaction", f"{leaf} must not import transaction")
            if leaf == "resolver":
                self.assertNotIn("nyxuri", {m.split(".")[0] for m in mods},
                                 "resolver must stay pure (zero nyxuri imports)")
            siblings = {"nyxuri.registry", "nyxuri.resolver", "nyxuri.ledger"}
            siblings.discard(f"nyxuri.{leaf}")
            self.assertFalse(siblings & mods, f"{leaf} must not import kernel siblings")

    def test_transaction_composes_all_three_leaves(self):
        mods = _imported_modules(self._source("transaction"))
        for leaf in ("nyxuri.registry", "nyxuri.resolver", "nyxuri.ledger"):
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


if __name__ == "__main__":
    unittest.main()
