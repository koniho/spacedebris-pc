"""Letter animation effects for enemies."""

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QGraphicsEllipseItem
from font_manager import font_manager
from config import get_button_label


class LetterActivationAnim:
    """Animation for when a letter is activated/typed."""

    def __init__(self, text_item: pg.TextItem, button: str):
        """Initialize letter activation animation."""
        self.text_item = text_item
        self.button = button
        self.duration = 0.3
        self.elapsed = 0.0
        self.base_size = 16
        self.max_size = 28
        self.completed = False

    def update(self, dt: float) -> bool:
        """Update animation. Returns True if animation is still running."""
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        if progress < 0.5:
            # Grow phase: white → green
            t = progress * 2
            size = int(self.base_size + (self.max_size - self.base_size) * t)
            r = int(255 - 155 * t)  # 255 → 100
            g = 255
            b = int(255 - 155 * t)  # 255 → 100
        else:
            # Settle phase: green → cyan
            t = (progress - 0.5) * 2
            size = int(self.max_size - (self.max_size - self.base_size * 1.2) * t)
            r = int(100 - 100 * t)  # 100 → 0
            g = 255
            b = int(100 + 155 * t)  # 100 → 255

        # Update font size and color without setHtml (setColor is overridable by reset)
        font = font_manager.get_enemy_letter_font(size, bold=True)
        self.text_item.setFont(font)
        self.text_item.setColor((r, g, b))

        if progress >= 1.0:
            self.completed = True
            return False
        return True
        b = int(b1 + (b2 - b1) * t)

        return f"#{r:02x}{g:02x}{b:02x}"

    def cleanup(self):
        """Clean up animation and restore letter to normal appearance."""
        # Reset letter to normal appearance
        font = font_manager.get_enemy_letter_font(20, bold=True)
        self.text_item.setFont(font)
        self.text_item.setText(get_button_label(self.button))
        self.text_item.setColor((255, 255, 255))  # White text
        self.completed = True


class EnemyLetterRingEffect:
    """Expanding ring effect for enemy letter activation (intro screen style)."""

    def __init__(self, view, position, color):
        """Initialize expanding ring effect."""
        self.view = view
        self.position = position
        self.color = color
        self.duration = 0.6
        self.max_radius = 60  # Smaller than intro screen for enemy letters
        self.elapsed = 0.0
        self.completed = False
        self.current_radius = 0

        # Create ring using ellipse item (no fill, just outline)
        self.ring = QGraphicsEllipseItem(0, 0, 0, 0)
        self.ring.setPos(position[0], position[1])
        self.ring.setPen(pg.mkPen(color=color, width=4))
        self.ring.setBrush(pg.mkBrush(None))  # No fill
        self.view.addItem(self.ring)

        # Create inner glow ring
        self.glow_ring = QGraphicsEllipseItem(0, 0, 0, 0)
        self.glow_ring.setPos(position[0], position[1])
        self.glow_ring.setPen(pg.mkPen(color=color, width=8))
        self.glow_ring.setBrush(pg.mkBrush(None))  # No fill
        self.glow_ring.setOpacity(0.4)
        self.view.addItem(self.glow_ring)

    def update(self, dt: float) -> bool:
        """Update ring expansion. Returns True if still active."""
        if self.completed:
            return False

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Calculate current radius with easing
        eased_progress = 1 - (1 - progress) ** 2  # Ease-out
        current_radius = self.max_radius * eased_progress

        # Calculate opacity (fade out near end)
        opacity = 1.0 - progress**2

        # Update ring size and opacity
        # setRect takes x, y, width, height relative to position
        self.ring.setRect(-current_radius, -current_radius, current_radius * 2, current_radius * 2)
        self.ring.setOpacity(opacity)

        # Update glow ring (slightly larger)
        glow_radius = current_radius * 1.1
        self.glow_ring.setRect(-glow_radius, -glow_radius, glow_radius * 2, glow_radius * 2)
        self.glow_ring.setOpacity(opacity * 0.4)

        # Check if animation complete
        if progress >= 1.0:
            self.completed = True
            self.cleanup()
            return False

        return True

    def cleanup(self):
        """Explicitly clean up visual elements."""
        if self.ring is not None:
            scene = self.ring.scene()
            if scene is not None:
                scene.removeItem(self.ring)
            self.ring = None
        if self.glow_ring is not None:
            scene = self.glow_ring.scene()
            if scene is not None:
                scene.removeItem(self.glow_ring)
            self.glow_ring = None


class HexagonFlashAnim:
    """Animation to restore hexagon appearance after flash effect."""

    def __init__(self, hexagon, original_pen, original_brush, duration=0.2):
        """Initialize hexagon flash animation."""
        self.hexagon = hexagon
        self.original_pen = original_pen
        self.original_brush = original_brush
        self.duration = duration
        self.elapsed = 0.0
        self.completed = False

    def update(self, dt: float) -> bool:
        """Update flash fade. Returns True if still active."""
        if self.completed:
            return False

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Check if animation complete
        if progress >= 1.0:
            self.completed = True
            # Restore original appearance
            self.hexagon.setPen(self.original_pen)
            self.hexagon._fill.setBrush(self.original_brush)
            return False

        return True

    def cleanup(self):
        """Clean up animation and restore hexagon to original appearance."""
        # Restore original appearance immediately
        self.hexagon.setPen(self.original_pen)
        self.hexagon._fill.setBrush(self.original_brush)
        self.completed = True


class DisengageFlashAnim:
    """Yellow flash animation on existing hexagon when player misses/disengages."""

    def __init__(self, hexagon):
        """Initialize disengage flash animation.

        Args:
            hexagon: The hexagon PlotCurveItem to flash (has _fill attribute for fill)
        """
        self.hexagon = hexagon
        self.duration = 0.2
        self.elapsed = 0.0
        self.completed = False

        # Store original appearance to restore later
        self.original_pen = hexagon.opts.get("pen")
        self.original_brush = hexagon._fill.opts.get("brush")

        # Set initial yellow flash (bright yellow outline and fill)
        self.hexagon.setPen(pg.mkPen(color=(255, 255, 0, 255), width=6))
        self.hexagon._fill.setBrush(pg.mkBrush(255, 255, 0, 150))

    def update(self, dt: float) -> bool:
        """Update animation. Returns True if still active."""
        if self.completed:
            return False

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Fade from yellow back to original
        alpha = int(255 * (1.0 - progress))
        fill_alpha = int(150 * (1.0 - progress))

        self.hexagon.setPen(pg.mkPen(color=(255, 255, 0, alpha), width=6))
        self.hexagon._fill.setBrush(pg.mkBrush(255, 255, 0, fill_alpha))

        if progress >= 1.0:
            self.completed = True
            self.cleanup()
            return False

        return True

    def cleanup(self):
        """Restore hexagon to original appearance."""
        self.hexagon.setPen(self.original_pen)
        self.hexagon._fill.setBrush(self.original_brush)
        self.completed = True
