"""Base enemy class for all enemy types."""

from abc import ABC, abstractmethod
from typing import Tuple


class BaseEnemy(ABC):
    """Abstract base class for all enemy types."""

    @abstractmethod
    def __init__(self, view, laser_manager=None, waveform=None):
        """Initialize base enemy properties."""
        self.view = view
        self.laser_manager = laser_manager
        self.waveform = waveform
        self.speed_multiplier = 1.0
        self.completed = False

    @abstractmethod
    def type_button(self, button: str) -> bool:
        """Try to type a button. Returns True if successful."""

    @abstractmethod
    def can_type_button(self, button: str) -> bool:
        """Check if this button can be typed on this enemy."""

    @abstractmethod
    def reset_typing_progress(self):
        """Reset typing progress to the beginning."""

    @abstractmethod
    def update(self, dt: float):
        """Update enemy position and animations."""

    @abstractmethod
    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of enemy."""

    @abstractmethod
    def get_width(self) -> float:
        """Get total width of enemy including spacing."""

    @abstractmethod
    def is_complete(self) -> bool:
        """Check if enemy is completely typed."""

    @abstractmethod
    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if enemy has moved below screen."""

    @abstractmethod
    def cleanup(self):
        """Remove all visual elements."""

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box of enemy (left, right, top, bottom).
        Default implementation - can be overridden by subclasses.
        """
        center_x, center_y = self.get_center_position()
        width = self.get_width()
        padding = 20

        left = center_x - width / 2 - padding
        right = center_x + width / 2 + padding
        top = center_y + padding
        bottom = center_y - padding

        return (left, right, top, bottom)

    def set_speed_multiplier(self, multiplier: float):
        """Set speed multiplier for slow motion effects."""
        self.speed_multiplier = multiplier

    def set_config_speed_multiplier(self, multiplier: float):
        """Set base speed based on config multiplier."""
        # This would need to be implemented in concrete classes
        # since speed calculation differs between enemy types

    def get_destruction_info(self):
        """Get information needed for destruction handling.

        Returns:
            dict: Dictionary containing:
                - points: int - Base points for destroying this enemy
                - explosion_type: str - Type of explosion effect
                - explosion_scale: float - Scale multiplier for explosion
                - shake_type: str - Type of screen shake to trigger
        """
        # Default implementation for basic enemies
        sequence = getattr(self, "sequence", "")
        return {
            "points": len(sequence) * 10,
            "explosion_type": "normal",
            "explosion_scale": 1.0,
            "shake_type": "enemy_destroyed",
        }

    def get_miss_info(self):
        """Get information needed for miss/collision handling.

        Returns:
            dict: Dictionary containing:
                - damage: float - Damage to deal to player (0.0 to 1.0)
                - enemy_type_name: str - Display name for logging
        """
        return {
            "damage": 0.25,
            "enemy_type_name": "Enemy",
        }  # 25% damage (4 hits to lose)

    def handle_destruction(self, game_engine):
        """Handle this enemy being destroyed with consistent engagement management.

        Args:
            game_engine: Reference to the game engine for engagement management
        """
        # Clear engagement if this enemy was engaged
        if game_engine.engaged_enemy == self:
            game_engine._clear_engagement()

        # Call the standard destruction handler
        game_engine._on_enemy_destroyed(self)

    def handle_miss(self, game_engine):
        """Handle this enemy missing/colliding with consistent engagement management.

        Args:
            game_engine: Reference to the game engine for engagement management
        """
        # Clear engagement if this enemy was engaged
        if game_engine.engaged_enemy == self:
            game_engine._clear_engagement()

        # Call the standard miss handler
        game_engine._on_enemy_missed(self)

    def create_victory_animations(self):
        """Create victory animations for this enemy.

        Returns:
            List of victory animation objects
        """
        # Default implementation for single enemies
        from enemies.animations import EnemyVictoryDeathAnimation

        victory_animation = EnemyVictoryDeathAnimation(self, self.view)
        return [victory_animation]

    def create_death_animations(self):
        """Create death animations for when this enemy hits the player.

        Subclasses can override to handle cleanup of special visuals
        before creating death animations.

        Returns:
            List of death animation objects
        """
        from enemies.animations import EnemyFireDeathAnimation

        death_animation = EnemyFireDeathAnimation(self, self.view)
        return [death_animation]

    def would_block_attack(self, _button: str) -> bool:
        """Check if this enemy would block an attack with the given button.

        Returns True if the attack should be blocked (e.g., by a shield).
        Subclasses should override this if they have blocking behavior.
        """
        return False

    def handle_blocked_attack(self, game_engine):
        """Handle a blocked attack.

        Called when would_block_attack returns True.
        Subclasses should override this if they have blocking behavior.
        """

    def has_active_animations(self) -> bool:
        """Check if enemy has active animations that need to complete.

        Subclasses should override this if they have animations.
        """
        return False

    def update_animations(self, dt: float):
        """Update any remaining animations owned by this enemy.

        Subclasses should override this if they have animations.
        """
