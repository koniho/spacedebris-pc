"""Starfield background that responds to game state."""

import random_manager
import numpy as np
import pyqtgraph as pg


class StarfieldBackground:
    """Dynamic starfield background that changes based on game state.

    Optimized for performance using a single ScatterPlotItem with batch updates.
    """

    def __init__(self, view, n_stars=1800):
        """Initialize starfield background.

        Args:
            view: PyQtGraph view to add stars to
            n_stars: Number of stars to render
        """
        self.view = view
        self.n_stars = n_stars

        # Star data - 3D positions (using float32 for better performance)
        self.x = random_manager.np_uniform(-1000, 1000, n_stars).astype(np.float32)
        self.y = random_manager.np_uniform(-800, 800, n_stars).astype(np.float32)
        self.z = random_manager.np_uniform(1, 150, n_stars).astype(np.float32)

        # Movement parameters
        self.base_speed = 0.8
        self.current_speed = self.base_speed
        self.direction_y = 0.0  # Vertical movement (-1 = up, 0 = neutral, 1 = down)

        # Color parameters
        self.base_color = (200, 200, 255)  # Bluish white
        self.current_color = self.base_color

        # Game state
        self.game_state = "intro"

        # Screen bounds for culling
        self.screen_bounds = (-500, 500, -400, 400)

        # Pre-allocate arrays for projected coordinates and visual properties
        self._px = np.zeros(n_stars, dtype=np.float32)
        self._py = np.zeros(n_stars, dtype=np.float32)
        self._sizes = np.zeros(n_stars, dtype=np.float32)
        self._brushes = [None] * n_stars  # Will be populated with reusable brushes

        # Create a single ScatterPlotItem for ALL stars (major optimization)
        # Using pxMode=True for constant pixel sizes, useCache=True for caching
        self.scatter = pg.ScatterPlotItem(
            size=4,
            pen=None,  # No pen for better performance
            pxMode=True,  # Constant pixel size (faster)
            useCache=True,  # Enable symbol caching
            antialias=False,  # Disable antialiasing for performance
        )
        self.scatter.setZValue(-1000)  # Behind all game elements
        self.view.addItem(self.scatter)

        # Pre-create reusable brush cache for common colors
        # This avoids creating new QBrush objects every frame
        self._brush_cache = {}

        # Flash effect state
        self.flash_active = False
        self.flash_timer = 0.0
        self.flash_duration = 0.1
        self.flash_frame = 0  # Alternates between 0 and 1

        self.flash_bg = pg.QtWidgets.QGraphicsRectItem(-500, -400, 1000, 800)
        self.flash_bg.setBrush(pg.mkBrush(255, 255, 255, 0))
        self.flash_bg.setPen(pg.mkPen(None))  # No border
        self.flash_bg.setZValue(-999)  # Just above starfield, below game elements
        self.view.addItem(self.flash_bg)
        self.flash_bg.setVisible(False)

        # Initialize target values
        self.target_speed = self.current_speed
        self.target_direction_y = self.direction_y
        self.target_color = self.current_color

    def _get_brush(self, r, g, b, a):
        """Get a cached brush or create a new one.

        Reusing brushes is critical for ScatterPlotItem performance.
        """
        # Quantize colors to reduce cache size (round to nearest 8)
        key = (r >> 3, g >> 3, b >> 3, a >> 3)
        if key not in self._brush_cache:
            self._brush_cache[key] = pg.mkBrush(r, g, b, a)
        return self._brush_cache[key]

    def start_flash(self, duration=0.3):
        """Start a screen flash effect with white background on alternating frames.

        Args:
            duration: How long the flash lasts in seconds.
        """
        self.flash_active = True
        self.flash_timer = 0.0
        self.flash_duration = duration
        self.flash_frame = 0

    def set_game_state(self, state: str):
        """Update starfield behavior based on game state.

        Args:
            state: One of 'intro', 'playing', 'wave_transition', 'game_over'
        """
        self.game_state = state

        if state == "intro":
            # Slow, peaceful movement
            self.target_speed = 0.3
            self.target_direction_y = 0.0
            self.target_color = (220, 220, 255)  # Bright bluish white

        elif state == "playing":
            # Normal speed, moving down (stars going up relative to player)
            self.target_speed = 1.0
            self.target_direction_y = 0.3  # Slight downward movement
            self.target_color = (255, 255, 255)  # Pure white for maximum visibility

        elif state == "wave_transition_enter":
            # Stars reverse direction (moving up)
            self.target_speed = 1.5
            self.target_direction_y = -4.0  # Strong upward movement
            self.target_color = (150, 255, 255)  # Bright cyan tint

        elif state == "wave_transition_exit":
            # Stars return to downward movement
            self.target_speed = 1.2
            self.target_direction_y = 4.5  # Return to downward
            self.target_color = (220, 220, 255)  # Back to bright bluish white

        elif state == "game_over":
            # Slow speed with reddish/orange tint
            self.target_speed = 0.5
            self.target_direction_y = 0.1
            self.target_color = (255, 180, 120)  # Brighter orange-red tint

    def update(self, dt: float):
        """Update starfield animation.

        Args:
            dt: Time delta in seconds
        """
        # Update flash effect
        if self.flash_active:
            self.flash_timer += dt
            self.flash_frame = 1 - self.flash_frame  # Alternate 0/1 each frame

            # Show white background on "on" frames
            if self.flash_frame == 1:
                self.flash_bg.setBrush(
                    pg.mkBrush(255, 255, 255, 200)
                )  # White with some transparency
                self.flash_bg.setVisible(True)
            else:
                self.flash_bg.setVisible(False)

            if self.flash_timer >= self.flash_duration:
                self.flash_active = False
                self.flash_bg.setVisible(False)

        # Smooth transitions for speed and direction
        transition_rate = 2.0 * dt  # How fast to transition

        # Update speed
        self.current_speed += (self.target_speed - self.current_speed) * transition_rate

        # Update direction
        self.direction_y += (self.target_direction_y - self.direction_y) * transition_rate

        # Update color
        r, g, b = self.current_color
        tr, tg, tb = self.target_color
        r += (tr - r) * transition_rate
        g += (tg - g) * transition_rate
        b += (tb - b) * transition_rate
        self.current_color = (r, g, b)

        # Move stars toward camera (z-axis movement)
        self.z -= self.current_speed * 60 * dt  # 60 for frame-rate independence

        # Apply vertical movement based on direction
        self.y += self.direction_y * 30 * dt

        # Reset stars that moved past camera
        mask = self.z < 1
        n_reset = np.sum(mask)
        if n_reset > 0:
            self.x[mask] = random_manager.np_uniform(-1000, 1000, n_reset).astype(np.float32)
            self.y[mask] = random_manager.np_uniform(-800, 800, n_reset).astype(np.float32)
            self.z[mask] = 150

        # Reset stars that moved too far off screen
        mask_y = np.abs(self.y) > 1200
        if np.any(mask_y):
            n_side = np.sum(mask_y)
            self.x[mask_y] = random_manager.np_uniform(-1000, 1000, n_side).astype(np.float32)
            self.y[mask_y] = (
                random_manager.np_uniform(-800, 800, n_side) * np.sign(self.y[mask_y]) * -0.5
            ).astype(np.float32)
            self.z[mask_y] = random_manager.np_uniform(50, 150, n_side).astype(np.float32)

        # Perspective projection (vectorized)
        scale = 150.0 / np.maximum(self.z, 0.1)
        self._px = self.x * scale
        self._py = self.y * scale

        # Filter to visible stars only (vectorized)
        visible_mask = (
            (self._px > self.screen_bounds[0])
            & (self._px < self.screen_bounds[1])
            & (self._py > self.screen_bounds[2])
            & (self._py < self.screen_bounds[3])
        )

        # Get visible star data
        visible_x = self._px[visible_mask]
        visible_y = self._py[visible_mask]
        visible_z = self.z[visible_mask]
        n_visible = len(visible_x)

        if n_visible == 0:
            self.scatter.setData([], [])
            return

        # Calculate depth factors for all visible stars (vectorized)
        depths = 1.0 - (visible_z / 150.0)

        # Calculate sizes based on depth (vectorized)
        sizes = 2.0 + depths * 6.0  # 2-8 pixel range

        # Calculate colors based on depth
        base_r, base_g, base_b = self.current_color
        brightness = 0.5 + depths * 0.5  # 50% to 100%
        alphas = (100 + depths * 155).astype(np.int32)  # 100-255

        # Handle flash effect
        if self.flash_active and self.flash_frame == 1:
            # Flash on: bright yellow stars, larger
            final_r = np.full(n_visible, 255, dtype=np.int32)
            final_g = np.full(n_visible, 255, dtype=np.int32)
            final_b = np.full(n_visible, 100, dtype=np.int32)
            alphas = np.full(n_visible, 255, dtype=np.int32)
            sizes = sizes * 3
        elif self.flash_active and self.flash_frame == 0:
            # Flash off: dim stars
            final_r = np.full(n_visible, 50, dtype=np.int32)
            final_g = np.full(n_visible, 50, dtype=np.int32)
            final_b = np.full(n_visible, 80, dtype=np.int32)
            alphas = np.full(n_visible, 50, dtype=np.int32)
        else:
            # Normal rendering
            final_r = (base_r * brightness).astype(np.int32)
            final_g = (base_g * brightness).astype(np.int32)
            final_b = (base_b * brightness).astype(np.int32)

        # Clamp color values
        final_r = np.clip(final_r, 0, 255)
        final_g = np.clip(final_g, 0, 255)
        final_b = np.clip(final_b, 0, 255)
        alphas = np.clip(alphas, 0, 255)

        # Create brush list using cached brushes
        brushes = [
            self._get_brush(final_r[i], final_g[i], final_b[i], alphas[i])
            for i in range(n_visible)
        ]

        # Single batch update to ScatterPlotItem (major performance gain)
        self.scatter.setData(
            x=visible_x,
            y=visible_y,
            size=sizes,
            brush=brushes,
        )

    def set_star_color(self, color: tuple):
        """Set the star color directly (overrides game state color).

        Args:
            color: RGB tuple (r, g, b) with values 0-255
        """
        self.current_color = color
        self.target_color = color

    def cleanup(self):
        """Remove all star items from the view."""
        if self.scatter:
            self.view.removeItem(self.scatter)
            self.scatter = None

        # Clear brush cache
        self._brush_cache.clear()

        # Remove flash background
        if self.flash_bg:
            self.view.removeItem(self.flash_bg)
            self.flash_bg = None
