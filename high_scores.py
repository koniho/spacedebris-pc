"""High score persistence."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional

from app_paths import get_user_data_dir


@dataclass
class HighScoreEntry:
    """Single high score entry."""

    name: str
    score: int
    wave: int
    bosses: int
    difficulty: str
    perfect_waves: int
    timestamp: str


class HighScoreBoard:
    """Manages persistent high score data."""

    MAX_ENTRIES = 10

    def __init__(self):
        self.config_dir = str(get_user_data_dir())
        self.filepath = os.path.join(self.config_dir, "high_scores.json")
        self.entries: List[HighScoreEntry] = []
        self.load()

    def load(self):
        """Load high scores from disk."""
        if not os.path.exists(self.filepath):
            self.entries = self._default_entries()
            self.save()
            return

        try:
            with open(self.filepath) as f:
                data = json.load(f)
            self.entries = [HighScoreEntry(**e) for e in data.get("scores", [])]
        except (json.JSONDecodeError, TypeError, KeyError):
            self.entries = self._default_entries()
            self.save()

    @staticmethod
    def _default_entries():
        """Seed entries for a fresh board."""
        seeds = [
            ("STN", 2800, 8, 2, "HARD", 3),
            ("SAM", 2200, 7, 1, "HARD", 2),
            ("FKD", 1900, 7, 1, "NORMAL", 4),
            ("RAY", 1500, 6, 1, "NORMAL", 2),
            ("SKY", 1200, 5, 1, "NORMAL", 1),
            ("REX", 900, 5, 1, "EASY", 3),
            ("DOT", 650, 4, 0, "EASY", 1),
            ("BUZ", 400, 3, 0, "EASY", 0),
        ]
        return [
            HighScoreEntry(
                name=name, score=score, wave=wave, bosses=bosses,
                difficulty=diff, perfect_waves=pw, timestamp="2026-01-01T00:00:00",
            )
            for name, score, wave, bosses, diff, pw in seeds
        ]

    def save(self):
        """Save high scores to disk."""
        os.makedirs(self.config_dir, exist_ok=True)
        data = {"scores": [asdict(e) for e in self.entries]}
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def qualifies(self, score: int) -> bool:
        """Check if a score qualifies for the board."""
        if score <= 0:
            return False
        if len(self.entries) < self.MAX_ENTRIES:
            return True
        return score >= self.entries[-1].score

    def get_qualifying_rank(self, score: int) -> int:
        """Return 0-indexed rank where this score would insert."""
        for i, entry in enumerate(self.entries):
            if score >= entry.score:
                return i
        return len(self.entries)

    def insert(self, entry: HighScoreEntry) -> int:
        """Insert entry at correct position, save, return rank."""
        rank = self.get_qualifying_rank(entry.score)
        self.entries.insert(rank, entry)
        self.entries = self.entries[: self.MAX_ENTRIES]
        self.save()
        return rank

    @staticmethod
    def create_entry(
        name: str, score: int, wave: int, bosses: int, difficulty: str, perfect_waves: int
    ) -> HighScoreEntry:
        """Create a new entry with current timestamp."""
        return HighScoreEntry(
            name=name,
            score=score,
            wave=wave,
            bosses=bosses,
            difficulty=difficulty,
            perfect_waves=perfect_waves,
            timestamp=datetime.now().isoformat(),
        )
