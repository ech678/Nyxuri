import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


class TestMigrations(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__()

    def test_runner_is_idempotent_and_records_level(self):
        from nyxniri import migrations

        with patch.object(migrations, "TOMBSTONES", (".cache/obsolete",)):
            old = self.ctx.home / ".cache/obsolete"
            old.parent.mkdir(parents=True, exist_ok=True)
            old.write_text("old", encoding="utf-8")
            self.assertTrue(migrations.run())
            self.assertFalse(old.exists())
            self.assertTrue(migrations.run())
        ledger = json.loads((self.ctx.env.state_dir / "state.json").read_text())
        self.assertEqual(ledger["migration_level"], migrations.MIGRATION_LEVEL)

    def test_tombstone_cannot_escape_home(self):
        from nyxniri import migrations

        outside = Path("/tmp/nyxniri-migration-test-outside")
        with patch.object(migrations, "TOMBSTONES", ("../nyxniri-migration-test-outside",)):
            self.assertFalse(migrations.run())
        self.assertFalse(outside.exists())

    def test_update_ledger_merges_nested_dicts(self):
        from nyxniri.state.ledger import read_ledger, update_ledger

        update_ledger(modules={"fcitx": True})
        update_ledger(modules={"fisher": True})
        ledger = read_ledger()
        self.assertEqual(ledger["modules"], {"fcitx": True, "fisher": True})


if __name__ == "__main__":
    unittest.main()
