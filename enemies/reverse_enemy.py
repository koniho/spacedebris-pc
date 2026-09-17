"""Reverse enemy implementation - typed right-to-left with sweep indicator."""

from typing import List, Tuple
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from enemies.base_enemy import BaseEnemy
from enemies.letter_effects import (
    LetterActivationAnim,
    EnemyLetterRingEffect,
    HexagonFlashAnim,
    DisengageFlashAnim,
)
from config import BUTTON_COLORS, get_button_label
from font_manager import font_manager


class ReverseEnemy(BaseEnemy):
    """Enemy that must be typed right-to-left, indicated by reverse sweep effect."""

    # Typing direction for sweep effect (right-to-left)
    typing_left_to_right = False

    def __init__(
        self,
        sequence: str,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
    ):
        """Initialize reverse enemy."""
        super().__init__(view, laser_manager, waveform)
        # Store original sequence for typing (typed right-to-left)
        self.sequence = sequence
        # Display sequence is reversed (so rightmost letter is first to type)
        self.display_sequence = sequence[::-1]
        self.typed_count = 0

        # Speed similar to normal enemies
        base_speed = 150
        length_multiplier = max(0.4, 5.0 / len(sequence))
        self.speed = base_speed * length_multiplier

        self.letter_spacing = 30

        # Sweep effect state
        self.sweep_timer = -0.5  # Start negative to delay first sweep by 0.5 seconds
        self.sweep_period = 3.0  # Time between sweep triggers
        self.sweep_duration = 0.8  # Duration of the actual sweep animation

        # Create letter items
        self.letter_items: List[pg.TextItem] = []
        self.animations: List[LetterActivationAnim] = []
        self.letter_backgrounds = []

        # Position letters left-to-right but display reversed sequence
        start_x = pos[0] - (len(sequence) - 1) * self.letter_spacing / 2

        for i, letter in enumerate(self.display_sequence):
            x = start_x + i * self.letter_spacing
            y = pos[1]

            # Create hexagon background with reverse indicator (dashed outline)
            hexagon_bg = self._create_letter_hexagon(x, y, letter)
            self.letter_backgrounds.append(hexagon_bg)

            # Create normal (non-mirrored) text item
            text_item = pg.TextItem(
                text=get_button_label(letter),
                color=(255, 255, 255),
                anchor=(0.5, 0.5),
            )
            text_item.setFont(font_manager.get_enemy_letter_font(20, bold=True))
            text_item.setPos(x, y)
            self.view.addItem(text_item)
            self.letter_items.append(text_item)

    def type_button(self, button: str) -> bool:
        """Try to type a button. Returns True if successful."""
        if self.typed_count >= len(self.sequence):
            return False

        # Current letter to type is from the original sequence
        current_letter = self.sequence[self.typed_count]

        if current_letter == button:
            # Get the display index (reversed - rightmost first)
            display_index = len(self.sequence) - 1 - self.typed_count
            self._activate_letter(display_index, button)

            self.typed_count += 1

            if self.typed_count >= len(self.sequence):
                self.completed = True

            return True
        return False

    def can_type_button(self, button: str) -> bool:
        """Check if this button can be typed on this enemy."""
        if self.typed_count >= len(self.sequence):
            return False
        return self.sequence[self.typed_count] == button

    def reset_typing_progress(self):
        """Reset typing progress to the beginning."""
        # Capture the display index where typing stopped
        missed_display_index = (
            len(self.sequence) - 1 - self.typed_count if self.typed_count > 0 else None
        )
        self.typed_count = 0
        self._reset_letter_colors(missed_display_index)

    def _activate_letter(self, display_index: int, button: str):
        """Activate a letter with animation effects."""
        if 0 <= display_index < len(self.letter_items):
            letter_item = self.letter_items[display_index]
            letter_bg = self.letter_backgrounds[display_index]

            button_color = BUTTON_COLORS.get(button, "#FFFFFF")

            # Create laser if manager available
            if self.laser_manager:
                letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                waveform_y = self.waveform.get_y_at_x(letter_pos[0]) if self.waveform else None
                self.laser_manager.create_laser(letter_pos, button, "normal", waveform_y)

            # Trigger waveform activity
            if self.waveform:
                letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                self.waveform.add_letter_activity(letter_pos[0], intensity=0.4)

            # Create ring effect
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

            # Letter activation animation
            animation = LetterActivationAnim(letter_item, button)
            self.animations.append(animation)

    def _reset_letter_colors(self, missed_display_index=None):
        """Reset all letters back to original appearance."""
        for animation in self.animations:
            animation.cleanup()
        self.animations.clear()

        for letter_item in self.letter_items:
            font = font_manager.get_enemy_letter_font(20, bold=True)
            letter_item.setFont(font)
            letter_item.setColor((255, 255, 255))

        # Disengage flash on missed letter
        if missed_display_index is not None and 0 <= missed_display_index < len(
            self.letter_backgrounds
        ):
            hexagon = self.letter_backgrounds[missed_display_index]
            flash_anim = DisengageFlashAnim(hexagon)
            self.animations.append(flash_anim)

    def update(self, dt: float):
        """Update enemy position and animations."""
        effective_speed = self.speed * self.speed_multiplier
        for letter_item, hexagon_bg in zip(self.letter_items, self.letter_backgrounds):
            pos = letter_item.pos()
            new_y = pos.y() - effective_speed * dt
            letter_item.setPos(pos.x(), new_y)
            self._move_hexagon(hexagon_bg, pos.x(), new_y)

        # Update sweep effect
        self._update_sweep_effect(dt)

        # Update animations
        completed_animations = []
        for animation in self.animations:
            if not animation.update(dt):
                completed_animations.append(animation)

        for animation in completed_animations:
            self.animations.remove(animation)

    def _update_sweep_effect(self, dt: float):
        """Update the pulsing sweep effect across untyped letters (right-to-left)."""
        self.sweep_timer += dt

        # Don't start sweep until timer is positive (0.5s delay)
        if self.sweep_timer < 0:
            return

        # Number of untyped letters
        untyped_count = len(self.sequence) - self.typed_count
        if untyped_count <= 0:
            return

        # Calculate time within current period
        time_in_period = self.sweep_timer % self.sweep_period

        # For reverse enemy, we iterate over display indices
        # Untyped letters are at display indices 0 to (len-1-typed_count)
        for display_idx in range(len(self.sequence) - self.typed_count):
            hexagon = self.letter_backgrounds[display_idx]
            letter = self.display_sequence[display_idx]

            # Calculate staggered start time for this letter
            # For reverse typing, rightmost letter (highest display_idx) starts first
            # letter_index 0 = rightmost (first to type), letter_index n-1 = leftmost (last)
            letter_index = untyped_count - 1 - display_idx

            # Stagger: each letter starts 0.33 * single_letter_duration after previous
            single_letter_duration = self.sweep_duration / max(1, untyped_count)
            stagger_offset = 0.33 * single_letter_duration
            letter_start_time = letter_index * stagger_offset

            # Calculate this letter's progress within its highlight window
            letter_time = time_in_period - letter_start_time

            # Glow intensity based on letter's individual timing
            if letter_time < 0 or letter_time > single_letter_duration:
                glow_intensity = 0.0
            else:
                # Smooth rise and fall within the letter's duration
                letter_progress = letter_time / single_letter_duration
                # Use sine curve for smooth pulse (0 -> 1 -> 0)
                glow_intensity = np.sin(letter_progress * np.pi)

            # Get base color
            color = BUTTON_COLORS.get(letter, "#FFFFFF")
            rgb = tuple(int(color[idx : idx + 2], 16) for idx in (1, 3, 5))

            # Apply glow
            glow_factor = 1.0 + 0.5 * glow_intensity
            glowed_rgb = tuple(min(255, int(c * glow_factor)) for c in rgb)

            # Update hexagon appearance with glow (keep dashed style)
            alpha = int(255 * (0.8 + 0.2 * glow_intensity))
            fill_alpha = int(80 + 120 * glow_intensity)
            width = int(3 + 2 * glow_intensity)

            hexagon.setPen(pg.mkPen(color=(*glowed_rgb, alpha), width=width, style=Qt.DashLine))
            hexagon._fill.setBrush(pg.mkBrush(*glowed_rgb, fill_alpha))

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of enemy."""
        if not self.letter_items:
            return (0, 0)

        total_x = sum(item.pos().x() for item in self.letter_items)
        total_y = sum(item.pos().y() for item in self.letter_items)
        count = len(self.letter_items)

        return (total_x / count, total_y / count)

    def get_next_letter_position(self) -> Tuple[float, float]:
        """Get position of the next letter to type (rightmost untyped)."""
        if not self.letter_items or self.typed_count >= len(self.letter_items):
            return self.get_center_position()

        # For reverse enemy, next letter is at display index (len - 1 - typed_count)
        display_index = len(self.sequence) - 1 - self.typed_count
        letter_item = self.letter_items[display_index]
        return (letter_item.pos().x(), letter_item.pos().y())

    def get_width(self) -> float:
        """Get total width of enemy including spacing."""
        return (len(self.sequence) - 1) * self.letter_spacing + 40

    def is_complete(self) -> bool:
        """Check if enemy is completely typed."""
        return self.completed

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if enemy has moved below screen."""
        if not self.letter_items:
            return True
        highest_y = max(item.pos().y() for item in self.letter_items)
        return highest_y < bottom_y

    def _create_letter_hexagon(self, x, y, letter):
        """Create hexagon background for letter with reverse indicator."""
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        # Create hexagon points
        size = 18
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        # Create filled hexagon
        hexagon_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*rgb, 80),
            fillLevel="enclosed",
        )
        self.view.addItem(hexagon_fill)

        # Create outline - dashed to indicate reverse
        hexagon_outline = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=pg.mkPen(color=(*rgb, 255), width=3, style=Qt.DashLine),
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
        """Get destruction info for reverse enemies."""
        return {
            "points": len(self.sequence) * 12,  # Slightly more points for cognitive challenge
            "explosion_type": "normal",
            "explosion_scale": 1.0,
            "shake_type": "enemy_destroyed",
        }

    def get_miss_info(self):
        """Get miss info for reverse enemies."""
        return {
            "damage": 0.25,
            "enemy_type_name": "Reverse enemy",
        }
