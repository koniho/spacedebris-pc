"""Game over screen."""

import math
import random_manager
import numpy as np
import pyqtgraph as pg
from font_manager import font_manager
from config import (
    BUTTON_COLORS,
    ALL_BUTTONS,
    LEFT_HAND_BUTTONS,
    RIGHT_HAND_BUTTONS,
    get_button_label,
)


class GameOverScreen:
    """Game over screen with restart functionality."""

    def __init__(self, view, config, final_score, final_wave, game_engine=None, stats=None):
        """Initialize game over screen."""
        self.view = view
        self.config = config
        self.game_engine = game_engine
        self.final_score = final_score
        self.final_wave = final_wave
        self.stats = stats or {"key_presses": 0, "enemies_destroyed": 0, "misses": 0}
        self.elapsed_time = 0.0
        self.active = True
        self.restart_requested = False

        # F+J simultaneous press tracking
        self.held_keys = set()

        self.left_button = LEFT_HAND_BUTTONS[-1]
        self.right_button = RIGHT_HAND_BUTTONS[0]

        # Fade-in animation parameters
        self.fade_in_duration = 0.5  # 0.5 second fade-in to match intro
        self.fade_in_progress = 0.0

        # Explosion transition state
        self.exploding = False
        self.explosion_start_time = 0.0
        self.explosion_duration = 0.8
        self.elements_cleared = False
        self.on_restart_callback = None  # Callback for when restart is triggered

        # Store all visual elements for explosion effect
        self.all_elements = []

        # Waveform animation state for link line
        self.waveform_intensity = 0.0
        self.waveform_decay_rate = 3.0
        self.waveform_time = 0.0
        self.link_waveform = None

        # Track partial press state
        self.partial_press_triggered = False
        self.partial_press_flash_time = 0.0
        self.partial_press_flash_duration = 0.2
        self.partial_flash_button = None

        # Store line coordinates for waveform
        self.line_start_x = -60 + 25  # Right edge of F hexagon
        self.line_end_x = 60 - 25  # Left edge of J hexagon
        self.line_y = -260  # Same as button y position

        # Create visual elements
        self._create_game_over_text()
        self._create_score_display()
        self._create_stats_display()
        self._create_button_indicators()

        # Start with elements invisible (for fade-in)
        self._set_initial_opacity()

    def _create_game_over_text(self):
        """Create main game over text."""
        # Main game over title
        self.game_over_text = pg.TextItem(
            text="GAME OVER",
            color=(255, 0, 0),  # Red
            anchor=(0.5, 0.5),
        )
        self.game_over_text.setFont(font_manager.get_title_font(64, bold=True))
        self.game_over_text.setPos(0, 150)
        self.view.addItem(self.game_over_text)
        self.all_elements.append({"item": self.game_over_text, "pos": (0, 150)})

        # Subtitle
        self.subtitle_text = pg.TextItem(
            text="Mission Failed",
            color=(255, 100, 100),
            anchor=(0.5, 0.5),
        )
        self.subtitle_text.setFont(font_manager.get_subtitle_font(24, bold=True))
        self.subtitle_text.setPos(0, 100)
        self.view.addItem(self.subtitle_text)
        self.all_elements.append({"item": self.subtitle_text, "pos": (0, 100)})

    def _create_score_display(self):
        """Create final score and wave display."""
        # Difficulty indicator
        difficulty = getattr(self.config.spawning, "current_difficulty", "normal").upper()
        difficulty_colors = {
            "EASY": (100, 255, 100),  # Green
            "NORMAL": (255, 255, 100),  # Yellow
            "HARD": (255, 150, 50),  # Orange
            "IMPOSSIBLE": (255, 50, 50),  # Red
        }
        difficulty_color = difficulty_colors.get(difficulty, (200, 200, 200))
        self.difficulty_display = pg.TextItem(
            text=f"Difficulty: {difficulty}",
            color=difficulty_color,
            anchor=(0.5, 0.5),
        )
        self.difficulty_display.setFont(font_manager.get_instruction_font(18, bold=True))
        self.difficulty_display.setPos(0, 55)
        self.view.addItem(self.difficulty_display)
        self.all_elements.append({"item": self.difficulty_display, "pos": (0, 55)})

        # Final score
        self.score_display = pg.TextItem(
            text=f"Final Score: {self.final_score:,}",
            color=(255, 255, 255),
            anchor=(0.5, 0.5),
        )
        self.score_display.setFont(font_manager.get_instruction_font(32, bold=True))
        self.score_display.setPos(0, 30)
        self.view.addItem(self.score_display)
        self.all_elements.append({"item": self.score_display, "pos": (0, 30)})

        # Wave reached
        self.wave_display = pg.TextItem(
            text=f"Waves Completed: {self.final_wave - 1}",
            color=(200, 200, 200),
            anchor=(0.5, 0.5),
        )
        self.wave_display.setFont(font_manager.get_instruction_font(20))
        self.wave_display.setPos(0, -10)
        self.view.addItem(self.wave_display)
        self.all_elements.append({"item": self.wave_display, "pos": (0, -10)})

        # Performance rating
        rating = self._get_performance_rating()
        rating_color = self._get_rating_color(rating)
        self.rating_display = pg.TextItem(
            text=f"Rating: {rating}",
            color=rating_color,
            anchor=(0.5, 0.5),
        )
        self.rating_display.setFont(font_manager.get_instruction_font(24, bold=True))
        self.rating_display.setPos(0, -50)
        self.view.addItem(self.rating_display)
        self.all_elements.append({"item": self.rating_display, "pos": (0, -50)})

    def _create_stats_display(self):
        """Create statistics display."""
        stats_y_start = -90
        stats_spacing = 22

        # Calculate accuracy
        key_presses = self.stats.get("key_presses", 0)
        misses = self.stats.get("misses", 0)
        if key_presses > 0:
            accuracy = ((key_presses - misses) / key_presses) * 100
        else:
            accuracy = 0.0

        # Accuracy display (prominent)
        accuracy_color = self._get_accuracy_color(accuracy)
        self.accuracy_display = pg.TextItem(
            text=f"Accuracy: {accuracy:.1f}%",
            color=accuracy_color,
            anchor=(0.5, 0.5),
        )
        self.accuracy_display.setFont(font_manager.get_instruction_font(20, bold=True))
        self.accuracy_display.setPos(0, stats_y_start)
        self.view.addItem(self.accuracy_display)
        self.all_elements.append({"item": self.accuracy_display, "pos": (0, stats_y_start)})

        # Key presses stat
        self.key_presses_display = pg.TextItem(
            text=f"Key Presses: {key_presses:,}",
            color=(180, 180, 180),
            anchor=(0.5, 0.5),
        )
        self.key_presses_display.setFont(font_manager.get_instruction_font(16))
        self.key_presses_display.setPos(0, stats_y_start - stats_spacing)
        self.view.addItem(self.key_presses_display)
        self.all_elements.append(
            {"item": self.key_presses_display, "pos": (0, stats_y_start - stats_spacing)}
        )

        # Enemies destroyed stat
        enemies_destroyed = self.stats.get("enemies_destroyed", 0)
        self.enemies_display = pg.TextItem(
            text=f"Enemies Destroyed: {enemies_destroyed:,}",
            color=(180, 180, 180),
            anchor=(0.5, 0.5),
        )
        self.enemies_display.setFont(font_manager.get_instruction_font(16))
        self.enemies_display.setPos(0, stats_y_start - stats_spacing * 2)
        self.view.addItem(self.enemies_display)
        self.all_elements.append(
            {"item": self.enemies_display, "pos": (0, stats_y_start - stats_spacing * 2)}
        )

        # Misses stat
        self.misses_display = pg.TextItem(
            text=f"Misses: {misses:,}",
            color=(180, 180, 180),
            anchor=(0.5, 0.5),
        )
        self.misses_display.setFont(font_manager.get_instruction_font(16))
        self.misses_display.setPos(0, stats_y_start - stats_spacing * 3)
        self.view.addItem(self.misses_display)
        self.all_elements.append(
            {"item": self.misses_display, "pos": (0, stats_y_start - stats_spacing * 3)}
        )

        # Perfect waves stat
        perfect_waves = self.stats.get("perfect_waves", 0)
        perfect_color = (255, 255, 0) if perfect_waves > 0 else (180, 180, 180)
        self.perfect_waves_display = pg.TextItem(
            text=f"Perfect Waves: {perfect_waves}",
            color=perfect_color,
            anchor=(0.5, 0.5),
        )
        self.perfect_waves_display.setFont(font_manager.get_instruction_font(16))
        self.perfect_waves_display.setPos(0, stats_y_start - stats_spacing * 4)
        self.view.addItem(self.perfect_waves_display)
        self.all_elements.append(
            {"item": self.perfect_waves_display, "pos": (0, stats_y_start - stats_spacing * 4)}
        )

    def _get_accuracy_color(self, accuracy):
        """Get color based on accuracy percentage."""
        if accuracy >= 95:
            return (0, 255, 0)  # Green - excellent
        elif accuracy >= 85:
            return (100, 255, 100)  # Light green - great
        elif accuracy >= 70:
            return (255, 255, 0)  # Yellow - good
        elif accuracy >= 50:
            return (255, 165, 0)  # Orange - okay
        else:
            return (255, 100, 100)  # Red - needs improvement

    def _get_performance_rating(self):
        """Calculate performance rating based on score and waves."""
        if self.final_score >= 5000:
            return "LEGENDARY"
        elif self.final_score >= 3000:
            return "EXCELLENT"
        elif self.final_score >= 2000:
            return "GREAT"
        elif self.final_score >= 1000:
            return "GOOD"
        elif self.final_score >= 500:
            return "FAIR"
        else:
            return "ROOKIE"

    def _get_rating_color(self, rating):
        """Get color for performance rating."""
        colors = {
            "LEGENDARY": (255, 215, 0),  # Gold
            "EXCELLENT": (255, 165, 0),  # Orange
            "GREAT": (0, 255, 0),  # Green
            "GOOD": (0, 255, 255),  # Cyan
            "FAIR": (255, 255, 0),  # Yellow
            "ROOKIE": (128, 128, 128),  # Gray
        }
        return colors.get(rating, (255, 255, 255))

    def _create_button_indicators(self):
        """Create F and J button indicators."""
        self.button_items = {}
        self.button_circles = {}

        # Only show F and J buttons for restart
        positions = {
            self.left_button: (-60, -260),
            self.right_button: (60, -260),
        }

        for button, pos in positions.items():
            # Create circle background
            color = BUTTON_COLORS[button]
            rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

            # Hexagon button
            hexagon = self._create_hexagon_button(pos, rgb, button)
            self.view.addItem(hexagon)
            self.button_circles[button] = hexagon
            self.all_elements.append({"item": hexagon, "pos": pos})

            # Letter text
            text = pg.TextItem(
                text=get_button_label(button), color=(255, 255, 255), anchor=(0.5, 0.5)
            )
            text.setFont(font_manager.get_button_font(20, bold=True))
            text.setPos(pos[0], pos[1])
            self.view.addItem(text)
            self.button_items[button] = text
            self.all_elements.append({"item": text, "pos": pos})

        # Create connecting line between F and J (at same y position as buttons, thicker)
        # Line ends at hexagon edges (hexagon radius is 25, buttons at x=-60 and x=60)
        self.combo_line = pg.PlotCurveItem(
            x=[self.line_start_x, self.line_end_x],
            y=[self.line_y, self.line_y],
            pen=pg.mkPen(color=(255, 255, 0, 150), width=12),
        )
        self.combo_line.setZValue(-5)  # Below buttons
        self.view.addItem(self.combo_line)
        self.all_elements.append({"item": self.combo_line, "pos": (0, self.line_y)})

        # Add glow effect for the line
        self.combo_line_glow = pg.PlotCurveItem(
            x=[self.line_start_x, self.line_end_x],
            y=[self.line_y, self.line_y],
            pen=pg.mkPen(color=(255, 255, 0, 60), width=20),
        )
        self.combo_line_glow.setZValue(-6)  # Below main line
        self.view.addItem(self.combo_line_glow)
        self.all_elements.append({"item": self.combo_line_glow, "pos": (0, self.line_y)})

        # Waveform overlay for partial press animation
        self.link_waveform = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 255, 255, 200), width=3))
        self.link_waveform.setZValue(-4)  # Above link line but below buttons
        self.view.addItem(self.link_waveform)
        self.all_elements.append({"item": self.link_waveform, "pos": (0, self.line_y)})

    def _create_hexagon_button(self, pos, rgb, button):
        """Create a hexagon button."""
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = pos[0] + 25 * np.cos(angles)
        y_points = pos[1] + 25 * np.sin(angles)

        hexagon_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*rgb, 0),
            fillLevel="enclosed",
        )
        self.view.addItem(hexagon_fill)

        hexagon_outline = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=pg.mkPen(color=(*rgb, 255), width=3), brush=None
        )

        hexagon_outline._fill = hexagon_fill
        return hexagon_outline

    def on_key_press(self, key: str, timestamp: int) -> str:
        """Handle key press event. Returns action to take."""
        if self.exploding:
            return "continue"  # Ignore input during explosion

        if key == "\x1b":  # ESC key
            return "quit"

        # Track held keys for F+J combo
        if key in ALL_BUTTONS:
            self.held_keys.add(key)

            # Visual feedback for button press
            if key in self.button_circles:
                hexagon = self.button_circles[key]
                rgb = tuple(int(BUTTON_COLORS[key][i : i + 2], 16) for i in (1, 3, 5))
                bright_rgb = tuple(min(255, c + 50) for c in rgb)
                hexagon.setPen(pg.mkPen(color=(*bright_rgb, 255), width=6))
                hexagon._fill.setBrush(pg.mkBrush(*bright_rgb, 200))

            # Check for F+J simultaneous press
            if self.left_button in self.held_keys and self.right_button in self.held_keys:
                self._trigger_restart_sequence()
                return "continue"  # Don't restart immediately, wait for animation

            # Check for partial press
            if key in (self.left_button, self.right_button):
                other_key = self.right_button if key == self.left_button else self.left_button
                if other_key not in self.held_keys:
                    self._show_partial_press_feedback(other_key)

        return "continue"

    def on_key_release(self, key: str):
        """Handle key release event."""
        if key in self.held_keys:
            self.held_keys.remove(key)

            # Reset button appearance
            if key in self.button_circles:
                hexagon = self.button_circles[key]
                rgb = tuple(int(BUTTON_COLORS[key][i : i + 2], 16) for i in (1, 3, 5))
                hexagon.setPen(pg.mkPen(color=(*rgb, 255), width=3))
                hexagon._fill.setBrush(pg.mkBrush(*rgb, 120))

    def _set_initial_opacity(self):
        """Set initial opacity to zero for fade-in effect."""
        for elem_data in self.all_elements:
            try:
                elem_data["item"].setOpacity(0)
            except:
                pass  # Some items might not support opacity

    def _show_partial_press_feedback(self, unpressed_button: str):
        """Show feedback when only F or J is pressed (not both)."""
        # Play denied sound effect
        if self.game_engine and self.game_engine.sound_manager:
            self.game_engine.sound_manager.play_denied_1_sound()

        # Trigger waveform animation on the link
        self._trigger_waveform_pulse()

        # Flash the unpressed button's hexagon
        self.partial_press_triggered = True
        self.partial_press_flash_time = 0.0
        self.partial_flash_button = unpressed_button

        # Set the hexagon to yellow flash
        hexagon = self.button_circles[unpressed_button]
        hexagon.setPen(pg.mkPen(color=(255, 255, 0, 255), width=6))
        hexagon._fill.setBrush(pg.mkBrush(255, 255, 0, 150))

    def _trigger_waveform_pulse(self):
        """Trigger a waveform pulse animation on the link line."""
        self.waveform_intensity = 1.0
        self.waveform_time = 0.0

    def _update_waveform_animation(self, dt: float):
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

        # Generate line base points
        num_points = 50
        base_x = np.linspace(self.line_start_x, self.line_end_x, num_points)
        base_y = np.full(num_points, self.line_y)

        # Create sinc-like waveform with traveling wave effect
        wave_frequency = 8.0
        wave_speed = 8.0
        amplitude = 15.0 * self.waveform_intensity

        t_normalized = np.linspace(0, 1, num_points)
        center_offset = self.waveform_time * wave_speed
        wave_arg = (t_normalized - 0.5) * wave_frequency * np.pi

        # Avoid division by zero in sinc
        safe_arg = np.where(np.abs(wave_arg) < 0.001, 0.001, wave_arg)
        sinc_wave = np.sin(safe_arg + center_offset) / safe_arg
        sinc_wave = np.where(np.abs(wave_arg) < 0.001, 1.0, sinc_wave)

        # Add secondary higher frequency component
        detail_wave = 0.3 * np.sin(t_normalized * 20 * np.pi + center_offset * 2)

        # Combine waves with envelope that tapers at ends
        envelope = np.sin(t_normalized * np.pi)
        displacement = amplitude * (sinc_wave + detail_wave) * envelope

        # Apply displacement (vertical for horizontal line)
        wave_y = base_y + displacement

        # Update waveform visual with intensity-based opacity
        alpha = int(200 * self.waveform_intensity)
        self.link_waveform.setData(
            x=base_x, y=wave_y, pen=pg.mkPen(color=(255, 255, 255, alpha), width=3)
        )

    def _trigger_restart_sequence(self):
        """Trigger restart explosion sequence."""
        if self.exploding:
            return

        # Start explosion transition
        self.exploding = True
        self.explosion_start_time = self.elapsed_time

        # Create expanding ring from center
        self.center_ring = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 255, 255, 255), width=5))
        self.view.addItem(self.center_ring)

        # Store element velocities for explosion
        for elem_data in self.all_elements:
            # Calculate angle and distance from center
            pos = elem_data["pos"]
            dx = pos[0]
            dy = pos[1]
            distance = math.sqrt(dx * dx + dy * dy) if dx != 0 or dy != 0 else 1

            # Set velocity away from center
            speed = 500.0  # pixels per second
            elem_data["velocity"] = (dx / distance * speed, dy / distance * speed)
            elem_data["angular_velocity"] = random_manager.uniform(-480, 480)  # degrees per second
            elem_data["rotation"] = 0

        # Trigger screen shake and sound if game engine is available
        # Restore global speed to 1.0 before transition
        self.game_engine.set_speed_multiplier(1.0)
        self.game_engine.sound_manager.play_twinkle_sound()
        self.game_engine.shake_manager.trigger_shake(magnitude=10.0, duration=0.8)

        self.restart_requested = True

    def update(self, dt: float):
        """Update game over screen animations."""
        if not self.active:
            return

        self.elapsed_time += dt

        # Handle explosion transition
        if self.exploding:
            explosion_time = self.elapsed_time - self.explosion_start_time
            explosion_progress = explosion_time / self.explosion_duration

            if explosion_progress < 1.0:
                # Update expanding ring
                ring_radius = explosion_progress * 600
                ring_opacity = max(0, 1.0 - explosion_progress)
                angles = np.linspace(0, 2 * np.pi, 100)
                x_points = ring_radius * np.cos(angles)
                y_points = ring_radius * np.sin(angles)
                self.center_ring.setData(x=x_points, y=y_points)
                self.center_ring.setPen(
                    pg.mkPen(color=(255, 255, 255, int(255 * ring_opacity)), width=5)
                )

                # Move elements outward
                for elem_data in self.all_elements:
                    if "velocity" in elem_data:
                        # Calculate new position
                        vx, vy = elem_data["velocity"]
                        original_pos = elem_data["pos"]
                        new_x = original_pos[0] + vx * explosion_time
                        new_y = original_pos[1] + vy * explosion_time

                        # Apply rotation
                        elem_data["rotation"] += elem_data["angular_velocity"] * dt

                        # Update position and fade out
                        try:
                            elem_data["item"].setPos(new_x, new_y)
                            # Special handling for hexagon fills
                            if hasattr(elem_data["item"], "_fill"):
                                # Animate fill: surge to full opacity then fade
                                if explosion_progress < 0.2:
                                    # First 20% - surge to full opacity
                                    fill_opacity = explosion_progress * 5.0  # 0 to 1
                                    elem_data["item"]._fill.setOpacity(fill_opacity)
                                else:
                                    # Remaining 80% - fade out
                                    fill_opacity = 1.0 - (explosion_progress - 0.2) / 0.8
                                    elem_data["item"]._fill.setOpacity(fill_opacity)
                                # Regular opacity for outline
                                elem_data["item"].setOpacity(1.0 - explosion_progress)
                            else:
                                # Regular fade for non-hexagon elements
                                elem_data["item"].setOpacity(1.0 - explosion_progress)

                        except:
                            pass
            else:
                # All elements cleared
                if not self.elements_cleared:
                    self.elements_cleared = True
                    self.cleanup()
                    # Trigger callback to restart game
                    if self.on_restart_callback:
                        self.on_restart_callback()
            return  # Skip normal animations during explosion

        # Handle fade-in
        if self.fade_in_progress < self.fade_in_duration:
            self.fade_in_progress += dt
            opacity = min(1.0, self.fade_in_progress / self.fade_in_duration)

            # Apply fade-in to all elements
            for elem_data in self.all_elements:
                try:
                    elem_data["item"].setOpacity(opacity)
                except:
                    pass

        # Normal animations after fade-in complete
        if self.fade_in_progress >= self.fade_in_duration:
            # Pulse game over text
            pulse = 0.8 + 0.2 * math.sin(self.elapsed_time * 2)
            self.game_over_text.setOpacity(pulse)

            # Pulse F-J connecting line
            line_alpha = 0.4 + 0.3 * math.sin(self.elapsed_time * 4)
            line_width = 12 + 2 * math.sin(self.elapsed_time * 3)
            self.combo_line.setPen(
                pg.mkPen(color=(255, 255, 0, int(line_alpha * 255)), width=int(line_width))
            )

            # Pulse glow as well
            glow_alpha = 0.15 + 0.1 * math.sin(self.elapsed_time * 4)
            self.combo_line_glow.setPen(
                pg.mkPen(color=(255, 255, 0, int(glow_alpha * 255)), width=int(line_width + 8))
            )

            # Update waveform animation
            self._update_waveform_animation(dt)

            # Update partial press flash animation
            if self.partial_press_triggered:
                self.partial_press_flash_time += dt
                if self.partial_press_flash_time >= self.partial_press_flash_duration:
                    self.partial_press_triggered = False
                else:
                    # Fade the yellow flash
                    progress = self.partial_press_flash_time / self.partial_press_flash_duration
                    flash_alpha = int(255 * (1.0 - progress))
                    fill_alpha = int(150 * (1.0 - progress))
                    hexagon = self.button_circles[self.partial_flash_button]
                    hexagon.setPen(pg.mkPen(color=(255, 255, 0, flash_alpha), width=6))
                    hexagon._fill.setBrush(pg.mkBrush(255, 255, 0, fill_alpha))

            # Reset button appearance if not held
            for button, hexagon in self.button_circles.items():
                # Skip the button being flashed
                if self.partial_press_triggered and button == self.partial_flash_button:
                    continue
                if button not in self.held_keys:
                    rgb = tuple(int(BUTTON_COLORS[button][i : i + 2], 16) for i in (1, 3, 5))
                    hexagon.setPen(pg.mkPen(color=(*rgb, 255), width=3))
                    hexagon._fill.setBrush(pg.mkBrush(*rgb, 120))

    def cleanup(self):
        """Remove all visual elements."""
        if not self.active:
            return

        # Remove expanding ring if it exists
        if hasattr(self, "center_ring"):
            self.view.removeItem(self.center_ring)

        # Remove all tracked elements
        for elem_data in self.all_elements:
            try:
                self.view.removeItem(elem_data["item"])
            except:
                pass  # Item might already be removed

        # Remove button elements (might not be in all_elements)
        for text in self.button_items.values():
            try:
                self.view.removeItem(text)
            except:
                pass
        for hexagon in self.button_circles.values():
            try:
                self.view.removeItem(hexagon)
                if hasattr(hexagon, "_fill"):
                    self.view.removeItem(hexagon._fill)
            except:
                pass

        self.active = False
