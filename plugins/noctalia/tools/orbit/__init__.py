"""
Orbit Launcher (星环启动器) - Modern M3E Radial App Launcher & Intelligent Gemini Search Hub.
"""

from .window import OrbitLauncher
from .lock import acquire_instance_lock, release_instance_lock

__all__ = ["OrbitLauncher", "acquire_instance_lock", "release_instance_lock"]
