"""Centralized random manager for deterministic game behavior."""

import random
import numpy as np


class RandomManager:
    """Centralized random number generator with seed support for deterministic behavior."""

    def __init__(self, seed=None):
        """Initialize random manager with optional seed.

        Args:
            seed: Optional integer seed for deterministic behavior.
                  If None, a seed will be auto-generated on first use.
        """
        self._seed = None
        self._rng = random.Random()
        self._np_rng = np.random.default_rng()
        self._initialized = False

        if seed is not None:
            self.set_seed(seed)

    def _ensure_initialized(self):
        """Ensure RNG is initialized with a seed (auto-generate if needed)."""
        if not self._initialized:
            # Auto-generate a seed if none was set
            # Use the _rng instance which is a Random object, not the module function
            seed = self._rng.randint(0, 2**31 - 1)
            self.set_seed(seed)

    def set_seed(self, seed):
        """Set seed for both Python random and numpy random generators.

        Args:
            seed: Integer seed value.
        """
        self._seed = seed
        self._rng.seed(seed)
        self._np_rng = np.random.default_rng(seed)
        self._initialized = True
        print(f"Random seed set to: {seed}")

    def get_seed(self):
        """Get the current seed value (auto-generates if not set)."""
        self._ensure_initialized()
        return self._seed

    # Python random equivalents
    def random(self):
        """Return random float in [0.0, 1.0)."""
        self._ensure_initialized()
        return self._rng.random()

    def uniform(self, a, b):
        """Return random float N such that a <= N <= b."""
        self._ensure_initialized()
        return self._rng.uniform(a, b)

    def randint(self, a, b):
        """Return random integer N such that a <= N <= b."""
        self._ensure_initialized()
        return self._rng.randint(a, b)

    def choice(self, seq):
        """Return random element from non-empty sequence."""
        self._ensure_initialized()
        return self._rng.choice(seq)

    def sample(self, population, k):
        """Return k unique random elements from population."""
        self._ensure_initialized()
        return self._rng.sample(population, k)

    def shuffle(self, x):
        """Shuffle list x in place."""
        self._ensure_initialized()
        self._rng.shuffle(x)

    # Numpy random equivalents
    def np_uniform(self, low=0.0, high=1.0, size=None):
        """Generate uniform random values using numpy."""
        self._ensure_initialized()
        return self._np_rng.uniform(low, high, size)

    def np_random(self, size=None):
        """Generate random values in [0.0, 1.0) using numpy."""
        self._ensure_initialized()
        return self._np_rng.random(size)

    def np_integers(self, low, high=None, size=None):
        """Generate random integers using numpy."""
        self._ensure_initialized()
        return self._np_rng.integers(low, high, size)


# Global singleton instance
_random_manager = RandomManager()


def get_random_manager():
    """Get the global random manager instance."""
    return _random_manager


def set_global_seed(seed):
    """Set the seed for the global random manager."""
    _random_manager.set_seed(seed)


# Convenience functions that use the global manager
def random():
    """Return random float in [0.0, 1.0)."""
    return _random_manager.random()


def uniform(a, b):
    """Return random float N such that a <= N <= b."""
    return _random_manager.uniform(a, b)


def randint(a, b):
    """Return random integer N such that a <= N <= b."""
    return _random_manager.randint(a, b)


def choice(seq):
    """Return random element from non-empty sequence."""
    return _random_manager.choice(seq)


def sample(population, k):
    """Return k unique random elements from population."""
    return _random_manager.sample(population, k)


def shuffle(x):
    """Shuffle list x in place."""
    _random_manager.shuffle(x)


def np_uniform(low=0.0, high=1.0, size=None):
    """Generate uniform random values using numpy."""
    return _random_manager.np_uniform(low, high, size)


def np_random(size=None):
    """Generate random values in [0.0, 1.0) using numpy."""
    return _random_manager.np_random(size)
