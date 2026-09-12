"""GPU diagnostics and deployment contracts, isolated with TempEnv."""

import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from nyxniri.deploy.hardware import classify_gpu_devices
from nyxniri.deploy.deploy import deploy_selected_configs, test_deploy
from nyxniri.doctor import generate_bug_report
from tests.utils import TempEnv

# Realistic `LC_ALL=C lspci` snippets. Kernel-driver continuation lines omitted;
# the parser only reads the PCI device class line.
LSPCI_HYBRID_AMD = """\
01:00.0 3D controller: NVIDIA Corporation GA107M [GeForce RTX 3050 Mobile] (rev a1)
01:00.1 Audio device: NVIDIA Corporation Device 2291 (rev a1)
05:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Cezanne [Radeon Vega Series / Radeon Vega Mobile Series] (rev c5)
"""

LSPCI_HYBRID_INTEL = """\
00:02.0 VGA compatible controller: Intel Corporation TigerLake-LP GT2 [Iris Xe Graphics]
01:00.0 3D controller: NVIDIA Corporation GA107M [GeForce RTX 3050 Mobile]
"""

LSPCI_NVIDIA_DESKTOP = """\
01:00.0 VGA compatible controller: NVIDIA Corporation GA104 [GeForce RTX 3070 Lite Hash Rate] (rev a1)
01:00.1 Audio device: NVIDIA Corporation GA104 High Definition Audio Controller (rev a1)
"""

LSPCI_NVIDIA_ONLY_3D = """\
00:02.0 3D controller: NVIDIA Corporation Device 25a2
"""

LSPCI_AMD_ONLY = """\
05:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Cezanne
"""

LSPCI_NVIDIA_AUDIO_ON_AMD = """\
01:00.1 Audio device: NVIDIA Corporation Device 2291 (rev a1)
05:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Cezanne
"""

LSPCI_DUAL_VGA = """\
00:02.0 VGA compatible controller: Intel Corporation AlderLake-S GT1
01:00.0 VGA compatible controller: NVIDIA Corporation GA102 [GeForce RTX 3080]
"""


REMOVED_VARIABLES = (
    "GBM_BACKEND", "__GLX_VENDOR_LIBRARY_NAME",
    "LIBVA_DRIVER_NAME", "ELECTRON_OZONE_PLATFORM_HINT",
)
OLD_CONFIG = 'environment {\n' + ''.join(
    f'    {name} "personal-value"\n' for name in REMOVED_VARIABLES
) + '}\nscreenshot-path "/personal/screenshots/%s.png"\n'


class TestGpuContracts(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_device_classification(self):
        for pci, expected in (
            (LSPCI_HYBRID_AMD, "NVIDIA + other GPU devices"),
            (LSPCI_HYBRID_INTEL, "NVIDIA + other GPU devices"),
            (LSPCI_DUAL_VGA, "NVIDIA + other GPU devices"),
            (LSPCI_NVIDIA_DESKTOP, "NVIDIA GPU devices only"),
            (LSPCI_NVIDIA_ONLY_3D, "NVIDIA GPU devices only"),
            ("00:01.0 Display controller: NVIDIA Corporation", "NVIDIA GPU devices only"),
            (LSPCI_AMD_ONLY, "Other GPU devices only"),
            (LSPCI_NVIDIA_AUDIO_ON_AMD, "Other GPU devices only"),
            ("00:01.0 Audio device: NVIDIA Corporation", "Unknown"),
            ("", "Unknown"),
            ("  \n", "Unknown"),
        ):
            with self.subTest(pci=pci):
                self.assertEqual(classify_gpu_devices(pci), expected)
                self.assertEqual(classify_gpu_devices(pci.upper()), expected)

    def _old_config(self):
        target = self.ctx.env.config_dir / "niri"
        target.mkdir()
        (target / "config.kdl").write_text(OLD_CONFIG)
        (target / "__custom__.kdl").write_text(OLD_CONFIG)
        return target

    def test_default_redeploy_removes_variables_and_preserves_custom(self):
        target = self._old_config()
        with patch("nyxniri.deploy.deploy._phase_post_install_services"), \
             patch("nyxniri.core.get_pics_dir", return_value=self.ctx.home / "Pictures"), \
             patch("nyxniri.deploy.templates.get_pics_dir", return_value=self.ctx.home / "Pictures"), \
             patch("subprocess.run", side_effect=AssertionError("Unexpected external command")):
            self.assertEqual(deploy_selected_configs(items_to_deploy=["niri"]), [])
            first = (target / "config.kdl").read_bytes()
            self.assertEqual(deploy_selected_configs(items_to_deploy=["niri"]), [])
            self.assertEqual((target / "config.kdl").read_bytes(), first)
        for variable in REMOVED_VARIABLES:
            self.assertNotIn(variable.encode(), first)
        self.assertIn(b'~/Pictures/Screenshots/', first)
        self.assertNotIn(b"/home/user", first)
        self.assertEqual((target / "__custom__.kdl").read_text(), OLD_CONFIG)

    def test_other_app_deploy_leaves_niri_untouched(self):
        target = self._old_config()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
        with patch("nyxniri.deploy.deploy._phase_post_install_services"):
            self.assertEqual(deploy_selected_configs(items_to_deploy=["kitty"]), [])
        self.assertEqual(
            {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}, before,
        )

    def test_test_deploy_removes_variables(self):
        target = self._old_config()
        with patch("nyxniri.deploy.deploy.deploy_wallpapers"), \
             patch("nyxniri.deploy.deploy.render_completion_screen"):
            self.assertTrue(test_deploy())
        for variable in REMOVED_VARIABLES:
            self.assertNotIn(variable, (target / "config.kdl").read_text())
        self.assertEqual((target / "__custom__.kdl").read_text(), OLD_CONFIG)

    def test_report_reuses_pci_probe_and_never_changes_config(self):
        target = self._old_config()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
        cases = (
            (0, LSPCI_HYBRID_AMD, None, "NVIDIA + other GPU devices"),
            (1, LSPCI_NVIDIA_DESKTOP, None, "Unknown"),
            (0, "", None, "Unknown"),
            (0, "", OSError("missing"), "Unknown"),
            (0, "", subprocess.TimeoutExpired(["lspci"], 15), "Unknown"),
        )
        for code, stdout, error, expected in cases:
            with self.subTest(code=code, error=error, stdout=stdout):
                def fake_run(argv, **kwargs):
                    if error:
                        raise error
                    return subprocess.CompletedProcess(argv, code, stdout=stdout, stderr="")
                with patch("nyxniri.doctor.shutil.which", side_effect=lambda name: "/usr/bin/lspci" if name == "lspci" else None), \
                     patch("nyxniri.doctor.subprocess.run", side_effect=fake_run) as run:
                    report = generate_bug_report().read_text()
                run.assert_called_once()
                self.assertEqual(run.call_args.args, (["lspci"],))
                kwargs = run.call_args.kwargs
                self.assertEqual(kwargs["env"]["LC_ALL"], "C")
                self.assertEqual(kwargs["env"]["HOME"], str(self.ctx.home))
                self.assertEqual(kwargs["timeout"], 15)
                self.assertTrue(kwargs["capture_output"])
                self.assertTrue(kwargs["text"])
                self.assertFalse(kwargs["check"])
                self.assertIn(f"PCI device classification: {expected} (not the active rendering GPU)", report)
                if expected == "Unknown":
                    self.assertNotIn(LSPCI_NVIDIA_DESKTOP.strip(), report)
        self.assertEqual(
            {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}, before,
        )

    def test_report_missing_lspci_is_unknown(self):
        with patch("nyxniri.doctor.shutil.which", return_value=None), \
             patch("nyxniri.doctor.subprocess.run") as run:
            report = generate_bug_report().read_text()
        run.assert_not_called()
        self.assertIn("PCI device classification: Unknown", report)


if __name__ == "__main__":
    unittest.main()
