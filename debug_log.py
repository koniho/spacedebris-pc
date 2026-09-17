"""Debug-only console output for the game."""

import builtins
import sys


DEBUG_ENABLED = "--debug" in sys.argv


def debug_print(*args, **kwargs):
    """Print only when the game was launched with ``--debug``."""
    if DEBUG_ENABLED:
        builtins.print(*args, **kwargs)
