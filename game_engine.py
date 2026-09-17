"""Core game engine and state management."""

# Initialize sound manager early so it can be used by intro screen
import os
import sys

from PyQt5.QtCore import QFile, QRectF
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QGraphicsRectItem
import math
import random_manager
import time
from typing import Optional, List
import pyqtgraph as pg
from config import GameConfig, ALL_BUTTONS, get_button_color
from typing_handler import SimultaneousInputTracker
from word_manager import SequenceGenerator
from enemies import (
    BaseEnemy,
    Enemy,
    RapidHitEnemy,
    LinkedEnemyPair,
    ReverseEnemy,
    ShieldedEnemy,
    ForcefieldBoss,
    EnemyVictoryDeathAnimation,
)
from enemies.phase_shift_boss import PhaseShiftBoss
from enemies.sinusoid_boss import SinusoidBoss
from enemies.chaotic_cloud_boss import ChaoticCloudBoss
from enemies.face_boss import FaceBoss

from font_manager import font_manager
from spawning_manager import SpawningManager
from engagement_indicator import EngagementCrosshair
from wave_transition import WaveTransition
from player_waveform import PlayerHealthWaveform
from effects.lasers import LaserManager
from effects.explosions import ExplosionManager
from effects.screen_shake import ScreenShakeManager
from config_ui import ConfigUI
from sound_manager import SoundManager
from intro_screen import IntroScreen
from starfield_background import StarfieldBackground
from mute_button import MuteButton


from game_over_screen import GameOverScreen
from you_win_screen import YouWinScreen
from high_scores import HighScoreBoard
from high_score_screen import HighScoreScreen

WAVES_PER_BOSS = 4


class GameEngine:
    """Core game engine managing game state and components."""

    def __init__(self, view):
        """Initialize game engine.

        Args:
            view: The pyqtgraph view to render on.
        """
        self.view = view
        self.config = GameConfig()
        self.state = (
            "intro"  # 'intro', 'playing', 'paused', 'death_sequence', 'game_over', 'you_win'
        )

        self.you_win_screen = None
        self.pending_you_win = False  # Set when face boss defeated, triggers after animations

        # Use safe default for audio enabled since audio config might not exist
        audio_enabled = getattr(self.config, "audio", None)
        if audio_enabled:
            audio_enabled = getattr(audio_enabled, "enabled", True)
        else:
            audio_enabled = True

        # Detect if Qt resources are available (bundled app)
        use_resources = QFile.exists(":/sounds/laser_1.wav")
        if use_resources:
            self.sound_manager = SoundManager(enabled=audio_enabled, use_resources=True)
            print("SoundManager initialized with Qt resources")
        else:
            sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")
            self.sound_manager = SoundManager(sounds_dir=sounds_dir, enabled=audio_enabled)
            print(f"SoundManager initialized from filesystem: {sounds_dir}")
        print(f"Audio enabled: {audio_enabled}")

        self.starfield = StarfieldBackground(self.view, n_stars=1500)
        self.starfield.set_game_state("intro")

        self.intro_screen = IntroScreen(self.view, self.config, game_engine=self)
        self.game_over_screen = None
        self.high_score_board = HighScoreBoard()
        self.high_score_screen = None

        # Mute button (always visible, bottom-left)
        self.mute_button = MuteButton(self._on_mute_toggled)
        self.view.addItem(self.mute_button)

        # Start background music with intro screen
        self.sound_manager.play_background_music()

        # Initialize game managers
        # Create laser manager with callback to get waveform Y position
        waveform_y_callback = lambda x: (
            self.player_waveform.get_y_at_x(x) if self.player_waveform else -280
        )
        self.laser_manager = LaserManager(self.view, self.config, None, waveform_y_callback)
        self.explosion_manager = ExplosionManager(self.view, self.config)
        self.shake_manager = ScreenShakeManager(self.view, self.config)
        self.input_tracker = None  # Will be initialized when game starts (needs to reset state)

        # Game state
        self.enemies: List[BaseEnemy] = []
        self.score = 0
        self.wave = 1

        # Statistics tracking
        self.stats = {
            "key_presses": 0,
            "enemies_destroyed": 0,
            "misses": 0,
            "perfect_waves": 0,
        }
        self.wave_misses = 0  # Track misses in current wave
        self.cycle_perfect_waves = set()  # Wave numbers in current boss cycle that were perfect
        self.player_waveform = None  # Created when game starts
        self.engagement_crosshair = None  # Created when game starts

        # Initialize configuration UI early so it can be used in intro/game_over screens
        self.config_ui = ConfigUI(self)
        self.config_ui.restart_requested.connect(self._restart_game)
        self.sequence_generator = SequenceGenerator()
        self.spawning_manager = SpawningManager()
        self.screen_bottom = -300

        # Global animation speed multiplier (1.0 = normal, 0.25 = slow motion)
        self.animation_speed = 1.0
        self.boss_death_timer = 0.0  # Timer to restore speed after boss death

        # Player disable state (e.g., when shield blocks attack)
        self.player_disabled = False
        self.player_disabled_timer = 0.0
        self.player_disabled_duration = 0.3  # Default disable duration

        # Wave spawning state
        self.wave_spawning = False
        self.spawn_queue = []  # Queue of enemies/pairs to spawn
        self.spawn_timer = 0.0
        self.spawn_interval = 0.0  # Time between spawns
        self.remaining_spawn_interval = 0.0  # Interval for spawns after the first
        self.first_spawn_done = False  # Track if first spawn happened
        self.spawn_y_position = 350  # Fixed spawn height
        self.occupied_regions = []  # Track occupied X regions to prevent overlap

        # Wave transition state
        self.wave_transition = None  # Current wave transition animation
        self.pending_wave_num = None  # Wave number waiting to start after transition

        # Death animation state
        self.death_animations = []  # List of active death animations
        self.victory_animations = []  # List of active victory animations

        # Enemy engagement system - unified for all enemy types
        self.engaged_enemy: Optional[BaseEnemy] = None  # Currently engaged enemy

        # Slow motion effect on player hit
        self.slow_motion_active = False
        self.slow_motion_timer = 0.0
        self.slow_motion_base_duration = 1.0  # Base duration per hit
        self.slow_motion_slowdown_duration = 0.2  # 200ms to slow down
        self.slow_motion_base_reduction = 0.25  # Each hit reduces speed by 25%
        self.slow_motion_min_speed = 0.1  # Minimum 10% speed (maximum slowdown)
        self.current_speed_multiplier = 1.0  # Current speed for all enemies
        self.target_speed_multiplier = 1.0  # Target speed to transition to

        # HUD elements
        self.score_text = None
        self.wave_text = None
        self.fps_text = None
        self.pause_text = None
        self.pause_overlay = None
        self.pause_fade_progress = 0.0  # 0 = transparent, 1 = fully dimmed
        self.pause_fade_dir = 0  # +1 fading to pause, -1 fading to playing
        self.fps_samples = []  # For averaging FPS over multiple frames
        self.last_raw_dt = 0.0  # Raw dt for FPS calculation

    def simulate_key_press(self, key: str, timestamp: int):
        """Simulate a key press event."""
        print(f"Simulating key press: {key}")
        self.on_key_press(key, timestamp)

    def simulate_key_release(self, key: str):
        """Simulate a key release event."""
        print(f"Simulating key release: {key}")
        self.on_key_release(key)

    def toggle_mute(self):
        """Toggle mute state (e.g. from 'M' key)."""
        muted = self.sound_manager.enabled  # currently enabled → we're about to mute
        self._on_mute_toggled(muted)
        self.mute_button.set_muted(muted)

    def _on_mute_toggled(self, muted: bool):
        """Called when mute button is clicked or M key pressed."""
        if muted:
            self.sound_manager.enabled = False
            self.sound_manager.music_player_a.setVolume(0)
            self.sound_manager.music_player_b.setVolume(0)
        else:
            self.sound_manager.enabled = True
            self.sound_manager.music_player_a.setVolume(self.sound_manager.music_volume)
            self.sound_manager.music_player_b.setVolume(self.sound_manager.music_volume)

    def on_key_press(self, key: str, timestamp: int):
        """Handle key press event."""
        # Handle backtick key to toggle config UI (available in all states)
        if key == "`":
            self.config_ui.toggle_ui()
            return

        if key == "M":
            self.toggle_mute()
            return

        if key == "P" and self.state in ("playing", "paused"):
            if self.state == "playing":
                self.state = "paused"
                self.pause_fade_dir = 1
                if self.pause_text:
                    self.pause_text.setVisible(True)
                self.sound_manager.fade_music_for_pause(0.3)
            elif self.pause_fade_progress > 0:
                self.pause_fade_dir = -1
                self.sound_manager.fade_music_for_unpause(0.3)
            return

        if self.state == "intro":
            should_start = self.intro_screen.on_key_press(key, timestamp)
            if should_start:
                self._start_game()
        elif self.state == "playing":
            self._handle_game_input(key, timestamp)
        elif self.state == "game_over":
            action = self.game_over_screen.on_key_press(key, timestamp)
            # Action is now "continue" during animation, handled by callback
            if action == "quit":
                self._quit_game()
        elif self.state == "you_win":
            action = self.you_win_screen.on_key_press(key, timestamp)
            # Action is now "continue" during animation, handled by callback
            if action == "quit":
                self._quit_game()
        elif self.state == "high_score":
            action = self.high_score_screen.on_key_press(key, timestamp)
            if action == "quit":
                self._quit_game()

    def on_key_release(self, key: str):
        """Handle key release event."""
        if self.state == "intro":
            self.intro_screen.on_key_release(key)
        elif self.state == "game_over":
            self.game_over_screen.on_key_release(key)
        elif self.state == "you_win":
            self.you_win_screen.on_key_release(key)
        elif self.state == "high_score":
            self.high_score_screen.on_key_release(key)
        elif self.state == "playing":
            if self.input_tracker:
                self.input_tracker.on_button_release(key)

            # Check if any boss enemies need to release their forcefield
            for enemy in self.enemies:
                if isinstance(enemy, ForcefieldBoss):
                    enemy.release_forcefield(key)

    def update(self, dt: float):
        """Update game state."""
        # Store raw dt for FPS calculation
        self.last_raw_dt = dt
        # Apply animation speed multiplier to dt
        adjusted_dt = dt * self.animation_speed

        # Handle boss death timer with gradual speed ramp-up
        if self.boss_death_timer > 0:
            self.boss_death_timer -= dt  # Use real dt, not adjusted

            # Ramp speed back up gradually over the animation duration
            # Start at 0.15, ramp to 1.0 over 3 seconds
            total_duration = 3.0
            time_elapsed = total_duration - self.boss_death_timer
            progress = min(1.0, time_elapsed / total_duration)  # 0 to 1 over animation

            # Use easing function for smooth ramp up
            # Start slow, accelerate in the middle, smooth at the end
            eased_progress = 1 - (1 - progress) ** 3  # Cubic ease-out

            # Interpolate from 0.15 to 1.0
            start_speed = 0.15
            target_speed = 1.0
            self.animation_speed = start_speed + (target_speed - start_speed) * eased_progress

            if self.boss_death_timer <= 0:
                # Ensure we end at exactly 1.0
                self.animation_speed = 1.0
                self.boss_death_timer = 0.0
                print("Boss death animation complete - speed restored to 1.0")

        # Update player disabled timer
        if self.player_disabled:
            self.player_disabled_timer -= dt  # Use real dt
            if self.player_disabled_timer <= 0:
                self.player_disabled = False
                self.player_disabled_timer = 0.0

        # Update pause fade animation (runs regardless of state)
        if self.pause_fade_dir != 0:
            self.pause_fade_progress += self.pause_fade_dir * dt / 0.3
            self.pause_fade_progress = max(0.0, min(1.0, self.pause_fade_progress))
            if self.pause_overlay:
                alpha = int(180 * self.pause_fade_progress)
                self.pause_overlay.setBrush(QBrush(QColor(0, 0, 0, alpha)))
            if self.pause_fade_dir == -1 and self.pause_fade_progress <= 0.0:
                self.state = "playing"
                self.pause_fade_dir = 0
                if self.pause_text:
                    self.pause_text.setVisible(False)
            elif self.pause_fade_dir == 1 and self.pause_fade_progress >= 1.0:
                self.pause_fade_dir = 0

        # Always update starfield background (freeze when paused)
        # Use raw dt outside gameplay so animation_speed doesn't affect intro/game over
        if self.starfield and self.state != "paused":
            starfield_dt = adjusted_dt if self.state in ("playing", "death_sequence") else dt
            self.starfield.update(starfield_dt)

        if self.state == "intro" and self.intro_screen:
            self.intro_screen.update(dt)
        elif self.state == "playing":
            self._update_game(adjusted_dt)
        elif self.state == "death_sequence":
            self._update_death_sequence(adjusted_dt)
        elif self.state == "game_over":
            # Use raw dt for game over screen so explosion isn't affected by slow motion
            self.game_over_screen.update(dt)
        elif self.state == "you_win":
            # Use raw dt for you win screen so explosion isn't affected by slow motion
            self.you_win_screen.update(dt)
        elif self.state == "high_score":
            self.high_score_screen.update(dt)

    def _start_game(self):
        """Transition from intro to playing."""

        # Store selected difficulty from intro screen before it's cleared
        selected_difficulty = self.intro_screen.selected_difficulty

        # Set callback for when intro animation completes
        def on_intro_complete():
            # Apply difficulty settings
            self.config.spawning.apply_difficulty(selected_difficulty)
            print(f"Starting game with difficulty: {selected_difficulty.value.upper()}")

            # Reset animation and game state
            self.animation_speed = 1.0
            self.boss_death_timer = 0.0
            self.score = 0
            self.wave = 1
            self.stats = {"key_presses": 0, "enemies_destroyed": 0, "misses": 0, "perfect_waves": 0}
            self.wave_misses = 0
            self.cycle_perfect_waves = set()
            self.enemies.clear()
            self.death_animations.clear()
            self.victory_animations.clear()
            self.wave_spawning = False
            self.spawn_queue = []
            self.spawn_timer = 0.0
            self.spawn_interval = 0.0
            self.remaining_spawn_interval = 0.0
            self.first_spawn_done = False
            self.spawn_y_position = 350
            self.occupied_regions = []
            self.wave_transition = None
            self.pending_wave_num = None
            self.slow_motion_active = False
            self.slow_motion_timer = 0.0
            self.current_speed_multiplier = 1.0
            self.target_speed_multiplier = 1.0
            self.pending_you_win = False
            self.player_disabled = False
            self.player_disabled_timer = 0.0
            self._clear_engagement()


            # Change state to playing
            self.state = "playing"

            # Update starfield to playing state
            if self.starfield:
                self.starfield.set_game_state("playing")

            # Clear intro screen reference
            self.intro_screen = None

            # Initialize/reset input tracker for fresh game state
            self.input_tracker = SimultaneousInputTracker()

            # Create HUD
            self._create_hud()

            # Reinitialize effects managers
            waveform_y_callback = lambda x: (
                self.player_waveform.get_y_at_x(x) if self.player_waveform else -280
            )
            self.laser_manager = LaserManager(self.view, self.config, None, waveform_y_callback)
            self.explosion_manager = ExplosionManager(self.view, self.config)
            self.sequence_generator = SequenceGenerator()
            self.spawning_manager = SpawningManager()

            # Continue with game initialization
            self._initialize_game_elements()

            # Start first wave after elements are initialized
            self._start_wave_transition(1)

        # Set the callback and trigger the explosion
        self.intro_screen.on_start_callback = on_intro_complete
        self.intro_screen._trigger_start_sequence()

    def _initialize_game_elements(self):
        """Initialize game elements after intro."""
        # Create engagement crosshair (starting off-screen)
        self.engagement_crosshair = EngagementCrosshair(self.view)
        # Start crosshair off-screen (below bottom)
        self.engagement_crosshair.current_pos = (0, -450)
        self.engagement_crosshair.resting_pos = (0, -450)
        self.engagement_crosshair._update_crosshair_position(self.engagement_crosshair.current_pos)

        # Create player health waveform (starting off-screen)
        self.player_waveform = PlayerHealthWaveform(self.view, screen_width=800, screen_height=600)
        # Start waveform off-screen (below bottom)
        self.player_waveform.base_y = -450

        print("Game started!")

    def _handle_game_input(self, key: str, timestamp: int):
        """Handle input during gameplay."""
        if key not in ALL_BUTTONS:
            return

        # Track key presses
        self.stats["key_presses"] += 1

        # Check if player is disabled (e.g., from shield block)
        if self.player_disabled:
            # Play denied sound and show waveform reaching out (no laser)
            self.sound_manager.play_denied_1_sound()
            if self.player_waveform:
                # Add activity spike to show waveform "reaching out"
                self.player_waveform.add_activity(0.3)
            return

        # Block all input if player waveform is disabled (e.g., boss punishment)
        # Do this BEFORE adding to input tracker to avoid buffered inputs
        if self.player_waveform and self.player_waveform.is_disabled():
            return

        # Pass to input tracker
        self.input_tracker.on_button_press(key, timestamp)

        # Handle enemy engagement system
        self._process_enemy_input(key)

    def _process_enemy_input(self, key: str):
        """Process input using the unified engagement system."""
        # If we have an engaged enemy, try to continue with it
        if self.engaged_enemy:
            if self.engaged_enemy.can_type_button(key):
                # Check if attack would be blocked (e.g., by shield)
                if self.engaged_enemy.would_block_attack(key):
                    self.engaged_enemy.handle_blocked_attack(self)
                    # Count blocked attack as a miss
                    self.stats["misses"] += 1
                    self.wave_misses += 1
                else:
                    success = self.engaged_enemy.type_button(key)
                    if success:
                        self.sound_manager.play_laser_sound()
                        if self.engaged_enemy:
                            if self.engaged_enemy.is_complete():
                                self.engaged_enemy.handle_destruction(self)

            elif getattr(self.engaged_enemy, "is_boss", False):
                # Boss - call type_button (handles feedback internally), disengage on failure
                success = self.engaged_enemy.type_button(key)
                if success:
                    self.sound_manager.play_laser_sound()
                    if self.engaged_enemy and self.engaged_enemy.is_complete():
                        self.engaged_enemy.handle_destruction(self)
                else:
                    self._clear_engagement()
            else:
                # Regular enemy - wrong key means reset and disengage
                self.stats["misses"] += 1
                self.wave_misses += 1
                self.sound_manager.play_denied_2_sound()
                self.engaged_enemy.reset_typing_progress()
                self._clear_engagement()

        # No engagement - try to start new engagement or handle boss input
        else:
            # First check for boss projectiles that can be typed
            has_typeable_projectiles = False
            for enemy in self.enemies:
                if not getattr(enemy, "is_boss", False) or enemy.is_complete():
                    continue
                # Check boss projectiles
                if hasattr(enemy, "projectiles") and enemy.projectiles:
                    for projectile in enemy.projectiles:
                        if projectile in self.enemies and projectile.can_type_button(key):
                            has_typeable_projectiles = True
                            break
                if has_typeable_projectiles:
                    break

            if has_typeable_projectiles:
                self._try_start_new_engagement(key)
                return

            # Check for boss enemies that can type this key
            for enemy in self.enemies:
                if not getattr(enemy, "is_boss", False) or enemy.is_complete():
                    continue

                if enemy.can_type_button(key):
                    # Engage the boss and type the key
                    self._engage_enemy(enemy)
                    success = enemy.type_button(key)
                    if success:
                        self.sound_manager.play_laser_sound()
                        if enemy.is_complete():
                            enemy.handle_destruction(self)
                    return

            # Notify bosses of unmatched input (for punishment)
            for enemy in self.enemies:
                if not getattr(enemy, "is_boss", False) or enemy.is_complete():
                    continue
                if hasattr(enemy, "on_unmatched_input") and enemy.on_unmatched_input(key):
                    return

            # No boss handled it - try normal engagement
            self._try_start_new_engagement(key)

    def _try_start_new_engagement(self, key: str):
        """Try to start engagement with enemies that match the key.

        RULE: New enemies can ONLY be engaged if NO other enemy is currently engaged.
        This ensures clean state - wrong keys reset everything to disengaged.
        """
        # Strict rule: Only start new engagement if completely disengaged
        if self.engaged_enemy:
            return

        # Find all enemies that can be typed with this key
        matching_enemies = []

        for enemy in self.enemies:
            if enemy.can_type_button(key):
                matching_enemies.append(enemy)

        if not matching_enemies:
            # No enemy can be typed with this key - count as miss
            self.stats["misses"] += 1
            self.wave_misses += 1
            self.sound_manager.play_denied_2_sound()
            return

        # Sort by distance to player (lowest Y coordinate = closest to player waveform)
        matching_enemies.sort(key=lambda e: e.get_center_position()[1])

        # Get the closest typeable enemy
        closest_enemy = matching_enemies[0]

        # Handle special case for LinkedEnemyPair (pairs use engagement but different input handling)
        if isinstance(closest_enemy, LinkedEnemyPair):
            # Engage the pair so crosshair moves to the link arc
            self._engage_enemy(closest_enemy)
            # Pairs are handled by simultaneous input checking in the main update loop
            # No immediate typing action needed here
            return

        self._engage_enemy(closest_enemy)

        # Check if this is a shielded enemy that would block the attack
        if closest_enemy.would_block_attack(key):
            closest_enemy.handle_blocked_attack(self)
            # Count blocked attack as a miss
            self.stats["misses"] += 1
            self.wave_misses += 1
            return

        success = closest_enemy.type_button(key)
        if success:
            # Play laser sound for successful first hit
            self.sound_manager.play_laser_sound()
        if closest_enemy.is_complete():
            closest_enemy.handle_destruction(self)

    def _engage_enemy(self, enemy):
        """Engage an enemy and highlight it."""
        self.engaged_enemy = enemy
        # Adapt crosshair size to enemy
        enemy_width = enemy.get_width()
        self.engagement_crosshair.set_enemy_size(enemy_width)
        # Move crosshair to next letter position (if method exists) or center
        if hasattr(enemy, "get_next_letter_position"):
            enemy_pos = enemy.get_next_letter_position()
        else:
            enemy_pos = enemy.get_center_position()
        self.engagement_crosshair.set_target(enemy_pos)

    def _clear_engagement(self):
        """Clear current engagement."""
        self.engaged_enemy = None
        # Return crosshair to resting position
        if self.engagement_crosshair:
            self.engagement_crosshair.set_resting()

    def clear_engagement(self):
        """Public method to clear current engagement (for use by enemies)."""
        self._clear_engagement()

    def _update_game(self, dt: float):
        """Update game state during gameplay."""
        current_time = time.time() * 1000  # Convert to milliseconds

        # Handle slow motion effect with smooth transitions
        if self.slow_motion_active:
            self.slow_motion_timer -= dt

            if self.slow_motion_timer <= 0:
                # End slow motion - return to normal speed
                self.slow_motion_active = False
                self.current_speed_multiplier = 1.0
                self.target_speed_multiplier = 1.0
            else:
                # Smoothly transition toward target speed and gradually recover
                speed_diff = self.target_speed_multiplier - self.current_speed_multiplier

                # Fast transition to slower speeds (when hit), slower transition to faster speeds
                if speed_diff < 0:  # Slowing down
                    transition_rate = abs(speed_diff) / self.slow_motion_slowdown_duration
                else:  # Speeding up - gradual recovery
                    transition_rate = abs(speed_diff) / max(0.1, self.slow_motion_timer)

                transition_amount = transition_rate * dt
                if abs(speed_diff) <= transition_amount:
                    self.current_speed_multiplier = self.target_speed_multiplier
                elif speed_diff > 0:
                    self.current_speed_multiplier += transition_amount
                else:
                    self.current_speed_multiplier -= transition_amount

                # Gradually recover target speed toward normal over time
                recovery_rate = (
                    (1.0 - self.target_speed_multiplier) / max(0.1, self.slow_motion_timer) * 0.5
                )
                self.target_speed_multiplier = min(
                    1.0, self.target_speed_multiplier + recovery_rate * dt
                )

            # Apply current speed to all enemies
            for enemy in self.enemies:
                enemy.set_speed_multiplier(self.current_speed_multiplier)

        # Handle wave transition animation
        if self.wave_transition:
            ready_to_spawn = self.wave_transition.update(dt)

            # Start spawning when transition enters exit phase
            if ready_to_spawn and self.pending_wave_num and not self.wave_spawning:
                self._start_wave_spawning(self.pending_wave_num)
                self.pending_wave_num = None
                # Update starfield to exit phase
                if self.starfield:
                    self.starfield.set_game_state("wave_transition_exit")

            # Clean up completed transition
            if self.wave_transition.is_completed():
                # Play whoosh sound for wave transition end
                self.sound_manager.play_whoosh_2_sound()

                self.wave_transition.cleanup()
                self.wave_transition = None
                # Return starfield to playing state
                if self.starfield:
                    self.starfield.set_game_state("playing")

        # Handle timed spawning
        if self.wave_spawning:
            self._update_spawning(dt)

        # Find the closest LinkedEnemyPair by min y position for engagement check
        closest_pair = None
        closest_pair_y = float("inf")
        for enemy in self.enemies:
            if isinstance(enemy, LinkedEnemyPair) and not enemy.is_complete():
                min_y = enemy.get_min_y_position()
                if min_y < closest_pair_y:
                    closest_pair_y = min_y
                    closest_pair = enemy

        # Update enemies (unified processing for all enemy types)
        for enemy in self.enemies[:]:
            # Handle special LinkedEnemyPair simultaneous input processing
            # Only process input if this pair is engaged, OR if no enemy is engaged
            # and this is the closest pair
            if isinstance(enemy, LinkedEnemyPair):
                is_engaged = self.engaged_enemy == enemy
                is_closest_and_no_engagement = enemy == closest_pair and self.engaged_enemy is None
                should_process_input = is_engaged or is_closest_and_no_engagement
                if should_process_input:
                    result = enemy.check_simultaneous_input(
                        self.input_tracker, current_time, is_engaged=is_engaged
                    )
                    if result == "complete":
                        enemy.handle_destruction(self)
                        continue
                    elif result == "active":
                        # Successful simultaneous press - engage and play sound
                        if not is_engaged:
                            self._engage_enemy(enemy)
                        self.sound_manager.play_laser_sound()
                        # Don't continue here - we still need to update the enemy's position!
                    elif result == "failed" and is_engaged:
                        # Disengage the pair enemy when wrong keys pressed
                        self.stats["misses"] += 1
                        self.wave_misses += 1
                        self.sound_manager.play_denied_2_sound()
                        self._clear_engagement()
                        # Don't continue here either - let the enemy update

            # Update enemy and handle boss projectile spawning
            result = enemy.update(dt)

            if result and isinstance(enemy, (ForcefieldBoss, SinusoidBoss, ChaoticCloudBoss)):
                # Add boss projectile(s) to enemies list so they can be typed
                if isinstance(result, list):
                    self.enemies.extend(result)
                else:
                    self.enemies.append(result)

            # Check if any boss is complete (all bosses now inherit from BaseBoss)
            if getattr(enemy, "is_boss", False) and enemy.is_complete():
                enemy.handle_destruction(self)
                continue

            # Check if enemy collided with player waveform
            # Waveform collision height is at the peak amplitude above base_y
            if self.player_waveform:
                waveform_collision_y = (
                    self.player_waveform.base_y + self.player_waveform.max_amplitude
                )
                if enemy.get_center_position()[1] <= waveform_collision_y:
                    enemy.handle_miss(self)

        # Update engagement crosshair
        if self.engagement_crosshair:
            self.engagement_crosshair.update(dt)
            # If we have an engaged enemy, keep crosshair on next letter as it moves
            if self.engaged_enemy:
                if hasattr(self.engaged_enemy, "get_next_letter_position"):
                    enemy_pos = self.engaged_enemy.get_next_letter_position()
                else:
                    enemy_pos = self.engaged_enemy.get_center_position()
                self.engagement_crosshair.set_target(enemy_pos)

        # Update player health waveform
        if self.player_waveform:
            self.player_waveform.update(dt)

            # Check for player death (from any cause - damage or manual restart)
            if self.player_waveform.is_dead() and self.state == "playing":
                self._start_death_sequence()

        # Update effects managers
        if self.laser_manager:
            self.laser_manager.update(dt)
        if self.explosion_manager:
            self.explosion_manager.update(dt)
        if self.shake_manager:
            self.shake_manager.update(dt)

        # Update death animations (only during normal gameplay)
        completed_death_animations = []
        for death_anim in self.death_animations:
            if not death_anim.update(dt):
                completed_death_animations.append(death_anim)

        # Remove completed death animations and cleanup enemies
        for death_anim in completed_death_animations:
            death_anim.enemy.cleanup()
            self.death_animations.remove(death_anim)

        # Update victory animations
        completed_victory_animations = []
        for victory_anim in self.victory_animations:
            if not victory_anim.update(dt):
                completed_victory_animations.append(victory_anim)

        # Remove completed victory animations and cleanup enemies
        for victory_anim in completed_victory_animations:
            # If this is a boss, also remove its projectiles from enemies list
            if hasattr(victory_anim.enemy, "projectiles"):
                # Boss enemy - remove all its projectiles from enemies list
                for projectile in victory_anim.enemy.projectiles[:]:
                    if projectile in self.enemies:
                        self.enemies.remove(projectile)
                        projectile.cleanup()

            victory_anim.enemy.cleanup()
            self.victory_animations.remove(victory_anim)

        # Clean up occupied regions of destroyed enemies
        self._cleanup_occupied_regions()

        # Update HUD
        self._update_hud()

        # Check if wave is complete and start transition
        # Wait for all enemies, animations, and effects to complete
        # Check if pending you win should trigger (after all animations complete)
        if self.pending_you_win:
            animations_complete = (
                not self.victory_animations
                and not self.explosion_manager.has_active_animations()
                and not self.laser_manager.has_active_animations()
            )
            if animations_complete:
                self.pending_you_win = False
                self._trigger_you_win()
                return  # Don't continue with normal update

        wave_complete_conditions = (
            not self.wave_spawning
            and not self.enemies
            and not self.spawn_queue
            and not self.wave_transition
            and not self.death_animations
            and not self.victory_animations
            and not self.laser_manager.has_active_animations()
            and not self.explosion_manager.has_active_animations()
            and (not self.player_waveform or not self.player_waveform.has_active_animations())
        )

        if wave_complete_conditions:
            # Check if wave was completed perfectly (no misses)
            is_perfect_wave = self.wave_misses == 0
            if is_perfect_wave:
                self.stats["perfect_waves"] += 1
                self.cycle_perfect_waves.add(self.wave)
                print(f"PERFECT WAVE {self.wave}!")

            # Reset cycle tracking after boss wave
            next_wave = self.wave + 1
            if next_wave % WAVES_PER_BOSS == 1:
                self.cycle_perfect_waves.clear()

            self._start_wave_transition(next_wave, is_perfect_wave)

    def toggle_explosions(self):
        """Toggle explosion effects."""
        self.config.visual_effects.explosions_enabled = (
            not self.config.visual_effects.explosions_enabled
        )
        self.save_config()

    def toggle_screen_shake(self):
        """Toggle screen shake effect."""
        self.config.visual_effects.screen_shake_enabled = (
            not self.config.visual_effects.screen_shake_enabled
        )
        self.save_config()

    def toggle_lasers(self):
        """Toggle laser effects."""
        self.config.visual_effects.lasers_enabled = not self.config.visual_effects.lasers_enabled
        self.save_config()

    def save_config(self):
        """Save configuration to file."""
        self.config.save()

    # Spawning configuration methods
    def set_test_spawning_for_pairs(self):
        """Set spawning to primarily pairs for testing."""
        self.config.spawning.test_normal_ratio = 0.1
        self.config.spawning.test_rapid_hit_ratio = 0.1
        self.config.spawning.test_pair_ratio = 1.0
        self.save_config()
        print("Spawning set to mostly pairs")

    def set_test_spawning_for_rapid_hit(self):
        """Set spawning to primarily rapid-hit enemies for testing."""
        self.config.spawning.test_normal_ratio = 0.1
        self.config.spawning.test_rapid_hit_ratio = 1.0
        self.config.spawning.test_pair_ratio = 0.1
        self.save_config()
        print("Spawning set to mostly rapid-hit enemies")

    def set_test_spawning_for_normal(self):
        """Set spawning to primarily normal enemies for testing."""
        self.config.spawning.test_normal_ratio = 1.0
        self.config.spawning.test_rapid_hit_ratio = 0.1
        self.config.spawning.test_pair_ratio = 0.1
        self.save_config()
        print("Spawning set to mostly normal enemies")

    def reset_spawning_to_normal(self):
        """Reset spawning to normal ratios."""
        self.config.spawning.test_normal_ratio = -1
        self.config.spawning.test_rapid_hit_ratio = -1
        self.config.spawning.test_pair_ratio = -1
        self.save_config()
        print("Spawning reset to normal ratios")

    def toggle_wave_progression(self):
        """Toggle wave progression on/off."""
        self.config.spawning.enable_wave_progression = (
            not self.config.spawning.enable_wave_progression
        )
        self.save_config()
        status = "enabled" if self.config.spawning.enable_wave_progression else "disabled"
        print(f"Wave progression {status}")

    def set_force_wave(self, wave_number: int):
        """Force a specific wave number."""
        self.config.spawning.force_wave_number = wave_number
        self.save_config()
        if wave_number > 0:
            print(f"Forced wave number to {wave_number}")
        else:
            print("Wave forcing disabled")

    def toggle_infinite_health(self):
        """Toggle infinite health mode."""
        self.config.spawning.infinite_health = not self.config.spawning.infinite_health
        self.save_config()
        status = "enabled" if self.config.spawning.infinite_health else "disabled"
        print(f"Infinite health {status}")

    def damage_player(self, damage: float):
        """Deal damage to the player.

        Note: This method is deprecated. Enemies should use the standard collision
        detection which automatically calls _on_enemy_missed() for proper effects.
        """
        if self.player_waveform and not self.config.spawning.infinite_health:
            # Apply damage multiplier from difficulty settings
            actual_damage = damage * self.config.spawning.damage_multiplier
            self.player_waveform.take_damage(actual_damage)
            print(
                f"Player took {actual_damage} damage! Health: {self.player_waveform.get_health():.1%}"
            )

    def set_speed_multiplier(self, multiplier: float):
        """Set global speed override multiplier for all enemies."""
        self.config.spawning.speed_multiplier = max(0.1, multiplier)  # Minimum 0.1x speed
        self.config.spawning.speed_override_enabled = True
        self.save_config()
        effective_speed = self.config.spawning.get_effective_speed_multiplier()
        print(f"Speed override set to {multiplier:.1f}x (effective: {effective_speed:.2f}x)")

        # Apply immediately to existing enemies
        for enemy in self.enemies:
            enemy.set_config_speed_multiplier(effective_speed)

    def _create_hud(self):
        """Create HUD elements."""
        # Score text (top-left)
        self.score_text = pg.TextItem(f"Score: {self.score}", color=(255, 255, 255), anchor=(0, 0))
        self.score_text.setFont(font_manager.get_hud_font(16, bold=True))
        self.score_text.setPos(-390, 280)
        self.view.addItem(self.score_text)

        # Wave text (top-center)
        self.wave_text = pg.TextItem(f"Wave {self.wave}", color=(255, 255, 255), anchor=(0.5, 0))
        self.wave_text.setFont(font_manager.get_hud_font(16, bold=True))
        self.wave_text.setPos(0, 280)
        self.view.addItem(self.wave_text)

        # FPS text (bottom-right) - only visible if enabled in config
        self.fps_text = pg.TextItem("FPS: --", color=(150, 150, 150), anchor=(1, 1))
        self.fps_text.setFont(font_manager.get_hud_font(12, bold=False))
        self.fps_text.setPos(390, -280)
        self.fps_text.setVisible(self.config.visual_effects.show_fps)
        self.view.addItem(self.fps_text)

        # Semi-transparent black overlay for pause fade
        self.pause_overlay = QGraphicsRectItem(QRectF(-500, -400, 1000, 800))
        self.pause_overlay.setBrush(QBrush(QColor(0, 0, 0, 0)))
        self.pause_overlay.setPen(QColor(0, 0, 0, 0))
        self.pause_overlay.setZValue(50)
        self.view.addItem(self.pause_overlay)

        # Pause text (above overlay)
        self.pause_text = pg.TextItem("PAUSED", color=(255, 255, 100), anchor=(0.5, 0.5))
        self.pause_text.setFont(font_manager.get_hud_font(36, bold=True))
        self.pause_text.setPos(0, 0)
        self.pause_text.setVisible(False)
        self.pause_text.setZValue(51)
        self.view.addItem(self.pause_text)

    def _update_hud(self):
        """Update HUD display."""
        if self.score_text:
            self.score_text.setText(f"Score: {self.score}")
        if self.wave_text:
            self.wave_text.setText(f"Wave {self.wave}")
        if self.fps_text:
            # Update visibility based on config
            self.fps_text.setVisible(self.config.visual_effects.show_fps)
            # Update FPS value if visible
            if self.config.visual_effects.show_fps and self.last_raw_dt > 0:
                current_fps = 1.0 / self.last_raw_dt
                self.fps_samples.append(current_fps)
                # Keep last 30 samples for smoothing
                if len(self.fps_samples) > 30:
                    self.fps_samples.pop(0)
                avg_fps = sum(self.fps_samples) / len(self.fps_samples)
                self.fps_text.setText(f"FPS: {int(avg_fps)}")

    def _is_boss_wave(self, wave_num: int) -> bool:
        """Check if the given wave number is a boss wave."""
        # Apply force_wave_number if configured
        if self.config.spawning.force_wave_number > 0:
            wave_num = self.config.spawning.force_wave_number
        return self.config.spawning.boss_every_wave or (
            (wave_num % WAVES_PER_BOSS == 0) and wave_num > 0
        )

    def _start_wave_transition(self, wave_num: int, is_perfect_wave: bool = False):
        """Start wave transition animation."""
        print(f"Starting wave {wave_num} transition")

        self.pending_wave_num = wave_num
        # Check if this is the first wave (from intro or game over)
        is_first_wave = wave_num == 1
        self.wave_transition = WaveTransition(
            self.view,
            wave_num,
            self.engagement_crosshair,
            self.player_waveform,
            is_first_wave,
            is_perfect_wave,
            self.sound_manager,
            self.cycle_perfect_waves,
        )

        # Play whoosh sound for wave transition start
        self.sound_manager.play_whoosh_1_sound()

        # Trigger starfield wave transition effect
        if self.starfield:
            self.starfield.set_game_state("wave_transition_enter")

    def _start_wave_spawning(self, wave_num: int):
        """Start a new wave with configurable spawning."""
        # Use forced wave number if configured
        if self.config.spawning.force_wave_number > 0:
            wave_num = self.config.spawning.force_wave_number

        self.wave = wave_num
        print(f"Starting wave {wave_num}")

        # Reset wave miss counter for perfect wave tracking
        self.wave_misses = 0

        # Clear previous wave state
        self.spawn_queue.clear()
        self.occupied_regions.clear()
        self.spawn_timer = 0.0
        self.first_spawn_done = False

        if self._is_boss_wave(wave_num):
            # Boss wave - spawn only the boss
            print(f"Wave {wave_num}: BOSS WAVE!")
            self.spawn_queue.append({"type": "boss"})
            self.spawn_interval = 0.5  # Spawn boss quickly after wave transition
            self.wave_spawning = True
            self.first_spawn_done = False
            return

        # Get spawning ratios from config
        (
            normal_ratio,
            rapid_ratio,
            pair_ratio,
            reverse_ratio,
            shielded_ratio,
        ) = self.config.spawning.get_active_ratios()

        # Progressive enemy type introduction:
        # Wave 1: Only basic enemies
        # Wave 2: Introduce rapid-hit enemies
        # Wave 3: Introduce pair enemies
        # Wave 4: Boss wave
        # Wave 5: Introduce shielded enemies
        # Wave 6: Continue with shielded
        # Wave 7+: Introduce reverse enemies (all types available)
        if wave_num == 1:
            rapid_ratio = 0.0
            pair_ratio = 0.0
            reverse_ratio = 0.0
            shielded_ratio = 0.0
        elif wave_num == 2:
            pair_ratio = 0.0
            reverse_ratio = 0.0
            shielded_ratio = 0.0
        elif wave_num <= 4:
            reverse_ratio = 0.0
            shielded_ratio = 0.0
        elif wave_num <= 6:
            reverse_ratio = 0.0
        # Wave 7+ uses all configured ratios

        # Calculate total enemy count based on wave (unless overridden)
        if self.config.spawning.enable_wave_progression:
            # Wave-based scaling: starts at 12, increases by 4 per wave, caps at 48
            difficulty = min(wave_num, 5)
            base_enemies = min(12 + (wave_num - 1) * 4, 48)
            # Apply difficulty multiplier
            total_enemies = max(3, int(base_enemies * self.config.spawning.enemy_count_multiplier))
        else:
            # Fixed count for testing
            total_enemies = 15
            difficulty = 3

        # Normalize ratios
        total_ratio = normal_ratio + rapid_ratio + pair_ratio + reverse_ratio + shielded_ratio
        if total_ratio <= 0:
            # Fallback to normal enemies only
            normal_ratio = 1.0
            rapid_ratio = pair_ratio = reverse_ratio = shielded_ratio = 0.0
            total_ratio = 1.0

        # Calculate enemy counts based on ratios
        normal_count = int((normal_ratio / total_ratio) * total_enemies)
        rapid_count = int((rapid_ratio / total_ratio) * total_enemies)
        pair_count = int((pair_ratio / total_ratio) * total_enemies)
        reverse_count = int((reverse_ratio / total_ratio) * total_enemies)
        shielded_count = int((shielded_ratio / total_ratio) * total_enemies)

        # Ensure at least one of each available enemy type spawns per wave
        # This guarantees variety and that players see introduced enemy types
        if rapid_ratio > 0 and rapid_count == 0:
            rapid_count = 1
        if pair_ratio > 0 and pair_count == 0:
            pair_count = 1
        if reverse_ratio > 0 and reverse_count == 0:
            reverse_count = 1
        if shielded_ratio > 0 and shielded_count == 0:
            shielded_count = 1

        # Adjust for pair counting (each pair uses 2 enemy slots)
        actual_pair_enemies = pair_count * 2
        total_single_enemies = normal_count + rapid_count + reverse_count + shielded_count
        if total_single_enemies + actual_pair_enemies > total_enemies:
            # Reduce normal enemies to fit
            normal_count = max(
                0,
                total_enemies - rapid_count - reverse_count - shielded_count - actual_pair_enemies,
            )

        print(
            f"Wave {wave_num} spawning: {normal_count} normal, {rapid_count} rapid-hit, "
            f"{pair_count} pairs, {reverse_count} reverse, {shielded_count} shielded "
            f"(total_enemies={total_enemies}, ratios: n={normal_ratio:.2f} r={rapid_ratio:.2f} "
            f"p={pair_ratio:.2f})"
        )

        # Generate sequences for normal enemies
        # Apply word length offset from difficulty settings
        max_word_length = max(4, 4 + difficulty + self.config.spawning.max_word_length_offset)
        if normal_count > 0:
            sequences = self.sequence_generator.generate_word_list(
                normal_count,
                min_length=3,
                max_length=max_word_length,
                difficulty=difficulty,
            )
            for sequence in sequences:
                self.spawn_queue.append({"type": "enemy", "sequence": sequence})

        # Generate sequences for rapid hit enemies
        # Introduced wave 2: start at length 1, increase to max 3 over ~15 waves (3x slower)
        if rapid_count > 0:
            waves_since_rapid_intro = max(0, wave_num - 2)
            rapid_max_length = min(3, 1 + waves_since_rapid_intro // 3)
            rapid_sequences = self.sequence_generator.generate_rapid_hit_word_list(
                rapid_count, min_length=1, max_length=rapid_max_length, difficulty=difficulty
            )
            for sequence in rapid_sequences:
                self.spawn_queue.append({"type": "rapid_hit", "sequence": sequence})

        # Generate paired enemies
        # Introduced wave 3: start at length 1, increase to max 4 over ~15 waves (3x slower)
        if pair_count > 0:
            waves_since_pair_intro = max(0, wave_num - 3)
            pair_max_length = min(4, 1 + waves_since_pair_intro // 3)
            pairs = self.sequence_generator.generate_paired_word_list(
                pair_count, min_length=1, max_length=pair_max_length, difficulty=difficulty
            )
            for seq1, seq2 in pairs:
                self.spawn_queue.append({"type": "pair", "sequence1": seq1, "sequence2": seq2})

        # Generate reverse enemies (mirrored text, typed right-to-left)
        # Introduced wave 7: start at length 2, increase to max 5 over ~12 waves (3x slower)
        if reverse_count > 0:
            waves_since_reverse_intro = max(0, wave_num - 7)
            reverse_max_length = min(5, 2 + waves_since_reverse_intro // 3)
            reverse_sequences = self.sequence_generator.generate_word_list(
                reverse_count,
                min_length=2,
                max_length=reverse_max_length,
                difficulty=difficulty,
            )
            for sequence in reverse_sequences:
                self.spawn_queue.append({"type": "reverse", "sequence": sequence})

        # Generate shielded enemies (single letter with rotating shield)
        if shielded_count > 0:
            shielded_sequences = self.sequence_generator.generate_word_list(
                shielded_count,
                min_length=1,
                max_length=1,
                difficulty=difficulty,
            )
            for sequence in shielded_sequences:
                self.spawn_queue.append({"type": "shielded", "sequence": sequence})

        # Shuffle spawn queue so enemy types spawn in random order
        # This gives pairs a fair chance at finding space (they need more room)
        random_manager.shuffle(self.spawn_queue)

        # Calculate spawn intervals - first enemy spawns at 0.5s, rest spread over remaining 9.5s
        if self.spawn_queue:
            if len(self.spawn_queue) == 1:
                # Only one enemy - spawn it at 0.5s
                self.spawn_interval = 0.5
            else:
                # First enemy at 0.5s, remaining enemies spread over 9.5s
                self.spawn_interval = 0.5  # Time to first spawn
                self.remaining_spawn_interval = 9.5 / (len(self.spawn_queue) - 1)

            self.wave_spawning = True
            self.first_spawn_done = False
            total_entities = len(self.spawn_queue)
            print(
                f"Wave {wave_num}: {total_entities} entities to spawn (first at 0.5s, rest over 9.5s)"
            )
        else:
            self.wave_spawning = False

    def _update_spawning(self, dt: float):
        """Handle timed spawning of enemies."""
        self.spawn_timer += dt

        # Determine current spawn interval
        if not hasattr(self, "first_spawn_done"):
            self.first_spawn_done = False

        current_interval = self.spawn_interval
        if self.first_spawn_done and hasattr(self, "remaining_spawn_interval"):
            current_interval = self.remaining_spawn_interval

        # Check if it's time to spawn next enemy
        if self.spawn_timer >= current_interval and self.spawn_queue:
            self.spawn_timer = 0.0
            spawn_data = self.spawn_queue.pop(0)

            if spawn_data["type"] == "enemy":
                self._spawn_single_enemy(spawn_data["sequence"])
            elif spawn_data["type"] == "rapid_hit":
                self._spawn_rapid_hit_enemy(spawn_data["sequence"])
            elif spawn_data["type"] == "pair":
                self._spawn_enemy_pair(spawn_data["sequence1"], spawn_data["sequence2"])
            elif spawn_data["type"] == "reverse":
                self._spawn_reverse_enemy(spawn_data["sequence"])
            elif spawn_data["type"] == "shielded":
                self._spawn_shielded_enemy(spawn_data["sequence"])
            elif spawn_data["type"] == "boss":
                self._spawn_boss()

            # Mark first spawn as done and switch to remaining interval
            if not self.first_spawn_done:
                self.first_spawn_done = True

            # Check if wave spawning is complete
            if not self.spawn_queue:
                self.wave_spawning = False
                print(f"Wave {self.wave} spawning complete")

    def _spawn_single_enemy(self, sequence: str):
        """Spawn a single enemy at a non-overlapping position."""
        enemy_width = (len(sequence) - 1) * 30 + 40
        position = self._find_spawn_position(enemy_width)

        if position:
            enemy = Enemy(sequence, position, self.view, self.laser_manager, self.player_waveform)
            # Apply effective speed multiplier (difficulty + optional override)
            enemy.speed *= self.config.spawning.get_effective_speed_multiplier()
            self.enemies.append(enemy)

            # Mark region as occupied
            self._mark_region_occupied(position[0], enemy_width)
            print(f"Spawned enemy '{sequence}' at {position}")
        else:
            print(f"Failed to find position for enemy '{sequence}' - no space available")

    def _spawn_rapid_hit_enemy(self, sequence: str):
        """Spawn a rapid hit enemy at a non-overlapping position."""
        enemy_width = (len(sequence) - 1) * 40 + 50  # Wider spacing for rapid hit
        position = self._find_spawn_position(enemy_width)

        if position:
            rapid_enemy = RapidHitEnemy(
                sequence,
                position,
                self.view,
                self.laser_manager,
                self.player_waveform,
                max_hit_count=self.config.spawning.rapid_hit_max_count,
            )
            # Apply effective speed multiplier (difficulty + optional override)
            rapid_enemy.speed *= self.config.spawning.get_effective_speed_multiplier()
            self.enemies.append(rapid_enemy)

            # Mark region as occupied
            self._mark_region_occupied(position[0], enemy_width)
            print(f"Spawned rapid hit enemy '{sequence}' at {position}")
        else:
            print(f"Failed to find position for rapid hit enemy '{sequence}' - no space available")

    def _spawn_reverse_enemy(self, sequence: str):
        """Spawn a reverse enemy (typed right-to-left)."""
        enemy_width = (len(sequence) - 1) * 30 + 40
        position = self._find_spawn_position(enemy_width)

        if position:
            reverse_enemy = ReverseEnemy(
                sequence,
                position,
                self.view,
                self.laser_manager,
                self.player_waveform,
            )
            # Apply effective speed multiplier (difficulty + optional override)
            reverse_enemy.speed *= self.config.spawning.get_effective_speed_multiplier() * 0.75
            self.enemies.append(reverse_enemy)

            # Mark region as occupied
            self._mark_region_occupied(position[0], enemy_width)
            print(f"Spawned reverse enemy '{sequence}' at {position}")
        else:
            print(f"Failed to find position for reverse enemy '{sequence}' - no space available")

    def _spawn_shielded_enemy(self, sequence: str):
        """Spawn a shielded enemy (single letter with rotating shield)."""
        enemy_width = 90  # Wider due to shield
        position = self._find_spawn_position(enemy_width)

        if position:
            shielded_enemy = ShieldedEnemy(
                sequence,
                position,
                self.view,
                self.laser_manager,
                self.player_waveform,
            )
            # Apply effective speed multiplier (difficulty + optional override)
            shielded_enemy.speed *= self.config.spawning.get_effective_speed_multiplier()
            self.enemies.append(shielded_enemy)

            # Mark region as occupied
            self._mark_region_occupied(position[0], enemy_width)
            print(f"Spawned shielded enemy '{sequence}' at {position}")
        else:
            print(f"Failed to find position for shielded enemy '{sequence}' - no space available")

    def _spawn_enemy_pair(self, seq1: str, seq2: str):
        """Spawn a pair of linked enemies."""
        width1 = (len(seq1) - 1) * 30 + 40
        width2 = (len(seq2) - 1) * 30 + 40
        separation = max(120, (width1 + width2) / 2 + 40)
        total_width = width1 + width2 + separation

        # Find center position for pair
        center_x = self._find_pair_center_position(total_width)

        if center_x is not None:
            pos1 = (center_x - separation / 2, self.spawn_y_position)
            pos2 = (center_x + separation / 2, self.spawn_y_position)

            pair = LinkedEnemyPair(
                seq1,
                seq2,
                pos1,
                pos2,
                self.view,
                self.laser_manager,
                self.player_waveform,
            )
            # Apply effective speed multiplier to both enemies in the pair
            effective_speed = self.config.spawning.get_effective_speed_multiplier()
            pair.enemy1.speed *= effective_speed
            pair.enemy2.speed *= effective_speed
            self.enemies.append(pair)

            # Mark both regions as occupied
            self._mark_region_occupied(center_x, total_width)
            print(f"Spawned pair '{seq1}'-'{seq2}' at center {center_x}")
        else:
            print(f"Failed to find position for pair '{seq1}'-'{seq2}' - no space available")

    def _spawn_boss(self):
        """Spawn a boss enemy."""
        # Boss spawns in the center at the top
        boss_pos = (0, self.spawn_y_position)

        # Check if we should only spawn a specific boss type for testing
        if self.config.spawning.test_sinusoid_boss:
            spawn_choice = "sinusoid"
            print(f"DEBUG: test_sinusoid_boss is enabled, forcing Sinusoid Boss")
        elif self.config.spawning.test_phase_shift_boss:
            spawn_choice = "phase_shift"
            print(f"DEBUG: test_phase_shift_boss is enabled, forcing Phase Shift Boss")
        elif self.config.spawning.test_force_field_boss:
            spawn_choice = "force_field"
            print(f"DEBUG: test_force_field_boss is enabled, forcing Force Field Boss")
        elif self.config.spawning.test_chaotic_cloud_boss:  # New test option
            spawn_choice = "chaotic_cloud"
            print(f"DEBUG: test_chaotic_cloud_boss is enabled, forcing Chaotic Cloud Boss")
        elif self.config.spawning.test_face_boss:
            spawn_choice = "face"
            print(f"DEBUG: test_face_boss is enabled, forcing Face Boss")
        else:
            # Determine which boss type to spawn based on boss encounter count
            boss_count = (self.wave // WAVES_PER_BOSS) if self.wave > 0 else 1
            boss_types = [
                "chaotic_cloud",
                "phase_shift",
                "force_field",
                "sinusoid",
                "face",
            ]  # Add new boss type
            spawn_choice = boss_types[(boss_count - 1) % len(boss_types)]
            print(
                f"DEBUG: Normal boss rotation - wave {self.wave}, boss_count {boss_count}, spawn_choice: {spawn_choice}"
            )

        if spawn_choice == "force_field":
            # Original boss with rotating forcefield
            # Create callback for core enemy destruction
            def on_core_enemy_destroyed(core_enemy):
                self._on_enemy_destroyed(core_enemy)

            boss = ForcefieldBoss(
                boss_pos,
                self.view,
                self.laser_manager,
                self.player_waveform,
                on_core_enemy_destroyed,
                self.sound_manager,  # Pass sound_manager
            )
            # Apply effective speed multiplier to all boss speeds
            effective_speed = self.config.spawning.get_effective_speed_multiplier()
            boss.entry_speed *= effective_speed
            boss.horizontal_speed *= effective_speed
            print(f"Spawned BOSS (Forcefield Type) at {boss_pos}")
        elif spawn_choice == "phase_shift":
            # Phase shift boss with dimensional mechanics
            boss = PhaseShiftBoss(
                self.view, self.laser_manager, self.player_waveform, game_engine=self
            )

            # Set destruction callback
            def on_phase_boss_destroyed(enemy, is_boss=False, is_boss_segment=False):
                if is_boss:
                    # Use handle_destruction for proper death animation callbacks
                    # Guard against double-call (update loop also checks is_complete)
                    if enemy in self.enemies:
                        enemy.handle_destruction(self)
                elif is_boss_segment:
                    center_pos = enemy.get_center_position()
                    button = (
                        enemy.sequence[0] if hasattr(enemy, "sequence") and enemy.sequence else "S"
                    )
                    self.explosion_manager.create_explosion(
                        center_pos,
                        color=get_button_color(button),
                        explosion_type="enhanced",
                        intensity=1.5,
                    )
                    self.sound_manager.play_explosion_sound()
                    self.shake_manager.trigger_shake(magnitude=3.0, duration=0.2)

            boss.destruction_callback = on_phase_boss_destroyed
            print(f"Spawned BOSS (Phase Shift Type) at {boss_pos}")

        elif spawn_choice == "sinusoid":
            boss = SinusoidBoss(
                pos=boss_pos,
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.player_waveform,
                game_engine=self,
            )
            print(f"Spawned BOSS (Sinusoid Type) at {boss_pos}")

        elif spawn_choice == "chaotic_cloud":
            boss = ChaoticCloudBoss(
                pos=boss_pos,
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.player_waveform,
                game_engine=self,
                attack_interval_multiplier=self.config.spawning.chaotic_cloud_attack_interval_multiplier,
            )
            print(f"Spawned BOSS (Chaotic Cloud Type) at {boss_pos}")

        elif spawn_choice == "face":
            boss = FaceBoss(
                view=self.view,
                laser_manager=self.laser_manager,
                waveform=self.player_waveform,
                game_engine=self,
            )

            # Set destruction callback - face boss triggers you win screen
            def on_face_boss_destroyed(enemy, is_boss=False):
                if is_boss:
                    self._on_enemy_destroyed(enemy)
                    # Face boss is the final boss - set pending you win
                    # (actual transition happens after animations complete)
                    self.pending_you_win = True

            boss.destruction_callback = on_face_boss_destroyed
            print(f"Spawned BOSS (Face Type) at {boss_pos}")

        self.enemies.append(boss)

        # Play dramatic sound for boss appearance
        if self.sound_manager:
            self.sound_manager.play_whoosh_2_sound()

    def _find_spawn_position(self, enemy_width: float) -> tuple:
        """Find a non-overlapping spawn position for single enemy."""
        screen_width = 800
        margin = 50

        # Calculate safe x range
        half_width = enemy_width / 2
        min_x = -screen_width / 2 + margin + half_width
        max_x = screen_width / 2 - margin - half_width

        # Try to find non-overlapping position
        for attempt in range(100):
            x = random_manager.uniform(min_x, max_x)

            if self._is_position_clear(x, enemy_width):
                return (x, self.spawn_y_position)

        return None

    def _find_pair_center_position(self, total_width: float) -> float:
        """Find center position for enemy pair that doesn't overlap."""
        screen_width = 800
        margin = 50

        # Calculate safe center range
        half_total_width = total_width / 2
        min_center = -screen_width / 2 + margin + half_total_width
        max_center = screen_width / 2 - margin - half_total_width

        # Try to find non-overlapping center
        for attempt in range(100):
            center_x = random_manager.uniform(min_center, max_center)

            if self._is_position_clear(center_x, total_width):
                return center_x

        return None

    def _is_position_clear(self, x: float, width: float) -> bool:
        """Check if position is clear of existing enemies/occupied regions."""
        half_width = width / 2
        min_separation = 30  # Minimum gap between enemies

        # Check against occupied regions
        for occupied_x, occupied_width in self.occupied_regions:
            occupied_half_width = occupied_width / 2

            # Check for overlap with buffer zone
            distance = abs(x - occupied_x)
            required_distance = half_width + occupied_half_width + min_separation

            if distance < required_distance:
                return False

        # Check against existing enemies
        for enemy in self.enemies:
            enemy_pos = enemy.get_center_position()
            enemy_width = enemy.get_width()
            enemy_half_width = enemy_width / 2

            distance = abs(x - enemy_pos[0])
            required_distance = half_width + enemy_half_width + min_separation

            if distance < required_distance:
                return False

        # Check against existing pairs (now included in unified enemies list)
        # Already checked above in the unified enemies loop

        return True

    def _mark_region_occupied(self, x: float, width: float):
        """Mark a region as occupied by an enemy."""
        self.occupied_regions.append((x, width))

    def _cleanup_occupied_regions(self):
        """Remove occupied regions for enemies that no longer exist."""
        # This is a simplified cleanup - in a full implementation,
        # you'd track which enemy owns which region
        # For now, we'll clear regions periodically
        if len(self.occupied_regions) > len(self.enemies) * 2:
            self.occupied_regions.clear()

    def _on_enemy_destroyed(self, enemy: BaseEnemy):
        """Handle enemy destruction for all enemy types using unified interface."""
        # Track enemies destroyed
        self.stats["enemies_destroyed"] += 1

        # Get destruction info from the enemy itself
        destruction_info = enemy.get_destruction_info()

        # Update score
        points = destruction_info["points"]
        self.score += points
        print(f"Enemy destroyed! +{points} points")

        # Trigger slow motion for boss death
        if isinstance(enemy, ForcefieldBoss):
            # Set animation speed to slow motion (similar to game over)
            self.animation_speed = 0.15  # Dramatic slow motion
            # Schedule return to normal speed after 3 seconds
            self.boss_death_timer = 3.0

        # Play explosion sound
        self.sound_manager.play_explosion_sound()

        # Create explosion effect at enemy position
        if self.explosion_manager:
            if isinstance(enemy, LinkedEnemyPair):
                # Multiple explosions for pairs
                pos1 = enemy.enemy1.get_center_position()
                pos2 = enemy.enemy2.get_center_position()
                first_letter = enemy.sequence1[0] if enemy.sequence1 else "A"
                second_letter = enemy.sequence2[0] if enemy.sequence2 else "B"
                self.explosion_manager.create_explosion(
                    pos1,
                    get_button_color(first_letter),
                    destruction_info["explosion_type"],
                    destruction_info["explosion_scale"],
                )
                self.explosion_manager.create_explosion(
                    pos2,
                    get_button_color(second_letter),
                    destruction_info["explosion_type"],
                    destruction_info["explosion_scale"],
                )
            else:
                # Single explosion for normal/rapid hit enemies
                enemy_pos = enemy.get_center_position()
                first_letter = (
                    getattr(enemy, "sequence", ["A"])[0]
                    if hasattr(enemy, "sequence") and enemy.sequence
                    else "A"
                )
                self.explosion_manager.create_explosion(
                    enemy_pos,
                    get_button_color(first_letter),
                    destruction_info["explosion_type"],
                    destruction_info["explosion_scale"],
                )

        # Add screen shake based on enemy type
        if self.shake_manager:
            shake_type = destruction_info["shake_type"]
            if shake_type == "large":
                self.shake_manager.large_shake()
            elif shake_type == "medium":
                self.shake_manager.medium_shake()
            else:  # 'enemy_destroyed' or other
                self.shake_manager.enemy_destroyed_shake()

        # Remove from enemies list but don't cleanup yet
        if enemy in self.enemies:
            self.enemies.remove(enemy)

        # Add immediate waveform activity at enemy center position
        if self.player_waveform:
            enemy_pos = enemy.get_center_position()
            self.player_waveform.add_targeted_activity(enemy_pos[0], intensity=1.2, duration=1.5)

        # Start victory animation - let enemy handle its own victory animations
        victory_animations = enemy.create_victory_animations()
        self.victory_animations.extend(victory_animations)

        # Start letter collection animations - unified handling using properties
        # Skip for bosses which don't have letter_items/sequence
        if self.player_waveform and hasattr(enemy, "letter_items") and hasattr(enemy, "sequence"):
            letter_items = enemy.letter_items  # Uses unified property interface
            sequence = enemy.sequence  # Uses unified property interface
            for i, letter_item in enumerate(letter_items):
                if i < len(sequence):
                    letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                    letter = sequence[i]
                    self.player_waveform.add_letter_collection(letter_pos[0], letter)
                    if self.player_waveform.letter_animations:
                        self.player_waveform.letter_animations[-1]["start_y"] = letter_pos[1]

    def _on_rapid_hit_enemy_destroyed(self, rapid_enemy: RapidHitEnemy):
        """Handle rapid hit enemy destruction."""
        # Bonus score for rapid hit enemies (higher difficulty)
        base_points = len(rapid_enemy.sequence) * 15  # More points than normal enemies
        hit_bonus = sum(rapid_enemy.hit_counts_required) * 2  # Bonus for total hits required
        points = base_points + hit_bonus
        self.score += points

        print(f"Rapid hit enemy destroyed! +{points} points")

        # Remove from enemies list but don't cleanup yet
        if rapid_enemy in self.enemies:
            self.enemies.remove(rapid_enemy)

        # Add immediate waveform activity at enemy center position
        if self.player_waveform:
            enemy_pos = rapid_enemy.get_center_position()
            self.player_waveform.add_targeted_activity(enemy_pos[0], intensity=1.5, duration=2.0)

        # Start victory animation towards blue collection point
        victory_animation = EnemyVictoryDeathAnimation(rapid_enemy, self.view)
        self.victory_animations.append(victory_animation)

        # Start letter collection animations immediately
        if self.player_waveform:
            for i, letter_item in enumerate(rapid_enemy.letter_items):
                if i < len(rapid_enemy.sequence):
                    letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                    letter = rapid_enemy.sequence[i]
                    self.player_waveform.add_letter_collection(letter_pos[0], letter)
                    if self.player_waveform.letter_animations:
                        self.player_waveform.letter_animations[-1]["start_y"] = letter_pos[1]

    def _on_pair_destroyed(self, pair: LinkedEnemyPair):
        """Handle enemy pair destruction."""
        # Bonus points for synchronized typing
        points = (len(pair.sequence1) + len(pair.sequence2)) * 15
        self.score += points

        # TODO: Add dual explosion effects in Phase 3
        print(f"Enemy pair destroyed! +{points} points")

        # Remove from enemies list but don't cleanup yet
        if pair in self.enemies:
            self.enemies.remove(pair)

        # Add immediate waveform activity for both enemy positions
        if self.player_waveform:
            enemy1_pos = pair.enemy1.get_center_position()
            enemy2_pos = pair.enemy2.get_center_position()
            self.player_waveform.add_targeted_activity(enemy1_pos[0], intensity=1.5, duration=1.8)
            self.player_waveform.add_targeted_activity(enemy2_pos[0], intensity=1.5, duration=1.8)

        # Start victory animations for both enemies in the pair
        victory_anim1 = EnemyVictoryDeathAnimation(pair.enemy1, self.view)
        victory_anim2 = EnemyVictoryDeathAnimation(pair.enemy2, self.view)
        self.victory_animations.extend([victory_anim1, victory_anim2])

        # Clean up pair visuals immediately
        # Note: We only clean up the link visuals here, individual enemies are cleaned up by victory animations
        if pair.link_line and pair.link_line.scene() is not None:
            self.view.removeItem(pair.link_line)
        if pair.link_glow and pair.link_glow.scene() is not None:
            self.view.removeItem(pair.link_glow)
        if pair.sync_icon and pair.sync_icon.scene() is not None:
            self.view.removeItem(pair.sync_icon)

        # Start letter collection animations immediately (concurrent with victory animations)
        if self.player_waveform:
            # Enemy 1 letters
            for i, letter_item in enumerate(pair.enemy1.letter_items):
                if i < len(pair.enemy1.sequence):
                    letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                    letter = pair.enemy1.sequence[i]
                    self.player_waveform.add_letter_collection(letter_pos[0], letter)
                    if self.player_waveform.letter_animations:
                        self.player_waveform.letter_animations[-1]["start_y"] = letter_pos[1]

            # Enemy 2 letters
            for i, letter_item in enumerate(pair.enemy2.letter_items):
                if i < len(pair.enemy2.sequence):
                    letter_pos = (letter_item.pos().x(), letter_item.pos().y())
                    letter = pair.enemy2.sequence[i]
                    self.player_waveform.add_letter_collection(letter_pos[0], letter)
                    if self.player_waveform.letter_animations:
                        self.player_waveform.letter_animations[-1]["start_y"] = letter_pos[1]

    def _trigger_slow_motion(self):
        """Trigger slow motion effect for all enemies with additive stacking."""
        # Initialize if first time
        if not hasattr(self, "current_speed_multiplier"):
            self.current_speed_multiplier = 1.0
        if not hasattr(self, "target_speed_multiplier"):
            self.target_speed_multiplier = 1.0

        # Additive effects: reduce target speed further and extend time
        self.target_speed_multiplier = max(
            self.slow_motion_min_speed,
            self.target_speed_multiplier - self.slow_motion_base_reduction,
        )

        # Add to the timer (stacking duration)
        self.slow_motion_timer += self.slow_motion_base_duration
        self.slow_motion_active = True

    def _on_enemy_missed(self, enemy: BaseEnemy):
        """Handle enemy colliding with player waveform using unified interface."""
        if self.player_waveform and self.player_waveform.is_dead():
            return  # Already game over, ignore additional misses

        # Get miss info from the enemy itself
        miss_info = enemy.get_miss_info()

        # Count as a miss (negates perfect wave)
        self.stats["misses"] += 1
        self.wave_misses += 1

        # Take damage to health waveform (unless infinite health is enabled)
        # Apply damage multiplier from difficulty settings
        if self.player_waveform and not self.config.spawning.infinite_health:
            actual_damage = miss_info["damage"] * self.config.spawning.damage_multiplier
            self.player_waveform.take_damage(actual_damage)
            print(
                f"{miss_info['enemy_type_name']} hit player! Health: {self.player_waveform.get_health():.1%}"
            )

            # Check if this is the final hit (health is now zero)
            is_final_hit = self.player_waveform.is_dead()

            # Play appropriate hit sound
            if is_final_hit:
                # Play dramatic final hit sound
                self.sound_manager.play_player_hit_2_sound()
            else:
                # Play normal hit sound
                self.sound_manager.play_player_hit_sound()

            # Trigger slow motion effect on hit
            self._trigger_slow_motion()

            # Add screen shake when player gets hit (more intense for final hit)
            if self.shake_manager:
                if is_final_hit:
                    self.shake_manager.large_shake()  # Intense shake for death
                else:
                    self.shake_manager.enemy_hit_shake()
        elif self.config.spawning.infinite_health:
            print(f"{miss_info['enemy_type_name']} hit player! (Infinite health enabled)")

            # Still add visual effects even with infinite health
            if self.shake_manager:
                self.shake_manager.enemy_hit_shake()

        # Remove from active enemies list but don't cleanup yet
        if enemy in self.enemies:
            self.enemies.remove(enemy)

        # Clear engagement if this enemy was engaged
        if self.engaged_enemy == enemy:
            self._clear_engagement()

        # Start death animation - let enemy handle its own death animations
        death_animations = enemy.create_death_animations()
        self.death_animations.extend(death_animations)

        # Check if health reached zero
        if self.player_waveform and self.player_waveform.is_dead():
            self._start_death_sequence()

    def _start_death_sequence(self):
        """Start the dramatic death sequence - all enemies burn before game over."""
        print("Starting dramatic death sequence...")

        self.state = "death_sequence"

        # Apply dramatic slowdown effect (0.25x speed)
        self.animation_speed = 0.25
        print("Animation speed slowed to 0.25x")

        # Start fading out background music over 1 second
        if self.sound_manager:
            self.sound_manager.fade_out_background_music(duration=1.0)

        # Update starfield to game over state
        if self.starfield:
            self.starfield.set_game_state("game_over")

        # Start player waveform death sequence
        if self.player_waveform:
            self.player_waveform.start_death_sequence()

        # Start death animations for ALL remaining enemies using unified handling
        enemies_to_process = self.enemies[:]  # Make a copy before clearing
        self.enemies.clear()  # Clear active enemies list immediately

        for enemy in enemies_to_process:
            # Clear engagement if this enemy was engaged
            if self.engaged_enemy == enemy:
                self._clear_engagement()

            # Skip death animation for bosses (they don't have sequence/letter_items)
            if hasattr(enemy, "is_boss") and enemy.is_boss:
                enemy.cleanup()
                continue

            # Start death animation - let enemy handle its own death animations
            death_animations = enemy.create_death_animations()
            self.death_animations.extend(death_animations)

    def _update_death_sequence(self, dt: float):
        """Update death sequence - wait for all animations and explosions to complete."""
        # Keep effects managers running so visible explosions complete
        if self.laser_manager:
            self.laser_manager.update(dt)
        if self.explosion_manager:
            self.explosion_manager.update(dt)
        if self.shake_manager:
            self.shake_manager.update(dt)

        # Continue updating victory animations (boss death may still be playing)
        completed_victory_animations = []
        for victory_anim in self.victory_animations:
            if not victory_anim.update(dt):
                completed_victory_animations.append(victory_anim)
        for victory_anim in completed_victory_animations:
            if hasattr(victory_anim.enemy, "projectiles"):
                for projectile in victory_anim.enemy.projectiles[:]:
                    if projectile in self.enemies:
                        self.enemies.remove(projectile)
                        projectile.cleanup()
            victory_anim.enemy.cleanup()
            self.victory_animations.remove(victory_anim)

        # Update death animations
        completed_death_animations = []
        for death_anim in self.death_animations:
            if not death_anim.update(dt):
                completed_death_animations.append(death_anim)

        # Remove completed death animations and cleanup enemies
        for death_anim in completed_death_animations:
            death_anim.enemy.cleanup()
            self.death_animations.remove(death_anim)

        # Wait for all animations and explosions to complete
        explosions_done = (
            not self.explosion_manager or not self.explosion_manager.has_active_animations()
        )
        all_done = not self.death_animations and not self.victory_animations and explosions_done
        if all_done:
            print("All death animations complete - showing game over")
            self._game_over()

    def _game_over(self):
        """Handle game over."""
        print(f"Game Over! Final Score: {self.score}")

        # Clean up current game state
        self._cleanup_game()

        # Play game over music
        if self.sound_manager:
            self.sound_manager.play_gameover_music()

        self.game_over_screen = GameOverScreen(
            self.view, self.config, self.score, self.wave, game_engine=self, stats=self.stats
        )

        # Set callback for restart explosion animation - go back to intro
        self.game_over_screen.on_restart_callback = self._show_high_scores

        self.state = "game_over"

        # Keep animation speed slow for a bit longer, then gradually return to normal
        # This will be handled in the game over screen update

        # Update starfield to game over state (already set in _start_death_sequence)
        if self.starfield:
            self.starfield.set_game_state("game_over")

    def _trigger_you_win(self):
        """Trigger the you win screen after defeating the face boss."""
        print(f"YOU WIN! Final Score: {self.score}")

        # Clean up current game state
        self._cleanup_game()

        # Play you win music (fade out background music first)
        if self.sound_manager:
            self.sound_manager.fade_out_background_music(duration=0.5)

        # Create you win screen
        self.you_win_screen = YouWinScreen(
            self.view, self.config, self.score, self.wave, game_engine=self, stats=self.stats
        )

        # Set callback for restart explosion animation - go back to intro
        self.you_win_screen.on_restart_callback = self._show_high_scores

        self.state = "you_win"

        # Reset animation speed to normal
        self.animation_speed = 1.0

        # Update starfield to playing state (you win screen handles its own pulse)
        if self.starfield:
            self.starfield.set_game_state("playing")
            # Stop any active flash effect
            self.starfield.flash_active = False
            self.starfield.flash_bg.setVisible(False)

    def trigger_you_win_test(self):
        """Trigger the you win screen for testing purposes."""
        if self.state == "playing":
            self._trigger_you_win()

    def _cleanup_game(self):
        """Forcibly clean up all game objects and ensure complete destruction."""
        print("Forcibly cleaning up all game objects...")

        # Force cleanup of any remaining active enemies (should be rare, but ensures completeness)
        for enemy in self.enemies[:]:
            print(f"Force cleanup active enemy: {type(enemy).__name__}")
            enemy.cleanup()
        self.enemies.clear()

        # Clean up HUD
        if self.score_text:
            self.view.removeItem(self.score_text)
            self.score_text = None
        if self.wave_text:
            self.view.removeItem(self.wave_text)
            self.wave_text = None
        if self.fps_text:
            self.view.removeItem(self.fps_text)
            self.fps_text = None
        if self.pause_text:
            self.view.removeItem(self.pause_text)
            self.pause_text = None
        if self.pause_overlay:
            self.view.removeItem(self.pause_overlay)
            self.pause_overlay = None
        self.pause_fade_progress = 0.0
        self.pause_fade_dir = 0
        self.fps_samples = []

        # Clean up crosshair
        if self.engagement_crosshair:
            self.engagement_crosshair.cleanup()
            self.engagement_crosshair = None

        # Clean up player waveform
        if self.player_waveform:
            self.player_waveform.cleanup()
            self.player_waveform = None

        # Clean up wave transition
        if self.wave_transition:
            self.wave_transition.cleanup()
            self.wave_transition = None

        # Force cleanup of all death animations and their enemies
        for death_anim in self.death_animations:
            print(f"Force cleanup death animation enemy: {type(death_anim.enemy).__name__}")
            # Cleanup the animation's own visual elements
            if hasattr(death_anim, "cleanup"):
                death_anim.cleanup()
            death_anim.enemy.cleanup()
        self.death_animations.clear()

        # Force cleanup of all victory animations and their enemies
        for victory_anim in self.victory_animations:
            print(f"Force cleanup victory animation enemy: {type(victory_anim.enemy).__name__}")
            # Cleanup the animation's own visual elements (rings, etc.)
            if hasattr(victory_anim, "cleanup"):
                victory_anim.cleanup()
            victory_anim.enemy.cleanup()
        self.victory_animations.clear()

        # Clean up effects managers
        if self.laser_manager:
            self.laser_manager.cleanup()
            self.laser_manager = None
        if self.explosion_manager:
            self.explosion_manager.cleanup()
            self.explosion_manager = None
        if self.shake_manager:
            self.shake_manager.stop_shake()

        # Hide config UI
        if self.config_ui:
            self.config_ui.hide_ui()

        # Clear any engagement state
        self._clear_engagement()

        print("Game cleanup completed - all active elements destroyed")

    def _restart_game(self):
        """Restart the game by setting player health to zero, triggering natural game over flow."""
        if self.state in ("game_over", "you_win", "high_score"):
            # Already in game over or you win state - proceed with restart directly
            self._perform_restart()
        elif self.player_waveform:
            # Set player health to zero to trigger natural death sequence and cleanup
            print("Restart requested - setting player health to zero for proper cleanup")
            self.player_waveform.set_health(0.0)
        else:
            # No active game or already dead - safe to restart directly
            self._perform_restart()

    def _perform_restart(self):
        """Perform the actual game restart after cleanup."""
        # Clean up game over screen
        if self.game_over_screen:
            self.game_over_screen.cleanup()
            self.game_over_screen = None

        # Clean up you win screen
        if self.you_win_screen:
            self.you_win_screen.cleanup()
            self.you_win_screen = None

        # Clean up high score screen
        if self.high_score_screen:
            self.high_score_screen.cleanup()
            self.high_score_screen = None

        # Cross-fade from game over music back to background music
        if self.sound_manager:
            self.sound_manager.crossfade_to_background_music(duration=1.0)

        # Reset animation speed back to normal
        self.animation_speed = 1.0
        print("Animation speed restored to 1.0x")

        # Reset game state
        self.score = 0
        self.wave = 1
        self.stats = {"key_presses": 0, "enemies_destroyed": 0, "misses": 0, "perfect_waves": 0}
        self.wave_misses = 0
        self.cycle_perfect_waves = set()
        self.enemies.clear()
        self.death_animations.clear()
        self.victory_animations.clear()

        # Reset ALL wave spawning state variables to initial values
        self.wave_spawning = False
        self.spawn_queue = []
        self.spawn_timer = 0.0
        self.spawn_interval = 0.0
        self.remaining_spawn_interval = 0.0
        self.first_spawn_done = False
        self.spawn_y_position = 350
        self.occupied_regions = []

        # Reset wave transition state
        self.wave_transition = None
        self.pending_wave_num = None

        # Reset slow motion state
        self.slow_motion_active = False
        self.slow_motion_timer = 0.0
        self.current_speed_multiplier = 1.0
        self.target_speed_multiplier = 1.0

        # Reset pending you win state
        self.pending_you_win = False

        # Clear engagement
        self._clear_engagement()

        # Reinitialize game managers
        self.input_tracker = SimultaneousInputTracker()
        self.sequence_generator = SequenceGenerator()
        self.spawning_manager = SpawningManager()

        # Reinitialize effects managers
        # Create laser manager with callback to get waveform Y position
        waveform_y_callback = lambda x: (
            self.player_waveform.get_y_at_x(x) if self.player_waveform else -280
        )
        self.laser_manager = LaserManager(self.view, self.config, None, waveform_y_callback)
        self.explosion_manager = ExplosionManager(self.view, self.config)
        self.shake_manager = ScreenShakeManager(self.view, self.config)

        # Hide config UI during restart
        if self.config_ui:
            self.config_ui.hide_ui()

        self._create_hud()

        # Recreate engagement crosshair (starting off-screen)
        self.engagement_crosshair = EngagementCrosshair(self.view)
        # Start crosshair off-screen (below bottom)
        self.engagement_crosshair.current_pos = (0, -450)
        self.engagement_crosshair.resting_pos = (0, -450)
        self.engagement_crosshair._update_crosshair_position(self.engagement_crosshair.current_pos)

        # Recreate player health waveform (starting off-screen)
        self.player_waveform = PlayerHealthWaveform(self.view, screen_width=800, screen_height=600)
        # Start waveform off-screen (below bottom)
        self.player_waveform.base_y = -450

        # Start wave transition (will animate them into view)
        self._start_wave_transition(1)
        self.state = "playing"

        # Update starfield to playing state
        if self.starfield:
            self.starfield.set_game_state("playing")

        print("Game restarted!")

    def _quit_game(self):
        """Return to the intro screen."""
        self._show_intro()

    def _show_high_scores(self):
        """Show the high score board after game over or you win."""
        if self.game_over_screen:
            self.game_over_screen.cleanup()
            self.game_over_screen = None
        if self.you_win_screen:
            self.you_win_screen.cleanup()
            self.you_win_screen = None

        self.high_score_screen = HighScoreScreen(
            self.view,
            self.config,
            self.score,
            self.wave,
            game_engine=self,
            stats=self.stats,
        )
        self.high_score_screen.on_restart_callback = self._show_intro
        self.state = "high_score"

    def _show_intro(self):
        """Tear down current game state and show the intro screen."""
        if self.game_over_screen:
            self.game_over_screen.cleanup()
            self.game_over_screen = None
        if self.you_win_screen:
            self.you_win_screen.cleanup()
            self.you_win_screen = None
        if self.high_score_screen:
            self.high_score_screen.cleanup()
            self.high_score_screen = None

        self.sound_manager.crossfade_to_background_music(duration=1.0)

        self.state = "intro"
        if self.starfield:
            self.starfield.set_game_state("intro")

        self.intro_screen = IntroScreen(self.view, self.config, game_engine=self)

    def disable_player(self, duration: float = 0.3):
        """Disable player input for a duration (e.g., from shield block).

        Args:
            duration: How long to disable input in seconds.
        """
        self.player_disabled = True
        self.player_disabled_timer = duration
        self.player_disabled_duration = duration

        # Trigger gray flash on waveform
        if self.player_waveform:
            self.player_waveform.trigger_disabled_flash(duration)

        # Play denied sound
        if self.sound_manager:
            self.sound_manager.play_denied_1_sound()
