"""Behavior contracts for deploy: atomic replace rollback, broken symlink, no-clobber.

Safety: all tests use tempfile.TemporaryDirectory for filesystem operations.
No test touches the real ~/.config or the real repo configs/ directory.
"""

import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import io
import json
import time



class TestAtomicReplaceFileRollback(unittest.TestCase):
    """If the 2nd rename fails, dest must be restored from old_dest."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_file_replace_rollback_on_second_rename_failure(self):
        """If tmp_file.rename(dest) fails, dest must be restored from old_dest."""
        from nyxuri.deploy.atomic import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "src.txt"
            src.write_text("new")
            dest = workdir / "dest.txt"
            dest.write_text("original")

            original_rename = Path.rename

            def fail_second_rename(self_path, target):
                if ".new." in self_path.name and target == dest:
                    raise OSError("simulated rename failure")
                return original_rename(self_path, target)

            with patch.object(Path, "rename", fail_second_rename):
                result = atomic_replace_item(src, dest)

            self.assertFalse(result, "Should return False on failure")
            self.assertTrue(dest.exists(), "dest must still exist (restored)")
            self.assertEqual(dest.read_text(), "original",
                             "dest content must be the original, not 'new'")

    def test_file_replace_normal_success(self):
        """Normal file replace should succeed."""
        from nyxuri.deploy.atomic import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "src.txt"
            src.write_text("new content")
            dest = workdir / "dest.txt"
            dest.write_text("old content")

            result = atomic_replace_item(src, dest)
            self.assertTrue(result)
            self.assertEqual(dest.read_text(), "new content")


class TestAtomicReplaceDirRollback(unittest.TestCase):
    """Directory atomic replace must also rollback on failure."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_dir_replace_rollback_on_rename_failure(self):
        """If tmp_new.rename(dest) fails, dest must be restored from old_dest."""
        from nyxuri.deploy.atomic import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "srcdir"
            src.mkdir()
            (src / "file.txt").write_text("new")
            dest = workdir / "dest_dir"
            dest.mkdir()
            (dest / "old.txt").write_text("original")

            original_rename = Path.rename

            def fail_final_rename(self_path, target):
                if ".new." in self_path.name and target == dest:
                    raise OSError("simulated dir rename failure")
                return original_rename(self_path, target)

            with patch.object(Path, "rename", fail_final_rename):
                result = atomic_replace_item(src, dest)

            self.assertFalse(result)
            self.assertTrue(dest.exists(), "dest must be restored")
            self.assertTrue((dest / "old.txt").exists(),
                            "Original content must survive rollback")


class TestEffectsSymlinkBroken(unittest.TestCase):
    """A broken effects.kdl symlink should be detected and recreated."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_broken_symlink_condition(self):
        """The deploy condition for broken symlinks must fire correctly.

        Tests in a temp directory — never touches the real repo.
        """
        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            effects_normal = workdir / "effects_normal.kdl"
            effects_normal.write_text("// normal")
            effects_sym = workdir / "effects.kdl"

            effects_sym.symlink_to(workdir / "effects_eyecare.kdl")

            self.assertTrue(effects_normal.is_file())
            self.assertFalse(effects_sym.exists(),
                             "Broken symlink should not exist() — triggers recreation")
            self.assertTrue(effects_sym.is_symlink())

            if effects_normal.is_file() and not effects_sym.exists():
                effects_sym.unlink(missing_ok=True)
                effects_sym.symlink_to(effects_normal)

            self.assertTrue(effects_sym.exists())
            self.assertEqual(effects_sym.resolve(), effects_normal.resolve())


class TestPreserveInjectionBeforeSwap(unittest.TestCase):
    """manifest preserve files must be in tmp_new BEFORE rename — no post-swap window."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_preserve_file_survives_swap_with_user_content(self):
        """preserve=["monitor.kdl"] → dest/monitor.kdl keeps user's content, not repo's."""
        from nyxuri.deploy.atomic import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "srcdir"
            src.mkdir()
            (src / "config.kdl").write_text("new config")
            (src / "monitor.kdl").write_text("repo default")  # would clobber user's

            dest = workdir / "dest_dir"
            dest.mkdir()
            (dest / "config.kdl").write_text("old config")
            (dest / "monitor.kdl").write_text("user monitors")  # must survive

            result = atomic_replace_item(src, dest, preserve=["monitor.kdl"])

            self.assertTrue(result)
            self.assertEqual((dest / "config.kdl").read_text(), "new config")
            self.assertEqual((dest / "monitor.kdl").read_text(), "user monitors",
                             "preserve file must keep user content, not repo default")

    def test_preserve_skipped_when_dest_file_missing(self):
        """preserve on a non-existent file is a no-op, swap still succeeds."""
        from nyxuri.deploy.atomic import atomic_replace_item

        with tempfile.TemporaryDirectory() as workdir:
            workdir = Path(workdir)
            src = workdir / "srcdir"
            src.mkdir()
            (src / "config.kdl").write_text("new")

            dest = workdir / "dest_dir"
            dest.mkdir()
            (dest / "config.kdl").write_text("old")

            result = atomic_replace_item(src, dest, preserve=["monitor.kdl"])

            self.assertTrue(result)
            self.assertFalse((dest / "monitor.kdl").exists(),
                             "No monitor.kdl in dest → repo's (absent) ships, no crash")


class TestPreserveValuesAcrossSwap(unittest.TestCase):
    """manifest preserve_values must carry individual keys into the staged tree."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _swap(self, src_text, dest_text, keys, rel="app-config.toml"):
        from nyxuri.deploy.atomic import atomic_replace_item

        workdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, workdir, True)
        src = workdir / "srcdir"
        src.mkdir()
        (src / rel).write_text(src_text)
        (src / "extra.conf").write_text("shipped")
        dest = workdir / "dest_dir"
        dest.mkdir()
        if dest_text is not None:
            (dest / rel).write_text(dest_text)
        result = atomic_replace_item(src, dest, preserve_values={rel: keys})
        self.assertTrue(result)
        return (dest / rel).read_text()

    def test_user_value_survives_swap(self):
        """The shipped default must not clobber a value the user turned on."""
        text = self._swap(
            "[brightness]\nenable_ddcutil = false\nother = 2\n",
            "[brightness]\nenable_ddcutil = true\nother = 1\n",
            ["enable_ddcutil"],
        )
        self.assertIn("enable_ddcutil = true", text)
        self.assertNotIn("enable_ddcutil = false", text)

    def test_missing_key_falls_back_to_shipped_default(self):
        """A key the user never set must keep the shipped value."""
        text = self._swap(
            "[brightness]\nenable_ddcutil = false\n",
            "[brightness]\nother = 1\n",
            ["enable_ddcutil"],
        )
        self.assertIn("enable_ddcutil = false", text)

    def test_missing_dest_file_falls_back_to_shipped_default(self):
        """First deploy has nothing to carry → the shipped value ships."""
        text = self._swap(
            "[brightness]\nenable_ddcutil = false\n",
            None,
            ["enable_ddcutil"],
        )
        self.assertIn("enable_ddcutil = false", text)

    def test_undeclared_keys_still_come_from_the_shipped_file(self):
        """Only declared keys carry over; every other line updates normally."""
        text = self._swap(
            "[brightness]\nenable_ddcutil = false\nother = 2\n",
            "[brightness]\nenable_ddcutil = true\nother = 1\n",
            ["enable_ddcutil"],
        )
        self.assertIn("other = 2", text)
        self.assertNotIn("other = 1", text)

    def test_comment_and_formatting_of_shipped_file_are_kept(self):
        """The swap must not graft the outgoing file's comments onto the new one."""
        text = self._swap(
            "[brightness]\n# shipped note\nenable_ddcutil = false\n",
            "[brightness]\n# user note\nenable_ddcutil = true\n",
            ["enable_ddcutil"],
        )
        self.assertIn("# shipped note", text)
        self.assertNotIn("# user note", text)

    def test_same_key_name_in_another_section_is_untouched(self):
        """Carrying is section-scoped, so an unrelated homonym cannot be rewritten."""
        text = self._swap(
            "[a]\nenabled = false\n\n[b]\nenabled = false\n",
            "[a]\nenabled = true\n\n[b]\nenabled = false\n",
            ["enabled"],
        )
        self.assertIn("[a]\nenabled = true", text)
        self.assertIn("[b]\nenabled = false", text)

    def test_absent_key_in_shipped_file_is_not_appended(self):
        """A key the shipped file dropped stays dropped instead of being re-added."""
        text = self._swap(
            "[brightness]\nremoved = true\n",
            "[brightness]\nenable_ddcutil = true\n",
            ["enable_ddcutil"],
        )
        self.assertNotIn("enable_ddcutil", text)

    def test_declared_target_absent_from_staged_tree_is_skipped(self):
        """A declared path that the shipped tree does not contain is ignored."""
        from nyxuri.deploy.atomic import atomic_replace_item

        workdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, workdir, True)
        src = workdir / "srcdir"
        src.mkdir()
        (src / "app-config.toml").write_text("[brightness]\nenable_ddcutil = false\n")
        dest = workdir / "dest_dir"
        dest.mkdir()
        (dest / "app-config.toml").write_text("[brightness]\nenable_ddcutil = true\n")

        result = atomic_replace_item(
            src, dest, preserve_values={"gone.toml": ["enable_ddcutil"]})

        self.assertTrue(result)
        self.assertEqual((dest / "app-config.toml").read_text(),
                         "[brightness]\nenable_ddcutil = false\n")

    def test_declared_target_cannot_escape_the_staged_tree(self):
        """A traversal path must be refused rather than read from outside."""
        from nyxuri.deploy.atomic import atomic_replace_item

        workdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, workdir, True)
        src = workdir / "srcdir"
        src.mkdir()
        (src / "app-config.toml").write_text("[brightness]\nenable_ddcutil = false\n")
        dest = workdir / "dest_dir"
        dest.mkdir()
        (dest / "app-config.toml").write_text("[brightness]\nenable_ddcutil = true\n")
        (workdir / "outside.toml").write_text("[brightness]\nenable_ddcutil = true\n")

        result = atomic_replace_item(
            src, dest, preserve_values={"../outside.toml": ["enable_ddcutil"]})

        self.assertTrue(result)
        self.assertEqual((dest / "app-config.toml").read_text(),
                         "[brightness]\nenable_ddcutil = false\n")


class TestNiriRequiredIncludes(unittest.TestCase):
    """Every non-optional include in niri's config.kdl must exist in the repo.

    niri fails to load the whole config when a required include is missing, so a
    fresh install would break on a file the repo never shipped.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.niri_src = self.env.plugins_src / "niri"

    def tearDown(self):
        self._ctx.__exit__()

    def _required_includes(self):
        text = (self.niri_src / "config.kdl").read_text(encoding="utf-8")
        return [
            m.group(1)
            for m in re.finditer(r'include\s+(?:optional=true\s+)?"([^"]+)"', text)
            if "optional=true" not in m.group(0)
        ]

    def test_all_required_includes_exist_in_source(self):
        required = self._required_includes()
        self.assertIn("effects.kdl", required)
        for name in required:
            self.assertTrue(
                (self.niri_src / name).exists(),
                f"config.kdl requires {name} but the repo does not ship it",
            )

    def test_effects_kdl_is_eyecare_symlink(self):
        link = self.niri_src / "effects.kdl"
        self.assertTrue(link.is_symlink(), "effects.kdl must stay a runtime-managed symlink")
        self.assertEqual(os.readlink(link), "effects_normal.kdl")
        self.assertTrue(link.exists(), "symlink must resolve to a shipped file")

    def test_required_includes_survive_fresh_deploy(self):
        from nyxuri.deploy.deploy import deploy_selected_configs

        with patch("nyxuri.deploy.deploy._phase_post_install_services"), \
             patch("builtins.print"):
            deploy_selected_configs(do_backup=False, items_to_deploy=["niri"])

        dest = self.env.config_dir / "niri"
        for name in self._required_includes():
            self.assertTrue(
                (dest / name).exists(),
                f"fresh deploy left {name} missing; niri would fail to load",
            )
        deployed = dest / "effects.kdl"
        self.assertTrue(deployed.is_symlink())
        self.assertEqual(os.readlink(deployed), "effects_normal.kdl")


class TestWallpapersUnit(unittest.TestCase):
    """The wallpapers plugin: merge semantics over a shared living area.

    on = no-clobber blueprint fallback; off = withdraw only laid files;
    the pack and the user's own wallpapers are never eaten, never tracked.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def _wp_dest(self):
        return self.env.home / "Pictures" / "Wallpapers"

    def test_on_lays_fallback_and_records_ledger(self):
        from nyxuri.kernel import ledger, transaction

        steps = transaction.plugin_on("wallpapers")
        self.assertTrue(all(s.ok for s in steps), steps)
        dest = self._wp_dest()
        self.assertTrue((dest / "lawson_fuji.webp").is_file())
        rec = ledger.get_plugin("wallpapers")
        self.assertEqual(rec["state"], "enabled")
        self.assertIn("lawson_fuji.webp", rec["files"])

    def test_on_never_clobbers_user_content(self):
        from nyxuri.kernel import ledger, transaction

        dest = self._wp_dest()
        dest.mkdir(parents=True, exist_ok=True)
        user_wp = dest / "lawson_fuji.webp"
        user_wp.write_bytes(b"USER OWN IMAGE")

        steps = transaction.plugin_on("wallpapers")
        self.assertTrue(all(s.ok for s in steps), steps)
        self.assertEqual(user_wp.read_bytes(), b"USER OWN IMAGE",
                         "merge deploy must never overwrite existing files")
        # The blocked file is not ours: not in the laid snapshot.
        self.assertNotIn("lawson_fuji.webp", ledger.get_plugin("wallpapers")["files"])

    def test_off_withdraws_only_laid_files(self):
        from nyxuri.kernel import transaction

        dest = self._wp_dest()
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "my_own.webp").write_bytes(b"USER")
        transaction.plugin_on("wallpapers")
        (dest / "pack_video.mp4").write_bytes(b"PACK")  # arrives after on

        steps = transaction.plugin_off("wallpapers")
        self.assertTrue(all(s.ok for s in steps), steps)
        self.assertFalse((dest / "lawson_fuji.webp").exists(),
                         "laid fallback must be withdrawn")
        self.assertEqual((dest / "my_own.webp").read_bytes(), b"USER")
        self.assertTrue((dest / "pack_video.mp4").exists(),
                        "pack content is user-domain and survives off")
        self.assertIn("pack_video.mp4", steps[-1].detail,
                      "foreign survivors must be reported")

    def test_disabled_shared_area_is_not_ghost(self):
        from nyxuri.kernel import transaction

        dest = self._wp_dest()
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "my_own.webp").write_bytes(b"USER")
        transaction.plugin_on("wallpapers")
        transaction.plugin_off("wallpapers")

        report = transaction.audit_plugins("wallpapers")
        self.assertEqual(report.get("wallpapers"), transaction.STATE_SYNCED,
                         "user content in a shared area is not residue")

    def test_blueprint_named_residue_is_ghost(self):
        from nyxuri.kernel import transaction

        dest = self._wp_dest()
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "lawson_fuji.webp").write_bytes(b"OLD FALLBACK RESIDUE")

        report = transaction.audit_plugins("wallpapers")
        self.assertEqual(report.get("wallpapers"), transaction.STATE_GHOST)


class TestOwnershipCarry(unittest.TestCase):
    """Issue #139: a swap never destroys what the engine cannot explain.

    The verdict is judged against the caller-injected ledger baseline
    (hashes of what the engine last laid); atomic.py itself never reads
    the ledger (star layering). Dunder / preserve / preserve_values keep
    their own mechanisms and are exempt from carry.
    """

    def setUp(self):
        from nyxuri.deploy.atomic import atomic_replace_item
        self._replace = staticmethod(atomic_replace_item)

    @staticmethod
    def _hash(content: str) -> str:
        import hashlib
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _stage(self, workdir: Path, files: dict) -> Path:
        src = workdir / "src"
        src.mkdir(exist_ok=True)
        for rel, content in files.items():
            p = src / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return src

    def test_untouched_file_follows_template_update(self):
        """dest == baseline → engine-laid and untouched → template wins."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("v1\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True,
                carry_baseline={"a.conf": self._hash("v1\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")
            self.assertEqual(carried, {})

    def test_user_modified_file_is_carried(self):
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("my edit\n", encoding="utf-8")
            carried: dict = {}
            log: list = []
            self.assertTrue(self._replace(
                src, dest, preserved_log=log, carry=True,
                carry_baseline={"a.conf": self._hash("v1\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertEqual((dest / "a.conf").read_text(), "my edit\n")
            self.assertEqual(carried, {"a.conf": "modified"})
            self.assertTrue(log, "carried files must surface in the report")

    def test_user_extra_file_survives_every_stance(self):
        """A file outside the payload is the user's — carried even on adoption."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("v1\n", encoding="utf-8")
            (dest / "zz-tools.fish").write_text("atuin init\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True,
                carry_baseline={"a.conf": self._hash("v1\n")},
                carry_unknown=False, carried_out=carried,
            ))
            self.assertEqual((dest / "zz-tools.fish").read_text(), "atuin init\n")
            self.assertEqual(carried, {"zz-tools.fish": "user"})
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")

    def test_ghost_dest_update_carries_payload(self):
        """No record (Ghost) + update stance: 宁可错保 — nothing is overwritten."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n", "new.conf": "n\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("v3-era\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True, carry_baseline=None,
                carry_unknown=True, carried_out=carried,
            ))
            self.assertEqual((dest / "a.conf").read_text(), "v3-era\n")
            self.assertEqual(carried, {"a.conf": "unknown"},
                             "Ghost provenance is reported as unknown, never as the user's edit")
            self.assertEqual((dest / "new.conf").read_text(), "n\n",
                             "template-new files still land")

    def test_adoption_claims_payload_names(self):
        """No record + adoption stance (install/on): payload names are claimed."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("pre-existing\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True, carry_baseline=None,
                carry_unknown=False, carried_out=carried,
            ))
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")
            self.assertEqual(carried, {})

    def test_carry_off_keeps_plain_swap_semantics(self):
        """carry=False (--force / rollback): template wins, nothing reported."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("my edit\n", encoding="utf-8")
            (dest / "extra.conf").write_text("user\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(src, dest, carried_out=carried))
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")
            self.assertFalse((dest / "extra.conf").exists())
            self.assertEqual(carried, {})

    def test_carried_file_stays_carred_on_repeat_updates(self):
        """A stale baseline keeps protecting the carried file — no self-heal lie."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("my edit\n", encoding="utf-8")
            baseline = {"a.conf": self._hash("v1\n")}
            for _ in range(2):
                carried: dict = {}
                self.assertTrue(self._replace(
                    src, dest, carry=True, carry_baseline=baseline,
                    carry_unknown=True, carried_out=carried,
                ))
                self.assertEqual((dest / "a.conf").read_text(), "my edit\n")
                self.assertEqual(carried, {"a.conf": "modified"})

    def test_single_file_unit_carry(self):
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = wd / "src.toml"
            src.write_text("v2\n", encoding="utf-8")
            dest = wd / "starship.toml"
            dest.write_text("my edit\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True,
                carry_baseline={"starship.toml": self._hash("v1\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertEqual(dest.read_text(), "my edit\n")
            self.assertEqual(carried, {"starship.toml": "modified"})

            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True, carry_baseline=None,
                carry_unknown=False, carried_out=carried,
            ))
            self.assertEqual(dest.read_text(), "v2\n")
            self.assertEqual(carried, {})

    def test_hook_products_retire_when_not_laid_again(self):
        """Baseline-known, untouched, not in this payload → engine didn't lay
        it this time (hook product): it retires with the swap and the hook
        replay re-lays it — it is not the user's, so it is not carried."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("v1\n", encoding="utf-8")
            fisher = dest / "functions/fisher.fish"
            fisher.parent.mkdir(parents=True)
            fisher.write_text("hook product\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True,
                carry_baseline={"a.conf": self._hash("v1\n"),
                                "functions/fisher.fish": self._hash("hook product\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertFalse((dest / "functions/fisher.fish").exists(),
                             "retired engine products must not masquerade as user files")
            self.assertEqual(carried, {})
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")

    def test_retired_name_but_user_modified_is_carried(self):
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("v1\n", encoding="utf-8")
            fisher = dest / "functions/fisher.fish"
            fisher.parent.mkdir(parents=True)
            fisher.write_text("user tweaked\n", encoding="utf-8")
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True,
                carry_baseline={"a.conf": self._hash("v1\n"),
                                "functions/fisher.fish": self._hash("hook product\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertEqual((dest / "functions/fisher.fish").read_text(), "user tweaked\n")
            self.assertEqual(carried, {"functions/fisher.fish": "modified"})

    def test_pycache_never_carried_or_reported(self):
        """Bytecode cache is neither payload nor user content (#139 field
        report): pruned from the carry walk, gone with the swap, absent from
        the report."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("v1\n", encoding="utf-8")
            pyc_dir = dest / "tools/__pycache__"
            pyc_dir.mkdir(parents=True)
            (pyc_dir / "config.cpython-314.pyc").write_bytes(b"\x00bytecode")
            (dest / "tools/loose.pyc").write_bytes(b"\x00bytecode")
            carried: dict = {}
            log: list = []
            self.assertTrue(self._replace(
                src, dest, preserved_log=log, carry=True,
                carry_baseline={"a.conf": self._hash("v1\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertFalse(pyc_dir.exists())
            self.assertFalse((dest / "tools/loose.pyc").exists())
            self.assertEqual(carried, {})
            self.assertFalse(any(".pyc" in line or "__pycache__" in line for line in log))

    def test_directory_preserve_injects_tree_and_shields_carry(self):
        """A preserve DIRECTORY is a whole runtime-managed tree (#139 field
        report): injected before the rename in one piece, its files shielded
        from carry — they are Fisher's, not the user's, and not residue."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {"a.conf": "v2\n"})  # template lays no functions/
            dest = wd / "dest"
            dest.mkdir()
            (dest / "a.conf").write_text("v1\n", encoding="utf-8")
            fisher = dest / "functions/fisher.fish"
            fisher.parent.mkdir(parents=True)
            fisher.write_text("fisher plugin\n", encoding="utf-8")
            carried: dict = {}
            log: list = []
            self.assertTrue(self._replace(
                src, dest, preserved_log=log, carry=True,
                preserve=["functions"],
                carry_baseline={"a.conf": self._hash("v1\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertEqual((dest / "functions/fisher.fish").read_text(), "fisher plugin\n")
            self.assertEqual(carried, {}, "preserved tree files must not enter the carry map")
            self.assertEqual([line for line in log if "functions" in line],
                             ["~/.config/dest/functions"],
                             "a preserved tree reports once, not per file")

    def test_preserve_and_values_targets_exempt_from_carry(self):
        """preserve / preserve_values files ride their own mechanisms."""
        with tempfile.TemporaryDirectory() as wd:
            wd = Path(wd)
            src = self._stage(wd, {
                "monitor.kdl": "template monitor\n",
                "settings.toml": "[brightness]\nenable_ddcutil = false\n",
            })
            dest = wd / "dest"
            dest.mkdir()
            (dest / "monitor.kdl").write_text("user monitor layout\n", encoding="utf-8")
            (dest / "settings.toml").write_text(
                "[brightness]\nenable_ddcutil = true\n", encoding="utf-8"
            )
            carried: dict = {}
            self.assertTrue(self._replace(
                src, dest, carry=True,
                preserve=["monitor.kdl"],
                preserve_values={"settings.toml": ["enable_ddcutil"]},
                carry_baseline={"monitor.kdl": self._hash("old\n"),
                                "settings.toml": self._hash("old\n")},
                carry_unknown=True, carried_out=carried,
            ))
            self.assertEqual(carried, {}, "exempt files never enter the carry map")
            self.assertEqual((dest / "monitor.kdl").read_text(), "user monitor layout\n")
            self.assertIn("enable_ddcutil = true", (dest / "settings.toml").read_text())


if __name__ == "__main__":
    unittest.main()


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestWallpaperPackProbe(unittest.TestCase):
    """wallpapers_pack_present: video-validated pack probe (user-domain)."""

    def test_pack_requires_a_real_video(self):
        from nyxuri.deploy.deploy import WALLPAPER_VIDEO_SUFFIXES, wallpapers_pack_present
        with TempEnv() as ctx:
            video_dir = ctx.home / "Pictures" / "Wallpapers" / "video"
            self.assertFalse(wallpapers_pack_present())
            video_dir.mkdir(parents=True)
            (video_dir / "README.md").write_text("docs", encoding="utf-8")
            self.assertFalse(wallpapers_pack_present())
            clip = video_dir / "clip.mp4"
            clip.write_text("v", encoding="utf-8")
            self.assertTrue(clip.suffix in WALLPAPER_VIDEO_SUFFIXES)
            self.assertTrue(wallpapers_pack_present())

    def test_existing_user_wallpaper_is_never_clobbered_or_tracked(self):
        from nyxuri.kernel import ledger, transaction
        with TempEnv() as ctx:
            wp = ctx.home / "Pictures" / "Wallpapers"
            wp.mkdir(parents=True)
            user_file = wp / "lawson_fuji.webp"
            user_file.write_text("USER", encoding="utf-8")
            _quiet(transaction.plugin_on, "wallpapers")
            # No tracking marker exists at all — the pack era is over.
            self.assertFalse((wp / ".nyxuri-managed.json").exists())
            self.assertEqual(user_file.read_text(encoding="utf-8"), "USER")
            # The user's same-named file blocked the layout: not ours.
            self.assertNotIn("lawson_fuji.webp", ledger.get_plugin("wallpapers")["files"])

class TestDeployRobustness(unittest.TestCase):

    def _sandbox(self, ctx):
        ctx.env.plugins_src = Path(tempfile.mkdtemp())
        import nyxuri.deploy.manifest as manifest
        import nyxuri.deploy.deploy as deploy
        manifest._MANIFEST_CACHE = None
        deploy._CONFIG_ITEMS_CACHE = []
        return ctx.env.plugins_src

    def _app(self, src, name, manifest_toml, files):
        root = src / name
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        (root / "manifest.toml").write_text(manifest_toml, encoding="utf-8")
        return root

    def test_unrealizable_part_variant_is_reported(self):
        import nyxuri.deploy.deploy as deploy
        from nyxuri.kernel.ledger import update_ledger
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            root = self._app(
                src, "demo",
                'preserve = ["part.kdl"]\n\n[parts.effects]\ntarget = "part.kdl"\n'
                'source_dir = "effects"\ndefault = "default"\n',
                {"part.kdl": "// default-part\n"},
            )
            slot = root / "__presets__" / "effects"
            slot.mkdir(parents=True)
            (slot / "default.kdl").write_text("// default-part\n", encoding="utf-8")
            update_ledger(parts={"demo:effects": "ghost"})
            with patch.object(deploy, "_phase_post_install_services"):
                failed = _quiet(deploy.deploy_selected_configs, items_to_deploy=["demo"], preserved_log=[])
            self.assertEqual(failed, ["demo"])

    def test_absolute_or_empty_chmod_pattern_does_not_abort(self):
        import nyxuri.deploy.deploy as deploy
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            self._app(src, "demo", 'chmod = ["/etc/*", ""]\n', {"config.kdl": "// c\n"})
            with patch.object(deploy, "_phase_post_install_services"):
                failed = _quiet(deploy.deploy_selected_configs, items_to_deploy=["demo"], preserved_log=[])
            self.assertEqual(failed, [])
            self.assertTrue((ctx.env.config_dir / "demo" / "config.kdl").is_file())

    def test_scalar_items_to_deploy_is_treated_as_one_item(self):
        import nyxuri.deploy.deploy as deploy
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            self._app(src, "demo", "", {"config.kdl": "// c\n"})
            with patch.object(deploy, "_phase_post_install_services"):
                failed = _quiet(deploy.deploy_selected_configs, items_to_deploy="demo", preserved_log=[])
            self.assertEqual(failed, [])
            self.assertTrue((ctx.env.config_dir / "demo" / "config.kdl").is_file())
