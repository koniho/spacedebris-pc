"""Platform-native filesystem locations used by Space Debris."""

import os
import sys
from pathlib import Path


def get_user_data_dir() -> Path:
    """Return the writable per-user application data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Space Debris"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Space Debris"

    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "space-debris"


def get_bundled_config_dir() -> Path:
    """Return the read-only configuration defaults bundled with the game."""
    return Path(__file__).resolve().parent / "config"
