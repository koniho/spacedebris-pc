"""Engagement crosshair indicator."""

import math
import time
import numpy as np
import pyqtgraph as pg


class EngagementCrosshair:
    """Animated crosshair that shows which enemy is engaged."""

    def __init__(self, view):
        """Initialize crosshair indicator."""
        self.view = view

        # Animation properties
        self.animation_duration = 0.2  # 200ms
        self.animation_start_time = 0
        self.animating = False

        # Position tracking
        self.current_pos = (0, -250)  # Resting position near bottom
        self.target_pos = (0, -250)  # Where we want to move to
        self.start_pos = (0, -250)  # Animation start position
        self.resting_pos = (0, -250)  # Fixed resting position

        # Visual elements
        self.crosshair_lines = []
        self.center_dot = None
        self.glow_lines = []
        self.engagement_outline_lines = []  # Extra thick outline when engaged
        self.engagement_glow_lines = []  # Extra wide glow when engaged
        self.engaged = False  # Track engagement state

        # Size properties (can be modified by set_enemy_size)
        self.line_length = 25
        self.gap = 8

        self._create_crosshair()

    def _create_crosshair(self):
        """Create the crosshair visual elements."""
        # Use instance variables for dimensions
        line_length = self.line_length
        gap = self.gap
        line_width = 3
        glow_width = 6

        # Colors
        main_color = (255, 255, 0, 200)  # Yellow
        glow_color = (255, 255, 0, 100)  # Semi-transparent yellow
        engagement_outline_color = (255, 255, 255, 255)  # White outline when engaged
        engagement_glow_color = (255, 255, 0, 60)  # Strong yellow glow when engaged

        # Create crosshair lines (4 lines extending from center)
        line_positions = [
            # Horizontal lines
            ((-line_length, -gap), (-gap, 0)),  # Left
            ((gap, 0), (line_length, gap)),  # Right
            # Vertical lines
            ((-gap, -line_length), (0, -gap)),  # Top
            ((0, gap), (gap, line_length)),  # Bottom
        ]

        for start, end in line_positions:
            # Engagement glow (extra wide, initially hidden)
            engagement_glow_line = pg.PlotCurveItem(
                x=[start[0], end[0]],
                y=[start[1], end[1]],
                pen=pg.mkPen(color=engagement_glow_color, width=12),
            )
            engagement_glow_line.setVisible(False)  # Hidden by default
            self.view.addItem(engagement_glow_line)
            self.engagement_glow_lines.append(engagement_glow_line)

            # Engagement outline (thick white, initially hidden)
            engagement_outline_line = pg.PlotCurveItem(
                x=[start[0], end[0]],
                y=[start[1], end[1]],
                pen=pg.mkPen(color=engagement_outline_color, width=8),
            )
            engagement_outline_line.setVisible(False)  # Hidden by default
            self.view.addItem(engagement_outline_line)
            self.engagement_outline_lines.append(engagement_outline_line)

            # Glow line (thicker, semi-transparent)
            glow_line = pg.PlotCurveItem(
                x=[start[0], end[0]],
                y=[start[1], end[1]],
                pen=pg.mkPen(color=glow_color, width=glow_width),
            )
            self.view.addItem(glow_line)
            self.glow_lines.append(glow_line)

            # Main line (thinner, opaque)
            main_line = pg.PlotCurveItem(
                x=[start[0], end[0]],
                y=[start[1], end[1]],
                pen=pg.mkPen(color=main_color, width=line_width),
            )
            self.view.addItem(main_line)
            self.crosshair_lines.append(main_line)

        # Center dot
        self.center_dot = pg.ScatterPlotItem(
            [0],
            [0],
            size=8,
            brush=pg.mkBrush(*main_color),
            pen=pg.mkPen(color=main_color, width=2),
        )
        self.view.addItem(self.center_dot)

        # Initial positioning
        self._update_crosshair_position(self.current_pos)

    def set_target(self, target_pos):
        """Animate crosshair to target position."""
        if target_pos != self.target_pos:
            self.start_pos = self.current_pos
            self.target_pos = target_pos
            self.animation_start_time = time.time()
            self.animating = True
            # Show engagement effects when moving to target
            self._set_engagement_effects_visible(True)

    def set_resting(self):
        """Animate crosshair back to resting position."""
        # Hide engagement effects when returning to rest
        self._set_engagement_effects_visible(False)
        # Reset size properties to default values
        self._reset_size_properties()
        self.set_target(self.resting_pos)

    def update(self, dt: float):
        """Update crosshair animation."""
        if not self.animating:
            return

        elapsed = time.time() - self.animation_start_time
        progress = min(elapsed / self.animation_duration, 1.0)

        # Smooth easing function (ease-out)
        progress = 1 - (1 - progress) ** 3

        # Interpolate position
        start_x, start_y = self.start_pos
        target_x, target_y = self.target_pos

        current_x = start_x + (target_x - start_x) * progress
        current_y = start_y + (target_y - start_y) * progress

        self.current_pos = (current_x, current_y)
        self._update_crosshair_position(self.current_pos)

        # Add subtle pulse when engaged (not at resting position)
        if self.target_pos != self.resting_pos:
            pulse = 1.0 + 0.1 * math.sin(time.time() * 8)
            self._update_crosshair_scale(pulse)
        else:
            self._update_crosshair_scale(1.0)

        # End animation
        if progress >= 1.0:
            self.animating = False

    def _update_crosshair_position(self, pos):
        """Update the position of all crosshair elements."""
        x, y = pos

        # Use dynamic dimensions if available, otherwise use defaults
        line_length = getattr(self, "line_length", 25)
        gap = getattr(self, "gap", 8)

        line_positions = [
            # Horizontal lines
            ([x - line_length, x - gap], [y, y]),  # Left
            ([x + gap, x + line_length], [y, y]),  # Right
            # Vertical lines
            ([x, x], [y - line_length, y - gap]),  # Top
            ([x, x], [y + gap, y + line_length]),  # Bottom
        ]

        for i, (line, glow_line, outline_line, engagement_glow_line) in enumerate(
            zip(
                self.crosshair_lines,
                self.glow_lines,
                self.engagement_outline_lines,
                self.engagement_glow_lines,
            )
        ):
            x_coords, y_coords = line_positions[i]
            line.setData(x=x_coords, y=y_coords)
            glow_line.setData(x=x_coords, y=y_coords)
            outline_line.setData(x=x_coords, y=y_coords)
            engagement_glow_line.setData(x=x_coords, y=y_coords)

        # Update center dot
        self.center_dot.setData([x], [y])

    def _update_crosshair_scale(self, scale):
        """Update the scale of crosshair elements for pulse effect."""
        x, y = self.current_pos

        # Use dynamic dimensions if available, otherwise use defaults
        base_line_length = getattr(self, "line_length", 25)
        base_gap = getattr(self, "gap", 8)
        line_length = base_line_length * scale
        gap = base_gap * scale

        line_positions = [
            # Horizontal lines
            ([x - line_length, x - gap], [y, y]),  # Left
            ([x + gap, x + line_length], [y, y]),  # Right
            # Vertical lines
            ([x, x], [y - line_length, y - gap]),  # Top
            ([x, x], [y + gap, y + line_length]),  # Bottom
        ]

        for i, (line, glow_line, outline_line, engagement_glow_line) in enumerate(
            zip(
                self.crosshair_lines,
                self.glow_lines,
                self.engagement_outline_lines,
                self.engagement_glow_lines,
            )
        ):
            x_coords, y_coords = line_positions[i]
            line.setData(x=x_coords, y=y_coords)
            glow_line.setData(x=x_coords, y=y_coords)
            outline_line.setData(x=x_coords, y=y_coords)
            engagement_glow_line.setData(x=x_coords, y=y_coords)

        # Update center dot size
        self.center_dot.setSize(8 * scale)

    def _set_engagement_effects_visible(self, visible: bool):
        """Show or hide engagement effects (outline and glow)."""
        for outline_line in self.engagement_outline_lines:
            outline_line.setVisible(visible)
        for glow_line in self.engagement_glow_lines:
            glow_line.setVisible(visible)
        self.engaged = visible

    def _reset_size_properties(self):
        """Reset crosshair size properties to default values."""
        # Reset to default dimensions
        self.line_length = 25
        self.gap = 8

        # Reset engagement effect widths to default
        default_outline_width = 8
        default_glow_width = 12
        engagement_outline_color = (255, 255, 255, 255)
        engagement_glow_color = (255, 255, 0, 60)

        for outline_line in self.engagement_outline_lines:
            outline_line.setPen(
                pg.mkPen(color=engagement_outline_color, width=default_outline_width)
            )
        for glow_line in self.engagement_glow_lines:
            glow_line.setPen(pg.mkPen(color=engagement_glow_color, width=default_glow_width))

        # Force update position with default dimensions
        self._update_crosshair_position(self.current_pos)

    def set_enemy_size(self, enemy_width: float):
        """Adapt crosshair size to engaged enemy width."""
        # Scale crosshair based on enemy size
        base_size = 25
        size_multiplier = max(0.8, min(2.0, enemy_width / 150))  # Scale between 80% and 200%

        # Update crosshair dimensions based on enemy size
        self.line_length = int(base_size * size_multiplier)
        self.gap = max(6, int(8 * size_multiplier))

        # Update engagement outline thickness based on size
        outline_width = max(6, int(8 * size_multiplier))
        glow_width = max(10, int(12 * size_multiplier))

        # Update pen widths for engagement effects
        engagement_outline_color = (255, 255, 255, 255)
        engagement_glow_color = (255, 255, 0, 60)

        for outline_line in self.engagement_outline_lines:
            outline_line.setPen(pg.mkPen(color=engagement_outline_color, width=outline_width))
        for glow_line in self.engagement_glow_lines:
            glow_line.setPen(pg.mkPen(color=engagement_glow_color, width=glow_width))

        # Force update position with new dimensions
        self._update_crosshair_position(self.current_pos)

    def cleanup(self):
        """Remove all visual elements."""
        for line in self.crosshair_lines:
            self.view.removeItem(line)
        for glow_line in self.glow_lines:
            self.view.removeItem(glow_line)
        for outline_line in self.engagement_outline_lines:
            self.view.removeItem(outline_line)
        for engagement_glow_line in self.engagement_glow_lines:
            self.view.removeItem(engagement_glow_line)
        if self.center_dot:
            self.view.removeItem(self.center_dot)

        self.crosshair_lines.clear()
        self.glow_lines.clear()
        self.engagement_outline_lines.clear()
        self.engagement_glow_lines.clear()
        self.center_dot = None
