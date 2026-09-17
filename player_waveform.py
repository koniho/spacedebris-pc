"""Player health waveform visualization."""

import math
import time
import random_manager
import numpy as np
import pyqtgraph as pg
from typing import Tuple


class PlayerHealthWaveform:
    """Animated waveform representing player health and activity."""

    def __init__(self, view, screen_width: int = 800, screen_height: int = 600):
        """Initialize player health waveform."""
        self.view = view
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Waveform positioning (zero at bottom edge, 5% of screen height)
        self.base_y = -screen_height // 2  # Bottom edge of screen
        self.max_amplitude = screen_height * 0.05  # 5% of screen height

        # Health system (0.0 to 1.1 - can go up to 110% with perfect waves)
        self.health = 1.0  # Full health
        self.max_health = 1.1  # Can exceed 100% up to 110%

        # Animation state
        self.time_offset = 0.0
        self.activity_boost = 0.0  # Boost when enemy attacked
        self.activity_decay = 2.0  # How fast activity boost decays
        self.activity_color_timer = 0.0  # Timer for color flash animation
        self.activity_color_duration = 0.5  # How long color flash lasts
        self.damage_flash_timer = 0.0  # Timer for red damage flash
        self.damage_flash_duration = 0.3  # How long red damage flash lasts
        self.disabled_flash_timer = 0.0  # Timer for gray disabled flash
        self.disabled_flash_duration = 0.3  # How long gray disabled flash lasts

        # Organic animation offsets for jello-like behavior
        self.phase_offsets = random_manager.np_uniform(0, 2 * math.pi, 5)  # Random phase shifts
        self.freq_multipliers = random_manager.np_uniform(0.8, 1.2, 5)  # Frequency variations

        # Targeted activity spikes (for enemy-specific animations)
        self.targeted_spikes = []  # List of active targeted spikes

        # Letter collection animations
        self.letter_animations = []  # List of active letter collection animations
        self.letter_text_items = []  # Visual text items for falling letters

        # Death sequence state
        self.death_sequence_active = False
        self.death_progress = 0.0  # 0.0 to 1.0

        # Perfect wave bonus state
        self.perfect_wave_timer = 0.0  # Timer for perfect wave animation
        self.perfect_wave_duration = 1.0  # How long the perfect wave effect lasts
        self.perfect_wave_amplitude_boost = 0.0  # Extra amplitude during perfect wave

        # Cache waveform data for interpolation
        self.cached_x_points = None
        self.cached_y_points = None

        # Waveform parameters
        self.wave_width = screen_width
        self.wavelength = screen_width * 0.75  # 75% of screen width
        self.num_points = 300
        self.base_frequency = (2 * math.pi) / self.wavelength  # Base wave frequency
        self.detail_frequency = (2 * math.pi) / (self.wavelength * 0.3)  # Detail wave frequency

        # Visual elements
        self.waveform_fill = None
        self.waveform_line = None
        self.baseline = None

        self._create_waveform()

    def _create_waveform(self):
        """Create the waveform visual elements."""
        # Create baseline (flat line at bottom)
        baseline_x = [-self.wave_width // 2, self.wave_width // 2]
        baseline_y = [self.base_y, self.base_y]

        self.baseline = pg.PlotCurveItem(
            x=baseline_x, y=baseline_y, pen=pg.mkPen(color=(0, 100, 150, 100), width=2)
        )
        self.view.addItem(self.baseline)

        # Create main waveform with fill
        self.waveform_fill = pg.PlotCurveItem(
            pen=None,
            brush=pg.mkBrush(0, 150, 255, 80),  # Semi-transparent blue
            fillLevel=self.base_y,
        )
        self.view.addItem(self.waveform_fill)

        # Create waveform outline
        self.waveform_line = pg.PlotCurveItem(pen=pg.mkPen(color=(0, 200, 255, 200), width=3))
        self.view.addItem(self.waveform_line)

    def _generate_waveform_points(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate waveform points based on current health and activity."""
        x_points = np.linspace(-self.wave_width // 2, self.wave_width // 2, self.num_points)

        # Create organic, jello-like wave components with multiple layers
        # Each layer has slightly different frequency and phase for organic movement
        wave_layers = []

        # Primary wave layer - stationary, no scrolling
        wave1 = np.sin(
            x_points * self.base_frequency * self.freq_multipliers[0] + self.phase_offsets[0]
        ) * np.sin(
            self.time_offset * 1.2
        )  # Slow amplitude modulation instead of scrolling

        # Secondary wave layer - different phase but no position scrolling
        wave2 = (
            0.6
            * np.sin(
                x_points * self.base_frequency * self.freq_multipliers[1] * 1.3
                + self.phase_offsets[1]
            )
            * np.sin(self.time_offset * 1.8 + math.pi / 3)
        )

        # Tertiary detail wave - position-locked but amplitude varies
        wave3 = (
            0.4
            * np.sin(
                x_points * self.detail_frequency * self.freq_multipliers[2] + self.phase_offsets[2]
            )
            * np.sin(self.time_offset * 2.1 + math.pi / 2)
        )

        # High frequency texture wave - stationary with breathing
        wave4 = (
            0.2
            * np.sin(
                x_points * self.detail_frequency * self.freq_multipliers[3] * 2.5
                + self.phase_offsets[3]
            )
            * (0.7 + 0.3 * np.sin(self.time_offset * 3.2))
        )

        # Slow modulation wave for organic breathing effect
        wave5 = (
            0.3
            * np.sin(
                x_points * self.base_frequency * self.freq_multipliers[4] * 0.4
                + self.phase_offsets[4]
            )
            * (0.8 + 0.2 * np.sin(self.time_offset * 0.8))
        )

        # Health affects amplitude and variation
        # Non-linear scaling: at 25% health, display at 50% amplitude
        # This makes the waveform more visible at low health
        # Using sqrt gives us: health=1.0 -> 1.0, health=0.25 -> 0.5, health=0 -> 0
        # For health > 1.0, scale linearly above sqrt(1.0)
        base_amplitude = self.max_amplitude * (1.0 + self.perfect_wave_amplitude_boost)
        if self.health > 1.0:
            # Above 100%: continue scaling linearly from 1.0
            health_amplitude = (1.0 + (self.health - 1.0) * 0.5) * base_amplitude
        else:
            health_amplitude = math.sqrt(self.health) * base_amplitude
        variation_factor = min(1.0, self.health) * 0.7 + 0.3  # Less variation at low health

        # Activity boost adds prominent energy spikes
        # Cap activity_factor to prevent excessive amplitude
        activity_factor = min(2.5, 1.0 + self.activity_boost * 4.0)

        # Scale down spike intensity when many spikes are active
        num_spikes = len(self.targeted_spikes)
        spike_scale = 1.0 / max(1.0, num_spikes * 0.4) if num_spikes > 0 else 1.0

        # Add targeted spikes for specific enemy positions using sinc function
        for spike in self.targeted_spikes:
            spike_center = spike["x"]
            spike_intensity = spike["intensity"] * 2
            spike_age = spike["age"]
            spike_duration = spike["duration"]

            # Calculate spike strength based on age (fade out over time)
            age_factor = max(0, 1.0 - (spike_age / spike_duration))

            # Create sinc-based spike under enemy position
            spike_width = 25  # Width control for sinc function - narrower for sharper spikes
            distance_from_center = (x_points - spike_center) / spike_width

            # Avoid division by zero at the center
            safe_distance = np.where(
                np.abs(distance_from_center) < 1e-10, 1e-10, distance_from_center
            )

            # Sinc function: sin(πx)/(πx)
            sinc_factor = np.sin(np.pi * safe_distance) / (np.pi * safe_distance)

            # At the exact center, sinc(0) = 1
            sinc_factor = np.where(np.abs(distance_from_center) < 1e-10, 1.0, sinc_factor)

            # Modulate sinc with time for dynamic reaching effect
            time_modulation = (
                np.sin(self.time_offset * 8 + spike_age * 6) * 0.3
                + np.sin(self.time_offset * 12 + spike_age * 9) * 0.2
                + 0.5
            )

            # Create the final spike wave using sinc
            spike_wave = (
                spike_intensity
                * age_factor
                * sinc_factor
                * time_modulation
                * spike_scale  # Scale down when many spikes active
                * 8.0  # Amplify for visibility
            )
            wave1 += spike_wave

        # Add general activity boost if present (for non-targeted activity)
        if self.activity_boost > 0 and not self.targeted_spikes:
            # General activity ripples across entire waveform
            activity_wave = (
                self.activity_boost
                * 1.5
                * np.sin(x_points * self.base_frequency * 2 + self.time_offset * 10)
            )
            wave1 += activity_wave

        # Combine all wave layers with organic mixing
        combined_wave = (wave1 + wave2 + wave3 + wave4 + wave5) * variation_factor * activity_factor

        # Add standing wave effect when disabled (being hit by disable ray)
        if self.disabled_flash_timer > 0:
            # Standing wave with period = 1/10 of screen width
            standing_wave_period = self.screen_width / 10.0
            standing_wave_freq = (2 * math.pi) / standing_wave_period
            # Amplitude = 1/3 of nominal waveform height
            standing_wave_amplitude = 1.0 / 3.0
            # Standing wave: spatial sine * temporal sine (creates nodes and antinodes)
            standing_wave = (
                standing_wave_amplitude
                * np.sin(x_points * standing_wave_freq)
                * np.sin(self.time_offset * 15)  # Fast temporal oscillation
            )
            combined_wave += standing_wave

        # Apply death sequence fading
        if self.death_sequence_active:
            death_fade = 1.0 - self.death_progress
            combined_wave *= death_fade
            # Health amplitude already has sqrt scaling applied
            health_amplitude *= death_fade

        # Ensure all values are positive (above zero baseline)
        # Add base offset to keep waveform above zero
        base_offset = 0.3  # Minimum height above baseline
        wave_height = base_offset + (combined_wave * 0.5 + 0.5) * 0.7  # Normalize and scale

        # Calculate final Y positions (always above base_y)
        y_points = self.base_y + wave_height * health_amplitude

        return x_points, y_points

    def _get_health_color(self) -> Tuple[int, int, int, int]:
        """Get color based on current health, death state, damage flash, and activity."""
        # Check for perfect wave flash first (highest priority - yellow/gold)
        if self.perfect_wave_timer > 0:
            # Yellow/gold flash with smooth ease-in and fade-out
            flash_progress = 1.0 - (self.perfect_wave_timer / self.perfect_wave_duration)

            # Ease in during first 20% of animation, then fade out
            if flash_progress < 0.2:
                # Ease in: use smoothstep for gradual transition
                t = flash_progress / 0.2
                yellow_intensity = t * t * (3 - 2 * t)  # Smoothstep
            else:
                # Fade out over remaining 80%
                t = (flash_progress - 0.2) / 0.8
                yellow_intensity = 1.0 - t

            # Subtle pulsing on top of the base intensity
            pulse = 0.1 * math.sin(flash_progress * math.pi * 4)

            r = int(255 * yellow_intensity)
            g = int(255 * yellow_intensity * (0.9 + pulse))
            b = int(255 * (1 - yellow_intensity * 0.8))  # Blend from blue to yellow
            alpha = int(255 * math.sqrt(min(1.0, self.health)))

            return (r, g, b, alpha)

        # Check for disabled flash (gray)
        if self.disabled_flash_timer > 0:
            # Gray disabled flash with fade out
            flash_progress = 1.0 - (self.disabled_flash_timer / self.disabled_flash_duration)
            flash_intensity = math.sin(flash_progress * math.pi)  # Sine fade for smooth transition

            # Gray flash
            gray_value = int(180 * flash_intensity + 75 * (1 - flash_intensity))
            alpha = int(255 * math.sqrt(self.health))  # Use sqrt scaling for visibility

            return (gray_value, gray_value, gray_value, alpha)

        # Check for damage flash (red)
        if self.damage_flash_timer > 0:
            # Red damage flash with fade out
            flash_progress = 1.0 - (self.damage_flash_timer / self.damage_flash_duration)
            flash_intensity = math.sin(flash_progress * math.pi)  # Sine fade for smooth transition

            # Bright red flash
            r = 255
            g = int(50 * (1 - flash_intensity))  # Slight green for darker red
            b = int(50 * (1 - flash_intensity))  # Slight blue for darker red
            alpha = int(255 * math.sqrt(self.health))  # Use sqrt scaling for visibility

            return (r, g, b, alpha)

        if self.death_sequence_active:
            # Transition from blue -> orange -> black during death
            if self.death_progress < 0.5:
                # Blue to orange phase
                t = self.death_progress * 2
                r = int(0 + (255 * t))
                g = int(150 + (100 * t))
                b = int(255 * (1 - t))
                alpha = int(200 * (1 - self.death_progress * 0.5))
            else:
                # Orange to black phase
                t = (self.death_progress - 0.5) * 2
                r = int(255 * (1 - t))
                g = int(150 * (1 - t))
                b = 0
                alpha = int(200 * (1 - self.death_progress * 0.5))

            return (r, g, b, alpha)

        # Check for activity color flash
        activity_flash_intensity = 0.0
        if self.activity_color_timer > 0:
            # Create a flash effect that fades over time
            flash_progress = 1.0 - (self.activity_color_timer / self.activity_color_duration)
            # Use sine wave for smooth flash animation
            activity_flash_intensity = math.sin(flash_progress * math.pi) * 0.8

        # Normal health-based coloring (blue spectrum)
        base_r, base_g, base_b = 0, 0, 0
        if self.health > 1.0:
            # Above 100%: cyan with yellow tint (greenish-cyan to gold)
            # At 110% health, t = 1.0
            t = min(1.0, (self.health - 1.0) / 0.1)
            base_r = int(0 + (200 * t))  # Add red for yellow
            base_g = int(250 + (5 * t))  # Keep green high
            base_b = int(255 * (1 - t * 0.6))  # Reduce blue for yellow
        elif self.health > 0.6:
            # Healthy: bright blue to cyan
            t = (self.health - 0.6) / 0.4
            base_r = int(0 + (50 * (1 - t)))
            base_g = int(150 + (100 * t))
            base_b = 255
        elif self.health > 0.3:
            # Moderate: blue to purple-blue
            t = (self.health - 0.3) / 0.3
            base_r = int(100 * (1 - t))
            base_g = int(100 + (50 * t))
            base_b = 255
        else:
            # Low health: purple-blue to dark blue
            t = self.health / 0.3
            base_r = int(150 * (1 - t))
            base_g = int(50 + (50 * t))
            base_b = int(200 + (55 * t))

        # Apply activity color flash (bright white-blue flash)
        if activity_flash_intensity > 0:
            flash_r = 255
            flash_g = 255
            flash_b = 255

            # Blend base color with flash color
            r = int(base_r + (flash_r - base_r) * activity_flash_intensity)
            g = int(base_g + (flash_g - base_g) * activity_flash_intensity)
            b = int(base_b + (flash_b - base_b) * activity_flash_intensity)
        else:
            r, g, b = base_r, base_g, base_b

        # Activity boost adds brightness to base colors
        if self.activity_boost > 0:
            boost_factor = 1.0 + self.activity_boost * 0.3
            r = min(255, int(r * boost_factor))
            g = min(255, int(g * boost_factor))
            b = min(255, int(b * boost_factor))

        # Use sqrt scaling for visibility, capped at 1.0 for alpha calculation
        alpha = int(200 * math.sqrt(min(1.0, self.health)))
        return (r, g, b, alpha)

    def update(self, dt: float):
        """Update waveform animation."""
        self.time_offset += dt

        # Decay activity boost
        if self.activity_boost > 0:
            self.activity_boost = max(0, self.activity_boost - dt * self.activity_decay)

        # Update activity color flash timer
        if self.activity_color_timer > 0:
            self.activity_color_timer = max(0, self.activity_color_timer - dt)

        # Update damage flash timer
        if self.damage_flash_timer > 0:
            self.damage_flash_timer = max(0, self.damage_flash_timer - dt)

        # Update disabled flash timer
        if self.disabled_flash_timer > 0:
            self.disabled_flash_timer = max(0, self.disabled_flash_timer - dt)

        # Update perfect wave timer and amplitude boost
        if self.perfect_wave_timer > 0:
            self.perfect_wave_timer = max(0, self.perfect_wave_timer - dt)
        if self.perfect_wave_amplitude_boost > 0:
            # Decay amplitude boost slowly
            self.perfect_wave_amplitude_boost = max(0, self.perfect_wave_amplitude_boost - dt * 0.1)

        # Update targeted spikes
        active_spikes = []
        for spike in self.targeted_spikes:
            spike["age"] += dt
            if spike["age"] < spike["duration"]:
                active_spikes.append(spike)
        self.targeted_spikes = active_spikes

        # Update letter collection animations
        active_letters = []
        for letter_anim in self.letter_animations:
            letter_anim["age"] += dt
            if letter_anim["age"] < letter_anim["duration"]:
                active_letters.append(letter_anim)
            else:
                # Letter reached waveform - just remove the text item (no impact spike)
                self.view.removeItem(letter_anim["text_item"])
        self.letter_animations = active_letters

        # Update death sequence
        if self.death_sequence_active:
            self.death_progress = min(1.0, self.death_progress + dt * 1.5)  # 1.5 = death speed

        # Periodically update organic movement parameters for more natural jello effect
        if int(self.time_offset * 4) % 10 == 0:  # Every 2.5 seconds
            self.phase_offsets += random_manager.np_uniform(-0.1, 0.1, 5)  # Slight phase drift
            self.freq_multipliers += random_manager.np_uniform(
                -0.02, 0.02, 5
            )  # Slight frequency drift
            # Keep multipliers in reasonable bounds
            self.freq_multipliers = np.clip(self.freq_multipliers, 0.6, 1.4)

        # Generate new waveform points
        x_points, y_points = self._generate_waveform_points()

        # Cache the waveform data for interpolation
        self.cached_x_points = x_points
        self.cached_y_points = y_points

        # Get current health color
        line_color = self._get_health_color()
        fill_color = (line_color[0], line_color[1], line_color[2], line_color[3] // 3)

        # Update visual elements with fill level following base_y position
        self.waveform_fill.setData(
            x=x_points, y=y_points, brush=pg.mkBrush(*fill_color), fillLevel=self.base_y
        )

        self.waveform_line.setData(x=x_points, y=y_points, pen=pg.mkPen(color=line_color, width=3))

        # Update baseline position to follow base_y
        baseline_x = [-self.wave_width // 2, self.wave_width // 2]
        baseline_y = [self.base_y, self.base_y]
        self.baseline.setData(x=baseline_x, y=baseline_y)

        # Update falling letter visuals
        self._update_letter_visuals()

    def _update_letter_visuals(self):
        """Update positions and appearance of falling letters."""
        for letter_anim in self.letter_animations:
            progress = letter_anim["age"] / letter_anim["duration"]

            # Calculate current position
            current_y = (
                letter_anim["start_y"]
                + (letter_anim["target_y"] - letter_anim["start_y"]) * progress
            )

            # Update text item position
            letter_anim["text_item"].setPos(letter_anim["x"], current_y)

            # Add some visual effects as letter falls
            # Scale gets smaller as it approaches waveform
            scale_factor = 1.0 - (progress * 0.3)  # Scale down to 70%
            opacity = 1.0 - (progress * 0.1)  # Slight fade

            # Update text item properties
            letter_anim["text_item"].setOpacity(opacity)

            # Cycle through blue colors as it falls
            blue_intensity = int(255 * (0.7 + 0.3 * abs(math.sin(progress * math.pi * 4))))
            letter_anim["text_item"].setColor((0, blue_intensity, 255))

    def take_damage(self, damage: float = 0.25):
        """Take damage and reduce health."""
        self.health = max(0.0, self.health - damage)

        # Add activity spike when taking damage
        self.activity_boost = min(1.0, self.activity_boost + 0.8)

        # Trigger red damage flash animation
        self.damage_flash_timer = self.damage_flash_duration

    def trigger_disabled_flash(self, duration: float = 0.3):
        """Trigger gray flash for disabled state (e.g., shield block).

        Unlike take_damage, this doesn't reduce health - just visual feedback.
        """
        self.disabled_flash_timer = duration
        self.disabled_flash_duration = duration

    def is_disabled(self) -> bool:
        """Check if waveform is currently in disabled state."""
        return self.disabled_flash_timer > 0

    def add_activity(self, intensity: float = 0.5):
        """Add general activity boost when enemy is attacked."""
        self.activity_boost = min(1.0, self.activity_boost + intensity)

        # Trigger color flash animation
        self.activity_color_timer = self.activity_color_duration

        # Add more dramatic organic variation on activity
        variation = random_manager.np_uniform(-0.3, 0.3, 5) * intensity
        self.phase_offsets += variation
        self.freq_multipliers += variation * 0.5
        # Keep multipliers in bounds
        self.freq_multipliers = np.clip(self.freq_multipliers, 0.6, 1.4)

    def add_targeted_activity(self, enemy_x: float, intensity: float = 1.0, duration: float = 0.8):
        """Add targeted activity spike under specific enemy position."""
        # Create a new targeted spike
        spike = {
            "x": enemy_x,  # X position of the enemy
            "intensity": intensity,
            "age": 0.0,
            "duration": duration,
        }
        self.targeted_spikes.append(spike)

        # Also trigger color flash
        self.activity_color_timer = self.activity_color_duration

        # Add organic variation for this specific spike
        variation = random_manager.np_uniform(-0.2, 0.2, 5) * intensity
        self.phase_offsets += variation
        self.freq_multipliers += variation * 0.3
        self.freq_multipliers = np.clip(self.freq_multipliers, 0.6, 1.4)

    def add_letter_activity(self, letter_x: float, intensity: float = 0.4):
        """Add small activity spike when typing individual letters."""
        # Create a smaller, shorter spike for letter typing
        spike = {
            "x": letter_x,  # X position of the letter
            "intensity": intensity,
            "age": 0.0,
            "duration": 0.3,  # Shorter duration for letters
        }
        self.targeted_spikes.append(spike)

        # Very subtle color flash for letters
        self.activity_color_timer = max(
            self.activity_color_timer, self.activity_color_duration * 0.3
        )

    def add_letter_collection(self, letter_x: float, letter: str):
        """Add letter collection animation moving to waveform."""
        # Create visible text item for the falling letter
        from font_manager import font_manager
        from config import get_button_label

        text_item = pg.TextItem(
            text=get_button_label(letter), color=(0, 255, 255), anchor=(0.5, 0.5)
        )

        text_item.setFont(font_manager.get_enemy_letter_font(16, bold=True))
        text_item.setPos(letter_x, 0)  # Will be updated in animation
        self.view.addItem(text_item)

        # Create letter collection animation
        animation = {
            "x": letter_x,  # X position where letter will be collected
            "letter": letter,
            "age": 0.0,
            "duration": 0.6,  # Time for letter to reach waveform
            "start_y": 0,  # Will be set when letter starts falling
            "target_y": self.base_y,  # Bottom of screen
            "text_item": text_item,  # Reference to visual text item
        }
        self.letter_animations.append(animation)

    def start_death_sequence(self):
        """Start the death sequence animation."""
        self.death_sequence_active = True
        self.death_progress = 0.0

    def reset_health(self):
        """Reset to full health (for game restart)."""
        self.health = 1.0
        self.activity_boost = 0.0
        self.activity_color_timer = 0.0
        self.death_sequence_active = False
        self.death_progress = 0.0
        self.perfect_wave_timer = 0.0
        self.perfect_wave_amplitude_boost = 0.0
        self.targeted_spikes.clear()

        # Clean up any remaining letter text items
        for letter_anim in self.letter_animations:
            self.view.removeItem(letter_anim["text_item"])
        self.letter_animations.clear()

    def set_health(self, health: float):
        """Set health to specific value (0.0 to 1.0)."""
        self.health = max(0.0, min(1.0, health))

    def get_health(self) -> float:
        """Get current health value (0.0 to 1.0)."""
        return self.health

    def is_dead(self) -> bool:
        """Check if health has reached zero."""
        return self.health <= 0.0

    def trigger_perfect_wave_bonus(self):
        """Trigger perfect wave bonus: yellow flash, amplitude boost, and health gain."""
        # Start the yellow flash animation
        self.perfect_wave_timer = self.perfect_wave_duration

        # Add 10% amplitude boost (will animate and decay)
        self.perfect_wave_amplitude_boost = 0.1

        # Add 10% health (capped at max)
        self.health = min(self.max_health, self.health + 0.1)

        # Add activity boost for visual excitement
        self.activity_boost = min(1.0, self.activity_boost + 0.8)

    def get_y_at_x(self, x_pos: float) -> float:
        """Get the Y position of the waveform at a specific X position.

        Args:
            x_pos: The X coordinate to query

        Returns:
            The Y coordinate of the waveform at that X position
        """
        # Use cached waveform data if available, otherwise generate
        if self.cached_x_points is None or self.cached_y_points is None:
            x_points, y_points = self._generate_waveform()
            self.cached_x_points = x_points
            self.cached_y_points = y_points
        else:
            x_points = self.cached_x_points
            y_points = self.cached_y_points

        # Find the closest X points for interpolation
        x_array = np.array(x_points) if not isinstance(x_points, np.ndarray) else x_points
        y_array = np.array(y_points) if not isinstance(y_points, np.ndarray) else y_points

        # If x_pos is outside the range, return the edge values
        if x_pos <= x_array[0]:
            return float(y_array[0])
        if x_pos >= x_array[-1]:
            return float(y_array[-1])

        # Linear interpolation between points
        return float(np.interp(x_pos, x_array, y_array))

    def get_letter_positions(self):
        """Get current positions of falling letters for visualization."""
        positions = []
        for letter_anim in self.letter_animations:
            progress = letter_anim["age"] / letter_anim["duration"]
            # Animate from enemy position down to waveform
            current_y = (
                letter_anim["start_y"]
                + (letter_anim["target_y"] - letter_anim["start_y"]) * progress
            )
            positions.append(
                {
                    "x": letter_anim["x"],
                    "y": current_y,
                    "letter": letter_anim["letter"],
                    "progress": progress,
                }
            )
        return positions

    def has_active_animations(self) -> bool:
        """Check if there are any active letter collection animations."""
        return len(self.letter_animations) > 0

    def cleanup(self):
        """Remove all visual elements."""
        if self.waveform_fill:
            self.view.removeItem(self.waveform_fill)
        if self.waveform_line:
            self.view.removeItem(self.waveform_line)
        if self.baseline:
            self.view.removeItem(self.baseline)

        # Clean up letter text items
        for letter_anim in self.letter_animations:
            self.view.removeItem(letter_anim["text_item"])
        self.letter_animations.clear()

        self.waveform_fill = None
        self.waveform_line = None
        self.baseline = None
