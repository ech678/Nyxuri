from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

from copy import deepcopy
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from orbit_translate.config import ConfigError
from orbit_translate.providers import ProviderOutcome
from orbit_translate.settings import SettingsDocument, SettingsError


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="orbit settings ")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "translate__custom__.toml"
        self.original = b'''# keep the original in backup
source = "en"
target = "zh-CN"
max_cards = 2
custom = { note = "unmodified", values = [1, 2] }
[[providers]]
id = "memory"
name = "MyMemory"
type = "mymemory"
enabled = true
extra = ["preserve", "me"]
'''
        self.path.write_bytes(self.original)

    def test_toggle_save_backup_and_roundtrip_preserve_unedited_values(self) -> None:
        document = SettingsDocument(self.path)
        before = deepcopy(document.data)
        document.toggle(0)
        self.assertTrue(document.dirty)
        self.assertEqual(self.path.read_bytes(), self.original)
        backup = document.save()
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertEqual(os.stat(backup).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        before["providers"][0]["enabled"] = False
        self.assertEqual(tomllib.loads(self.path.read_text()), before)
        self.assertFalse(document.dirty)
        self.assertIsNone(document.save())

    def test_discard_and_noop_do_not_rewrite_comments(self) -> None:
        document = SettingsDocument(self.path)
        self.assertIsNone(document.save())
        document.toggle(0)
        document.toggle(0)
        self.assertFalse(document.dirty)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_invalid_edit_is_rejected_without_mutation(self) -> None:
        document = SettingsDocument(self.path)
        before = deepcopy(document.data)
        with self.assertRaises(ConfigError):
            document.put_provider(0, {"type": "unknown"})
        self.assertEqual(document.data, before)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_duplicate_provider_is_rejected(self) -> None:
        document = SettingsDocument(self.path)
        with self.assertRaises(ConfigError):
            document.put_provider(None, dict(document.providers[0]))
        self.assertEqual(len(document.providers), 1)

    def test_new_and_deleted_providers_roundtrip(self) -> None:
        document = SettingsDocument(self.path)
        document.put_provider(None, {"id": "other", "type": "google", "enabled": False})
        document.delete_provider(0)
        document.save()
        self.assertEqual(SettingsDocument(self.path).config.providers[0].id, "other")
        document.delete_provider(0)
        document.save()
        self.assertFalse(SettingsDocument(self.path).providers)

    def test_external_change_is_not_overwritten(self) -> None:
        document = SettingsDocument(self.path)
        document.toggle(0)
        replacement = self.original + b"\n# external edit\n"
        self.path.write_bytes(replacement)
        with self.assertRaises(SettingsError):
            document.save()
        self.assertEqual(self.path.read_bytes(), replacement)

    def test_replace_failure_keeps_original_and_backup(self) -> None:
        document = SettingsDocument(self.path)
        document.toggle(0)
        with patch("orbit_translate.settings.os.replace", side_effect=OSError("fixture")):
            with self.assertRaises(SettingsError):
                document.save()
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(len(list(self.path.parent.glob("*.backup-*"))), 1)
        self.assertFalse(list(self.path.parent.glob(".translate*")))

    def test_probe_uses_explicit_example_even_when_channel_disabled(self) -> None:
        document = SettingsDocument(self.path)
        document.toggle(0)
        success = ProviderOutcome("memory", "MyMemory", text="fixture translation")
        with patch("orbit_translate.settings.translate_provider", return_value=success) as translate:
            self.assertIs(document.probe(0), success)
        self.assertEqual(translate.call_args.args[1:4], ("Hello world", "en", "zh-CN"))
        self.assertFalse(translate.call_args.args[0].enabled)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_save_syncs_directory_after_replace(self) -> None:
        import stat

        document = SettingsDocument(self.path)
        document.toggle(0)
        events = []
        real_replace, real_fsync = os.replace, os.fsync

        def replace(*args):
            events.append("replace")
            real_replace(*args)

        def sync(descriptor):
            events.append("directory" if stat.S_ISDIR(os.fstat(descriptor).st_mode) else "file")
            real_fsync(descriptor)

        with patch("orbit_translate.settings.os.replace", side_effect=replace), patch("orbit_translate.settings.os.fsync", side_effect=sync):
            document.save()
        self.assertEqual(events, ["file", "file", "replace", "directory"])

    def test_directory_sync_failure_reports_replaced_file_truthfully(self) -> None:
        import stat

        document = SettingsDocument(self.path)
        document.toggle(0)
        real_fsync = os.fsync

        def sync(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError("fixture disk failure")
            real_fsync(descriptor)

        with patch("orbit_translate.settings.os.fsync", side_effect=sync), self.assertRaisesRegex(SettingsError, "配置已替换"):
            document.save()
        self.assertFalse(SettingsDocument(self.path).providers[0]["enabled"])
        self.assertFalse(document.dirty)
        self.assertEqual(len(list(self.path.parent.glob("*.backup-*"))), 1)

    def test_key_goes_to_keyring_only(self) -> None:
        document = SettingsDocument(self.path)
        marker = "not-a-real-credential-fixture"
        with patch("orbit_translate.settings.make_secret_reference", return_value="kwallet:memory"), patch("orbit_translate.settings.store_key") as store:
            document.set_key(0, marker)
        store.assert_called_once_with("kwallet:memory", marker)
        self.assertEqual(document.providers[0]["api_key_secret"], "kwallet:memory")
        self.assertNotIn(marker, repr(document.data))
        document.save()
        self.assertNotIn(marker.encode(), self.path.read_bytes())

    def test_failed_key_write_does_not_change_config(self) -> None:
        document = SettingsDocument(self.path)
        before = deepcopy(document.data)
        with patch("orbit_translate.settings.make_secret_reference", return_value="kwallet:memory"), patch("orbit_translate.settings.store_key", side_effect=SettingsError("钥匙串不可用")):
            with self.assertRaises(SettingsError):
                document.set_key(0, "fixture")
        self.assertEqual(document.data, before)

    def test_keychain_wait_does_not_drop_intervening_edits(self) -> None:
        document = SettingsDocument(self.path)
        with patch("orbit_translate.settings.make_secret_reference", return_value="kwallet:memory"), patch("orbit_translate.settings.store_key", side_effect=lambda *_: document.toggle(0)):
            document.set_key(0, "fixture")
        self.assertFalse(document.providers[0]["enabled"])
        self.assertEqual(document.providers[0]["api_key_secret"], "kwallet:memory")

    def test_unsupported_value_does_not_destroy_original(self) -> None:
        document = SettingsDocument(self.path)
        document.data["unsupported"] = float("nan")
        with self.assertRaises(SettingsError):
            document.save()
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_empty_example_is_rejected_without_request(self) -> None:
        document = SettingsDocument(self.path)
        with patch("orbit_translate.settings.translate_provider") as translate:
            with self.assertRaises(SettingsError):
                document.probe(0, text="  ")
        translate.assert_not_called()

    def test_symlink_is_not_replaced(self) -> None:
        link = self.path.parent / "link.toml"
        link.symlink_to(self.path)
        document = SettingsDocument(link)
        document.toggle(0)
        with self.assertRaises(SettingsError):
            document.save()
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.path.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
