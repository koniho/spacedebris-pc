"""Base class for all boss enemies."""

from abc import abstractmethod
from typing import Tuple
from enemies.base_enemy import BaseEnemy


class BaseBoss(BaseEnemy):
    """Base class for all boss enemies with common boss functionality."""

    def __init__(self, view, laser_manager=None, waveform=None):
        """Initialize base boss."""
        super().__init__(view, laser_manager, waveform)
        self.is_boss = True  # Mark this as a boss enemy

    def on_unmatched_input(self, key: str) -> bool:
        """Called by engine when input doesn't match any enemy.

        Override to handle wrong key presses (e.g., spawn punishment projectiles).
        Returns True if boss handled/punished the input, False otherwise.
        """
        return False

    @abstractmethod
    def get_boss_radius(self) -> float:
        """Get the radius of the boss for death animations.

        Returns:
            float: The radius to use for death animation effects
        """
        pass

    def handle_destruction(self, game_engine):
        """Handle boss destruction with common boss death behavior."""
        # Add points for boss destruction
        destruction_info = self.get_destruction_info()
        game_engine.score += destruction_info["points"]

        # Create victory animations
        animations = self.create_victory_animations()

        # Set up explosion callbacks for boss death animations
        for anim in animations:
            if hasattr(anim, "is_boss") and anim.is_boss:
                # Create staggered explosions during boss death
                import random_manager
                import math
                from config import ALL_BUTTONS, get_button_color

                explosion_count = [0]  # Use list to allow modification in closure
                explosion_types = ["normal", "enhanced", "critical"]

                def spawn_boss_explosion():
                    # Generate random position around boss
                    angle = random_manager.uniform(0, 2 * 3.14159)
                    radius = random_manager.uniform(0, anim.boss_radius * 1.5)
                    x_offset = radius * math.cos(angle)
                    y_offset = radius * math.sin(angle)
                    explosion_pos = (
                        anim.center_pos[0] + x_offset,
                        anim.center_pos[1] + y_offset,
                    )

                    # Cycle through explosion types
                    explosion_type = explosion_types[explosion_count[0] % len(explosion_types)]
                    explosion_count[0] += 1

                    # Use a random button for color
                    button = random_manager.choice(ALL_BUTTONS)

                    # Create the explosion
                    if game_engine.explosion_manager:
                        game_engine.explosion_manager.create_explosion(
                            explosion_pos,
                            get_button_color(button),
                            explosion_type,
                            1.5,  # Larger scale for boss
                        )
                        # Quick starfield flash with each explosion
                        if game_engine.starfield:
                            game_engine.starfield.start_flash(0.05)
                        # Play explosion sound
                        game_engine.sound_manager.play_explosion_sound()
                        # Trigger screen shake
                        if game_engine.shake_manager:
                            if explosion_type == "critical":
                                game_engine.shake_manager.large_shake()
                            else:
                                game_engine.shake_manager.medium_shake()

                anim.explosion_callback = spawn_boss_explosion

                # Set up screen shake callback
                def trigger_boss_shake():
                    if game_engine.shake_manager:
                        # Alternate between medium and large shakes for variety
                        if random_manager.random() > 0.3:
                            game_engine.shake_manager.medium_shake()
                        else:
                            game_engine.shake_manager.large_shake()

                anim.shake_callback = trigger_boss_shake

                def trigger_finale_effects(progress):
                    """Intensifying flashes and shakes near the end of death animation."""
                    if game_engine.starfield:
                        flash_duration = 0.05 + progress * 0.1
                        game_engine.starfield.start_flash(flash_duration)
                    if game_engine.shake_manager:
                        magnitude = 5 + progress * 15
                        game_engine.shake_manager.trigger_shake(
                            magnitude=magnitude, duration=0.15
                        )
                    game_engine.sound_manager.play_explosion_sound(
                        volume=0.1 + progress * 0.2
                    )

                anim.finale_callback = trigger_finale_effects

        for animation in animations:
            game_engine.victory_animations.append(animation)

        # Trigger screen shake for boss death
        if game_engine.shake_manager:
            shake_type = destruction_info.get("shake_type", "massive")
            if shake_type == "massive":
                # Trigger multiple large shakes for boss death
                game_engine.shake_manager.large_shake()
            elif shake_type == "large":
                game_engine.shake_manager.large_shake()
            elif shake_type == "medium":
                game_engine.shake_manager.medium_shake()
            else:
                game_engine.shake_manager.enemy_destroyed_shake()

        # Trigger starfield flash for boss death
        if game_engine.starfield:
            game_engine.starfield.start_flash(0.1)

        # Trigger slow motion for boss death
        game_engine.animation_speed = 0.15  # Dramatic slow motion
        game_engine.boss_death_timer = 3.0  # Return to normal after 3 seconds

        # Remove boss from enemies list
        if self in game_engine.enemies:
            game_engine.enemies.remove(self)

        # Trigger destruction sequence for all boss projectiles
        # They will animate and be removed through normal destruction flow
        if hasattr(self, "projectiles"):
            for projectile in self.projectiles[:]:
                if projectile in game_engine.enemies:
                    # Trigger the projectile's destruction sequence
                    projectile.handle_destruction(game_engine)

        # Clean up boss visuals (but projectiles handle their own cleanup)
        self.cleanup()

        # Mark wave as complete for boss waves
        if game_engine.spawning_manager:
            game_engine.spawning_manager.boss_spawned = False
            game_engine.spawning_manager.wave_complete = True

    def handle_miss(self, game_engine):
        """Handle when boss reaches the player."""
        # Default implementation - bosses typically don't move toward player
        pass

    def create_victory_animations(self):
        """Create victory animations for boss defeat."""
        from effects.boss_death_animation import BossDeathAnimation

        animation = BossDeathAnimation(self, self.view)
        animation.is_boss = True
        return [animation]

    def get_destruction_info(self):
        """Get destruction info for boss."""
        return {
            "points": 1000,
            "explosion_type": "mega",
            "explosion_scale": 3.0,
            "shake_type": "massive",
        }
