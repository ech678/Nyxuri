"""Kernel transaction tests (KM2): on/off atomic closure, Vault in/out,
white-paper wipe, doctor three-state audit, and the frozen kernel layering.

Every test runs inside TempEnv — the real ~/.config is never touched.
"""

import ast
import hashlib
import importlib
import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from nyxuri.kernel import ledger, transaction
from tests.utils import TempEnv



def _stage(ctx, spec):
    """在临时目录铺设单元夹具，并让当前环境从该目录读取蓝图。

    spec 按单元 ID 保存 manifest 文本和相对路径到内容的 files 映射。
    未明确声明 packages 时视为无原生包依赖，避免配置生命周期测试依赖宿主包名。
    """
    configs = ctx.home / "configs-src"
    configs.mkdir(exist_ok=True)
    for uid, entry in spec.items():
        unit = configs / uid
        unit.mkdir(exist_ok=True)
        manifest = entry.get("manifest")
        if manifest is None:
            # 临时配置单元没有显式软件依赖；空列表避免按目录名推导宿主包名。
            manifest = "packages = []\n"
        elif not re.search(
            r"(?m)^packages\s*=", re.split(r"(?m)^\s*\[", manifest, maxsplit=1)[0]
        ):
            # 显式清单也按无包样例处理，除非测试明确给出 repo 包列表。
            # 放在首个表之前，确保它仍是 TOML 根字段。
            manifest = "packages = []\n" + manifest
        (unit / "manifest.toml").write_text(manifest, encoding="utf-8")
        for rel, content in entry.get("files", {}).items():
            p = unit / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    ctx.env.units_src = configs


class TestUnitOn(unittest.TestCase):
    """Enable transaction: resolve → preflight → swap → ledger → event."""

    def setUp(self):
        # 普通事务样例不读取宿主包状态；依赖样例单独控制探测器或恢复真实解析链。
        self._missing_packages_patcher = mock.patch.object(
            transaction, "missing_packages", return_value=[]
        )
        self._missing_packages_patcher.start()
        self.addCleanup(self._stop_missing_packages_patcher)

    def _stop_missing_packages_patcher(self):
        if self._missing_packages_patcher is not None:
            self._missing_packages_patcher.stop()
            self._missing_packages_patcher = None

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
            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="arch"), \
                 mock.patch.object(transaction, "missing_packages",
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

            def installer(uid, pkgs):
                calls.append((uid, pkgs))
                return True

            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="arch"), \
                 mock.patch.object(transaction, "missing_packages",
                                   side_effect=[["missing-pkg"], []]):
                steps = transaction.unit_on("app", install_packages=installer)
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual(calls, [("app", ["missing-pkg"])])
            self.assertTrue((ctx.home / ".config/app/a.conf").is_file())

    def test_ubuntu_unsupported_unit_is_rejected_before_deployment(self):
        """Ubuntu 未声明依赖时，事务必须在安装或落账前停止。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {
                "manifest": '[platforms.ubuntu]\nsupported = false\nreason = "not packaged"\n',
                "files": {"a.conf": "a"},
            }})
            installer = mock.Mock()
            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"), \
                 mock.patch.object(transaction, "_phase_atomic_deployment") as deploy, \
                 mock.patch.object(transaction, "_run_unit_hook") as hook:
                steps = transaction.unit_on("app", install_packages=installer)

            self.assertFalse(steps[0].ok)
            self.assertIn("unsupported-platform", steps[0].detail)
            installer.assert_not_called()
            deploy.assert_not_called()
            hook.assert_not_called()
            self.assertFalse((ctx.home / ".config/app").exists())
            self.assertIsNone(ledger.get_unit("app"))

    def test_ubuntu_unmapped_arch_package_is_rejected_before_deployment(self):
        """Ubuntu 不得把顶层 Arch 包名当作无依赖或 APT 包名。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {
                "manifest": 'packages = ["arch-only"]\n',
                "files": {"a.conf": "a"},
            }})
            installer = mock.Mock()
            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"), \
                 mock.patch.object(transaction, "_phase_atomic_deployment") as deploy:
                steps = transaction.unit_on("app", install_packages=installer)

            self.assertFalse(steps[0].ok)
            self.assertIn("unsupported-platform", steps[0].detail)
            installer.assert_not_called()
            deploy.assert_not_called()
            self.assertIsNone(ledger.get_unit("app"))

    def test_ubuntu_package_still_missing_after_installer_stops_before_deploy(self):
        """APT 成功返回后仍须重新探测；未满足的包不能进入部署事务。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {
                "manifest": '[platforms.ubuntu]\npackages = ["apt-demo"]\n',
                "files": {"a.conf": "a"},
            }})
            installer = mock.Mock(return_value=True)
            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"), \
                 mock.patch.object(transaction, "missing_packages", side_effect=[["apt-demo"], ["apt-demo"]]) as missing, \
                 mock.patch.object(transaction, "_phase_atomic_deployment") as deploy:
                steps = transaction.unit_on("app", install_packages=installer)

            self.assertFalse(steps[0].ok)
            self.assertIn("missing-packages: apt-demo", steps[0].detail)
            installer.assert_called_once_with("app", ["apt-demo"])
            self.assertEqual(missing.call_count, 2)
            deploy.assert_not_called()
            self.assertFalse((ctx.home / ".config/app").exists())
            self.assertIsNone(ledger.get_unit("app"))

    def test_ubuntu_manual_resource_then_apt_supply_enables_and_audits_synced(self):
        """先补手动资源，再模拟 APT 供给；真实 CLI 与事务完成部署并对账。"""
        import contextlib
        import io
        from unittest.mock import patch

        with TempEnv() as ctx:
            # 此链路特意保留真实缺失包解析；包探测只使用本测试的内存集合。
            self._stop_missing_packages_patcher()
            unit_root = ctx.home / "isolated-units"
            app = unit_root / "demo"
            app.mkdir(parents=True)
            (app / "manifest.toml").write_text(
                'packages = ["arch-package"]\n'
                '[platforms.ubuntu]\npackages = ["apt-package"]\n'
                'manual = ["manual-font"]\n',
                encoding="utf-8",
            )
            (app / "demo.conf").write_text("setting=true\n", encoding="utf-8")
            ctx.env.units_src = unit_root
            installed = set()

            def invoke_cli(*, confirm=False, installer=None):
                from nyxuri.cli import main

                stdout, stderr = io.StringIO(), io.StringIO()
                with patch("sys.argv", ["nyxuri", "on", "demo"]), \
                     patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"), \
                     patch("nyxuri.pkg.detection.DependencyProbe.installed",
                           new=lambda _probe, name: name in installed), \
                     patch("nyxuri.cli.prompt_confirm", return_value=confirm) as prompt, \
                     patch("nyxuri.cli._package_installer", side_effect=installer) as supply, \
                     patch("nyxuri.cli.acquire_lock"), \
                     patch("nyxuri.cli.init_logger"), \
                     patch("nyxuri.cli.ensure_nyxuri_symlink"), \
                     patch("nyxuri.cli.check_path_occlusion"), \
                     contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as result:
                        main()
                return result.exception.code, stdout.getvalue(), stderr.getvalue(), prompt, supply

            code, output, error, prompt, supply = invoke_cli()
            self.assertEqual(code, 1, output + error)
            self.assertIn("manual-font", error)
            prompt.assert_not_called()
            supply.assert_not_called()
            self.assertFalse((ctx.home / ".config/demo").exists())

            installed.add("manual-font")

            def install_apt(unit_id, packages):
                self.assertEqual(unit_id, "demo")
                self.assertEqual(packages, ["apt-package"])
                installed.add("apt-package")
                return True

            code, output, _, prompt, supply = invoke_cli(confirm=True, installer=install_apt)
            self.assertEqual(code, 0, output)
            prompt.assert_called_once()
            supply.assert_called_once_with("demo", ["apt-package"])
            self.assertEqual((ctx.home / ".config/demo/demo.conf").read_text(encoding="utf-8"),
                             "setting=true\n")
            self.assertEqual(transaction.audit_units("demo"), {"demo": "Synced"})

    def test_ubuntu_template_is_rendered_before_hook_and_snapshotted(self):
        """Ubuntu 启用顺序应先渲染路径，再运行钩子并记录渲染后的哈希。"""
        with TempEnv() as ctx:
            _stage(ctx, {"niri": {
                "manifest": 'post_install = "verify"\n[platforms.ubuntu]\npackages = []\n',
                "files": {"config.kdl": 'include "/home/user/nested"\n'},
            }})
            hook = ctx.env.units_src / "niri" / "hooks" / "verify"
            hook.parent.mkdir(parents=True)
            hook.write_text(
                "#!/bin/sh\ncat \"$NYXURI_UNIT_DEST/config.kdl\" > \"$HOME/hook-observed.txt\"\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)

            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"):
                steps = transaction.unit_on("niri")

            target = ctx.home / ".config/niri/config.kdl"
            rendered = f'include "{ctx.home}/nested"\n'
            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual((ctx.home / "hook-observed.txt").read_text(encoding="utf-8"), rendered)
            self.assertEqual(target.read_text(encoding="utf-8"), rendered)
            self.assertEqual(ledger.get_unit("niri")["files"]["config.kdl"],
                             hashlib.sha256(target.read_bytes()).hexdigest())

    def test_ubuntu_custom_file_survives_template_deployment(self):
        """平台适配部署不能覆盖用户的 Dunder 与按名 preserve 文件。"""
        with TempEnv() as ctx:
            _stage(ctx, {"niri": {
                "manifest": 'preserve = ["monitor.kdl"]\n[platforms.ubuntu]\npackages = []\n',
                "files": {"config.kdl": "blueprint\n"},
            }})
            living = ctx.home / ".config/niri"
            living.mkdir(parents=True)
            (living / "__custom__.kdl").write_text("private\n", encoding="utf-8")
            (living / "monitor.kdl").write_text("outputs\n", encoding="utf-8")

            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"):
                steps = transaction.unit_on("niri")

            self.assertTrue(steps[0].ok, str(steps))
            self.assertEqual((living / "__custom__.kdl").read_text(encoding="utf-8"), "private\n")
            self.assertEqual((living / "monitor.kdl").read_text(encoding="utf-8"), "outputs\n")

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
                "files": {"niri.conf": "spawn {}\n", "monitor.kdl": "output eDP-1\n",
                          "theme__custom__.conf": "# template slot\n"},
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

    def test_ubuntu_off_reports_mapped_packages_and_keeps_them_installed(self):
        """Ubuntu 停用只撤配置，并报告平台覆盖声明的保留包。"""
        with TempEnv() as ctx:
            _stage(ctx, {"niri": {
                "manifest": 'packages = ["arch-only"]\n'
                            '[platforms.ubuntu]\npackages = ["ubuntu-only"]\n',
                "files": {"config.kdl": "config\n"},
            }})
            manager_run = mock.patch("nyxuri.pkg.run")
            manager = manager_run.start()
            self.addCleanup(manager_run.stop)
            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"):
                on_steps = transaction.unit_on("niri")
                off_steps = transaction.unit_off("niri")

            self.assertTrue(on_steps[0].ok, str(on_steps))
            self.assertTrue(off_steps[0].ok, str(off_steps))
            self.assertIn("packages-left: ubuntu-only", off_steps[0].detail)
            self.assertNotIn("arch-only", off_steps[0].detail)
            self.assertFalse((ctx.home / ".config/niri").exists())
            self.assertEqual(ledger.get_unit("niri")["state"], "disabled")
            manager.assert_not_called()

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

    def test_off_without_ledger_preserves_unknown_files(self):
        """没有账本归属时，同名模板也不足以证明文件可以删除。"""
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x"}}})
            dest = ctx.home / ".config/kitty"
            dest.mkdir(parents=True)
            (dest / "k.conf").write_text("deployed by old installer\n")
            (dest / "my-notes.txt").write_text("keep me\n")
            steps = transaction.unit_off("kitty")
            self.assertTrue(steps[0].ok)
            self.assertTrue((dest / "k.conf").exists(), "unknown files must survive")
            self.assertTrue((dest / "my-notes.txt").is_file(), "user files must never be eaten")
            self.assertIn("foreign-left: k.conf, my-notes.txt", steps[0].detail)

    def test_off_never_eats_unregistered_single_file(self):
        """Single-file unit: a dest file outside the managed snapshot survives."""
        with TempEnv() as ctx:
            _stage(ctx, {"starship": {"manifest": 'target = "starship.toml"\n',
                                      "files": {"starship.toml": "$schema\n"}}})
            dest = ctx.home / ".config/starship.toml"
            dest.write_text("user's own\n", encoding="utf-8")
            steps = transaction.unit_off("starship")
            self.assertTrue(steps[0].ok)
            self.assertIn("foreign-left: starship.toml", steps[0].detail)
            self.assertEqual(dest.read_text(), "user's own\n")

    def test_personal_fish_plugins_and_protected_files_stay_active_after_off(self):
        """首次启用前的 Fisher 插件和清单经刷新、停用仍留在可供 Fish 读取的位置。"""
        with TempEnv() as ctx:
            _stage(ctx, {"fish": {
                "manifest": 'preserve = ["functions", "fish_plugins", "fish_variables"]\n',
                "files": {"config.fish": "# managed\n", "fish_variables": "# defaults\n",
                          "theme__custom__.fish": "# template slot\n"},
            }})
            dest = ctx.env.config_dir / "fish"
            personal = {"functions/getopts.fish": "function getopts; echo personal; end\n",
                        "fish_plugins": "jorgebucaran/getopts.fish\n",
                        "fish_variables": "SETUVAR personal:value\n",
                        "theme__custom__.fish": "# personal custom\n"}
            for rel, content in personal.items():
                path = dest / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            for action in (transaction.unit_on, transaction.unit_refresh):
                self.assertTrue(all(step.ok for step in action("fish")))
                self.assertEqual(ledger.get_deployment("fish")["protected_paths"], [])
                self.assertTrue(set(personal).isdisjoint(ledger.get_unit("fish")["files"]))
            # 部署完成后由用户另建的 custom 同样不能仅凭名称获得撤回权限。
            personal["later__custom__.fish"] = "# added by user\n"
            (dest / "later__custom__.fish").write_text(personal["later__custom__.fish"])
            for _ in range(2):
                steps = transaction.unit_off("fish")
                self.assertTrue(all(step.ok for step in steps), steps)
                self.assertFalse((dest / "config.fish").exists())
                for rel, content in personal.items():
                    self.assertEqual((dest / rel).read_text(), content)
                    self.assertIn(rel, steps[0].detail)
                self.assertFalse(transaction.vault_dir("fish").exists())
                self.assertTrue(all(step.ok for step in transaction.unit_on("fish")))

    def test_old_record_does_not_infer_protected_ownership(self):
        """旧账本没有来源字段时，保留名不能反推出撤回权限。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'preserve = ["runtime"]\n',
                                  "files": {"main.conf": "main", "runtime": "state",
                                            "user__custom__.conf": "custom"}}})
            transaction.unit_on("app")
            data = ledger.read_ledger()
            data["deployments"]["app"].pop("protected_paths")
            ledger.ledger_path().write_text(json.dumps(data))
            self.assertTrue(transaction.unit_off("app")[0].ok)
            dest = ctx.env.config_dir / "app"
            self.assertEqual((dest / "runtime").read_text(), "state")
            self.assertEqual((dest / "user__custom__.conf").read_text(), "custom")
            self.assertFalse((dest / "main.conf").exists())

    def test_protected_sources_survive_failed_hook_retry_refresh_and_vault(self):
        """来源集合在钩子失败前已提交，重试不能把个人内容重基为模板哈希。"""
        for merge in (False, True):
            with self.subTest(merge=merge), TempEnv() as ctx:
                _stage(ctx, {"app": {
                    "manifest": 'preserve = ["runtime"]\npost_install = "seed"\n'
                                + ('merge = true\n' if merge else ''),
                    "files": {"main.conf": "main", "runtime": "default",
                              "user__custom__.conf": "# slot"},
                }})
                with mock.patch.object(transaction, "_run_unit_hook", return_value=False):
                    self.assertFalse(transaction.unit_on("app")[0].ok)
                owned = ["runtime", "user__custom__.conf"]
                self.assertEqual(ledger.get_deployment("app")["protected_paths"], owned)
                dest = ctx.env.config_dir / "app"
                (dest / "runtime").write_text("personal runtime")
                (dest / "user__custom__.conf").write_text("personal custom")
                with mock.patch.object(transaction, "_run_unit_hook", return_value=True):
                    self.assertTrue(transaction.unit_on("app")[0].ok)
                    self.assertTrue(transaction.unit_refresh("app")[0].ok)
                self.assertTrue(set(owned).isdisjoint(ledger.get_unit("app")["files"]))
                self.assertTrue(transaction.unit_off("app")[0].ok)
                self.assertFalse(dest.exists())
                self.assertEqual((transaction.vault_dir("app") / "runtime").read_text(), "personal runtime")
                with mock.patch.object(transaction, "_run_unit_hook", return_value=True):
                    self.assertTrue(transaction.unit_on("app")[0].ok)
                self.assertEqual((dest / "runtime").read_text(), "personal runtime")
                self.assertEqual((dest / "user__custom__.conf").read_text(), "personal custom")
                self.assertEqual(ledger.get_deployment("app")["protected_paths"], owned)

    def test_off_vaults_preserve_directory_and_restores_it(self):
        """钩子新建且有来源记录的保留文件可归档，目录名本身不授予整树权限。"""
        with TempEnv() as ctx:
            _stage(ctx, {"fish": {
                "manifest": 'preserve = ["functions"]\npost_install = "create-plugin"\n',
                "files": {"config.fish": "set -x PATH\n"},
            }})
            dest = ctx.home / ".config/fish"
            def create_plugin(*args, **kwargs):
                plugin = dest / "functions/fisher.fish"
                plugin.parent.mkdir(parents=True, exist_ok=True)
                if not plugin.exists():
                    plugin.write_text("plugin\n", encoding="utf-8")
                return True

            with mock.patch.object(transaction, "_run_unit_hook", side_effect=create_plugin):
                transaction.unit_on("fish")
            self.assertEqual(ledger.get_deployment("fish")["protected_paths"], ["functions/fisher.fish"])
            self.assertTrue(
                transaction._is_user_owned("functions/fisher.fish",
                                           transaction.registry.load_unit("fish")),
                "every file under a preserved directory is user-owned by prefix")

            steps = transaction.unit_off("fish")
            self.assertTrue(steps[0].ok, str(steps))
            vault = ctx.home / ".local/state/nyxuri/vault/fish"
            self.assertEqual((vault / "functions/fisher.fish").read_text(), "plugin\n")
            self.assertFalse(dest.exists())

            with mock.patch.object(transaction, "_run_unit_hook", side_effect=create_plugin):
                transaction.unit_on("fish")
            self.assertEqual((dest / "functions/fisher.fish").read_text(), "plugin\n",
                             "the preserved tree must ride the Vault back")

    def test_off_then_on_restores_vault_and_consumes_it(self):
        with TempEnv() as ctx:
            _stage(ctx, {"kitty": {"files": {"k.conf": "x", "theme__custom__.conf": "# slot"}}})
            dest = ctx.home / ".config/kitty"
            transaction.unit_on("kitty")
            # 来源已记录后移除模板，后续用户删除也不得被旧 Vault 再次复活。
            (ctx.env.units_src / "kitty/theme__custom__.conf").unlink()
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


class TestOwnershipCarryLedger(unittest.TestCase):
    """Ledger doctrine (#139): the ledger records what the engine laid,
    never what it carried. Update re-baselines through ``resnapshot_units``;
    ``on`` is adoption (payload names claimed, extras stay user-owned)."""

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _make_hook(self, unit_dir: Path, name: str, body: str) -> Path:
        hooks = unit_dir / "hooks"
        hooks.mkdir(exist_ok=True)
        script = hooks / name
        script.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    def test_carry_baselines_enabled_units_only(self):
        with TempEnv() as ctx:
            _stage(ctx, {
                "kitty": {"files": {"k.conf": "x"}},
                "fish": {"files": {"f.conf": "y"}},
            })
            transaction.unit_on("kitty")
            baselines = transaction.carry_baselines(["kitty", "fish"])
            self.assertEqual(set(baselines["kitty"]), {"k.conf"})
            self.assertIsNone(baselines["fish"], "Ghost units have no baseline")

    def test_on_preserves_unknown_payload_and_keeps_extras(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "template\n"}}})
            dest = ctx.home / ".config/app"
            dest.mkdir(parents=True)
            (dest / "a.conf").write_text("user's own take\n", encoding="utf-8")
            (dest / "extra.conf").write_text("user's tool\n", encoding="utf-8")
            steps = transaction.unit_on("app")
            self.assertTrue(steps[0].ok, str(steps))
            # 首次启用没有归属证据，同名个人文件必须保留并披露冲突。
            self.assertEqual((dest / "a.conf").read_text(), "user's own take\n")
            self.assertEqual(steps[0].conflicts, ("a.conf",))
            # …and the user's extra file survives as user-owned.
            self.assertEqual((dest / "extra.conf").read_text(), "user's tool\n")
            rec = ledger.get_unit("app")
            self.assertEqual(set(rec["files"]), set(),
                             "carried files must never enter the snapshot")
            self.assertEqual(transaction.audit_units("app"), {"app": "Synced"})

    def test_update_carry_then_resnapshot_rebaselines_laid_only(self):
        from nyxuri.deploy.atomic import CarryPolicy

        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "v1\n"}}})
            transaction.unit_on("app")
            dest = ctx.home / ".config/app"
            (dest / "a.conf").write_text("my edit\n", encoding="utf-8")
            (dest / "extra.conf").write_text("user's tool\n", encoding="utf-8")
            # Template moves on (the repo pull).
            (ctx.env.units_src / "app" / "a.conf").write_text("v2\n", encoding="utf-8")

            policy = CarryPolicy(
                baselines=transaction.carry_baselines(["app"]), unknown=True
            )
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"], carry_policy=policy))
            # 宁可错保: the user's edit and extra file both survive the update.
            self.assertEqual((dest / "a.conf").read_text(), "my edit\n")
            self.assertEqual((dest / "extra.conf").read_text(), "user's tool\n")
            self.assertEqual(policy.carried["app"]["a.conf"], "modified")
            self.assertEqual(policy.carried["app"]["extra.conf"], "user")

            transaction.resnapshot_units(["app"], policy.carried)
            rec = ledger.get_unit("app")
            self.assertEqual(rec["files"]["a.conf"], hashlib.sha256(b"v1\n").hexdigest(),
                             "modified files retain the original deployment baseline")
            self.assertNotIn("extra.conf", rec["files"])
            # 保留历史归属后，doctor 继续如实显示个人改动。
            self.assertEqual(transaction.audit_units("app"), {"app": "Drifted"})

            # Force is the adopt verb: template side wins and is re-baselined.
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"]))
            transaction.resnapshot_units(["app"], carried={})
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")
            self.assertEqual(
                ledger.get_unit("app")["files"]["a.conf"],
                hashlib.sha256((dest / "a.conf").read_bytes()).hexdigest(),
            )

    def test_hook_product_lifecycle_through_update(self):
        """KM3 restored under carry (#139 field report): hook products retire
        at the swap (engine didn't lay them), the hook replay re-lays them,
        and resnapshot puts them back under ledger ownership — `off` wipes
        them again instead of leaving foreign residue."""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'packages = []\npost_install = "seed"\n',
                                 "files": {"a.conf": "v1\n"}}})
            self._make_hook(
                ctx.env.units_src / "app", "seed",
                'printf "hooked\\n" > "$NYXURI_UNIT_DEST/hooked.conf"',
            )
            self.assertTrue(transaction.unit_on("app")[0].ok)
            dest = ctx.home / ".config/app"
            self.assertIn("hooked.conf", ledger.get_unit("app")["files"])

            # Template moves on; the payload still has no hooked.conf.
            (ctx.env.units_src / "app" / "a.conf").write_text("v2\n", encoding="utf-8")
            from nyxuri.deploy.atomic import CarryPolicy
            policy = CarryPolicy(
                baselines=transaction.carry_baselines(["app"]), unknown=True
            )
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"], carry_policy=policy))
            self.assertFalse((dest / "hooked.conf").exists(),
                             "retired hook product must not be carried as a user file")
            self.assertEqual(policy.carried.get("app"), {})

            # Hook replay re-lays it; resnapshot re-owns it.
            self.assertTrue(transaction._run_unit_hook(
                "app", transaction.registry.load_unit("app"), "seed"))
            transaction.resnapshot_units(["app"], policy.carried)
            self.assertIn("hooked.conf", ledger.get_unit("app")["files"])
            self.assertEqual(transaction.audit_units("app"), {"app": "Synced"})

    def test_preset_switch_on_enabled_unit_respects_baseline(self):
        """A re-deploy over an enabled unit carries edits made after `on`."""
        from nyxuri.deploy.atomic import CarryPolicy

        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "v1\n"}}})
            transaction.unit_on("app")
            dest = ctx.home / ".config/app"
            (dest / "a.conf").write_text("tuned\n", encoding="utf-8")
            (ctx.env.units_src / "app" / "a.conf").write_text("v2\n", encoding="utf-8")
            policy = CarryPolicy(
                baselines=transaction.carry_baselines(["app"]), unknown=False
            )
            self.assertNotIn("app", transaction._phase_atomic_deployment(["app"], carry_policy=policy))
            self.assertEqual((dest / "a.conf").read_text(), "tuned\n")
            self.assertEqual(policy.carried["app"]["a.conf"], "modified")


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
        kernel = Path(importlib.import_module("nyxuri").__file__).parent / "kernel"
        return (kernel / f"{name}.py").read_text(encoding="utf-8")

    def test_kernel_package_holds_the_four_modules(self):
        """KM3.5 正名: the kernel lives physically in nyxuri/kernel/."""
        kernel = Path(importlib.import_module("nyxuri").__file__).parent / "kernel"
        for name in ("registry", "resolver", "ledger", "transaction"):
            self.assertTrue((kernel / f"{name}.py").is_file(), name)
        # The flat top level must not keep ghosts of the old layout.
        top = kernel.parent
        for name in ("registry", "resolver", "ledger", "transaction"):
            self.assertFalse((top / f"{name}.py").exists(), name)

    def test_leaves_never_import_siblings_or_transaction(self):
        for leaf in ("registry", "resolver", "ledger"):
            mods = _imported_modules(self._source(leaf))
            for mod in mods:
                top = mod.lstrip(".").split(".")[0]
                self.assertNotEqual(top, "transaction", f"{leaf} must not import transaction")
            if leaf == "resolver":
                self.assertNotIn("nyxuri", {m.split(".")[0] for m in mods},
                                 "resolver must stay pure (zero nyxuri imports)")
            siblings = {"nyxuri.kernel.registry", "nyxuri.kernel.resolver", "nyxuri.kernel.ledger"}
            siblings.discard(f"nyxuri.kernel.{leaf}")
            self.assertFalse(siblings & mods, f"{leaf} must not import kernel siblings")

    def test_transaction_composes_all_three_leaves(self):
        mods = _imported_modules(self._source("transaction"))
        for leaf in ("nyxuri.kernel.registry", "nyxuri.kernel.resolver", "nyxuri.kernel.ledger"):
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


class TestUnitHooks(unittest.TestCase):
    """KM3 hook contract: unit-owned scripts, declared in the manifest.

    - post_install runs BEFORE the ledger snapshot, so products the hook
      lands inside the unit's own living area become transaction-managed
      (``off`` wipes them through the normal white-paper path).
    - post_remove runs AFTER the wipe (effects outside the living area).
    - hooks never ship to the living area and never count as deployable.
    """

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _make_hook(self, unit_dir: Path, name: str, body: str) -> Path:
        hooks = unit_dir / "hooks"
        hooks.mkdir(exist_ok=True)
        script = hooks / name
        script.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    def test_on_runs_hook_and_snapshot_covers_living_area_products(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {
                "manifest": 'post_install = "seed"\n',
                "files": {"a.conf": "a"},
            }})
            self._make_hook(
                ctx.env.units_src / "app", "seed",
                'printf "hooked\\n" > "$NYXURI_UNIT_DEST/hooked.conf"',
            )
            steps = transaction.unit_on("app")
            self.assertTrue(steps[0].ok, str(steps))
            self.assertNotIn("hook-failed", steps[0].detail)
            dest = ctx.home / ".config/app"
            self.assertTrue((dest / "hooked.conf").is_file())
            rec = ledger.get_unit("app")
            self.assertIn("hooked.conf", rec["files"], "hook products must enter the managed snapshot")

    def test_on_hook_failure_marks_pending(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'post_install = "nope"\n', "files": {"a.conf": "a"}}})
            steps = transaction.unit_on("app")
            self.assertFalse(steps[0].ok)
            self.assertEqual(ledger.get_deployment("app")["pending"], "post_install")
            self.assertIn("hook-failed: nope", steps[0].detail)
            self.assertTrue((ctx.home / ".config/app/a.conf").is_file())

    def test_off_runs_post_remove_after_wipe(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {
                "manifest": 'post_remove = "clean"\n',
                "files": {"a.conf": "a"},
            }})
            calls = []
            original = transaction._run_unit_hook

            def spy(uid, manifest, spec):
                calls.append((uid, spec, (ctx.home / ".config/app").exists()))
                return original(uid, manifest, spec)

            with mock.patch.object(transaction, "_run_unit_hook", side_effect=spy):
                transaction.unit_on("app")
                steps = transaction.unit_off("app")
            self.assertFalse(steps[0].ok, str(steps))
            self.assertEqual(ledger.get_deployment("app")["pending"], "post_remove")
            self.assertEqual(calls[-1], ("app", "clean", False),
                             "post_remove must run after the wipe")
            self.assertFalse((ctx.home / ".config/app").exists())

    def test_hook_env_exposes_unit_identity(self):
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'post_install = "identity"\n', "files": {"a.conf": "a"}}})
            marker = ctx.home / "hook-env.txt"
            self._make_hook(
                ctx.env.units_src / "app", "identity",
                f'env | grep -E "^NYXURI_UNIT" > "{marker}"',
            )
            steps = transaction.unit_on("app")
            self.assertTrue(steps[0].ok, str(steps))
            content = marker.read_text(encoding="utf-8")
            self.assertIn("NYXURI_UNIT=app", content)
            self.assertIn("NYXURI_UNIT_SRC=", content)
            self.assertIn("NYXURI_UNIT_DEST=", content)

    def test_hooks_never_count_as_deployable_config(self):
        from nyxuri.deploy.manifest import load_manifest

        with TempEnv() as ctx:
            _stage(ctx, {"ghost-unit": {"manifest": 'packages = ["x"]\n'}})
            self._make_hook(ctx.env.units_src / "ghost-unit", "hook", "true")
            m = load_manifest(ctx.env.units_src / "ghost-unit")
            self.assertFalse(m.is_deployable, "manifest + hooks only must stay non-deployable")


if __name__ == "__main__":
    unittest.main()


class TestLedgerResilience(unittest.TestCase):

    def test_unhashable_active_shell_falls_back_to_default(self):
        from nyxuri.kernel import ledger
        with TempEnv():
            for bad in ([], {}, ["a"], 5, None, "weird"):
                ledger.update_ledger(active_shell=bad)
                self.assertEqual(ledger.active_shell(), "noctalia")

    def test_concurrent_updates_do_not_lose_keys(self):
        from nyxuri.kernel import ledger
        with TempEnv():
            ledger.update_ledger(seed="x")
            read_fd, write_fd = os.pipe()
            pids = []
            for index in range(6):
                pid = os.fork()
                if pid == 0:
                    try:
                        os.read(read_fd, 1)
                        ledger.update_ledger(**{f"k{index}": index})
                    finally:
                        os._exit(0)
                pids.append(pid)
            os.close(read_fd)
            for _ in range(6):
                os.write(write_fd, b"g")
            os.close(write_fd)
            for pid in pids:
                os.waitpid(pid, 0)
            data = ledger.read_ledger()
            self.assertEqual([data.get(f"k{i}") for i in range(6)], list(range(6)))


class TestManagementLifecycleAcceptance(unittest.TestCase):
    """审查方案明确列出的隔离验收：归档、预检、重试、共享目录和损坏账本。"""

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_modified_directory_file_and_merge_roundtrip_keep_original_baseline(self):
        """三种落地形状都先归档普通改动，再恢复，重复刷新不能认领个人版本。"""
        for shape in ("directory", "file", "merge"):
            with self.subTest(shape=shape), TempEnv() as ctx:
                manifest = ('target = "a.conf"\n' if shape == "file" else
                            'merge = true\ntarget = "~/shared"\n' if shape == "merge" else '')
                _stage(ctx, {"app": {"manifest": manifest, "files": {"a.conf": "v1"}}})
                self.assertTrue(transaction.unit_on("app")[0].ok)
                root = ctx.home / ("shared" if shape == "merge" else ".config/app")
                target = ctx.home / ".config/a.conf" if shape == "file" else root / "a.conf"
                baseline = ledger.get_unit("app")["files"]["a.conf"]
                target.write_text("personal")
                self.assertTrue(transaction.unit_off("app")[0].ok)
                self.assertFalse(target.exists())
                self.assertEqual((transaction.vault_dir("app") / "a.conf").read_text(), "personal")
                self.assertTrue(transaction.unit_on("app")[0].ok)
                (ctx.env.units_src / "app/a.conf").write_text("v2")
                for _ in range(2):
                    self.assertTrue(transaction.unit_refresh("app")[0].ok)
                    self.assertEqual(target.read_text(), "personal")
                    self.assertEqual(ledger.get_unit("app")["files"]["a.conf"], baseline)
                self.assertEqual(transaction.audit_units("app"), {"app": "Drifted"})
                self.assertTrue(transaction.unit_off("app")[0].ok)
                self.assertEqual((transaction.vault_dir("app") / "a.conf").read_text(), "personal")

    def test_vault_restores_nested_custom_without_removing_foreign_sibling(self):
        """Vault 的叶节点合并不得把同父目录内的外来文件整目录替换。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"main.conf": "template", "nested/user__custom__.conf": "# slot"}}})
            transaction.unit_on("app")
            root = ctx.home / ".config/app/nested"
            (root / "user__custom__.conf").write_text("custom")
            (root / "foreign.conf").write_text("foreign")
            transaction.unit_off("app")
            self.assertFalse((root / "user__custom__.conf").exists())
            self.assertEqual((transaction.vault_dir("app") / "nested/user__custom__.conf").read_text(), "custom")
            self.assertEqual((root / "foreign.conf").read_text(), "foreign")
            transaction.unit_on("app")
            self.assertEqual((root / "user__custom__.conf").read_text(), "custom")
            self.assertEqual((root / "foreign.conf").read_text(), "foreign")

    def test_invalid_explicit_preset_has_no_dependency_or_active_writes(self):
        """显式预设先于依赖部署校验，失败不创建账本、active 或依赖配置。"""
        with TempEnv() as ctx:
            _stage(ctx, {"base": {"files": {"base.conf": "base"}},
                         "app": {"manifest": 'dependencies = ["base"]\n', "files": {"a.conf": "a"}}})
            step = transaction.unit_on("app", preset="missing")[0]
            self.assertFalse(step.ok)
            self.assertFalse(ledger.ledger_path().exists())
            self.assertFalse((ctx.env.config_dir / "base").exists())
            self.assertFalse((ctx.env.presets_dir / "app.active").exists())
            self.assertFalse((ctx.env.state_dir / "vault").exists())

    def test_explicit_preset_on_empty_target_is_not_reset_to_default(self):
        """首次启用即部署所选预设，文件和两处预设状态一致。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "default", "__presets__/dark/a.conf": "dark"}}})
            self.assertTrue(transaction.unit_on("app", preset="dark")[0].ok)
            self.assertEqual((ctx.env.config_dir / "app/a.conf").read_text(), "dark")
            self.assertEqual(ledger.get_unit("app")["preset"], "dark")
            self.assertEqual((ctx.env.presets_dir / "app.active").read_text(), "dark")

    def test_force_has_recoverable_backup_and_backup_failure_does_not_overwrite(self):
        """强制覆盖前备份个人内容；备份失败不落地，也不能由普通备份选项绕过。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "template"}}})
            dest = ctx.env.config_dir / "app"
            dest.mkdir()
            (dest / "a.conf").write_text("personal")
            (dest / "foreign").write_text("foreign")
            with mock.patch("nyxuri.state.backup.backup_configs", return_value=None):
                self.assertFalse(transaction.unit_on("app", force=True)[0].ok)
            self.assertEqual((dest / "a.conf").read_text(), "personal")
            self.assertIsNone(ledger.get_unit("app"))
            result = transaction.unit_on("app", force=True)[0]
            self.assertTrue(result.ok, result)
            self.assertEqual((Path(result.backup) / "app/a.conf").read_text(), "personal")
            self.assertTrue((Path(result.backup) / "snapshot.json").is_file())
            self.assertEqual((dest / "a.conf").read_text(), "template")
            self.assertEqual((dest / "foreign").read_text(), "foreign")

    def test_hook_failures_remain_pending_and_retry_completes(self):
        """on 和 off 的关键钩子失败都返回未完成，并允许同一动词重试。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'post_install = "setup"\npost_remove = "clean"\n',
                                 "files": {"a.conf": "a"}}})
            with mock.patch.object(transaction, "_run_unit_hook", side_effect=[False, True, False, True]) as hook:
                first = transaction.unit_on("app")[0]
                self.assertFalse(first.ok)
                self.assertEqual(transaction.audit_units("app"), {"app": "Pending"})
                self.assertTrue(transaction.unit_on("app")[0].ok)
                self.assertFalse(transaction.unit_off("app")[0].ok)
                self.assertEqual(ledger.get_deployment("app")["pending"], "post_remove")
                self.assertTrue(transaction.unit_off("app")[0].ok)
                self.assertIsNone(ledger.get_deployment("app")["pending"])
                self.assertEqual([call.args[2] for call in hook.call_args_list], ["setup", "setup", "clean", "clean"])

    def test_merge_refresh_updates_owned_adds_new_removes_old_and_preserves_personal(self):
        """真实新旧版本差异覆盖新增、修改、删除与冲突，共享目录不整体置换。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'merge = true\ntarget = "~/shared"\n',
                                 "files": {"update": "v1", "edit": "v1", "retire": "old"}}})
            transaction.unit_on("app")
            root = ctx.home / "shared"
            (root / "edit").write_text("personal")
            (root / "foreign").write_text("foreign")
            src = ctx.env.units_src / "app"
            (src / "update").write_text("v2")
            (src / "edit").write_text("v2")
            (src / "retire").unlink()
            (src / "new").write_text("new")
            step = transaction.unit_refresh("app")[0]
            self.assertTrue(step.ok, step)
            self.assertEqual(step.conflicts, ("edit",))
            self.assertEqual((root / "update").read_text(), "v2")
            self.assertEqual((root / "edit").read_text(), "personal")
            self.assertEqual((root / "foreign").read_text(), "foreign")
            self.assertEqual((root / "new").read_text(), "new")
            self.assertFalse((root / "retire").exists())
            self.assertNotIn("foreign", ledger.get_unit("app")["files"])

    def test_orphan_audit_and_withdraw_use_historical_target(self):
        """源码已删除时 doctor 继续报告其他单元，并依据历史元数据安全停用。"""
        import shutil
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "a"}}, "other": {"files": {"o.conf": "o"}}})
            transaction.unit_on("app")
            transaction.unit_on("other")
            dest = ctx.env.config_dir / "app/a.conf"
            dest.write_text("personal")
            shutil.rmtree(ctx.env.units_src / "app")
            self.assertEqual(transaction.audit_units(), {"app": "Orphan", "other": "Synced"})
            self.assertEqual(transaction.plan_off("app"), ["app"])
            self.assertTrue(transaction.unit_off("app")[0].ok)
            self.assertFalse(dest.exists())
            self.assertEqual((transaction.vault_dir("app") / "a.conf").read_text(), "personal")

    def test_changed_layout_requires_old_target_withdrawal(self):
        """manifest 更改目标后拒绝直接 refresh，off 仍撤回历史落地点。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"manifest": 'merge = true\ntarget = "~/old"\n', "files": {"a": "a"}}})
            transaction.unit_on("app")
            (ctx.env.units_src / "app/manifest.toml").write_text('packages = []\nmerge = true\ntarget = "~/new"\n')
            self.assertFalse(transaction.unit_refresh("app")[0].ok)
            self.assertTrue((ctx.home / "old/a").exists())
            self.assertFalse((ctx.home / "new").exists())
            self.assertTrue(transaction.unit_off("app")[0].ok)
            self.assertFalse((ctx.home / "old/a").exists())

    def test_corrupt_ledger_and_lock_failure_stop_before_file_changes(self):
        """损坏与锁异常不能伪装首次部署；保留原账本和配置字节。"""
        with TempEnv() as ctx:
            _stage(ctx, {"app": {"files": {"a.conf": "a"}}})
            path = ledger.ledger_path()
            path.write_text('{"units": invalid')
            self.assertFalse(transaction.unit_on("app")[0].ok)
            self.assertEqual(path.read_text(), '{"units": invalid')
            self.assertFalse((ctx.env.config_dir / "app").exists())
            path.unlink()
            with mock.patch.object(ledger.fcntl, "flock", side_effect=OSError("lock unavailable")):
                self.assertFalse(transaction.unit_on("app")[0].ok)
            self.assertFalse(path.exists())
            self.assertFalse((ctx.env.config_dir / "app").exists())


class TestManagedRuntimeTransformationLifecycle(unittest.TestCase):
    """审查方案中的运行时产物基线、更新和停用闭环，所有内容均在 TempEnv。"""

    def setUp(self):
        patcher = mock.patch.object(transaction, "missing_packages", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _starship(self, ctx):
        """启用最小主题消费者并选择自研Shell，只验证Python提交边界。"""
        _stage(ctx, {
            "theme": {"manifest": 'runtime = true\n'},
            "starship": {"manifest": 'target = "starship.toml"\n', "files": {"starship.toml": "template-v1"}},
        })
        self.assertTrue(transaction.unit_on("theme")[0].ok)
        self.assertTrue(transaction.unit_on("starship")[0].ok)
        ledger.set_shell("nyxuri-shell")
        return ctx.env.config_dir / "starship.toml"

    def test_managed_main_file_render_refresh_restore_and_off(self):
        """运行态基线仍可升级模板，停用撤回变换后不把原模板误归档为个人修改。"""
        from nyxuri.desktop import owned_outputs
        with TempEnv() as ctx:
            target = self._starship(ctx)
            self.assertTrue(owned_outputs.write_transformation("nyxuri-shell", "starship", target, b"rendered-v1"))
            self.assertEqual(target.read_text(), "rendered-v1")
            self.assertEqual(transaction.audit_units("starship"), {"starship": "Synced"})
            (ctx.env.units_src / "starship/starship.toml").write_text("template-v2")
            self.assertTrue(transaction.unit_refresh("starship")[0].ok)
            self.assertEqual(target.read_text(), "template-v2")
            self.assertTrue(owned_outputs.write_transformation("nyxuri-shell", "starship", target, b"rendered-v2"))
            owned_outputs.withdraw_outputs(producer="nyxuri-shell")
            self.assertEqual(target.read_text(), "template-v2")
            self.assertEqual(transaction.audit_units("starship"), {"starship": "Synced"})
            self.assertTrue(owned_outputs.write_transformation("nyxuri-shell", "starship", target, b"rendered-again"))
            self.assertTrue(transaction.unit_off("starship")[0].ok)
            self.assertFalse(target.exists())
            self.assertFalse((transaction.vault_dir("starship") / "starship.toml").exists())

    def test_personal_main_file_change_is_not_rebased_by_render_or_refresh(self):
        """运行态主文件的个人修改保持漂移证据，off归档后on仍受同一保护。"""
        from nyxuri.desktop import owned_outputs
        with TempEnv() as ctx:
            target = self._starship(ctx)
            self.assertTrue(owned_outputs.write_transformation("nyxuri-shell", "starship", target, b"rendered"))
            baseline = ledger.get_unit("starship")["files"]["starship.toml"]
            target.write_text("personal")
            self.assertFalse(owned_outputs.write_transformation("nyxuri-shell", "starship", target, b"other-render"))
            (ctx.env.units_src / "starship/starship.toml").write_text("template-v2")
            self.assertTrue(transaction.unit_refresh("starship")[0].ok)
            self.assertEqual(target.read_text(), "personal")
            self.assertEqual(ledger.get_unit("starship")["files"]["starship.toml"], baseline)
            self.assertTrue(transaction.unit_off("starship")[0].ok)
            self.assertEqual((transaction.vault_dir("starship") / "starship.toml").read_text(), "personal")
            self.assertTrue(transaction.unit_on("starship")[0].ok)
            self.assertEqual(target.read_text(), "personal")
            self.assertFalse(owned_outputs.write_transformation("nyxuri-shell", "starship", target, b"other-render"))
            self.assertEqual(transaction.audit_units("starship"), {"starship": "Drifted"})


class TestDeclaredLayoutMigration(unittest.TestCase):
    """批准的共享目标迁移、冲突重试、Portal 多桌面与壁纸目录场景。"""

    def _fcitx(self, ctx, *, metadata=True):
        _stage(ctx, {"fcitx5-rime": {"files": {"settings.conf": "template-v1", "profile": "profile-default"},
                                    "manifest": 'preserve = ["profile"]\n'}})
        self.assertTrue(all(step.ok for step in transaction.unit_on("fcitx5-rime")))
        old = ctx.env.config_dir / "fcitx5-rime"
        (old / "settings.conf").write_text("personal-settings")
        (old / "profile").write_text("personal-profile")
        (old / "foreign.conf").write_text("unowned-old")
        vault = transaction.vault_dir("fcitx5-rime")
        vault.mkdir(parents=True)
        (vault / "__custom__.conf").write_text("archived-personal")
        if not metadata:
            data = ledger.read_ledger()
            data.pop("deployments", None)
            ledger.ledger_path().write_text(json.dumps(data))
        src = ctx.env.units_src / "fcitx5-rime"
        (src / "manifest.toml").write_text('packages = []\ntarget = "fcitx5"\nmerge = true\npreserve = ["profile"]\nlegacy_targets = { "fcitx5-rime" = "directory" }\n')
        (src / "settings.conf").write_text("template-v2")
        return old, ctx.env.config_dir / "fcitx5"

    def test_legacy_metadata_and_five_field_records_preserve_all_personal_data(self):
        for metadata in (True, False):
            with self.subTest(metadata=metadata), TempEnv() as ctx:
                old, new = self._fcitx(ctx, metadata=metadata)
                new.mkdir()
                (new / "gnome-user.conf").write_text("existing-shared-data")
                steps = transaction.unit_on("fcitx5-rime")
                self.assertTrue(all(step.ok for step in steps), steps)
                self.assertEqual((new / "settings.conf").read_text(), "personal-settings")
                self.assertEqual((new / "profile").read_text(), "personal-profile")
                self.assertEqual((new / "__custom__.conf").read_text(), "archived-personal")
                self.assertEqual((old / "foreign.conf").read_text(), "unowned-old")
                self.assertFalse((old / "settings.conf").exists())
                snapshot = json.loads((Path(steps[0].backup) / "snapshot.json").read_text())
                targets = {entry["target"] for entry in snapshot["paths"]}
                self.assertTrue({str(old), str(new), str(transaction.vault_dir("fcitx5-rime"))} <= targets)
                self.assertEqual(snapshot["version"], 2)
                self.assertTrue(all(step.ok for step in transaction.unit_off("fcitx5-rime")))
                self.assertEqual((new / "gnome-user.conf").read_text(), "existing-shared-data")
                self.assertEqual((old / "foreign.conf").read_text(), "unowned-old")
                self.assertFalse((new / "settings.conf").exists())
                self.assertTrue(all(step.ok for step in transaction.unit_on("fcitx5-rime")))
                self.assertEqual((new / "settings.conf").read_text(), "personal-settings")
                self.assertEqual((new / "profile").read_text(), "personal-profile")

    def test_migration_conflict_is_pending_then_force_preserves_old_modification(self):
        with TempEnv() as ctx:
            old, new = self._fcitx(ctx, metadata=False)
            new.mkdir()
            (new / "settings.conf").write_text("existing-new-settings")
            steps = transaction.unit_on("fcitx5-rime")
            self.assertFalse(steps[0].ok)
            self.assertIn("settings.conf", steps[0].conflicts)
            self.assertEqual(ledger.get_deployment("fcitx5-rime")["pending"], "migration")
            self.assertEqual((new / "settings.conf").read_text(), "existing-new-settings")
            self.assertEqual((old / "settings.conf").read_text(), "personal-settings")
            self.assertFalse(transaction.unit_off("fcitx5-rime")[0].ok)
            steps = transaction.unit_on("fcitx5-rime", force=True)
            self.assertTrue(all(step.ok for step in steps), steps)
            self.assertEqual((new / "settings.conf").read_text(), "personal-settings")
            self.assertTrue(Path(steps[0].backup, "snapshot.json").exists())
            self.assertIsNone(ledger.get_deployment("fcitx5-rime")["pending"])

    def test_migration_snapshots_restore_old_new_vault_and_five_field_state(self):
        from nyxuri.state.backup import rollback_configs
        for force in (False, True):
            with self.subTest(force=force), TempEnv() as ctx:
                old, new = self._fcitx(ctx, metadata=False)
                new.mkdir()
                (new / "settings.conf").write_text("existing-new-settings")
                steps = transaction.unit_on("fcitx5-rime", force=force)
                self.assertEqual(steps[0].ok, force)
                with mock.patch("builtins.print"):
                    self.assertTrue(rollback_configs(steps[0].backup))
                self.assertEqual((old / "settings.conf").read_text(), "personal-settings")
                self.assertEqual((old / "profile").read_text(), "personal-profile")
                self.assertEqual((new / "settings.conf").read_text(), "existing-new-settings")
                self.assertEqual((transaction.vault_dir("fcitx5-rime") / "__custom__.conf").read_text(), "archived-personal")
                self.assertEqual(ledger.get_deployment("fcitx5-rime"), {})
                self.assertEqual(ledger.get_unit("fcitx5-rime")["state"], "enabled")

    def test_copy_failure_retains_old_files_and_retries(self):
        with TempEnv() as ctx:
            old, new = self._fcitx(ctx)
            from nyxuri.deploy import atomic
            real = atomic.atomic_replace_item
            def fail_settings(src, dst, *args, **kwargs):
                return False if src.name == "settings.conf" else real(src, dst, *args, **kwargs)
            with mock.patch.object(atomic, "atomic_replace_item", side_effect=fail_settings):
                steps = transaction.unit_on("fcitx5-rime")
            self.assertFalse(steps[-1].ok)
            self.assertEqual((old / "profile").read_text(), "personal-profile")
            self.assertEqual((old / "settings.conf").read_text(), "personal-settings")
            self.assertEqual(ledger.get_deployment("fcitx5-rime")["target"], str(old))
            steps = transaction.unit_on("fcitx5-rime")
            self.assertTrue(all(step.ok for step in steps), steps)
            self.assertEqual((new / "settings.conf").read_text(), "personal-settings")

    def test_off_old_record_never_withdraws_new_shared_directory(self):
        with TempEnv() as ctx:
            old, new = self._fcitx(ctx, metadata=False)
            new.mkdir()
            (new / "settings.conf").write_text("existing-shared")
            self.assertTrue(all(step.ok for step in transaction.unit_off("fcitx5-rime")))
            self.assertEqual((new / "settings.conf").read_text(), "existing-shared")
            self.assertFalse((old / "settings.conf").exists())
            self.assertEqual(ledger.get_deployment("fcitx5-rime")["target"], str(old))

    def test_pictures_target_tracks_localized_and_changed_directory(self):
        with TempEnv() as ctx:
            _stage(ctx, {"wallpapers": {"manifest": 'merge = true\ntarget = "~/Pictures/Wallpapers"\n',
                                        "files": {"fallback.png": "fallback-v1"}}})
            self.assertTrue(transaction.unit_on("wallpapers")[0].ok)
            old = ctx.home / "Pictures/Wallpapers"
            (old / "user.jpg").write_text("personal-picture")
            src = ctx.env.units_src / "wallpapers/manifest.toml"
            src.write_text('packages = []\nmerge = true\ntarget = "@pictures/Wallpapers"\nlegacy_targets = { "~/Pictures/Wallpapers" = "merge" }\n')
            localized = ctx.home / "图片"
            with mock.patch("nyxuri.core.get_pics_dir", return_value=localized):
                steps = transaction.unit_on("wallpapers")
                self.assertTrue(all(step.ok for step in steps), steps)
                self.assertTrue((localized / "Wallpapers/fallback.png").exists())
                self.assertEqual((old / "user.jpg").read_text(), "personal-picture")
                self.assertFalse((old / "fallback.png").exists())
            next_pics = ctx.home / "Photos"
            with mock.patch("nyxuri.core.get_pics_dir", return_value=next_pics):
                self.assertTrue(transaction.unit_refresh("wallpapers")[0].ok)
                self.assertTrue((next_pics / "Wallpapers/fallback.png").exists())
                self.assertFalse((localized / "Wallpapers/fallback.png").exists())
                self.assertTrue(transaction.unit_off("wallpapers")[0].ok)


class TestConditionalPortalRules(unittest.TestCase):
    """Portal 专用规则覆盖全部受支持且启用的桌面，普通 GNOME 配置保留。"""

    def _portal(self, ctx, *, legacy=False):
        manifest = '' if legacy else ('merge = true\nlegacy_targets = { "xdg-desktop-portal" = "directory" }\n'
                     'when_units = { "niri-portals.conf" = ["niri"], "mango-portals.conf" = ["mango"] }\n'
                     'retired_files = ["portals.conf"]\n')
        files = {"niri-portals.conf": "niri-route", "mango-portals.conf": "mango-route"}
        if legacy:
            files["portals.conf"] = "old-generic-route"
        _stage(ctx, {"niri": {"files": {"config.kdl": "niri-config"}},
                     "mango": {"manifest": '[platforms.ubuntu]\nsupported = false\nreason = "not supported"\n',
                               "files": {"config.conf": "mango-config"}},
                     "xdg-desktop-portal": {"manifest": manifest, "files": files}})
        return ctx.env.config_dir / "xdg-desktop-portal"

    def test_all_enabled_supported_wms_and_toggle_without_autoenable(self):
        with TempEnv() as ctx, mock.patch("nyxuri.pkg.platform.current_platform", return_value="arch"):
            dest = self._portal(ctx)
            self.assertTrue(transaction.unit_on("niri")[0].ok)
            self.assertIsNone(ledger.get_unit("xdg-desktop-portal"))
            self.assertTrue(transaction.unit_on("mango")[0].ok)
            self.assertTrue(transaction.unit_on("xdg-desktop-portal")[0].ok)
            self.assertTrue((dest / "niri-portals.conf").exists())
            self.assertTrue((dest / "mango-portals.conf").exists())
            self.assertFalse((dest / "portals.conf").exists())
            (dest / "niri-portals.conf").write_text("personal-niri-route")
            self.assertTrue(all(step.ok for step in transaction.unit_off("niri")))
            self.assertFalse((dest / "niri-portals.conf").exists())
            self.assertTrue((dest / "mango-portals.conf").exists())
            self.assertTrue(all(step.ok for step in transaction.unit_on("niri")))
            self.assertEqual((dest / "niri-portals.conf").read_text(), "personal-niri-route")
            with mock.patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"):
                self.assertTrue(transaction.unit_refresh("xdg-desktop-portal")[0].ok)
                self.assertFalse((dest / "mango-portals.conf").exists())
                self.assertTrue((dest / "niri-portals.conf").exists())
            self.assertTrue(transaction.unit_off("xdg-desktop-portal")[0].ok)
            self.assertTrue(transaction.unit_off("niri")[0].ok)
            self.assertEqual(ledger.get_unit("xdg-desktop-portal")["state"], "disabled")

    def test_rollback_restores_wm_set_portal_bytes_and_pending_together(self):
        from nyxuri.state.backup import backup_configs, rollback_configs
        with TempEnv() as ctx, mock.patch("nyxuri.pkg.platform.current_platform", return_value="arch"):
            dest = self._portal(ctx)
            for uid in ("niri", "mango", "xdg-desktop-portal"):
                self.assertTrue(all(step.ok for step in transaction.unit_on(uid)))
            with mock.patch("builtins.print"):
                snapshot = backup_configs(interactive=False)
            (dest / "niri-portals.conf").write_text("after-snapshot-personal-rule")
            self.assertTrue(all(step.ok for step in transaction.unit_off("niri")))
            self.assertFalse((dest / "niri-portals.conf").exists())
            with mock.patch("builtins.print"):
                self.assertTrue(rollback_configs(str(snapshot)))
            for uid in ("niri", "mango", "xdg-desktop-portal"):
                self.assertEqual(ledger.get_unit(uid)["state"], "enabled")
                self.assertIsNone(ledger.get_deployment(uid)["pending"])
            self.assertEqual((dest / "niri-portals.conf").read_text(), "niri-route")
            self.assertEqual((dest / "mango-portals.conf").read_text(), "mango-route")
            self.assertFalse((dest / "portals.conf").exists())

    def test_generic_retirement_requires_exact_old_identity(self):
        for variant in ("unchanged", "modified", "unknown"):
            with self.subTest(variant=variant), TempEnv() as ctx:
                dest = self._portal(ctx, legacy=True)
                if variant != "unknown":
                    self.assertTrue(transaction.unit_on("xdg-desktop-portal")[0].ok)
                else:
                    dest.mkdir(parents=True)
                if variant != "unchanged":
                    (dest / "portals.conf").write_text("gnome-personal-route")
                (dest / "gnome-portals.conf").write_text("gnome-route")
                src = ctx.env.units_src / "xdg-desktop-portal"
                (src / "portals.conf").unlink()
                (src / "manifest.toml").write_text('packages = []\nmerge = true\nlegacy_targets = { "xdg-desktop-portal" = "directory" }\nwhen_units = { "niri-portals.conf" = ["niri"], "mango-portals.conf" = ["mango"] }\nretired_files = ["portals.conf"]\n')
                steps = transaction.unit_on("xdg-desktop-portal")
                self.assertTrue(all(step.ok for step in steps), steps)
                self.assertEqual((dest / "gnome-portals.conf").read_text(), "gnome-route")
                self.assertFalse((dest / "niri-portals.conf").exists())
                self.assertFalse((dest / "mango-portals.conf").exists())
                if variant == "unchanged":
                    self.assertFalse((dest / "portals.conf").exists())
                    self.assertTrue(Path(steps[0].backup, "snapshot.json").exists())
                else:
                    self.assertEqual((dest / "portals.conf").read_text(), "gnome-personal-route")
                    self.assertIn("foreign-left: portals.conf", steps[0].detail)
                self.assertTrue(transaction.unit_off("xdg-desktop-portal")[0].ok)
                self.assertEqual((dest / "gnome-portals.conf").read_text(), "gnome-route")
                if variant != "unchanged":
                    self.assertEqual((dest / "portals.conf").read_text(), "gnome-personal-route")
