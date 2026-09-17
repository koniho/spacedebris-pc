# enemies/chaotic_cloud_boss.py

import math
import random
from typing import List, Tuple, Optional
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QTimer
from enemies.base_boss import BaseBoss
from enemies.projectile_enemy import ProjectileEnemy  # To shoot letters that can move diagonally
from enemies.rapid_hit_enemy import RapidHitEnemy  # To shoot letters as rapid hit
from enemies.linked_enemy_pair import LinkedEnemyPair  # To shoot letters as linked pairs
from config import ALL_BUTTONS, BUTTON_COLORS, get_button_label
from font_manager import font_manager
from effects.dimensional_effects import DimensionalEffectManager
from effects.particle_effects import ContainedParticleSystem, ParticleSystem

from config import ALL_BUTTONS, LEFT_HAND_BUTTONS, RIGHT_HAND_BUTTONS


class ChaoticCloudBoss(BaseBoss):
    """
    A chaotic cloud boss composed of many letters that attacks by shooting individual letters
    which evolve into rapid-hit and linked-pair enemies as the boss loses letters.
    """

    def __init__(
        self,
        pos: Tuple[float, float],
        view,
        laser_manager,
        waveform,
        game_engine,
        attack_interval_multiplier: float = 1.0,
    ):
        super().__init__(view, laser_manager, waveform)
        self.game_engine = game_engine  # Needed to spawn new enemies
        self.attack_interval_multiplier = attack_interval_multiplier
        # Adjust position lower to account for the cloud size
        self.center_pos = list(pos)  # Make it mutable for movement
        self.center_pos[1] -= 150  # Move boss lower on screen
        self.core_velocity = [0, 0]  # Core movement velocity
        self.core_time = 0  # For sinusoidal motion
        self.letters_remaining = 100  # Tracks how many letters are left in the cloud
        self.active_projectiles = []  # Track spawned projectiles to check if they're destroyed
        self.cloud_letters: List[pg.TextItem] = []
        self.cloud_letter_data: List[dict] = []  # Store position, velocity, original color etc.
        self.active_letters: List[bool] = [
            True
        ] * self.letters_remaining  # Track which letters are still in the cloud

        # Boss states and thresholds
        self.current_phase = 1  # 1: Single letters, 2: Rapid-hit, 3: Linked-pairs
        self.phase_2_threshold = 40
        self.phase_3_threshold = 20
        self.completed = False

        # Visuals
        self.view = view
        self.laser_manager = laser_manager
        self.waveform = waveform

        # Attack mechanics
        self.attack_timer = 0.0
        self.base_attack_interval = 0.3  # Much faster initial attack rate
        self.attack_interval = self.base_attack_interval * attack_interval_multiplier
        self.attack_speed = 150  # Speed of shot letters

        # Cloud properties
        self.cloud_spread_radius = 120  # Max radius for letters around center
        self.cloud_flicker_timer = 0.0
        self.cloud_flicker_interval = 0.1  # Flicker letters for chaotic effect

        # Rainbow particle core (using ContainedParticleSystem)
        self.core_radius = 50  # Radius of the core area
        self.rainbow_core = ContainedParticleSystem(
            view,
            center_x=self.center_pos[0],
            center_y=self.center_pos[1],
            contain_radius=self.core_radius,
            pull_strength=2.0,
            max_particles=100,
            spawn_interval=0.02,
            default_pen_width=0,  # No outline
        )
        self.core_particles_spawned = 0  # Track how many particles spawned during entry

        # Pre-shot effects
        self.charging_rings = []  # List of charging ring effects
        # Launch burst particle system
        self.launch_burst_system = ParticleSystem(view)

        # Entry animation state
        self.entry_phase = "particles"  # "particles", "letters_incoming", "coalescing", "complete"
        self.entry_timer = 0.0
        self.entry_duration = 3.0  # Total 3 seconds
        self.particles_duration = 0.5  # First 0.5s: particles appear
        self.letters_fly_duration = 2.0  # Next 2s: letters fly in
        self.coalesce_duration = 0.5  # Final 0.5s: settle into position

        # Dimensional effects manager for flashes and tears
        self.dim_effects = DimensionalEffectManager(view)

        # Entry animation letter tracking
        self.letter_start_positions = []  # Where letters start (screen edges)
        self.letter_target_positions = []  # Where letters end up (cloud positions)

        self._initialize_rainbow_core()
        self._generate_initial_letters()
        self._setup_entry_animation()
        self._create_visuals()

    def _generate_initial_letters(self):
        """Generates the initial 100 letters for the chaotic cloud."""
        for i in range(self.letters_remaining):
            letter_char = random.choice(ALL_BUTTONS)

            # Target position within cloud spread (where letter will end up)
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0.2 * self.cloud_spread_radius, self.cloud_spread_radius)

            target_x = self.center_pos[0] + distance * math.cos(angle)
            target_y = self.center_pos[1] + distance * math.sin(angle)

            # Store target position
            self.letter_target_positions.append([target_x, target_y])

            # Random velocity for internal chaotic movement (increased speed)
            vx = random.uniform(-60, 60)
            vy = random.uniform(-60, 60)

            # Random initial color (from button colors)
            color_str = BUTTON_COLORS.get(letter_char, "#FFFFFF")
            color_rgb = tuple(int(color_str[j : j + 2], 16) for j in (1, 3, 5))

            self.cloud_letter_data.append(
                {
                    "char": letter_char,
                    "pos": [target_x, target_y],  # Will be overwritten in _setup_entry_animation
                    "vel": [vx, vy],
                    "color_rgb": color_rgb,
                    "original_idx": i,  # Store original index for tracking
                }
            )

    def _setup_entry_animation(self):
        """Setup the entry animation - letters start at screen edges."""
        # Screen bounds for spawning letters
        screen_left = -450
        screen_right = 450
        screen_top = 350
        screen_bottom = -350

        for i, letter_data in enumerate(self.cloud_letter_data):
            # Choose a random edge (0=top, 1=right, 2=bottom, 3=left)
            edge = random.randint(0, 3)

            if edge == 0:  # Top
                start_x = random.uniform(screen_left, screen_right)
                start_y = screen_top + random.uniform(20, 100)
            elif edge == 1:  # Right
                start_x = screen_right + random.uniform(20, 100)
                start_y = random.uniform(screen_bottom, screen_top)
            elif edge == 2:  # Bottom
                start_x = random.uniform(screen_left, screen_right)
                start_y = screen_bottom - random.uniform(20, 100)
            else:  # Left
                start_x = screen_left - random.uniform(20, 100)
                start_y = random.uniform(screen_bottom, screen_top)

            self.letter_start_positions.append([start_x, start_y])

            # Set initial position to start position
            letter_data["pos"] = [start_x, start_y]

    def _create_visuals(self):
        """Creates the visual elements for the chaotic cloud letters and adds them to the view."""
        for i, letter_data in enumerate(self.cloud_letter_data):
            # Letter text
            text_item = pg.TextItem(
                text=get_button_label(letter_data["char"]),
                color=letter_data["color_rgb"],
                anchor=(0.5, 0.5),
            )
            text_item.setFont(
                font_manager.get_enemy_letter_font(18)
            )  # Smaller font for cloud letters
            text_item.setPos(letter_data["pos"][0], letter_data["pos"][1])
            # Start invisible during entry animation - will fade in as letters fly
            text_item.setOpacity(0.0)
            self.view.addItem(text_item)
            self.cloud_letters.append(text_item)

    def _initialize_rainbow_core(self):
        """Initializes the rainbow particle core.

        During entry animation, particles spawn gradually.
        After entry, all particles are spawned.
        """
        # Don't spawn particles immediately - they'll spawn gradually during entry
        pass

    def _spawn_core_particle(self):
        """Spawns a single rainbow core particle."""
        self.rainbow_core.spawn()

    def _update_rainbow_core_particles(self, dt: float):
        """Updates the rainbow particle core animation."""
        # Update center position to follow boss movement
        self.rainbow_core.set_center(self.center_pos[0], self.center_pos[1])
        # Update with auto_spawn based on entry phase
        auto_spawn = self.entry_phase == "complete"
        self.rainbow_core.update(dt, auto_spawn=auto_spawn)

    def _create_charging_ring(self, letter_pos, letter_char):
        """Create a charging ring effect at a letter position."""
        # Use yellow-whitish color for all charging effects
        rgb = (255, 250, 200)  # Yellow-whitish

        # Create expanding ring - 3x larger than before
        ring_item = pg.PlotCurveItem(pen=pg.mkPen(color=(*rgb, 255), width=4), brush=None)
        self.view.addItem(ring_item)

        self.charging_rings.append(
            {
                "item": ring_item,
                "pos": letter_pos,
                "radius": 5,
                "max_radius": 75,  # 3x larger (was 25)
                "growth_rate": 150,  # Faster expansion to match larger size
                "age": 0,
                "lifetime": 0.6,  # Slightly longer to allow full fade
                "rgb": rgb,
            }
        )

        # Also create a large launch burst orb that stays in place
        self._create_launch_burst(letter_pos)

    def _update_charging_rings(self, dt: float):
        """Update all charging ring effects."""
        for ring in self.charging_rings[:]:
            ring["age"] += dt
            ring["radius"] += ring["growth_rate"] * dt

            if ring["age"] < ring["lifetime"]:
                # Update ring geometry
                angles = np.linspace(0, 2 * np.pi, 48)  # More points for smoother large ring
                x_points = ring["pos"][0] + ring["radius"] * np.cos(angles)
                y_points = ring["pos"][1] + ring["radius"] * np.sin(angles)

                # Fade to clear as it expands
                progress = ring["age"] / ring["lifetime"]
                alpha = int(255 * (1 - progress))
                # Line width also fades
                width = max(1, int(4 * (1 - progress * 0.5)))

                ring["item"].setData(x=x_points, y=y_points)
                ring["item"].setPen(pg.mkPen(color=(*ring["rgb"], alpha), width=width))
            else:
                # Remove completed ring
                self.view.removeItem(ring["item"])
                self.charging_rings.remove(ring)

    def _create_launch_burst(self, pos):
        """Create a large orb burst effect at the launch position."""
        # Use yellow-whitish color for all launch bursts
        rgb = (255, 250, 200)  # Yellow-whitish
        # Emit burst particles
        self.launch_burst_system.emit(
            x=pos[0],
            y=pos[1],
            color=rgb,
            count=8,
            speed_range=(20, 60),
            size_range=(15, 25),
            lifetime=0.8,
            gravity=0,  # No gravity for burst effect
        )

    def _update_launch_bursts(self, dt: float):
        """Update launch burst particle system."""
        self.launch_burst_system.update(dt)

    def type_button(self, button: str) -> bool:
        # ChaoticCloudBoss doesn't get "typed" directly. Its letters are enemies.
        # This method might be called if an "engaged enemy" for the boss itself is tried.
        # For now, it will return False, as the individual letters are the typeable elements.
        return False

    def can_type_button(self, button: str) -> bool:
        # Same as type_button, the boss itself isn't typeable.
        return False

    def reset_typing_progress(self):
        # No direct typing progress to reset for the boss itself.
        pass

    def update(self, dt: float):
        """Update chaotic cloud boss, internal letter movement, attack logic, and phase transitions."""
        new_projectile = None

        # Update dimensional effects
        self.dim_effects.update(dt)

        # Handle entry animation
        if self.entry_phase != "complete":
            self._update_entry_animation(dt)
            # Update rainbow core particles during entry too
            self._update_rainbow_core_particles(dt)
            return None  # No attacks during entry

        # Clean up destroyed projectiles from tracking list
        self.active_projectiles = [
            p for p in self.active_projectiles if p in self.game_engine.enemies
        ]

        # Destruction condition - all letters shot AND all projectiles destroyed
        if self.letters_remaining <= 0 and len(self.active_projectiles) == 0 and not self.completed:
            self.completed = True
            print("ChaoticCloudBoss: All letters and projectiles destroyed! Boss defeated.")
            return None  # No more activity from this boss

        # Update core motion (sinusoidal floating motion)
        self.core_time += dt
        self.center_pos[0] += math.sin(self.core_time * 0.5) * 30 * dt  # Horizontal sway
        self.center_pos[1] += math.cos(self.core_time * 0.7) * 20 * dt  # Vertical float

        # Keep core within screen bounds
        self.center_pos[0] = max(-350, min(350, self.center_pos[0]))
        self.center_pos[1] = max(-50, min(250, self.center_pos[1]))

        # Update rainbow core particles
        self._update_rainbow_core_particles(dt)

        # Update charging rings
        self._update_charging_rings(dt)

        # Update launch bursts
        self._update_launch_bursts(dt)

        # Update internal letter positions (chaotic movement)
        for i, letter_data in enumerate(self.cloud_letter_data):
            if self.active_letters[i]:  # Only update active letters
                letter_data["pos"][0] += letter_data["vel"][0] * dt
                letter_data["pos"][1] += letter_data["vel"][1] * dt

                # Keep letters loosely within a circular boundary around boss center
                dx = letter_data["pos"][0] - self.center_pos[0]
                dy = letter_data["pos"][1] - self.center_pos[1]
                distance = math.sqrt(dx**2 + dy**2)

                if distance > self.cloud_spread_radius * 1.2:  # If too far, pull back
                    letter_data["vel"][0] -= dx * dt
                    letter_data["vel"][1] -= dy * dt
                elif distance < self.cloud_spread_radius * 0.5:  # If too close, push out
                    letter_data["vel"][0] += dx * dt
                    letter_data["vel"][1] += dy * dt

                # Randomly perturb velocity for more chaos (increased)
                letter_data["vel"][0] += random.uniform(-20, 20) * dt
                letter_data["vel"][1] += random.uniform(-20, 20) * dt

                # Clamp velocities (increased max speed)
                letter_data["vel"][0] = max(-80, min(80, letter_data["vel"][0]))
                letter_data["vel"][1] = max(-80, min(80, letter_data["vel"][1]))

                # Update visual position
                self.cloud_letters[i].setPos(letter_data["pos"][0], letter_data["pos"][1])

        # --- Attack Mechanism ---
        self.attack_timer += dt

        # Shortcut: In phase 3, if player destroys all active projectiles, fire immediately
        should_fire = self.attack_timer >= self.attack_interval
        if (
            self.current_phase == 3
            and len(self.active_projectiles) == 0
            and self.letters_remaining > 0
        ):
            should_fire = True

        if should_fire and self.letters_remaining > 0:
            self.attack_timer = 0.0
            new_projectile = self._shoot_letter()
            if new_projectile:
                # Track the projectile so we know when all are destroyed
                self.active_projectiles.append(new_projectile)

        # --- Phase Transition ---
        self._check_phase_transition()

        return new_projectile  # May return a newly spawned enemy projectile

    def _update_entry_animation(self, dt: float):
        """Update the entry animation sequence."""
        self.entry_timer += dt

        # Phase 1: Particles appear gradually (0 - 0.5s)
        if self.entry_phase == "particles":
            # Spawn particles gradually over the particles phase
            particles_progress = self.entry_timer / self.particles_duration
            target_particles = int(self.rainbow_core.max_particles * particles_progress)

            # Spawn particles to reach target count
            while self.core_particles_spawned < target_particles:
                self._spawn_core_particle()
                self.core_particles_spawned += 1

            if self.entry_timer >= self.particles_duration:
                self.entry_phase = "letters_incoming"
                print("ChaoticCloudBoss: Entry - Letters incoming!")
                # Create initial burst of dimensional effects
                self.dim_effects.create_burst(
                    tuple(self.center_pos),
                    num_tears=8,
                    num_flashes=5,
                    colors=[(255, 100, 200), (100, 200, 255), (255, 255, 100)],
                )
                # Starfield flash with tears and thunder
                self.game_engine.starfield.start_flash(0.1)
                self.game_engine.sound_manager.play_thunder_sound()

        # Phase 2: Letters fly in from edges (0.5s - 2.5s)
        elif self.entry_phase == "letters_incoming":
            fly_progress = (self.entry_timer - self.particles_duration) / self.letters_fly_duration

            if fly_progress >= 1.0:
                self.entry_phase = "coalescing"
                print("ChaoticCloudBoss: Entry - Coalescing!")
                # Another burst as letters arrive
                self.dim_effects.create_burst(
                    tuple(self.center_pos),
                    num_tears=5,
                    num_flashes=8,
                    colors=[(255, 100, 200), (100, 200, 255)],
                )
                # Starfield flash with tears and thunder
                self.game_engine.starfield.start_flash(0.1)
                self.game_engine.sound_manager.play_thunder_sound()
            else:
                # Ease-out function for smooth arrival
                eased_progress = 1 - (1 - fly_progress) ** 2

                # Update each letter position and opacity
                for i, letter_data in enumerate(self.cloud_letter_data):
                    if not self.active_letters[i]:
                        continue

                    start = self.letter_start_positions[i]
                    target = self.letter_target_positions[i]

                    # Interpolate position
                    new_x = start[0] + (target[0] - start[0]) * eased_progress
                    new_y = start[1] + (target[1] - start[1]) * eased_progress
                    letter_data["pos"] = [new_x, new_y]

                    # Update visual
                    self.cloud_letters[i].setPos(new_x, new_y)
                    # Fade in with some variation per letter
                    letter_opacity = min(1.0, eased_progress * 1.5) * 0.8
                    self.cloud_letters[i].setOpacity(letter_opacity)

                # Spawn occasional flashes and tears during flight
                if random.random() < 0.15:  # 15% chance per frame
                    # Random position along the path of letters
                    rand_idx = random.randint(0, len(self.cloud_letter_data) - 1)
                    if self.active_letters[rand_idx]:
                        pos = tuple(self.cloud_letter_data[rand_idx]["pos"])
                        if random.random() < 0.5:
                            self.dim_effects.create_flash(
                                pos,
                                color=self.cloud_letter_data[rand_idx]["color_rgb"],
                                max_radius=40,
                                duration=0.2,
                            )
                        else:
                            self.dim_effects.create_tear(
                                pos,
                                color=self.cloud_letter_data[rand_idx]["color_rgb"],
                                spread=30,
                            )

        # Phase 3: Letters settle and start chaotic motion (2.5s - 3.0s)
        elif self.entry_phase == "coalescing":
            coalesce_progress = (
                self.entry_timer - self.particles_duration - self.letters_fly_duration
            ) / self.coalesce_duration

            if coalesce_progress >= 1.0:
                self.entry_phase = "complete"
                print("ChaoticCloudBoss: Entry complete! Boss is now active.")

                # Final flash burst - big and obvious
                self.dim_effects.create_burst(
                    tuple(self.center_pos),
                    num_tears=15,
                    num_flashes=12,
                    colors=[(255, 255, 255), (255, 100, 200), (100, 200, 255)],
                )

                # Create a large central flash
                self.dim_effects.create_flash(
                    tuple(self.center_pos),
                    color=(255, 255, 255),
                    max_radius=200,
                    duration=0.5,
                )

                # Screen shake
                self.game_engine.shake_manager.trigger_shake(magnitude=8.0, duration=0.4)

                # Starfield flash effect
                self.game_engine.starfield.start_flash(0.1)

                # Whoosh sound effect
                self.game_engine.sound_manager.play_whoosh_1_sound()

                # Set final opacity
                for i, letter_item in enumerate(self.cloud_letters):
                    if self.active_letters[i] and letter_item:
                        letter_item.setOpacity(0.8)
            else:
                # Small random perturbations as letters settle
                for i, letter_data in enumerate(self.cloud_letter_data):
                    if not self.active_letters[i]:
                        continue

                    target = self.letter_target_positions[i]
                    current = letter_data["pos"]

                    # Gently pull toward target with some wobble
                    wobble_x = math.sin(self.entry_timer * 10 + i) * 5 * (1 - coalesce_progress)
                    wobble_y = (
                        math.cos(self.entry_timer * 10 + i * 0.7) * 5 * (1 - coalesce_progress)
                    )

                    new_x = current[0] + (target[0] - current[0]) * 0.1 + wobble_x
                    new_y = current[1] + (target[1] - current[1]) * 0.1 + wobble_y
                    letter_data["pos"] = [new_x, new_y]

                    self.cloud_letters[i].setPos(new_x, new_y)

    def _check_phase_transition(self):
        """Checks the number of remaining letters and updates the boss's phase and attack interval."""
        if self.letters_remaining <= self.phase_3_threshold and self.current_phase < 3:
            self.current_phase = 3
            self.attack_interval = 0.9 * self.attack_interval_multiplier
            print(
                f"ChaoticCloudBoss: Transitioned to Phase 3 (Linked-Pairs) - {self.letters_remaining} letters left."
            )
        elif self.letters_remaining <= self.phase_2_threshold and self.current_phase < 2:
            self.current_phase = 2
            self.attack_interval = 0.7 * self.attack_interval_multiplier
            print(
                f"ChaoticCloudBoss: Transitioned to Phase 2 (Rapid-Hit) - {self.letters_remaining} letters left."
            )

    def _spawn_ghost_particle(self, pos, color_rgb, velocity):
        """Spawn a ghost particle at the position where a letter was removed.

        The particle follows the same chaotic motion as the rainbow core particles
        but uses the letter's color.
        """
        x, y = pos
        # Spawn into the contained particle system with the letter's color
        self.rainbow_core.spawn(
            x=x,
            y=y,
            color=color_rgb,
            pen_color=color_rgb,
            size_range=(20, 35),
            lifetime_range=(1.5, 2.5),
            brush_alpha=180,
            pen_alpha=200,
            pen_width=4,
        )

    def _get_and_remove_single_letter(self) -> Optional[Tuple[str, Tuple[float, float], int]]:
        """Selects a single random active letter, removes it from the cloud visuals, and updates state."""
        available_letter_indices = [i for i, active in enumerate(self.active_letters) if active]
        if not available_letter_indices:
            return None

        shot_letter_idx = random.choice(available_letter_indices)
        letter_data = self.cloud_letter_data[shot_letter_idx]
        letter_char = letter_data["char"]
        current_pos = tuple(letter_data["pos"])  # Make a copy as tuple

        # Create charging ring effect before removing the letter
        self._create_charging_ring(current_pos, letter_char)

        # Spawn ghost particle with letter's color and velocity
        self._spawn_ghost_particle(current_pos, letter_data["color_rgb"], tuple(letter_data["vel"]))

        # Mark letter as inactive and remove visual from cloud
        self.active_letters[shot_letter_idx] = False
        self.view.removeItem(self.cloud_letters[shot_letter_idx])
        self.cloud_letters[shot_letter_idx] = None  # Clear reference
        self.letters_remaining -= 1

        print(
            f"ChaoticCloudBoss: Removed letter '{letter_char}'. {self.letters_remaining} remaining."
        )
        return letter_char, current_pos, shot_letter_idx

    def _get_and_remove_paired_letters(
        self,
    ) -> Optional[Tuple[str, Tuple[float, float], str, Tuple[float, float], Tuple[int, int]]]:
        """Selects two random active letters from different hands, removes them from the cloud."""
        # Define hand groupings
        left_hand = set(LEFT_HAND_BUTTONS)
        right_hand = set(RIGHT_HAND_BUTTONS)

        available_letter_indices = [i for i, active in enumerate(self.active_letters) if active]
        if len(available_letter_indices) < 2:
            return None

        # Separate available letters by hand
        left_hand_indices = [
            i for i in available_letter_indices if self.cloud_letter_data[i]["char"] in left_hand
        ]
        right_hand_indices = [
            i for i in available_letter_indices if self.cloud_letter_data[i]["char"] in right_hand
        ]

        # Ensure we have at least one letter from each hand
        if not left_hand_indices or not right_hand_indices:
            # Not enough letters from both hands - pick any two available letters
            # but override their characters to ensure left+right hand pairing
            shot_letter_idx_1 = random.choice(available_letter_indices)
            available_letter_indices.remove(shot_letter_idx_1)
            shot_letter_idx_2 = random.choice(available_letter_indices)
            # Force letters to be from different hands
            self.cloud_letter_data[shot_letter_idx_1]["char"] = random.choice(LEFT_HAND_BUTTONS)
            self.cloud_letter_data[shot_letter_idx_2]["char"] = random.choice(RIGHT_HAND_BUTTONS)
        else:
            # Pick one from each hand
            shot_letter_idx_1 = random.choice(left_hand_indices)
            shot_letter_idx_2 = random.choice(right_hand_indices)

        letter_data_1 = self.cloud_letter_data[shot_letter_idx_1]
        letter_char_1 = letter_data_1["char"]
        pos_1 = tuple(letter_data_1["pos"])  # Make a copy

        letter_data_2 = self.cloud_letter_data[shot_letter_idx_2]
        letter_char_2 = letter_data_2["char"]
        pos_2 = tuple(letter_data_2["pos"])  # Make a copy

        # Create charging rings for both letters
        self._create_charging_ring(pos_1, letter_char_1)
        self._create_charging_ring(pos_2, letter_char_2)

        # Spawn ghost particles with each letter's color and velocity
        self._spawn_ghost_particle(pos_1, letter_data_1["color_rgb"], tuple(letter_data_1["vel"]))
        self._spawn_ghost_particle(pos_2, letter_data_2["color_rgb"], tuple(letter_data_2["vel"]))

        # Mark letters as inactive and remove visuals
        self.active_letters[shot_letter_idx_1] = False
        self.active_letters[shot_letter_idx_2] = False
        self.view.removeItem(self.cloud_letters[shot_letter_idx_1])
        self.view.removeItem(self.cloud_letters[shot_letter_idx_2])
        self.cloud_letters[shot_letter_idx_1] = None
        self.cloud_letters[shot_letter_idx_2] = None
        self.letters_remaining -= 2

        print(
            f"ChaoticCloudBoss: Removed pair '{letter_char_1}' and '{letter_char_2}'. {self.letters_remaining} remaining."
        )
        return letter_char_1, pos_1, letter_char_2, pos_2, (shot_letter_idx_1, shot_letter_idx_2)

    def _get_existing_enemy_positions(self) -> List[Tuple[float, float]]:
        """Get positions of all existing enemies to check for overlaps."""
        positions = []

        for enemy in self.game_engine.enemies:
            if enemy in self.active_projectiles:
                # Include our own active projectiles
                pos = enemy.get_center_position()
                positions.append(pos)
            elif enemy != self:
                # Include other enemies but not self
                pos = enemy.get_center_position()
                positions.append(pos)

        return positions

    def _resolve_position_overlaps(
        self, pos: Tuple[float, float], letter_width: float = 36, max_iterations: int = 10
    ) -> Tuple[float, float]:
        """Move position away from overlapping enemies until no overlaps remain."""
        min_distance = 2 * letter_width
        separation = 1.5 * letter_width
        existing_positions = self._get_existing_enemy_positions()

        current_pos = list(pos)

        for _ in range(max_iterations):
            overlap_found = False

            for existing_pos in existing_positions:
                dx = current_pos[0] - existing_pos[0]
                dy = current_pos[1] - existing_pos[1]
                distance = math.sqrt(dx**2 + dy**2)

                if distance < min_distance:
                    overlap_found = True
                    # Move away from overlapping enemy
                    if distance < 0.1:
                        # Nearly same position - move in random direction
                        angle = random.uniform(0, 2 * math.pi)
                        current_pos[0] += separation * math.cos(angle)
                        current_pos[1] += separation * math.sin(angle)
                    else:
                        # Move along the direction away from overlapping enemy
                        dir_x = dx / distance
                        dir_y = dy / distance
                        current_pos[0] += dir_x * separation
                        current_pos[1] += dir_y * separation
                    break

            if not overlap_found:
                break

        return (current_pos[0], current_pos[1])

    def _shoot_letter(self):
        """Selects a letter(s) from the cloud, turns it into a projectile(s), and removes it from the cloud."""
        if self.letters_remaining <= 0:
            return None

        new_enemy = None

        # Determine target for projectile (player waveform center)
        target_y = -280  # Default player waveform Y position

        if self.current_phase == 1 or self.current_phase == 2:
            # Phase 1: Single letters as regular enemies
            # Phase 2: Rapid-hit enemies (count of 3)

            result = self._get_and_remove_single_letter()
            if result is None:
                return None
            letter_char, current_pos, _ = result

            # Resolve overlaps with existing enemies
            current_pos = self._resolve_position_overlaps(current_pos)

            if self.waveform:
                target_y = (
                    self.waveform.get_y_at_x(current_pos[0])
                    if hasattr(self.waveform, "get_y_at_x")
                    else -280
                )
            target_pos = (current_pos[0], target_y)

            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            distance = math.sqrt(dx**2 + dy**2)

            velocity_x = (dx / distance) * self.attack_speed
            velocity_y = (dy / distance) * self.attack_speed

            if self.current_phase == 1:
                new_enemy = ProjectileEnemy(
                    sequence=letter_char,
                    pos=(current_pos[0], current_pos[1]),
                    view=self.view,
                    laser_manager=self.laser_manager,
                    waveform=self.waveform,
                    velocity=(velocity_x, velocity_y),
                )
            else:  # self.current_phase == 2
                # For RapidHitEnemy, we need to create a custom version with velocity
                new_enemy = RapidHitEnemy(
                    sequence=letter_char,
                    pos=(current_pos[0], current_pos[1]),
                    view=self.view,
                    laser_manager=self.laser_manager,
                    waveform=self.waveform,
                    hit_count=3,
                )
                # Since RapidHitEnemy doesn't support velocity, just use downward speed
                new_enemy.speed = self.attack_speed

        elif self.current_phase == 3:
            # Phase 3: Linked-pair enemies
            result = self._get_and_remove_paired_letters()
            if result is None:
                return None
            letter_char_1, pos_1, letter_char_2, pos_2, _ = result

            # Ensure sufficient distance between letters to prevent overlap
            # Letter width is approximately 2 * hexagon_radius (diameter)
            letter_width = 36  # 2 * 18 (hexagon_radius from LinkedEnemyPair)
            min_distance = 2 * letter_width  # Minimum distance to avoid overlap

            dx = pos_2[0] - pos_1[0]
            dy = pos_2[1] - pos_1[1]
            distance = math.sqrt(dx**2 + dy**2)

            if distance < min_distance:
                # Letters are too close - separate them by 1.5 letter widths each direction
                separation = 1.5 * letter_width
                # Determine which is leftmost (smaller x)
                if pos_1[0] <= pos_2[0]:
                    pos_1 = (pos_1[0] - separation, pos_1[1])
                    pos_2 = (pos_2[0] + separation, pos_2[1])
                else:
                    pos_1 = (pos_1[0] + separation, pos_1[1])
                    pos_2 = (pos_2[0] - separation, pos_2[1])

            # Resolve overlaps with existing enemies for both positions
            pos_1 = self._resolve_position_overlaps(pos_1, letter_width)
            pos_2 = self._resolve_position_overlaps(pos_2, letter_width)

            # Calculate mid-point and trajectory for the pair
            mid_x = (pos_1[0] + pos_2[0]) / 2
            mid_y = (pos_1[1] + pos_2[1]) / 2

            if self.waveform:
                target_y = (
                    self.waveform.get_y_at_x(mid_x)
                    if hasattr(self.waveform, "get_y_at_x")
                    else -280
                )
            target_pos = (mid_x, target_y)

            dx = target_pos[0] - mid_x
            dy = target_pos[1] - mid_y
            distance = math.sqrt(dx**2 + dy**2)

            velocity_x = (dx / distance) * self.attack_speed
            velocity_y = (dy / distance) * self.attack_speed

            new_enemy = LinkedEnemyPair(
                seq1=letter_char_1,
                seq2=letter_char_2,
                pos1=(pos_1[0], pos_1[1]),
                pos2=(pos_2[0], pos_2[1]),
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.waveform,
            )
            # LinkedEnemyPair uses Enemy class internally, which doesn't support velocity
            # So just set their speed for downward movement
            new_enemy.enemy1.speed = self.attack_speed
            new_enemy.enemy2.speed = self.attack_speed

        return new_enemy

    def get_center_position(self) -> Tuple[float, float]:
        """Get the center position of the boss."""
        return tuple(self.center_pos)

    def get_width(self) -> float:
        """Get the width of the boss (cloud spread diameter)."""
        return self.cloud_spread_radius * 2

    def get_boss_radius(self) -> float:
        """Get the radius of the boss for death animations."""
        return self.cloud_spread_radius

    def is_below_screen(self) -> bool:
        """Check if the boss is below the screen."""
        return self.center_pos[1] < -400

    def is_complete(self) -> bool:
        """Check if the boss is complete (defeated)."""
        # Clean up destroyed projectiles from tracking list
        self.active_projectiles = [
            p for p in self.active_projectiles if p in self.game_engine.enemies
        ]

        # Boss is only complete when all letters are shot AND all projectiles are destroyed
        if self.letters_remaining <= 0 and len(self.active_projectiles) == 0:
            self.completed = True

        return self.completed

    def cleanup(self):
        """Remove all visual elements."""
        # Clean up active projectiles that were spawned by this boss
        for projectile in self.active_projectiles[:]:
            if projectile in self.game_engine.enemies:
                self.game_engine.enemies.remove(projectile)
            projectile.cleanup()
        self.active_projectiles.clear()

        # Remove cloud letters
        for letter_item in self.cloud_letters:
            if letter_item:  # Check if not None
                self.view.removeItem(letter_item)
        self.cloud_letters.clear()
        self.cloud_letter_data.clear()
        self.active_letters.clear()

        # Cleanup rainbow core particle system
        self.rainbow_core.cleanup()

        # Remove charging rings
        for ring in self.charging_rings:
            self.view.removeItem(ring["item"])
        self.charging_rings.clear()

        # Cleanup launch burst particle system
        self.launch_burst_system.cleanup()

        # Clean up dimensional effects
        self.dim_effects.cleanup()

    def get_destruction_info(self):
        # Custom destruction info for the chaotic cloud boss
        return {
            "points": 1000,
            "explosion_type": "mega",
            "explosion_scale": 3.0,
            "shake_type": "massive",
        }

    def get_miss_info(self):
        # Custom miss info for the chaotic cloud boss (if it can "miss" by letting letters pass)
        return {
            "damage": 0.5,
            "enemy_type_name": "Chaotic Cloud Boss",
        }

    @property
    def sequence(self):
        """Return empty sequence for compatibility with death animations."""
        # ChaoticCloudBoss doesn't have a traditional sequence
        # Return empty string to satisfy animation requirements
        return ""

    @property
    def projectiles(self):
        """Return active projectiles for compatibility with base_boss cleanup."""
        return self.active_projectiles

    @property
    def letter_items(self):
        """Get letter items for compatibility with animations."""
        # Return cloud letters that are still active
        return [
            item for i, item in enumerate(self.cloud_letters) if item and self.active_letters[i]
        ]

    @property
    def letter_backgrounds(self):
        """Get letter backgrounds for compatibility with animations."""
        # ChaoticCloudBoss doesn't use traditional letter backgrounds
        return []
