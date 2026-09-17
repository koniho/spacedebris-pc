# enemies/projectile_enemy.py

from typing import Tuple
from enemies.enemy import Enemy


class ProjectileEnemy(Enemy):
    """An enemy that can move in any direction with custom velocity."""

    def __init__(self, sequence, pos, view, laser_manager=None, waveform=None, velocity=(0, -100)):
        super().__init__(sequence, pos, view, laser_manager, waveform)
        self.velocity = velocity  # (vx, vy) tuple

    def update(self, dt: float):
        """Update enemy position using custom velocity."""
        # Move all letters and backgrounds using velocity with speed multiplier
        for letter_item, hexagon_bg in zip(self.letter_items, self.letter_backgrounds):
            pos = letter_item.pos()
            new_x = pos.x() + self.velocity[0] * self.speed_multiplier * dt
            new_y = pos.y() + self.velocity[1] * self.speed_multiplier * dt
            letter_item.setPos(new_x, new_y)
            # Move hexagon background
            self._move_hexagon(hexagon_bg, new_x, new_y)

        # Update animations
        completed_animations = []
        for animation in self.animations:
            if not animation.update(dt):
                completed_animations.append(animation)

        # Remove completed animations
        for animation in completed_animations:
            self.animations.remove(animation)
