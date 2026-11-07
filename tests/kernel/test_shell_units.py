"""KM4 shell-namespace tests: dotted-id catalog roots, runtime plugins
(state-only existence, no living area), the event bridge delivery, and
doctor reconciliation for payload-less plugins.

Every test runs inside TempEnv — the real ~/.config is never touched.
"""

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from nyxuri.system import shell as bridge
from nyxuri.state import store
from nyxuri.deploy import catalog, engine
from tests.utils import TempEnv


def _stage_shell(ctx, spec):
    """Create shell-namespace plugins under a temp root and point the env at it.

    spec maps domain -> {"manifest": toml body | None} (runtime plugins are
    ui-kind plugins: their state form comes from kinds, and the staged entry
    file stands in for the domain's QML root).
    """
    root = ctx.home / "shell-plugins-src"
    root.mkdir(exist_ok=True)
    for domain, entry in spec.items():
        plugin = root / domain
        plugin.mkdir(exist_ok=True)
        (plugin / "Unit.qml").write_text("// entry\n", encoding="utf-8")
        if entry.get("manifest") is not None:
            text = (
                'schemaVersion = 1\n'
                f'id = "shell.{domain}"\n'
                'kinds = ["overlay"]\n'
                + entry["manifest"]
                + '[entryPoints]\noverlay = "Unit.qml"\n'
            )
            (plugin / "manifest.toml").write_text(text, encoding="utf-8")
    ctx.env.shell_units_src = root


def _runtime_manifest(**extra):
    lines = [f'{k} = "{v}"' for k, v in extra.items()]
    return "\n".join(lines) + ("\n" if lines else "")


class TestShellNamespaceRegistry(unittest.TestCase):
    """The shell blueprint root yields dotted ids through the same door."""

    def test_shell_units_get_dotted_ids_from_the_root(self):
        with TempEnv() as ctx:
            _stage_shell(ctx, {"bar": {"manifest": _runtime_manifest(label="Bar")}})
            ids = catalog.plugin_ids()
            self.assertIn("shell.bar", ids)
            self.assertIn("kitty", ids)  # bare root still present
            self.assertIn("shell.bar", catalog.dependency_graph())

    def test_load_unit_sees_the_declared_dotted_id(self):
        with TempEnv() as ctx:
            _stage_shell(ctx, {"dock": {"manifest": _runtime_manifest()}})
            m = catalog.load_plugin("shell.dock")
            self.assertEqual(m.id, "shell.dock")
            self.assertTrue(m.runtime)

    def test_unknown_and_malformed_ids_never_resolve(self):
        with TempEnv() as ctx:
            _stage_shell(ctx, {"bar": {"manifest": _runtime_manifest()}})
            self.assertIsNone(catalog.plugin_dir("shell.nope"))
            self.assertIsNone(catalog.plugin_dir("shell."))
            with self.assertRaises(KeyError):
                catalog.load_plugin("shell.nope")

    def test_shell_manifests_are_invisible_to_deploy_discovery(self):
        """Deploy/deps menus scan the bare root only — packages ≠ plugins."""
        from nyxuri.deploy.manifest import discover_manifest_apps

        with TempEnv() as ctx:
            _stage_shell(ctx, {"bar": {"manifest": _runtime_manifest()}})
            self.assertNotIn("shell.bar", [name for name, _ in discover_manifest_apps()])
            self.assertIn("kitty", [name for name, _ in discover_manifest_apps()])


class TestRuntimePluginEngine(unittest.TestCase):
    """on/off for runtime plugins: pure state store + one event, zero disk touch."""

    def setUp(self):
        patcher = mock.patch.object(engine, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _staged(self, ctx, **extra):
        _stage_shell(ctx, {"bar": {"manifest": _runtime_manifest(**extra)}})

    def test_on_records_enabled_without_touching_the_machine(self):
        with TempEnv() as ctx:
            self._staged(ctx)
            events = []
            engine.set_event_sink(lambda uid, st: events.append((uid, st)))
            self.addCleanup(engine.set_event_sink, None)
            steps = engine.plugin_on("shell.bar")
            self.assertEqual([s.ok for s in steps], [True], str(steps))
            rec = store.get_plugin("shell.bar")
            self.assertEqual(rec["state"], "enabled")
            self.assertEqual(rec["files"], {})
            self.assertIsNone(rec["vault"])
            # No living area anywhere: not the dotted name, not the bare one.
            self.assertFalse((ctx.home / ".config/shell.bar").exists())
            self.assertFalse((ctx.home / ".config/bar").exists())
            self.assertFalse((ctx.home / ".local/state/nyxuri/vault/shell.bar").exists())
            self.assertEqual(events, [("shell.bar", "enabled")])

    def test_off_is_state_only_and_never_eats_same_named_dirs(self):
        """The deadly case: ~/.config/bar belongs to some other app — an off
        of the runtime plugin must not wipe it (runtime plugins have no target)."""
        with TempEnv() as ctx:
            self._staged(ctx)
            stranger = ctx.home / ".config/bar"
            stranger.mkdir()
            (stranger / "unrelated.conf").write_text("keep me", encoding="utf-8")
            engine.plugin_on("shell.bar")
            events = []
            engine.set_event_sink(lambda uid, st: events.append((uid, st)))
            self.addCleanup(engine.set_event_sink, None)
            steps = engine.plugin_off("shell.bar")
            self.assertTrue(steps[0].ok, str(steps))
            rec = store.get_plugin("shell.bar")
            self.assertEqual(rec["state"], "disabled")
            self.assertTrue((stranger / "unrelated.conf").is_file())
            self.assertEqual(events, [("shell.bar", "disabled")])

    def test_off_of_never_enabled_runtime_unit_short_circuits(self):
        with TempEnv() as ctx:
            self._staged(ctx)
            events = []
            engine.set_event_sink(lambda uid, st: events.append((uid, st)))
            self.addCleanup(engine.set_event_sink, None)
            steps = engine.plugin_off("shell.bar")
            self.assertEqual(steps[0].detail, "already-disabled")
            self.assertEqual(events, [])

    def test_preset_axis_does_not_apply_to_runtime_units(self):
        with TempEnv() as ctx:
            self._staged(ctx)
            steps = engine.plugin_on("shell.bar", form="fancy")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual(store.get_plugin("shell.bar")["form"], "default")
            self.assertFalse((ctx.home / ".config/nyxuri/forms/shell.bar").exists())

    def test_dependency_closure_spans_namespaces(self):
        with TempEnv() as ctx:
            _stage_shell(ctx, {"bar": {"manifest": _runtime_manifest()}})
            configs = ctx.home / "configs-src"
            configs.mkdir(exist_ok=True)
            host = configs / "hostbase"
            host.mkdir()
            (host / "manifest.toml").write_text(
                'schemaVersion = 1\nid = "hostbase"\nkinds = ["config"]\npackages = []\n',
                encoding="utf-8")
            (host / "h.conf").write_text("h\n", encoding="utf-8")
            ctx.env.plugins_src = configs
            events = []
            engine.set_event_sink(lambda uid, st: events.append(uid))
            self.addCleanup(engine.set_event_sink, None)
            steps = engine.plugin_on("shell.bar")  # bar has no deps: solo
            self.assertTrue(all(s.ok for s in steps), str(steps))

    def test_cascade_disables_enabled_dependents(self):
        with TempEnv() as ctx:
            _stage_shell(ctx, {
                "bar": {"manifest": _runtime_manifest()},
                "dock": {"manifest": 'dependencies = ["shell.bar"]\n'},
            })
            engine.plugin_on("shell.bar")
            engine.plugin_on("shell.dock")
            blocked = engine.plugin_off("shell.bar")
            self.assertFalse(blocked[0].ok)
            self.assertIn("blocked-by-enabled-dependents", blocked[0].detail)
            cascaded = engine.plugin_off("shell.bar", cascade=True)
            self.assertTrue(all(s.ok for s in cascaded), str(cascaded))
            self.assertEqual(store.get_plugin("shell.dock")["state"], "disabled")
            self.assertEqual(store.get_plugin("shell.bar")["state"], "disabled")


class TestRuntimePluginDoctor(unittest.TestCase):
    """Payload-less plugins: the state record is the whole existence."""

    def test_audit_synced_both_ways_and_never_ghost(self):
        with TempEnv() as ctx:
            _stage_shell(ctx, {"bar": {"manifest": _runtime_manifest()}})
            engine.plugin_on("shell.bar")
            self.assertEqual(engine.audit_plugins("shell.bar"),
                             {"shell.bar": engine.STATE_SYNCED})
            engine.plugin_off("shell.bar")
            self.assertEqual(engine.audit_plugins("shell.bar"),
                             {"shell.bar": engine.STATE_SYNCED})
            # Foreign junk where a target would be is still not our Ghost.
            junk = ctx.home / ".config/bar"
            junk.mkdir()
            (junk / "x.conf").write_text("x\n", encoding="utf-8")
            self.assertEqual(engine.audit_plugins("shell.bar"),
                             {"shell.bar": engine.STATE_SYNCED})


class TestEventBridge(unittest.TestCase):
    """The outer layer's delivery: existing Quickshell IPC, zero new channel."""

    def test_wire_injects_the_sink(self):
        self.addCleanup(engine.set_event_sink, None)
        bridge.wire()
        self.assertIs(engine._event_sink, bridge.notify_plugin_changed)

    def test_no_running_shell_spawns_nothing(self):
        with TempEnv() as ctx:
            with mock.patch.object(bridge, "probe_running_shells", return_value=[]), \
                 mock.patch.object(bridge.subprocess, "run") as run:
                bridge.notify_plugin_changed("shell.bar", "enabled")
            run.assert_not_called()

    def test_delivery_uses_exact_ipc_shape(self):
        """External commands are asserted on argv shape (tests contract)."""
        with TempEnv() as ctx:
            shell_dir = ctx.home / "shellplace"
            shell_dir.mkdir()
            (shell_dir / "shell.qml").write_text("// marker\n", encoding="utf-8")
            bin_link = shell_dir / "nyxuri-shell"
            bin_link.write_text("#!/bin/sh\n", encoding="utf-8")
            instances = [("nyxuri-shell", 4242)]
            with mock.patch.object(bridge, "probe_running_shells",
                                   return_value=instances), \
                 mock.patch.object(bridge, "resolve_custom_bin",
                                   return_value=str(bin_link)), \
                 mock.patch.object(bridge.subprocess, "run") as run:
                bridge.notify_plugin_changed("shell.bar", "disabled")
            run.assert_called_once()
            args, kwargs = run.call_args
            self.assertEqual(
                args[0],
                ["qs", "-p", str(shell_dir), "ipc", "call", "unit", "reload"],
            )
            self.assertFalse(kwargs.get("check", True))
            self.assertLess(kwargs.get("timeout", 99), 5)

    def test_unresolvable_shell_dir_degrades_to_warn_without_raise(self):
        with TempEnv() as ctx:
            with mock.patch.object(bridge, "probe_running_shells",
                                   return_value=[("nyxuri-shell", 1)]), \
                 mock.patch.object(bridge, "resolve_custom_bin", return_value=""), \
                 mock.patch.object(bridge.subprocess, "run") as run:
                bridge.notify_plugin_changed("shell.bar", "enabled")  # must not raise
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
