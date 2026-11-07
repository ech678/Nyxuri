"""Tests for P1 Plugins Control Plane & Dynamic Navigation.

Verifies:
1. ControlCenterWindow dynamically filters settings routes based on StateProjection.isEnabledUnit.
2. SpotlightCatalog gates route availability by StateProjection.isEnabledUnit.
3. PluginsPage provides built-in and third-party plugin lifecycle management.
4. PluginManagerService coordinates lifecycle commands via array arguments.
5. ShellPage is purified of unit switch toggles and dedicated to system diagnostics.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL = REPO_ROOT / "shell"
SERVICES = SHELL / "services"
SETTINGS = SHELL / "plugins" / "settings"


class TestPluginsControlPlaneContract(unittest.TestCase):
    def test_control_center_filters_disabled_units(self):
        source = (SETTINGS / "ControlCenterWindow.qml").read_text(encoding="utf-8")
        self.assertIn("StateProjection.isEnabledUnit(entry.pluginId)", source)
        self.assertIn("onPagesChanged", source)
        self.assertIn("currentPage = Math.max(0, pages.length - 1)", source)

    def test_spotlight_catalog_gates_disabled_units(self):
        source = (SERVICES / "SpotlightCatalog.qml").read_text(encoding="utf-8")
        self.assertIn("entry.pluginId && !StateProjection.isEnabledUnit(entry.pluginId)", source)
        self.assertIn("Connections {", source)
        self.assertIn("target: StateProjection", source)
        self.assertIn("function onUnitsChanged()", source)

    def test_state_projection_emits_units_changed(self):
        source = (SERVICES / "StateProjection.qml").read_text(encoding="utf-8")
        self.assertIn("signal unitsChanged()", source)
        self.assertIn("root.unitsChanged()", source)

    def test_plugin_registry_populates_third_party_flag(self):
        source = (SERVICES / "PluginRegistry.qml").read_text(encoding="utf-8")
        self.assertIn("const isThirdParty = record.dir.indexOf(registry.pluginsDir) === 0", source)
        self.assertIn("isThirdParty: isThirdParty", source)

    def test_plugin_settings_supports_reset(self):
        source = (SERVICES / "PluginSettings.qml").read_text(encoding="utf-8")
        self.assertIn("function resetPlugin(pluginId)", source)

    def test_plugin_manager_service_api_and_guards(self):
        source = (SERVICES / "PluginManagerService.qml").read_text(encoding="utf-8")
        for token in (
            "pragma Singleton",
            "function installPlugin(",
            "function updatePlugin(",
            "function removePlugin(",
            "function resetPlugin(",
            "function openPluginDir(",
            "signal operationFinished(",
            "Component.onDestruction:",
        ):
            self.assertIn(token, source, f"missing token in PluginManagerService: {token}")

    def test_shell_page_purified_of_switches(self):
        source = (SETTINGS / "ShellPage.qml").read_text(encoding="utf-8")
        self.assertNotIn("PluginRegistry.toggles", source,
                         "ShellPage must not contain plugin switch toggles")
        self.assertIn("ShellControlService.setPageMounted(true)", source)
        self.assertIn("CompositorDriver.reconnect()", source)
        self.assertIn("ShellControlService.exportDiagnostics()", source)

    def test_plugins_page_composes_management_features(self):
        source = (SETTINGS / "PluginsPage.qml").read_text(encoding="utf-8")
        self.assertIn("PluginRegistry.toggles.filter(p => !p.isThirdParty)", source)
        self.assertIn("PluginRegistry.toggles.filter(p => p.isThirdParty)", source)
        self.assertIn("UnitControlService.setUnit(", source)
        self.assertIn("PluginManagerService.resetPlugin(", source)
        self.assertIn("PluginManagerService.installPlugin(", source)
        self.assertIn("PluginManagerService.updatePlugin(", source)
        self.assertIn("PluginManagerService.removePlugin(", source)
        self.assertIn("PluginManagerService.openPluginDir(", source)


if __name__ == "__main__":
    unittest.main()
