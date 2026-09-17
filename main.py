#!/usr/bin/env python
"""Main entry point and game window."""

import os
import sys
import argparse
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer, Qt, QElapsedTimer
from PyQt5.QtGui import QKeyEvent
import pyqtgraph as pg
from debug_log import debug_print as print

# Try to import compiled Qt resources (for bundled app)
try:
    import resources_rc  # noqa: F401

    print("Loaded compiled Qt resources")
except ImportError:
    pass  # Running from source, resources loaded from filesystem

from game_engine import GameEngine
from random_manager import set_global_seed, get_random_manager

# Enable high-DPI scaling
# Note: os.environ must be set BEFORE QApplication is instantiated
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)


class SpaceDebrisWindow(QMainWindow):
    """Main game window."""

    def __init__(self, antialias=False):
        super().__init__()
        self.setWindowTitle("Space Debris")
        self.resize(1200, 800)
        # Set up PyQtGraph
        pg.setConfigOptions(antialias=antialias)

        # Create the graphics view
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.setCentralWidget(self.graphics_widget)

        # Create plot view
        self.view = self.graphics_widget.addPlot()
        self.view.hideButtons()
        self.view.setAspectLocked(True)
        self.view.hideAxis("left")
        self.view.hideAxis("bottom")
        self.view.setRange(xRange=[-400, 400], yRange=[-300, 300])
        self.view.setMouseEnabled(x=False, y=False)

        self.engine = GameEngine(self.view)

        # Set up game timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)  # ~60 FPS

        # Track delta time
        self.elapsed_timer = QElapsedTimer()
        self.elapsed_timer.start()
        self.last_time = 0

    def update_game(self):
        """Update game state."""
        current_time = self.elapsed_timer.elapsed()
        dt = (current_time - self.last_time) / 1000.0  # Convert to seconds
        self.last_time = current_time

        # Limit delta time to prevent huge jumps
        dt = min(dt, 0.05)

        self.engine.update(dt)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.isAutoRepeat():
            return

        # Handle ESC key specially
        if event.key() == Qt.Key_Escape:
            key = "\x1b"  # ESC character
        else:
            # Check for Shift+Q to quit before uppercasing
            if event.text() == "Q":
                self.close()
                return
            key = event.text().upper()

        timestamp = self.elapsed_timer.elapsed()

        self.engine.on_key_press(key, timestamp)

    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release events."""
        if event.isAutoRepeat():
            return

        # Handle ESC key specially
        if event.key() == Qt.Key_Escape:
            key = "\x1b"  # ESC character
        else:
            key = event.text().upper()

        timestamp = self.elapsed_timer.elapsed()

        self.engine.on_key_release(key)

    def closeEvent(self, event):
        """Handle window close event."""
        # Close config window if open
        if hasattr(self.engine, "config_ui") and self.engine.config_ui is not None:
            self.engine.config_ui.close()

        # Clean up game engine
        if hasattr(self.engine, "cleanup"):
            self.engine.cleanup()

        event.accept()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Space Debris - A typing game")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic gameplay (e.g., --seed 12345)",
    )
    parser.add_argument(
        "--replay",
        type=str,
        default=None,
        metavar="FILE",
        help="Replay key presses from FILE (e.g., --replay session.json)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable diagnostic console logging",
    )
    parser.add_argument(
        "-a",
        "--no-antialias",
        action="store_false",
        default=True,
        dest="antialias",
        help="antialiasing by default",
    )

    args = parser.parse_args()

    # Note: if no seed specified RandomManager auto-generates one
    if args.seed is not None:
        set_global_seed(args.seed)

    app = QApplication(sys.argv)
    window = SpaceDebrisWindow(antialias=args.antialias)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
