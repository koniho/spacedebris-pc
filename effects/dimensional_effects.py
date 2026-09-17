"""Dimensional tear and flash effects for boss animations.

Factored out from PhaseShiftBoss death animation for reuse.
"""

import math
import numpy as np
import pyqtgraph as pg
import random_manager


class DimensionalTear:
    """A jagged line representing a tear in dimensional space."""

    def __init__(self, view, center_pos, color=None, spread=200):
        """Initialize a dimensional tear.

        Args:
            view: PyQtGraph view to add items to.
            center_pos: Center position (x, y) around which to spawn tears.
            color: RGB tuple for tear color. If None, uses magenta.
            spread: How far from center tears can spawn.
        """
        self.view = view
        self.center_pos = center_pos
        self.color = color or (255, 0, 255)
        self.timer = 0.0
        self.duration = 0.5
        self.completed = False

        # Create jagged tear line
        num_points = random_manager.randint(8, 15)
        start_x = center_pos[0] + random_manager.uniform(-spread, spread)
        start_y = center_pos[1] + random_manager.uniform(-spread, spread)

        # Random direction for the tear
        angle = random_manager.uniform(0, 2 * math.pi)
        length = random_manager.uniform(30, 80)

        x_points = []
        y_points = []
        for i in range(num_points):
            progress = i / (num_points - 1)
            base_x = start_x + math.cos(angle) * length * progress
            base_y = start_y + math.sin(angle) * length * progress
            # Add jaggedness perpendicular to main direction
            perp_angle = angle + math.pi / 2
            jag = random_manager.uniform(-15, 15)
            x_points.append(base_x + math.cos(perp_angle) * jag)
            y_points.append(base_y + math.sin(perp_angle) * jag)

        self.item = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=pg.mkPen(color=(*self.color, 255), width=3)
        )
        self.view.addItem(self.item)

    def update(self, dt):
        """Update the tear animation.

        Returns:
            True if still active, False if completed.
        """
        self.timer += dt

        if self.timer < self.duration:
            progress = self.timer / self.duration
            alpha = int(255 * (1 - progress))
            width = 3 + int(2 * (1 - progress))
            self.item.setPen(pg.mkPen(color=(*self.color, alpha), width=width))
            return True

        self.completed = True
        return False

    def cleanup(self):
        """Remove the tear from the view."""
        if self.item.scene():
            self.view.removeItem(self.item)


class DimensionalFlash:
    """A bright flash effect emanating from a point."""

    def __init__(self, view, pos, color=None, max_radius=100, duration=0.3):
        """Initialize a dimensional flash.

        Args:
            view: PyQtGraph view to add items to.
            pos: Position (x, y) of the flash center.
            color: RGB tuple for flash color. If None, uses white.
            max_radius: Maximum radius the flash expands to.
            duration: How long the flash lasts.
        """
        self.view = view
        self.pos = pos
        self.color = color or (255, 255, 255)
        self.max_radius = max_radius
        self.duration = duration
        self.timer = 0.0
        self.completed = False

        # Create expanding ring
        self.ring = pg.PlotCurveItem(pen=pg.mkPen(color=(*self.color, 255), width=8))
        self.view.addItem(self.ring)

        # Create inner glow
        self.glow = pg.ScatterPlotItem(
            pos=[pos], size=20, brush=pg.mkBrush(*self.color, 200), pen=None
        )
        self.view.addItem(self.glow)

    def update(self, dt):
        """Update the flash animation.

        Returns:
            True if still active, False if completed.
        """
        self.timer += dt

        if self.timer < self.duration:
            progress = self.timer / self.duration
            radius = self.max_radius * progress
            alpha = int(255 * (1 - progress))

            # Update ring
            angles = np.linspace(0, 2 * np.pi, 40)
            x_points = self.pos[0] + radius * np.cos(angles)
            y_points = self.pos[1] + radius * np.sin(angles)
            self.ring.setData(x=x_points, y=y_points)
            self.ring.setPen(
                pg.mkPen(color=(*self.color, alpha), width=max(1, int(8 * (1 - progress))))
            )

            # Update glow
            glow_size = 20 + 30 * progress
            glow_alpha = int(200 * (1 - progress))
            self.glow.setData(
                pos=[self.pos], size=glow_size, brush=pg.mkBrush(*self.color, glow_alpha)
            )

            return True

        self.completed = True
        return False

    def cleanup(self):
        """Remove the flash from the view."""
        if self.ring.scene():
            self.view.removeItem(self.ring)
        if self.glow.scene():
            self.view.removeItem(self.glow)


class CollapsingRing:
    """A ring that collapses toward a center point."""

    def __init__(self, view, center_pos, initial_radius, speed, color, width=10):
        """Initialize a collapsing ring.

        Args:
            view: PyQtGraph view to add items to.
            center_pos: Center position (x, y) to collapse toward.
            initial_radius: Starting radius of the ring.
            speed: Speed at which the ring collapses (pixels per second).
            color: RGB tuple for ring color.
            width: Line width of the ring.
        """
        self.view = view
        self.center_pos = center_pos
        self.radius = initial_radius
        self.speed = speed
        self.color = color
        self.width = width
        self.completed = False

        self.item = pg.PlotCurveItem(pen=pg.mkPen(color=(*color, 200), width=width))
        self.view.addItem(self.item)

    def update(self, dt):
        """Update the collapsing ring.

        Returns:
            True if still active, False if completed.
        """
        self.radius -= self.speed * dt

        if self.radius > 0:
            angles = np.linspace(0, 2 * np.pi, 60)
            x_points = self.center_pos[0] + self.radius * np.cos(angles)
            y_points = self.center_pos[1] + self.radius * np.sin(angles)
            self.item.setData(x=x_points, y=y_points)

            # Fade and intensify as it collapses
            alpha = min(255, int(200 + 55 * (1 - self.radius / 300)))
            self.item.setPen(pg.mkPen(color=(*self.color, alpha), width=self.width))
            return True

        self.completed = True
        return False

    def cleanup(self):
        """Remove the ring from the view."""
        if self.item.scene():
            self.view.removeItem(self.item)


class DimensionalEffectManager:
    """Manager for creating and updating dimensional effects."""

    def __init__(self, view):
        """Initialize the effect manager.

        Args:
            view: PyQtGraph view to add effects to.
        """
        self.view = view
        self.tears = []
        self.flashes = []
        self.rings = []

    def create_tear(self, center_pos, color=None, spread=200):
        """Create a dimensional tear effect."""
        tear = DimensionalTear(self.view, center_pos, color, spread)
        self.tears.append(tear)
        return tear

    def create_flash(self, pos, color=None, max_radius=100, duration=0.3):
        """Create a dimensional flash effect."""
        flash = DimensionalFlash(self.view, pos, color, max_radius, duration)
        self.flashes.append(flash)
        return flash

    def create_collapsing_ring(self, center_pos, initial_radius, speed, color, width=10):
        """Create a collapsing ring effect."""
        ring = CollapsingRing(self.view, center_pos, initial_radius, speed, color, width)
        self.rings.append(ring)
        return ring

    def create_burst(self, center_pos, num_tears=5, num_flashes=3, colors=None):
        """Create a burst of dimensional effects.

        Args:
            center_pos: Center position of the burst.
            num_tears: Number of tears to create.
            num_flashes: Number of flashes to create.
            colors: List of RGB colors to use. If None, uses default magenta/cyan.
        """
        if colors is None:
            colors = [(255, 0, 255), (0, 255, 255)]

        for _ in range(num_tears):
            color = random_manager.choice(colors)
            self.create_tear(center_pos, color)

        for _ in range(num_flashes):
            color = random_manager.choice(colors)
            offset_x = random_manager.uniform(-50, 50)
            offset_y = random_manager.uniform(-50, 50)
            pos = (center_pos[0] + offset_x, center_pos[1] + offset_y)
            self.create_flash(pos, color, max_radius=60, duration=0.2)

    def update(self, dt):
        """Update all active effects."""
        # Update tears
        for tear in self.tears[:]:
            if not tear.update(dt):
                tear.cleanup()
                self.tears.remove(tear)

        # Update flashes
        for flash in self.flashes[:]:
            if not flash.update(dt):
                flash.cleanup()
                self.flashes.remove(flash)

        # Update rings
        for ring in self.rings[:]:
            if not ring.update(dt):
                ring.cleanup()
                self.rings.remove(ring)

    def cleanup(self):
        """Clean up all effects."""
        for tear in self.tears:
            tear.cleanup()
        self.tears.clear()

        for flash in self.flashes:
            flash.cleanup()
        self.flashes.clear()

        for ring in self.rings:
            ring.cleanup()
        self.rings.clear()

    def is_active(self):
        """Check if any effects are still active."""
        return bool(self.tears or self.flashes or self.rings)
