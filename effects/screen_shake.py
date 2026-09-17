"""Screen shake effects."""

import math
import random_manager
import time
from typing import Tuple, Optional


class ScreenShakeManager:
    """Manages screen shake effects with customizable intensity and patterns."""

    def __init__(self, view, config):
        """Initialize screen shake manager."""
        self.view = view
        self.config = config

        # Shake state
        self.active = False
        self.duration = 0.0
        self.elapsed = 0.0
        self.base_magnitude = 0.0
        self.shake_pattern = "normal"

        # Original view position (for restoration)
        self.original_center = (0, 0)  # Will be set when first shake occurs
        self.current_offset = (0, 0)

        # Shake patterns
        self.patterns = {
            "normal": self._normal_shake,
            "impact": self._impact_shake,
            "explosion": self._explosion_shake,
            "continuous": self._continuous_shake,
        }

    def trigger_shake(
        self,
        magnitude: float,
        duration: float,
        pattern: str = "normal",
        intensity_curve: str = "ease_out",
    ):
        """Trigger a screen shake effect.

        Args:
            magnitude: Shake intensity (pixels)
            duration: Shake duration (seconds)
            pattern: Shake pattern type ('normal', 'impact', 'explosion', 'continuous')
            intensity_curve: How shake intensity changes over time ('linear', 'ease_out', 'ease_in')
        """
        if not self.config.visual_effects.screen_shake_enabled:
            return

        # Apply config multipliers
        scaled_magnitude = magnitude * self.config.visual_effects.shake_intensity_multiplier
        scaled_duration = duration * self.config.visual_effects.shake_duration_base

        # If already shaking, combine effects
        if self.active:
            # Additive stacking for multiple shakes
            self.base_magnitude = max(self.base_magnitude, scaled_magnitude)
            self.duration = max(self.duration - self.elapsed, scaled_duration) + self.elapsed
        else:
            # Start new shake
            self.active = True
            self.elapsed = 0.0
            self.duration = scaled_duration
            self.base_magnitude = scaled_magnitude
            self.shake_pattern = pattern
            self.intensity_curve = intensity_curve

            # Store original view center if not already stored
            if hasattr(self.view, "getViewBox"):
                view_box = self.view.getViewBox()
                if view_box:
                    self.original_center = view_box.viewRect().center()
                    self.original_center = (
                        self.original_center.x(),
                        self.original_center.y(),
                    )

    def update(self, dt: float):
        """Update screen shake animation."""
        if not self.active:
            return

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        if progress >= 1.0:
            # Shake complete - restore original position
            self._restore_position()
            self.active = False
            return

        # Calculate current shake intensity based on curve
        if self.intensity_curve == "ease_out":
            intensity = self.base_magnitude * (1.0 - progress**2)
        elif self.intensity_curve == "ease_in":
            intensity = self.base_magnitude * (progress**2)
        elif self.intensity_curve == "ease_in_out":
            if progress < 0.5:
                intensity = self.base_magnitude * (2 * progress**2)
            else:
                intensity = self.base_magnitude * (1 - 2 * (1 - progress) ** 2)
        else:  # linear
            intensity = self.base_magnitude * (1.0 - progress)

        # Apply shake pattern
        if self.shake_pattern in self.patterns:
            offset_x, offset_y = self.patterns[self.shake_pattern](intensity, progress)
        else:
            offset_x, offset_y = self._normal_shake(intensity, progress)

        self.current_offset = (offset_x, offset_y)

        # Apply shake to view
        self._apply_shake_offset(offset_x, offset_y)

    def _normal_shake(self, intensity: float, progress: float) -> Tuple[float, float]:
        """Normal random shake pattern."""
        offset_x = random_manager.uniform(-intensity, intensity)
        offset_y = random_manager.uniform(-intensity, intensity)
        return (offset_x, offset_y)

    def _impact_shake(self, intensity: float, progress: float) -> Tuple[float, float]:
        """Sharp impact shake with quick decay."""
        # Stronger horizontal shake, weaker vertical
        offset_x = random_manager.uniform(-intensity * 1.5, intensity * 1.5)
        offset_y = random_manager.uniform(-intensity * 0.7, intensity * 0.7)

        # Add high-frequency jitter early in the shake
        if progress < 0.3:
            jitter_mult = (0.3 - progress) / 0.3  # More jitter early
            offset_x += random_manager.uniform(-intensity * 0.5, intensity * 0.5) * jitter_mult
            offset_y += random_manager.uniform(-intensity * 0.3, intensity * 0.3) * jitter_mult

        return (offset_x, offset_y)

    def _explosion_shake(self, intensity: float, progress: float) -> Tuple[float, float]:
        """Explosion shake with radial pattern."""
        # Create a radial shake pattern
        angle = random_manager.uniform(0, 2 * math.pi)
        radius = intensity * (0.8 + 0.4 * random_manager.random())  # Some variation

        offset_x = radius * math.cos(angle)
        offset_y = radius * math.sin(angle)

        # Add some chaos
        offset_x += random_manager.uniform(-intensity * 0.3, intensity * 0.3)
        offset_y += random_manager.uniform(-intensity * 0.3, intensity * 0.3)

        return (offset_x, offset_y)

    def _continuous_shake(self, intensity: float, progress: float) -> Tuple[float, float]:
        """Continuous smooth shake (for ongoing effects)."""
        # Sine wave based shake for smoothness
        time_factor = self.elapsed * 15  # Frequency
        offset_x = intensity * math.sin(time_factor) * 0.8
        offset_y = intensity * math.sin(time_factor * 1.3 + 1) * 0.6  # Different frequency

        # Add small random component
        offset_x += random_manager.uniform(-intensity * 0.2, intensity * 0.2)
        offset_y += random_manager.uniform(-intensity * 0.2, intensity * 0.2)

        return (offset_x, offset_y)

    def _apply_shake_offset(self, offset_x: float, offset_y: float):
        """Apply shake offset to the view."""
        if hasattr(self.view, "getViewBox"):
            view_box = self.view.getViewBox()
            if view_box:
                # Calculate new center position
                new_center_x = self.original_center[0] + offset_x
                new_center_y = self.original_center[1] + offset_y

                # Get current view rect to preserve zoom
                current_rect = view_box.viewRect()
                width = current_rect.width()
                height = current_rect.height()

                # Set new view rect centered at shaken position
                view_box.setRange(
                    xRange=[new_center_x - width / 2, new_center_x + width / 2],
                    yRange=[new_center_y - height / 2, new_center_y + height / 2],
                    padding=0,
                )

    def _restore_position(self):
        """Restore view to original position."""
        if hasattr(self.view, "getViewBox"):
            view_box = self.view.getViewBox()
            if view_box:
                # Get current view rect to preserve zoom
                current_rect = view_box.viewRect()
                width = current_rect.width()
                height = current_rect.height()

                # Restore original center
                view_box.setRange(
                    xRange=[
                        self.original_center[0] - width / 2,
                        self.original_center[0] + width / 2,
                    ],
                    yRange=[
                        self.original_center[1] - height / 2,
                        self.original_center[1] + height / 2,
                    ],
                    padding=0,
                )

        self.current_offset = (0, 0)

    def stop_shake(self):
        """Immediately stop any active shake and restore position."""
        if self.active:
            self._restore_position()
            self.active = False
            self.elapsed = 0.0

    def is_shaking(self) -> bool:
        """Check if screen shake is currently active."""
        return self.active

    def get_current_offset(self) -> Tuple[float, float]:
        """Get current shake offset for debugging/external use."""
        return self.current_offset

    # Convenient preset shake methods
    def small_shake(self):
        """Small shake for minor impacts."""
        self.trigger_shake(magnitude=3.0, duration=0.15, pattern="normal")

    def medium_shake(self):
        """Medium shake for normal impacts."""
        self.trigger_shake(magnitude=6.0, duration=0.25, pattern="impact")

    def large_shake(self):
        """Large shake for explosions."""
        self.trigger_shake(magnitude=10.0, duration=0.4, pattern="explosion")

    def enemy_hit_shake(self):
        """Shake when enemy hits player."""
        self.trigger_shake(
            magnitude=8.0, duration=0.3, pattern="impact", intensity_curve="ease_out"
        )

    def enemy_destroyed_shake(self, intensity_multiplier: float = 1.0):
        """Shake when enemy is destroyed."""
        self.trigger_shake(
            magnitude=4.0 * intensity_multiplier,
            duration=0.2,
            pattern="explosion",
            intensity_curve="ease_out",
        )
