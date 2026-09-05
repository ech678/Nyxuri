"""Contracts for NVIDIA hardware env patching.

Safety: TempEnv only. lspci is always mocked — never read the host GPU.
"""

import re
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from nyxniri.deploy.hardware import (
    _apply_nvidia_env,
    _classify_nvidia_role,
    _nvidia_role,
    _phase_hardware_patches,
)
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

COMMENTED = """\
environment {
    XDG_CURRENT_DESKTOP "niri"
    // NVIDIA env: deploy enables these only when NVIDIA is the display GPU
    // GBM_BACKEND "nvidia-drm"
    // __GLX_VENDOR_LIBRARY_NAME "nvidia"
    // LIBVA_DRIVER_NAME "nvidia"
}
"""

ENABLED = """\
environment {
    XDG_CURRENT_DESKTOP "niri"
    // NVIDIA env: deploy enables these only when NVIDIA is the display GPU
    GBM_BACKEND "nvidia-drm"
    __GLX_VENDOR_LIBRARY_NAME "nvidia"
    LIBVA_DRIVER_NAME "nvidia"
}
"""


def _env_enabled(content: str) -> bool:
    return bool(re.search(r'^\s*GBM_BACKEND\s+"nvidia-drm"', content, re.M))


def _env_commented(content: str) -> bool:
    return bool(re.search(r'^\s*//\s*GBM_BACKEND\s+"nvidia-drm"', content, re.M))


class TestClassifyNvidiaRole(unittest.TestCase):
    """Pure lspci-text parser. No subprocess."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_hybrid_amd_igpu_nvidia_3d(self):
        self.assertEqual(_classify_nvidia_role(LSPCI_HYBRID_AMD), "hybrid")

    def test_hybrid_intel_igpu_nvidia_3d(self):
        self.assertEqual(_classify_nvidia_role(LSPCI_HYBRID_INTEL), "hybrid")

    def test_nvidia_desktop_vga(self):
        self.assertEqual(_classify_nvidia_role(LSPCI_NVIDIA_DESKTOP), "primary")

    def test_nvidia_only_3d_is_primary(self):
        self.assertEqual(_classify_nvidia_role(LSPCI_NVIDIA_ONLY_3D), "primary")

    def test_amd_only(self):
        self.assertEqual(_classify_nvidia_role(LSPCI_AMD_ONLY), "none")

    def test_empty(self):
        self.assertEqual(_classify_nvidia_role(""), "none")

    def test_nvidia_audio_line_is_not_a_gpu(self):
        self.assertEqual(_classify_nvidia_role(LSPCI_NVIDIA_AUDIO_ON_AMD), "none")

    def test_dual_vga_nvidia_counts_as_primary(self):
        self.assertEqual(_classify_nvidia_role(LSPCI_DUAL_VGA), "primary")

    def test_case_insensitive(self):
        self.assertEqual(
            _classify_nvidia_role(LSPCI_HYBRID_AMD.upper()),
            "hybrid",
        )


class TestApplyNvidiaEnv(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_enable_uncomments(self):
        out = _apply_nvidia_env(COMMENTED, True)
        self.assertTrue(_env_enabled(out))
        self.assertFalse(_env_commented(out))
        self.assertIn('XDG_CURRENT_DESKTOP "niri"', out)

    def test_disable_recomments(self):
        out = _apply_nvidia_env(ENABLED, False)
        self.assertTrue(_env_commented(out))
        self.assertFalse(_env_enabled(out))

    def test_enable_is_idempotent(self):
        self.assertEqual(_apply_nvidia_env(ENABLED, True), ENABLED)

    def test_disable_is_idempotent(self):
        self.assertEqual(_apply_nvidia_env(COMMENTED, False), COMMENTED)

    def test_disable_does_not_double_comment(self):
        once = _apply_nvidia_env(ENABLED, False)
        twice = _apply_nvidia_env(once, False)
        self.assertEqual(once, twice)
        self.assertEqual(twice.count("GBM_BACKEND"), 1)


class TestLspciCommandShape(unittest.TestCase):
    """§9: mock subprocess.run, assert argv/env shape, do not mock the classifier."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_lspci_invocation_shape_and_cache(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((list(argv), kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout=LSPCI_HYBRID_AMD, stderr="")

        with patch("nyxniri.deploy.hardware.subprocess.run", side_effect=fake_run):
            self.assertEqual(_nvidia_role(), "hybrid")
            self.assertEqual(_nvidia_role(), "hybrid")

        self.assertEqual(len(calls), 1, "role is cached for the process")
        argv, kwargs = calls[0]
        self.assertEqual(argv, ["lspci"])
        self.assertTrue(kwargs.get("capture_output"))
        self.assertTrue(kwargs.get("text"))
        self.assertFalse(kwargs.get("check"))
        self.assertEqual(kwargs["env"]["LC_ALL"], "C")

    def test_lspci_failure_is_none(self):
        with patch("nyxniri.deploy.hardware.subprocess.run", side_effect=OSError("no lspci")):
            self.assertEqual(_nvidia_role(), "none")


class TestPhaseHardwarePatches(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.niri_conf = self._ctx.env.config_dir / "niri" / "config.kdl"

    def tearDown(self):
        self._ctx.__exit__()

    def _write(self, content: str) -> Path:
        self.niri_conf.parent.mkdir(parents=True, exist_ok=True)
        self.niri_conf.write_text(content, encoding="utf-8")
        return self.niri_conf

    def _run(self, lspci_text: str) -> str:
        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout=lspci_text, stderr="")

        with patch("nyxniri.deploy.hardware.subprocess.run", side_effect=fake_run):
            _phase_hardware_patches()
        return self.niri_conf.read_text(encoding="utf-8")

    def test_primary_uncomments(self):
        self._write(COMMENTED)
        out = self._run(LSPCI_NVIDIA_DESKTOP)
        self.assertTrue(_env_enabled(out))
        self.assertFalse(_env_commented(out))

    def test_hybrid_keeps_commented(self):
        self._write(COMMENTED)
        out = self._run(LSPCI_HYBRID_AMD)
        self.assertTrue(_env_commented(out))
        self.assertFalse(_env_enabled(out))

    def test_hybrid_recomments_old_deploy(self):
        """Existing hybrid installs already have the three lines uncommented."""
        self._write(ENABLED)
        out = self._run(LSPCI_HYBRID_AMD)
        self.assertTrue(_env_commented(out))
        self.assertFalse(_env_enabled(out))

    def test_none_recomments_old_deploy(self):
        self._write(ENABLED)
        out = self._run(LSPCI_AMD_ONLY)
        self.assertTrue(_env_commented(out))
        self.assertFalse(_env_enabled(out))

    def test_missing_config_is_noop(self):
        def fake_run(argv, **kwargs):
            self.fail("lspci must not run when config.kdl is absent")

        with patch("nyxniri.deploy.hardware.subprocess.run", side_effect=fake_run):
            _phase_hardware_patches()
        self.assertFalse(self.niri_conf.exists())


if __name__ == "__main__":
    unittest.main()
