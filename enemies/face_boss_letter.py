"""Single letter enemy for FaceBoss word segments and projectiles."""

import math
from typing import Tuple

import pyqtgraph as pg
from PyQt5.QtCore import Qt

from config import BUTTON_COLORS
from enemies.enemy import Enemy


class FaceBossLetter(Enemy):
    """Single character enemy that slides horizontally instead of falling."""

    def __init__(
        self,
        letter: str,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
    ):
        """Initialize single letter enemy."""
        super().__init__(letter, pos, view, laser_manager, waveform)
        self.speed = 0  # Don't move downward

        # Set high z-values so letters appear above face curves (which are z=3-8)
        for letter_item in self.letter_items:
            letter_item.setZValue(20)
        for hexagon in self.letter_backgrounds:
            hexagon.setZValue(18)
            # pylint: disable=protected-access
            hexagon._fill.setZValue(17)

        # Horizontal slide animation state
        self.target_x = pos[0]
        self.slide_velocity = 0.0  # Horizontal velocity for slide-out
        self.opacity = 1.0
        self.fading_out = False

        # Yellow flash animation state (for miss feedback)
        self.yellow_flash_factor = 0.0  # 0 = normal color, 1 = full yellow
        self.yellow_flash_flashing_in = False  # True = fading to yellow, False = fading back
        self.yellow_flash_active = False

        # Highlight state (for showing next letter to type)
        self.highlighted = False
        self.highlight_pulse_timer = 0.0

        # Typing direction (False = right-to-left, uses dashed style)
        self.typing_left_to_right = True

    def _get_pen_style(self):
        """Get pen style based on typing direction (dashed for right-to-left)."""
        return Qt.SolidLine if self.typing_left_to_right else Qt.DashLine

    def set_typing_direction(self, left_to_right: bool):
        """Set typing direction and update hexagon style accordingly."""
        self.typing_left_to_right = left_to_right
        # Update hexagon style immediately
        if self.letter_backgrounds:
            hexagon = self.letter_backgrounds[0]
            letter = self.sequence[0]
            color = BUTTON_COLORS.get(letter, "#FFFFFF")
            rgb = tuple(int(color[idx : idx + 2], 16) for idx in (1, 3, 5))
            alpha = int(255 * self.opacity)
            hexagon.setPen(pg.mkPen(color=(*rgb, alpha), width=3, style=self._get_pen_style()))

    def set_highlighted(self, highlighted: bool):
        """Set whether this letter is highlighted as the next to type."""
        self.highlighted = highlighted
        if highlighted:
            self.highlight_pulse_timer = 0.0

    def start_yellow_flash(self):
        """Start yellow flash animation on this letter's hexagon."""
        self.yellow_flash_active = True
        self.yellow_flash_flashing_in = True
        self.yellow_flash_factor = 0.0

    def end_yellow_flash(self):
        """Start fading the yellow flash back to normal color."""
        if self.yellow_flash_active:
            self.yellow_flash_flashing_in = False

    def _update_yellow_flash(self, dt: float):
        """Update yellow flash animation state."""
        if not self.yellow_flash_active:
            return

        flash_speed = 4.0  # Speed of color transition

        if self.yellow_flash_flashing_in:
            # Fade to yellow
            self.yellow_flash_factor = min(1.0, self.yellow_flash_factor + dt * flash_speed)
        else:
            # Fade back to normal
            self.yellow_flash_factor = max(0.0, self.yellow_flash_factor - dt * flash_speed)
            if self.yellow_flash_factor <= 0:
                self.yellow_flash_active = False

        # Apply the color change to hexagon
        self._apply_yellow_flash_color()

    def _apply_yellow_flash_color(self):
        """Apply interpolated color between original and yellow to hexagon."""
        if not self.letter_backgrounds:
            return

        hexagon = self.letter_backgrounds[0]
        letter = self.sequence[0]

        # Get original color
        original_color = BUTTON_COLORS.get(letter, "#FFFFFF")
        original_rgb = tuple(int(original_color[idx : idx + 2], 16) for idx in (1, 3, 5))

        # Yellow target color
        yellow_rgb = (255, 255, 0)

        # Interpolate between original and yellow
        factor = self.yellow_flash_factor
        interpolated_rgb = tuple(
            int(original_rgb[i] + (yellow_rgb[i] - original_rgb[i]) * factor) for i in range(3)
        )

        # Apply interpolated alpha based on current opacity
        alpha = int(255 * self.opacity)

        # Update hexagon colors (use dashed style for right-to-left typing)
        hexagon.setPen(pg.mkPen(color=(*interpolated_rgb, alpha), width=3, style=self._get_pen_style()))
        # pylint: disable=protected-access
        hexagon._fill.setBrush(pg.mkBrush(*interpolated_rgb, alpha // 3))

    def set_target_position(self, target_x: float, target_y: float):
        """Set the target position for this letter to smoothly move toward."""
        self.target_x = target_x
        self.target_y = target_y

    def start_slide_out(self, velocity: float = -200):
        """Start sliding out horizontally and fading."""
        self.slide_velocity = velocity
        self.fading_out = True

    def type_button(self, button: str) -> bool:
        """Override to not set completed=True - let fade animation handle that."""
        if self.typed_count < len(self.sequence) and self.sequence[self.typed_count] == button:
            self.activate_letter(self.typed_count)
            self.typed_count += 1
            # Don't set self.completed = True here - fade animation will do it
            return True
        return False

    def update(self, dt: float):
        """Update letter position with horizontal slide behavior."""
        if not self.letter_items:
            return

        current_pos = self.letter_items[0].pos()
        current_x = current_pos.x()
        current_y = current_pos.y()

        if self.fading_out:
            # Apply slide velocity
            new_x = current_x + self.slide_velocity * dt
            new_y = current_y  # Keep Y position stable while fading
            self.opacity = max(0, self.opacity - dt * 3)

            # Update visual opacity
            self._update_opacity()

            # Mark complete when faded out
            if self.opacity <= 0:
                self.completed = True
        else:
            # Smoothly interpolate toward target position
            new_x = current_x + (self.target_x - current_x) * dt * 10
            new_y = current_y + (self.target_y - current_y) * dt * 10

        # Update position
        self.letter_items[0].setPos(new_x, new_y)
        self._move_hexagon(self.letter_backgrounds[0], new_x, new_y)

        # Update yellow flash animation
        self._update_yellow_flash(dt)

        # Update highlight pulse
        self._update_highlight(dt)

        # Update animations
        completed_animations = []
        for animation in self.animations:
            if not animation.update(dt):
                completed_animations.append(animation)

        for animation in completed_animations:
            self.animations.remove(animation)

    def _update_opacity(self):
        """Update visual opacity of letter and hexagon."""
        alpha = int(255 * self.opacity)

        # Update hexagon
        hexagon = self.letter_backgrounds[0]
        letter = self.sequence[0]

        # Get original color
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[idx : idx + 2], 16) for idx in (1, 3, 5))

        # Update pen and brush with new alpha (use dashed style for right-to-left typing)
        hexagon.setPen(pg.mkPen(color=(*rgb, alpha), width=3, style=self._get_pen_style()))
        # pylint: disable=protected-access
        hexagon._fill.setBrush(pg.mkBrush(*rgb, alpha // 3))

        # Update letter text opacity
        letter_item = self.letter_items[0]
        letter_item.setOpacity(self.opacity)

    def _update_highlight(self, dt: float):
        """Update highlight pulse effect for active letter."""
        if not self.highlighted or self.fading_out:
            return

        self.highlight_pulse_timer += dt
        # Pulse between 0.5 and 1.0 brightness at 3Hz
        pulse = 0.75 + 0.25 * math.sin(self.highlight_pulse_timer * 6 * math.pi)

        if not self.letter_backgrounds:
            return

        hexagon = self.letter_backgrounds[0]
        letter = self.sequence[0]

        # Get original color and brighten it
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[idx : idx + 2], 16) for idx in (1, 3, 5))

        # Brighten based on pulse
        bright_rgb = tuple(min(255, int(c_val * (0.8 + 0.4 * pulse))) for c_val in rgb)

        alpha = int(255 * self.opacity)
        # Thicker outline when highlighted (use dashed style for right-to-left typing)
        hexagon.setPen(pg.mkPen(color=(*bright_rgb, alpha), width=5, style=self._get_pen_style()))
        # pylint: disable=protected-access
        hexagon._fill.setBrush(pg.mkBrush(*bright_rgb, int(alpha * 0.5 * pulse)))

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of this letter."""
        if not self.letter_items:
            return (0, 0)
        pos = self.letter_items[0].pos()
        return (pos.x(), pos.y())


class FaceBossProjectile(Enemy):
    """Projectile enemy fired by FaceBoss - moves in a specific direction."""

    def __init__(
        self,
        letter: str,
        pos: Tuple[float, float],
        velocity: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
        damage: float = 0.05,
    ):
        """Initialize projectile enemy.

        Args:
            letter: Single character for this projectile
            pos: Starting position (x, y)
            velocity: Movement velocity (vx, vy) in units per second
            view: PyQtGraph view to add visuals to
            laser_manager: Optional laser manager for effects
            waveform: Optional player waveform reference
            damage: Damage to deal on hit (default 0.05 = 5%)
        """
        super().__init__(letter, pos, view, laser_manager, waveform)
        self.speed = 0  # Don't use standard downward movement
        self.velocity_x = velocity[0]
        self.velocity_y = velocity[1]
        self.damage = damage

    def set_velocity(self, vx: float, vy: float):
        """Update the projectile's velocity."""
        self.velocity_x = vx
        self.velocity_y = vy

    def set_damage(self, damage: float):
        """Update the projectile's damage value."""
        self.damage = damage

    def update(self, dt: float):
        """Update projectile position using velocity vector."""
        if not self.letter_items:
            return

        # Get current position
        current_pos = self.letter_items[0].pos()
        current_x = current_pos.x()
        current_y = current_pos.y()

        # Apply velocity with speed multiplier
        new_x = current_x + self.velocity_x * self.speed_multiplier * dt
        new_y = current_y + self.velocity_y * self.speed_multiplier * dt

        # Update visual positions
        self.letter_items[0].setPos(new_x, new_y)
        self._move_hexagon(self.letter_backgrounds[0], new_x, new_y)

        # Update animations
        completed_animations = []
        for animation in self.animations:
            if not animation.update(dt):
                completed_animations.append(animation)

        for animation in completed_animations:
            self.animations.remove(animation)

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of this projectile."""
        if not self.letter_items:
            return (0, 0)
        pos = self.letter_items[0].pos()
        return (pos.x(), pos.y())

    def get_miss_info(self):
        """Get information for collision handling with custom damage."""
        return {
            "damage": self.damage,
            "enemy_type_name": "FaceBoss Projectile",
        }

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if projectile has moved off screen (any direction)."""
        if not self.letter_items:
            return True

        pos = self.letter_items[0].pos()
        # Check if off screen in any direction
        if pos.y() < bottom_y:
            return True
        if abs(pos.x()) > 500:
            return True
        return False
