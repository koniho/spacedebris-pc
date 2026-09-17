"""Phase Shift Boss - A boss that shifts between dimensions."""

import time
import random
import random_manager
import math
from debug_log import debug_print as print
from typing import Tuple
import numpy as np
import pyqtgraph as pg
from enemies.base_boss import BaseBoss
from enemies import Enemy
from effects.particle_effects import ParticleSystem, OrbitalParticleSystem
from effects.boss_death_animation import BossDeathAnimation


from config import (
    ALL_BUTTONS,
    LEFT_HAND_BUTTONS,
    RIGHT_HAND_BUTTONS,
    get_button_color,
    get_button_label,
)


class PhaseShiftBoss(BaseBoss):
    """Boss that shifts between dimensions, making parts temporarily invulnerable."""

    def __init__(self, view, laser_manager, waveform, game_engine):
        """Initialize phase shift boss."""
        super().__init__(view, laser_manager, waveform)

        # Boss state
        self.completed = False
        self.game_engine = game_engine  # Reference to game engine for player damage
        self.boss_y = 500  # Starting position (off screen at top)
        self.target_y = 150  # Target position on screen (same as original boss)
        self.speed = 0  # Boss doesn't move down continuously
        self.entry_speed = 200  # Speed for entry animation
        self.movement_phase = "entering"  # "entering" or "stationary"

        # Track engaged segment for proper typing flow
        self.engaged_segment = None

        # Phase shifting mechanics
        self.current_phase = 0  # 0 or 1 for two dimensions
        self.phase_timer = 0.0
        self.phase_duration = 3.0  # Seconds in each phase (faster for more intensity)
        self.phase_transition_time = 0.5  # Transition animation duration
        self.is_transitioning = False
        self.transition_progress = 0.0
        self.attacks_this_phase = 0  # Track successful attacks during current phase

        # Attack system
        self.attack_timer = 0.0
        self.attack_interval = 8.0  # Attack every 8 seconds (reduced by 75% from 2 seconds)
        self.projectiles = []  # Phase projectiles
        self.rift_attacks = []  # Dimensional rift attacks

        # Punishment throttling
        self.last_punishment_time = 0.0
        self.punishment_cooldown = 1.0  # 1 second cooldown between punishments

        # Invalid input animation
        self.invalid_input_flash = None
        self.invalid_input_timer = 0.0

        # Visual intensity
        self.segment_rotation = 0.0  # Rotation angle for segments
        self.segment_pulse = 0.0  # Pulse animation timer

        # Energy particles around core (using OrbitalParticleSystem)
        self.energy_particles = OrbitalParticleSystem(
            view,
            size=6,
            base_radius=120,
            radius_variance=40,
            radius_oscillation_speed=3.0,
            orbit_speed=2.0,
            fade_rate=80,
        )

        # General particle system for effects
        self.particle_system = ParticleSystem(view)

        # Boss components
        self.core_segments = []  # Vulnerable segments that can be typed
        self.shield_segments = []  # Shield segments that protect cores
        self.phase_indicators = []  # Visual indicators of current phase

        # Visual elements
        self.graphics_items = []
        self.phase_shift_effect = None

        # Phase visual effects (must be defined before generating structure)
        self.phase_colors = [
            (100, 200, 255),
            (255, 100, 200),
        ]  # Blue dimension  # Pink dimension

        # Countdown visual - shrinking arc
        self.countdown_arc = None
        self.countdown_arc_background = None

        # Generate boss structure (needs phase_colors to be defined)
        self._generate_boss_structure()

        # Destruction callback
        self.destruction_callback = None

        # Boss health visualization
        self.health_bar = None
        self._create_health_bar()

        # Create countdown visual elements
        self._create_countdown_visuals()

    def _generate_boss_structure(self):
        """Generate the boss's segmented structure."""
        # Create 8 segments arranged in a circle
        num_segments = 8
        radius = 100
        center_x, center_y = (0, self.boss_y)

        valid_keys = ALL_BUTTONS

        # Track used starting characters for each phase
        phase0_starts = set()
        phase1_starts = set()

        for i in range(num_segments):
            angle = (i / num_segments) * 2 * math.pi
            seg_x = center_x + radius * math.cos(angle)
            seg_y = center_y + radius * math.sin(angle)

            # Determine if this segment is in phase 0 or 1
            segment_phase = i % 2

            # Create a core segment (4 letter sequence for more challenge)
            sequence_length = 4

            # Choose a starting character that hasn't been used in this phase
            used_starts = phase0_starts if segment_phase == 0 else phase1_starts
            available_starts = [k for k in valid_keys if k not in used_starts]

            # If all starts are used (shouldn't happen with 5 keys and 4 segments per phase), reset
            if not available_starts:
                available_starts = valid_keys.copy()

            start_char = random_manager.choice(available_starts)
            used_starts.add(start_char)

            # Build the rest of the sequence randomly
            remaining_chars = [
                random_manager.choice(valid_keys) for _ in range(sequence_length - 1)
            ]
            sequence = start_char + "".join(remaining_chars)

            # Create segment enemy
            segment = BossSegment(
                sequence=sequence,
                pos=(seg_x, seg_y),
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.waveform,
                phase=segment_phase,
                segment_index=i,
                boss=self,
            )

            self.core_segments.append(segment)

        # Create central core
        self._create_central_core()

        # Create phase shift visual effect
        self._create_phase_effect()

    def _create_central_core(self):
        """Create the central core visual."""
        # Central hexagon
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = 0 + 40 * np.cos(angles)
        y_points = self.boss_y + 40 * np.sin(angles)

        color = self.phase_colors[0]
        self.central_core = pg.PlotCurveItem(
            x=x_points,
            y=y_points,
            pen=pg.mkPen(color=(*color, 200), width=15),
            brush=pg.mkBrush(*color, 50),
        )
        self.view.addItem(self.central_core)
        self.graphics_items.append(self.central_core)

    def _create_phase_effect(self):
        """Create phase shift visual effect."""
        # Create rotating rings that indicate current phase
        self.phase_rings = []
        for _ in range(3):
            circle = pg.PlotCurveItem(
                pen=pg.mkPen(
                    color=(*self.phase_colors[0], 100),
                    width=15,
                    style=pg.QtCore.Qt.PenStyle.DashLine,
                )
            )
            self.view.addItem(circle)
            self.phase_rings.append(circle)
            self.graphics_items.append(circle)

    def _create_health_bar(self):
        """Create boss health bar."""
        # Create health bar background
        bar_width = 300
        bar_height = 20
        bar_x = -bar_width / 2
        bar_y = self.boss_y + 180

        # Background
        self.health_bg = pg.PlotCurveItem(
            x=[bar_x, bar_x + bar_width, bar_x + bar_width, bar_x, bar_x],
            y=[bar_y, bar_y, bar_y + bar_height, bar_y + bar_height, bar_y],
            pen=pg.mkPen(color=(100, 100, 100), width=15),
            brush=pg.mkBrush(50, 50, 50, 100),
        )
        self.view.addItem(self.health_bg)
        self.graphics_items.append(self.health_bg)

        # Health fill
        self.health_fill = pg.PlotCurveItem(
            x=[bar_x, bar_x + bar_width, bar_x + bar_width, bar_x, bar_x],
            y=[bar_y, bar_y, bar_y + bar_height, bar_y + bar_height, bar_y],
            pen=None,
            brush=pg.mkBrush(0, 255, 100, 150),
        )
        self.view.addItem(self.health_fill)
        self.graphics_items.append(self.health_fill)

    def _create_countdown_visuals(self):
        """Create countdown visual elements."""
        # Create background arc (full circle)
        self.countdown_arc_background = pg.PlotCurveItem(
            pen=pg.mkPen(color=(100, 100, 100, 100), width=20)
        )
        self.view.addItem(self.countdown_arc_background)
        self.graphics_items.append(self.countdown_arc_background)

        # Create countdown arc that shrinks over time
        self.countdown_arc = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 200, 50, 200), width=20))
        self.view.addItem(self.countdown_arc)
        self.graphics_items.append(self.countdown_arc)

    def update_health_bar(self):
        """Update health bar based on remaining segments."""
        total_segments = len(self.core_segments)
        remaining = sum(1 for seg in self.core_segments if not seg.completed)
        health_percent = remaining / total_segments if total_segments > 0 else 0

        # Update health fill width
        bar_width = 300
        bar_height = 20
        bar_x = -bar_width / 2
        bar_y = self.boss_y + 180

        fill_width = bar_width * health_percent

        # Update color based on health
        if health_percent > 0.5:
            color = (0, 255, 100)
        elif health_percent > 0.25:
            color = (255, 200, 0)
        else:
            color = (255, 50, 50)

        self.health_fill.setData(
            x=[bar_x, bar_x + fill_width, bar_x + fill_width, bar_x, bar_x],
            y=[bar_y, bar_y, bar_y + bar_height, bar_y + bar_height, bar_y],
            brush=pg.mkBrush(*color, 150),
        )

    def type_button(self, button: str) -> bool:
        """Try to type a button on vulnerable segments."""
        if self.completed:
            return False

        # Boss is invulnerable during entry
        if self.movement_phase == "entering":
            return False

        # Note: Projectiles are handled by the game engine as normal enemies,
        # not by the boss itself

        # Don't process segments during transition
        if self.is_transitioning:
            # Invalid during transition - punish
            self._punish_invalid_input()
            return False

        # Check if we have an engaged segment
        if self.engaged_segment:
            # Continue typing on engaged segment
            if self.engaged_segment.completed:
                # Segment was already completed, disengage
                self._disengage_segment()
            elif self.engaged_segment.phase != self.current_phase:
                # Segment phased out, disengage and look for new one
                self._disengage_segment()
            else:
                # Try to type on engaged segment
                if self.engaged_segment.can_type_button(button):
                    success = self.engaged_segment.type_button(button)
                    if success:
                        self.attacks_this_phase += 1  # Track successful attack
                        if self.engaged_segment.completed:
                            self._on_segment_destroyed(self.engaged_segment)
                            self.engaged_segment = None  # Disengage after completion
                        return True
                else:
                    # Wrong key for engaged segment - disengage and punish
                    self._disengage_segment()
                    self._punish_invalid_input()
                    return False

        # No engaged segment - find closest vulnerable segment that matches the button
        best_segment = None
        best_distance = float("inf")

        for segment in self.core_segments:
            if segment.phase == self.current_phase and not segment.completed:
                if segment.can_type_button(button):
                    # Calculate distance (simple Y distance since they're arranged in circle)
                    # Could be enhanced to consider actual screen position
                    distance = abs(segment.pos[1] - self.boss_y)
                    if distance < best_distance:
                        best_distance = distance
                        best_segment = segment

        if best_segment:
            # Engage and type on the closest matching segment
            self.engaged_segment = best_segment
            self._highlight_engaged_segment()
            success = best_segment.type_button(button)
            if success:
                self.attacks_this_phase += 1  # Track successful attack
                if best_segment.completed:
                    self._on_segment_destroyed(best_segment)
                    self.engaged_segment = None  # Disengage after completion
                return True
        else:
            # No valid segment found - punish for invalid input with 2 projectiles
            self._punish_invalid_input()

        return False

    def on_unmatched_input(self, key: str) -> bool:
        """Handle wrong key press by spawning punishment projectiles."""
        if self.completed or self.movement_phase != "stationary" or self.is_transitioning:
            return False
        self._punish_invalid_input()
        return True

    def can_type_button(self, button: str) -> bool:
        """Check if button can be typed on any vulnerable segment."""
        if self.completed:
            return False

        # Boss is invulnerable during entry
        if self.movement_phase == "entering":
            return False

        # Note: Projectiles are handled by the game engine as normal enemies

        # Don't check segments during transition
        if self.is_transitioning:
            return False

        # When a segment is engaged, only that segment can be typed
        if self.engaged_segment:
            return self.engaged_segment.can_type_button(button)

        # No engagement — check all vulnerable segments
        for segment in self.core_segments:
            if segment.phase == self.current_phase and not segment.completed:
                if segment.can_type_button(button):
                    return True
        return False

    def _on_segment_destroyed(self, segment):
        """Handle segment destruction."""
        # Hide destroyed segment completely
        for anim in segment.animations:
            anim.cleanup()
        segment.animations.clear()
        for letter_item in segment.letter_items:
            letter_item.setOpacity(0.0)
        for hexagon in segment.letter_backgrounds:
            hexagon.setOpacity(0.0)
            hexagon._fill.setOpacity(0.0)

        # Trigger destruction callback
        if self.destruction_callback:
            self.destruction_callback(segment, is_boss_segment=True)

        # Update health bar
        self.update_health_bar()

        # Disengage crosshair after segment is destroyed
        self.game_engine._clear_engagement()

        # Fire a retaliation projectile from the destroyed segment's position
        remaining = [s for s in self.core_segments if not s.completed]
        if remaining:
            self._spawn_retaliation_projectile(segment.pos)

        # Check if all segments destroyed
        if all(seg.completed for seg in self.core_segments):
            self.completed = True
            if self.destruction_callback:
                self.destruction_callback(self, is_boss=True)

    def update(self, dt: float):
        """Update boss state and animations."""
        if self.completed:
            return

        # Handle entry animation
        if self.movement_phase == "entering":
            # Move boss down from top of screen
            self.boss_y -= self.entry_speed * dt

            # Check if reached target position
            if self.boss_y <= self.target_y:
                self.boss_y = self.target_y
                self.movement_phase = "stationary"
                print(f"Phase Shift Boss reached target position at Y={self.target_y}")

            # Update all visual elements to new position
            self._update_positions()

        # Update phase timer (only after entry)
        if self.movement_phase == "stationary":
            self.phase_timer += dt

            # Update countdown arc visual
            if not self.is_transitioning:
                self._update_countdown_arc()

            # Update attack timer
            self.attack_timer += dt
            if self.attack_timer >= self.attack_interval:
                self.attack_timer = 0.0
                self._launch_attack()

            # Check for phase transition
            if not self.is_transitioning and self.phase_timer >= self.phase_duration:
                self._start_phase_transition()

        # Update visual animations
        self.segment_rotation += dt * 30  # Rotate segments slowly
        self.segment_pulse += dt * 2  # Pulse animation
        self._update_segment_positions()

        # Update invalid input animation
        if self.invalid_input_timer > 0:
            self.invalid_input_timer -= dt
            self._update_invalid_input_animation()
            if self.invalid_input_timer <= 0:
                self._clear_invalid_input_animation()

        # Update transition
        if self.is_transitioning:
            self.transition_progress += dt / self.phase_transition_time
            if self.transition_progress >= 1.0:
                self._complete_phase_transition()
            else:
                self._update_transition_effect()

        # Update segments
        for segment in self.core_segments:
            segment.update(dt)

        # Clean up completed projectiles from our tracking list
        # Note: Game engine handles updating and collision for projectiles
        self.projectiles = [
            p for p in self.projectiles if not p.completed and p in self.game_engine.enemies
        ]

        # Update rift attacks
        self._update_rift_attacks(dt)

        # Update energy particles
        self._update_energy_particles(dt)

        # Update general particle system
        self.particle_system.update(dt)

        # Update phase visual effects
        self._update_phase_effects(dt)

        # Update central core with pulsing effect
        color = self.phase_colors[self.current_phase]
        pulse_factor = 0.5 + 0.5 * math.sin(self.segment_pulse * math.pi)

        if self.is_transitioning:
            # Intense flashing during transition
            alpha = int(200 * (0.5 + 0.5 * math.sin(self.transition_progress * math.pi * 8)))
            width = 15 + int(10 * math.sin(self.transition_progress * math.pi * 4))
        else:
            # Regular pulsing
            alpha = int(150 + 50 * pulse_factor)
            width = 15 + int(5 * pulse_factor)

        self.central_core.setPen(pg.mkPen(color=(*color, alpha), width=width))
        self.central_core.setBrush(pg.mkBrush(*color, int(alpha * 0.3)))

    def _start_phase_transition(self):
        """Start transitioning to the other phase."""
        # FIRST: Check for in-progress typing and punish player
        # This must happen BEFORE we disengage or reset anything
        self._check_and_punish_incomplete_typing()

        # SECOND: Disengage any engaged segment after checking for punishment
        # This ensures we reset the segment state cleanly
        if self.engaged_segment:
            print(
                f"Disengaging segment during phase transition, typed_count: {self.engaged_segment.typed_count}"
            )
            self._disengage_segment()

        # THIRD: Check if no attacks were made during this phase
        if self.attacks_this_phase == 0:
            # Punish player by shooting projectiles spread horizontally
            # Number of projectiles depends on difficulty setting
            punishment_count = 4  # Default for HARD
            punishment_count = self.game_engine.config.spawning.boss_punishment_projectiles

            # Space them out so player can see all letters
            if punishment_count == 1:
                x_positions = [0]
            elif punishment_count == 2:
                x_positions = [-75, 75]
            elif punishment_count == 3:
                x_positions = [-100, 0, 100]
            else:
                x_positions = [-150, -50, 50, 150]
            source_positions = [(x, self.boss_y) for x in x_positions]
            self._spawn_punishment_projectiles(punishment_count, source_positions=source_positions)

        # FINALLY: Start the transition
        self.is_transitioning = True
        self.transition_progress = 0.0
        self.phase_timer = 0.0
        self.attacks_this_phase = 0  # Reset for next phase

        # Visual feedback for transition
        for segment in self.core_segments:
            segment.start_phase_transition()

    def _complete_phase_transition(self):
        """Complete the phase transition."""
        self.is_transitioning = False
        self.current_phase = 1 - self.current_phase  # Toggle between 0 and 1

        # Update segment vulnerabilities and ensure proper colors
        for segment in self.core_segments:
            segment.complete_phase_transition(self.current_phase)

    def _update_transition_effect(self):
        """Update visual effects during transition."""
        # Pulse effect during transition
        pulse = math.sin(self.transition_progress * math.pi * 8)

        for ring in self.phase_rings:
            # Interpolate color between phases
            old_color = self.phase_colors[1 - self.current_phase]
            new_color = self.phase_colors[self.current_phase]

            red = int(old_color[0] + (new_color[0] - old_color[0]) * self.transition_progress)
            green = int(old_color[1] + (new_color[1] - old_color[1]) * self.transition_progress)
            blue = int(old_color[2] + (new_color[2] - old_color[2]) * self.transition_progress)

            alpha = int(100 + 50 * pulse)
            ring.setPen(
                pg.mkPen(
                    color=(red, green, blue, alpha),
                    width=15 + abs(pulse * 5),
                    style=pg.QtCore.Qt.PenStyle.DashLine,
                )
            )

    def _update_phase_effects(self, dt):  # pylint: disable=unused-argument
        """Update rotating phase rings."""
        rotation_speed = 30  # degrees per second
        angle_offset = (self.phase_timer * rotation_speed) % 360

        for i, ring in enumerate(self.phase_rings):
            radius = 150 + i * 20
            # Create rotating dashed circle
            angles = np.linspace(0, 2 * np.pi, 60)
            angles += math.radians(angle_offset * (1 + i * 0.3))
            x_points = 0 + radius * np.cos(angles)
            y_points = self.boss_y + radius * np.sin(angles)

            ring.setData(x=x_points, y=y_points)

    def _update_positions(self):
        """Update positions of all visual elements based on boss_y."""
        # Update core segments
        for i, segment in enumerate(self.core_segments):
            angle = (i / len(self.core_segments)) * 2 * math.pi
            radius = 100
            seg_x = 0 + radius * math.cos(angle)
            seg_y = self.boss_y + radius * math.sin(angle)

            # Update segment position (move all letter items and backgrounds)
            for letter_item in segment.letter_items:
                current_pos = letter_item.pos()
                letter_item.setPos(seg_x + (current_pos.x() - segment.pos[0]), seg_y)

            for hexagon in segment.letter_backgrounds:
                # Update hexagon position
                segment._move_hexagon(hexagon, seg_x, seg_y)

            # Update segment's internal position
            segment.pos = (seg_x, seg_y)

        # Update central core
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = 0 + 40 * np.cos(angles)
        y_points = self.boss_y + 40 * np.sin(angles)
        self.central_core.setData(x=x_points, y=y_points)

        # Update health bar
        bar_width = 300
        bar_height = 20
        bar_x = -bar_width / 2
        bar_y = self.boss_y + 180

        self.health_bg.setData(
            x=[bar_x, bar_x + bar_width, bar_x + bar_width, bar_x, bar_x],
            y=[bar_y, bar_y, bar_y + bar_height, bar_y + bar_height, bar_y],
        )

        # Update health fill with same Y position
        self.update_health_bar()

        # Update countdown arc position
        self._update_countdown_arc_position()

    def _launch_attack(self):
        """Launch an attack based on current phase."""
        if self.current_phase == 0:
            # Blue phase - launch homing phase projectiles
            self._spawn_phase_projectiles()
        else:
            # Pink phase - create dimensional rifts
            self._create_dimensional_rift()

        # Visual feedback for attack
        self._create_attack_flash()

    def _spawn_phase_projectiles(self):
        """Spawn projectiles that home towards player position."""
        # Spawn 1 projectile from a random segment position (reduced from 3)
        active_segments = [seg for seg in self.core_segments if not seg.completed]
        if active_segments:
            selected = [random_manager.choice(active_segments)]
        else:
            selected = []

        for segment in selected:
            # Create a simple projectile enemy
            projectile = Enemy(
                sequence=random_manager.choice(ALL_BUTTONS),
                pos=segment.pos,
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.waveform,
            )
            # Store the initial position for testing
            projectile.initial_pos = segment.pos
            # Set projectile speed (reduced by 35% from 180 to 117)
            projectile.speed = 117
            self.projectiles.append(projectile)
            # Add projectile to game engine's enemy list for proper management
            self.game_engine.enemies.append(projectile)

    def _create_dimensional_rift(self):
        """Create a dimensional rift that spawns enemies."""
        # Create rift visual at random position
        rift_x = random_manager.uniform(-200, 200)
        rift_y = self.boss_y - 50

        # Create expanding/contracting rift circle
        rift = pg.PlotCurveItem(pen=pg.mkPen(color=(*self.phase_colors[1], 150), width=15))
        self.view.addItem(rift)

        rift_data = {
            "visual": rift,
            "x": rift_x,
            "y": rift_y,
            "timer": 0.0,
            "duration": 1.5,
            "spawned": False,
        }
        self.rift_attacks.append(rift_data)

    def _update_rift_attacks(self, dt):
        """Update dimensional rifts."""
        for rift in self.rift_attacks[:]:
            rift["timer"] += dt
            progress = rift["timer"] / rift["duration"]

            if progress < 1.0:
                # Animate rift
                radius = 30 * math.sin(progress * math.pi)
                angles = np.linspace(0, 2 * math.pi, 30)
                x_points = rift["x"] + radius * np.cos(angles + progress * math.pi * 2)
                y_points = rift["y"] + radius * np.sin(angles + progress * math.pi * 2)
                rift["visual"].setData(x=x_points, y=y_points)

                # Spawn enemy at midpoint
                if not rift["spawned"] and progress > 0.5:
                    rift["spawned"] = True
                    # Spawn a small enemy from the rift
                    enemy = Enemy(
                        sequence=random_manager.choice(["SD", "FK", "JD"]),
                        pos=(rift["x"], rift["y"]),
                        view=self.view,
                        laser_manager=self.laser_manager,
                        waveform=self.waveform,
                    )
                    # Store the initial position for testing
                    enemy.initial_pos = (rift["x"], rift["y"])
                    enemy.speed = 65  # Reduced by 35% from 100
                    self.projectiles.append(enemy)
                    # Add to game engine's enemy list
                    self.game_engine.enemies.append(enemy)
            else:
                # Remove completed rift
                self.view.removeItem(rift["visual"])
                self.rift_attacks.remove(rift)

    def _update_energy_particles(self, dt):
        """Update energy particles around core."""
        # Update center position for orbital system
        self.energy_particles.set_center(0, self.boss_y)

        # Spawn new particles occasionally
        if random_manager.random() < 0.1:  # 10% chance per frame
            self._spawn_energy_particle()

        # Update the orbital particle system
        self.energy_particles.update(dt)

    def _spawn_energy_particle(self):
        """Spawn energy particles."""
        self.energy_particles.spawn(color=self.phase_colors[self.current_phase], count=3)

    def _update_segment_positions(self):
        """Update segment positions with rotation and pulse."""
        for i, segment in enumerate(self.core_segments):
            # Calculate base angle with rotation
            base_angle = (i / len(self.core_segments)) * 2 * math.pi
            angle = base_angle + math.radians(self.segment_rotation)

            # Add pulse effect to radius
            pulse_offset = 5 * math.sin(self.segment_pulse * math.pi + i * 0.5)
            radius = 100 + pulse_offset

            seg_x = 0 + radius * math.cos(angle)
            seg_y = self.boss_y + radius * math.sin(angle)

            # Update segment visual position if it has moved significantly
            old_x, old_y = segment.pos
            if abs(seg_x - old_x) > 0.1 or abs(seg_y - old_y) > 0.1:
                # Update letter positions using segment's letter_spacing
                spacing = segment.letter_spacing
                for j, letter_item in enumerate(segment.letter_items):
                    letter_x = seg_x + (j - len(segment.letter_items) / 2 + 0.5) * spacing
                    letter_item.setPos(letter_x, seg_y)

                # Update hexagon backgrounds
                for j, hexagon in enumerate(segment.letter_backgrounds):
                    hex_x = seg_x + (j - len(segment.letter_backgrounds) / 2 + 0.5) * spacing
                    segment._move_hexagon(hexagon, hex_x, seg_y)

                segment.pos = (seg_x, seg_y)

    def _create_attack_flash(self):
        """Create a flash effect when attacking."""
        # Create expanding ring from center
        flash_ring = pg.PlotCurveItem(
            pen=pg.mkPen(color=(*self.phase_colors[self.current_phase], 200), width=15)
        )
        self.view.addItem(flash_ring)

        # Animate it expanding and fading
        def update_flash(timer=[0]):
            timer[0] += 0.03
            if timer[0] < 1.0:
                radius = 150 * timer[0]
                alpha = int(200 * (1 - timer[0]))
                angles = np.linspace(0, 2 * math.pi, 60)
                x_points = 0 + radius * np.cos(angles)
                y_points = self.boss_y + radius * np.sin(angles)
                flash_ring.setData(x=x_points, y=y_points)
                flash_ring.setPen(
                    pg.mkPen(color=(*self.phase_colors[self.current_phase], alpha), width=15)
                )
            else:
                self.view.removeItem(flash_ring)

        # This would need a timer system, for now just remove after creation
        self.view.removeItem(flash_ring)

    def reset_typing_progress(self):
        """Reset typing progress for all segments."""
        for segment in self.core_segments:
            if not segment.completed:
                # Clear engagement and reset typing
                segment.is_engaged = False
                segment.typed_count = 0
                # Force proper reset using setText to clear HTML formatting
                for i, letter_item in enumerate(segment.letter_items):
                    letter_item.setText(get_button_label(segment.sequence[i]))
                    letter_item.setColor((255, 255, 255))

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of boss."""
        return (0, self.boss_y)

    def get_next_letter_position(self) -> Tuple[float, float]:
        """Get position of the next letter to type for crosshair tracking."""
        if self.engaged_segment and not self.engaged_segment.completed:
            return self.engaged_segment.get_next_letter_position()
        return self.get_center_position()

    def get_width(self) -> float:
        """Get total width of boss."""
        return 300

    def get_boss_radius(self) -> float:
        """Get the radius of the boss for death animations."""
        return 150  # Half of the width

    def is_complete(self) -> bool:
        """Check if boss is defeated."""
        return self.completed

    def is_below_screen(self, bottom_y: float) -> bool:
        """Boss doesn't move, so never below screen."""
        return False

    def cleanup(self):
        """Remove all visual elements."""
        # Cleanup segments
        for segment in self.core_segments:
            segment.cleanup()

        # Cleanup projectiles - remove from game engine's enemy list first
        for projectile in self.projectiles:
            if projectile in self.game_engine.enemies:
                self.game_engine.enemies.remove(projectile)
            projectile.cleanup()
        self.projectiles.clear()

        # Cleanup rift attacks
        for rift in self.rift_attacks:
            self.view.removeItem(rift["visual"])
        self.rift_attacks.clear()

        # Cleanup energy particles
        self.energy_particles.cleanup()

        # Cleanup particle system
        self.particle_system.cleanup()

        # Remove phase rings
        for ring in self.phase_rings:
            self.view.removeItem(ring)

        # Remove health bar
        self.view.removeItem(self.health_bg)
        self.view.removeItem(self.health_fill)

        # Remove graphics items
        for item in self.graphics_items:
            self.view.removeItem(item)
        self.graphics_items.clear()

        # Clean up invalid input animation
        if self.invalid_input_flash and self.invalid_input_flash.scene():
            self.view.removeItem(self.invalid_input_flash)
            self.invalid_input_flash = None

    def create_victory_animations(self):
        """Create victory animation for phase shift boss defeat."""
        animation = PhaseShiftDeathAnimation(self, self.view)
        animation.is_boss = True  # Mark as boss animation for explosion callbacks
        return [animation]

    def get_destruction_info(self):
        """Get destruction info for boss."""
        return {
            "points": 1000,
            "explosion_type": "boss",
            "explosion_scale": 2.0,
            "shake_type": "heavy",
        }

    @property
    def sequence(self):
        """Return segment sequences combined for unified interface."""
        return "".join([seg.sequence for seg in self.core_segments])

    @property
    def letter_items(self):
        """Get all letter items from segments."""
        items = []
        for segment in self.core_segments:
            items.extend(segment.letter_items)
        return items

    @property
    def letter_backgrounds(self):
        """Get all letter backgrounds from segments."""
        backgrounds = []
        for segment in self.core_segments:
            backgrounds.extend(segment.letter_backgrounds)
        return backgrounds

    def _update_countdown_arc(self):
        """Update the countdown arc based on phase timer."""
        # Calculate progress through the phase (0 to 1)
        progress = self.phase_timer / self.phase_duration

        # Arc radius around the boss
        radius = 180

        # Draw background circle
        if self.countdown_arc_background:
            angles = np.linspace(0, 2 * np.pi, 100)
            x_points = 0 + radius * np.cos(angles)
            y_points = self.boss_y + radius * np.sin(angles)
            self.countdown_arc_background.setData(x=x_points, y=y_points)

        # Draw shrinking arc (starts full, shrinks to nothing)
        if self.countdown_arc:
            remaining = 1.0 - progress
            if remaining > 0:
                # Arc starts at top and goes clockwise
                start_angle = -np.pi / 2  # Start at top
                end_angle = start_angle + (2 * np.pi * remaining)

                # More points for smoother arc
                num_points = max(3, int(100 * remaining))
                angles = np.linspace(start_angle, end_angle, num_points)
                x_points = 0 + radius * np.cos(angles)
                y_points = self.boss_y + radius * np.sin(angles)

                # Color changes as time runs out
                if remaining > 0.5:
                    color = (100, 255, 100, 200)  # Green
                elif remaining > 0.25:
                    color = (255, 255, 100, 200)  # Yellow
                else:
                    # Red and pulsing when almost out of time
                    pulse = math.sin(self.phase_timer * 10) * 0.5 + 0.5
                    alpha = int(150 + 100 * pulse)
                    color = (255, 50, 50, alpha)  # Red

                self.countdown_arc.setData(x=x_points, y=y_points)
                self.countdown_arc.setPen(pg.mkPen(color=color, width=20))
            else:
                # Hide arc when complete
                self.countdown_arc.setData(x=[], y=[])

    def _update_countdown_arc_position(self):
        """Update countdown arc position when boss moves."""
        # Arc will be updated in _update_countdown_arc with current boss_y

    def _check_and_punish_incomplete_typing(self):
        """Check for incomplete typing on segments and punish player."""
        print(f"=== CHECKING FOR INCOMPLETE TYPING ===")
        print(f"Current phase (leaving): {self.current_phase}")
        print(f"Total segments: {len(self.core_segments)}")

        # FIRST: Check segments from the CURRENT phase for incomplete typing
        # BEFORE resetting anything
        punishment_count = 0
        punished_segments = []

        for i, segment in enumerate(self.core_segments):
            print(
                f"Segment {i}: phase={segment.phase}, typed_count={segment.typed_count}, completed={segment.completed}"
            )

            # Only check segments from the current phase that we're leaving
            if segment.phase == self.current_phase and not segment.completed:
                # Check if segment has been partially typed
                if segment.typed_count > 0:
                    print(
                        f">>> INCOMPLETE SEGMENT FOUND! Phase {segment.phase}, typed_count: {segment.typed_count}"
                    )
                    punishment_count += 1
                    punished_segments.append(segment)

        # Spawn punishment projectiles if there was incomplete typing
        print(f"=== PUNISHMENT COUNT: {punishment_count} ===")
        if punishment_count > 0:
            print(f"Phase shift punishment! Spawning {punishment_count} punishment projectiles!")
            # Show visual feedback for punishment
            self._show_invalid_input_animation()
            # Play denied sound
            self.game_engine.sound_manager.play_denied_2_sound()
            self._spawn_punishment_projectiles(punishment_count, punished_segments)

            # Screen shake for punishment
            self.game_engine.shake_manager.trigger_shake(magnitude=5.0, duration=0.3)

        # SECOND: Now reset all segments after checking and punishing
        for i, segment in enumerate(self.core_segments):
            # Reset ALL segments regardless of phase or typing state
            # This ensures clean state for the next phase
            if segment.typed_count > 0:
                print(f"Resetting segment {i} typing progress from {segment.typed_count} to 0")

            # Clear engagement and properly reset typing
            segment.is_engaged = False
            segment.typed_count = 0
            # Use setText to clear any HTML formatting and force white color
            for j, letter_item in enumerate(segment.letter_items):
                letter_item.setText(get_button_label(segment.sequence[j]))
                letter_item.setColor((255, 255, 255))
            print(f"  Forced segment {i} to white via setText")

    def _punish_invalid_input(self):
        """Punish player for typing invalid letter when no enemy is engaged."""
        current_time = time.time()

        # Check if enough time has passed since last punishment
        if current_time - self.last_punishment_time < self.punishment_cooldown:
            # Still on cooldown, just show visual feedback
            self._show_invalid_input_animation()
            return

        self.last_punishment_time = current_time
        print("Invalid input! Spawning 2 punishment projectiles!")

        # Show visual feedback
        self._show_invalid_input_animation()

        # Play denied sound
        self.game_engine.sound_manager.play_denied_2_sound()

        # Spawn 2 fast punishment projectiles with different X positions
        x_positions = [-75, 75]  # Spread them horizontally
        source_positions = [(x, self.boss_y) for x in x_positions]
        self._spawn_punishment_projectiles(2, source_positions=source_positions)
        # Small screen shake
        self.game_engine.shake_manager.trigger_shake(magnitude=2.0, duration=0.1)

    def _spawn_retaliation_projectile(self, source_pos):
        """Spawn a single projectile from a destroyed segment's position."""
        projectile = Enemy(
            sequence=random_manager.choice(ALL_BUTTONS),
            pos=source_pos,
            view=self.view,
            laser_manager=self.laser_manager,
            waveform=self.waveform,
        )
        projectile.initial_pos = source_pos
        projectile.speed = 120  # Moderate speed

        # Phase-colored tint
        phase_color = self.phase_colors[self.current_phase]
        for letter_item in projectile.letter_items:
            letter_item.setColor(phase_color)

        self.projectiles.append(projectile)
        self.game_engine.enemies.append(projectile)

    def _spawn_punishment_projectiles(self, count, source_positions=None):
        """Spawn punishment projectiles that are faster and more dangerous."""

        if source_positions is None:
            # Default to spawning from boss center
            source_positions = [(0, self.boss_y)] * count
        elif isinstance(source_positions[0], BossSegment):
            # Extract positions from segments
            source_positions = [seg.pos for seg in source_positions]

        for i in range(count):
            pos = source_positions[i % len(source_positions)]

            # Create a punishment projectile - single letter, fast
            projectile = Enemy(
                sequence=random_manager.choice(ALL_BUTTONS),
                pos=pos,
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.waveform,
            )
            # Store the initial position for testing
            projectile.initial_pos = pos

            # Make punishment projectiles threatening but not too fast (reduced by 35% from 250 to 162)
            projectile.speed = 162  # Punishment projectiles

            # Give it a red tint to show it's a punishment
            if projectile.letter_items:
                for letter_item in projectile.letter_items:
                    letter_item.setColor((255, 100, 100))  # Red tinted

            self.projectiles.append(projectile)

            # Add to game engine's enemy list
            self.game_engine.enemies.append(projectile)

    def _disengage_segment(self):
        """Disengage the current segment and restore its colors."""
        if self.engaged_segment:
            self.engaged_segment.reset_typing_progress()
            self.engaged_segment = None

    def _highlight_engaged_segment(self):
        """Highlight the engaged segment with brighter colors."""
        if self.engaged_segment:
            # Mark segment as engaged and update appearance
            self.engaged_segment.is_engaged = True
            self.engaged_segment._update_phase_appearance()

    def _show_invalid_input_animation(self):
        """Show visual feedback for invalid input."""
        self.invalid_input_timer = 0.3  # Animation duration

        # Create a red flash effect around the boss
        if not self.invalid_input_flash:
            # Create a large red circle that will flash
            self.invalid_input_flash = pg.PlotCurveItem(
                pen=pg.mkPen(color=(255, 50, 50, 200), width=8)
            )
            self.view.addItem(self.invalid_input_flash)

    def _update_invalid_input_animation(self):
        """Update the invalid input animation."""
        if self.invalid_input_flash:
            # Create pulsing red circle
            radius = 150 + 30 * math.sin(self.invalid_input_timer * 20)
            angles = np.linspace(0, 2 * np.pi, 60)
            x_points = 0 + radius * np.cos(angles)
            y_points = self.boss_y + radius * np.sin(angles)

            # Update flash opacity based on timer
            alpha = int(200 * (self.invalid_input_timer / 0.3))
            self.invalid_input_flash.setPen(pg.mkPen(color=(255, 50, 50, alpha), width=8))
            self.invalid_input_flash.setData(x=x_points, y=y_points)

    def _clear_invalid_input_animation(self):
        """Clear the invalid input animation."""
        # Remove flash effect
        if self.invalid_input_flash and self.invalid_input_flash.scene():
            self.view.removeItem(self.invalid_input_flash)
            self.invalid_input_flash = None


class BossSegment(Enemy):
    """Individual segment of the phase shift boss."""

    def __init__(
        self,
        sequence: str,
        pos: Tuple[float, float],
        view,
        laser_manager=None,
        waveform=None,
        phase=0,
        segment_index=0,
        boss=None,
    ):
        """Initialize boss segment."""
        # Initialize as simple enemy but with special properties
        super().__init__(sequence, pos, view, laser_manager, waveform)

        self.phase = phase
        self.segment_index = segment_index
        self.boss = boss
        self.is_vulnerable = phase == 0  # Start with phase 0 vulnerable
        self.is_engaged = False  # Track engagement state
        self.speed = 0  # Segments don't move independently
        self.pos = pos  # Store position for updates

        # Override visual appearance based on phase
        self._update_phase_appearance()

    def _update_phase_appearance(self):
        """Update appearance based on current vulnerability."""
        if self.boss:
            is_vulnerable = self.phase == self.boss.current_phase
            # Check both the flag and actual engagement status
            is_engaged = self.is_engaged or (self.boss.engaged_segment == self)
        else:
            is_vulnerable = self.is_vulnerable
            is_engaged = self.is_engaged

        print(
            f"  Segment update: phase={self.phase}, vulnerable={is_vulnerable}, engaged={is_engaged}, typed_count={self.typed_count}, completed={self.completed}"
        )

        # Don't touch completed segments - they stay in their destroyed state
        if self.completed:
            return

        # Update letter and background opacity/color
        for i, (letter_item, hexagon) in enumerate(zip(self.letter_items, self.letter_backgrounds)):
            if is_vulnerable:
                # Full visibility and normal colors
                letter_item.setOpacity(1.0)
                hexagon.setOpacity(1.0)
                # Access fill directly - duck typing
                hexagon._fill.setOpacity(1.0)  # pylint: disable=protected-access

                # Use proper colors based on typing state
                # Only show typed letters as green if segment is engaged AND typed_count > 0
                if i < self.typed_count and self.typed_count > 0 and is_engaged:
                    # Typed letters - green (only when engaged)
                    print(f"    Letter {i}: GREEN (typed, engaged)")
                    letter_item.setColor((100, 255, 100))
                else:
                    # Untyped letters or disengaged - always white
                    print(f"    Letter {i}: WHITE (untyped or disengaged)")
                    letter_item.setColor((255, 255, 255))
            else:
                # Phased out - semi-transparent and different color
                if self.typed_count == 0 and not is_engaged:
                    print(f"    Letter {i}: WHITE (phased out but reset)")
                    letter_item.setOpacity(0.3)
                    letter_item.setColor((255, 255, 255))
                else:
                    print(f"    Letter {i}: DIM BLUE (phased out)")
                    letter_item.setOpacity(0.3)
                    letter_item.setColor((150, 150, 200))
                hexagon.setOpacity(0.2)
                # Access fill directly - duck typing
                hexagon._fill.setOpacity(0.1)  # pylint: disable=protected-access

    def type_button(self, button: str) -> bool:
        """Only allow typing if segment is vulnerable."""
        if not self.is_vulnerable:
            return False
        result = super().type_button(button)
        if result:
            # Only update appearance if we're still engaged
            # (segment might be completed and disengaged)
            if self.boss and self.boss.engaged_segment == self:
                self._update_phase_appearance()
        return result

    def can_type_button(self, button: str) -> bool:
        """Check if button can be typed."""
        if not self.is_vulnerable:
            return False
        return super().can_type_button(button)

    def reset_typing_progress(self):
        """Reset typing progress and restore colors."""
        self.is_engaged = False
        super().reset_typing_progress()
        for i, letter_item in enumerate(self.letter_items):
            letter_item.setColor((255, 255, 255))

    def start_phase_transition(self):
        """Visual effect when phase transition starts."""
        # Add shimmer or pulse effect

    def complete_phase_transition(self, new_phase):
        """Update vulnerability after phase transition."""
        if self.completed:
            return  # Don't touch destroyed segments
        self.is_vulnerable = self.phase == new_phase
        self.is_engaged = False
        self.typed_count = 0
        for i, letter_item in enumerate(self.letter_items):
            letter_item.setColor((255, 255, 255))
        self._update_phase_appearance()

    def update(self, dt: float):
        """Update segment (no movement, just animations)."""
        # Update animations only, no movement
        completed_animations = []
        for animation in self.animations:
            if not animation.update(dt):
                completed_animations.append(animation)

        for animation in completed_animations:
            self.animations.remove(animation)

        # DON'T constantly update phase appearance - it overwrites our color changes!
        # Phase appearance is updated when needed:
        # - When segment is created
        # - When phase transitions occur
        # - When typing state changes
        # - When engagement changes

    def _move_hexagon(self, hexagon, x, y):
        """Move hexagon to new position."""
        # This is a simplified version - just update position
        # The actual hexagon movement would need more complex updates
        pass


class PhaseShiftDeathAnimation(BossDeathAnimation):
    """Death animation specifically for Phase Shift Boss."""

    def __init__(self, boss, view):
        """Initialize the phase shift boss death animation."""
        # Initialize base class for finale support
        super().__init__(boss, view)
        # Remove shield rings spawned by base class — this animation has its own visuals
        for ring_info in self.shield_rings:
            self.view.removeItem(ring_info["item"])
        self.shield_rings.clear()

        # Store boss state for animation
        self.segments = boss.core_segments
        self.phase_colors = boss.phase_colors

        # Animation elements
        self.explosion_timer = 0.0
        self.explosion_interval = 0.1
        self.dimensional_tears = []
        self.collapse_rings = []

        # Override boss_visuals with phase shift specific elements
        self.boss_visuals = [
            boss.central_core,
            boss.countdown_arc,
            boss.countdown_arc_background,
            boss.health_bg,
            boss.health_fill,
        ]
        self.boss_visuals.extend(boss.phase_rings)

        # Create initial dimensional collapse effect
        self._create_dimensional_collapse()

    def _create_dimensional_collapse(self):
        """Create the initial dimensional collapse visual."""

        # Create multiple collapsing rings
        for i in range(5):
            ring = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 100, 200, 100), width=10))
            self.view.addItem(ring)
            self.collapse_rings.append(
                {
                    "item": ring,
                    "radius": 200 + i * 30,
                    "speed": 50 + i * 10,
                    "color_phase": i % 2,  # Alternate between phase colors
                }
            )

    def update(self, dt):
        """Update the death animation."""

        if self.completed:
            return False

        self.elapsed += dt

        # Phase 1: Dimensional instability (0-1 seconds)
        if self.elapsed < 1.0:
            # Flicker between dimensions
            flicker_rate = 10 + self.elapsed * 20  # Accelerating flicker
            phase_flicker = int(self.elapsed * flicker_rate) % 2

            # Calculate overall fade progress (1.0 to 0.3 over first second)
            fade_progress = 1.0 - (self.elapsed * 0.7)  # Goes from 1.0 to 0.3

            # Flash opacity between 0 and decreasing max value
            flash_opacity = 0 if phase_flicker == 0 else fade_progress

            # Update segment colors and opacity to flicker
            for segment in self.segments:
                color = self.phase_colors[phase_flicker]
                for letter_item in segment.letter_items:
                    letter_item.setColor(color)
                    letter_item.setOpacity(flash_opacity)

                for bg in segment.letter_backgrounds:
                    bg.setOpacity(flash_opacity * 0.5)  # Backgrounds fade more

            # Flash and fade boss visual elements
            for visual in self.boss_visuals:
                if visual:
                    visual.setOpacity(flash_opacity)

        # Phase 2: Dimensional tears and explosions (1-2.5 seconds)
        if 1.0 <= self.elapsed < 2.5:
            # Keep elements at low opacity
            remaining_opacity = 0.3
            for segment in self.segments:
                for letter_item in segment.letter_items:
                    letter_item.setOpacity(remaining_opacity)
                for bg in segment.letter_backgrounds:
                    bg.setOpacity(remaining_opacity * 0.5)

            # Keep boss visuals faded
            for visual in self.boss_visuals:
                if visual:
                    visual.setOpacity(remaining_opacity * 0.2)  # Very faded

            # Spawn explosions periodically
            self.explosion_timer += dt
            if self.explosion_timer >= self.explosion_interval:
                self.explosion_timer = 0
                self._spawn_random_explosion()

            # Create dimensional tears
            if random_manager.random() < 0.1:  # 10% chance per frame
                self._create_dimensional_tear()

        # Phase 3: Final collapse with escalating effects (2.5-3 seconds)
        if self.elapsed >= 2.5:
            collapse_progress = (self.elapsed - 2.5) / 0.5

            # Collapse all elements to center
            for segment in self.segments:
                for letter_item in segment.letter_items:
                    current_pos = letter_item.pos()
                    new_x = current_pos.x() * (1 - collapse_progress)
                    new_y = self.center_pos[1] + (current_pos.y() - self.center_pos[1]) * (
                        1 - collapse_progress
                    )
                    letter_item.setPos(new_x, new_y)
                    letter_item.setOpacity(1 - collapse_progress)

        # Finale effects from base class
        self._update_finale()

        # Update collapsing rings
        for ring_data in self.collapse_rings:
            ring_data["radius"] -= ring_data["speed"] * dt
            if ring_data["radius"] > 0:
                angles = np.linspace(0, 2 * np.pi, 60)
                x_points = self.center_pos[0] + ring_data["radius"] * np.cos(angles)
                y_points = self.center_pos[1] + ring_data["radius"] * np.sin(angles)
                ring_data["item"].setData(x=x_points, y=y_points)

                # Fade and color shift
                alpha = int(200 * (ring_data["radius"] / 300))
                color = self.phase_colors[ring_data["color_phase"]]
                ring_data["item"].setPen(pg.mkPen(color=(*color, alpha), width=10))

        # Update dimensional tears
        for tear in self.dimensional_tears[:]:
            tear["timer"] += dt
            if tear["timer"] < tear["duration"]:
                # Animate tear
                progress = tear["timer"] / tear["duration"]
                alpha = int(255 * (1 - progress))
                tear["item"].setPen(pg.mkPen(color=(*tear["color"], alpha), width=5))
            else:
                self.view.removeItem(tear["item"])
                self.dimensional_tears.remove(tear)

        # Check if animation is complete
        if self.elapsed >= self.duration:
            self.completed = True
            self._cleanup_animation()

            # Create final explosion
            self.enemy.game_engine.explosion_manager.create_explosion(
                self.center_pos,
                color="#FFFFAA",
                explosion_type="boss",
                intensity=3.0,
            )
            # Big screen shake
            self.enemy.game_engine.shake_manager.trigger_shake(magnitude=10.0, duration=0.5)
            return False

        return True

    def _spawn_random_explosion(self):
        """Spawn a random explosion during death."""
        # Random position near boss
        offset_x = random_manager.uniform(-150, 150)
        offset_y = random_manager.uniform(-150, 150)
        pos = (self.center_pos[0] + offset_x, self.center_pos[1] + offset_y)

        button = random_manager.choice(ALL_BUTTONS)
        self.enemy.game_engine.explosion_manager.create_explosion(
            pos,
            color=get_button_color(button),
            explosion_type="enhanced",
            intensity=1.5,
        )
        # Play explosion sound
        self.enemy.game_engine.sound_manager.play_explosion_sound()

        # Trigger screen shake
        self.enemy.game_engine.shake_manager.medium_shake()

    def _create_dimensional_tear(self):
        """Create a visual dimensional tear effect."""
        # Create a jagged line representing a tear in space
        num_points = 10
        start_x = self.center_pos[0] + random_manager.uniform(-200, 200)
        start_y = self.center_pos[1] + random_manager.uniform(-200, 200)

        x_points = []
        y_points = []
        for i in range(num_points):
            x_points.append(start_x + i * 5 + random_manager.uniform(-10, 10))
            y_points.append(start_y + i * 5 + random_manager.uniform(-10, 10))

        tear_line = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=pg.mkPen(color=(255, 0, 255, 255), width=5)
        )
        self.view.addItem(tear_line)

        self.dimensional_tears.append(
            {
                "item": tear_line,
                "timer": 0.0,
                "duration": 0.5,
                "color": self.phase_colors[random_manager.randint(0, 1)],
            }
        )

    def _cleanup_animation(self):
        """Clean up all animation elements."""
        # Remove collapse rings
        for ring_data in self.collapse_rings:
            self.view.removeItem(ring_data["item"])
        self.collapse_rings.clear()

        # Remove dimensional tears
        for tear in self.dimensional_tears:
            self.view.removeItem(tear["item"])
        self.dimensional_tears.clear()

        # The boss cleanup will be called by the game engine

    def cleanup(self):
        """Cleanup method for compatibility with game engine."""
        super().cleanup()  # Clean up base class shield rings
        self._cleanup_animation()
        self.enemy.cleanup()
