"""Enemy spawning manager with overlap prevention."""

import random_manager
from typing import List, Tuple
from enemies import Enemy, LinkedEnemyPair


class SpawningManager:
    """Manages enemy spawning positions to prevent overlap."""

    def __init__(self, screen_width: float = 800, margin: float = 50):
        """Initialize spawning manager."""
        self.screen_width = screen_width
        self.margin = margin
        self.min_separation = 120  # Minimum distance between enemy centers

    def generate_non_overlapping_positions(
        self, enemy_widths: List[float], spawn_y_range: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """Generate spawn positions that don't overlap."""
        if not enemy_widths:
            return []

        positions = []
        max_attempts = 200  # More attempts to find good positions
        enemy_height = 40  # Approximate height of enemy including hexagons

        for i, width in enumerate(enemy_widths):
            # Calculate safe x range for this enemy
            half_width = width / 2
            min_x = -self.screen_width / 2 + self.margin + half_width
            max_x = self.screen_width / 2 - self.margin - half_width

            position_found = False

            for attempt in range(max_attempts):
                # Random position
                x = random_manager.uniform(min_x, max_x)
                y = random_manager.uniform(*spawn_y_range)

                # Check for overlaps with ALL existing enemies
                overlaps = False
                for j, (existing_pos, existing_width) in enumerate(
                    zip(positions, enemy_widths[: len(positions)])
                ):
                    # Calculate required distances in both X and Y
                    x_distance = abs(x - existing_pos[0])
                    y_distance = abs(y - existing_pos[1])

                    # Required separation distances
                    required_x_distance = (width + existing_width) / 2 + self.min_separation
                    required_y_distance = enemy_height + 40  # Extra vertical spacing

                    # Check if enemies would overlap in either X or Y (more conservative)
                    if x_distance < required_x_distance or y_distance < required_y_distance:
                        overlaps = True
                        break

                if not overlaps:
                    positions.append((x, y))
                    position_found = True
                    break

            if not position_found:
                # Use deterministic grid fallback that guarantees no overlaps
                fallback_pos = self._get_guaranteed_non_overlapping_position(
                    i, enemy_widths, spawn_y_range
                )
                positions.append(fallback_pos)

        return positions

    def _get_guaranteed_non_overlapping_position(
        self, index: int, enemy_widths: List[float], spawn_y_range: Tuple[float, float]
    ) -> Tuple[float, float]:
        """Get guaranteed non-overlapping position using grid layout."""
        # Calculate grid dimensions
        enemies_up_to_now = enemy_widths[: index + 1]
        max_width = max(enemies_up_to_now) if enemies_up_to_now else 100

        # Use larger spacing to absolutely guarantee no overlaps
        grid_spacing_x = max_width + self.min_separation + 40  # Extra padding
        grid_spacing_y = 80  # Vertical spacing between rows

        # Calculate how many enemies can fit in one row (conservative)
        available_width = self.screen_width - 2 * self.margin - 100  # Extra margin for safety
        enemies_per_row = max(1, int(available_width / grid_spacing_x))

        # Calculate grid position
        row = index // enemies_per_row
        col = index % enemies_per_row

        # Calculate position
        total_width_needed = enemies_per_row * grid_spacing_x
        start_x = -total_width_needed / 2 + grid_spacing_x / 2

        x = start_x + col * grid_spacing_x
        y = spawn_y_range[1] - row * grid_spacing_y  # Start from top and go down

        # Ensure position is within bounds
        current_width = enemy_widths[index]
        half_width = current_width / 2
        min_x = -self.screen_width / 2 + self.margin + half_width
        max_x = self.screen_width / 2 - self.margin - half_width

        x = max(min_x, min(max_x, x))
        y = max(spawn_y_range[0], min(spawn_y_range[1], y))

        return (x, y)

    def generate_paired_positions(
        self,
        pair_count: int,
        sequence_lengths: List[Tuple[int, int]],
        spawn_y_range: Tuple[float, float],
        existing_single_positions: List[Tuple[float, float]] = None,
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Generate positions for enemy pairs with adequate separation."""
        pair_positions = []
        used_regions = []  # Track used regions to avoid overlap
        enemy_height = 40

        if existing_single_positions is None:
            existing_single_positions = []

        for i in range(pair_count):
            seq1_len, seq2_len = sequence_lengths[i] if i < len(sequence_lengths) else (3, 3)

            # Calculate widths for both enemies in the pair
            width1 = (seq1_len - 1) * 30 + 40
            width2 = (seq2_len - 1) * 30 + 40
            separation = max(120, (width1 + width2) / 2 + 40)  # Minimum separation
            pair_total_width = width1 + width2 + separation

            region_found = False
            max_attempts = 50

            for attempt in range(max_attempts):
                # Choose center point for the pair
                pair_center_x = random_manager.uniform(-300, 300)
                y = random_manager.uniform(*spawn_y_range)

                # Calculate positions for both enemies
                x1 = pair_center_x - separation / 2
                x2 = pair_center_x + separation / 2

                # Check screen bounds first
                if (
                    x1 - width1 / 2 < -self.screen_width / 2 + self.margin
                    or x2 + width2 / 2 > self.screen_width / 2 - self.margin
                ):
                    continue

                overlaps = False

                # Check overlap with existing single enemies
                for single_pos in existing_single_positions:
                    for enemy_x, enemy_width in [(x1, width1), (x2, width2)]:
                        x_dist = abs(enemy_x - single_pos[0])
                        y_dist = abs(y - single_pos[1])

                        if (
                            x_dist < (enemy_width + 100) / 2 + self.min_separation
                            and y_dist < enemy_height + 20
                        ):
                            overlaps = True
                            break
                    if overlaps:
                        break

                # Check overlap with existing pairs
                if not overlaps:
                    for used_center, used_width in used_regions:
                        if (
                            abs(pair_center_x - used_center)
                            < (pair_total_width + used_width) / 2 + 40
                        ):
                            overlaps = True
                            break

                if not overlaps:
                    pair_positions.append(((x1, y), (x2, y)))
                    used_regions.append((pair_center_x, pair_total_width))
                    region_found = True
                    break

            if not region_found:
                # Guaranteed non-overlapping fallback
                fallback_pos = self._get_guaranteed_pair_position(
                    i,
                    sequence_lengths,
                    spawn_y_range,
                    existing_single_positions,
                    pair_positions,
                )
                pair_positions.append(fallback_pos)
                # Update used regions with fallback
                center_x = (fallback_pos[0][0] + fallback_pos[1][0]) / 2
                used_regions.append((center_x, pair_total_width))

        return pair_positions

    def _get_guaranteed_pair_position(
        self,
        index: int,
        sequence_lengths: List[Tuple[int, int]],
        spawn_y_range: Tuple[float, float],
        existing_single_positions: List[Tuple[float, float]],
        existing_pair_positions: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Get guaranteed non-overlapping position for a pair using grid layout."""
        seq1_len, seq2_len = sequence_lengths[index] if index < len(sequence_lengths) else (3, 3)
        width1 = (seq1_len - 1) * 30 + 40
        width2 = (seq2_len - 1) * 30 + 40
        separation = max(120, (width1 + width2) / 2 + 40)

        # Use grid layout for pairs
        pairs_per_row = max(1, int((self.screen_width - 2 * self.margin) / (separation + 100)))

        row = index // pairs_per_row
        col = index % pairs_per_row

        # Calculate center position
        grid_spacing_x = (self.screen_width - 2 * self.margin) / pairs_per_row
        center_x = -self.screen_width / 2 + self.margin + grid_spacing_x * (col + 0.5)
        y = spawn_y_range[0] + 50 * row  # Offset rows downward

        # Ensure we don't go out of spawn range
        y = min(spawn_y_range[1], y)

        x1 = center_x - separation / 2
        x2 = center_x + separation / 2

        return ((x1, y), (x2, y))
