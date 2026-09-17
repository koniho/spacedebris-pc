"""Game configuration and settings management."""

import json
import os
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class DifficultyLevel(Enum):
    """Game difficulty levels."""

    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


# Difficulty presets: speed_multiplier, enemy_count_multiplier, damage_multiplier
# EASY is 25% of HARD, NORMAL is 50%, HARD is 100%
DIFFICULTY_PRESETS = {
    DifficultyLevel.EASY: {
        "speed_multiplier": 0.25,  # 25% of HARD
        "enemy_count_multiplier": 0.25,
        "damage_multiplier": 0.25,
        "max_word_length_offset": -3,  # Shorter words
        "rapid_hit_max_count": 3,  # Max hits per letter for rapid hit enemies
        "boss_punishment_projectiles": 1,  # Projectiles for no-action punishment
        "chaotic_cloud_attack_interval_multiplier": 1.5,  # 50% slower projectiles
    },
    DifficultyLevel.NORMAL: {
        "speed_multiplier": 0.5,  # 50% of HARD
        "enemy_count_multiplier": 0.7,
        "damage_multiplier": 0.5,
        "max_word_length_offset": -2,
        "rapid_hit_max_count": 5,
        "boss_punishment_projectiles": 2,
        "chaotic_cloud_attack_interval_multiplier": 1.25,  # 25% slower projectiles
    },
    DifficultyLevel.HARD: {
        "speed_multiplier": 0.7,  # Full speed
        "enemy_count_multiplier": 1.0,
        "damage_multiplier": 0.5,  # Full damage
        "max_word_length_offset": 0,  # Full word length
        "rapid_hit_max_count": 6,
        "boss_punishment_projectiles": 3,
        "chaotic_cloud_attack_interval_multiplier": 1.0,
    },
}


# Button configuration
LEFT_HAND_BUTTONS = ["S", "D", "F"]
# LEFT_HAND_BUTTONS = ["S", "D"]
RIGHT_HAND_BUTTONS = ["J", "K", "L"]
# LEFT_HAND_BUTTONS = ["F"]
# RIGHT_HAND_BUTTONS = ["J"]
ALL_BUTTONS = LEFT_HAND_BUTTONS + RIGHT_HAND_BUTTONS

# Button colors
BUTTON_COLORS = {
    "S": "#FF4444",  # Red
    "D": "#44FF44",  # Green
    "F": "#4444FF",  # Blue
    "J": "#FFAA44",  # Orange
    "K": "#AA44FF",  # Purple
    "L": "#44FFFF",  # Cyan
}

# Button display labels (for custom key mappings)
# If a button is not in this dict, the button letter itself is used
# BUTTON_LABELS: Dict[str, str] = {"S": "L1", "D": "L2", "F": "L3", "J": "R3", "K": "R2", "L": "R1"}
BUTTON_LABELS: Dict[str, str] = {}
# BUTTON_LABELS: Dict[str, str] = {"S": "L1", "D": "L2", "J": "R3", "K": "R2", "L": "R1"}


@dataclass
class SpawningConfig:
    """Configuration for enemy spawning."""

    # Enemy type ratios (will be normalized)
    normal_enemy_ratio: float = 1.0
    rapid_hit_enemy_ratio: float = 0.5
    pair_enemy_ratio: float = 0.4
    reverse_enemy_ratio: float = 0.3
    shielded_enemy_ratio: float = 0.2

    # Override ratios for testing (set to -1 to use normal ratios)
    test_normal_ratio: float = -1
    test_rapid_hit_ratio: float = -1
    test_pair_ratio: float = -1
    test_reverse_ratio: float = -1
    test_shielded_ratio: float = -1

    # Single enemy type testing (empty string = normal spawning)
    # Valid values: "", "normal", "rapid_hit", "pair", "reverse", "shielded"
    test_enemy_type: str = ""

    # Wave progression settings
    enable_wave_progression: bool = True
    force_wave_number: int = -1  # -1 = normal progression, >0 = force specific wave

    # Gameplay modifiers for testing
    infinite_health: bool = False
    speed_override_enabled: bool = False  # Whether to use speed_multiplier override
    speed_multiplier: float = 1.0  # Override speed multiplier (applied on top of difficulty)
    boss_every_wave: bool = False  # Spawn boss on every wave for testing
    test_phase_shift_boss: bool = False  # Only spawn phase shift boss for testing
    test_force_field_boss: bool = False  # Only spawn force field boss for testing
    test_sinusoid_boss: bool = False  # Only spawn sinusoid boss for testing
    test_chaotic_cloud_boss: bool = False  # Only spawn chaotic cloud boss for testing
    test_face_boss: bool = False  # Only spawn face boss for testing

    # Difficulty settings (applied from DifficultyLevel presets)
    current_difficulty: str = "hard"  # Current difficulty level name
    enemy_count_multiplier: float = 1.0  # Multiplier for enemy count per wave
    damage_multiplier: float = 1.0  # Multiplier for damage taken
    max_word_length_offset: int = 0  # Offset for max word length
    rapid_hit_max_count: int = 6  # Max hits per letter for rapid hit enemies
    boss_punishment_projectiles: int = 4  # Projectiles for boss no-action punishment
    chaotic_cloud_attack_interval_multiplier: float = 1.0  # Multiplier for attack intervals

    def save_to_file(self, filepath: str):
        """Save configuration to JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "SpawningConfig":
        """Load configuration from JSON file."""
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                return cls(**data)
        return cls()

    def get_active_ratios(self) -> tuple[float, float, float, float, float]:
        """Get the currently active ratios (test overrides if set, otherwise normal).

        Returns:
            Tuple of (normal, rapid_hit, pair, reverse, shielded) ratios.
        """
        # Check if single enemy type testing is enabled
        if self.test_enemy_type:
            type_ratios = {
                "normal": (1.0, 0.0, 0.0, 0.0, 0.0),
                "rapid_hit": (0.0, 1.0, 0.0, 0.0, 0.0),
                "pair": (0.0, 0.0, 1.0, 0.0, 0.0),
                "reverse": (0.0, 0.0, 0.0, 1.0, 0.0),
                "shielded": (0.0, 0.0, 0.0, 0.0, 1.0),
            }
            if self.test_enemy_type in type_ratios:
                return type_ratios[self.test_enemy_type]

        # Check if all test ratios are set (legacy support)
        all_test_set = (
            self.test_normal_ratio >= 0
            and self.test_rapid_hit_ratio >= 0
            and self.test_pair_ratio >= 0
            and self.test_reverse_ratio >= 0
            and self.test_shielded_ratio >= 0
        )
        if all_test_set:
            return (
                self.test_normal_ratio,
                self.test_rapid_hit_ratio,
                self.test_pair_ratio,
                self.test_reverse_ratio,
                self.test_shielded_ratio,
            )
        return (
            self.normal_enemy_ratio,
            self.rapid_hit_enemy_ratio,
            self.pair_enemy_ratio,
            self.reverse_enemy_ratio,
            self.shielded_enemy_ratio,
        )

    def apply_difficulty(self, difficulty: DifficultyLevel):
        """Apply difficulty preset settings."""
        preset = DIFFICULTY_PRESETS[difficulty]
        self.current_difficulty = difficulty.value
        # Note: speed_multiplier is now an override, not set by difficulty
        self.enemy_count_multiplier = preset["enemy_count_multiplier"]
        self.damage_multiplier = preset["damage_multiplier"]
        self.max_word_length_offset = preset["max_word_length_offset"]
        self.rapid_hit_max_count = preset["rapid_hit_max_count"]
        self.boss_punishment_projectiles = preset["boss_punishment_projectiles"]
        self.chaotic_cloud_attack_interval_multiplier = preset[
            "chaotic_cloud_attack_interval_multiplier"
        ]

    def get_difficulty_level(self) -> DifficultyLevel:
        """Get the current difficulty level as an enum."""
        return DifficultyLevel(self.current_difficulty)

    def get_effective_speed_multiplier(self) -> float:
        """Get the effective speed multiplier combining difficulty and override.

        Returns the difficulty-based speed multiplier, optionally modified by
        the speed_multiplier override if speed_override_enabled is True.
        """
        difficulty = self.get_difficulty_level()
        base_speed = DIFFICULTY_PRESETS[difficulty]["speed_multiplier"]

        if self.speed_override_enabled:
            return base_speed * self.speed_multiplier

        return base_speed


@dataclass
class VisualEffectsConfig:
    """Configuration for visual effects."""

    explosions_enabled: bool = True
    screen_shake_enabled: bool = True
    lasers_enabled: bool = True
    explosion_duration_multiplier: float = 1.0
    explosion_size_multiplier: float = 1.0
    shake_intensity_multiplier: float = 1.0
    shake_duration_base: float = 0.3
    shake_magnitude_base: float = 5.0
    laser_duration: float = 0.2
    enable_sinc_explosions: bool = True
    enable_radial_explosions: bool = True
    enable_ripple_explosions: bool = True
    enable_colorshift_explosions: bool = True
    show_fps: bool = False

    def save_to_file(self, filepath: str):
        """Save configuration to JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "VisualEffectsConfig":
        """Load configuration from JSON file."""
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                return cls(**data)
        return cls()


@dataclass
class GameConfig:
    """Main game configuration."""

    visual_effects: VisualEffectsConfig = field(default_factory=VisualEffectsConfig)
    spawning: SpawningConfig = field(default_factory=SpawningConfig)
    config_dir: str = field(
        default_factory=lambda: os.path.join(os.path.dirname(__file__), "config")
    )

    def __post_init__(self):
        """Load all configurations after initialization."""
        effects_file = os.path.join(self.config_dir, "visual_effects.json")
        spawning_file = os.path.join(self.config_dir, "spawning.json")

        self.visual_effects = VisualEffectsConfig.load_from_file(effects_file)
        self.spawning = SpawningConfig.load_from_file(spawning_file)

    def save(self):
        """Save all configurations."""
        effects_file = os.path.join(self.config_dir, "visual_effects.json")
        spawning_file = os.path.join(self.config_dir, "spawning.json")

        self.visual_effects.save_to_file(effects_file)
        self.spawning.save_to_file(spawning_file)


def get_hand(button: str) -> Optional[str]:
    """Get which hand a button belongs to."""
    if button in LEFT_HAND_BUTTONS:
        return "left"
    elif button in RIGHT_HAND_BUTTONS:
        return "right"
    return None


def buttons_are_opposite_hands(btn1: str, btn2: str) -> bool:
    """Check if two buttons are on opposite hands."""
    hand1 = get_hand(btn1)
    hand2 = get_hand(btn2)
    if hand1 is None or hand2 is None:
        return False
    return hand1 != hand2


def get_explosion_type(word_length: int) -> str:
    """Determine explosion type based on word length."""
    if word_length <= 4:
        return "sinc"
    elif word_length <= 6:
        return "radial"
    elif word_length <= 8:
        return "ripple"
    else:
        return "color_shift"


def get_button_color(button: str) -> Tuple[int, int, int]:
    """Get RGB color tuple for a button.

    Args:
        button: Button letter (S, D, F, J, K, L)

    Returns:
        RGB tuple (r, g, b) for the button color, defaults to white if unknown
    """
    color_hex = BUTTON_COLORS.get(button, "#FFFFFF")
    return tuple(int(color_hex[i : i + 2], 16) for i in (1, 3, 5))


def get_button_label(button: str) -> str:
    """Get display label for a button.

    Args:
        button: Button letter (S, D, F, J, K, L)

    Returns:
        Display label for the button, or the button letter itself if no mapping exists
    """
    return BUTTON_LABELS.get(button, button)


def get_letter_spacing_for_sequence(sequence: str, base_spacing: int = 30) -> int:
    """Calculate letter spacing based on maximum label length in sequence.

    Args:
        sequence: String of button letters (e.g., "SDFJKL")
        base_spacing: Base spacing for single-character labels (default 30)

    Returns:
        Adjusted spacing to accommodate the longest label in the sequence
    """
    if not sequence:
        return base_spacing

    max_label_len = max(len(get_button_label(letter)) for letter in sequence)
    # Scale spacing: base_spacing is for 1 char, add ~12 pixels per extra character
    return base_spacing + (max_label_len - 1) * 12


def generate_evenly_distributed_letters(
    count: int, buttons: Optional[List[str]] = None
) -> List[str]:
    """Generate a list of letters with even distribution from available buttons.

    Works with any number of buttons (minimum 2 recommended). Each button appears
    approximately the same number of times, with random shuffling.

    Args:
        count: Number of letters to generate
        buttons: List of available buttons (defaults to ALL_BUTTONS)

    Returns:
        List of letters with even distribution, shuffled randomly
    """
    import random_manager

    if buttons is None:
        buttons = ALL_BUTTONS

    if not buttons:
        return []

    # Calculate how many times each button should appear for even distribution
    base_count = count // len(buttons)
    remainder = count % len(buttons)

    # Build the list with even distribution
    result = []
    for i, button in enumerate(buttons):
        # Add base_count of each button, plus one more for first 'remainder' buttons
        times = base_count + (1 if i < remainder else 0)
        result.extend([button] * times)

    # Shuffle to randomize order
    random_manager.shuffle(result)
    return result
