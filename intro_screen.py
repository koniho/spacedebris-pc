"""Interactive intro/attract screen."""

import math
from typing import Set, List, Optional
import pyqtgraph as pg
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
import random_manager
from debug_log import debug_print as print
import numpy as np
from config import BUTTON_COLORS, ALL_BUTTONS, DifficultyLevel
from config import LEFT_HAND_BUTTONS, RIGHT_HAND_BUTTONS, get_button_label
from font_manager import font_manager
from effects.intro_effects import (
    ConnectingBeamEffect,
    ExpandingRingEffect,
    IntroLaserEffect,
    MassiveExplosionEffect,
    ParticleBurstEffect,
    ScreenFlashEffect,
    SpiralEffect,
)


class IntroScreen:
    """Interactive intro/attract screen."""

    def __init__(self, view, config, game_engine=None):
        """Initialize intro screen.

        Args:
            view: The pyqtgraph view to render on.
            config: Game configuration.
            game_engine: Optional game engine reference.
        """
        self.view = view
        self.config = config
        self.game_engine = game_engine
        self.held_keys: Set[str] = set()
        self.active = True
        self.elapsed_time = 0.0
        self.start_triggered = False
        self.active_effects: List = []

        # Fade-in effect
        self.fade_in_duration = 0.5
        self.fade_in_progress = 0.0

        # Explosion transition state
        self.exploding = False
        self.explosion_start_time = 0.0
        self.explosion_duration = 0.8
        self.elements_cleared = False
        self.on_start_callback = None  # Callback for when intro is done

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

        # Difficulty selection - default to EASY
        self.difficulties = [DifficultyLevel.EASY, DifficultyLevel.NORMAL, DifficultyLevel.HARD]
        self.selected_difficulty_index = 0  # Default to EASY (index 0)
        self.selected_difficulty = self.difficulties[self.selected_difficulty_index]

        # Start combo buttons (last left-hand + first right-hand)
        self.start_left_button = LEFT_HAND_BUTTONS[-1]
        self.start_right_button = RIGHT_HAND_BUTTONS[0]

        # Simultaneous press detection - wait 100ms before triggering independent press
        self.pending_left_press = False
        self.pending_right_press = False
        self.pending_press_time = 0.0
        self.simultaneous_window = 0.1  # 100ms window for simultaneous detection

        # Create visual elements
        self._create_title()
        self._create_difficulty_selector()
        self._create_button_indicators()
        self._add_start_combo_highlight()

        # Set initial opacity to 0 for fade-in
        self._set_all_opacity(0.0)

    def _create_title(self):
        """Create title text with glow effect."""
        # Main title
        self.title_text = pg.TextItem(
            text="SPACE DEBRIS",
            color=(0, 255, 255),  # Cyan
            anchor=(0.5, 0.5),
        )
        self.title_text.setFont(font_manager.get_title_font(48, bold=True))
        self.title_text.setPos(0, 200)
        self.view.addItem(self.title_text)
        self.all_elements.append({"item": self.title_text, "pos": (0, 200)})

        # Subtitle
        self.subtitle_text = pg.TextItem(
            text="Type to Survive",
            color=(255, 255, 255),
            anchor=(0.5, 0.5),
        )
        self.subtitle_text.setFont(font_manager.get_subtitle_font(18))
        self.subtitle_text.setPos(0, 160)
        self.view.addItem(self.subtitle_text)
        self.all_elements.append({"item": self.subtitle_text, "pos": (0, 160)})

    def _create_difficulty_selector(self):
        """Create difficulty selection UI."""
        # Difficulty label
        self.difficulty_label = pg.TextItem(
            text="DIFFICULTY",
            color=(180, 180, 180),
            anchor=(0.5, 0.5),
        )
        self.difficulty_label.setFont(font_manager.get_instruction_font(14))
        self.difficulty_label.setPos(0, 100)
        self.view.addItem(self.difficulty_label)
        self.all_elements.append({"item": self.difficulty_label, "pos": (0, 100)})

        # Difficulty options - positioned horizontally
        self.difficulty_texts = {}
        self.difficulty_boxes = {}
        difficulty_colors = {
            DifficultyLevel.EASY: (0, 255, 100),  # Green
            DifficultyLevel.NORMAL: (255, 200, 0),  # Yellow/Gold
            DifficultyLevel.HARD: (255, 50, 50),  # Red
        }
        difficulty_positions = {
            DifficultyLevel.EASY: -120,
            DifficultyLevel.NORMAL: 0,
            DifficultyLevel.HARD: 120,
        }
        difficulty_y = 60

        # Box widths - NORMAL needs more horizontal padding due to longer text
        box_widths = {
            DifficultyLevel.EASY: 90,
            DifficultyLevel.NORMAL: 110,  # Wider for "NORMAL" text
            DifficultyLevel.HARD: 90,
        }

        for difficulty in self.difficulties:
            x_pos = difficulty_positions[difficulty]
            color = difficulty_colors[difficulty]

            # Create selection box (outline) with per-difficulty width
            box_width = box_widths[difficulty]
            box_height = 35
            box_x = [
                x_pos - box_width / 2,
                x_pos + box_width / 2,
                x_pos + box_width / 2,
                x_pos - box_width / 2,
                x_pos - box_width / 2,
            ]
            box_y = [
                difficulty_y - box_height / 2,
                difficulty_y - box_height / 2,
                difficulty_y + box_height / 2,
                difficulty_y + box_height / 2,
                difficulty_y - box_height / 2,
            ]

            box = pg.PlotCurveItem(
                x=box_x,
                y=box_y,
                pen=pg.mkPen(color=(*color, 100), width=2),
            )
            box.setZValue(-1)
            self.view.addItem(box)
            self.difficulty_boxes[difficulty] = box
            self.all_elements.append({"item": box, "pos": (x_pos, difficulty_y)})

            # Create text label
            text = pg.TextItem(
                text=difficulty.value.upper(),
                color=color,
                anchor=(0.5, 0.5),
            )
            text.setFont(font_manager.get_instruction_font(20, bold=True))
            text.setPos(x_pos, difficulty_y)
            self.view.addItem(text)
            self.difficulty_texts[difficulty] = text
            self.all_elements.append({"item": text, "pos": (x_pos, difficulty_y)})

        # Arrow indicators for Left and Right
        arrow_y = difficulty_y
        self.left_arrow = pg.TextItem(
            text="<",
            color=BUTTON_COLORS[self.start_left_button],
            anchor=(0.5, 0.5),
        )
        self.left_arrow.setFont(font_manager.get_instruction_font(16, bold=True))
        self.left_arrow.setPos(-200, arrow_y)
        self.view.addItem(self.left_arrow)
        self.all_elements.append({"item": self.left_arrow, "pos": (-200, arrow_y)})

        # Right arrow (J to go right)
        self.right_arrow = pg.TextItem(
            text=">",
            color=BUTTON_COLORS[self.start_right_button],
            anchor=(0.5, 0.5),
        )
        self.right_arrow.setFont(font_manager.get_instruction_font(16, bold=True))
        self.right_arrow.setPos(200, arrow_y)
        self.view.addItem(self.right_arrow)
        self.all_elements.append({"item": self.right_arrow, "pos": (200, arrow_y)})

        # Update visual to show current selection
        self._update_difficulty_display()

    def _update_difficulty_display(self):
        """Update the difficulty selector visuals to reflect current selection."""
        difficulty_colors = {
            DifficultyLevel.EASY: (0, 255, 100),
            DifficultyLevel.NORMAL: (255, 200, 0),
            DifficultyLevel.HARD: (255, 50, 50),
        }

        for difficulty in self.difficulties:
            box = self.difficulty_boxes[difficulty]
            text = self.difficulty_texts[difficulty]
            color = difficulty_colors[difficulty]

            if difficulty == self.selected_difficulty:
                # Selected - bright outline and text
                box.setPen(pg.mkPen(color=(*color, 255), width=4))
                text.setColor(pg.mkColor(*color, 255))
            else:
                # Not selected - dim
                box.setPen(pg.mkPen(color=(*color, 80), width=2))
                text.setColor(pg.mkColor(*color, 120))

    def _change_difficulty(self, direction: int):
        """Change difficulty selection by direction (-1 for left, +1 for right)."""
        new_index = self.selected_difficulty_index + direction
        if 0 <= new_index < len(self.difficulties):
            self.selected_difficulty_index = new_index
            self.selected_difficulty = self.difficulties[self.selected_difficulty_index]
            self._update_difficulty_display()

            # Play sound feedback
            if self.game_engine and self.game_engine.sound_manager:
                self.game_engine.sound_manager.play_minor_scale_sound()

    def _create_button_indicators(self):
        """Create button indicator displays."""
        self.button_items = {}
        self.button_circles = {}

        # Button positions - left hand buttons on left, right hand buttons on right
        self.button_hexagon_size = 25
        button_spacing = 60
        hand_gap = 60  # Gap between left and right hand button groups
        button_y = -50

        positions = {}

        # Position left hand buttons (right-aligned to center gap)
        num_left = len(LEFT_HAND_BUTTONS)
        left_group_width = (num_left - 1) * button_spacing if num_left > 1 else 0
        left_start_x = -hand_gap / 2 - left_group_width - self.button_hexagon_size
        for i, button in enumerate(LEFT_HAND_BUTTONS):
            positions[button] = (left_start_x + i * button_spacing, button_y)

        # Position right hand buttons (left-aligned to center gap)
        right_start_x = hand_gap / 2 + self.button_hexagon_size
        for i, button in enumerate(RIGHT_HAND_BUTTONS):
            positions[button] = (right_start_x + i * button_spacing, button_y)

        # Store positions for other methods
        self.button_positions = positions

        for button, pos in positions.items():
            # Create circle background
            color = BUTTON_COLORS[button]
            rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

            # Hexagon with outline and gradient
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

    def _create_hexagon_button(self, pos, rgb, button):
        """Create a hexagon button with gradient and outline."""
        # Create hexagon points - use consistent size (25) like game over screen
        size = self.button_hexagon_size
        angles = np.linspace(0, 2 * np.pi, 7)  # 7 points for closed hexagon
        x_points = pos[0] + size * np.cos(angles)
        y_points = pos[1] + size * np.sin(angles)

        # Create filled hexagon (starts transparent, fills on press)
        hexagon_fill = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=None,
            brush=pg.mkBrush(*rgb, 0),
            fillLevel="enclosed",
        )

        # Create outline with width 3 (consistent with game over screen)
        hexagon_outline = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=pg.mkPen(color=(*rgb, 255), width=3), brush=None
        )

        # Store fill reference for later manipulation
        hexagon_outline._fill = hexagon_fill
        self.view.addItem(hexagon_fill)

        return hexagon_outline

    def _add_start_combo_highlight(self):
        """Add visual connection between last left-hand button and first right-hand button."""
        # Line connects last left-hand button to first right-hand button (the start combo)
        left_button = LEFT_HAND_BUTTONS[-1]  # Last left-hand button
        right_button = RIGHT_HAND_BUTTONS[0]  # First right-hand button
        left_pos = self.button_positions[left_button]
        right_pos = self.button_positions[right_button]

        # Line ends at hexagon edges
        self.line_start_x = left_pos[0] + self.button_hexagon_size  # Right edge of left button
        self.line_end_x = right_pos[0] - self.button_hexagon_size  # Left edge of right button
        self.line_y = left_pos[1]  # Same as button y position

        # Main connecting line (thick, solid)
        self.combo_line = pg.PlotCurveItem(
            x=[self.line_start_x, self.line_end_x],
            y=[self.line_y, self.line_y],
            pen=pg.mkPen(color=(255, 255, 0, 150), width=12),
        )
        self.combo_line.setZValue(-5)  # Below buttons
        self.view.addItem(self.combo_line)
        self.all_elements.append({"item": self.combo_line, "pos": (0, self.line_y)})

        # Glow effect for the line
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

    def _refresh_button_labels(self):
        """Refresh the button label text items with current labels."""
        for button, text_item in self.button_items.items():
            text_item.setText(get_button_label(button))

    def _set_all_opacity(self, opacity: float):
        """Set opacity for all visual elements."""
        for elem_data in self.all_elements:
            try:
                elem_data["item"].setOpacity(opacity)
            except:
                pass  # Some items might not support opacity

    def on_key_press(self, key: str, timestamp: int) -> bool:
        """Handle key press event."""
        if key in ALL_BUTTONS:
            self.held_keys.add(key)
            self._create_button_effect(key, timestamp)

            # Check for start combo simultaneous press (within 100ms window)
            if not self.start_triggered:
                if key == self.start_left_button and self.pending_right_press:
                    # Right was pending, left just pressed - simultaneous!
                    self.pending_right_press = False
                    self._trigger_start_sequence()
                    return True
                elif key == self.start_right_button and self.pending_left_press:
                    # Left was pending, right just pressed - simultaneous!
                    self.pending_left_press = False
                    self._trigger_start_sequence()
                    return True
                elif (
                    key == self.start_left_button and self.start_right_button not in self.held_keys
                ):
                    # Left start button pressed alone - set pending and wait for right or timeout
                    self.pending_left_press = True
                    self.pending_press_time = 0.0
                elif (
                    key == self.start_right_button and self.start_left_button not in self.held_keys
                ):
                    # Right start button pressed alone - set pending and wait for left or timeout
                    self.pending_right_press = True
                    self.pending_press_time = 0.0
                elif key not in (self.start_left_button, self.start_right_button):
                    # Play minor scale sound only for non-start-combo keys
                    if self.game_engine and self.game_engine.sound_manager:
                        self.game_engine.sound_manager.play_minor_scale_sound()

                    if key in LEFT_HAND_BUTTONS:
                        self._change_difficulty(-1)  # Easier
                    elif key in RIGHT_HAND_BUTTONS:
                        self._change_difficulty(1)  # Harder

        else:
            # Any other key creates random effect
            self._create_random_effect(timestamp)

        return False

    def on_key_release(self, key: str):
        """Handle key release event."""
        self.held_keys.discard(key)

    def _create_button_effect(self, button: str, timestamp: int):
        """Create visual effect when button is pressed."""
        if button not in self.button_circles:
            return

        # Get button position from stored positions
        pos = self.button_positions[button]

        # Create expanding ring
        ring_effect = ExpandingRingEffect(self.view, pos, BUTTON_COLORS[button])
        self.active_effects.append(ring_effect)

        # Create upward laser
        laser_effect = IntroLaserEffect(self.view, pos, BUTTON_COLORS[button])
        self.active_effects.append(laser_effect)

        # Enlarge and brighten hexagon temporarily (consistent with game over screen)
        rgb = tuple(int(BUTTON_COLORS[button][i : i + 2], 16) for i in (1, 3, 5))
        bright_rgb = tuple(min(255, int(c + 50)) for c in rgb)  # Brighten
        hexagon = self.button_circles[button]
        hexagon.setPen(pg.mkPen(color=(*bright_rgb, 255), width=6))  # Thicker outline
        hexagon._fill.setBrush(pg.mkBrush(*bright_rgb, 200))

    def _create_random_effect(self, timestamp: int):
        """Create random visual effect."""
        # Random position
        x = random_manager.uniform(-350, 350)
        y = random_manager.uniform(-250, 250)
        pos = (x, y)

        # Random color
        color = random_manager.choice(list(BUTTON_COLORS.values()))

        # Random effect type
        effect_type = random_manager.choice(["ring", "burst", "spiral"])

        if effect_type == "ring":
            effect = ExpandingRingEffect(self.view, pos, color)
        elif effect_type == "burst":
            effect = ParticleBurstEffect(self.view, pos, color)
        else:
            effect = SpiralEffect(self.view, pos, color)

        self.active_effects.append(effect)

    def _show_partial_press_feedback(self, unpressed_button: str):
        """Show feedback when only LEFT or RIGHT is pressed (not both)."""
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

    def _trigger_start_sequence(self):
        """Trigger game start sequence."""
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
            elem_data["angular_velocity"] = random_manager.uniform(-360, 360)  # degrees per second
            elem_data["rotation"] = 0

        # Trigger screen shake if game engine is available
        print("IntroScreen: Calling play_twinkle_sound.")
        self.game_engine.sound_manager.play_twinkle_sound()
        self.game_engine.shake_manager.trigger_shake(magnitude=8.0, duration=0.8)

        self.start_triggered = True

    def update(self, dt: float):
        """Update intro screen animations."""
        if not self.active:
            return

        self.elapsed_time += dt

        # Handle fade-in
        if self.fade_in_progress < self.fade_in_duration:
            self.fade_in_progress += dt
            opacity = min(1.0, self.fade_in_progress / self.fade_in_duration)
            self._set_all_opacity(opacity)

        # Handle explosion transition
        if self.exploding:
            explosion_time = self.elapsed_time - self.explosion_start_time
            explosion_progress = explosion_time / self.explosion_duration

            if explosion_progress < 1.0:
                # Update expanding ring
                ring_radius = explosion_progress * 500
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
                    # Trigger callback to start game
                    if self.on_start_callback:
                        self.on_start_callback()
            return  # Skip normal animations during explosion

        # Normal animations (when not exploding)
        # Pulse instruction alpha
        alpha = 0.7 + 0.3 * math.sin(self.elapsed_time * 3)

        # Pulse F-J connecting line (unified with game over screen)
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

        # Reset button appearance if not held (width=3 consistent with game over screen)
        for button, hexagon in self.button_circles.items():
            # Skip the button being flashed
            if self.partial_press_triggered and button == self.partial_flash_button:
                continue
            if button not in self.held_keys:
                rgb = tuple(int(BUTTON_COLORS[button][i : i + 2], 16) for i in (1, 3, 5))
                # Reset to normal appearance
                hexagon.setPen(pg.mkPen(color=(*rgb, 255), width=3))
                hexagon._fill.setBrush(pg.mkBrush(*rgb, 120))

        # Process pending start combo presses after 100ms window expires
        if self.pending_left_press or self.pending_right_press:
            self.pending_press_time += dt
            if self.pending_press_time >= self.simultaneous_window:
                # Window expired - trigger the independent press action
                if self.pending_left_press:
                    self.pending_left_press = False
                    self._show_partial_press_feedback(self.start_right_button),
                    self._change_difficulty(-1)
                elif self.pending_right_press:
                    self.pending_right_press = False
                    self._show_partial_press_feedback(self.start_left_button),
                    self._change_difficulty(1)

        # Update active effects
        completed_effects = []
        for effect in self.active_effects:
            if not effect.update(dt):
                completed_effects.append(effect)

        # Remove completed effects
        for effect in completed_effects:
            effect.cleanup()
            self.active_effects.remove(effect)

    def cleanup(self):
        """Remove all visual elements."""
        if not self.active:
            return

        # Remove expanding ring if it exists
        self.view.removeItem(self.center_ring)

        # Remove all tracked elements
        for elem_data in self.all_elements:
            try:
                self.view.removeItem(elem_data["item"])
            except:
                pass  # Item might already be removed

        # Remove button indicators
        for text in self.button_items.values():
            self.view.removeItem(text)
        for hexagon in self.button_circles.values():
            self.view.removeItem(hexagon)
            self.view.removeItem(hexagon._fill)

        # Clear active effects
        for effect in self.active_effects:
            effect.cleanup()
        self.active_effects.clear()

        self.active = False
