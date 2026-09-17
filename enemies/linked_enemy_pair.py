"""Linked enemy pair implementation - requires simultaneous typing."""

import math
import time
from typing import Tuple, List
import numpy as np
import pyqtgraph as pg
from enemies.base_enemy import BaseEnemy
from enemies.enemy import Enemy
from enemies.letter_effects import DisengageFlashAnim
from enemies.animations import EnemyVictoryDeathAnimation
from enemies.animations import EnemyFireDeathAnimation

from font_manager import font_manager


class LinkedEnemyPair(BaseEnemy):
    """Pair of enemies that must be typed simultaneously."""

    def __init__(
        self,
        seq1: str,
        seq2: str,
        pos1: Tuple[float, float],
        pos2: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
    ):
        """Initialize linked enemy pair."""
        super().__init__(view, laser_manager, waveform)
        self.sequence1 = seq1
        self.sequence2 = seq2
        self.current_position = 0

        # Create two enemies
        self.enemy1 = Enemy(seq1, pos1, view, laser_manager, waveform)
        self.enemy2 = Enemy(seq2, pos2, view, laser_manager, waveform)

        # Sync speeds for paired enemies - 3x faster than before
        base_speed = 120  # 3x faster (was 40)
        avg_length = (len(seq1) + len(seq2)) / 2
        length_multiplier = max(0.3, 2.0 / avg_length)
        pair_speed = base_speed * length_multiplier

        self.enemy1.speed = pair_speed
        self.enemy2.speed = pair_speed

        # Hit animation state - letters move outward and back
        self.hit_anim_active = False
        self.hit_anim_time = 0.0
        self.hit_anim_duration = 0.15
        self.hit_anim_distance = 15  # Pixels to move outward

        # Hexagon radius for calculating line endpoints
        self.hexagon_radius = 18  # Same as Enemy._create_letter_hexagon

        # Create link visual with thick appearance (rendered below hexagons)
        self.link_line = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 0, 255), width=20))
        self.link_line.setZValue(-10)  # Below hexagons
        self.view.addItem(self.link_line)

        # Create glow effect for link (even wider, more transparent)
        self.link_glow = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 0, 255, 80), width=30))
        self.link_glow.setZValue(-11)  # Below main line
        self.view.addItem(self.link_glow)

        # Create waveform overlay for activation animation
        self.link_waveform = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 255, 255, 200), width=3))
        self.link_waveform.setZValue(-9)  # Above link line but below hexagons
        self.view.addItem(self.link_waveform)

        # Waveform animation state
        self.waveform_active = False
        self.waveform_intensity = 0.0
        self.waveform_decay_rate = 3.0  # How fast waveform fades
        self.waveform_time = 0.0  # Time accumulator for waveform animation

        # Animations list for flash effects
        self.animations: List = []

        # Track partial press state to avoid repeated triggers
        self.partial_press_triggered = False

        # Create sync icon at midpoint
        self.sync_icon = pg.TextItem(text="⚡", color=(255, 255, 0), anchor=(0.5, 0.5))
        self.sync_icon.setFont(font_manager.get_button_font(16))
        self.view.addItem(self.sync_icon)

        self._update_link_visual()

    def check_simultaneous_input(
        self, input_tracker, current_time: float, is_engaged: bool = False
    ) -> str:
        """Check for simultaneous input. Returns 'complete', 'failed', or 'active'.

        Args:
            input_tracker: The input tracker to check for button presses.
            current_time: Current game time.
            is_engaged: Whether this pair is currently engaged. Only engaged pairs
                        should show partial press feedback.
        """
        if self.completed:
            return "complete"

        if self.current_position >= len(self.sequence1):
            self.completed = True
            return "complete"

        required_buttons = {
            self.sequence1[self.current_position],
            self.sequence2[self.current_position],
        }

        # Check for successful simultaneous press
        if input_tracker.check_simultaneous_press(required_buttons, current_time):
            # Activate both letters - this will create lasers internally
            self.enemy1.activate_letter(self.current_position)
            self.enemy2.activate_letter(self.current_position)

            self.current_position += 1

            # Start hit animation (restart if already active)
            self._start_hit_animation()

            # Create sync effect
            self._create_sync_effect()

            # Reset partial press tracking
            self.partial_press_triggered = False

            # Check if complete
            if self.current_position >= len(self.sequence1):
                self.completed = True
                return "complete"
            return "active"

        # Only show partial press feedback if this pair is engaged
        if is_engaged:
            # Check for partial press (only one of the required buttons is held)
            held_buttons = input_tracker.get_held_buttons()
            partial_match = held_buttons & required_buttons

            if len(partial_match) == 1 and not self.partial_press_triggered:
                # One button pressed but not the other - show invalid highlight on unpressed
                self._show_partial_press_feedback(partial_match, required_buttons)
                self.partial_press_triggered = True
                return "partial"

            # Reset partial press tracking when no buttons are held
            if not partial_match:
                self.partial_press_triggered = False

            # Check if there are any recent key presses that don't match the required buttons
            recent_presses = input_tracker.get_recent_presses(current_time, 200)  # 200ms window
            if recent_presses:
                # Check if any recent press was a wrong key
                wrong_keys = recent_presses - required_buttons
                if wrong_keys:
                    # Wrong keys were pressed - disengage
                    self.reset_typing_progress()
                    return "failed"

        # No input or waiting for input - return None or empty string to indicate no action
        return ""  # Empty string means no action taken

    def _update_link_visual(self, dt: float = 0.0):
        """Update the visual link between enemies."""
        pos1 = self.enemy1.get_center_position()
        pos2 = self.enemy2.get_center_position()

        # Calculate direction vector from enemy1 to enemy2
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 1:
            distance = 1  # Avoid division by zero

        # Normalize direction
        dir_x = dx / distance
        dir_y = dy / distance

        # Calculate line start and end points at hexagon edges
        start_x = pos1[0] + dir_x * self.hexagon_radius
        start_y = pos1[1] + dir_y * self.hexagon_radius
        end_x = pos2[0] - dir_x * self.hexagon_radius
        end_y = pos2[1] - dir_y * self.hexagon_radius

        # Generate straight line points (no curve)
        num_points = 50
        t = np.linspace(0, 1, num_points)
        x = start_x + t * (end_x - start_x)
        y = start_y + t * (end_y - start_y)

        # Apply subtle pulse effect to line width
        pulse = 1.0 + 0.1 * math.sin(time.time() * 3)
        width = int(20 * pulse)
        glow_width = int(30 * pulse)

        # Update main link line
        self.link_line.setData(x=x, y=y, pen=pg.mkPen(color=(255, 0, 255), width=width))

        # Update glow effect
        self.link_glow.setData(x=x, y=y, pen=pg.mkPen(color=(255, 0, 255, 80), width=glow_width))

        # Update waveform animation
        self._update_waveform_animation(x, y, dt)

        # Update sync icon position (at midpoint)
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        self.sync_icon.setPos(mid_x, mid_y)

    def _update_waveform_animation(self, base_x: np.ndarray, base_y: np.ndarray, dt: float):
        """Update waveform overlay animation on the link line."""
        # Decay waveform intensity over time
        if self.waveform_intensity > 0:
            self.waveform_intensity = max(
                0, self.waveform_intensity - dt * self.waveform_decay_rate
            )
            self.waveform_time += dt

        if self.waveform_intensity <= 0.01:
            # Hide waveform when not active
            self.link_waveform.setData(x=[], y=[])
            return

        # Calculate perpendicular direction for waveform displacement
        if len(base_x) < 2:
            return

        # Get the line direction
        line_dx = base_x[-1] - base_x[0]
        line_dy = base_y[-1] - base_y[0]
        line_length = math.sqrt(line_dx * line_dx + line_dy * line_dy)

        if line_length < 1:
            return

        # Perpendicular direction (normalized)
        perp_x = -line_dy / line_length
        perp_y = line_dx / line_length

        # Generate waveform displacement along the line
        num_points = len(base_x)
        t_normalized = np.linspace(0, 1, num_points)

        # Create sinc-like waveform with traveling wave effect
        wave_frequency = 8.0  # Number of wave cycles
        wave_speed = 8.0  # How fast the wave travels
        amplitude = 30.0 * self.waveform_intensity  # Max displacement

        # Sinc function centered on the line with traveling component
        center_offset = self.waveform_time * wave_speed
        wave_arg = (t_normalized - 0.5) * wave_frequency * np.pi

        # Avoid division by zero in sinc
        safe_arg = np.where(np.abs(wave_arg) < 0.001, 0.001, wave_arg)
        sinc_wave = np.sin(safe_arg + center_offset) / safe_arg
        sinc_wave = np.where(np.abs(wave_arg) < 0.001, 1.0, sinc_wave)

        # Add secondary higher frequency component for complexity
        detail_wave = 0.3 * np.sin(t_normalized * 20 * np.pi + center_offset * 2)

        # Combine waves with envelope that tapers at ends
        envelope = np.sin(t_normalized * np.pi)  # Tapers to 0 at both ends
        displacement = amplitude * (sinc_wave + detail_wave) * envelope

        # Apply displacement perpendicular to line
        wave_x = base_x + perp_x * displacement
        wave_y = base_y + perp_y * displacement

        # Update waveform visual with intensity-based opacity
        alpha = int(200 * self.waveform_intensity)
        self.link_waveform.setData(
            x=wave_x, y=wave_y, pen=pg.mkPen(color=(255, 255, 255, alpha), width=6)
        )

    def _trigger_waveform_pulse(self):
        """Trigger a waveform pulse animation on the link line."""
        self.waveform_intensity = 1.0
        self.waveform_time = 0.0

    def _create_sync_effect(self):
        """Create visual effect when buttons are synced."""
        # Trigger waveform pulse on the link line
        self._trigger_waveform_pulse()

    def _show_partial_press_feedback(self, pressed_buttons: set, required_buttons: set):
        """Show invalid highlight on unpressed letter when only one button is pressed."""
        unpressed_buttons = required_buttons - pressed_buttons

        # Trigger waveform animation on the link
        self._trigger_waveform_pulse()

        # Show flash on the unpressed letter's hexagon
        for button in unpressed_buttons:
            if (
                self.current_position < len(self.sequence1)
                and button == self.sequence1[self.current_position]
            ):
                # Flash enemy1's current letter
                if self.current_position < len(self.enemy1.letter_backgrounds):
                    hexagon = self.enemy1.letter_backgrounds[self.current_position]
                    flash_anim = DisengageFlashAnim(hexagon)
                    self.animations.append(flash_anim)
            elif (
                self.current_position < len(self.sequence2)
                and button == self.sequence2[self.current_position]
            ):
                # Flash enemy2's current letter
                if self.current_position < len(self.enemy2.letter_backgrounds):
                    hexagon = self.enemy2.letter_backgrounds[self.current_position]
                    flash_anim = DisengageFlashAnim(hexagon)
                    self.animations.append(flash_anim)

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position between both enemies."""
        pos1 = self.enemy1.get_center_position()
        pos2 = self.enemy2.get_center_position()
        return ((pos1[0] + pos2[0]) / 2, (pos1[1] + pos2[1]) / 2)

    def get_min_y_position(self) -> float:
        """Get minimum y position across both enemies (closest to player)."""
        pos1 = self.enemy1.get_center_position()
        pos2 = self.enemy2.get_center_position()
        return min(pos1[1], pos2[1])

    def is_complete(self) -> bool:
        """Check if pair is complete."""
        return self.completed

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if either enemy is below screen."""
        return self.enemy1.is_below_screen(bottom_y) or self.enemy2.is_below_screen(bottom_y)

    def type_button(self, button: str) -> bool:
        """LinkedEnemyPair doesn't use standard typing - handled by simultaneous input."""
        return False

    def can_type_button(self, button: str) -> bool:
        """LinkedEnemyPair doesn't use standard typing - handled by simultaneous input."""
        if self.current_position >= len(self.sequence1):
            return False
        return (
            button == self.sequence1[self.current_position]
            or button == self.sequence2[self.current_position]
        )

    def reset_typing_progress(self):
        """Reset typing progress to the beginning."""
        self.current_position = 0
        self.enemy1.reset_typing_progress()
        self.enemy2.reset_typing_progress()

    def get_width(self) -> float:
        """Get total width spanning both enemies."""
        pos1 = self.enemy1.get_center_position()
        pos2 = self.enemy2.get_center_position()
        enemy1_width = self.enemy1.get_width()
        enemy2_width = self.enemy2.get_width()
        distance = abs(pos2[0] - pos1[0])
        return distance + max(enemy1_width, enemy2_width)

    def update(self, dt: float):
        """Update enemies without special handling - overrides BaseEnemy abstract method."""
        # Propagate speed multiplier to child enemies
        self.enemy1.set_speed_multiplier(self.speed_multiplier)
        self.enemy2.set_speed_multiplier(self.speed_multiplier)

        # Update both enemies
        self.enemy1.update(dt)
        self.enemy2.update(dt)

        # Update hit animation - letters move outward and back
        if self.hit_anim_active:
            self.hit_anim_time += dt
            if self.hit_anim_time >= self.hit_anim_duration:
                # Animation complete - reset positions
                self.hit_anim_active = False
                self.hit_anim_time = 0.0
                self._reset_hit_anim_positions()
            else:
                # Calculate offset using sine wave for smooth out-and-back motion
                progress = self.hit_anim_time / self.hit_anim_duration
                offset = math.sin(progress * math.pi) * self.hit_anim_distance
                self._apply_hit_anim_offset(offset)

        # Update link visual with dt for waveform animation
        self._update_link_visual(dt)

        # Update flash animations
        completed_anims = []
        for anim in self.animations:
            if not anim.update(dt):
                completed_anims.append(anim)
        for anim in completed_anims:
            self.animations.remove(anim)

    def _start_hit_animation(self):
        """Start or restart the hit animation."""
        self.hit_anim_active = True
        self.hit_anim_time = 0.0
        # Store base positions for animation
        self._store_base_positions()

    def _store_base_positions(self):
        """Store the base positions of letters for hit animation."""
        self.enemy1_base_positions = []
        self.enemy2_base_positions = []
        for item in self.enemy1.letter_items:
            pos = item.pos()
            self.enemy1_base_positions.append((pos.x(), pos.y()))
        for item in self.enemy2.letter_items:
            pos = item.pos()
            self.enemy2_base_positions.append((pos.x(), pos.y()))
        # Also store backgrounds
        self.enemy1_bg_base_positions = []
        self.enemy2_bg_base_positions = []
        for bg in self.enemy1.letter_backgrounds:
            data = bg.getData()
            if data[0] is not None:
                center_x = np.mean(data[0])
                center_y = np.mean(data[1])
                self.enemy1_bg_base_positions.append((center_x, center_y))
        for bg in self.enemy2.letter_backgrounds:
            data = bg.getData()
            if data[0] is not None:
                center_x = np.mean(data[0])
                center_y = np.mean(data[1])
                self.enemy2_bg_base_positions.append((center_x, center_y))

    def _apply_hit_anim_offset(self, offset: float):
        """Apply offset to letter positions - enemy1 moves left, enemy2 moves right."""
        # Move enemy1 letters left (negative x offset)
        for i, item in enumerate(self.enemy1.letter_items):
            if i < len(self.enemy1_base_positions):
                base_x, base_y = self.enemy1_base_positions[i]
                item.setPos(base_x - offset, base_y)
        # Move enemy1 backgrounds
        for i, bg in enumerate(self.enemy1.letter_backgrounds):
            if i < len(self.enemy1_bg_base_positions):
                base_x, base_y = self.enemy1_bg_base_positions[i]
                data = bg.getData()
                if data[0] is not None:
                    current_center_x = np.mean(data[0])
                    dx = (base_x - offset) - current_center_x
                    bg.setData(x=data[0] + dx, y=data[1])

        # Move enemy2 letters right (positive x offset)
        for i, item in enumerate(self.enemy2.letter_items):
            if i < len(self.enemy2_base_positions):
                base_x, base_y = self.enemy2_base_positions[i]
                item.setPos(base_x + offset, base_y)
        # Move enemy2 backgrounds
        for i, bg in enumerate(self.enemy2.letter_backgrounds):
            if i < len(self.enemy2_bg_base_positions):
                base_x, base_y = self.enemy2_bg_base_positions[i]
                data = bg.getData()
                if data[0] is not None:
                    current_center_x = np.mean(data[0])
                    dx = (base_x + offset) - current_center_x
                    bg.setData(x=data[0] + dx, y=data[1])

    def _reset_hit_anim_positions(self):
        """Reset letter positions to their base positions."""
        # Reset enemy1 letters
        for i, item in enumerate(self.enemy1.letter_items):
            if i < len(self.enemy1_base_positions):
                base_x, base_y = self.enemy1_base_positions[i]
                item.setPos(base_x, base_y)
        # Reset enemy1 backgrounds
        for i, bg in enumerate(self.enemy1.letter_backgrounds):
            if i < len(self.enemy1_bg_base_positions):
                base_x, base_y = self.enemy1_bg_base_positions[i]
                data = bg.getData()
                if data[0] is not None:
                    current_center_x = np.mean(data[0])
                    dx = base_x - current_center_x
                    bg.setData(x=data[0] + dx, y=data[1])

        # Reset enemy2 letters
        for i, item in enumerate(self.enemy2.letter_items):
            if i < len(self.enemy2_base_positions):
                base_x, base_y = self.enemy2_base_positions[i]
                item.setPos(base_x, base_y)
        # Reset enemy2 backgrounds
        for i, bg in enumerate(self.enemy2.letter_backgrounds):
            if i < len(self.enemy2_bg_base_positions):
                base_x, base_y = self.enemy2_bg_base_positions[i]
                data = bg.getData()
                if data[0] is not None:
                    current_center_x = np.mean(data[0])
                    dx = base_x - current_center_x
                    bg.setData(x=data[0] + dx, y=data[1])

    def cleanup(self):
        """Remove all visual elements."""
        self.enemy1.cleanup()
        self.enemy2.cleanup()

        # Clean up flash animations
        for anim in self.animations:
            anim.cleanup()
        self.animations.clear()

        # Safely remove link visual elements
        if self.link_line and self.link_line.scene() is not None:
            self.view.removeItem(self.link_line)
        if self.link_glow and self.link_glow.scene() is not None:
            self.view.removeItem(self.link_glow)
        if self.link_waveform and self.link_waveform.scene() is not None:
            self.view.removeItem(self.link_waveform)
        if self.sync_icon and self.sync_icon.scene() is not None:
            self.view.removeItem(self.sync_icon)

    @property
    def letter_items(self):
        """Get combined letter items from both child enemies for unified interface."""
        # Return combined list of all letter items from both enemies
        items = []
        items.extend(self.enemy1.letter_items)
        items.extend(self.enemy2.letter_items)
        return items

    @property
    def sequence(self):
        """Get combined sequence from both child enemies for unified interface."""
        # Return combined sequence string from both enemies
        return self.enemy1.sequence + self.enemy2.sequence

    @property
    def letter_backgrounds(self):
        """Get combined letter backgrounds from both child enemies for unified interface."""
        # Return combined list of all letter backgrounds from both enemies
        backgrounds = []
        backgrounds.extend(self.enemy1.letter_backgrounds)
        backgrounds.extend(self.enemy2.letter_backgrounds)
        return backgrounds

    def get_destruction_info(self):
        """Get destruction info for linked enemy pairs."""
        return {
            "points": (len(self.sequence1) + len(self.sequence2)) * 25,
            "explosion_type": "critical",
            "explosion_scale": 1.0,
            "shake_type": "large",
        }

    def get_miss_info(self):
        """Get miss info for linked enemy pairs."""
        return {
            "damage": 0.25,
            "enemy_type_name": "Enemy pair",
        }  # Same damage as normal enemies

    def _cleanup_link_visuals(self):
        """Clean up link visual elements (link line, glow, waveform, sync icon)."""
        if self.link_line and self.link_line.scene() is not None:
            self.view.removeItem(self.link_line)
        if self.link_glow and self.link_glow.scene() is not None:
            self.view.removeItem(self.link_glow)
        if self.link_waveform and self.link_waveform.scene() is not None:
            self.view.removeItem(self.link_waveform)
        if self.sync_icon and self.sync_icon.scene() is not None:
            self.view.removeItem(self.sync_icon)

    def has_active_animations(self) -> bool:
        """Check if pair or child enemies have active animations."""
        if len(self.animations) > 0:
            return True
        return self.enemy1.has_active_animations() or self.enemy2.has_active_animations()

    def update_animations(self, dt: float):
        """Update remaining animations (called after enemy is destroyed)."""
        # Update pair's own animations
        completed = []
        for animation in self.animations:
            if not animation.update(dt):
                completed.append(animation)
        for animation in completed:
            self.animations.remove(animation)

        # Update child enemy animations
        self.enemy1.update_animations(dt)
        self.enemy2.update_animations(dt)

    def create_victory_animations(self):
        """Create victory animations for both child enemies in the pair."""

        # Clean up link visuals, leave child enemy visuals for animations
        self._cleanup_link_visuals()

        # Create victory animations for both child enemies
        victory_anim1 = EnemyVictoryDeathAnimation(self.enemy1, self.view)
        victory_anim2 = EnemyVictoryDeathAnimation(self.enemy2, self.view)
        return [victory_anim1, victory_anim2]

    def create_death_animations(self):
        """Create death animations for when this pair hits the player."""

        # Clean up link visuals first
        self._cleanup_link_visuals()

        # Create death animations for both child enemies
        death_anim1 = EnemyFireDeathAnimation(self.enemy1, self.view)
        death_anim2 = EnemyFireDeathAnimation(self.enemy2, self.view)
        return [death_anim1, death_anim2]
