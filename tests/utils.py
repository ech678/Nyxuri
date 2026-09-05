"""Shared test utilities: environment isolation, temp HOME, subprocess mocks.

Design principle: tests must NEVER touch the real ~/.config, ~/.local, or ~/.cache.
All Environment access is patched to point at a temp directory for the entire test.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import nyxniri.core as core


class TempEnv:
    """Context manager that fully isolates the NyxNiri Environment to a temp HOME.

    Patches core._ENV, os.environ["HOME"], and get_env() so that every module
    that calls get_env() gets the temp environment — not the real one.
    """

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self._old_env = {}
        self._patcher = None

    def __enter__(self):
        home = self.home
        # Create directory skeleton
        (home / ".config").mkdir(parents=True, exist_ok=True)
        (home / ".local" / "bin").mkdir(parents=True, exist_ok=True)
        (home / ".local" / "state" / "NyxNiri").mkdir(parents=True, exist_ok=True)
        (home / ".cache").mkdir(parents=True, exist_ok=True)
        (home / "Pictures").mkdir(parents=True, exist_ok=True)

        # Save and override environment variables
        for key in ("HOME", "XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
            self._old_env[key] = os.environ.get(key)
        os.environ["HOME"] = str(home)
        os.environ["XDG_STATE_HOME"] = str(home / ".local" / "state")
        os.environ["XDG_CONFIG_HOME"] = str(home / ".config")
        os.environ["XDG_CACHE_HOME"] = str(home / ".cache")

        # Reset cached Environment so next get_env() picks up new HOME
        core._ENV = None
        # Reset module-level caches that leak across tests (isolation, §9).
        # _PICS_DIR_CACHE especially: get_pics_dir() otherwise returns a path
        # from a previously-deleted temp HOME, breaking wallpaper assertions.
        core._PICS_DIR_CACHE = None
        import nyxniri.deploy.deploy as _deploy_core
        import nyxniri.deploy.hardware as _deploy_hw
        import nyxniri.deploy.manifest as _deploy_manifest
        import nyxniri.deps as _deps
        import nyxniri.modules.greeter as _greeter
        _deploy_core._CONFIG_ITEMS_CACHE = []
        _deploy_hw._IS_NVIDIA = None
        _deploy_manifest._MANIFEST_CACHE = None
        _deps._AUR_HELPER_CACHE = None
        _deps._PACMAN_INSTALLED_CACHE = None
        _deps._FLATPAK_LIST_CACHE = None
        _deps._FC_LIST_CACHE = None
        _deps._MISSING_DEPS_CACHE = None
        _deps._GI_CACHE = None
        _greeter._GREETER_STATUS_CACHE = None

        # Build the Environment with temp HOME, then force repo mode
        env = core.get_env()
        env.run_mode = "repo"
        env.mode_label = "Local Path"
        env.repo_dir = Path(__file__).resolve().parent.parent
        env.configs_src = env.repo_dir / "configs"
        env.assets_src = env.repo_dir / "assets"
        self.env = env

        return self

    def __exit__(self, *exc):
        # Restore environment variables
        for key, val in self._old_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        # Reset cached Environment so subsequent code uses real HOME
        core._ENV = None
        self._tmp.cleanup()
        return False
