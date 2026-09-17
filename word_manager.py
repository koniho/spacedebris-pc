"""Word sequence generation and management."""

import random_manager
from typing import Tuple, List
from config import (
    LEFT_HAND_BUTTONS,
    RIGHT_HAND_BUTTONS,
    ALL_BUTTONS,
    buttons_are_opposite_hands,
)


class SequenceGenerator:
    """Generates typing sequences for enemies."""

    def __init__(self):
        """Initialize sequence generator."""
        self.left_buttons = LEFT_HAND_BUTTONS
        self.right_buttons = RIGHT_HAND_BUTTONS
        self.all_buttons = ALL_BUTTONS

    def generate_single_sequence(self, length: int, difficulty: int) -> str:
        """Generate a single-hand or mixed sequence."""
        if length < 1:
            return ""

        # Choose hand or mixed based on difficulty
        if difficulty < 2:
            # Easy: single hand sequences
            hand = random_manager.choice(["left", "right"])
            buttons = self.left_buttons if hand == "left" else self.right_buttons
        else:
            # Medium+: allow mixed sequences
            if random_manager.random() < 0.3:  # 30% chance for single hand
                hand = random_manager.choice(["left", "right"])
                buttons = self.left_buttons if hand == "left" else self.right_buttons
            else:
                buttons = self.all_buttons

        sequence = []
        for _ in range(length):
            if difficulty < 3:
                # Allow repeats for easier sequences
                button = random_manager.choice(buttons)
            else:
                # Prefer variety - avoid consecutive same button
                if sequence and len(set(buttons)) > 1:
                    available = [b for b in buttons if b != sequence[-1]]
                    button = (
                        random_manager.choice(available)
                        if available
                        else random_manager.choice(buttons)
                    )
                else:
                    button = random_manager.choice(buttons)

            sequence.append(button)

        return "".join(sequence)

    def generate_rapid_hit_sequence(self, length: int, difficulty: int) -> str:
        """Generate a sequence for rapid-hit enemies with no adjacent duplicates."""
        if length < 1:
            return ""

        # Choose button set based on difficulty
        if difficulty < 2:
            # Easy: single hand sequences
            hand = random_manager.choice(["left", "right"])
            buttons = self.left_buttons if hand == "left" else self.right_buttons
        else:
            # Medium+: allow mixed sequences
            if random_manager.random() < 0.3:  # 30% chance for single hand
                hand = random_manager.choice(["left", "right"])
                buttons = self.left_buttons if hand == "left" else self.right_buttons
            else:
                buttons = self.all_buttons

        # Always prevent adjacent duplicates for rapid-hit enemies
        sequence = []
        for _ in range(length):
            if sequence and len(set(buttons)) > 1:
                # Ensure no adjacent duplicates
                available = [b for b in buttons if b != sequence[-1]]
                button = (
                    random_manager.choice(available)
                    if available
                    else random_manager.choice(buttons)
                )
            else:
                button = random_manager.choice(buttons)
            sequence.append(button)

        return "".join(sequence)

    def generate_paired_sequences(self, length: int, _difficulty: int) -> Tuple[str, str]:
        """Generate two sequences that can be typed simultaneously.

        Left enemy (seq1) uses only left-hand buttons.
        Right enemy (seq2) uses only right-hand buttons.
        Ensures no adjacent repeated button pairs.
        """
        if length < 1:
            return "", ""

        seq1 = []  # Left enemy - left hand buttons only
        seq2 = []  # Right enemy - right hand buttons only
        last_pair = None  # Track the last used pair to avoid adjacent duplicates

        for _ in range(length):
            attempts = 0
            max_attempts = 50  # Prevent infinite loop

            while attempts < max_attempts:
                # Left enemy gets a left-hand button
                left_button = random_manager.choice(self.left_buttons)
                # Right enemy gets a right-hand button
                right_button = random_manager.choice(self.right_buttons)

                # Create pair tuple for tracking
                pair = (left_button, right_button)

                # Check if this pair is different from the last one (no adjacent duplicates)
                if pair != last_pair:
                    seq1.append(left_button)
                    seq2.append(right_button)
                    last_pair = pair
                    break

                attempts += 1

            # Fallback if we can't find a different pair
            if attempts >= max_attempts:
                # Force a different combination by cycling through options
                left_button = random_manager.choice(
                    [b for b in self.left_buttons if b != (last_pair[0] if last_pair else None)]
                )
                right_button = random_manager.choice(
                    [b for b in self.right_buttons if b != (last_pair[1] if last_pair else None)]
                )
                seq1.append(left_button)
                seq2.append(right_button)
                last_pair = (left_button, right_button)

        return "".join(seq1), "".join(seq2)

    def validate_pair(self, seq1: str, seq2: str) -> bool:
        """Validate that two sequences can be typed simultaneously.

        Ensures:
        - seq1 (left enemy) only contains left-hand buttons
        - seq2 (right enemy) only contains right-hand buttons
        - No duplicate buttons at same position
        - Buttons at each position are from opposite hands
        """
        if len(seq1) != len(seq2):
            return False

        # Check that seq1 only has left-hand buttons
        for button in seq1:
            if button not in self.left_buttons:
                return False

        # Check that seq2 only has right-hand buttons
        for button in seq2:
            if button not in self.right_buttons:
                return False

        for button1, button2 in zip(seq1, seq2):
            # Check that buttons are from opposite hands (redundant but kept for safety)
            if not buttons_are_opposite_hands(button1, button2):
                return False

            # Check no duplicate letters at same position
            if button1 == button2:
                return False

        return True

    def generate_word_list(
        self, count: int, min_length: int = 3, max_length: int = 6, difficulty: int = 1
    ) -> List[str]:
        """Generate a list of single sequences."""
        sequences = []
        for i in range(count):
            # Last enemy gets longer words (7+ characters) if max_length allows it
            if i == count - 1 and max_length > 6:
                # Final enemy: use longer sequences (7 to max_length+2)
                final_min = max(7, min_length)
                final_max = min(max_length + 2, 12)  # Cap at 12 chars
                length = random_manager.randint(final_min, final_max)
            else:
                # Regular enemies: use normal length but cap at 6
                regular_max = min(max_length, 6)
                length = random_manager.randint(min_length, regular_max)

            sequence = self.generate_single_sequence(length, difficulty)
            sequences.append(sequence)
        return sequences

    def generate_rapid_hit_word_list(
        self, count: int, min_length: int = 2, max_length: int = 3, difficulty: int = 1
    ) -> List[str]:
        """Generate a list of rapid-hit sequences with no adjacent duplicates."""
        sequences = []
        for _ in range(count):
            length = random_manager.randint(min_length, max_length)
            sequence = self.generate_rapid_hit_sequence(length, difficulty)
            sequences.append(sequence)
        return sequences

    def generate_paired_word_list(
        self, count: int, min_length: int = 3, max_length: int = 5, difficulty: int = 3
    ) -> List[Tuple[str, str]]:
        """Generate a list of paired sequences."""
        pairs = []
        for _ in range(count):
            length = random_manager.randint(min_length, max_length)
            seq1, seq2 = self.generate_paired_sequences(length, difficulty)
            if self.validate_pair(seq1, seq2):
                pairs.append((seq1, seq2))
            else:
                # Retry once if validation fails
                seq1, seq2 = self.generate_paired_sequences(length, difficulty)
                pairs.append((seq1, seq2))
        return pairs


def get_sequence_difficulty_score(sequence: str) -> int:
    """Calculate difficulty score for a sequence."""
    if not sequence:
        return 0

    score = len(sequence)

    # Add difficulty for hand switches
    hand_switches = 0
    for i in range(1, len(sequence)):
        prev_hand = "left" if sequence[i - 1] in LEFT_HAND_BUTTONS else "right"
        curr_hand = "left" if sequence[i] in LEFT_HAND_BUTTONS else "right"
        if prev_hand != curr_hand:
            hand_switches += 1

    score += hand_switches

    # Add difficulty for finger complexity
    finger_positions = {
        "S": 1,
        "D": 2,
        "F": 3,  # Left hand positions
        "J": 3,
        "K": 2,
        "L": 1,  # Right hand positions (mirrored)
    }

    finger_jumps = 0
    for i in range(1, len(sequence)):
        prev_pos = finger_positions.get(sequence[i - 1], 2)
        curr_pos = finger_positions.get(sequence[i], 2)
        finger_jumps += abs(prev_pos - curr_pos)

    score += finger_jumps // 2

    return score
