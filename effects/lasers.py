"""Laser beam effects."""

import math
import time
from typing import List, Tuple
import pyqtgraph as pg
from PyQt5.QtWidgets import QGraphicsEllipseItem
from config import BUTTON_COLORS


class LaserBeam:
    """Individual laser beam with animation."""

    def __init__(
        self,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        button: str,
        view,
        beam_type: str = "normal",
        get_waveform_y_callback=None,
    ):
        """Initialize laser beam.

        Args:
            start_pos: Starting position (bottom of screen)
            end_pos: Target position (enemy letter)
            button: Button that triggered this laser
            view: PyQtGraph view to add items to
            beam_type: Type of beam effect ('normal', 'enhanced', 'critical')
            get_waveform_y_callback: Callback function that returns Y position at given X
        """
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.button = button
        self.view = view
        self.beam_type = beam_type
        self.get_waveform_y = get_waveform_y_callback  # Callback: lambda x: waveform.get_y_at_x(x)

        # Animation properties
        self.duration = 0.2  # 200ms laser beam duration
        self.elapsed = 0.0
        self.completed = False

        # Visual elements
        self.beam_lines = []
        self.glow_lines = []
        self.core_line = None
        self.impact_effect = None
        self.impact_circle = None
        self.impact_circle_center = None  # More opaque center
        self.impact_circle_outline = None

        # Get button color (gray for blocked beams)
        if beam_type == "blocked":
            self.color_hex = "#888888"
            self.color_rgb = (136, 136, 136)
        else:
            self.color_hex = BUTTON_COLORS.get(button, "#FFFFFF")
            self.color_rgb = tuple(int(self.color_hex[i : i + 2], 16) for i in (1, 3, 5))

        self._create_beam()

    def _create_beam(self):
        """Create the laser beam visual elements."""
        # Create multiple beam layers for depth
        beam_configs = [
            {"width": 8, "alpha": 60, "blur": True},  # Outer glow
            {"width": 4, "alpha": 120, "blur": False},  # Middle beam
            {"width": 2, "alpha": 200, "blur": False},  # Core beam
            {"width": 1, "alpha": 255, "blur": False},  # Center line
        ]

        for config in beam_configs:
            beam_line = pg.PlotCurveItem(
                x=[self.start_pos[0], self.end_pos[0]],
                y=[self.start_pos[1], self.end_pos[1]],
                pen=pg.mkPen(color=(*self.color_rgb, config["alpha"]), width=config["width"]),
            )
            self.view.addItem(beam_line)
            self.beam_lines.append(beam_line)

        # Enhanced beams get extra effects
        if self.beam_type in ["enhanced", "critical"]:
            self._add_enhanced_effects()

        # Add impact circle at the laser origin (player waveform intersection)
        self._create_impact_circle()

    def _add_enhanced_effects(self):
        """Add enhanced visual effects for special beam types."""
        # Add pulsing glow for enhanced/critical beams
        for i in range(2):  # Extra glow layers
            glow_line = pg.PlotCurveItem(
                x=[self.start_pos[0], self.end_pos[0]],
                y=[self.start_pos[1], self.end_pos[1]],
                pen=pg.mkPen(color=(*self.color_rgb, 30 + i * 10), width=12 + i * 4),
            )
            self.view.addItem(glow_line)
            self.glow_lines.append(glow_line)

    def _create_impact_circle(self):
        """Create glowing circle at laser origin (player waveform intersection)."""
        # Use bluish color for waveform (matching player waveform color)
        waveform_color = (100, 150, 255)  # Bluish color
        radius = 30
        center_radius = 12  # Smaller, more opaque center

        # Create outer circle with low opacity
        self.impact_circle = QGraphicsEllipseItem(
            -radius,
            -radius,  # Top-left corner relative to center
            radius * 2,
            radius * 2,  # Width and height
        )

        # Set position to laser start
        self.impact_circle.setPos(self.start_pos[0], self.start_pos[1])

        # Set fill (brush) and outline (pen)
        self.impact_circle.setBrush(pg.mkBrush(*waveform_color, 30))  # Low opacity fill
        self.impact_circle.setPen(
            pg.mkPen((*waveform_color, 80), width=10)
        )  # Low opacity thick outline

        # Add to view
        self.view.addItem(self.impact_circle)

        # Create more opaque center circle
        self.impact_circle_center = QGraphicsEllipseItem(
            -center_radius,
            -center_radius,
            center_radius * 2,
            center_radius * 2,
        )

        # Set position to same as outer circle
        self.impact_circle_center.setPos(self.start_pos[0], self.start_pos[1])

        # More opaque center
        self.impact_circle_center.setBrush(pg.mkBrush(*waveform_color, 80))  # Higher opacity
        self.impact_circle_center.setPen(pg.mkPen(None))  # No outline for center

        # Add center circle
        self.view.addItem(self.impact_circle_center)

        # We don't need a separate outline item anymore since QGraphicsEllipseItem handles both
        self.impact_circle_outline = None

    def update(self, dt: float) -> bool:
        """Update laser beam animation. Returns True if still active."""
        if self.completed:
            return False

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Update impact circle Y position using callback
        if self.get_waveform_y and self.impact_circle:
            # Get current waveform Y at the laser's X position
            current_y = self.get_waveform_y(self.start_pos[0])
            # Update circle positions
            self.impact_circle.setPos(self.start_pos[0], current_y)
            if self.impact_circle_center:
                self.impact_circle_center.setPos(self.start_pos[0], current_y)

        # Beam fade-out animation
        if progress > 0.6:  # Start fading after 60% of duration
            fade_progress = (progress - 0.6) / 0.4
            fade_alpha = 1.0 - fade_progress

            # Update all beam line alphas
            for i, beam_line in enumerate(self.beam_lines):
                base_alpha = [60, 120, 200, 255][i]
                new_alpha = int(base_alpha * fade_alpha)
                beam_line.setPen(
                    pg.mkPen(
                        color=(*self.color_rgb, new_alpha),
                        width=beam_line.opts["pen"].width(),
                    )
                )

            # Update glow lines for enhanced beams
            for i, glow_line in enumerate(self.glow_lines):
                base_alpha = 30 + i * 10
                new_alpha = int(base_alpha * fade_alpha)
                glow_line.setPen(
                    pg.mkPen(
                        color=(*self.color_rgb, new_alpha),
                        width=glow_line.opts["pen"].width(),
                    )
                )

            # Update impact circle opacity during fade
            if self.impact_circle:
                waveform_color = (100, 150, 255)
                circle_alpha = int(30 * fade_alpha)
                outline_alpha = int(80 * fade_alpha)
                center_alpha = int(80 * fade_alpha)

                self.impact_circle.setBrush(pg.mkBrush(*waveform_color, circle_alpha))
                self.impact_circle.setPen(
                    pg.mkPen(color=(*waveform_color, outline_alpha), width=10)
                )

                if self.impact_circle_center:
                    self.impact_circle_center.setBrush(pg.mkBrush(*waveform_color, center_alpha))

        # Enhanced beam pulse effect
        if self.beam_type in ["enhanced", "critical"] and progress < 0.6:
            pulse = 1.0 + 0.3 * math.sin(time.time() * 20)  # Fast pulse
            for glow_line in self.glow_lines:
                original_width = 12 if glow_line == self.glow_lines[0] else 16
                glow_line.setPen(
                    pg.mkPen(
                        color=glow_line.opts["pen"].color(),
                        width=int(original_width * pulse),
                    )
                )

        if progress >= 1.0:
            self.completed = True
            return False

        return True

    def cleanup(self):
        """Remove all visual elements."""
        for beam_line in self.beam_lines:
            self.view.removeItem(beam_line)
        for glow_line in self.glow_lines:
            self.view.removeItem(glow_line)

        if self.impact_circle:
            self.view.removeItem(self.impact_circle)
        if self.impact_circle_center:
            self.view.removeItem(self.impact_circle_center)

        self.beam_lines.clear()
        self.glow_lines.clear()


class LaserManager:
    """Manages all laser beam effects in the game."""

    def __init__(self, view, config, sound_manager=None, get_waveform_y_callback=None):
        """Initialize laser manager."""
        self.view = view
        self.config = config
        self.sound_manager = sound_manager
        self.get_waveform_y = get_waveform_y_callback  # Callback to get waveform Y at X
        self.active_beams: List[LaserBeam] = []

        # Laser origin point (bottom center of screen)
        self.laser_origin = (0, -280)  # Slightly above bottom edge

    def create_laser(
        self,
        target_pos: Tuple[float, float],
        button: str,
        beam_type: str = "normal",
        waveform_y: float = None,
        shield_radius: float = None,
    ):
        """Create a new laser beam effect.

        Args:
            target_pos: Target position (enemy letter location)
            button: Button that was pressed
            beam_type: Type of beam ('normal', 'enhanced', 'critical', 'blocked')
            waveform_y: Y position of player waveform (if None, use default origin)
            shield_radius: For 'blocked' type, the shield radius to stop at
        """
        if not self.config.visual_effects.lasers_enabled:
            return

        # Calculate laser start position: same X as target, Y from waveform
        if waveform_y is not None:
            laser_start = (target_pos[0], waveform_y)
        else:
            laser_start = self.laser_origin

        # For blocked lasers, adjust target to stop at shield
        actual_target = target_pos
        if beam_type == "blocked" and shield_radius:
            # Stop the laser at the shield radius from the enemy center
            direction_y = target_pos[1] - laser_start[1]
            if direction_y != 0:
                # Calculate point where laser hits shield
                shield_stop_y = target_pos[1] - shield_radius
                actual_target = (target_pos[0], shield_stop_y)

        beam = LaserBeam(
            laser_start, actual_target, button, self.view, beam_type, self.get_waveform_y
        )
        self.active_beams.append(beam)

    def create_crosshair_laser(
        self,
        crosshair_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        button: str,
    ):
        """Create laser beam from crosshair to target.

        Args:
            crosshair_pos: Current crosshair position
            target_pos: Target enemy letter position
            button: Button that was pressed
        """
        if not self.config.visual_effects.lasers_enabled:
            return

        beam = LaserBeam(
            crosshair_pos,
            target_pos,
            button,
            self.view,
            "enhanced",  # Crosshair lasers are enhanced
            self.get_waveform_y,
        )
        self.active_beams.append(beam)

    def create_multi_laser(
        self,
        target_positions: List[Tuple[float, float]],
        button: str,
        waveform_y: float = None,
    ):
        """Create multiple laser beams for rapid-fire effects.

        Args:
            target_positions: List of target positions
            button: Button that was pressed
            waveform_y: Y position of player waveform (if None, use default origin)
        """
        if not self.config.visual_effects.lasers_enabled:
            return

        for target_pos in target_positions:
            # Stagger the laser creation slightly
            beam_type = "critical" if len(target_positions) > 3 else "enhanced"

            # Calculate laser start position: same X as target, Y from waveform
            if waveform_y is not None:
                laser_start = (target_pos[0], waveform_y)
            else:
                laser_start = self.laser_origin

            beam = LaserBeam(
                laser_start,
                target_pos,
                button,
                self.view,
                beam_type,
                self.get_waveform_y,
            )
            self.active_beams.append(beam)

    def update(self, dt: float):
        """Update all active laser beams."""
        completed_beams = []

        for beam in self.active_beams:
            if not beam.update(dt):
                completed_beams.append(beam)

        # Clean up completed beams
        for beam in completed_beams:
            beam.cleanup()
            self.active_beams.remove(beam)

    def has_active_animations(self) -> bool:
        """Check if there are any active laser beam animations."""
        return len(self.active_beams) > 0

    def cleanup(self):
        """Clean up all laser beams."""
        for beam in self.active_beams:
            beam.cleanup()
        self.active_beams.clear()

    def set_laser_origin(self, pos: Tuple[float, float]):
        """Update the laser origin point."""
        self.laser_origin = pos

    def set_waveform_callback(self, callback):
        """Update the waveform Y position callback."""
        self.get_waveform_y = callback
