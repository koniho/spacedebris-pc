"""Death animation classes for enemies."""

import math
from debug_log import debug_print as print
import pyqtgraph as pg
from font_manager import font_manager
from config import get_button_label


class EnemyVictoryDeathAnimation:
    """Victory death animation when enemy is defeated - moves towards blue collection point."""

    def __init__(self, enemy, view):
        """Initialize victory death animation."""
        self.enemy = enemy
        self.view = view
        self.duration = 0.8  # 800ms for smooth collection
        self.elapsed = 0.0
        self.completed = False

        # Blue collection point (top-right area)
        self.collection_point = (300, 250)

        # Store original positions and properties
        self.letter_animations = []
        self.blue_colors = [
            (0, 150, 255),  # Bright blue
            (50, 200, 255),  # Light blue
            (100, 220, 255),  # Cyan blue
            (150, 250, 255),  # Very light blue
            (0, 100, 200),  # Dark blue
        ]

        # Create individual letter animations
        for i, (letter_item, letter) in enumerate(zip(enemy.letter_items, enemy.sequence)):
            original_pos = (letter_item.pos().x(), letter_item.pos().y())

            # Calculate movement towards collection point with slight spread
            base_target = self.collection_point
            spread_x = (i - len(enemy.sequence) / 2) * 15  # Spread letters slightly
            spread_y = (i - len(enemy.sequence) / 2) * 8

            target_pos = (base_target[0] + spread_x, base_target[1] + spread_y)

            animation = {
                "letter_item": letter_item,
                "letter": letter,
                "original_pos": original_pos,
                "target_pos": target_pos,
                "color_index": 0,
                "color_timer": 0.0,
            }
            self.letter_animations.append(animation)

    def update(self, dt: float) -> bool:
        """Update victory animation. Returns True if still active."""
        if self.completed:
            return False

        # Update any remaining enemy animations (ring effects, etc.)
        self.enemy.update_animations(dt)

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Update each letter
        for anim in self.letter_animations:
            # Calculate position with easing towards collection point
            start_x, start_y = anim["original_pos"]
            target_x, target_y = anim["target_pos"]

            # Smooth ease-in-out movement
            eased_progress = 0.5 * (1 - math.cos(progress * math.pi))

            current_x = start_x + (target_x - start_x) * eased_progress
            current_y = start_y + (target_y - start_y) * eased_progress

            # Update position
            anim["letter_item"].setPos(current_x, current_y)

            # Animate blue colors (cycle through blue colors)
            anim["color_timer"] += dt * 12  # Moderate color cycling
            color_index = int(anim["color_timer"]) % len(self.blue_colors)
            blue_color = self.blue_colors[color_index]

            # Set blue color with HTML
            letter = anim["letter"]
            color_hex = f"#{blue_color[0]:02x}{blue_color[1]:02x}{blue_color[2]:02x}"
            anim["letter_item"].setHtml(
                f'<span style="color:{color_hex}">{get_button_label(letter)}</span>'
            )

            # Scale down and fade as approaching collection point
            scale_factor = 1.0 - (progress * 0.7)  # Scale down to 30% of original size
            opacity = 1.0 - (progress * 0.3)  # Fade to 70% opacity

            # Apply scale by adjusting font size
            base_size = 20
            new_size = max(6, int(base_size * scale_factor))
            font = font_manager.get_enemy_letter_font(new_size, bold=True)
            anim["letter_item"].setFont(font)
            anim["letter_item"].setOpacity(opacity)

        # Animate hexagon backgrounds with blue colors and fade
        for i, hexagon in enumerate(self.enemy.letter_backgrounds):
            # Use same blue color as corresponding letter
            anim_index = i % len(self.letter_animations)
            if anim_index < len(self.letter_animations):
                color_timer = self.letter_animations[anim_index]["color_timer"]
                color_index = int(color_timer) % len(self.blue_colors)
                blue_color = self.blue_colors[color_index]

                # Update hexagon colors with blue theme
                opacity_factor = 1.0 - (progress * 0.4)  # Fade out gradually
                blue_pen = pg.mkPen(color=(*blue_color, int(255 * opacity_factor)), width=3)
                blue_brush = pg.mkBrush(*blue_color, int(80 * opacity_factor))

                hexagon.setPen(blue_pen)
                hexagon._fill.setBrush(blue_brush)

            # Fade out opacity
            hexagon.setOpacity(1.0 - (progress * 0.4))
            hexagon._fill.setOpacity(1.0 - (progress * 0.4))

        # Check if main animation complete AND all enemy animations are done
        main_complete = progress >= 1.0
        enemy_anims_done = not self.enemy.has_active_animations()

        if main_complete and enemy_anims_done:
            self.completed = True
            return False

        return True

    def is_completed(self) -> bool:
        """Check if animation is completed."""
        return self.completed


class EnemyFireDeathAnimation:
    """Fire death animation when enemy reaches bottom of screen."""

    def __init__(self, enemy, view):
        """Initialize fire death animation."""
        self.enemy = enemy
        self.view = view
        self.duration = 0.6  # 600ms for more visible animation
        self.elapsed = 0.0
        self.completed = False
        print(f"EnemyFireDeathAnimation initialized for {enemy.sequence}")

        # Store original positions and properties
        self.letter_animations = []
        self.fire_colors = [
            (255, 100, 0),  # Orange-red
            (255, 150, 0),  # Orange
            (255, 200, 0),  # Yellow-orange
            (255, 255, 100),  # Light yellow
            (255, 50, 50),  # Red
        ]

        # Create individual letter animations
        for i, (letter_item, letter) in enumerate(zip(enemy.letter_items, enemy.sequence)):
            original_pos = (letter_item.pos().x(), letter_item.pos().y())

            # Calculate upward movement with slight randomness
            upward_distance = 40 + (i * 5)  # Staggered heights
            horizontal_drift = (i - len(enemy.sequence) / 2) * 8  # Spread outward

            target_pos = (
                original_pos[0] + horizontal_drift,
                original_pos[1] + upward_distance,
            )

            animation = {
                "letter_item": letter_item,
                "letter": letter,
                "original_pos": original_pos,
                "target_pos": target_pos,
                "color_index": 0,
                "color_timer": 0.0,
            }
            self.letter_animations.append(animation)

    def update(self, dt: float) -> bool:
        """Update fire animation. Returns True if still active."""
        if self.completed:
            return False

        # Update any remaining enemy animations (ring effects, etc.)
        self.enemy.update_animations(dt)

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        # Debug output on first frame
        if self.elapsed <= dt:
            print(f"First animation frame - {len(self.letter_animations)} letters to animate")

        # Update each letter
        for anim in self.letter_animations:
            # Calculate position with easing
            start_x, start_y = anim["original_pos"]
            target_x, target_y = anim["target_pos"]

            # Ease out for upward movement
            eased_progress = 1 - (1 - progress) ** 3

            current_x = start_x + (target_x - start_x) * eased_progress
            current_y = start_y + (target_y - start_y) * eased_progress

            # Update position
            anim["letter_item"].setPos(current_x, current_y)

            # Animate fire colors (cycle through fire colors rapidly)
            anim["color_timer"] += dt * 20  # Fast color cycling
            color_index = int(anim["color_timer"]) % len(self.fire_colors)
            fire_color = self.fire_colors[color_index]

            # Set fire color with HTML
            letter = anim["letter"]
            color_hex = f"#{fire_color[0]:02x}{fire_color[1]:02x}{fire_color[2]:02x}"
            anim["letter_item"].setHtml(
                f'<span style="color:{color_hex}">{get_button_label(letter)}</span>'
            )

            # Fade out opacity
            opacity = 1.0 - progress
            anim["letter_item"].setOpacity(opacity)

        # Animate hexagon backgrounds with fire colors and fade out
        for i, hexagon in enumerate(self.enemy.letter_backgrounds):
            # Use same fire color as corresponding letter
            anim_index = i % len(self.letter_animations)
            if anim_index < len(self.letter_animations):
                color_timer = self.letter_animations[anim_index]["color_timer"]
                color_index = int(color_timer) % len(self.fire_colors)
                fire_color = self.fire_colors[color_index]

                # Update hexagon colors
                fire_pen = pg.mkPen(color=(*fire_color, int(255 * (1.0 - progress))), width=3)
                fire_brush = pg.mkBrush(*fire_color, int(80 * (1.0 - progress)))

                hexagon.setPen(fire_pen)
                hexagon._fill.setBrush(fire_brush)

            # Fade out opacity
            hexagon.setOpacity(1.0 - progress)
            hexagon._fill.setOpacity(1.0 - progress)

        # Check if main animation complete AND all enemy animations are done
        main_complete = progress >= 1.0
        enemy_anims_done = not self.enemy.has_active_animations()

        if main_complete and enemy_anims_done:
            self.completed = True
            return False

        return True

    def is_completed(self) -> bool:
        """Check if animation is completed."""
        return self.completed
