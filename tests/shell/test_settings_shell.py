"""T3 settings shell baseline: panel-style axis convergence and route metadata.

M0 contracts: the settingsPanelStyle axis collapses from three values to
default + dashboard, historical "minimal" configs fold to "default" through the
existing normalizedOption fallbacks, and every settings route carries a
top-level description for the upcoming two-line NavPane (T3 M2 consumer).
"""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL = REPO_ROOT / "shell"


def _qml_sources():
    for sub in ("app", "commons", "ui", "services", "plugins"):
        for pattern in ("*.qml", "*.js"):
            for path in (SHELL / sub).rglob(pattern):
                if "__pycache__" not in path.parts:
                    yield path


class TestPanelStyleAxisConvergence(unittest.TestCase):
    """settingsPanelStyles is a two-value axis; "minimal" folds, not special-cases."""

    def _config_source(self):
        return (SHELL / "services" / "PersonalizationConfig.qml").read_text(encoding="utf-8")

    def test_axis_is_exactly_default_and_dashboard(self):
        source = self._config_source()
        start = source.index("readonly property var settingsPanelStyles")
        block = source[start:source.index("]", start)]
        values = re.findall(r'"value":\s*"([a-z]+)"', block)
        self.assertEqual(values, ["default", "dashboard"],
                         "panel-style axis must be exactly default + dashboard")

    def test_minimal_folds_to_default_on_load_and_write(self):
        source = self._config_source()
        self.assertIsNotNone(
            re.search(r'setValue\("settingsPanelStyle", normalizedOption\('
                      r'root\.settingsPanelStyles, value, "default"\)\)', source),
            "setter must keep folding unknown values to default")
        self.assertIsNotNone(
            re.search(r'root\.settingsPanelStyle = normalizedOption\('
                      r'root\.settingsPanelStyles, theme\.settingsPanelStyle,\s*"default"\)', source),
            "loader must keep folding stored minimal configs to default")

    def test_no_live_consumer_of_the_removed_value(self):
        offenders = [path.relative_to(REPO_ROOT)
                     for path in _qml_sources()
                     if '"minimal"' in path.read_text(encoding="utf-8")]
        self.assertEqual(offenders, [],
                         f'"minimal" panel-style value still referenced: {offenders}')


class TestRouteDescriptions(unittest.TestCase):
    """Every route carries a non-empty top-level description."""

    def test_every_route_has_a_nonempty_description(self):
        document = json.loads(
            (SHELL / "plugins" / "settings" / "settings-routes.json").read_text(encoding="utf-8"))
        routes = document["routes"]
        # 45361df 定向瘦身（删除抽屉/显示/自启动/默认应用页面）后的真实规模底线；
        # 当时断言未随瘦身更新，S0-1 随测试清算对齐。
        self.assertGreaterEqual(len(routes), 16)
        missing = [route["id"] for route in routes
                   if not str(route.get("description", "")).strip()]
        self.assertEqual(missing, [], f"routes without description: {missing}")


if __name__ == "__main__":
    unittest.main()
