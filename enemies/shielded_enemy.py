"""Shielded enemy implementation - single letter with rotating shield that fades in/out."""

from typing import Tuple
import random
import numpy as np
import pyqtgraph as pg
from enemies.base_enemy import BaseEnemy
from enemies.letter_effects import (
    LetterActivationAnim,
    EnemyLetterRingEffect,
    HexagonFlashAnim,
)
from config import BUTTON_COLORS, get_button_label
from config import ALL_BUTTONS
from font_manager import font_manager


class ShieldedEnemy(BaseEnemy):
    """Single-letter enemy with a rotating shield that blocks hits when active."""

    def __init__(
        self,
        sequence: str,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
    ):
        """Initialize shielded enemy."""
        super().__init__(view, laser_manager, waveform)
        # Only use first letter for single-letter enemy
        self.sequence = sequence[0] if sequence else random.choice(ALL_BUTTONS)
        self.typed_count = 0

        # Moderate speed for timing-based enemy
        self.speed = 160

        # Shield timing parameters
        self.shield_period = 1.5  # Full cycle duration in seconds
        self.shield_duty_cycle = 0.75  # 75% of time shield is active
        self.shield_time = 0.0  # Current time in shield cycle
        self.shield_active = True  # Current shield state

        # Shield visual parameters
        self.shield_rotation = 0.0  # Current rotation angle
        self.shield_rotation_speed = 180.0  # Degrees per second
        self.shield_radius = 35  # Shield orbit radius
        self.shield_segments = 3  # Number of shield segments

        # Create visual elements
        self.letter_items = []  # List for compatibility with victory animation
        self.letter_backgrounds = []
        self.shield_items = []
        self.animations = []
        self.shield_flash_timer = 0.0  # Timer for shield flash effect

        self._create_visuals(pos)

    def _create_visuals(self, pos: Tuple[float, float]):
        """Create all visual elements."""
        x, y = pos
        letter = self.sequence

        # Create hexagon background
        hexagon_bg = self._create_letter_hexagon(x, y, letter)
        self.letter_backgrounds.append(hexagon_bg)

        # Create letter text
        letter_item = pg.TextItem(
            text=get_button_label(letter),
            color=(255, 255, 255),
            anchor=(0.5, 0.5),
        )
        letter_item.setFont(font_manager.get_enemy_letter_font(20, bold=True))
        letter_item.setPos(x, y)
        self.view.addItem(letter_item)
        self.letter_items.append(letter_item)

        # Create rotating shield segments
        self._create_shield_segments(x, y)

    def _create_shield_segments(self, center_x: float, center_y: float):
        """Create the rotating shield segments."""
        color = BUTTON_COLORS.get(self.sequence, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        # Create arc segments around the letter
        for i in range(self.shield_segments):
            # Each segment is an arc
            segment = pg.PlotCurveItem(
                pen=pg.mkPen(color=(*rgb, 200), width=6),
            )
            self.view.addItem(segment)
            self.shield_items.append(segment)

        # Initial shield position
        self._update_shield_visuals(center_x, center_y)

    def _update_shield_visuals(self, center_x: float, center_y: float):
        """Update shield segment positions and opacity."""
        # Calculate shield opacity based on cycle position
        cycle_pos = self.shield_time / self.shield_period
        shield_on_duration = self.shield_duty_cycle

        if cycle_pos < shield_on_duration:
            # Shield is on - calculate fade in/out at edges
            fade_zone = 0.1  # 10% of on-time for fade transitions
            if cycle_pos < fade_zone * shield_on_duration:
                # Fading in
                opacity = cycle_pos / (fade_zone * shield_on_duration)
            elif cycle_pos > shield_on_duration * (1 - fade_zone):
                # Fading out
                opacity = (shield_on_duration - cycle_pos) / (fade_zone * shield_on_duration)
            else:
                opacity = 1.0
            self.shield_active = True
        else:
            # Shield is off
            opacity = 0.0
            self.shield_active = False

        color = BUTTON_COLORS.get(self.sequence, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        # Update each shield segment
        arc_length = 60  # Degrees per segment
        segment_gap = 360 / self.shield_segments

        for i, segment in enumerate(self.shield_items):
            # Calculate segment start angle
            base_angle = self.shield_rotation + i * segment_gap
            start_angle = np.radians(base_angle - arc_length / 2)
            end_angle = np.radians(base_angle + arc_length / 2)

            # Generate arc points
            num_points = 20
            angles = np.linspace(start_angle, end_angle, num_points)
            x_points = center_x + self.shield_radius * np.cos(angles)
            y_points = center_y + self.shield_radius * np.sin(angles)

            # Update segment with current opacity
            alpha = int(200 * opacity)
            segment.setData(
                x=x_points,
                y=y_points,
                pen=pg.mkPen(color=(*rgb, alpha), width=6),
            )

    def type_button(self, button: str) -> bool:
        """Try to type a button. Returns True if successful."""
        if self.typed_count > 0:
            return False

        if self.sequence != button:
            return False

        # Can only hit when shield is down
        if self.shield_active:
            return False

        # Hit successful
        self._activate_letter(button)
        self.typed_count = 1
        self.completed = True
        return True

    def would_block_attack(self, button: str) -> bool:
        """Check if this enemy's shield would block an attack with the given button.

        Returns True if the button matches but shield is active.
        """
        if self.typed_count > 0:
            return False
        return self.sequence == button and self.shield_active

    def handle_blocked_attack(self, game_engine):
        """Handle a blocked attack - create shield absorption effect and disable player."""
        # Create laser that stops at shield
        if self.laser_manager:
            letter_item = self.letter_items[0]
            letter_pos = (letter_item.pos().x(), letter_item.pos().y())
            waveform_y = self.waveform.get_y_at_x(letter_pos[0]) if self.waveform else None
            # Create a "blocked" laser that stops at the shield
            self.laser_manager.create_laser(
                letter_pos, self.sequence, "blocked", waveform_y, shield_radius=self.shield_radius
            )

        # Brighten shield segments briefly to show absorption
        self._flash_shield()

        # Disable player
        game_engine.disable_player(0.3)

    def _flash_shield(self):
        """Flash the shield segments bright to show absorption."""
        color = BUTTON_COLORS.get(self.sequence, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        # Set shields to bright white momentarily
        for segment in self.shield_items:
            segment.setPen(pg.mkPen(color=(255, 255, 255, 255), width=8))

        # Create animation to restore original color (via update cycle)
        self.shield_flash_timer = 0.15

    def can_type_button(self, button: str) -> bool:
        """Check if this button can be typed on this enemy.

        Returns True if the button matches, even if shield is active.
        The shield blocking behavior is handled separately via would_block_attack.
        """
        if self.typed_count > 0:
            return False
        return self.sequence == button

    def reset_typing_progress(self):
        """Reset typing progress to the beginning.

        Single letter enemy - nothing to reset mid-sequence.
        """

    def _activate_letter(self, button: str):
        """Activate letter with effects."""
        button_color = BUTTON_COLORS.get(button, "#FFFFFF")
        letter_item = self.letter_items[0]
        letter_bg = self.letter_backgrounds[0]

        # Create laser
        if self.laser_manager:
            letter_pos = (letter_item.pos().x(), letter_item.pos().y())
            waveform_y = self.waveform.get_y_at_x(letter_pos[0]) if self.waveform else None
            self.laser_manager.create_laser(letter_pos, button, "normal", waveform_y)

        # Trigger waveform activity
        if self.waveform:
            letter_pos = (letter_item.pos().x(), letter_item.pos().y())
            self.waveform.add_letter_activity(letter_pos[0], intensity=0.4)

        # Ring effect
        letter_pos = (letter_item.pos().x(), letter_item.pos().y())
        ring_effect = EnemyLetterRingEffect(self.view, letter_pos, button_color)
        self.animations.append(ring_effect)

        # Brighten hexagon
        rgb = tuple(int(button_color[i : i + 2], 16) for i in (1, 3, 5))
        bright_rgb = tuple(min(255, int(c * 1.5)) for c in rgb)

        original_pen = letter_bg.opts["pen"]
        original_brush = letter_bg._fill.opts["brush"]

        letter_bg.setPen(pg.mkPen(color=(*bright_rgb, 255), width=8))
        letter_bg._fill.setBrush(pg.mkBrush(*bright_rgb, 200))

        flash_anim = HexagonFlashAnim(letter_bg, original_pen, original_brush, 0.2)
        self.animations.append(flash_anim)

        # Letter animation
        animation = LetterActivationAnim(letter_item, button)
        self.animations.append(animation)

    def update(self, dt: float):
        """Update enemy position, shield rotation, and animations."""
        # Update shield timing
        self.shield_time = (self.shield_time + dt) % self.shield_period

        # Update shield rotation
        self.shield_rotation = (self.shield_rotation + self.shield_rotation_speed * dt) % 360

        # Update shield flash timer
        if self.shield_flash_timer > 0:
            self.shield_flash_timer = max(0, self.shield_flash_timer - dt)

        # Move enemy downward
        effective_speed = self.speed * self.speed_multiplier
        letter_item = self.letter_items[0]
        letter_bg = self.letter_backgrounds[0]
        pos = letter_item.pos()
        new_x = pos.x()
        new_y = pos.y() - effective_speed * dt

        letter_item.setPos(new_x, new_y)
        self._move_hexagon(letter_bg, new_x, new_y)
        self._update_shield_visuals(new_x, new_y)

        # Update animations
        completed_animations = []
        for animation in self.animations:
            if not animation.update(dt):
                completed_animations.append(animation)

        for animation in completed_animations:
            self.animations.remove(animation)

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of enemy."""
        if not self.letter_items:
            return (0, 0)
        pos = self.letter_items[0].pos()
        return (pos.x(), pos.y())

    def get_width(self) -> float:
        """Get total width of enemy including shield."""
        return self.shield_radius * 2 + 20

    def is_complete(self) -> bool:
        """Check if enemy is completely typed."""
        return self.completed

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if enemy has moved below screen."""
        if not self.letter_items:
            return True
        return self.letter_items[0].pos().y() < bottom_y

    def _create_letter_hexagon(self, x, y, letter):
        """Create hexagon background for letter."""
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        size = 18
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        # Filled hexagon
        hexagon_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*rgb, 80),
            fillLevel="enclosed",
        )
        self.view.addItem(hexagon_fill)

        # Outline
        hexagon_outline = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=pg.mkPen(color=(*rgb, 255), width=3),
            brush=None,
        )
        self.view.addItem(hexagon_outline)

        hexagon_outline._fill = hexagon_fill
        return hexagon_outline

    def _move_hexagon(self, hexagon, x, y):
        """Move hexagon background to new position."""
        size = 18
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        pen = hexagon.opts.get("pen", pg.mkPen(color=(255, 255, 255), width=3))
        hexagon.setData(x=x_points, y=y_points, pen=pen)

        brush = hexagon._fill.opts.get("brush", pg.mkBrush(255, 255, 255, 80))
        hexagon._fill.setData(x=x_points, y=y_points, brush=brush)

    def cleanup(self):
        """Remove all visual elements."""
        for letter_item in self.letter_items:
            self.view.removeItem(letter_item)
        self.letter_items.clear()

        for hexagon in self.letter_backgrounds:
            self.view.removeItem(hexagon)
            self.view.removeItem(hexagon._fill)
        self.letter_backgrounds.clear()

        for shield_item in self.shield_items:
            self.view.removeItem(shield_item)
        self.shield_items.clear()

        for animation in self.animations:
            animation.cleanup()
        self.animations.clear()

    def has_active_animations(self) -> bool:
        """Check if enemy has active animations that need to complete."""
        return len(self.animations) > 0

    def update_animations(self, dt: float):
        """Update remaining animations (called after enemy is destroyed)."""
        completed = []
        for animation in self.animations:
            if not animation.update(dt):
                completed.append(animation)
        for animation in completed:
            self.animations.remove(animation)

    def get_destruction_info(self):
        """Get destruction info for shielded enemies."""
        return {
            "points": 20,  # Bonus points for timing challenge
            "explosion_type": "normal",
            "explosion_scale": 1.0,
            "shake_type": "enemy_destroyed",
        }

    def get_miss_info(self):
        """Get miss info for shielded enemies."""
        return {
            "damage": 0.25,
            "enemy_type_name": "Shielded enemy",
        }
