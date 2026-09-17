"""Simultaneous input processing and tracking."""

from typing import Set, Dict, List, Optional


class SimultaneousInputTracker:
    """Tracks simultaneous button presses with timing tolerance."""

    def __init__(self, sync_window_ms: int = 100):
        """Initialize input tracker."""
        self.held_buttons: Set[str] = set()
        self.button_press_times: Dict[str, float] = {}
        self.sync_window_ms = sync_window_ms

        # Track recent presses for disengagement detection
        self.recent_presses: List[tuple] = []  # (button, timestamp) pairs

        # Debug properties
        self.last_sync_attempt: Optional[tuple] = None
        self.last_sync_success: bool = False

    def on_button_press(self, button: str, timestamp: float):
        """Handle button press event."""
        self.held_buttons.add(button)
        self.button_press_times[button] = timestamp

        # Track recent presses for disengagement detection
        self.recent_presses.append((button, timestamp))

        # Clean up old presses (keep only last 500ms)
        self.recent_presses = [(b, t) for b, t in self.recent_presses if timestamp - t <= 500]

    def on_button_release(self, button: str):
        """Handle button release event."""
        self.held_buttons.discard(button)
        self.button_press_times.pop(button, None)

    def check_simultaneous_press(
        self, required_buttons: Set[str], _current_time: float, consume: bool = True
    ) -> bool:
        """Check if required buttons are pressed simultaneously within tolerance.

        Args:
            required_buttons: Set of buttons that must be pressed together.
            _current_time: Current time (unused, kept for API compatibility).
            consume: If True, consume the press times on success so subsequent
                     checks won't trigger on the same press.
        """
        # Check all required buttons are currently held
        if not required_buttons.issubset(self.held_buttons):
            self.last_sync_attempt = (required_buttons, None)
            self.last_sync_success = False
            return False

        # Get press times for required buttons
        press_times = []
        for button in required_buttons:
            if button in self.button_press_times:
                press_times.append(self.button_press_times[button])
            else:
                self.last_sync_attempt = (required_buttons, None)
                self.last_sync_success = False
                return False

        # Check time spread
        if len(press_times) < 2:
            # Single button or no buttons - always "simultaneous"
            time_spread = 0.0
        else:
            time_spread = max(press_times) - min(press_times)

        self.last_sync_attempt = (required_buttons, time_spread)

        # Check if within tolerance window
        if time_spread <= self.sync_window_ms:
            self.last_sync_success = True
            # Consume the press times so subsequent checks won't trigger
            if consume:
                for button in required_buttons:
                    self.button_press_times.pop(button, None)
            return True

        self.last_sync_success = False
        return False

    def get_held_buttons(self) -> Set[str]:
        """Get copy of currently held buttons for UI feedback."""
        return self.held_buttons.copy()

    def get_recent_presses(self, current_time: float, window_ms: float) -> Set[str]:
        """Get buttons pressed recently within time window."""
        recent_buttons = set()
        for button, timestamp in self.recent_presses:
            if current_time - timestamp <= window_ms:
                recent_buttons.add(button)
        return recent_buttons

    def clear_all(self):
        """Clear all tracked button states."""
        self.held_buttons.clear()
        self.button_press_times.clear()
        self.recent_presses.clear()
        self.last_sync_attempt = None
        self.last_sync_success = False
