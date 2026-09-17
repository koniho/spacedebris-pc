"""Explosion effects."""

import math
import numpy as np
import pyqtgraph as pg
from typing import List, Tuple
from effects.particle_effects import ParticleSystem


class ExplosionRing:
    """Individual explosion ring element."""

    def __init__(
        self,
        center: Tuple[float, float],
        max_radius: float,
        color: Tuple[int, int, int],
        view,
        ring_type: str = "normal",
    ):
        """Initialize explosion ring."""
        self.center = center
        self.max_radius = max_radius
        self.color = color
        self.view = view
        self.ring_type = ring_type

        # Animation properties
        self.duration = 0.5  # 500ms explosion duration
        self.elapsed = 0.0
        self.completed = False

        # Ring properties
        self.current_radius = 0.0
        self.ring_width = max_radius * 0.2  # Ring thickness

        # Visual elements
        self.ring_items = []

        self._create_ring()

    def _create_ring(self):
        """Create the explosion ring visual."""
        # Create multiple ring layers for depth
        ring_configs = [
            {"width_mult": 1.0, "alpha": 150},  # Main ring
            {"width_mult": 0.6, "alpha": 200},  # Inner ring
            {"width_mult": 1.4, "alpha": 80},  # Outer glow
        ]

        for config in ring_configs:
            ring_width = self.ring_width * config["width_mult"]

            # Create circular ring using multiple points
            num_points = 64
            angles = np.linspace(0, 2 * np.pi, num_points + 1)

            ring_item = pg.PlotCurveItem(
                pen=pg.mkPen(color=(*self.color, config["alpha"]), width=max(1, int(ring_width)))
            )
            self.view.addItem(ring_item)
            self.ring_items.append(ring_item)

    def update(self, dt: float) -> bool:
        """Update explosion ring animation. Returns True if still active."""
        if self.completed:
            return False

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Ring expansion with easing
        eased_progress = 1 - (1 - progress) ** 2  # Ease out
        self.current_radius = self.max_radius * eased_progress

        # Fade out as ring expands
        fade_alpha = 1.0 - progress

        # Update ring positions and alpha
        num_points = 64
        angles = np.linspace(0, 2 * np.pi, num_points + 1)
        x_points = self.center[0] + self.current_radius * np.cos(angles)
        y_points = self.center[1] + self.current_radius * np.sin(angles)

        ring_configs = [
            {"width_mult": 1.0, "alpha": 150},
            {"width_mult": 0.6, "alpha": 200},
            {"width_mult": 1.4, "alpha": 80},
        ]

        for i, (ring_item, config) in enumerate(zip(self.ring_items, ring_configs)):
            alpha = int(config["alpha"] * fade_alpha)
            ring_width = max(1, int(self.ring_width * config["width_mult"] * (1 + progress * 0.5)))

            ring_item.setData(x=x_points, y=y_points)
            ring_item.setPen(pg.mkPen(color=(*self.color, alpha), width=ring_width))

        if progress >= 1.0:
            self.completed = True
            return False

        return True

    def cleanup(self):
        """Remove all visual elements."""
        for ring_item in self.ring_items:
            self.view.removeItem(ring_item)
        self.ring_items.clear()


class SincWaveExplosion:
    """Sinc wave-based explosion effect matching the player waveform style."""

    def __init__(
        self,
        center: Tuple[float, float],
        color: Tuple[int, int, int],
        view,
        intensity: float = 1.0,
    ):
        """Initialize sinc wave explosion."""
        self.center = center
        self.color = color
        self.view = view
        self.intensity = intensity

        # Animation properties
        self.duration = 0.6  # 600ms sinc duration
        self.elapsed = 0.0
        self.completed = False

        # Sinc wave properties
        self.max_amplitude = 50 * intensity
        self.wave_width = 200
        self.num_points = 100

        # Visual elements
        self.sinc_lines = []

        self._create_sinc_waves()

    def _create_sinc_waves(self):
        """Create sinc wave visual elements."""
        # Create multiple sinc layers
        wave_configs = [
            {"amplitude_mult": 1.0, "width_mult": 1.0, "alpha": 150},
            {"amplitude_mult": 0.7, "width_mult": 0.8, "alpha": 200},
            {"amplitude_mult": 1.3, "width_mult": 1.2, "alpha": 100},
        ]

        for config in wave_configs:
            sinc_line = pg.PlotCurveItem(
                pen=pg.mkPen(color=(*self.color, config["alpha"]), width=3)
            )
            self.view.addItem(sinc_line)
            self.sinc_lines.append(sinc_line)

    def update(self, dt: float) -> bool:
        """Update sinc wave explosion animation. Returns True if still active."""
        if self.completed:
            return False

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Sinc wave expansion and fade
        expansion = progress * 1.5  # How much the wave has expanded
        fade_alpha = 1.0 - progress

        # Generate sinc wave points
        x_points = np.linspace(
            self.center[0] - self.wave_width / 2,
            self.center[0] + self.wave_width / 2,
            self.num_points,
        )

        wave_configs = [
            {"amplitude_mult": 1.0, "width_mult": 1.0, "alpha": 150},
            {"amplitude_mult": 0.7, "width_mult": 0.8, "alpha": 200},
            {"amplitude_mult": 1.3, "width_mult": 1.2, "alpha": 100},
        ]

        for i, (sinc_line, config) in enumerate(zip(self.sinc_lines, wave_configs)):
            # Calculate sinc function
            amplitude = self.max_amplitude * config["amplitude_mult"] * (1 - progress * 0.5)
            width = 40 * config["width_mult"] * (1 + expansion * 2)  # Wave spreads out

            distance_from_center = (x_points - self.center[0]) / width
            safe_distance = np.where(
                np.abs(distance_from_center) < 1e-10, 1e-10, distance_from_center
            )
            sinc_factor = np.sin(np.pi * safe_distance) / (np.pi * safe_distance)
            sinc_factor = np.where(np.abs(distance_from_center) < 1e-10, 1.0, sinc_factor)

            # Apply time modulation for wave effect
            time_modulation = math.sin(self.elapsed * 10 + i * 2) * 0.3 + 0.7

            y_points = self.center[1] + amplitude * sinc_factor * time_modulation

            # Update line
            alpha = int(config["alpha"] * fade_alpha)
            sinc_line.setData(x=x_points, y=y_points)
            sinc_line.setPen(pg.mkPen(color=(*self.color, alpha), width=3))

        if progress >= 1.0:
            self.completed = True
            return False

        return True

    def cleanup(self):
        """Remove all visual elements."""
        for sinc_line in self.sinc_lines:
            self.view.removeItem(sinc_line)
        self.sinc_lines.clear()


class ExplosionManager:
    """Manages all explosion effects in the game."""

    def __init__(self, view, config):
        """Initialize explosion manager."""
        self.view = view
        self.config = config
        self.active_explosions = []

        # Shared particle system for all particle explosions (optimized)
        self.particle_system = ParticleSystem(view)

    def create_explosion(
        self,
        pos: Tuple[float, float],
        color: Tuple[int, int, int],
        explosion_type: str = "normal",
        intensity: float = 1.0,
    ):
        """Create explosion effect at position.

        Args:
            pos: Explosion position
            color: RGB color tuple (r, g, b) for the explosion
            explosion_type: Type of explosion ('normal', 'enhanced', 'critical')
            intensity: Explosion intensity multiplier
        """
        if not self.config.visual_effects.explosions_enabled:
            return

        color_rgb = color

        # Scale intensity by config
        scaled_intensity = intensity * self.config.visual_effects.explosion_size_multiplier

        # Create different explosion types based on type and config
        explosions_to_create = []

        if explosion_type == "normal":
            if self.config.visual_effects.enable_radial_explosions:
                explosions_to_create.append(("ring", scaled_intensity))
            if self.config.visual_effects.enable_sinc_explosions:
                explosions_to_create.append(("sinc", scaled_intensity * 0.8))

        elif explosion_type == "enhanced":
            if self.config.visual_effects.enable_radial_explosions:
                explosions_to_create.append(("ring", scaled_intensity * 1.3))
            if self.config.visual_effects.enable_ripple_explosions:
                explosions_to_create.append(("particles", scaled_intensity))
            if self.config.visual_effects.enable_sinc_explosions:
                explosions_to_create.append(("sinc", scaled_intensity))

        elif explosion_type == "critical" or explosion_type == "mega":
            # Critical explosions get all effects
            if self.config.visual_effects.enable_radial_explosions:
                explosions_to_create.append(("ring", scaled_intensity * 1.5))
            if self.config.visual_effects.enable_ripple_explosions:
                explosions_to_create.append(("particles", scaled_intensity * 1.2))
            if self.config.visual_effects.enable_sinc_explosions:
                explosions_to_create.append(("sinc", scaled_intensity * 1.1))
        else:
            print(f"Don't know {explosion_type}")

        # Create the explosions
        for effect_type, effect_intensity in explosions_to_create:
            if effect_type == "ring":
                explosion = ExplosionRing(pos, 60 * effect_intensity, color_rgb, self.view)
                self.active_explosions.append(explosion)
            elif effect_type == "particles":
                # Emit into shared particle system instead of creating separate object
                self.particle_system.emit_explosion(pos[0], pos[1], color_rgb, effect_intensity)
            elif effect_type == "sinc":
                explosion = SincWaveExplosion(pos, color_rgb, self.view, effect_intensity)
                self.active_explosions.append(explosion)

    def create_multi_explosion(
        self,
        positions: List[Tuple[float, float]],
        color: Tuple[int, int, int],
        intensity: float = 1.0,
    ):
        """Create multiple synchronized explosions.

        Args:
            positions: List of explosion positions
            color: RGB color tuple (r, g, b) for the explosions
            intensity: Base intensity for all explosions
        """
        for i, pos in enumerate(positions):
            # Stagger intensity slightly for visual variety
            stagger_intensity = intensity * (0.8 + 0.4 * (i / max(len(positions) - 1, 1)))
            explosion_type = "enhanced" if len(positions) > 1 else "normal"
            self.create_explosion(pos, color, explosion_type, stagger_intensity)

    def update(self, dt: float):
        """Update all active explosions."""
        # Update particle system
        self.particle_system.update(dt)

        # Update other explosion effects
        completed_explosions = []

        for explosion in self.active_explosions:
            if not explosion.update(dt):
                completed_explosions.append(explosion)

        # Clean up completed explosions
        for explosion in completed_explosions:
            explosion.cleanup()
            self.active_explosions.remove(explosion)

    def has_active_animations(self) -> bool:
        """Check if there are any active explosion animations."""
        return len(self.active_explosions) > 0 or len(self.particle_system.particles) > 0

    def cleanup(self):
        """Clean up all explosions."""
        self.particle_system.cleanup()
        for explosion in self.active_explosions:
            explosion.cleanup()
        self.active_explosions.clear()
