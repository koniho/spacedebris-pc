"""Visual effects used on the intro screen."""

import math

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt


class ExpandingRingEffect:
    """Expanding ring visual effect."""

    def __init__(self, view, position, color):
        self.view = view
        self.position = position
        self.color = color
        self.duration = 0.8
        self.max_radius = 100
        self.elapsed = 0.0

        # Create ring with thick outline and gradient
        self.ring = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=5))
        self.view.addItem(self.ring)

        # Create inner glow ring
        self.glow_ring = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=10, style=Qt.SolidLine))
        self.glow_ring.setOpacity(0.3)
        self.view.addItem(self.glow_ring)

    def update(self, dt):
        """Update effect animation."""
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Calculate radius and alpha
        radius = self.max_radius * progress
        alpha = int(255 * (1 - progress))

        # Generate circle points
        angles = np.linspace(0, 2 * np.pi, 50)
        x = self.position[0] + radius * np.cos(angles)
        y = self.position[1] + radius * np.sin(angles)

        # Update ring with gradient effect
        rgb = tuple(int(self.color[i : i + 2], 16) for i in (1, 3, 5))
        self.ring.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, alpha), width=5))

        # Update glow ring
        glow_alpha = int(alpha * 0.3)
        self.glow_ring.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, glow_alpha), width=10))

        return self.elapsed < self.duration

    def cleanup(self):
        """Remove effect from view."""
        self.view.removeItem(self.ring)
        self.view.removeItem(self.glow_ring)


class IntroLaserEffect:
    """Upward laser beam effect."""

    def __init__(self, view, position, color):
        self.view = view
        self.position = position
        self.color = color
        self.duration = 0.3
        self.max_length = 150
        self.elapsed = 0.0

        # Create laser line with glow effect
        self.laser = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=5))
        self.view.addItem(self.laser)

        # Create glow effect
        self.laser_glow = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=12))
        self.laser_glow.setOpacity(0.4)
        self.view.addItem(self.laser_glow)

    def update(self, dt):
        """Update laser animation."""
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Calculate laser length and alpha
        length = self.max_length * progress
        alpha = int(255 * (1 - progress))

        # Draw laser line upward
        x = [self.position[0], self.position[0]]
        y = [self.position[1], self.position[1] + length]

        rgb = tuple(int(self.color[i : i + 2], 16) for i in (1, 3, 5))
        self.laser.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, alpha), width=5))

        # Update glow
        glow_alpha = int(alpha * 0.4)
        self.laser_glow.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, glow_alpha), width=12))

        return self.elapsed < self.duration

    def cleanup(self):
        """Remove effect from view."""
        self.view.removeItem(self.laser)
        self.view.removeItem(self.laser_glow)


class ParticleBurstEffect:
    """Particle burst effect."""

    def __init__(self, view, position, color):
        self.view = view
        self.position = position
        self.color = color
        self.duration = 0.6
        self.elapsed = 0.0
        self.num_particles = 30

        # Generate particles
        angles = np.linspace(0, 2 * np.pi, self.num_particles)
        self.velocities = np.column_stack([np.cos(angles), np.sin(angles)]) * 100

        # Initial positions
        self.positions = np.tile(position, (self.num_particles, 1))

        # Create scatter plot
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        self.particles = pg.ScatterPlotItem(
            self.positions[:, 0],
            self.positions[:, 1],
            size=5,
            brush=pg.mkBrush(*rgb),
        )
        self.view.addItem(self.particles)

    def update(self, dt):
        """Update particle positions."""
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Update positions
        self.positions += self.velocities * dt

        # Update visual
        alpha = int(255 * (1 - progress))
        size = 5 * (1 - progress * 0.5)

        rgb = tuple(int(self.color[i : i + 2], 16) for i in (1, 3, 5))
        self.particles.setData(
            self.positions[:, 0],
            self.positions[:, 1],
            size=size,
            brush=pg.mkBrush(*rgb, alpha),
        )

        return self.elapsed < self.duration

    def cleanup(self):
        """Remove effect from view."""
        self.view.removeItem(self.particles)


class SpiralEffect:
    """Spiral visual effect."""

    def __init__(self, view, position, color):
        self.view = view
        self.position = position
        self.color = color
        self.duration = 1.0
        self.elapsed = 0.0

        # Create spiral curve with gradient effect
        self.spiral = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=5))
        self.view.addItem(self.spiral)

        # Create glow trail
        self.spiral_glow = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=8))
        self.spiral_glow.setOpacity(0.3)
        self.view.addItem(self.spiral_glow)

    def update(self, dt):
        """Update spiral animation."""
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Generate spiral points
        t = np.linspace(0, 4 * np.pi * progress, 100)
        radius = t * 10
        x = self.position[0] + radius * np.cos(t)
        y = self.position[1] + radius * np.sin(t)

        # Update visual with gradient
        alpha = int(255 * (1 - progress))
        rgb = tuple(int(self.color[i : i + 2], 16) for i in (1, 3, 5))
        self.spiral.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, alpha), width=5))

        # Update glow
        glow_alpha = int(alpha * 0.3)
        self.spiral_glow.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, glow_alpha), width=8))

        return self.elapsed < self.duration

    def cleanup(self):
        """Remove effect from view."""
        self.view.removeItem(self.spiral)
        self.view.removeItem(self.spiral_glow)


class MassiveExplosionEffect:
    """Massive explosion with multiple rings."""

    def __init__(self, view, position, color):
        self.view = view
        self.position = position
        self.color = color
        self.duration = 1.5
        self.max_radius = 200
        self.elapsed = 0.0
        self.num_rings = 10

        # Create rings with enhanced visuals
        self.rings = []
        self.glow_rings = []
        for i in range(self.num_rings):
            # Main ring
            ring = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=5))
            self.view.addItem(ring)
            self.rings.append(ring)

            # Glow ring
            glow_ring = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=10))
            glow_ring.setOpacity(0.3)
            self.view.addItem(glow_ring)
            self.glow_rings.append(glow_ring)

    def update(self, dt):
        """Update explosion animation."""
        self.elapsed += dt

        for i, (ring, glow_ring) in enumerate(zip(self.rings, self.glow_rings)):
            # Staggered delay
            delay = i * 0.1
            ring_progress = max(0, min((self.elapsed - delay) / (self.duration - delay), 1.0))

            if ring_progress > 0:
                radius = self.max_radius * ring_progress
                alpha = int(255 * (1 - ring_progress))

                # Generate circle
                angles = np.linspace(0, 2 * np.pi, 50)
                x = self.position[0] + radius * np.cos(angles)
                y = self.position[1] + radius * np.sin(angles)

                rgb = tuple(int(self.color[j : j + 2], 16) for j in (1, 3, 5))
                ring.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, alpha), width=5))

                # Update glow ring
                glow_alpha = int(alpha * 0.3)
                glow_ring.setData(x=x, y=y, pen=pg.mkPen(color=(*rgb, glow_alpha), width=10))

        return self.elapsed < self.duration

    def cleanup(self):
        """Remove effect from view."""
        for ring in self.rings:
            self.view.removeItem(ring)
        for glow_ring in self.glow_rings:
            self.view.removeItem(glow_ring)


class ConnectingBeamEffect:
    """Beam connecting two positions."""

    def __init__(self, view, pos1, pos2):
        self.view = view
        self.pos1 = pos1
        self.pos2 = pos2
        self.duration = 1.0
        self.elapsed = 0.0

        # Create beam with enhanced effect
        self.beam = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 255, 0), width=8))
        self.view.addItem(self.beam)

        # Create glow beam
        self.beam_glow = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 255, 0), width=16))
        self.beam_glow.setOpacity(0.4)
        self.view.addItem(self.beam_glow)

    def update(self, dt):
        """Update beam animation."""
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Pulsing width
        width = 8 + 8 * math.sin(self.elapsed * 10)

        # Fade out
        alpha = int(255 * (1 - progress))

        # Draw beam
        x = [self.pos1[0], self.pos2[0]]
        y = [self.pos1[1], self.pos2[1]]

        self.beam.setData(x=x, y=y, pen=pg.mkPen(color=(255, 255, 0, alpha), width=width))

        # Update glow beam
        glow_alpha = int(alpha * 0.4)
        glow_width = width * 2
        self.beam_glow.setData(
            x=x, y=y, pen=pg.mkPen(color=(255, 255, 0, glow_alpha), width=glow_width)
        )

        return self.elapsed < self.duration

    def cleanup(self):
        """Remove effect from view."""
        self.view.removeItem(self.beam)
        self.view.removeItem(self.beam_glow)


class ScreenFlashEffect:
    """Full screen flash effect."""

    def __init__(self, view):
        self.view = view
        self.duration = 0.5
        self.elapsed = 0.0

        # Create large scatter plot for flash
        self.flash = pg.ScatterPlotItem([0], [0], size=2000, brush=pg.mkBrush(255, 255, 255, 200))
        self.view.addItem(self.flash)

    def update(self, dt):
        """Update flash animation."""
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Fade out
        alpha = int(200 * (1 - progress))
        self.flash.setBrush(pg.mkBrush(255, 255, 255, alpha))

        return self.elapsed < self.duration

    def cleanup(self):
        """Remove effect from view."""
        self.view.removeItem(self.flash)
