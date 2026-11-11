"""S0-4 (narrowed) asset placement contracts: nothing shipped may rot.

The flat ``shell/ui/`` pool and the settings plugin's root QML files must each
keep at least one live consumer. Consumers are found by word-boundary name
match across the runtime tree (QML/JS type usage, ``Loader source: "Foo.qml"``
strings, manifest-declared settings sources, script probes) — test sources are
deliberately NOT consumers: the gate demands a real runtime consumer, so a
component kept alive only by a death-list mention or a test fixture fails.

``ui/shapes/`` is excluded from candidates: it is a vendored pure-JS shape
library consumed via directory-relative imports and the ``M3Shapes`` named
module (qualified usage pinned by other suites); its internals have no
type-name footprint by design.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL = REPO_ROOT / "shell"

# S0-4 sweeps executed these; the contract keeps them from sneaking back.
EXECUTED = (
    "ui/MaterialCard.qml",  # pre-M3 card chrome; LEGACY_VOCABULARY death-listed
    "ui/SidebarStagger.qml",  # last consumer died with the drawer demolition
    # autostart page companion; archived beside its only consumer
    "plugins/settings/AppBrowserPopup.qml",
    "ui/MaterialWaveProgressBar.qml",
    "ui/MediaControlBar.qml",
    "ui/MediaSourceIcon.qml",
    "ui/WaveProgressBar.qml",
)

_CANDIDATE_DIRS = ("ui", "plugins/settings")
_CORPUS_ROOTS = ("app", "plugins", "services", "commons", "ui", "scripts")


def _corpus():
    texts = []
    for root_name in _CORPUS_ROOTS:
        root = SHELL / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix not in (".qml", ".js", ".py", ".sh", ".toml"):
                continue
            if "__pycache__" in path.parts:
                continue
            try:
                texts.append((path, path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
    for extra in (SHELL / "shell.qml",):
        if extra.is_file():
            texts.append((extra, extra.read_text(encoding="utf-8")))
    return texts


def _flat_qml(directory: str) -> list[Path]:
    root = SHELL / directory
    return sorted(p for p in root.glob("*.qml") if p.is_file())


class TestExecutedStayOut(unittest.TestCase):
    def test_executed_assets_are_gone(self):
        for rel in EXECUTED:
            self.assertFalse((SHELL / rel).is_file(), f"{rel} must not come back")


class TestConsumerAlive(unittest.TestCase):
    """Every shipped component in the swept pools has a runtime consumer."""

    def test_flat_ui_pool_and_settings_root_have_consumers(self):
        corpus = _corpus()
        dead = []
        for directory in _CANDIDATE_DIRS:
            for path in _flat_qml(directory):
                name = path.stem
                pattern = re.compile(rf"\b{re.escape(name)}\b")
                consumed = any(
                    candidate != path and pattern.search(text)
                    for candidate, text in corpus
                )
                if not consumed:
                    dead.append(path.relative_to(SHELL).as_posix())
        self.assertEqual(dead, [], "zero-consumer components rotting the pools")
