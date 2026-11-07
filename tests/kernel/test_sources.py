"""Third-party plugin lifecycle (S1): sources ledger + add / remove / update.

The engine is its own plugin manager (plugin-model.md §5). Everything here
runs offline: git transport is exercised against plain local paths and
``file://`` URLs, and validation goes through the real loader — no mocks on
the code under test.
"""

import unittest
from pathlib import Path

from nyxuri.core import get_env
from nyxuri.kernel import ledger, registry, transaction
from nyxuri import sources
from tests.utils import TempEnv


def _git(dir_: Path, *args: str):
    import subprocess

    return subprocess.run(
        ["git", "-C", str(dir_), *args],
        capture_output=True, text=True, check=False,
    )


class SourceFixtureMixin:
    """Build disposable upstream plugin trees with real git history."""

    def _make_upstream(self, ctx, pid="io.github.test.cool", toml_body="") -> Path:
        src = ctx.home / "upstream" / pid
        src.mkdir(parents=True)
        (src / "manifest.toml").write_text(
            f'schemaVersion = 1\nid = "{pid}"\nkinds = ["config"]\n' + toml_body,
            encoding="utf-8",
        )
        (src / "payload.txt").write_text("v1\n", encoding="utf-8")
        _git(src, "init", "-q")
        _git(src, "config", "user.email", "test@local")
        _git(src, "config", "user.name", "test")
        _git(src, "add", "-A")
        _git(src, "commit", "-q", "-m", "init")
        return src

    def _commit_upstream(self, src: Path, name: str, content: str) -> str:
        (src / name).write_text(content, encoding="utf-8")
        _git(src, "add", "-A")
        _git(src, "commit", "-q", "-m", f"add {name}")
        return _git(src, "rev-parse", "HEAD").stdout.strip()

    def _add_git(self, ctx, upstream: Path) -> dict:
        return sources.add(f"file://{upstream}")

    def _landed(self, ctx, pid: str) -> Path:
        return ctx.env.data_dir / "plugins" / pid


class TestSourcesLedger(unittest.TestCase):
    """``sources`` top-level key + forget_plugin (账本唯一真相, no sidecar)."""

    def test_source_roundtrip_and_added_stamp(self):
        with TempEnv() as ctx:
            self.assertIsNone(ledger.get_source("io.github.test.cool"))
            first = ledger.set_source(
                "io.github.test.cool", url="file:///x", ref="main", commit="abc"
            )
            self.assertEqual(first["url"], "file:///x")
            added = first["added"]
            second = ledger.set_source(
                "io.github.test.cool", url="file:///y", ref="main", commit="def"
            )
            self.assertEqual(second["url"], "file:///y")
            self.assertEqual(second["added"], added, "added stamps only the first install")

    def test_forget_plugin_erases_every_trace(self):
        with TempEnv() as ctx:
            ledger.set_plugin(
                "io.github.test.cool", state="disabled", vault=None
            )
            ledger.set_source(
                "io.github.test.cool", url="u", ref="main", commit="c"
            )
            ledger.set_form_slot("io.github.test.cool", "glow", "off")
            ledger.forget_plugin("io.github.test.cool")
            self.assertIsNone(ledger.get_plugin("io.github.test.cool"))
            self.assertIsNone(ledger.get_source("io.github.test.cool"))
            self.assertEqual(ledger.get_form_slots("io.github.test.cool"), {})


class TestAdd(SourceFixtureMixin, unittest.TestCase):
    """add: land → validate through the loader → record origin. Default OFF."""

    def test_add_from_git_url_lands_and_records(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            result = self._add_git(ctx, upstream)
            pid = "io.github.test.cool"
            self.assertEqual(result["id"], pid)
            landed = self._landed(ctx, pid)
            self.assertTrue(landed.is_dir())
            self.assertIn(pid, registry.plugin_ids())
            self.assertEqual(registry.plugin_origin(pid), "third-party")
            origin = ledger.get_source(pid)
            self.assertEqual(origin["url"], f"file://{upstream}")
            upstream_ref = _git(upstream, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            self.assertEqual(origin["ref"], upstream_ref)
            self.assertEqual(
                origin["commit"], _git(upstream, "rev-parse", "HEAD").stdout.strip()
            )
            # Default OFF: installing never switches anything on.
            self.assertIsNone(ledger.get_plugin(pid))
            # A git-routed install keeps its transport.
            self.assertTrue((landed / ".git").exists())

    def test_add_from_local_dir_copies_without_git(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            result = sources.add(str(upstream))
            pid = result["id"]
            landed = self._landed(ctx, pid)
            self.assertTrue(landed.is_dir())
            self.assertFalse((landed / ".git").exists(), "local install strips transport")
            self.assertEqual(ledger.get_source(pid)["ref"], "")

    def test_add_conflict_refused(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            self._add_git(ctx, upstream)
            with self.assertRaisesRegex(ValueError, "already exists"):
                self._add_git(ctx, upstream)
            # The original install is untouched.
            self.assertIn("io.github.test.cool", registry.plugin_ids())

    def test_add_shape_refusals(self):
        with TempEnv() as ctx:
            for bad in ("shell.evil", "../evil", "bad/slash"):
                src = self._make_upstream(ctx, pid=bad)
                with self.assertRaises(ValueError):
                    self._add_git(ctx, src)
            self.assertEqual(
                [i for i in registry.plugin_ids() if i.startswith("shell.evil")], []
            )

    def test_add_bare_name_accepted(self):
        with TempEnv() as ctx:
            src = self._make_upstream(ctx, pid="cool-tool")
            res = self._add_git(ctx, src)
            self.assertEqual(res["id"], "cool-tool")
            self.assertIn("cool-tool", registry.plugin_ids())

    def test_add_hook_declaration_refused_and_rolled_back(self):
        """v1 三方拒钩子: the loader gate fires and the landing is undone."""
        with TempEnv() as ctx:
            upstream = self._make_upstream(
                ctx, toml_body='post_install = "setup"\n'
            )
            with self.assertRaisesRegex(ValueError, "lifecycle hooks"):
                self._add_git(ctx, upstream)
            self.assertFalse(
                self._landed(ctx, "io.github.test.cool").exists(),
                "a refused plugin must not leave a half-installed tree",
            )
            self.assertNotIn("io.github.test.cool", registry.plugin_ids())

    def test_add_staging_never_leaks_into_registry(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            self._add_git(ctx, upstream)
            leftovers = [
                p.name for p in (ctx.env.data_dir / "staging").iterdir()
            ] if (ctx.env.data_dir / "staging").is_dir() else []
            self.assertEqual(leftovers, [], "staging is cleaned up after landing")


class TestRemove(SourceFixtureMixin, unittest.TestCase):
    """remove: off → withdraw → timestamp backup for non-pristine trees."""

    def test_remove_pristine_git_tree_leaves_no_debris(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            self._add_git(ctx, upstream)
            result = sources.remove("io.github.test.cool")
            self.assertIsNone(result["backup"])
            self.assertFalse(self._landed(ctx, "io.github.test.cool").exists())
            self.assertNotIn("io.github.test.cool", registry.plugin_ids())
            self.assertIsNone(ledger.get_source("io.github.test.cool"))

    def test_remove_dirty_git_tree_timestamp_backup(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            self._add_git(ctx, upstream)
            landed = self._landed(ctx, "io.github.test.cool")
            (landed / "local-edit.txt").write_text("mine\n", encoding="utf-8")
            result = sources.remove("io.github.test.cool")
            backup = Path(result["backup"])
            self.assertTrue(backup.is_dir())
            self.assertTrue((backup / "local-edit.txt").exists())
            self.assertFalse(landed.exists())

    def test_remove_local_install_always_backed_up(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            sources.add(str(upstream))
            result = sources.remove("io.github.test.cool")
            self.assertTrue(Path(result["backup"]).is_dir())

    def test_remove_official_refused(self):
        with TempEnv() as ctx:
            with self.assertRaisesRegex(ValueError, "not a third-party plugin"):
                sources.remove("kitty")

    def test_remove_enabled_plugin_runs_off_first(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx, toml_body="packages = []\n")
            self._add_git(ctx, upstream)
            ledger.set_plugin("io.github.test.cool", state="enabled")
            result = sources.remove("io.github.test.cool")
            self.assertFalse(result["off_failed"])
            self.assertIsNone(ledger.get_plugin("io.github.test.cool"))
            self.assertFalse(self._landed(ctx, "io.github.test.cool").exists())


class TestUpdate(SourceFixtureMixin, unittest.TestCase):
    """update: ff-only gate → diff preview → loader validation → rollback."""

    def test_update_disabled_plugin_applies_and_records(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            self._add_git(ctx, upstream)
            new_commit = self._commit_upstream(upstream, "extra.txt", "v2\n")
            preview = sources.update("io.github.test.cool")
            self.assertIn("extra.txt", preview["diff"])
            applied = sources.update_apply("io.github.test.cool", preview)
            self.assertFalse(applied["redeployed"], "disabled plugins are not redeployed")
            landed = self._landed(ctx, "io.github.test.cool")
            self.assertTrue((landed / "extra.txt").exists())
            self.assertEqual(ledger.get_source("io.github.test.cool")["commit"], new_commit)

    def test_update_enabled_plugin_redeploys_through_transaction(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx, toml_body="packages = []\n")
            self._add_git(ctx, upstream)
            steps = transaction.plugin_on("io.github.test.cool", install_packages=None)
            self.assertTrue(steps and all(s.ok for s in steps))
            from nyxuri.deploy.deploy import config_item_dest
            living = config_item_dest("io.github.test.cool")
            self.assertTrue(living.is_dir(), "baseline deploy must exist first")
            self._commit_upstream(upstream, "extra.txt", "v2\n")
            preview = sources.update("io.github.test.cool")
            applied = sources.update_apply("io.github.test.cool", preview)
            self.assertTrue(applied["redeployed"])
            self.assertTrue(
                (living / "extra.txt").exists(),
                "the single activation pipeline re-applied the new blueprint",
            )

    def test_update_refuses_non_fast_forward(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            self._add_git(ctx, upstream)
            landed = self._landed(ctx, "io.github.test.cool")
            # A LOCAL commit diverges the installed tree from its origin —
            # upstream history never rewrites itself in this scenario.
            _git(landed, "config", "user.email", "local@local")
            _git(landed, "config", "user.name", "local")
            (landed / "local.txt").write_text("mine\n", encoding="utf-8")
            _git(landed, "add", "-A")
            _git(landed, "commit", "-q", "-m", "local")
            local_head = _git(landed, "rev-parse", "HEAD").stdout.strip()
            self._commit_upstream(upstream, "extra.txt", "v2\n")
            with self.assertRaisesRegex(ValueError, "not a fast-forward"):
                sources.update("io.github.test.cool")
            self.assertEqual(
                _git(landed, "rev-parse", "HEAD").stdout.strip(), local_head
            )

    def test_update_validation_failure_rolls_back(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            self._add_git(ctx, upstream)
            old = _git(upstream, "rev-parse", "HEAD").stdout.strip()
            # Upstream breaks its own manifest: unknown key → loader refuses.
            bad = self._commit_upstream(
                upstream, "manifest.toml",
                'schemaVersion = 1\nid = "io.github.test.cool"\nkinds = ["config"]\nboom = 1\n',
            )
            del bad
            preview = sources.update("io.github.test.cool")
            with self.assertRaisesRegex(ValueError, "rolled back"):
                sources.update_apply("io.github.test.cool", preview)
            landed = self._landed(ctx, "io.github.test.cool")
            self.assertEqual(
                _git(landed, "rev-parse", "HEAD").stdout.strip(), old,
                "the tree must be back on the last validated commit",
            )
            (landed / "manifest.toml").read_text(encoding="utf-8")  # intact tree

    def test_update_local_install_refused(self):
        with TempEnv() as ctx:
            upstream = self._make_upstream(ctx)
            sources.add(str(upstream))
            with self.assertRaisesRegex(ValueError, "local directory"):
                sources.update("io.github.test.cool")


if __name__ == "__main__":
    unittest.main()
