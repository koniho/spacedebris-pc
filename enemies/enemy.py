"""Standard enemy class implementation."""

from typing import List, Tuple
import numpy as np
import pyqtgraph as pg
from enemies.base_enemy import BaseEnemy
from enemies.letter_effects import (
    LetterActivationAnim,
    EnemyLetterRingEffect,
    HexagonFlashAnim,
    DisengageFlashAnim,
)
from config import BUTTON_COLORS, get_button_label, get_letter_spacing_for_sequence
from font_manager import font_manager


class Enemy(BaseEnemy):
    """Single enemy with typing sequence."""

    # Typing direction for sweep effect (True = left-to-right, False = right-to-left)
    typing_left_to_right = True

    def __init__(
        self,
        sequence: str,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
    ):
        """Initialize enemy."""
        super().__init__(view, laser_manager, waveform)
        self.sequence = sequence
        self.typed_count = 0

        # Speed based on sequence length - shorter enemies move much faster
        base_speed = 150  # 50 * 3 = 150
        length_multiplier = max(
            0.4, 5.0 / len(sequence)
        )  # 2-letter = 2.5x speed, 3-letter = 1.67x, 4-letter = 1.25x, 6-letter = 0.83x, 8+ = 0.4x
        self.speed = base_speed * length_multiplier

        self.letter_spacing = get_letter_spacing_for_sequence(sequence)

        # Sweep effect state
        self.sweep_timer = -0.5  # Start negative to delay first sweep by 0.5 seconds
        self.sweep_period = 3.0  # Time between sweep triggers
        self.sweep_duration = 0.8  # Duration of the actual sweep animation

        # Create letter items
        self.letter_items: List[pg.TextItem] = []
        self.animations: List[LetterActivationAnim] = []

        start_x = pos[0] - (len(sequence) - 1) * self.letter_spacing / 2
        self.letter_backgrounds = []  # Store hexagon backgrounds

        for i, letter in enumerate(sequence):
            x = start_x + i * self.letter_spacing
            y = pos[1]

            # Create hexagon background
            hexagon_bg = self._create_letter_hexagon(x, y, letter)
            self.letter_backgrounds.append(hexagon_bg)

            # Create text item
            text_item = pg.TextItem(
                text=get_button_label(letter),
                color=(255, 255, 255),
                anchor=(0.5, 0.5),  # White text for visibility
            )
            text_item.setFont(font_manager.get_enemy_letter_font(20, bold=True))
            text_item.setPos(x, y)
            self.view.addItem(text_item)
            self.letter_items.append(text_item)

    def type_button(self, button: str) -> bool:
        """Try to type a button. Returns True if successful."""
        if self.typed_count < len(self.sequence) and self.sequence[self.typed_count] == button:
            self.activate_letter(self.typed_count)
            self.typed_count += 1

            if self.typed_count >= len(self.sequence):
                self.completed = True

            return True
        return False

    def can_type_button(self, button: str) -> bool:
        """Check if this button can be typed on this enemy."""
        return self.typed_count < len(self.sequence) and self.sequence[self.typed_count] == button

    def reset_typing_progress(self):
        """Reset typing progress to the beginning."""
        # Capture the letter index where typing stopped (for disengage animation)
        missed_index = self.typed_count
        self.typed_count = 0
        self._reset_letter_colors(missed_index)

    def activate_letter(self, index: int):
        """Activate a letter with animation, laser, and intro-style effects."""
        if 0 <= index < len(self.letter_items):
            letter_item = self.letter_items[index]
            letter_bg = self.letter_backgrounds[index]
            button = self.sequence[index]

            # Get button color for consistent theming
            button_color = BUTTON_COLORS.get(button, "#FFFFFF")

            # Create laser if manager available
            if self.laser_manager:
                letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                # Get actual waveform Y at the laser's X position
                waveform_y = self.waveform.get_y_at_x(letter_pos[0]) if self.waveform else None
                self.laser_manager.create_laser(letter_pos, button, "normal", waveform_y)

            # Trigger waveform activity for this letter
            if self.waveform:
                letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                self.waveform.add_letter_activity(letter_pos[0], intensity=0.4)

            # Create expanding ring effect (intro screen style)
            letter_pos = (letter_item.pos().x(), letter_item.pos().y())
            ring_effect = EnemyLetterRingEffect(self.view, letter_pos, button_color)
            self.animations.append(ring_effect)

            # Brighten and enlarge hexagon temporarily (intro screen style)
            rgb = tuple(int(button_color[i : i + 2], 16) for i in (1, 3, 5))
            bright_rgb = tuple(min(255, int(c * 1.5)) for c in rgb)  # Brighten

            # Store original properties to restore later
            original_pen = letter_bg.opts["pen"]
            original_brush = letter_bg._fill.opts["brush"]

            # Apply bright effect
            letter_bg.setPen(pg.mkPen(color=(*bright_rgb, 255), width=8))  # Thicker outline
            letter_bg._fill.setBrush(pg.mkBrush(*bright_rgb, 200))

            # Create hexagon flash animation to restore original appearance
            flash_anim = HexagonFlashAnim(letter_bg, original_pen, original_brush, 0.2)
            self.animations.append(flash_anim)

            # Create activation animation for the letter text
            animation = LetterActivationAnim(letter_item, button)
            self.animations.append(animation)

    def update(self, dt: float):
        """Update enemy position and animations."""
        # Move all letters and backgrounds downward with speed multiplier
        effective_speed = self.speed * self.speed_multiplier
        for letter_item, hexagon_bg in zip(self.letter_items, self.letter_backgrounds):
            pos = letter_item.pos()
            new_y = pos.y() - effective_speed * dt
            letter_item.setPos(pos.x(), new_y)

            # Move hexagon background
            self._move_hexagon(hexagon_bg, pos.x(), new_y)

        # Update sweep effect
        self._update_sweep_effect(dt)

        # Update animations
        completed_animations = []
        for animation in self.animations:
            if not animation.update(dt):
                completed_animations.append(animation)

        # Remove completed animations
        for animation in completed_animations:
            self.animations.remove(animation)

    def _update_sweep_effect(self, dt: float):
        """Update the pulsing sweep effect across untyped letters."""
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

        # Apply sweep glow to untyped hexagons
        for i in range(self.typed_count, len(self.sequence)):
            # Guard against mismatched lengths
            if i >= len(self.letter_backgrounds):
                break
            hexagon = self.letter_backgrounds[i]
            letter = self.sequence[i]

            # Calculate staggered start time for this letter
            # Each letter starts when previous is 33% complete
            untyped_index = i - self.typed_count
            if self.typing_left_to_right:
                letter_index = untyped_index
            else:
                # Reverse direction - rightmost letter starts first
                letter_index = untyped_count - 1 - untyped_index

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

            # Apply glow - brighten based on intensity
            glow_factor = 1.0 + 0.5 * glow_intensity
            glowed_rgb = tuple(min(255, int(c * glow_factor)) for c in rgb)

            # Update hexagon appearance with glow
            alpha = int(255 * (0.8 + 0.2 * glow_intensity))
            fill_alpha = int(80 + 120 * glow_intensity)
            width = int(3 + 2 * glow_intensity)

            hexagon.setPen(pg.mkPen(color=(*glowed_rgb, alpha), width=width))
            hexagon._fill.setBrush(pg.mkBrush(*glowed_rgb, fill_alpha))

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of enemy."""
        if not self.letter_items:
            return (0, 0)

        # Calculate center of all letters
        total_x = sum(item.pos().x() for item in self.letter_items)
        total_y = sum(item.pos().y() for item in self.letter_items)
        count = len(self.letter_items)

        return (total_x / count, total_y / count)

    def get_next_letter_position(self) -> Tuple[float, float]:
        """Get position of the next letter to type."""
        if not self.letter_items or self.typed_count >= len(self.letter_items):
            return self.get_center_position()

        letter_item = self.letter_items[self.typed_count]
        return (letter_item.pos().x(), letter_item.pos().y())

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box of enemy (left, right, top, bottom)."""
        if not self.letter_items:
            return (0, 0, 0, 0)

        positions = [(item.pos().x(), item.pos().y()) for item in self.letter_items]
        xs, ys = zip(*positions)

        # Add padding for letter size
        padding = 20
        left = min(xs) - padding
        right = max(xs) + padding
        top = max(ys) + padding
        bottom = min(ys) - padding

        return (left, right, top, bottom)

    def get_width(self) -> float:
        """Get total width of enemy including spacing."""
        return (len(self.sequence) - 1) * self.letter_spacing + 40  # 40 for letter width + padding

    def is_complete(self) -> bool:
        """Check if enemy is completely typed."""
        return self.completed

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if enemy has moved below screen."""
        if not self.letter_items:
            return True

        highest_y = max(item.pos().y() for item in self.letter_items)
        return highest_y < bottom_y

    def _reset_letter_colors(self, missed_index=None):
        """Reset all letters back to original white color and normal size.

        Args:
            missed_index: Index of the letter where typing stopped (for disengage animation).
                         If provided and > 0, shows a yellow flash on that letter.
        """
        # Clear all active animations since we're resetting
        # Clean up all active animations before clearing the list
        for animation in self.animations:
            animation.cleanup()
        self.animations.clear()

        # Reset ALL letters to original state, regardless of their current state
        # This ensures both active and completed animations are properly reset
        for i, letter_item in enumerate(self.letter_items):
            letter = self.sequence[i]

            # Force reset to original appearance - use the same setup as creation
            font = font_manager.get_enemy_letter_font(20, bold=True)
            letter_item.setFont(font)

            # Reset text and color — use setPlainText to clear any stale HTML,
            # then setColor which works now that LetterActivationAnim uses setColor too
            letter_item.textItem.setPlainText(get_button_label(letter))
            letter_item.updateTextPos()
            letter_item.setColor((255, 255, 255))

        # Create disengage flash animation on the missed letter's hexagon
        # Only if there was actual typing progress (missed_index > 0)
        if (
            missed_index is not None
            and missed_index > 0
            and missed_index < len(self.letter_backgrounds)
        ):
            hexagon = self.letter_backgrounds[missed_index]
            flash_anim = DisengageFlashAnim(hexagon)
            self.animations.append(flash_anim)

    def cleanup(self):
        """Remove all visual elements."""
        for letter_item in self.letter_items:
            self.view.removeItem(letter_item)
        self.letter_items.clear()

        # Clean up hexagon backgrounds
        for hexagon in self.letter_backgrounds:
            self.view.removeItem(hexagon)
            self.view.removeItem(hexagon._fill)
        self.letter_backgrounds.clear()

        # Clean up all animations
        for animation in self.animations:
            animation.cleanup()
        self.animations.clear()

    def has_active_animations(self) -> bool:
        """Check if enemy has active ring effect animations that need to complete."""
        return len(self.animations) > 0

    def update_animations(self, dt: float):
        """Update remaining animations (called after enemy is destroyed)."""
        completed = []
        for animation in self.animations:
            if not animation.update(dt):
                completed.append(animation)
        for animation in completed:
            self.animations.remove(animation)

    def _create_letter_hexagon(self, x, y, letter):
        """Create hexagon background for letter."""
        # Get button color
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        # Create hexagon points
        size = 18
        angles = np.linspace(0, 2 * np.pi, 7)  # 7 points for closed hexagon
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        # Create filled hexagon with gradient
        hexagon_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*rgb, 80),  # Semi-transparent fill
            fillLevel="enclosed",
        )
        self.view.addItem(hexagon_fill)

        # Create outline
        hexagon_outline = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=pg.mkPen(color=(*rgb, 255), width=3), brush=None
        )
        self.view.addItem(hexagon_outline)

        # Store both components together
        hexagon_outline._fill = hexagon_fill
        return hexagon_outline

    def _move_hexagon(self, hexagon, x, y):
        """Move hexagon background to new position."""
        # Recreate hexagon points at new position
        size = 18
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        # Update outline position
        pen = hexagon.opts.get("pen", pg.mkPen(color=(255, 255, 255), width=3))
        hexagon.setData(x=x_points, y=y_points, pen=pen)

        # Update fill position
        brush = hexagon._fill.opts.get("brush", pg.mkBrush(255, 255, 255, 80))
        hexagon._fill.setData(x=x_points, y=y_points, brush=brush)
