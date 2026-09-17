"""
Sinusoid Boss - A boss that uses two strings of letters moving on closed oval paths.
Letters follow the path like a train, with upper and lower strings traveling opposite directions.
"""

import math
import random
import time
from typing import Tuple, List

import numpy as np
import pyqtgraph as pg

from enemies.base_boss import BaseBoss
from enemies.rapid_hit_enemy import RapidHitEnemy
from effects.boss_death_animation import BossDeathAnimation
from config import ALL_BUTTONS, BUTTON_COLORS, get_button_color, get_button_label, DifficultyLevel
from font_manager import font_manager


class BossLetter:
    """A single letter that is part of the SinusoidBoss."""

    def __init__(self, letter: str, pos: Tuple[float, float], view):
        self.letter = letter
        self.pos = pos
        self.view = view
        self.alive = True
        self.path_position = 0.0  # Position along the closed path (0 to 1)

        # Visuals - create at the actual position
        color = BUTTON_COLORS.get(self.letter, "#FFFFFF")
        self.text_item = pg.TextItem(
            text=get_button_label(self.letter), color=color, anchor=(0.5, 0.5)
        )
        self.text_item.setFont(font_manager.get_enemy_letter_font(24, bold=True))
        self.text_item.setPos(pos[0], pos[1])
        self.view.addItem(self.text_item)

        self.background = self._create_letter_hexagon(pos[0], pos[1], self.letter)

    def _create_letter_hexagon(self, x, y, letter):
        """Create hexagon background for letter."""
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        size = 18
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        hexagon_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*rgb, 100),
            fillLevel="enclosed",
        )
        self.view.addItem(hexagon_fill)

        hexagon_outline = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=pg.mkPen(color=(*rgb, 255), width=4), brush=None
        )
        self.view.addItem(hexagon_outline)

        hexagon_outline._fill = hexagon_fill
        return hexagon_outline

    def update_pos(self, new_pos: Tuple[float, float]):
        """Update the position of the letter."""
        self.pos = new_pos
        # Check if text_item still exists (might be None during cleanup)
        if self.text_item:
            self.text_item.setPos(new_pos[0], new_pos[1])
        if self.background:
            self._move_hexagon(self.background, new_pos[0], new_pos[1])

    def _move_hexagon(self, hexagon, x, y):
        """Move hexagon to new position."""
        size = 18
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        pen = hexagon.opts.get("pen", pg.mkPen(color=(255, 255, 255), width=4))
        hexagon.setData(x=x_points, y=y_points, pen=pen)

        brush = hexagon._fill.opts.get("brush", pg.mkBrush(255, 255, 255, 100))
        hexagon._fill.setData(x=x_points, y=y_points, brush=brush)

    def cleanup(self):
        """Remove visual items from the view."""
        if self.text_item and self.text_item.scene():
            self.view.removeItem(self.text_item)
        self.text_item = None
        if self.background and self.background.scene():
            self.view.removeItem(self.background)
            if self.background._fill and self.background._fill.scene():
                self.view.removeItem(self.background._fill)
        self.background = None

    def destroy(self):
        """Mark the letter as destroyed."""
        self.alive = False
        self.cleanup()

    def revive(self):
        """Revive a destroyed letter, recreating its visuals."""
        if self.alive:
            return  # Already alive

        self.alive = True

        # Recreate visuals at current position
        color = BUTTON_COLORS.get(self.letter, "#FFFFFF")
        self.text_item = pg.TextItem(
            text=get_button_label(self.letter), color=color, anchor=(0.5, 0.5)
        )
        self.text_item.setFont(font_manager.get_enemy_letter_font(24, bold=True))
        self.text_item.setPos(self.pos[0], self.pos[1])
        self.view.addItem(self.text_item)

        self.background = self._create_letter_hexagon(self.pos[0], self.pos[1], self.letter)


class DestroyedOrbPair:
    """Represents a pair of glowing orbs left behind when letters are destroyed."""

    # String colors matching the path curves
    STRING1_COLOR = (100, 200, 255)  # Cyan/light blue for upper string
    STRING2_COLOR = (255, 100, 200)  # Pink/magenta for lower string

    def __init__(self, pos1: Tuple[float, float], pos2: Tuple[float, float], view):
        self.pos1 = pos1
        self.pos2 = pos2
        self.view = view
        self.time = 0.0
        self.color1 = self.STRING1_COLOR
        self.color2 = self.STRING2_COLOR

        # Regeneration tracking
        self.regen_timer = 0.0
        self.regen_duration = 5.0  # Seconds before regenerating
        self.regenerating = False  # True when regeneration animation is playing
        self.regen_progress = 0.0  # 0 to 1 for regeneration animation

        # Flash effect for unmatched input
        self.flash_timer = 0.0
        self.flash_duration = 0.15

        # Create glowing orbs with string colors
        self.orb1 = self._create_orb(pos1, self.color1)
        self.orb2 = self._create_orb(pos2, self.color2)

        # Create link line between orbs (blend of both colors)
        link_color = (
            (self.color1[0] + self.color2[0]) // 2,
            (self.color1[1] + self.color2[1]) // 2,
            (self.color1[2] + self.color2[2]) // 2,
        )
        self.link_color = link_color
        self.link_line = pg.PlotCurveItem(
            x=[pos1[0], pos2[0]],
            y=[pos1[1], pos2[1]],
            pen=pg.mkPen(color=(*link_color, 150), width=3),
        )
        self.link_line.setZValue(-3)
        self.view.addItem(self.link_line)

        # Create glow effect for link
        self.link_glow = pg.PlotCurveItem(
            x=[pos1[0], pos2[0]],
            y=[pos1[1], pos2[1]],
            pen=pg.mkPen(color=(*link_color, 60), width=8),
        )
        self.link_glow.setZValue(-4)
        self.view.addItem(self.link_glow)

    def _create_orb(self, pos: Tuple[float, float], color: Tuple[int, int, int]):
        """Create a glowing orb at the given position with the specified color."""
        size = 12
        angles = np.linspace(0, 2 * np.pi, 20)
        x_points = pos[0] + size * np.cos(angles)
        y_points = pos[1] + size * np.sin(angles)

        # Inner bright orb
        orb_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*color, 180),
            fillLevel="enclosed",
        )
        orb_fill.setZValue(-1)
        self.view.addItem(orb_fill)

        # Outer glow
        glow_size = 18
        glow_x = pos[0] + glow_size * np.cos(angles)
        glow_y = pos[1] + glow_size * np.sin(angles)
        orb_glow = pg.PlotCurveItem(
            x=glow_x,
            y=glow_y,
            pen=None,
            brush=pg.mkBrush(*color, 60),
            fillLevel="enclosed",
        )
        orb_glow.setZValue(-2)
        self.view.addItem(orb_glow)

        return {"fill": orb_fill, "glow": orb_glow, "pos": pos, "color": color}

    def trigger_flash(self):
        """Trigger a flash effect to indicate regen speedup from unmatched input."""
        self.flash_timer = self.flash_duration

    def update(
        self, dt: float, new_pos1: Tuple[float, float], new_pos2: Tuple[float, float]
    ) -> bool:
        """Update orb positions and visual effects.

        Returns True if orb should regenerate into letters.
        """
        self.time += dt
        self.pos1 = new_pos1
        self.pos2 = new_pos2

        # Update regeneration timer
        self.regen_timer += dt

        # Update flash timer
        if self.flash_timer > 0:
            self.flash_timer -= dt

        # Calculate regen progress ratio (clamped to 0-1)
        regen_ratio = min(self.regen_timer / self.regen_duration, 1.0)

        # Scale orbs from 50% to 100% based on regen progress
        orb_scale = 0.5 + 0.5 * regen_ratio

        # Update orb positions with scale
        self._update_orb_position(self.orb1, new_pos1, orb_scale)
        self._update_orb_position(self.orb2, new_pos2, orb_scale)

        # Update link line
        self.link_line.setData(x=[new_pos1[0], new_pos2[0]], y=[new_pos1[1], new_pos2[1]])
        self.link_glow.setData(x=[new_pos1[0], new_pos2[0]], y=[new_pos1[1], new_pos2[1]])

        # Pulse frequency scales from 1 Hz to 10 Hz based on regen progress
        # 1 Hz = 2π rad/s, 10 Hz = 20π rad/s
        pulse_freq = 2 * math.pi * (1 + 9 * regen_ratio)
        pulse = 0.5 + 0.5 * math.sin(self.time * pulse_freq)

        # Check for flash effect (bright white flash)
        if self.flash_timer > 0:
            flash_intensity = self.flash_timer / self.flash_duration
            flash_color = (255, 255, 255)
            alpha = int(200 + 55 * flash_intensity)
            glow_alpha = int(150 * flash_intensity)
            width_boost = 4 * flash_intensity
            self.link_line.setPen(pg.mkPen(color=(*flash_color, alpha), width=3 + width_boost))
            self.link_glow.setPen(
                pg.mkPen(color=(*flash_color, glow_alpha), width=8 + width_boost * 2)
            )
            self._update_orb_colors(self.orb1, flash_color, alpha, glow_alpha)
            self._update_orb_colors(self.orb2, flash_color, alpha, glow_alpha)
        elif regen_ratio > 0.6:
            # Warning effect - shift color toward red
            warning_color = (
                int(self.link_color[0] + (255 - self.link_color[0]) * regen_ratio),
                int(self.link_color[1] * (1 - regen_ratio * 0.5)),
                int(self.link_color[2] * (1 - regen_ratio * 0.5)),
            )
            alpha = int(150 + 100 * pulse)
            glow_alpha = int(60 + 40 * pulse)
            self.link_line.setPen(pg.mkPen(color=(*warning_color, alpha), width=3 + 2 * pulse))
            self.link_glow.setPen(pg.mkPen(color=(*warning_color, glow_alpha), width=8 + 4 * pulse))
            self._update_orb_colors(self.orb1, warning_color, alpha, glow_alpha)
            self._update_orb_colors(self.orb2, warning_color, alpha, glow_alpha)
        else:
            # Normal pulse effect
            alpha = int(100 + 80 * pulse)
            glow_alpha = int(40 + 30 * pulse)
            self.link_line.setPen(pg.mkPen(color=(*self.link_color, alpha), width=3))
            self.link_glow.setPen(pg.mkPen(color=(*self.link_color, glow_alpha), width=8))
            self._update_orb_colors(
                self.orb1, self.orb1["color"], int(120 + 60 * pulse), int(40 + 20 * pulse)
            )
            self._update_orb_colors(
                self.orb2, self.orb2["color"], int(120 + 60 * pulse), int(40 + 20 * pulse)
            )

        # Check if regeneration should occur
        return self.regen_timer >= self.regen_duration

    def _update_orb_colors(
        self, orb: dict, color: Tuple[int, int, int], alpha: int, glow_alpha: int
    ):
        """Update orb fill and glow colors."""
        orb["fill"].setBrush(pg.mkBrush(*color, alpha))
        orb["glow"].setBrush(pg.mkBrush(*color, glow_alpha))

    def _update_orb_position(self, orb: dict, pos: Tuple[float, float], scale: float = 1.0):
        """Update a single orb's position and size."""
        base_size = 12
        base_glow_size = 18
        size = base_size * scale
        glow_size = base_glow_size * scale
        angles = np.linspace(0, 2 * np.pi, 20)

        # Update fill
        x_points = pos[0] + size * np.cos(angles)
        y_points = pos[1] + size * np.sin(angles)
        orb["fill"].setData(x=x_points, y=y_points)

        # Update glow
        glow_x = pos[0] + glow_size * np.cos(angles)
        glow_y = pos[1] + glow_size * np.sin(angles)
        orb["glow"].setData(x=glow_x, y=glow_y)

        orb["pos"] = pos

    def cleanup(self):
        """Remove all visual elements."""
        if self.orb1["fill"].scene():
            self.view.removeItem(self.orb1["fill"])
        if self.orb1["glow"].scene():
            self.view.removeItem(self.orb1["glow"])
        if self.orb2["fill"].scene():
            self.view.removeItem(self.orb2["fill"])
        if self.orb2["glow"].scene():
            self.view.removeItem(self.orb2["glow"])
        if self.link_line.scene():
            self.view.removeItem(self.link_line)
        if self.link_glow.scene():
            self.view.removeItem(self.link_glow)


class SinusoidBoss(BaseBoss):
    """
    A boss with two strings of letters moving on closed oval/racetrack paths.
    Letters follow the path like a train, traveling in opposite directions.
    """

    def __init__(
        self,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
        game_engine=None,
    ):
        super().__init__(view=view, laser_manager=laser_manager, waveform=waveform)

        self.game_engine = game_engine

        # Generic Boss Attributes
        self.center_pos = pos
        self.target_y = 150  # Target Y position for center
        self.defeated = False
        self.completed = False

        self.health = 40
        self.max_health = 40
        self.speed = 1.0  # Base speed multiplier

        # String generation - both strings have the same letters, using only valid buttons
        self.string1_text = "".join(random.choice(ALL_BUTTONS) for _ in range(20))
        self.string2_text = self.string1_text

        self.string1_letters: List[BossLetter] = []
        self.string2_letters: List[BossLetter] = []

        # Path parameters - oval/racetrack shape
        self.screen_width = 800
        self.path_width = 300  # Horizontal extent of oval path
        self.path_height = 50  # Vertical extent of oval path
        self.path_center_y_upper = self.target_y + 70  # Y center for upper path
        self.path_center_y_lower = self.target_y - 70  # Y center for lower path

        # Movement parameters
        self.time = 0.0
        self.path_speed = 0.075  # How fast letters traverse the path (reduced by 50%)
        self.letter_spacing_on_path = 0.05  # Spacing between letters as fraction of path (0-1)

        # Curves to visualize paths (thicker lines)
        self.curve1 = pg.PlotCurveItem(pen=pg.mkPen(color=(100, 200, 255, 100), width=16))
        self.curve2 = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 100, 200, 100), width=16))
        self.curve1.setZValue(-5)
        self.curve2.setZValue(-5)
        self.view.addItem(self.curve1)
        self.view.addItem(self.curve2)

        # Waveform animation state for each string
        self.string1_wave_time = 0.0
        self.string1_wave_active = False
        self.string2_wave_time = 0.0
        self.string2_wave_active = False
        self.wave_duration = 1.0  # Duration of wave animation
        self.wave_amplitude = 15.0  # Max displacement of wave
        self.wave_frequency = 3.0  # Number of waves along the path

        # Glowing lines for aligned pairs
        self.glowing_lines: List[pg.PlotCurveItem] = []
        self.alignment_threshold = 30  # pixels for X-alignment

        # Destroyed orb pairs (visual remnants of destroyed letter pairs)
        self.destroyed_orb_pairs: List[DestroyedOrbPair] = []

        # Entry animation state
        self.movement_phase = "entering_from_sides"  # "entering_from_sides", "circling"
        self.entry_progress = 0.0  # 0 to 1
        self.entry_duration = 2.0  # seconds for entry animation
        self.entry_speed_side = 400  # pixels per second

        # Create letters at off-screen positions
        self._create_letters()

        # Draw initial path curves
        self._draw_path_curves()

        # Attack
        self.attack_timer = 0
        self.attack_interval = 3.0

        # Regeneration cooldown to prevent rapid mass resurrection
        self.regen_cooldown = 0.0
        self.regen_cooldown_duration = 0.5  # Minimum time between regenerations

        # Track spawned projectiles for cleanup on boss death
        self.projectiles: List = []

    def _create_letters(self):
        """Create letters for both strings, starting off-screen."""
        # String 1 starts off-screen left, will enter from left side
        start_x1 = -self.screen_width / 2 - 50
        for i, letter_char in enumerate(self.string1_text):
            # Space letters out horizontally off-screen
            x = start_x1 - i * 40
            y = self.path_center_y_upper
            letter = BossLetter(letter_char, (x, y), self.view)
            # Set initial path position - letters are evenly spaced around the path
            letter.path_position = i * self.letter_spacing_on_path
            self.string1_letters.append(letter)

        # String 2 starts off-screen right, will enter from right side
        start_x2 = self.screen_width / 2 + 50
        for i, letter_char in enumerate(self.string2_text):
            # Space letters out horizontally off-screen
            x = start_x2 + i * 40
            y = self.path_center_y_lower
            letter = BossLetter(letter_char, (x, y), self.view)
            # Set initial path position - letters are evenly spaced around the path
            letter.path_position = i * self.letter_spacing_on_path
            self.string2_letters.append(letter)

    def _get_rounded_rect_position(
        self, t: float, center_y: float, wave_offset: float = 0.0
    ) -> Tuple[float, float]:
        """Get position on rounded rectangle (stadium) path for parameter t (0 to 1).

        The shape is a rectangle with semicircular ends (like a pill/capsule).
        t=0 starts at rightmost point, goes counter-clockwise.
        wave_offset adds perpendicular displacement for wave animation.
        """
        # The stadium shape: two semicircles connected by straight lines
        # Radius of semicircles = path_height
        # Half-width of straight section = path_width - path_height
        radius = self.path_height
        half_straight = self.path_width - self.path_height

        # Section lengths
        semicircle_arc = math.pi * radius  # Half circle
        straight_section = 2 * half_straight  # Full width of straight part

        # Total perimeter
        total_perimeter = 2 * semicircle_arc + 2 * straight_section

        # Normalize t to perimeter distance
        dist = (t % 1.0) * total_perimeter

        # Cumulative distances for each section boundary
        right_arc_end = semicircle_arc
        top_straight_end = right_arc_end + straight_section
        left_arc_end = top_straight_end + semicircle_arc
        # bottom_straight_end = total_perimeter

        if dist < right_arc_end:
            # Right semicircle (going from bottom to top)
            angle = -math.pi / 2 + (dist / radius)
            x = half_straight + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            # Normal points outward from center of arc
            normal_x, normal_y = math.cos(angle), math.sin(angle)
        elif dist < top_straight_end:
            # Top straight section (going left)
            progress = (dist - right_arc_end) / straight_section
            x = half_straight - progress * 2 * half_straight
            y = center_y + radius
            # Normal points up
            normal_x, normal_y = 0, 1
        elif dist < left_arc_end:
            # Left semicircle (going from top to bottom)
            arc_dist = dist - top_straight_end
            angle = math.pi / 2 + (arc_dist / radius)
            x = -half_straight + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            # Normal points outward from center of arc
            normal_x, normal_y = math.cos(angle), math.sin(angle)
        else:
            # Bottom straight section (going right)
            progress = (dist - left_arc_end) / straight_section
            x = -half_straight + progress * 2 * half_straight
            y = center_y - radius
            # Normal points down
            normal_x, normal_y = 0, -1

        # Apply wave offset perpendicular to path
        x += normal_x * wave_offset
        y += normal_y * wave_offset

        return (x, y)

    def _draw_path_curves(self):
        """Draw the rounded rectangle path curves with optional wave animation."""
        num_points = 150

        # Calculate wave offset for string 1
        wave1_offset_func = self._get_wave_offset_func(
            self.string1_wave_active, self.string1_wave_time
        )

        # Generate points for upper rounded rectangle
        points1_x, points1_y = [], []
        for i in range(num_points):
            t = i / num_points
            wave_offset = wave1_offset_func(t)
            x, y = self._get_rounded_rect_position(t, self.path_center_y_upper, wave_offset)
            points1_x.append(x)
            points1_y.append(y)
        # Close the loop
        points1_x.append(points1_x[0])
        points1_y.append(points1_y[0])
        self.curve1.setData(x=points1_x, y=points1_y)

        # Calculate wave offset for string 2
        wave2_offset_func = self._get_wave_offset_func(
            self.string2_wave_active, self.string2_wave_time
        )

        # Generate points for lower rounded rectangle
        points2_x, points2_y = [], []
        for i in range(num_points):
            t = i / num_points
            wave_offset = wave2_offset_func(t)
            x, y = self._get_rounded_rect_position(t, self.path_center_y_lower, wave_offset)
            points2_x.append(x)
            points2_y.append(y)
        # Close the loop
        points2_x.append(points2_x[0])
        points2_y.append(points2_y[0])
        self.curve2.setData(x=points2_x, y=points2_y)

    def _get_wave_offset_func(self, wave_active: bool, wave_time: float):
        """Return a function that calculates wave offset for a given path position."""
        if not wave_active:
            return lambda t: 0.0

        # Decay amplitude over time
        decay = max(0.0, 1.0 - wave_time / self.wave_duration)
        amplitude = self.wave_amplitude * decay

        def wave_func(t):
            # Traveling wave along the path
            phase = t * self.wave_frequency * 2 * math.pi - wave_time * 10
            return amplitude * math.sin(phase)

        return wave_func

    def update(self, dt: float):
        """Update the boss's state."""
        # Don't update if boss is defeated/completed
        if self.completed or self.defeated:
            return None

        effective_dt = dt * self.speed_multiplier

        # Update wave animations
        if self.string1_wave_active:
            self.string1_wave_time += dt
            if self.string1_wave_time >= self.wave_duration:
                self.string1_wave_active = False
                self.string1_wave_time = 0.0

        if self.string2_wave_active:
            self.string2_wave_time += dt
            if self.string2_wave_time >= self.wave_duration:
                self.string2_wave_active = False
                self.string2_wave_time = 0.0

        if self.movement_phase == "entering_from_sides":
            self._update_entry_animation(effective_dt)
        elif self.movement_phase == "circling":
            self._update_circling_movement(effective_dt)

        # Redraw path curves (for wave animation)
        self._draw_path_curves()

        # Update glowing lines (always update for visibility)
        self._update_glowing_lines()

        # Attack
        self.attack_timer += dt
        new_projectile = None
        if self.attack_timer >= self.attack_interval and self.movement_phase == "circling":
            self.attack_timer = 0
            new_projectile = self.spawn_projectile()

        return new_projectile

    def _update_entry_animation(self, dt: float):
        """Animate letters entering from opposite sides of the screen."""
        self.entry_progress += dt / self.entry_duration

        if self.entry_progress >= 1.0:
            # Entry complete, transition to circling
            self.entry_progress = 1.0
            self.movement_phase = "circling"
            self.time = 0.0
            # Sync all letters to their proper path positions
            for i, letter in enumerate(self.string1_letters):
                letter.path_position = i * self.letter_spacing_on_path
            for i, letter in enumerate(self.string2_letters):
                letter.path_position = i * self.letter_spacing_on_path
            return

        # Ease-out function for smooth deceleration
        ease_progress = 1.0 - (1.0 - self.entry_progress) ** 2

        # String 1: Enter from left, converge to starting positions on upper path
        for i, letter in enumerate(self.string1_letters):
            if not letter.alive:
                continue

            # Starting position (off-screen left)
            start_x = -self.screen_width / 2 - 50 - i * 40
            start_y = self.path_center_y_upper

            # Target position on path (staggered entry)
            target_t = i * self.letter_spacing_on_path
            target_x, target_y = self._get_rounded_rect_position(target_t, self.path_center_y_upper)

            # Interpolate
            current_x = start_x + (target_x - start_x) * ease_progress
            current_y = start_y + (target_y - start_y) * ease_progress

            letter.update_pos((current_x, current_y))

        # String 2: Enter from right, converge to starting positions on lower path
        for i, letter in enumerate(self.string2_letters):
            if not letter.alive:
                continue

            # Starting position (off-screen right)
            start_x = self.screen_width / 2 + 50 + i * 40
            start_y = self.path_center_y_lower

            # Target position on path (staggered entry)
            target_t = i * self.letter_spacing_on_path
            target_x, target_y = self._get_rounded_rect_position(target_t, self.path_center_y_lower)

            # Interpolate
            current_x = start_x + (target_x - start_x) * ease_progress
            current_y = start_y + (target_y - start_y) * ease_progress

            letter.update_pos((current_x, current_y))

    def _update_circling_movement(self, dt: float):
        """Update letters moving around their closed rounded rectangle paths."""
        # Increase speed based on health
        health_ratio = self.health / self.max_health
        current_speed = self.path_speed
        if health_ratio < 0.5:
            current_speed = self.path_speed * (1.0 + (1.0 - health_ratio) * 1.5)

        self.time += dt

        # Update path positions for all letters (they move as a train)
        path_advance = current_speed * dt

        # Get wave offset functions for both strings
        wave1_offset_func = self._get_wave_offset_func(
            self.string1_wave_active, self.string1_wave_time
        )
        wave2_offset_func = self._get_wave_offset_func(
            self.string2_wave_active, self.string2_wave_time
        )

        # String 1: Clockwise on upper path (path_position decreases, 70% slower)
        string1_advance = path_advance * 0.3  # 70% slower than string 2
        for letter in self.string1_letters:
            letter.path_position = (letter.path_position - string1_advance) % 1.0
            wave_offset = wave1_offset_func(letter.path_position)
            new_pos = self._get_rounded_rect_position(
                letter.path_position, self.path_center_y_upper, wave_offset
            )
            letter.pos = new_pos  # Always update pos for orb tracking
            if letter.alive:
                letter.update_pos(new_pos)

        # String 2: Counter-clockwise on lower path (path_position increases)
        for letter in self.string2_letters:
            letter.path_position = (letter.path_position + path_advance) % 1.0
            wave_offset = wave2_offset_func(letter.path_position)
            new_pos = self._get_rounded_rect_position(
                letter.path_position, self.path_center_y_lower, wave_offset
            )
            letter.pos = new_pos  # Always update pos for orb tracking
            if letter.alive:
                letter.update_pos(new_pos)

        # Update regeneration cooldown
        if self.regen_cooldown > 0:
            self.regen_cooldown -= dt

        # Update destroyed orb pairs to follow the path positions (with wave)
        # Check for regeneration - only regenerate ONE pair per cooldown period
        orb_to_regenerate = None
        for orb_pair in self.destroyed_orb_pairs:
            # Get positions with wave offset applied
            idx1 = orb_pair.letter_idx1
            idx2 = orb_pair.letter_idx2
            path_pos1 = self.string1_letters[idx1].path_position
            path_pos2 = self.string2_letters[idx2].path_position
            wave_offset1 = wave1_offset_func(path_pos1)
            wave_offset2 = wave2_offset_func(path_pos2)
            pos1 = self._get_rounded_rect_position(
                path_pos1, self.path_center_y_upper, wave_offset1
            )
            pos2 = self._get_rounded_rect_position(
                path_pos2, self.path_center_y_lower, wave_offset2
            )
            should_regen = orb_pair.update(dt, pos1, pos2)
            if should_regen and orb_to_regenerate is None and self.regen_cooldown <= 0:
                orb_to_regenerate = orb_pair

        # Process ONE regeneration per cooldown period (prevents mass resurrection)
        if orb_to_regenerate:
            self._regenerate_letter_pair(orb_to_regenerate)
            self.regen_cooldown = self.regen_cooldown_duration

    def _regenerate_letter_pair(self, orb_pair: DestroyedOrbPair):
        """Regenerate a letter pair from an orb pair."""
        # Don't regenerate if boss is already defeated
        if self.completed or self.defeated:
            return

        idx1 = orb_pair.letter_idx1
        idx2 = orb_pair.letter_idx2

        # Revive the letters
        letter1 = self.string1_letters[idx1]
        letter2 = self.string2_letters[idx2]

        letter1.revive()
        letter2.revive()

        # Restore health (each pair is worth 2 health)
        self.health = min(self.max_health, self.health + 2)

        # Clean up and remove the orb pair
        orb_pair.cleanup()
        self.destroyed_orb_pairs.remove(orb_pair)

    def _reset_all_orb_regen_timers(self):
        """Reset regeneration timers on all orb pairs (called when a new pair is destroyed)."""
        for orb_pair in self.destroyed_orb_pairs:
            orb_pair.regen_timer = 0.0

    def on_unmatched_input(self, key: str) -> bool:
        """Speed up regeneration when wrong key is pressed (discourages button mashing)."""
        if self.completed or self.movement_phase == "entering_from_sides":
            return False

        if not self.destroyed_orb_pairs:
            return False

        # Speed up regen on all orb pairs - add 0.5 seconds per wrong key
        regen_speedup = 0.5
        for orb_pair in self.destroyed_orb_pairs:
            orb_pair.regen_timer += regen_speedup
            orb_pair.trigger_flash()

        # Disable player input briefly to punish button mashing
        if self.game_engine:
            self.game_engine.disable_player(0.25)

        return True

    def _spawn_retaliation_projectile(self, pos1: Tuple[float, float], pos2: Tuple[float, float]):
        """Spawn a retaliatory projectile from the destruction point toward the player."""
        # Reduce projectile spawn rate based on difficulty
        # Easy: 30% spawn rate (70% less), Normal: 70% spawn rate (30% less)
        if self.game_engine and self.game_engine.config:
            difficulty = self.game_engine.config.spawning.get_difficulty_level()
            if difficulty == DifficultyLevel.EASY:
                if random.random() > 0.3:
                    return None
            elif difficulty == DifficultyLevel.NORMAL:
                if random.random() > 0.7:
                    return None

        # Spawn from the midpoint between the two destroyed letters
        spawn_x = (pos1[0] + pos2[0]) / 2
        spawn_y = (pos1[1] + pos2[1]) / 2

        letter = random.choice(ALL_BUTTONS)

        projectile = RapidHitEnemy(
            sequence=letter,
            pos=(spawn_x, spawn_y),
            view=self.view,
            laser_manager=self.laser_manager,
            waveform=self.waveform,
            hit_count=1,
        )
        # Faster speed for retaliation projectiles
        projectile.speed = 150
        # Track projectile for cleanup on boss death
        self.projectiles.append(projectile)
        return projectile

    def spawn_projectile(self):
        """Spawn a RapidHitEnemy projectile (reduced based on difficulty)."""
        # Reduce projectile spawn rate based on difficulty
        # Easy: 30% spawn rate (70% less), Normal: 70% spawn rate (30% less)
        if self.game_engine and self.game_engine.config:
            difficulty = self.game_engine.config.spawning.get_difficulty_level()
            if difficulty == DifficultyLevel.EASY:
                if random.random() > 0.3:
                    return None
            elif difficulty == DifficultyLevel.NORMAL:
                if random.random() > 0.7:
                    return None

        letter = random.choice(ALL_BUTTONS)
        pos = (random.uniform(-200, 200), self.center_pos[1])
        hit_count = random.randint(1, 4)

        projectile = RapidHitEnemy(
            sequence=letter,
            pos=pos,
            view=self.view,
            laser_manager=self.laser_manager,
            waveform=self.waveform,
            hit_count=hit_count,
        )
        projectile.speed = 100
        # Track projectile for cleanup on boss death
        self.projectiles.append(projectile)
        return projectile

    def type_button(self, button: str) -> bool:
        """Handle player typing.

        Any matching letters (same character) that are X-aligned are vulnerable,
        regardless of their position in the string.
        Boss is invulnerable during entry animation.
        """
        # Boss is invulnerable during entry
        if self.movement_phase == "entering_from_sides":
            return False

        # Find all alive letters with the matching button in both strings
        matching_letters_1 = [l for l in self.string1_letters if l.alive and l.letter == button]
        matching_letters_2 = [l for l in self.string2_letters if l.alive and l.letter == button]

        # Check for any X-aligned pairs between the two strings
        for l1 in matching_letters_1:
            for l2 in matching_letters_2:
                if abs(l1.pos[0] - l2.pos[0]) < self.alignment_threshold:
                    # Store positions before destroying
                    pos1 = l1.pos
                    pos2 = l2.pos

                    # Store letter indices for orb position tracking
                    idx1 = self.string1_letters.index(l1)
                    idx2 = self.string2_letters.index(l2)

                    # Found an aligned pair - destroy both
                    l1.destroy()
                    l2.destroy()
                    self.health -= 2

                    # Trigger wave animation on both strings
                    self.string1_wave_active = True
                    self.string1_wave_time = 0.0
                    self.string2_wave_active = True
                    self.string2_wave_time = 0.0

                    # Create orb pair at destruction positions
                    orb_pair = DestroyedOrbPair(pos1, pos2, self.view)
                    # Store indices for position tracking
                    orb_pair.letter_idx1 = idx1
                    orb_pair.letter_idx2 = idx2
                    self.destroyed_orb_pairs.append(orb_pair)

                    # Reset regeneration timers on all existing orb pairs
                    self._reset_all_orb_regen_timers()

                    if self.game_engine and self.game_engine.explosion_manager:
                        self.game_engine.explosion_manager.create_explosion(
                            pos1, get_button_color(button), "enhanced", 1.0
                        )
                        self.game_engine.explosion_manager.create_explosion(
                            pos2, get_button_color(button), "enhanced", 1.0
                        )

                    # Spawn retaliatory projectile from destruction point
                    retaliation = self._spawn_retaliation_projectile(pos1, pos2)
                    if retaliation:
                        self.game_engine.enemies.append(retaliation)

                    if self.health <= 0:
                        self.completed = True
                        self.defeated = True

                    return True

        return False

    def can_type_button(self, button: str) -> bool:
        """Check if a button can be typed.

        Any matching letters (same character) that are X-aligned are vulnerable,
        regardless of their position in the string.
        Boss is invulnerable during entry animation.
        """
        # Boss is invulnerable during entry
        if self.movement_phase == "entering_from_sides":
            return False

        # Find all alive letters with the matching button in both strings
        matching_letters_1 = [l for l in self.string1_letters if l.alive and l.letter == button]
        matching_letters_2 = [l for l in self.string2_letters if l.alive and l.letter == button]

        # Check for any X-aligned pairs
        for l1 in matching_letters_1:
            for l2 in matching_letters_2:
                if abs(l1.pos[0] - l2.pos[0]) < self.alignment_threshold:
                    return True
        return False

    def cleanup(self):
        """Clean up all visual elements."""
        super().cleanup()
        for letter in self.string1_letters:
            letter.cleanup()
        for letter in self.string2_letters:
            letter.cleanup()
        if self.curve1 and self.curve1.scene():
            self.view.removeItem(self.curve1)
        if self.curve2 and self.curve2.scene():
            self.view.removeItem(self.curve2)

        # Clean up glowing lines
        for line in self.glowing_lines:
            if line.scene():
                self.view.removeItem(line)
        self.glowing_lines.clear()

        # Clean up destroyed orb pairs
        for orb_pair in self.destroyed_orb_pairs:
            orb_pair.cleanup()
        self.destroyed_orb_pairs.clear()

    def _update_glowing_lines(self):
        """Draw glowing lines between X-aligned matching letter pairs."""
        # Cleanup existing lines
        for line in self.glowing_lines:
            if line.scene():
                self.view.removeItem(line)
        self.glowing_lines.clear()

        # Don't show glowing lines during entry animation
        if self.movement_phase == "entering_from_sides":
            return

        # Find all X-aligned matching pairs (any matching letters, not just by index)
        # Group letters by their character
        letters_by_char_1 = {}
        for letter in self.string1_letters:
            if letter.alive:
                if letter.letter not in letters_by_char_1:
                    letters_by_char_1[letter.letter] = []
                letters_by_char_1[letter.letter].append(letter)

        letters_by_char_2 = {}
        for letter in self.string2_letters:
            if letter.alive:
                if letter.letter not in letters_by_char_2:
                    letters_by_char_2[letter.letter] = []
                letters_by_char_2[letter.letter].append(letter)

        # Check for X-aligned pairs with matching characters
        current_time = time.time()
        alpha_pulse = 150 + 100 * math.sin(current_time * 5)
        width_pulse = 8 + 4 * math.sin(current_time * 5)

        for char, letters_1 in letters_by_char_1.items():
            if char not in letters_by_char_2:
                continue
            letters_2 = letters_by_char_2[char]

            for l1 in letters_1:
                for l2 in letters_2:
                    if abs(l1.pos[0] - l2.pos[0]) < self.alignment_threshold:
                        # Create a glowing line between l1 and l2
                        line = pg.PlotCurveItem(
                            x=[l1.pos[0], l2.pos[0]],
                            y=[l1.pos[1], l2.pos[1]],
                            pen=pg.mkPen(color=(255, 255, 0, int(alpha_pulse)), width=width_pulse),
                        )
                        self.view.addItem(line)
                        self.glowing_lines.append(line)

    def is_complete(self) -> bool:
        return self.completed or self.defeated or self.health <= 0

    @property
    def sequence(self):
        """Return combined sequence for unified interface."""
        s1 = "".join([l.letter for l in self.string1_letters if l.alive])
        s2 = "".join([l.letter for l in self.string2_letters if l.alive])
        return s1 + s2

    @property
    def letter_items(self):
        """Get all letter items from both strings."""
        items = []
        for letter in self.string1_letters:
            if letter.alive and letter.text_item:
                items.append(letter.text_item)
        for letter in self.string2_letters:
            if letter.alive and letter.text_item:
                items.append(letter.text_item)
        return items

    @property
    def letter_backgrounds(self):
        """Get all letter backgrounds from both strings."""
        backgrounds = []
        for letter in self.string1_letters:
            if letter.alive and letter.background:
                backgrounds.append(letter.background)
        for letter in self.string2_letters:
            if letter.alive and letter.background:
                backgrounds.append(letter.background)
        return backgrounds

    def create_victory_animations(self):
        """Create victory animations for boss defeat."""
        # Create custom boss death animation
        animation = SinusoidBossDeathAnimation(self, self.view)
        # Mark this as a boss animation for special handling
        animation.is_boss = True
        return [animation]

    # Implementing abstract methods from BaseEnemy
    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of boss."""
        return self.center_pos

    def get_boss_radius(self) -> float:
        """Get the radius of the boss for death animations."""
        # Use the path width for the radius
        return self.path_width * 2

    def get_width(self) -> float:
        """Get total width of boss."""
        # Calculate max width of the letters currently visible
        max_x = -float("inf")
        min_x = float("inf")
        for letter in self.string1_letters + self.string2_letters:
            if letter.alive:
                max_x = max(max_x, letter.pos[0])
                min_x = min(min_x, letter.pos[0])
        if max_x == -float("inf"):  # If no letters alive, return a default width
            return 0
        return max_x - min_x + 50  # Add some padding

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if boss has moved below screen."""
        # Sinusoid boss does not move below screen
        return False

    def reset_typing_progress(self):
        """Reset typing progress (not applicable for this boss)."""
        return

    def get_destruction_info(self):
        """Get destruction info for boss."""
        return {
            "points": 2000,
            "explosion_type": "boss",
            "explosion_scale": 3.0,
            "shake_type": "massive",
        }


class SinusoidBossDeathAnimation(BossDeathAnimation):
    """Custom death animation for the Sinusoid Boss.

    Letters from both strings converge in pairs toward the center,
    meeting and exploding together to highlight the paired nature.
    """

    def __init__(self, boss: SinusoidBoss, view):
        # Initialize base class for finale + explosion/shake callback support
        super().__init__(boss, view)
        self.duration = 2.5  # Override base duration
        # Remove shield rings spawned by base class — this animation has its own visuals
        for ring_info in self.shield_rings:
            self.view.removeItem(ring_info["item"])
        self.shield_rings.clear()

        # Store references to boss visual elements
        self.string1_letters = boss.string1_letters[:]
        self.string2_letters = boss.string2_letters[:]
        self.boss_curves = [boss.curve1, boss.curve2]
        self.boss_glowing_lines = boss.glowing_lines[:]

        # Keep orb pairs active during death animation and set up their collapse
        self.destroyed_orb_pairs = boss.destroyed_orb_pairs[:]
        boss.destroyed_orb_pairs.clear()  # Transfer ownership to animation

        # Set up orb pair collapse data
        self.orb_pair_data = []
        for i, orb_pair in enumerate(self.destroyed_orb_pairs):
            # Calculate meeting point (midpoint between the two orbs)
            meet_x = (orb_pair.pos1[0] + orb_pair.pos2[0]) / 2
            meet_y = (orb_pair.pos1[1] + orb_pair.pos2[1]) / 2
            self.orb_pair_data.append(
                {
                    "orb_pair": orb_pair,
                    "pos1_start": orb_pair.pos1,
                    "pos2_start": orb_pair.pos2,
                    "meet_point": (meet_x, meet_y),
                    "exploded": False,
                    "explosion_time": 0.2 + i * 0.1,  # Staggered orb explosions
                }
            )

        # Store initial positions for letter animation
        self.letter_data = []
        num_pairs = min(len(self.string1_letters), len(self.string2_letters))

        for i in range(num_pairs):
            l1 = self.string1_letters[i]
            l2 = self.string2_letters[i]

            # Calculate meeting point (midpoint between the two letters' X, center Y)
            meet_x = (l1.pos[0] + l2.pos[0]) / 2
            meet_y = self.center_pos[1]

            self.letter_data.append(
                {
                    "l1": l1,
                    "l2": l2,
                    "l1_start": l1.pos,
                    "l2_start": l2.pos,
                    "meet_point": (meet_x, meet_y),
                    "exploded": False,
                    "explosion_time": 0.3 + i * 0.08,  # Staggered explosions
                }
            )

        # Track explosions
        self.last_shake_time = 0.0
        self.final_explosion_triggered = False
        self.explosion_rings = []
        self.ring_start_time = 0.0

        # Create converging beam effects between pairs
        self.beam_lines = []
        for _ in self.letter_data:
            beam = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 255, 0, 150), width=12))
            beam.setZValue(-2)
            self.view.addItem(beam)
            self.beam_lines.append(beam)

    def update(self, dt):
        """Update the animation."""
        self.elapsed += dt
        progress = self.elapsed / self.duration

        # Fade out path curves quickly
        curve_opacity = max(0.0, 1.0 - progress * 3)
        for curve in self.boss_curves:
            if curve and curve.scene():
                curve.setOpacity(curve_opacity)

        # Clear old glowing lines
        for line in self.boss_glowing_lines:
            if line.scene():
                self.view.removeItem(line)
        self.boss_glowing_lines.clear()

        # Animate orb pairs collapsing toward their meeting points
        for data in self.orb_pair_data:
            if data["exploded"]:
                continue

            orb_pair = data["orb_pair"]
            meet_point = data["meet_point"]

            # Check if it's time for this orb pair to explode
            if self.elapsed >= data["explosion_time"]:
                data["exploded"] = True

                # Clean up the orb pair visuals
                orb_pair.cleanup()

                # Set center_pos to meeting point so explosion spawns there
                self.center_pos = meet_point

                # Trigger explosion at meeting point
                if self.explosion_callback:
                    self.explosion_callback()

                # Shake
                if self.shake_callback:
                    self.shake_callback()

                continue

            # Calculate convergence progress for this orb pair
            pair_progress = min(1.0, self.elapsed / data["explosion_time"])
            # Use ease-in for acceleration toward meeting point
            ease_progress = pair_progress * pair_progress

            # Move orbs toward meeting point
            pos1_x = data["pos1_start"][0] + (meet_point[0] - data["pos1_start"][0]) * ease_progress
            pos1_y = data["pos1_start"][1] + (meet_point[1] - data["pos1_start"][1]) * ease_progress
            pos2_x = data["pos2_start"][0] + (meet_point[0] - data["pos2_start"][0]) * ease_progress
            pos2_y = data["pos2_start"][1] + (meet_point[1] - data["pos2_start"][1]) * ease_progress

            orb_pair.update(dt, (pos1_x, pos1_y), (pos2_x, pos2_y))

        # Animate each letter pair (no explosions - just fade out)
        for i, data in enumerate(self.letter_data):
            l1, l2 = data["l1"], data["l2"]
            meet_point = data["meet_point"]

            if data["exploded"]:
                continue

            # Check if it's time for this pair to disappear
            if self.elapsed >= data["explosion_time"]:
                data["exploded"] = True

                # Remove the letters (no explosion)
                l1.cleanup()
                l2.cleanup()

                # Remove the beam
                if i < len(self.beam_lines) and self.beam_lines[i].scene():
                    self.view.removeItem(self.beam_lines[i])

                continue

            # Calculate convergence progress for this pair
            pair_progress = min(1.0, self.elapsed / data["explosion_time"])
            # Use ease-in for acceleration toward meeting point
            ease_progress = pair_progress * pair_progress

            # Move letters toward meeting point
            l1_x = data["l1_start"][0] + (meet_point[0] - data["l1_start"][0]) * ease_progress
            l1_y = data["l1_start"][1] + (meet_point[1] - data["l1_start"][1]) * ease_progress
            l2_x = data["l2_start"][0] + (meet_point[0] - data["l2_start"][0]) * ease_progress
            l2_y = data["l2_start"][1] + (meet_point[1] - data["l2_start"][1]) * ease_progress

            l1.update_pos((l1_x, l1_y))
            l2.update_pos((l2_x, l2_y))

            # Update beam between letters (pulsing)
            if i < len(self.beam_lines):
                beam = self.beam_lines[i]
                pulse = 0.5 + 0.5 * math.sin(self.elapsed * 15)
                alpha = int(100 + 155 * pulse * (1 - pair_progress))
                width = 3 + 5 * pulse
                beam.setData(
                    x=[l1_x, l2_x],
                    y=[l1_y, l2_y],
                    pen=pg.mkPen(color=(255, 255, 0, alpha), width=width),
                )

            # Increase letter brightness as they converge
            brightness_boost = int(100 * ease_progress)
            if l1.text_item and l1.text_item.scene():
                color = BUTTON_COLORS.get(l1.letter, "#FFFFFF")
                rgb = tuple(
                    min(255, int(color[j : j + 2], 16) + brightness_boost) for j in (1, 3, 5)
                )
                l1.text_item.setColor(pg.mkColor(*rgb))
            if l2.text_item and l2.text_item.scene():
                color = BUTTON_COLORS.get(l2.letter, "#FFFFFF")
                rgb = tuple(
                    min(255, int(color[j : j + 2], 16) + brightness_boost) for j in (1, 3, 5)
                )
                l2.text_item.setColor(pg.mkColor(*rgb))

        # Check if all orb pairs have collapsed
        all_orbs_collapsed = all(data["exploded"] for data in self.orb_pair_data)
        all_letters_done = all(data["exploded"] for data in self.letter_data)

        # Trigger final big explosion after all orbs collapse
        if all_orbs_collapsed and not self.final_explosion_triggered:
            self.final_explosion_triggered = True
            # Reset center_pos to boss center for final explosion
            self.center_pos = (0, self.boss.target_y)
            # Trigger multiple explosions for a big effect
            if self.explosion_callback:
                for _ in range(5):
                    self.explosion_callback()
            if self.shake_callback:
                self.shake_callback()
            # Create expanding rings at center
            self._create_explosion_rings()

        # Update explosion rings
        self._update_explosion_rings(dt)

        # Finale effects from base class
        self._update_finale()

        if self.elapsed >= self.duration or (all_orbs_collapsed and all_letters_done):
            self.completed = True
            self.cleanup()
            return False

        return True

    def _create_explosion_rings(self):
        """Create expanding ring effects at the center of the boss."""
        self.explosion_rings = []
        num_rings = 4
        for i in range(num_rings):
            ring = {
                "item": pg.PlotCurveItem(pen=pg.mkPen(color=(255, 200, 100, 255), width=6)),
                "radius": 10.0,
                "max_radius": 200 + i * 50,
                "speed": 300 + i * 50,
                "delay": i * 0.1,
                "started": False,
            }
            ring["item"].setZValue(10)
            self.view.addItem(ring["item"])
            self.explosion_rings.append(ring)
        self.ring_start_time = self.elapsed

    def _update_explosion_rings(self, dt: float):
        """Update the expanding explosion rings."""
        if not self.explosion_rings:
            return

        ring_elapsed = self.elapsed - self.ring_start_time

        for ring in self.explosion_rings:
            if ring_elapsed < ring["delay"]:
                continue

            if not ring["started"]:
                ring["started"] = True

            # Expand the ring
            ring["radius"] += ring["speed"] * dt

            # Fade out as it expands
            progress = ring["radius"] / ring["max_radius"]
            if progress >= 1.0:
                if ring["item"].scene():
                    self.view.removeItem(ring["item"])
                continue

            alpha = int(255 * (1 - progress))
            width = max(1, 6 * (1 - progress))

            # Draw the ring
            angles = np.linspace(0, 2 * np.pi, 60)
            x_points = self.center_pos[0] + ring["radius"] * np.cos(angles)
            y_points = self.center_pos[1] + ring["radius"] * np.sin(angles)

            ring["item"].setData(
                x=x_points,
                y=y_points,
                pen=pg.mkPen(color=(255, 200, 100, alpha), width=width),
            )

    def is_completed(self) -> bool:
        """Check if animation is completed."""
        return self.completed

    def cleanup(self):
        """Clean up animation elements."""
        # Clean up base class shield rings
        super().cleanup()

        # Clean up any remaining letters
        for data in self.letter_data:
            data["l1"].cleanup()
            data["l2"].cleanup()

        # Clean up curves
        for curve in self.boss_curves:
            if curve and curve.scene():
                self.view.removeItem(curve)

        # Clean up glowing lines
        for line in self.boss_glowing_lines:
            if line.scene():
                self.view.removeItem(line)

        # Clean up beam lines
        for beam in self.beam_lines:
            if beam.scene():
                self.view.removeItem(beam)

        # Clean up destroyed orb pairs
        for orb_pair in self.destroyed_orb_pairs:
            orb_pair.cleanup()
        self.destroyed_orb_pairs.clear()

        # Clean up explosion rings
        for ring in self.explosion_rings:
            if ring["item"].scene():
                self.view.removeItem(ring["item"])
        self.explosion_rings.clear()
