from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orbit_translate.config import parse_config
from orbit_translate.credentials import (
    CredentialError,
    make_secret_reference,
    resolve_key,
    store_key,
)


class KeyringReferenceTests(unittest.TestCase):
    def test_native_kwallet_is_preferred_to_secret_service(self) -> None:
        with patch("orbit_translate.credentials.shutil.which", side_effect=lambda name: "/usr/bin/" + name):
            self.assertEqual(make_secret_reference("provider-1"), "kwallet:provider-1")

    def test_secret_service_is_the_fallback_and_unsafe_ids_are_hashed(self) -> None:
        with patch(
            "orbit_translate.credentials.shutil.which",
            side_effect=lambda name: None if name == "kwallet-query" else "/usr/bin/secret-tool",
        ):
            reference = make_secret_reference("provider/with spaces")
        self.assertRegex(reference, r"^secret-service:[0-9a-f]{64}$")

    def test_missing_native_commands_fail_without_creating_a_fallback(self) -> None:
        with patch("orbit_translate.credentials.shutil.which", return_value=None):
            with self.assertRaises(CredentialError):
                make_secret_reference("provider")


class StoreKeyTests(unittest.TestCase):
    def test_kwallet_store_uses_stdin_and_fixed_folder(self) -> None:
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with (
            patch("orbit_translate.credentials.shutil.which", return_value="/usr/bin/kwallet-query"),
            patch("orbit_translate.credentials.subprocess.run", return_value=result) as run,
        ):
            store_key("kwallet:translate", "test-api-key")
        args, kwargs = run.call_args
        self.assertEqual(
            args[0],
            [
                "kwallet-query",
                "--write-password",
                "translate",
                "--folder",
                "Orbit Translate",
                "kdewallet",
            ],
        )
        self.assertEqual(kwargs["input"], "test-api-key")
        self.assertEqual(kwargs["timeout"], 45)
        self.assertNotIn("test-api-key", args[0])

    def test_secret_service_store_uses_stdin_and_stable_attributes(self) -> None:
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch("orbit_translate.credentials.subprocess.run", return_value=result) as run:
            store_key("secret-service:translate", "test-api-key")
        args, kwargs = run.call_args
        self.assertEqual(
            args[0],
            [
                "secret-tool",
                "store",
                "--label=Orbit Translate provider key",
                "application",
                "orbit-translate",
                "provider",
                "translate",
            ],
        )
        self.assertEqual(kwargs["input"], "test-api-key")
        self.assertEqual(kwargs["timeout"], 45)
        self.assertNotIn("test-api-key", args[0])

    def test_store_rejects_bad_reference_and_control_characters(self) -> None:
        for reference, value in (("/tmp/key", "key"), ("kwallet:bad/id", "key"), ("kwallet:id", "bad\nkey")):
            with self.subTest(reference=reference), self.assertRaises(CredentialError):
                store_key(reference, value)
        with self.assertRaises(CredentialError):
            store_key("kwallet:id", "")

    def test_failed_store_error_does_not_include_key_or_stderr(self) -> None:
        result = SimpleNamespace(returncode=1, stdout="", stderr="test-api-key failed")
        with patch("orbit_translate.credentials.subprocess.run", return_value=result):
            with self.assertRaises(CredentialError) as raised:
                store_key("kwallet:translate", "test-api-key")
        self.assertNotIn("test-api-key", str(raised.exception))
        self.assertNotIn("failed", str(raised.exception))


class ResolveKeyTests(unittest.TestCase):
    @staticmethod
    def _provider(**values: str):
        base = {"id": "test", "type": "openai_responses", "base_url": "https://api.example/v1", "model": "model"}
        return parse_config({"providers": [{**base, **values}]}).providers[0]

    def test_no_authentication_configuration_returns_empty(self) -> None:
        self.assertEqual(resolve_key(self._provider()), "")

    def test_environment_key_resolves_and_missing_environment_is_safe(self) -> None:
        provider = self._provider(api_key_env="ORBIT_TEST_KEY")
        with patch.dict("os.environ", {"ORBIT_TEST_KEY": "environment-key"}):
            self.assertEqual(resolve_key(provider), "environment-key")
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(CredentialError) as raised:
                resolve_key(provider)
        self.assertNotIn("environment-key", str(raised.exception))

    def test_secret_service_lookup_captures_stdout_without_putting_key_in_argv(self) -> None:
        provider = self._provider(api_key_secret="secret-service:test")
        result = SimpleNamespace(returncode=0, stdout="stored-key\n", stderr="")
        with patch("orbit_translate.credentials.subprocess.run", return_value=result) as run:
            self.assertEqual(resolve_key(provider), "stored-key")
        args, kwargs = run.call_args
        self.assertEqual(
            args[0],
            [
                "secret-tool",
                "lookup",
                "application",
                "orbit-translate",
                "provider",
                "test",
            ],
        )
        self.assertIsNone(kwargs["input"])
        self.assertEqual(kwargs["timeout"], 8)
        self.assertNotIn("stored-key", args[0])

    def test_missing_locked_and_failed_lookups_are_redacted(self) -> None:
        provider = self._provider(api_key_secret="kwallet:test")
        for status, stdout, stderr in (
            (1, "", "missing stored-key"),
            (2, "", "wallet locked stored-key"),
            (0, "", ""),
        ):
            result = SimpleNamespace(returncode=status, stdout=stdout, stderr=stderr)
            with self.subTest(status=status), patch("orbit_translate.credentials.subprocess.run", return_value=result):
                with self.assertRaises(CredentialError) as raised:
                    resolve_key(provider)
            self.assertNotIn("stored-key", str(raised.exception))
            self.assertNotIn("locked", str(raised.exception))

    def test_subprocess_timeout_is_safe(self) -> None:
        provider = self._provider(api_key_secret="kwallet:test")
        with patch("orbit_translate.credentials.subprocess.run", side_effect=TimeoutError("private output")):
            with self.assertRaises(CredentialError) as raised:
                resolve_key(provider)
        self.assertNotIn("private output", str(raised.exception))

    def test_resolved_key_control_characters_are_rejected(self) -> None:
        provider = self._provider(api_key_secret="kwallet:test")
        result = SimpleNamespace(returncode=0, stdout="bad\x1bkey", stderr="")
        with patch("orbit_translate.credentials.subprocess.run", return_value=result):
            with self.assertRaises(CredentialError):
                resolve_key(provider)

    def test_provider_model_representation_never_contains_resolved_key(self) -> None:
        provider = self._provider(api_key_secret="kwallet:test")
        result = SimpleNamespace(returncode=0, stdout="hidden-key", stderr="")
        with patch("orbit_translate.credentials.subprocess.run", return_value=result):
            resolved = resolve_key(provider)
        self.assertEqual(resolved, "hidden-key")
        self.assertNotIn(resolved, repr(provider))


if __name__ == "__main__":
    unittest.main()
