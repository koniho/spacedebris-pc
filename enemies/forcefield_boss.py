"""Boss enemy implementation with force field and projectiles."""

import math
import random_manager
from typing import List, Tuple, Optional
import numpy as np
import pyqtgraph as pg
from enemies.base_boss import BaseBoss
from enemies.linked_enemy_pair import LinkedEnemyPair
from enemies.rapid_hit_enemy import RapidHitEnemy
from effects.boss_death_animation import BossDeathAnimation
from effects.particle_effects import ParticleSystem, OrbitalParticleSystem
from config import BUTTON_COLORS, ALL_BUTTONS, get_button_label, generate_evenly_distributed_letters
from font_manager import font_manager


class ForcefieldBoss(BaseBoss):
    """Boss enemy with circular core, rotating force field, and projectiles."""

    def __init__(
        self,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
        destruction_callback=None,
        sound_manager=None,  # Add sound_manager to __init__
    ):
        """Initialize boss enemy."""
        super().__init__(view, laser_manager, waveform)
        self.destruction_callback = destruction_callback
        self.sound_manager = sound_manager  # Initialize sound_manager

        # Boss position and movement
        self.center_pos = pos
        self.entry_speed = 100  # Fast entry speed when scrolling down
        self.horizontal_speed = 40  # Side-to-side movement speed
        self.vertical_speed = 0  # No vertical movement after entry

        # Movement phase tracking
        self.movement_phase = "entering"  # "entering" or "side_to_side"
        self.target_y = 150  # Target Y position to stop at (upper part of screen)
        self.horizontal_direction = (
            1 if random_manager.random() > 0.5 else -1
        )  # Random initial direction
        self.horizontal_bounds = (-200, 200)  # X movement bounds

        # Sinusoidal vertical motion
        self.vertical_oscillation_time = 0.0  # Timer for sine wave
        self.vertical_oscillation_period = 2.0  # 2 second period
        self.vertical_oscillation_amplitude = 20  # +/- 20 pixels vertical movement

        # Core configuration
        self.core_letters = generate_evenly_distributed_letters(
            6
        )  # 6 letters with even distribution
        self.core_radius = 40  # Radius of letter circle
        self.core_rotation = 0.0  # Current rotation angle of core
        self.core_base_rotation_speed = (
            -20
        )  # Base rotation speed (negative = opposite to forcefield)
        self.core_rotation_speed = self.core_base_rotation_speed  # Current rotation speed

        # Create core enemies - each letter is a RapidHitEnemy with a single letter
        self.core_enemies: List[RapidHitEnemy] = []
        self._create_core_enemies()

        # Force field configuration
        self.forcefield_base_radius = 104  # 30% larger than 80
        self.forcefield_radius = self.forcefield_base_radius
        self.forcefield_rotation = 0.0  # Current rotation angle
        self.forcefield_base_rotation_speed = 90  # Base rotation speed
        self.forcefield_rotation_speed = (
            self.forcefield_base_rotation_speed
        )  # Current rotation speed
        self.forcefield_gap_size = 60  # Gap size in degrees
        self.forcefield_lines = []
        self.forcefield_holding = False
        self.forcefield_segment_count = 16  # Number of particle positions around arc

        # Consolidated forcefield rendering (single ScatterPlotItem instead of 16)
        self.forcefield_scatter = None  # Will be created in _create_forcefield_visuals
        self.forcefield_flash_timer = 0.0
        self.forcefield_flash_segments = set()  # Which segments are flashing
        self.forcefield_color_blend = 0.0  # For hold state color transition
        # Hold transition animation
        self.hold_transition_duration = 0.25  # 250ms transition
        self.hold_transition_timer = 0.0
        self.hold_transitioning = False  # True while transitioning to held state
        self.stored_rotation_speed = self.forcefield_rotation_speed
        # Shield diameter animation
        self.shield_pulse_time = 0.0  # Timer for pulsing animation
        self.shield_pulse_period = 1.2  # 1.2 second period for smoother animation
        self.shield_pulse_amplitude = 4  # Pixels of variation
        # Choose hold letter - prefer letters not in core, or least frequent in core
        self.forcefield_hold_letter = self._choose_hold_letter()
        self.currently_held_button = None  # Track which button is actually being held
        self.core_hit_counter = 0  # Count core hits to change hold letter
        self.core_hit_max = 3  # Change letter after 3 core hits

        # Projectile system
        self.projectile_timer = 0.0
        self.projectile_interval = 4.6  # Spawn projectiles 30% more frequently (was 6.0)
        self.projectiles: List[LinkedEnemyPair] = []

        # Barrage attack: periodic spread of projectiles
        self.barrage_timer = 0.0
        self.barrage_interval = 6.0  # First barrage after 6 seconds
        self.barrage_count = 1  # Projectiles per barrage
        self.barrage_number = 0  # Escalation counter

        # Counter-attack: fire back after core hit
        self.counter_attack_queue = 0  # Pending counter-attack projectiles
        self.counter_attack_delay = 0.0  # Brief delay before firing

        # Visual elements
        self._create_forcefield_visuals()

        # Shield hit animation
        self.shield_hit_timer = 0.0
        self.shield_hit_duration = 0.3

        # Vulnerability indicator animation time
        self.vulnerability_pulse_time = 0.0

        # Track which core enemies are currently vulnerable (for outline color changes)
        self._vulnerable_enemies = set()

        # Particle effects system
        self.particle_system = ParticleSystem(self.view)

        # Core orbital particle system (purple/cyan orb at center)
        self.core_orbital_particles = OrbitalParticleSystem(
            self.view,
            size=6,
            base_radius=self.core_radius - 30,  # Slightly smaller than core enemy orbit
            radius_variance=2,
            radius_oscillation_speed=2.0,
            orbit_speed=1.5,
            fade_rate=80,
        )
        self.core_orbital_particles.set_center(self.center_pos[0], self.center_pos[1])
        # Spawn initial particles with purple and cyan colors
        self.core_orbital_particles.spawn((128, 0, 255), count=1)  # Purple
        self.core_orbital_particles.spawn((0, 255, 255), count=1)  # Cyan

        # Animations (for core enemy death animations)
        self.animations = []

        # Track if boss is defeated
        self.defeated = False

        # Shield hold waveform visualization
        self.shield_waveforms = []  # List of waveform graphics
        self.shield_waveform_fade_timer = 0.0  # Timer for fade-out animation
        self.shield_waveform_time = 0.0  # Time for waveform animation

        # Pre-computed waveform x-point arrays (optimization - avoid np.linspace per frame)
        self._waveform_num_points = 50
        self._waveform_x_left = None  # Will be computed on first use
        self._waveform_x_right = None
        self._waveform_amplitude_left = np.linspace(0, 1, self._waveform_num_points)
        self._waveform_amplitude_right = np.linspace(1, 0, self._waveform_num_points)

        # Forcefield damage visual state
        self.forcefield_damage_flash = 0.0  # Flash timer when core destroyed
        self.forcefield_damage_flash_duration = 0.5
        self.forcefield_ripple_scale = 1.0  # Scale multiplier for ripple effect
        self.forcefield_color_animation_time = 0.0  # For color pulsing

    def _choose_hold_letter(self):
        """Choose a hold letter that won't conflict with remaining core letters.

        If only one unique letter remains in the core, the hold letter must be different.
        Otherwise, any letter from ALL_BUTTONS is valid.
        """
        # Get unique letters of remaining (not completed) core enemies
        remaining_core_letters = {
            enemy.sequence[0] for enemy in self.core_enemies if not enemy.is_complete()
        }

        # If no core enemies yet (called during init), use self.core_letters
        if not remaining_core_letters:
            remaining_core_letters = set(self.core_letters)

        # If only one unique letter remains, hold letter must be different
        if len(remaining_core_letters) == 1:
            available = [b for b in ALL_BUTTONS if b not in remaining_core_letters]
            if available:
                return random_manager.choice(available)

        # Otherwise, any button is fine
        return random_manager.choice(ALL_BUTTONS)

    def _create_core_enemies(self):
        """Create RapidHitEnemy objects for each core letter."""
        for i in range(6):
            # Calculate position in circle
            angle = (i * 60 + self.core_rotation) * math.pi / 180  # 60 degrees apart
            x = self.center_pos[0] + self.core_radius * math.cos(angle)
            y = self.center_pos[1] + self.core_radius * math.sin(angle)

            # Create a RapidHitEnemy with single letter (repeated for hit count)
            letter = self.core_letters[i]
            # Single letter rapid hit enemy
            core_enemy = RapidHitEnemy(
                sequence=letter,  # Single character
                pos=(x, y),
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.waveform,
                hit_count=3,  # Pass custom hit count of 3
            )

            # Set speed to 0 since boss manages movement
            core_enemy.speed = 0

            self.core_enemies.append(core_enemy)

    def _create_forcefield_visuals(self):
        """Create the rotating force field with gap using a single consolidated scatter plot."""
        # Create single ScatterPlotItem for all forcefield particles
        self.forcefield_scatter = pg.ScatterPlotItem(
            pos=[],
            size=[],
            pen=pg.mkPen(None),
            brush=[],
            pxMode=True,
        )
        self.forcefield_scatter.setZValue(5)
        self.view.addItem(self.forcefield_scatter)

        # Initialize particle data as numpy arrays for vectorized computation
        self.forcefield_particles_per_segment = 12
        total_particles = self.forcefield_segment_count * self.forcefield_particles_per_segment

        # Pre-allocate numpy arrays for particle properties (immutable during gameplay)
        self._ff_segments = np.empty(total_particles, dtype=np.int32)
        self._ff_t = np.empty(total_particles)
        self._ff_colors = np.empty((total_particles, 3), dtype=np.int32)
        self._ff_sizes = np.empty(total_particles)
        self._ff_phases = np.empty(total_particles)
        self._ff_speeds = np.empty(total_particles)
        self._ff_amplitudes = np.empty(total_particles)
        self._ff_timers = np.empty(total_particles)

        # Colors: purple and cyan
        color_purple = np.array([128, 0, 255], dtype=np.int32)
        color_cyan = np.array([0, 255, 255], dtype=np.int32)

        idx = 0
        for seg in range(self.forcefield_segment_count):
            for p in range(self.forcefield_particles_per_segment):
                self._ff_segments[idx] = seg
                self._ff_t[idx] = p / max(1, self.forcefield_particles_per_segment - 1)
                self._ff_colors[idx] = color_purple if seg % 2 == 0 else color_cyan
                self._ff_sizes[idx] = 4 + (p % 3) * 2
                self._ff_phases[idx] = seg * 0.4 + p * 0.5
                self._ff_speeds[idx] = 2 + (p % 4) * 0.5
                self._ff_amplitudes[idx] = 8 + (p % 3) * 4
                self._ff_timers[idx] = p * 0.3
                idx += 1

        # Pre-allocate output arrays for positions
        self._ff_positions = np.empty((total_particles, 2))

        # Pre-create brush cache for common colors (avoid repeated mkBrush calls)
        self._ff_brush_cache = {}

        # Keep arc and glow as None for compatibility
        self.forcefield_arc = None
        self.forcefield_glow = None

        # Create hold indicator text
        self.hold_indicator = pg.TextItem(
            text=f"HOLD [{get_button_label(self.forcefield_hold_letter)}]",
            color=(100, 255, 100),
            anchor=(0.5, 0.5),
        )
        self.hold_indicator.setFont(font_manager.get_button_font(16))
        self.hold_indicator.setPos(
            self.center_pos[0], self.center_pos[1] + self.forcefield_radius + 30
        )
        self.view.addItem(self.hold_indicator)
        self.hold_indicator.hide()

    def _update_forcefield(self, dt: float):
        """Update the rotating force field visuals."""
        # Update vulnerability pulse animation time
        self.vulnerability_pulse_time += dt

        # Handle hold transition animation (gradually slow down over 250ms)
        if self.hold_transitioning:
            self.hold_transition_timer += dt
            transition_progress = min(1.0, self.hold_transition_timer / self.hold_transition_duration)
            # Ease out - slow down gradually
            eased_progress = 1.0 - (1.0 - transition_progress) ** 2
            # Interpolate rotation speed from stored to 0
            self.forcefield_rotation_speed = self.stored_rotation_speed * (1.0 - eased_progress)

            if transition_progress >= 1.0:
                self.hold_transitioning = False
                self.forcefield_rotation_speed = 0

        # Calculate hold color blend (0 = normal colors, 1 = golden/yellow)
        hold_color_blend = 0.0
        if self.forcefield_holding:
            if self.hold_transitioning:
                # Blend to golden during transition
                hold_color_blend = min(1.0, self.hold_transition_timer / self.hold_transition_duration)
            else:
                hold_color_blend = 1.0

        # Rotate the force field
        self.forcefield_rotation += self.forcefield_rotation_speed * dt
        self.forcefield_rotation = self.forcefield_rotation % 360

        # Animate shield radius with smooth sine wave
        self.shield_pulse_time += dt
        pulse_offset = self.shield_pulse_amplitude * math.sin(
            2 * math.pi * self.shield_pulse_time / self.shield_pulse_period
        )

        # Add ripple effect when core destroyed (forcefield_damage_flash > 0)
        ripple_offset = 0
        if self.forcefield_damage_flash > 0:
            # Create expanding ripple that fades
            ripple_progress = 1.0 - (
                self.forcefield_damage_flash / self.forcefield_damage_flash_duration
            )
            ripple_offset = math.sin(ripple_progress * math.pi) * 20  # Max 20 pixel expansion
            self.forcefield_damage_flash -= dt

        self.forcefield_radius = self.forcefield_base_radius + pulse_offset + ripple_offset

        # Update color animation time
        self.forcefield_color_animation_time += dt

        # Check if gap is facing downward (within tolerance)
        gap_facing_down = abs((self.forcefield_rotation % 360) - 270) < 30

        # Always show hold indicator with appropriate color
        self.hold_indicator.show()

        hold_label = get_button_label(self.forcefield_hold_letter)
        if self.forcefield_holding:
            # Golden when actively holding
            self.hold_indicator.setHtml(
                f'<span style="color:#FFD700">HOLDING [{hold_label}]</span>'
            )
        else:
            # Green when available to hold
            self.hold_indicator.setHtml(f'<span style="color:#66FF66">HOLD [{hold_label}]</span>')

        # Calculate where the gap is in the rotating shield
        # The gap rotates with forcefield_rotation
        gap_angle = (270 + self.forcefield_rotation) % 360
        gap_start_angle = (gap_angle - self.forcefield_gap_size / 2) % 360
        gap_end_angle = (gap_angle + self.forcefield_gap_size / 2) % 360

        # Calculate the arc span (total degrees to cover, excluding gap)
        arc_span = 360 - self.forcefield_gap_size
        segment_span = arc_span / self.forcefield_segment_count

        # Update flash timer
        if self.forcefield_flash_timer > 0:
            self.forcefield_flash_timer -= dt
            if self.forcefield_flash_timer <= 0:
                self.forcefield_flash_segments.clear()

        # Update all particle timers (vectorized)
        self._ff_timers += dt

        # Vectorized angle calculations
        # segment_start_angles for each particle
        segment_start_angles = (gap_end_angle + self._ff_segments * segment_span) % 360
        segment_end_angles = (gap_end_angle + (self._ff_segments + 1) * segment_span) % 360

        # Handle wrap-around
        wrap_mask = segment_end_angles < segment_start_angles
        segment_end_angles = np.where(wrap_mask, segment_end_angles + 360, segment_end_angles)

        # Interpolate angles and convert to radians
        angles_deg = segment_start_angles + self._ff_t * (segment_end_angles - segment_start_angles)
        angles_rad = angles_deg * (np.pi / 180)

        # Vectorized oscillation calculation
        osc_offsets = self._ff_amplitudes * np.sin(
            self._ff_timers * self._ff_speeds + self._ff_phases
        )

        # Vectorized position calculation
        radii = self.forcefield_radius + osc_offsets
        self._ff_positions[:, 0] = self.center_pos[0] + radii * np.cos(angles_rad)
        self._ff_positions[:, 1] = self.center_pos[1] + radii * np.sin(angles_rad)

        # Calculate colors with hold blend (vectorized)
        blend_target = np.array([255, 220, 100], dtype=np.int32)
        if hold_color_blend > 0:
            blended_colors = (
                self._ff_colors + (blend_target - self._ff_colors) * hold_color_blend
            ).astype(np.int32)
        else:
            blended_colors = self._ff_colors

        # Build brushes (still need loop for pg.mkBrush, but with caching)
        brushes = []
        flash_progress = self.forcefield_flash_timer / 0.3 if self.forcefield_flash_timer > 0 else 0

        for i in range(len(self._ff_segments)):
            seg = self._ff_segments[i]
            r, g, b = blended_colors[i]

            # Apply flash if this segment is flashing
            if seg in self.forcefield_flash_segments and flash_progress > 0:
                r = int(r + (255 - r) * flash_progress)
                g = int(g + (255 - g) * flash_progress)
                b = int(b * (1 - flash_progress))
                alpha = 220
            else:
                alpha = 200

            # Use brush cache to avoid repeated mkBrush calls
            key = (int(r), int(g), int(b), alpha)
            if key not in self._ff_brush_cache:
                self._ff_brush_cache[key] = pg.mkBrush(*key)
            brushes.append(self._ff_brush_cache[key])

        # Single batch update for all forcefield particles
        self.forcefield_scatter.setData(
            pos=self._ff_positions, size=self._ff_sizes, brush=brushes
        )

        # Update vulnerability indicators for exposed letters
        # A letter is vulnerable when its X position is within the X-projection of the gap chord
        # AND the gap is in the lower half of the forcefield

        # Calculate the gap chord endpoints (on the forcefield circle)
        gap_start_rad = gap_start_angle * math.pi / 180
        gap_end_rad = gap_end_angle * math.pi / 180
        gap_x1 = self.center_pos[0] + self.forcefield_radius * math.cos(gap_start_rad)
        gap_x2 = self.center_pos[0] + self.forcefield_radius * math.cos(gap_end_rad)

        # Calculate gap center position to check if gap is in lower half
        gap_center_rad = gap_angle * math.pi / 180
        gap_center_y = self.center_pos[1] + self.forcefield_radius * math.sin(gap_center_rad)
        gap_in_lower_half = gap_center_y < self.center_pos[1]

        # Get the X-projection range (min and max X of the gap)
        gap_x_min = min(gap_x1, gap_x2)
        gap_x_max = max(gap_x1, gap_x2)

        # Track newly vulnerable enemies to update their outlines
        newly_vulnerable = set()

        for i, enemy in enumerate(self.core_enemies):
            if enemy.completed:  # Skip completed/destroyed enemies
                # Hide the completed enemy visuals (death animation takes over)
                for item in enemy.letter_items:
                    item.setOpacity(0)
                for item in enemy.count_items:
                    item.setOpacity(0)
                for bg in enemy.letter_backgrounds:
                    bg.setOpacity(0)
                    if hasattr(bg, "_fill"):
                        bg._fill.setOpacity(0)
                continue

            # Calculate this letter's position
            letter_angle_rad = (i * 60 + self.core_rotation) * math.pi / 180
            letter_x = self.center_pos[0] + self.core_radius * math.cos(letter_angle_rad)
            letter_y = self.center_pos[1] + self.core_radius * math.sin(letter_angle_rad)

            # Check if letter's X position is within the gap's X-projection
            # AND letter is in the lower half of its orbit (below boss center)
            # AND gap is in the lower half of the forcefield (no vulnerability when gap is on top)
            is_in_x_range = gap_x_min <= letter_x <= gap_x_max
            is_in_lower_half = letter_y < self.center_pos[1]
            is_vulnerable = is_in_x_range and is_in_lower_half and gap_in_lower_half

            if is_vulnerable:
                newly_vulnerable.add(i)

        # Update outline colors for enemies that changed vulnerability state
        for i, enemy in enumerate(self.core_enemies):
            if enemy.completed:
                continue

            was_vulnerable = i in self._vulnerable_enemies
            is_now_vulnerable = i in newly_vulnerable

            if is_now_vulnerable and not was_vulnerable:
                # Became vulnerable - set red pulsing outline
                self._set_enemy_vulnerable_outline(enemy, True)
            elif not is_now_vulnerable and was_vulnerable:
                # No longer vulnerable - restore original outline
                self._set_enemy_vulnerable_outline(enemy, False)
            elif is_now_vulnerable:
                # Still vulnerable - update pulse
                self._update_vulnerable_pulse(enemy)

        self._vulnerable_enemies = newly_vulnerable

    def _set_enemy_vulnerable_outline(self, enemy, vulnerable: bool):
        """Set enemy hexagon outline to vulnerable (red) or normal state."""
        if not enemy.letter_backgrounds:
            return

        hexagon = enemy.letter_backgrounds[0]
        letter = enemy.sequence[0]
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[j : j + 2], 16) for j in (1, 3, 5))

        if vulnerable:
            # Bright red/white pulsing outline
            hexagon.setPen(pg.mkPen(color=(255, 150, 150, 255), width=6))
            hexagon._fill.setBrush(pg.mkBrush(255, 100, 100, 150))
        else:
            # Restore original color
            hexagon.setPen(pg.mkPen(color=(*rgb, 255), width=4))
            hexagon._fill.setBrush(pg.mkBrush(*rgb, 100))

    def _update_vulnerable_pulse(self, enemy):
        """Update pulsing effect on vulnerable enemy outline."""
        if not enemy.letter_backgrounds:
            return

        hexagon = enemy.letter_backgrounds[0]
        # Pulsing brightness effect
        pulse = int(150 + 105 * math.sin(self.vulnerability_pulse_time * 5))
        hexagon.setPen(pg.mkPen(color=(255, pulse, pulse, 255), width=6))

    def can_be_damaged(self) -> bool:
        """Check if boss can be damaged (gap facing down)."""
        # The gap starts at 270 and rotates, so when rotation is 0, gap is at 270 (down)
        # We want to check if forcefield_rotation is near 0 (or 360)
        rotation_normalized = self.forcefield_rotation % 360
        gap_facing_down = rotation_normalized < 30 or rotation_normalized > 330
        return gap_facing_down

    def hold_forcefield(self, button: str) -> bool:
        """Try to hold the force field with a button."""
        if button != self.forcefield_hold_letter:
            return False

        # Can hold at any time
        self.forcefield_holding = True
        self.currently_held_button = button  # Track which button is actually being held
        # Store original speed and start transition (don't freeze immediately)
        self.stored_rotation_speed = self.forcefield_rotation_speed
        self.hold_transition_timer = 0.0
        self.hold_transitioning = True

        # Create shield hold waveforms
        self._create_shield_waveforms()

        return True

    def release_forcefield(self, button: str = None):
        """Release the force field hold."""
        # Only release if the button matches the button that was actually held down
        # (not the current hold letter, which may have changed)
        if self.forcefield_holding:
            # Check if this is the right button to release
            held_button = getattr(self, "currently_held_button", self.forcefield_hold_letter)
            if button == held_button or button is None:  # Allow force release with None
                self.forcefield_holding = False
                self.hold_transitioning = False
                self.currently_held_button = None
                # Restore rotation speed to current level based on damage
                remaining_count = sum(1 for enemy in self.core_enemies if not enemy.completed)
                if remaining_count == 1:
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 3.5
                elif remaining_count == 2:
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 2.8
                elif remaining_count == 3:
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 2.2
                elif remaining_count == 4:
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 1.7
                elif remaining_count == 5:
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 1.3
                else:
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed

                # Start waveform fade-out animation
                self.shield_waveform_fade_timer = 0.3  # 0.3 second fade-out

    def _button_matches_projectile(self, button: str) -> bool:
        """Check if button matches any letter in any active (non-completed) projectile."""
        for projectile in self.projectiles:
            # Skip completed projectiles (destroyed but still animating)
            if projectile.is_complete():
                continue
            # Check both sequences in the linked pair
            if button in projectile.sequence1 or button in projectile.sequence2:
                return True
        return False

    def type_button(self, button: str) -> bool:
        """Try to type a button on the boss core."""
        # Boss is invulnerable during entry
        if self.movement_phase == "entering":
            return False

        # Try to hold the force field if it's the hold button
        if button == self.forcefield_hold_letter:
            # If already holding, maintain the hold
            if self.forcefield_holding:
                return True
            # Try to initiate hold
            hold_result = self.hold_forcefield(button)
            if hold_result:
                return True

        # If projectiles are present and button matches a projectile letter,
        # don't process as boss attack - let projectile handle it
        if self.projectiles and self._button_matches_projectile(button):
            return False

        # Find the core enemy matching this button
        letter_index = -1
        target_enemy = None
        for i, enemy in enumerate(self.core_enemies):
            if enemy.can_type_button(button):
                letter_index = i
                target_enemy = enemy
                break

        if target_enemy is None:
            return False  # Not a valid core letter

        # Calculate this letter's position
        letter_angle = (letter_index * 60 + self.core_rotation) % 360
        letter_angle_rad = letter_angle * math.pi / 180
        letter_x = self.center_pos[0] + self.core_radius * math.cos(letter_angle_rad)
        letter_y = self.center_pos[1] + self.core_radius * math.sin(letter_angle_rad)

        # Calculate the gap chord X-projection
        gap_angle = (270 + self.forcefield_rotation) % 360
        gap_start_angle = (gap_angle - self.forcefield_gap_size / 2) % 360
        gap_end_angle = (gap_angle + self.forcefield_gap_size / 2) % 360
        gap_start_rad = gap_start_angle * math.pi / 180
        gap_end_rad = gap_end_angle * math.pi / 180
        gap_x1 = self.center_pos[0] + self.forcefield_radius * math.cos(gap_start_rad)
        gap_x2 = self.center_pos[0] + self.forcefield_radius * math.cos(gap_end_rad)
        gap_x_min = min(gap_x1, gap_x2)
        gap_x_max = max(gap_x1, gap_x2)

        # Check if gap is in the lower half of the forcefield
        gap_center_rad = gap_angle * math.pi / 180
        gap_center_y = self.center_pos[1] + self.forcefield_radius * math.sin(gap_center_rad)
        gap_in_lower_half = gap_center_y < self.center_pos[1]

        # Letter is vulnerable if its X position is within the gap's X-projection
        # AND letter is in the lower half of its orbit (below boss center)
        # AND gap is in the lower half of the forcefield (no vulnerability when gap is on top)
        is_in_x_range = gap_x_min <= letter_x <= gap_x_max
        is_in_lower_half = letter_y < self.center_pos[1]
        letter_in_gap = is_in_x_range and is_in_lower_half and gap_in_lower_half

        # If letter is in gap (X-projection), allow damage
        if letter_in_gap:
            # Continue to damage calculation below
            pass
        else:
            # Letter blocked by shield - trigger animation
            self.shield_hit_timer = self.shield_hit_duration

            # Play denied sound effect
            if self.sound_manager:  # This is the line that causes the AttributeError
                self.sound_manager.play_denied_1_sound()

            # Trigger yellow flash on the segment(s) near the hit
            self._trigger_shield_flash_at_angle(letter_angle)

            # Create laser that ends at the shield where the letter would be hit
            if self.laser_manager and self.waveform:
                # Calculate shield hit position based on letter angle
                shield_angle = letter_angle * math.pi / 180
                shield_x = self.center_pos[0] + self.forcefield_radius * math.cos(shield_angle)
                shield_y = self.center_pos[1] + self.forcefield_radius * math.sin(shield_angle)
                waveform_y = self.waveform.get_y_at_x(shield_x) if self.waveform else None
                self.laser_manager.create_laser((shield_x, shield_y), button, "blocked", waveform_y)

                # Create shield hit particles
                self.particle_system.emit_shield_hit(shield_x, shield_y)

            return True  # Button was processed, but no damage

        # At this point, we know the letter can be damaged (in gap and gap facing down)
        # Process the hit through the core enemy
        hit_successful = target_enemy.type_button(button)

        if hit_successful:
            # Track core hits and change hold letter after 3 hits
            self.core_hit_counter += 1
            if self.core_hit_counter >= self.core_hit_max:
                self.core_hit_counter = 0
                # Get all remaining core letters
                remaining_core_letters = [
                    enemy.sequence[0] for enemy in self.core_enemies if not enemy.completed
                ]

                # Store the old hold letter before changing
                old_hold_letter = self.forcefield_hold_letter
                self.forcefield_hold_letter = self._choose_hold_letter()

                # If forcefield is currently being held with the old letter, release it
                if self.forcefield_holding and self.currently_held_button == old_hold_letter:
                    self.release_forcefield()

            # Counter-attack: queue a fast projectile after each core hit
            self.counter_attack_queue += 1
            self.counter_attack_delay = 0.0
            # Reset barrage timer so it doesn't stack with counter-attack
            self.barrage_timer = 0.0

            # RapidHitEnemy handles its own laser and particle effects internally
            # Just add extra boss-specific particles
            if self.laser_manager:
                laser_pos = target_enemy.get_center_position()
                button_color = BUTTON_COLORS.get(button, "#FFFFFF")
                rgb = tuple(int(button_color[i : i + 2], 16) for i in (1, 3, 5))
                self.particle_system.emit_hit(laser_pos[0], laser_pos[1], rgb)

            # Check if this core enemy just completed after this hit
            if target_enemy.is_complete():
                # Trigger forcefield damage flash and ripple
                self.forcefield_damage_flash = self.forcefield_damage_flash_duration

                # Create death animation for this core enemy
                from enemies.animations import EnemyFireDeathAnimation

                death_anim = EnemyFireDeathAnimation(target_enemy, self.view)
                self.animations.append(death_anim)

                # Call the destruction callback to let game engine handle explosion
                if self.destruction_callback:
                    self.destruction_callback(target_enemy)

                # Update core rotation speed based on remaining enemies - accelerates twice as fast
                remaining_count = sum(1 for enemy in self.core_enemies if not enemy.completed)
                if remaining_count == 1:
                    # Last enemy - 4x speed
                    self.core_rotation_speed = self.core_base_rotation_speed * 4.0
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 3.5

                    # CRITICAL: Check if hold key is the same as the last core letter
                    # If so, force change it to prevent unwinnable state
                    last_core_letter = [
                        enemy.sequence[0] for enemy in self.core_enemies if not enemy.completed
                    ][0]

                    if self.forcefield_hold_letter == last_core_letter:
                        # Need to change hold letter immediately!
                        old_hold_letter = self.forcefield_hold_letter
                        self.forcefield_hold_letter = self._choose_hold_letter()

                        # If forcefield is currently being held with the old letter, release it
                        if (
                            self.forcefield_holding
                            and self.currently_held_button == old_hold_letter
                        ):
                            self.release_forcefield()
                elif remaining_count == 2:
                    # Two enemies left - 3x speed
                    self.core_rotation_speed = self.core_base_rotation_speed * 3.0
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 2.8
                elif remaining_count == 3:
                    # Three enemies left - 2.2x speed
                    self.core_rotation_speed = self.core_base_rotation_speed * 2.2
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 2.2
                elif remaining_count == 4:
                    # Four enemies left - 1.6x speed
                    self.core_rotation_speed = self.core_base_rotation_speed * 1.6
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 1.7
                elif remaining_count == 5:
                    # Five enemies left - 1.3x speed
                    self.forcefield_rotation_speed = self.forcefield_base_rotation_speed * 1.3

            # Check if boss is defeated (all core enemies completed)
            if all(enemy.completed for enemy in self.core_enemies):
                self.defeated = True
                self.completed = True

            return True

        return False

    def can_type_button(self, button: str) -> bool:
        """Check if button can be typed."""
        # Boss is invulnerable during entry
        if self.movement_phase == "entering":
            return False

        # Hold letter can always be typed (to hold or maintain hold)
        if button == self.forcefield_hold_letter:
            return True

        # If projectiles are present and button matches a projectile letter,
        # boss core cannot be typed - projectiles take precedence
        if self.projectiles and self._button_matches_projectile(button):
            return False

        # Check if any active core enemies can type this button
        # Return true even if shield is up, so we can trigger shield hit animation
        for enemy in self.core_enemies:
            if enemy.can_type_button(button):
                return True
        return False

    def spawn_projectile(self):
        """Spawn a linked pair projectile."""
        # Generate simple left/right pair using valid buttons
        from config import LEFT_HAND_BUTTONS, RIGHT_HAND_BUTTONS

        # If shield is being held, avoid the hold key so player can maintain hold
        if self.forcefield_holding:
            # Exclude hold letter from selection
            available_left = [b for b in LEFT_HAND_BUTTONS if b != self.forcefield_hold_letter]
            available_right = [b for b in RIGHT_HAND_BUTTONS if b != self.forcefield_hold_letter]

            # Fall back to full list if exclusion leaves no options
            if not available_left:
                available_left = LEFT_HAND_BUTTONS
            if not available_right:
                available_right = RIGHT_HAND_BUTTONS

            left_letter = random_manager.choice(available_left)
            right_letter = random_manager.choice(available_right)
        else:
            # Normal random selection when not holding
            left_letter = random_manager.choice(LEFT_HAND_BUTTONS)
            right_letter = random_manager.choice(RIGHT_HAND_BUTTONS)

        # Spawn position outside force field
        angle = random_manager.uniform(0, 2 * math.pi)
        spawn_distance = self.forcefield_radius + 40
        spawn_x = self.center_pos[0] + spawn_distance * math.cos(angle)
        spawn_y = self.center_pos[1] + spawn_distance * math.sin(angle)

        # Create projectile as a linked pair
        projectile = BossProjectile(
            left_letter,
            right_letter,
            (spawn_x, spawn_y),
            self.view,
            self.laser_manager,
            self.waveform,
        )

        # Set trajectory toward player waveform center
        target_y = -280  # Player waveform position
        dx = 0 - spawn_x  # Target center X
        dy = target_y - spawn_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            projectile.velocity = (dx / distance * 80, dy / distance * 80)

        self.projectiles.append(projectile)
        return projectile  # Return for game engine to add to enemies list

    def spawn_barrage(self):
        """Spawn a spread of projectiles in an arc aimed at the player."""
        new_projectiles = []
        count = self.barrage_count
        spread_angle = math.radians(60)  # 60 degree arc

        for i in range(count):
            # Evenly distribute across the arc, centered downward
            if count > 1:
                angle_offset = spread_angle * (i / (count - 1) - 0.5)
            else:
                angle_offset = 0

            # Base direction is straight down
            base_angle = -math.pi / 2 + angle_offset

            # Spawn from forcefield edge
            spawn_angle = base_angle + math.pi  # Opposite side for spawn point
            spawn_distance = self.forcefield_radius + 30
            spawn_x = self.center_pos[0] + spawn_distance * math.cos(spawn_angle)
            spawn_y = self.center_pos[1] + spawn_distance * math.sin(spawn_angle)

            from config import LEFT_HAND_BUTTONS, RIGHT_HAND_BUTTONS
            left_letter = random_manager.choice(LEFT_HAND_BUTTONS)
            right_letter = random_manager.choice(RIGHT_HAND_BUTTONS)

            projectile = BossProjectile(
                left_letter, right_letter,
                (spawn_x, spawn_y),
                self.view, self.laser_manager, self.waveform,
            )

            speed = 100 + self.barrage_number * 10  # Escalate speed
            projectile.velocity = (
                speed * math.cos(base_angle),
                speed * math.sin(base_angle),
            )

            self.projectiles.append(projectile)
            new_projectiles.append(projectile)

        self.barrage_number += 1
        # Escalate: increase to 2 after a few barrages
        if self.barrage_number >= 3 and self.barrage_count < 2:
            self.barrage_count = 2
        # Slightly decrease interval (min 4s)
        self.barrage_interval = max(4.0, self.barrage_interval - 0.3)

        return new_projectiles

    def spawn_counter_projectile(self):
        """Spawn a fast projectile as counter-attack after core hit."""
        # Fire from a random point on the forcefield toward player
        angle = random_manager.uniform(0, 2 * math.pi)
        spawn_distance = self.forcefield_radius + 20
        spawn_x = self.center_pos[0] + spawn_distance * math.cos(angle)
        spawn_y = self.center_pos[1] + spawn_distance * math.sin(angle)

        from config import LEFT_HAND_BUTTONS, RIGHT_HAND_BUTTONS
        left_letter = random_manager.choice(LEFT_HAND_BUTTONS)
        right_letter = random_manager.choice(RIGHT_HAND_BUTTONS)

        projectile = BossProjectile(
            left_letter, right_letter,
            (spawn_x, spawn_y),
            self.view, self.laser_manager, self.waveform,
        )

        # Fast, aimed at player center with some spread
        target_x = random_manager.uniform(-100, 100)
        target_y = -280
        dx = target_x - spawn_x
        dy = target_y - spawn_y
        distance = math.sqrt(dx * dx + dy * dy)
        speed = 75
        if distance > 0:
            projectile.velocity = (dx / distance * speed, dy / distance * speed)

        self.projectiles.append(projectile)
        return projectile

    def update(self, dt: float):
        """Update boss, force field, and projectiles."""
        # Apply speed multiplier for slow motion
        effective_dt = dt * self.speed_multiplier

        # Update shield hit animation timer
        if self.shield_hit_timer > 0:
            self.shield_hit_timer = max(0, self.shield_hit_timer - dt)

        # Update particles
        self.particle_system.update(effective_dt)

        # Update core orbital particles (position and spawn new ones)
        self.core_orbital_particles.set_center(self.center_pos[0], self.center_pos[1])
        self.core_orbital_particles.update(effective_dt)
        # Continuously spawn particles to maintain the effect
        if len(self.core_orbital_particles.particles) < 30:
            if random_manager.random() < 0.5:
                self.core_orbital_particles.spawn((128, 0, 255), count=1)  # Purple
            else:
                self.core_orbital_particles.spawn((0, 255, 255), count=1)  # Cyan

        # Handle movement based on phase
        if self.movement_phase == "entering":
            # Fast downward movement during entry
            old_y = self.center_pos[1]
            self.center_pos = (
                self.center_pos[0],
                self.center_pos[1] - self.entry_speed * effective_dt,
            )

            # Debug print on first frame only
            if not hasattr(self, "_debug_printed"):
                print(
                    f"Boss entering: Y={old_y} -> {self.center_pos[1]}, target={self.target_y}, speed={self.entry_speed}, dt={effective_dt}"
                )
                self._debug_printed = True

            # Check if boss has reached target position
            if self.center_pos[1] <= self.target_y:
                self.center_pos = (self.center_pos[0], self.target_y)
                self.movement_phase = "side_to_side"
                print(f"Boss reached target position at Y={self.target_y}")

        elif self.movement_phase == "side_to_side":
            # Update sinusoidal oscillation timer
            self.vertical_oscillation_time += effective_dt

            # Calculate vertical offset using sine wave
            vertical_offset = self.vertical_oscillation_amplitude * math.sin(
                2 * math.pi * self.vertical_oscillation_time / self.vertical_oscillation_period
            )

            # Side-to-side movement
            new_x = (
                self.center_pos[0]
                + self.horizontal_direction * self.horizontal_speed * effective_dt
            )

            # Bounce off bounds
            if new_x <= self.horizontal_bounds[0] or new_x >= self.horizontal_bounds[1]:
                self.horizontal_direction *= -1
                # Clamp to bounds
                new_x = max(self.horizontal_bounds[0], min(self.horizontal_bounds[1], new_x))

            # Apply both horizontal movement and vertical oscillation
            self.center_pos = (new_x, self.target_y + vertical_offset)

        # Rotate the core (opposite direction to forcefield)
        self.core_rotation += self.core_rotation_speed * effective_dt
        self.core_rotation = self.core_rotation % 360

        # Update all core enemies' positions with rotation
        for i, enemy in enumerate(self.core_enemies):
            angle = (i * 60 + self.core_rotation) * math.pi / 180
            x = self.center_pos[0] + self.core_radius * math.cos(angle)
            y = self.center_pos[1] + self.core_radius * math.sin(angle)

            # RapidHitEnemy doesn't have update_position, so we update manually
            # But only if the enemy is not completed (not destroyed)
            if not enemy.completed:
                # Update letter position
                if enemy.letter_items:
                    enemy.letter_items[0].setPos(x, y)

                # Update count item position
                if enemy.count_items:
                    enemy.count_items[0].setPos(x, y - 20)

                # Update hexagon background position
                if enemy.letter_backgrounds:
                    enemy._move_hexagon(enemy.letter_backgrounds[0], x, y)

            # Update enemy itself (for animations and other logic)
            enemy.update(effective_dt)

        # Update force field
        self._update_forcefield(effective_dt)

        # Update shield waveforms
        self._update_shield_waveforms(dt)

        # Update hold indicator position
        self.hold_indicator.setPos(
            self.center_pos[0], self.center_pos[1] + self.forcefield_radius + 30
        )

        # Spawn projectiles periodically (only after boss is in position)
        new_projectiles = []
        if self.movement_phase == "side_to_side":
            # Regular projectile timer
            self.projectile_timer += effective_dt
            if self.projectile_timer >= self.projectile_interval:
                self.projectile_timer = 0
                new_projectiles.append(self.spawn_projectile())

            # Barrage timer
            self.barrage_timer += effective_dt
            if self.barrage_timer >= self.barrage_interval:
                self.barrage_timer = 0
                new_projectiles.extend(self.spawn_barrage())

            # Counter-attack after core hit (brief delay)
            if self.counter_attack_queue > 0:
                self.counter_attack_delay += effective_dt
                if self.counter_attack_delay >= 0.3:
                    new_projectiles.append(self.spawn_counter_projectile())
                    self.counter_attack_queue -= 1
                    self.counter_attack_delay = 0.0

        # Update projectiles
        for projectile in self.projectiles[:]:
            projectile.update(dt)
            if projectile.is_below_screen(-350):
                projectile.cleanup()
                self.projectiles.remove(projectile)

        # Update animations (core enemy death animations)
        for anim in self.animations[:]:
            if not anim.update(effective_dt):
                self.animations.remove(anim)

        return new_projectiles if new_projectiles else None

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of boss."""
        return self.center_pos

    def get_boss_radius(self) -> float:
        """Get the radius of the boss for death animations."""
        return self.forcefield_radius

    def get_width(self) -> float:
        """Get total width of boss."""
        return self.forcefield_radius * 2 + 40

    def is_complete(self) -> bool:
        """Check if boss is defeated."""
        return self.defeated or self.completed

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if boss has moved below screen."""
        return self.center_pos[1] + self.forcefield_radius < bottom_y

    def reset_typing_progress(self):
        """Boss doesn't reset typing progress."""
        pass

    def _create_shield_waveforms(self):
        """Create animated waveforms when shield is held."""
        # Clear any existing waveforms
        self._cleanup_shield_waveforms()

        # Reset animation time
        self.shield_waveform_time = 0.0
        self.shield_waveform_fade_timer = 0.0

        # Create waveforms on both sides of the shield
        # Two traces per side in shades of yellow
        yellow_colors = [
            (255, 255, 100, 150),  # Bright yellow
            (255, 220, 50, 100),  # Golden yellow
        ]

        # Shield is at center_pos with forcefield_radius
        shield_width = self.forcefield_radius * 0.8  # 80% of shield diameter

        # Create left side waveforms
        for i, color in enumerate(yellow_colors):
            waveform_left = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=5))
            self.view.addItem(waveform_left)
            self.shield_waveforms.append(
                {
                    "curve": waveform_left,
                    "side": "left",
                    "index": i,
                    "base_color": color[:3],
                    "max_alpha": color[3],
                }
            )

        # Create right side waveforms
        for i, color in enumerate(yellow_colors):
            waveform_right = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=5))
            self.view.addItem(waveform_right)
            self.shield_waveforms.append(
                {
                    "curve": waveform_right,
                    "side": "right",
                    "index": i,
                    "base_color": color[:3],
                    "max_alpha": color[3],
                }
            )

    def _update_shield_waveforms(self, dt):
        """Update animated waveforms for shield hold effect."""
        if not self.shield_waveforms:
            return

        # Update animation time when holding
        if self.forcefield_holding:
            self.shield_waveform_time += dt

        # Update fade timer when released
        if self.shield_waveform_fade_timer > 0:
            self.shield_waveform_fade_timer -= dt
            if self.shield_waveform_fade_timer <= 0:
                # Fade complete, remove waveforms
                self._cleanup_shield_waveforms()
                return

        # Calculate waveform parameters
        boss_x = self.center_pos[0]
        boss_y = self.center_pos[1]
        shield_width = self.forcefield_radius * 0.8  # 80% of shield diameter

        # Calculate x ranges
        x_start_left = -400
        x_end_left = boss_x - shield_width - 30
        x_start_right = boss_x + shield_width + 30
        x_end_right = 400

        # Update cached x arrays (boss moves, so endpoints change each frame)
        # Use pre-allocated arrays and fill with linspace values
        if self._waveform_x_left is None:
            self._waveform_x_left = np.empty(self._waveform_num_points)
            self._waveform_x_right = np.empty(self._waveform_num_points)

        # Manually compute linspace in-place (avoids allocation)
        step_left = (x_end_left - x_start_left) / (self._waveform_num_points - 1)
        step_right = (x_end_right - x_start_right) / (self._waveform_num_points - 1)
        for i in range(self._waveform_num_points):
            self._waveform_x_left[i] = x_start_left + i * step_left
            self._waveform_x_right[i] = x_start_right + i * step_right

        # Pre-calculate fade amplitude multiplier
        if self.forcefield_holding and self.shield_waveform_fade_timer == 0:
            fade_amplitude_mult = 1.0
        else:
            fade_progress = (
                1.0 - (self.shield_waveform_fade_timer / 0.3)
                if self.shield_waveform_fade_timer > 0
                else 1.0
            )
            fade_amplitude_mult = 1.0 - fade_progress

        for waveform_data in self.shield_waveforms:
            curve = waveform_data["curve"]
            side = waveform_data["side"]
            index = waveform_data["index"]

            # Use pre-computed x points and amplitude scales
            if side == "left":
                x_points = self._waveform_x_left
                x_start = x_start_left
                x_end = x_end_left
                if self.forcefield_holding and self.shield_waveform_fade_timer == 0:
                    amplitude_scale = self._waveform_amplitude_left
                else:
                    amplitude_scale = fade_amplitude_mult
            else:
                x_points = self._waveform_x_right
                x_start = x_start_right
                x_end = x_end_right
                if self.forcefield_holding and self.shield_waveform_fade_timer == 0:
                    amplitude_scale = self._waveform_amplitude_right
                else:
                    amplitude_scale = fade_amplitude_mult

            # Generate waveform with animation
            frequency = 3 + index * 0.5  # Different frequencies for each trace
            phase = self.shield_waveform_time * math.pi  # Animate over time (2 * pi * 0.5)
            phase_offset = index * math.pi / 3  # Phase offset between traces

            # Generate sine wave - use numpy broadcasting
            x_range = x_end - x_start
            if x_range != 0:
                normalized_x = (x_points - x_start) / x_range
                y_points = boss_y + amplitude_scale * 15 * np.sin(
                    frequency * 2 * math.pi * normalized_x + phase + phase_offset
                )
            else:
                y_points = np.full(self._waveform_num_points, boss_y)

            # Update curve data
            curve.setData(x=x_points, y=y_points)

            # Update opacity during fade
            if self.shield_waveform_fade_timer > 0:
                fade_alpha = int(
                    waveform_data["max_alpha"] * (self.shield_waveform_fade_timer / 0.3)
                )
                curve.setPen(pg.mkPen(color=(*waveform_data["base_color"], fade_alpha), width=2))

    def _cleanup_shield_waveforms(self):
        """Remove all shield waveform graphics."""
        for waveform_data in self.shield_waveforms:
            self.view.removeItem(waveform_data["curve"])
        self.shield_waveforms.clear()

    def _trigger_shield_flash_at_angle(self, hit_angle: float):
        """Trigger yellow flash on segment(s) near the given angle.

        Args:
            hit_angle: Angle in degrees where the shield was hit.
        """
        # Calculate the gap position
        gap_angle = (270 + self.forcefield_rotation) % 360
        gap_end_angle = (gap_angle + self.forcefield_gap_size / 2) % 360

        # Calculate which segment the hit angle falls into
        arc_span = 360 - self.forcefield_gap_size
        segment_span = arc_span / self.forcefield_segment_count

        # Calculate angle relative to gap_end_angle
        relative_angle = (hit_angle - gap_end_angle) % 360

        # Find segment index
        segment_index = int(relative_angle / segment_span)

        # Flash the hit segment and neighbors for more visible effect
        self.forcefield_flash_timer = 0.3
        self.forcefield_flash_segments.clear()
        for offset in [-1, 0, 1]:
            idx = (segment_index + offset) % self.forcefield_segment_count
            self.forcefield_flash_segments.add(idx)

    def cleanup(self):
        """Remove all visual elements."""
        # Clean up shield waveforms
        self._cleanup_shield_waveforms()

        # Clean up particle system
        self.particle_system.cleanup()

        # Clean up core orbital particles
        self.core_orbital_particles.cleanup()

        # Clean up core enemies
        for enemy in self.core_enemies:
            enemy.cleanup()
        self.core_enemies.clear()

        # Clean up forcefield scatter plot
        if self.forcefield_scatter is not None:
            self.view.removeItem(self.forcefield_scatter)
            self.forcefield_scatter = None

        self.view.removeItem(self.hold_indicator)

        # Note: Projectiles are cleaned up through their own destruction sequence
        # triggered by base_boss.handle_destruction(), so don't clean them up here
        # Don't clear projectiles list - they need to complete their destruction animations

    def _create_letter_hexagon(self, x, y, letter, size=18):
        """Create hexagon background for letter."""
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

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

    def _move_hexagon(self, hexagon, x, y, size=18):
        """Move hexagon to new position."""
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = x + size * np.cos(angles)
        y_points = y + size * np.sin(angles)

        pen = hexagon.opts.get("pen", pg.mkPen(color=(255, 255, 255), width=4))
        hexagon.setData(x=x_points, y=y_points, pen=pen)

        brush = hexagon._fill.opts.get("brush", pg.mkBrush(255, 255, 255, 100))
        hexagon._fill.setData(x=x_points, y=y_points, brush=brush)

    def get_destruction_info(self):
        """Get destruction info for boss."""
        return {
            "points": 500,  # High points for defeating boss
            "explosion_type": "mega",
            "explosion_scale": 2.0,
            "shake_type": "massive",
        }

    def get_miss_info(self):
        """Get miss info for boss."""
        return {
            "damage": 0.5,  # Boss does heavy damage
            "enemy_type_name": "Boss",
        }

    @property
    def sequence(self):
        """Return core letters as sequence for unified interface."""
        return self.core_letters

    @property
    def letter_items(self):
        """Get all letter items from core enemies."""
        items = []
        for enemy in self.core_enemies:
            items.extend(enemy.letter_items)
        return items

    @property
    def letter_backgrounds(self):
        """Get all letter backgrounds from core enemies."""
        backgrounds = []
        for enemy in self.core_enemies:
            backgrounds.extend(enemy.letter_backgrounds)
        return backgrounds

    def create_victory_animations(self):
        """Create victory animations for boss defeat."""
        # Create custom boss death animation
        animation = BossDeathAnimation(self, self.view)
        # Mark this as a boss animation for special handling
        animation.is_boss = True
        return [animation]


# BossDeathAnimation moved to effects/boss_death_animation.py
class BossProjectile(LinkedEnemyPair):
    """Projectile fired by boss - simplified linked pair."""

    def __init__(
        self,
        left_letter: str,
        right_letter: str,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
    ):
        """Initialize boss projectile."""
        # Create as linked pair with close positioning
        pos1 = (pos[0] - 30, pos[1])
        pos2 = (pos[0] + 30, pos[1])

        super().__init__(left_letter, right_letter, pos1, pos2, view, laser_manager, waveform)

        # Set speed to 0 - we use custom velocity for movement
        self.enemy1.speed = 0
        self.enemy2.speed = 0
        self.velocity = (0, -100)  # Default downward

        # Start faded and fade in
        self.fade_timer = 0.0
        self.fade_duration = 0.5
        self._set_opacity(0)

    def _set_opacity(self, opacity: float):
        """Set opacity for all visual elements."""
        for item in self.enemy1.letter_items + self.enemy2.letter_items:
            item.setOpacity(opacity)
        for bg in self.enemy1.letter_backgrounds + self.enemy2.letter_backgrounds:
            bg.setOpacity(opacity)
            bg._fill.setOpacity(opacity)
        self.link_line.setOpacity(opacity)
        self.link_glow.setOpacity(opacity)
        self.sync_icon.setOpacity(opacity)

    def update(self, dt: float):
        """Update projectile with custom velocity."""
        # Fade in
        if self.fade_timer < self.fade_duration:
            self.fade_timer += dt
            opacity = min(1.0, self.fade_timer / self.fade_duration)
            self._set_opacity(opacity)

        # Update child enemies for animations (speed is 0 so they won't move)
        self.enemy1.set_speed_multiplier(self.speed_multiplier)
        self.enemy2.set_speed_multiplier(self.speed_multiplier)
        self.enemy1.update(dt)
        self.enemy2.update(dt)

        # Custom movement using velocity
        effective_dt = dt * self.speed_multiplier
        dx = self.velocity[0] * effective_dt
        dy = self.velocity[1] * effective_dt

        # Move both enemies
        for enemy in [self.enemy1, self.enemy2]:
            for item in enemy.letter_items:
                pos = item.pos()
                item.setPos(pos.x() + dx, pos.y() + dy)

            # Move backgrounds
            for i, bg in enumerate(enemy.letter_backgrounds):
                pos = enemy.letter_items[i].pos()
                enemy._move_hexagon(bg, pos.x(), pos.y())

        # Update link visual with dt for waveform animation
        self._update_link_visual(dt)

    def get_miss_info(self):
        """Get miss info for projectiles."""
        return {
            "damage": 0.1,  # Less damage than regular enemies
            "enemy_type_name": "Boss projectile",
        }
