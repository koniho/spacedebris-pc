"""Rapid hit enemy implementation - requires multiple hits per letter."""

import random_manager
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
from config import BUTTON_COLORS, get_button_label
from font_manager import font_manager


class RapidHitEnemy(BaseEnemy):
    """Enemy that requires rapid repeated hits on letters."""

    def __init__(
        self,
        sequence: str,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
        hit_count=None,
        max_hit_count=9,
    ):
        """Initialize rapid-hit enemy."""
        super().__init__(view, laser_manager, waveform)
        self.sequence = sequence
        self.current_letter_index = 0

        # Use custom hit count or generate random counts based on max_hit_count
        # Min is always 2, max is configurable by difficulty
        min_hits = 2
        if hit_count is not None:
            self.hit_counts_required = [hit_count for _ in sequence]
        else:
            self.hit_counts_required = [
                random_manager.randint(min_hits, max_hit_count) for _ in sequence
            ]
        self.hit_counts_remaining = self.hit_counts_required.copy()

        # Speed based on sequence length - 3x faster than before
        base_speed = 120  # 3x faster (was 40)
        length_multiplier = max(0.3, 2.0 / len(sequence))
        self.speed = base_speed * length_multiplier

        self.letter_spacing = 40  # Wider spacing for visibility
        self.letter_items: List[pg.TextItem] = []
        self.count_items: List[pg.TextItem] = []  # Display remaining hit counts
        self.letter_backgrounds = []
        self.animations: List[LetterActivationAnim] = []

        # Create visual elements
        start_x = pos[0] - (len(sequence) - 1) * self.letter_spacing / 2

        for i, letter in enumerate(sequence):
            x = start_x + i * self.letter_spacing
            y = pos[1]

            # Create hexagon background (larger for rapid hit enemies)
            hexagon_bg = self._create_letter_hexagon(x, y, letter)
            self.letter_backgrounds.append(hexagon_bg)

            # Create letter text item
            letter_item = pg.TextItem(
                text=get_button_label(letter), color=(255, 255, 255), anchor=(0.5, 0.5)
            )
            letter_item.setFont(font_manager.get_enemy_letter_font(24, bold=True))
            letter_item.setPos(x, y)
            self.view.addItem(letter_item)
            self.letter_items.append(letter_item)

            # Create count text item (shows remaining hits)
            count_item = pg.TextItem(
                text=str(self.hit_counts_remaining[i]),
                color=(255, 255, 100),  # Yellow for count
                anchor=(0.5, 0.5),
            )
            count_item.setFont(font_manager.get_enemy_letter_font(14, bold=True))
            count_item.setPos(x, y - 25)  # Above the letter
            self.view.addItem(count_item)
            self.count_items.append(count_item)

        # Highlight current letter
        self._update_letter_highlights()

    def type_button(self, button: str) -> bool:
        """Try to type a button. Returns True if successful."""
        if self.current_letter_index >= len(self.sequence):
            return False

        current_letter = self.sequence[self.current_letter_index]

        if current_letter == button:
            # Re-apply highlights when successfully typing (in case we were disengaged)
            self._update_letter_highlights()
            # Decrease hit count for current letter
            self.hit_counts_remaining[self.current_letter_index] -= 1

            # Update count display
            self.count_items[self.current_letter_index].setText(
                str(self.hit_counts_remaining[self.current_letter_index])
            )

            # Create laser effect if manager available
            if self.laser_manager:
                letter_pos = self.letter_items[self.current_letter_index].pos()
                laser_pos = (letter_pos.x(), letter_pos.y())
                # Get actual waveform Y at the laser's X position
                waveform_y = self.waveform.get_y_at_x(laser_pos[0]) if self.waveform else None
                self.laser_manager.create_laser(laser_pos, button, "enhanced", waveform_y)

            # Trigger waveform activity
            if self.waveform:
                letter_pos = self.letter_items[self.current_letter_index].pos()
                self.waveform.add_letter_activity(letter_pos.x(), intensity=0.3)

            # Add intro-style effects for rapid hit letters
            letter_item = self.letter_items[self.current_letter_index]
            letter_bg = self.letter_backgrounds[self.current_letter_index]

            # Get button color for consistent theming
            button_color = BUTTON_COLORS.get(button, "#FFFFFF")

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

            # Create rapid-hit animation effect
            animation = LetterActivationAnim(self.letter_items[self.current_letter_index], button)
            self.animations.append(animation)

            # Check if this letter is complete
            if self.hit_counts_remaining[self.current_letter_index] <= 0:
                # Move to next letter
                self.current_letter_index += 1

                # Check if entire sequence is complete
                if self.current_letter_index >= len(self.sequence):
                    self.completed = True
                else:
                    # Update highlights for next letter
                    self._update_letter_highlights()

            return True

        return False

    def can_type_button(self, button: str) -> bool:
        """Check if this button can be typed on this enemy."""
        if self.current_letter_index >= len(self.sequence):
            return False
        return self.sequence[self.current_letter_index] == button

    def reset_typing_progress(self):
        """Reset typing progress to the beginning."""
        # Capture the letter index where typing stopped (for disengage animation)
        missed_index = self.current_letter_index
        self.current_letter_index = 0
        self.hit_counts_remaining = self.hit_counts_required.copy()

        # Reset count displays
        for i, count_item in enumerate(self.count_items):
            count_item.setText(str(self.hit_counts_remaining[i]))

        # Reset letter colors to white (for disengagement)
        # Do NOT call _update_letter_highlights() here as that would re-apply colors
        self._reset_letter_colors(missed_index)

    def _update_letter_highlights(self):
        """Update visual highlights for current letter."""
        # Reset all letters to normal appearance
        for i, (letter_item, count_item) in enumerate(zip(self.letter_items, self.count_items)):
            letter = self.sequence[i]
            label = get_button_label(letter)
            if i < self.current_letter_index:
                # Completed letters - green
                letter_item.setHtml(f'<span style="color:#64FF64">{label}</span>')
                count_item.setColor((100, 255, 100))
            elif i == self.current_letter_index:
                # Current letter - bright white/yellow
                letter_item.setHtml(f'<span style="color:#FFFFFF">{label}</span>')
                count_item.setColor((255, 255, 100))
            else:
                # Future letters - dim
                letter_item.setHtml(f'<span style="color:#969696">{label}</span>')
                count_item.setColor((150, 150, 100))

    def _reset_letter_colors(self, missed_index=None):
        """Reset all letters back to original white color.

        Args:
            missed_index: Index of the letter where typing stopped (for disengage animation).
                         If provided and > 0, shows a yellow flash on that letter.
        """
        # Clean up all active animations before clearing the list
        for animation in self.animations:
            animation.cleanup()
        self.animations.clear()
        for i, letter_item in enumerate(self.letter_items):
            letter = self.sequence[i]
            font = font_manager.get_enemy_letter_font(24, bold=True)
            letter_item.setFont(font)
            # CRITICAL: Use setHtml with white color to override any previous HTML formatting
            # This ensures we clear any color set by animations
            letter_item.setHtml(f'<span style="color:#FFFFFF">{get_button_label(letter)}</span>')
        # Also reset count item colors to yellow (neutral state)
        for count_item in self.count_items:
            count_item.setColor((255, 255, 100))

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

    def update(self, dt: float):
        """Update enemy position and animations."""
        # Move all letters and backgrounds downward
        effective_speed = self.speed * self.speed_multiplier
        for letter_item, count_item, hexagon_bg in zip(
            self.letter_items, self.count_items, self.letter_backgrounds
        ):
            pos = letter_item.pos()
            new_y = pos.y() - effective_speed * dt
            letter_item.setPos(pos.x(), new_y)

            # Move count item
            count_pos = count_item.pos()
            count_item.setPos(count_pos.x(), count_pos.y() - effective_speed * dt)

            # Move hexagon background
            self._move_hexagon(hexagon_bg, pos.x(), new_y)

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

        total_x = sum(item.pos().x() for item in self.letter_items)
        total_y = sum(item.pos().y() for item in self.letter_items)
        count = len(self.letter_items)

        return (total_x / count, total_y / count)

    def get_width(self) -> float:
        """Get total width of enemy including spacing."""
        return (len(self.sequence) - 1) * self.letter_spacing + 50

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
        """Create hexagon background for letter (larger for rapid hit)."""
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        # Larger hexagon for rapid hit enemies
        size = 22
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        # Create filled hexagon
        hexagon_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*rgb, 100),  # More opaque for visibility
            fillLevel="enclosed",
        )
        self.view.addItem(hexagon_fill)

        # Create outline with special pattern for rapid hit
        hexagon_outline = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=pg.mkPen(color=(*rgb, 255), width=4), brush=None
        )
        self.view.addItem(hexagon_outline)

        hexagon_outline._fill = hexagon_fill
        return hexagon_outline

    def _move_hexagon(self, hexagon, x, y):
        """Move hexagon background to new position."""
        size = 22
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        pen = hexagon.opts.get("pen", pg.mkPen(color=(255, 255, 255), width=4))
        hexagon.setData(x=x_points, y=y_points, pen=pen)

        brush = hexagon._fill.opts.get("brush", pg.mkBrush(255, 255, 255, 100))
        hexagon._fill.setData(x=x_points, y=y_points, brush=brush)

    def cleanup(self):
        """Remove all visual elements."""
        for letter_item in self.letter_items:
            self.view.removeItem(letter_item)
        self.letter_items.clear()

        for count_item in self.count_items:
            self.view.removeItem(count_item)
        self.count_items.clear()

        for hexagon in self.letter_backgrounds:
            self.view.removeItem(hexagon)
            self.view.removeItem(hexagon._fill)
        self.letter_backgrounds.clear()

        # Clean up all active animations before clearing the list
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
        """Get destruction info for rapid hit enemies."""
        base_points = len(self.sequence) * 15  # More points than normal enemies
        hit_bonus = sum(self.hit_counts_required) * 2  # Bonus for total hits required
        return {
            "points": base_points + hit_bonus,
            "explosion_type": "enhanced",
            "explosion_scale": 1.2,
            "shake_type": "medium",
        }

    def get_miss_info(self):
        """Get miss info for rapid hit enemies."""
        return {
            "damage": 0.25,  # Same damage as normal enemies
            "enemy_type_name": "Rapid hit enemy",
        }
