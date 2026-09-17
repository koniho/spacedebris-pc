"""Face boss with SVG morphing visuals."""

import math
from debug_log import debug_print as print
import re
from typing import Callable, List, Optional, Tuple

import numpy as np
import pyqtgraph as pg
import random_manager
from svg_path_morph import compile as svg_compile, morph

from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt

from config import ALL_BUTTONS, BUTTON_COLORS, LEFT_HAND_BUTTONS, RIGHT_HAND_BUTTONS
from effects.cone_effect import ConeEffect
from effects.particle_effects import AttractionParticleSystem
from enemies import Enemy
from enemies.base_boss import BaseBoss
from enemies.face_boss_letter import FaceBossLetter, FaceBossProjectile


# Path data extracted from the SVG files
# fmt: off
FACE_PATHS = {
    "left_up": (
        "M1 113C7.83333 132.667 4 188 50.5 189C76.9939 189.57 102.055 148.324 "
        "126.555 138.324C153.489 127.331 149 -56.5 67 18.5C-15 93.5 5.5 34 "
        "15.0001 29C21 21.5 38 18.5 43.5 34.9999C30.5 40.5 14 39.5 8.99999 32.5"
        "C3.99999 21 -0.0124836 4.00012 26.5553 6.32433C76.5 10.6936 40.736 "
        "34.508 29 64.5C20 87.5 47 78.5 56.5 78.5C64.1 78.5 69.1667 85.6666 "
        "70.5 87.5M21 113C25.1667 111.5 33.3 102.2 40.5 107C44 109.333 48.0746 "
        "107.606 50.5 107C54.5 106 56.5 111.5 72.5 116.5C85.3 120.5 87 121.333 "
        "87.5 120.5C76 132.833 40.5 139.5 20.5 115C29 118.333 51.5 121.5 90 "
        "120.5M80 34.9999C91.5 18.5 113 18 128 39C121.5 40.5 98 45 80 34.9999Z"
    ),
    "right_up": (
        "M25 130.5C37 139 42 174 80 178.5C106.316 181.616 119 171 120.5 169.5"
        "C139.182 150.819 143.353 -87.9039 66.7648 37.4225C28.2648 100.422 "
        "5.50001 70.5001 14 50.0001C17.5 40.0001 40 26.5001 53.5 51.0001C38 "
        "55.5001 22.5 57.0001 10.7647 50.9222C-15.8336 37.1465 19.522 13.9678 "
        "46.0781 16.4222C94.7649 20.9222 81.8113 46.4215 100 73C113.687 93 "
        "86.3123 89.1578 83.5 90C74.1999 92.7853 73 91 72 89M50 127.5C55 127.5 "
        "76 114 80 113C91.1566 110.211 91.5 117 93.5 115.5C95.5 114 97.5 "
        "111.771 103 113C106.5 113.782 120 128.333 120.5 127.5C119.5 131.5 "
        "78.5 141 48.5 126.5C60.4997 133.5 80.5 112 123 128.5M90.7649 48.0001"
        "C95.2649 38.5001 120.928 21.5001 127.428 51.0001C120 53.0001 111.5 "
        "54.0001 90.7649 48.0001Z"
    ),
    "left_down": (
        "M39.5 134.5C51.5 143 39.5 171.5 77.5 176C103.816 179.116 110 142 "
        "134.5 132C161.433 121.007 172.105 -67.395 60 27.5C10 69.8243 -4.49997 "
        "40.5 5.00007 35.5C11 30 25 32 34.5 39C21.5001 49 9.99998 44.5 7.00002 "
        "36C2.00002 24.5 -8.49999 11.9999 18 14.9999C44.5 17.9999 39.3478 "
        "59.5328 30.5 90.5C23.5 115 48 106.5 57.5554 102.5C66.5107 98.7512 "
        "68.1667 103.667 69.5 105.5M41.5 118.5C46.5 118.5 54.5554 122 57.5554 "
        "124C59.8054 125.5 64.5 124.5 66.5 123C68.5 121.5 75 121.271 80.5 "
        "122.5C84 123.282 99 121.833 99.5 121C92.5 134 49 154 42 119.5C52.5 "
        "128 61 133 103 120M75.5 38C82.5554 37 105.5 38 123.5 31.5C116.5 44.5 "
        "91.5 60.5 75.5 38Z"
    ),
    "right_down": (
        "M23.0001 152.5C35.0001 161 37.0001 191.5 75.0001 196C101.316 199.116 "
        "99.5 169 114 149.5C131.358 126.156 142.089 -85.3262 65.4999 40.0001"
        "C26.9999 103 -10.5002 60.4999 11.4998 49.5004C17.4998 44.0004 42.5001 "
        "47.0004 53 49.5004C41.5501 66.4999 20.4999 60.76 9.49985 53.4999"
        "C-15.5001 36.9999 18.2571 16.5455 44.8132 18.9999C93.5 23.4999 84.3487 "
        "70.6738 96.5 100.5C107.5 127.5 70.5759 110.924 68.5 113C67 114.5 67.5 "
        "115 67.5 116.5M41 139C46 139 57.5 140 61.5 139C72.6566 136.211 75.5 "
        "141.5 77.5 140C79.5 138.5 81.5 137.771 87 139C90.5 139.782 105.5 "
        "132.833 106 132C98.5 157.5 70.5 166.5 42 139C69.5 140 74 157 107.5 "
        "131M97.4998 49.5001C106.313 42.0001 115.5 46.5 133.5 40C126.5 53 117 "
        "69.5001 97.4998 49.5001Z"
    ),
}
# fmt: on


def extract_points_from_path(path: str) -> List[Tuple[float, float]]:
    """Extract all coordinate points from an SVG path string."""
    compiled = svg_compile([path])
    points = []
    for idx, _ in enumerate(compiled.commands):
        coords = compiled.average[idx]
        for j in range(0, len(coords), 2):
            if j + 1 < len(coords):
                points.append((coords[j], coords[j + 1]))
    return points


class FaceBoss(BaseBoss):
    """Boss with an animated SVG face that morphs between poses."""

    def __init__(self, view, laser_manager, waveform, game_engine):
        super().__init__(view, laser_manager, waveform)

        self.game_engine = game_engine
        self.view = view

        # Arc movement parameters (phase 1) - defined early so initial position matches
        self.arc_center_x = 0  # Center of arc horizontally
        self.arc_center_y = 50  # Center of arc (below boss starting position)
        self.arc_radius = 120  # Radius of the arc
        self.arc_speed = 0.8  # Speed of movement along arc (radians per second)
        self.arc_angle = math.pi / 2  # Start at top of arc (90 degrees)

        # Boss position (set to match arc start position for smooth transition)
        self.boss_x = self.arc_center_x + self.arc_radius * math.cos(self.arc_angle)
        self.boss_y = self.arc_center_y + self.arc_radius * math.sin(self.arc_angle)
        self.center_pos = (self.boss_x, self.boss_y)

        # SVG scale and offset for rendering
        self.svg_scale = 2.0
        self.svg_offset_x = -75  # Center the SVG (original viewbox is ~153 wide)
        self.svg_offset_y = -90  # Center vertically (original viewbox is ~177 tall)

        # Compile paths for morphing
        self.compiled_paths = svg_compile(
            [
                FACE_PATHS["left_up"],
                FACE_PATHS["right_up"],
                FACE_PATHS["left_down"],
                FACE_PATHS["right_down"],
            ]
        )

        # Current morph weights [left_up, right_up, left_down, right_down]
        self.morph_weights = [0.25, 0.25, 0.25, 0.25]
        self.morph_lerp_speed = 3.0  # How fast to interpolate to target weights

        # Extract points for star animation (use left_down as base)
        self.target_points = extract_points_from_path(FACE_PATHS["left_down"])

        # Animation state
        # Phases: "stars_entering", "svg_fading_in", "phase1_active",
        #         "transition_to_center", "transition_flash", "transition_split",
        #         "phase2_active", "destroyed"
        self.phase = "stars_entering"
        self.animation_time = 0.0
        self.stars_duration = 2.0  # Time for stars to fly in
        self.fade_duration = 2.0  # Time for SVG to fade in
        self.active_time = 0.0

        # Phase 2 state - two faces
        self.boss_phase = 1  # 1 or 2
        self.transition_duration = 3.0  # Time to move to center (with screen shake)
        self.flash_duration = 0.5  # Screen flash duration
        self.split_duration = 1.5  # Time to move to corners
        self.rumble_timer = 0.0  # Timer for rumble sound effects
        self.rumble_interval = 0.15  # How often to play rumble sounds

        # Second face (for phase 2)
        self.face2_x = 0.0
        self.face2_y = 0.0
        self.face2_scale = 1.0
        self.face2_morph_weights = [0.25, 0.25, 0.25, 0.25]
        self.face2_curves: List[pg.PlotCurveItem] = []
        self.face2_curves_layer1: List[pg.PlotCurveItem] = []
        self.face2_curves_layer2: List[pg.PlotCurveItem] = []
        self.face2_eye_curves: List[pg.PlotCurveItem] = []
        self.face2_eye_curves_layer1: List[pg.PlotCurveItem] = []
        self.face2_eye_curves_layer2: List[pg.PlotCurveItem] = []
        self.face2_eye_fill: Optional[pg.PlotDataItem] = None
        self.face2_eye_center = (0.0, 0.0)
        self.face2_eye_glow = 0.0
        self.face2_eye_glowing = False
        self.face2_eye_glow_timer = 0.0

        # Phase 2 corner positions (15% off-screen)
        # Screen width is ~800 (-400 to 400), so 15% off = 400 * 1.15 = 460
        self.corner_left = (-300, 175)  # Top left corner, 15% off-screen
        self.corner_right = (300, 175)  # Top right corner, 15% off-screen
        self.phase2_scale = 1.2  # 20% larger in phase 2

        # Grey tone for transition
        self.grey_factor = 0.0  # 0 = normal colors, 1 = grey

        # Phase 2 attack timing
        self.phase2_attack_interval = 2.0
        self.phase2_attack_timer = 0.0
        self.phase2_attacking_face = None  # "left" or "right"

        # Phase 2 dual-face engagement mechanic
        self.phase2_engaged_face: Optional[str] = (
            None  # "left" or "right" - which face player is attacking
        )
        self.phase2_left_idle_timer = 0.0  # Time since left face was last attacked
        self.phase2_right_idle_timer = 0.0  # Time since right face was last attacked
        self.phase2_idle_timeout = 3.0  # Seconds before idle face attacks
        self.phase2_switchover_active = False  # True during face switchover animation
        self.phase2_switchover_timer = 0.0
        self.phase2_switchover_duration = 0.4  # Time for switchover animation

        # Phase 2 word state for each face
        self.phase2_left_word = ""  # Current word for left face
        self.phase2_left_typed = 0  # Letters typed on left face
        self.phase2_left_letters: List[FaceBossLetter] = []
        self.phase2_right_word = ""  # Current word for right face
        self.phase2_right_typed = 0  # Letters typed on right face
        self.phase2_right_letters: List[FaceBossLetter] = []

        # Phase 2 progression - word length increases as letters are destroyed
        self.phase2_letters_destroyed = 0  # Total letters destroyed
        self.phase2_letters_per_length_increase = 20  # Letters needed to increase word length
        self.phase2_min_word_length = 2
        self.phase2_max_word_length = 5

        # Phase 2 fire cone attack state (per face)
        self.phase2_left_firing = False
        self.phase2_left_fire_timer = 0.0
        self.phase2_left_fire_last_shot = 0.0
        self.phase2_left_fire_cone: Optional[ConeEffect] = None
        self.phase2_right_firing = False
        self.phase2_right_fire_timer = 0.0
        self.phase2_right_fire_last_shot = 0.0
        self.phase2_right_fire_cone: Optional[ConeEffect] = None
        self.phase2_fire_duration = 1.5  # Fire for 1.5 seconds
        self.phase2_fire_interval = 0.2  # Fire every 200ms

        # Phase 2 charging state (for non-engaged face)
        self.phase2_left_charging = False
        self.phase2_left_charge_timer = 0.0
        self.phase2_left_charge_particles = AttractionParticleSystem(
            view,
            spawn_distance_range=(60, 120),
            num_particles=45,
            color=(255, 120, 50),  # Orange/red for fire attack
            base_size=5,
            base_alpha=200,
            z_value=12,
        )
        self.phase2_right_charging = False
        self.phase2_right_charge_timer = 0.0
        self.phase2_right_charge_particles = AttractionParticleSystem(
            view,
            spawn_distance_range=(60, 120),
            num_particles=45,
            color=(255, 120, 50),  # Orange/red for fire attack
            base_size=5,
            base_alpha=200,
            z_value=12,
        )
        self.phase2_charge_duration = 1.0  # 1 second charge before attack

        # Transition state
        self.transition_start_pos = (0.0, 0.0)
        self.phase2_transition_timer = 0.0

        # Star particles - single ScatterPlotItem for all stars
        self.stars: List[dict] = []
        self.stars_plot_item: Optional[pg.ScatterPlotItem] = None
        self.star_base_size = 8  # Star size
        # Constellation formation state
        self.constellation_lines: List[pg.PlotCurveItem] = []
        self.constellation_line_progress = 0.0  # 0-1 progress of line drawing
        self.constellation_draw_duration = 1.5  # Time to draw all lines
        self.constellation_glow_duration = 1.0  # Time for glow/pulse phase
        self.constellation_glow_timer = 0.0
        self.constellation_pulse_count = 0  # Number of pulses completed

        self._create_stars()

        # SVG visual elements - main curves plus two duplicate layers with offsets
        # Face curves (segments 0 and 1 - head outline and mouth)
        self.svg_curves: List[pg.PlotCurveItem] = []  # Main (cyan)
        self.svg_curves_layer1: List[pg.PlotCurveItem] = []  # Red/magenta layer
        self.svg_curves_layer2: List[pg.PlotCurveItem] = []  # Yellow/green layer
        self.svg_opacity = 0.0

        # Eye curves (segment 2 - the closed Z path)
        self.eye_curves: List[pg.PlotCurveItem] = []  # Main eye outline
        self.eye_curves_layer1: List[pg.PlotCurveItem] = []  # Eye red layer
        self.eye_curves_layer2: List[pg.PlotCurveItem] = []  # Eye yellow layer
        self.eye_fill: Optional[pg.PlotDataItem] = None  # Filled eye shape
        self.eye_center = (0.0, 0.0)  # World position for projectiles
        self.eye_glow = 0.0  # 0-1 glow intensity
        self.eye_glow_timer = 0.0  # Timer for glow triggers
        self.eye_glow_interval = 2.0  # Seconds between glow triggers
        self.eye_glow_duration = 0.5  # Duration of glow effect
        self.eye_glowing = False  # Whether eye is currently glowing

        # Eye blink animation (damage only, separate from color pulsing)
        self.eye_blink = 0.0  # 0-1 blink intensity for Y-scaling
        self.eye_blink_timer = 0.0
        self.eye_blink_duration = 0.5
        self.eye_blinking = False

        # Animated offsets for duplicate layers
        self.layer1_offset_x = 0.0
        self.layer1_offset_y = 0.0
        self.layer2_offset_x = 0.0
        self.layer2_offset_y = 0.0

        # Boss state
        self.completed = False
        self.defeated = False

        # Destruction callback
        self.destruction_callback: Optional[Callable] = None

        # Target enemy for phase 1 (typeable word near eye)
        self.target_enemy: Optional[Enemy] = None
        self.laser_manager = laser_manager
        self.waveform = waveform

        # Phase 1 word attack system
        self.word_sequence = ""  # Current 4-letter word
        self.word_typed_count = 0  # Letters typed so far
        self.word_timer = 0.0  # Time since word started
        self.word_timeout = 3.0  # Seconds before attack fires
        self.word_active = False  # Whether word is currently displayed
        self.word_letters: List[FaceBossLetter] = []  # Letter enemy instances
        self.word_base_y = 0.0  # Base Y position for letters
        self.word_slide_from_left = True  # Direction for letter slide animations
        self.words_completed = 0  # Number of word segments destroyed

        # here tuning
        self.words_to_phase2 = 7  # Words needed to trigger phase 2
        self.phase2_health = 100

        # Word completion animation state
        self.word_complete_animating = False
        self.word_complete_timer = 0.0
        self.word_complete_duration = 1.0  # 1 second animation
        self.base_stroke_width = 3  # Normal stroke width
        self.current_stroke_width = 3.0

        # Red flash animation state (for damage feedback)
        self.red_flash_factor = 0.0  # 0 = normal colors, 1 = full red
        self.red_flash_timer = 0.0
        self.red_flash_duration = 0.3  # Duration of red flash
        self.red_flash_active = False

        # Red pulse animation state (for phase 2 transition)
        self.red_pulse_active = False

        # Distortion effect state (for damage and death animation)
        self.distortion_amount = 0.0  # 0 = no distortion, higher = more distortion
        self.distortion_seed = 0  # Seed for consistent random distortion per damage
        self.damage_distortion_active = False
        self.damage_distortion_timer = 0.0
        self.damage_distortion_duration = 0.5  # Damage distortion lasts 0.5 seconds

        # Death animation state
        self.death_animation_active = False
        self.death_animation_timer = 0.0
        self.death_frame_skip_counter = 0  # For skipping frames during death
        self.death_collapse_duration = 3.0  # 3 seconds to collapse into horizontal band
        self.death_fade_duration = 3.0  # 3 seconds to fade out with explosions
        self.death_y_scale = 1.0  # Y-scale factor (1.0 = normal, 0.05 = collapsed band)
        self.death_explosion_timer = 0.0  # Timer for spawning explosions
        self.death_explosion_interval = 0.15  # Spawn explosion every 150ms
        self.death_flash_timer = 0.0  # Timer for flash effects
        self.death_flash_interval = 0.3  # Flash every 300ms

        # Mouth charging state
        self.mouth_charging = False
        self.mouth_charge_progress = 0.0  # 0-1 charge level
        self.mouth_center = (0.0, 0.0)  # Center of mouth for particles
        self.charge_particles = AttractionParticleSystem(
            view,
            spawn_distance_range=(80, 150),
            num_particles=40,
            color=(255, 100, 100),
            base_size=5,
            base_alpha=200,
            z_value=12,
        )

        # Projectile attack state
        self.firing_projectiles = False
        self.fire_timer = 0.0
        self.fire_duration = 2.0  # Fire for 2 seconds
        self.fire_interval = 0.167  # Fire every ~167ms (reduced by 70% from 50ms)
        self.fire_last_shot = 0.0
        self.projectiles: List[FaceBossProjectile] = []  # Active projectile enemies

        # Fire cone config
        self.fire_cone: Optional[ConeEffect] = None
        self.fire_cone_num_interior = 10

        # Disable cone config (from eye to player)
        self.disable_cone: Optional[ConeEffect] = None
        self.disable_cone_num_interior = 25
        self.disable_cone_active = False
        self.disable_cone_timer = 0.0
        self.disable_cone_duration = 1.0  # 1 second disable

        # Track exiting cones so they can finish their animations
        self.exiting_cones: List[ConeEffect] = []

        # Sequence restart cooldown
        self.sequence_cooldown = 0.0
        self.sequence_cooldown_duration = 1.0  # Wait 1 second after attack ends

        # Trail effect - rendered to a QPixmap that fades over time
        self.trail_enabled = True
        self.trail_fade_alpha = 20  # Alpha to subtract each frame (higher = faster fade)
        self.trail_width = 800  # Surface width in pixels
        self.trail_height = 800  # Surface height in pixels (taller to capture full face)
        # World coordinate bounds for trail surface
        self.trail_world_x_min = -400
        self.trail_world_x_max = 400
        self.trail_world_y_min = -300
        self.trail_world_y_max = 500  # Extended to capture top of face
        self.trail_pixmap: Optional[QPixmap] = None
        self.trail_image_item: Optional[pg.ImageItem] = None
        self._create_trail_surface()

    def _create_trail_surface(self):
        """Create the trail rendering surface using QPixmap."""
        # Create transparent pixmap
        self.trail_pixmap = QPixmap(self.trail_width, self.trail_height)
        self.trail_pixmap.fill(Qt.transparent)

        # Create initial empty numpy array for the ImageItem
        # After transpose, dimensions will be (width, height, 4)
        initial_arr = np.zeros((self.trail_width, self.trail_height, 4), dtype=np.uint8)

        # Create ImageItem to display the trail
        self.trail_image_item = pg.ImageItem(initial_arr)
        self.trail_image_item.setZValue(0)  # Behind everything else
        # Position the image to cover the extended screen area
        world_width = self.trail_world_x_max - self.trail_world_x_min
        world_height = self.trail_world_y_max - self.trail_world_y_min
        self.trail_image_item.setRect(
            self.trail_world_x_min, self.trail_world_y_min, world_width, world_height
        )
        self.view.addItem(self.trail_image_item)

    def _world_to_surface(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to surface pixel coordinates."""
        # World coords to QPixmap coords (y increases downward in QPixmap)
        world_width = self.trail_world_x_max - self.trail_world_x_min
        world_height = self.trail_world_y_max - self.trail_world_y_min
        surface_x = int((world_x - self.trail_world_x_min) * self.trail_width / world_width)
        surface_y = int((self.trail_world_y_max - world_y) * self.trail_height / world_height)
        return surface_x, surface_y

    def _render_curves_to_pixmap(
        self, painter: QPainter, curves: List[pg.PlotCurveItem], color: QColor
    ):
        """Render a list of curves to the pixmap using QPainter."""
        pen = QPen(color)
        pen.setWidth(3)
        painter.setPen(pen)

        for curve in curves:
            data = curve.getData()
            if data[0] is None or len(data[0]) < 2:
                continue
            x_data, y_data = data
            for i in range(len(x_data) - 1):
                sx1, sy1 = self._world_to_surface(x_data[i], y_data[i])
                sx2, sy2 = self._world_to_surface(x_data[i + 1], y_data[i + 1])
                painter.drawLine(sx1, sy1, sx2, sy2)

    def _update_trail(self):
        """Update the trail surface - fade existing and render current frame."""
        if not self.trail_enabled or self.trail_pixmap is None:
            return

        # Create a new pixmap for compositing
        new_pixmap = QPixmap(self.trail_width, self.trail_height)
        new_pixmap.fill(Qt.transparent)

        painter = QPainter(new_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the old trail with reduced opacity (fading effect)
        painter.setOpacity(0.92)  # Fade rate
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.drawPixmap(0, 0, self.trail_pixmap)

        # Reset opacity for new curves
        painter.setOpacity(0.7)  # Trail alpha

        # Determine trail colors based on phase
        if self.phase == "death_animation":
            # Cycle between red, orange, yellow during death
            cycle_speed = 8.0  # Cycles per second
            t = (self.death_animation_timer * cycle_speed) % 3.0
            if t < 1.0:
                # Red to orange
                r, g, b = 255, int(100 + 155 * t), 0
            elif t < 2.0:
                # Orange to yellow
                r, g, b = 255, 255, int(255 * (t - 1.0))
            else:
                # Yellow to red
                r, g, b = 255, int(255 * (3.0 - t)), int(255 * (3.0 - t))
            face_color = QColor(r, g, b, 200)
            eye_color = QColor(r, g, b, 200)
        else:
            face_color = QColor(100, 200, 255, 200)
            eye_color = QColor(255, 100, 100, 200)

        # Render face 1 curves
        if self.svg_curves:
            self._render_curves_to_pixmap(painter, self.svg_curves, face_color)
        if self.eye_curves:
            self._render_curves_to_pixmap(painter, self.eye_curves, eye_color)

        # Render face 2 curves (phase 2)
        if self.boss_phase == 2:
            if self.face2_curves:
                self._render_curves_to_pixmap(painter, self.face2_curves, face_color)
            if self.face2_eye_curves:
                self._render_curves_to_pixmap(painter, self.face2_eye_curves, eye_color)

        painter.end()

        # Update the trail pixmap
        self.trail_pixmap = new_pixmap

        # Convert QPixmap to numpy array for ImageItem
        image = self.trail_pixmap.toImage()
        width = image.width()
        height = image.height()
        ptr = image.bits()
        ptr.setsize(height * width * 4)
        arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 4))
        # Convert BGRA to RGBA
        arr = arr[:, :, [2, 1, 0, 3]]
        # Flip Y axis (QPixmap Y increases down, pyqtgraph Y increases up)
        arr = arr[::-1, :, :]
        # Transpose for pyqtgraph ImageItem (expects width, height, channels)
        arr = np.transpose(arr, (1, 0, 2))

        if self.trail_image_item is not None:
            self.trail_image_item.setImage(arr)

    def _create_stars(self):
        """Create star particles that will fly in from screen edges."""
        screen_width = 400
        screen_height = 350

        for idx, (tx, ty) in enumerate(self.target_points):
            # Transform target point to screen coordinates
            target_x = self.boss_x + (tx + self.svg_offset_x) * self.svg_scale
            target_y = self.boss_y + (-ty - self.svg_offset_y) * self.svg_scale  # Flip Y

            # Random starting position outside screen edges
            edge = random_manager.choice(["top", "bottom", "left", "right"])
            if edge == "top":
                start_x = random_manager.uniform(-screen_width, screen_width)
                start_y = screen_height + 50
            elif edge == "bottom":
                start_x = random_manager.uniform(-screen_width, screen_width)
                start_y = -screen_height - 50
            elif edge == "left":
                start_x = -screen_width - 50
                start_y = random_manager.uniform(-screen_height, screen_height)
            else:  # right
                start_x = screen_width + 50
                start_y = random_manager.uniform(-screen_height, screen_height)

            # Random delay for staggered arrival
            delay = random_manager.uniform(0, self.stars_duration * 0.5)

            self.stars.append(
                {
                    "index": idx,  # Index for constellation line connections
                    "start_x": start_x,
                    "start_y": start_y,
                    "target_x": target_x,
                    "target_y": target_y,
                    "current_x": start_x,
                    "current_y": start_y,
                    "delay": delay,
                    "arrived": False,
                    "motion_time": 0.0,  # Time since star started moving (for color pulse)
                }
            )

        # Create single ScatterPlotItem for all stars
        if self.stars:
            positions = [(star["start_x"], star["start_y"]) for star in self.stars]
            self.stars_plot_item = pg.ScatterPlotItem(
                pos=positions,
                size=8,
                brush=pg.mkBrush(100, 200, 255, 255),
                pen=pg.mkPen(None),
            )
            self.stars_plot_item.setZValue(10)
            self.view.addItem(self.stars_plot_item)

    def _create_svg_visual(self):
        """Create the SVG path visual using PlotCurveItem."""
        # Get the morphed path
        morphed_path = morph(self.compiled_paths, self.morph_weights)

        # Parse the path and create curve segments
        self._update_svg_curves(morphed_path)

    def _apply_grey(self, color: tuple) -> tuple:
        """Apply grey factor to a color tuple."""
        if self.grey_factor <= 0:
            return color
        red, green, blue = color[0], color[1], color[2]
        grey = int((red + green + blue) / 3)
        new_r = int(red + (grey - red) * self.grey_factor)
        new_g = int(green + (grey - green) * self.grey_factor)
        new_b = int(blue + (grey - blue) * self.grey_factor)
        if len(color) > 3:
            return (new_r, new_g, new_b, color[3])
        return (new_r, new_g, new_b)

    def _apply_red_flash(self, color: tuple) -> tuple:
        """Apply red flash factor to a color tuple."""
        if self.red_flash_factor <= 0:
            return color
        red, green, blue = color[0], color[1], color[2]
        # Blend toward red (255, 50, 50)
        new_r = int(red + (255 - red) * self.red_flash_factor)
        new_g = int(green + (50 - green) * self.red_flash_factor)
        new_b = int(blue + (50 - blue) * self.red_flash_factor)
        if len(color) > 3:
            return (new_r, new_g, new_b, color[3])
        return (new_r, new_g, new_b)

    def _apply_distortion(self, x: float, y: float, point_index: int) -> Tuple[float, float]:
        """Apply distortion to a point based on current distortion amount.

        Uses a deterministic pseudo-random offset based on point index and seed
        so distortion is consistent within a frame but varies per point.
        """
        if self.distortion_amount <= 0:
            return x, y

        # Use sine/cosine with different frequencies per point for pseudo-random effect
        # The seed changes the phase, point_index changes the frequency
        seed_offset = self.distortion_seed * 0.1
        freq_x = 1.0 + (point_index % 7) * 0.3
        freq_y = 1.0 + (point_index % 5) * 0.4

        # Calculate offset using trigonometric functions for smooth, deterministic noise
        offset_x = math.sin(point_index * freq_x + seed_offset) * self.distortion_amount
        offset_y = math.cos(point_index * freq_y + seed_offset * 1.3) * self.distortion_amount

        # Add higher frequency component for more chaotic look
        offset_x += math.sin(point_index * 2.7 + seed_offset * 2) * self.distortion_amount * 0.5
        offset_y += math.cos(point_index * 3.1 + seed_offset * 2.5) * self.distortion_amount * 0.5

        return x + offset_x, y + offset_y

    def _apply_distortion_batch(
        self, x_points: np.ndarray, y_points: np.ndarray, start_index: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply distortion to arrays of points using vectorized numpy operations.

        Much faster than calling _apply_distortion for each point individually.
        """
        if self.distortion_amount <= 0:
            return x_points, y_points

        n_points = len(x_points)
        indices = np.arange(start_index, start_index + n_points)
        seed_offset = self.distortion_seed * 0.1

        # Vectorized frequency calculations
        freq_x = 1.0 + (indices % 7) * 0.3
        freq_y = 1.0 + (indices % 5) * 0.4

        # Vectorized distortion calculations
        offset_x = np.sin(indices * freq_x + seed_offset) * self.distortion_amount
        offset_y = np.cos(indices * freq_y + seed_offset * 1.3) * self.distortion_amount

        # Add higher frequency component
        offset_x += np.sin(indices * 2.7 + seed_offset * 2) * self.distortion_amount * 0.5
        offset_y += np.cos(indices * 3.1 + seed_offset * 2.5) * self.distortion_amount * 0.5

        return x_points + offset_x, y_points + offset_y

    def _trigger_damage_distortion(self):
        """Trigger a temporary distortion effect when the boss takes damage."""
        self.damage_distortion_active = True
        self.damage_distortion_timer = 0.0
        self.distortion_seed = random_manager.randint(0, 1000)

    def _update_damage_distortion(self, dt: float):
        """Update the damage distortion effect over time."""
        if not self.damage_distortion_active:
            return

        self.damage_distortion_timer += dt

        # Calculate distortion amount with smooth rise and fall
        progress = self.damage_distortion_timer / self.damage_distortion_duration
        if progress >= 1.0:
            # Distortion complete
            self.damage_distortion_active = False
            self.distortion_amount = 0.0
            self.damage_distortion_timer = 0.0
        else:
            # Use sine curve for smooth rise and fall (0 -> peak -> 0)
            self.distortion_amount = math.sin(progress * math.pi) * 12  # Max 12 pixels

    def _update_svg_curves(self, path_d: str):  # pylint: disable=too-many-locals
        """Update or create SVG curve visuals from path data."""
        # Parse path into segments
        segments = self._parse_path_to_segments(path_d)

        # Separate face segments (0, 1) from eye segment (2)
        face_segments = segments[:2] if len(segments) >= 2 else segments
        eye_segment = segments[2] if len(segments) > 2 else None

        # Animate layer offsets
        anim_time = self.active_time if "active" in self.phase else self.animation_time
        self.layer1_offset_x = 5 * math.sin(anim_time * 3.7)
        self.layer1_offset_y = 5 * math.cos(anim_time * 2.9)
        self.layer2_offset_x = 5 * math.sin(anim_time * 2.3 + 2)
        self.layer2_offset_y = 5 * math.cos(anim_time * 3.1 + 1)

        alpha = int(255 * self.svg_opacity)

        # Apply grey factor and red flash to colors
        color1 = self._apply_red_flash(self._apply_grey((255, 50, 100, alpha)))
        color2 = self._apply_red_flash(self._apply_grey((255, 255, 50, alpha)))
        color_main = self._apply_red_flash(self._apply_grey((100, 200, 255, alpha)))

        # Face layer configurations: (curve_list, color, z_value, offset_x, offset_y)
        face_layers = [
            (
                self.svg_curves_layer1,
                color1,
                3,
                self.layer1_offset_x,
                self.layer1_offset_y,
            ),
            (
                self.svg_curves_layer2,
                color2,
                4,
                self.layer2_offset_x,
                self.layer2_offset_y,
            ),
            (self.svg_curves, color_main, 5, 0, 0),  # Main layer on top
        ]

        # Update face curves
        stroke_width = int(self.current_stroke_width)
        for curve_list, color, z_value, offset_x, offset_y in face_layers:
            # Remove old curves if count changed
            while len(curve_list) > len(face_segments):
                curve = curve_list.pop()
                self.view.removeItem(curve)

            # Create or update curves using numpy for batch operations
            point_counter = 0
            for i, segment in enumerate(face_segments):
                if i >= len(curve_list):
                    curve = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=stroke_width))
                    curve.setZValue(z_value)
                    self.view.addItem(curve)
                    curve_list.append(curve)

                # Convert segment to numpy arrays for vectorized operations
                segment_arr = np.array(segment)
                px_arr = segment_arr[:, 0]
                py_arr = segment_arr[:, 1]

                # Vectorized transform
                x_points = self.boss_x + offset_x + (px_arr + self.svg_offset_x) * self.svg_scale
                y_points = self.boss_y + offset_y + (-py_arr - self.svg_offset_y) * self.svg_scale

                # Apply death Y-scale (collapse toward center Y)
                y_points = self.boss_y + (y_points - self.boss_y) * self.death_y_scale

                # Apply batch distortion
                x_points, y_points = self._apply_distortion_batch(x_points, y_points, point_counter)
                point_counter += len(segment)

                curve_list[i].setData(x=x_points, y=y_points)
                curve_list[i].setPen(pg.mkPen(color=color, width=stroke_width))

        # Update eye if present (skip during death animation - eyes are removed)
        if eye_segment and self.phase != "death_animation":
            self._update_eye_curves(eye_segment, alpha)

    def _update_eye_curves(  # pylint: disable=too-many-locals
        self, eye_segment: List[Tuple[float, float]], alpha: int
    ):
        """Update eye curves separately with glow effect."""
        # Calculate eye glow color - transitions from red to white when glowing
        glow_factor = self.eye_glow
        eye_r = 255
        eye_g = int(50 + 205 * glow_factor)  # 50 -> 255
        eye_b = int(50 + 205 * glow_factor)  # 50 -> 255
        eye_width = 3 + int(3 * glow_factor)  # Thicker when glowing

        # Calculate Y scale for blink animation (1.0 = normal, 0.1 = closed)
        # Use eye_blink (damage only) not glow_factor (color pulse)
        eye_y_scale = 1.0 - 0.9 * self.eye_blink  # 1.0 -> 0.1 -> 1.0

        # Eye layer configurations
        eye_layers = [
            (
                self.eye_curves_layer1,
                (255, 50, 100, alpha),
                6,
                self.layer1_offset_x,
                self.layer1_offset_y,
            ),
            (
                self.eye_curves_layer2,
                (255, 255, 50, alpha),
                7,
                self.layer2_offset_x,
                self.layer2_offset_y,
            ),
            (self.eye_curves, (eye_r, eye_g, eye_b, alpha), 8, 0, 0),  # Main eye on top
        ]

        # Convert eye segment to numpy array once
        eye_arr = np.array(eye_segment)
        px_arr = eye_arr[:, 0]
        py_arr = eye_arr[:, 1]

        # Calculate eye center Y for scaling reference (vectorized)
        ty_base = self.boss_y + (-py_arr - self.svg_offset_y) * self.svg_scale
        eye_center_y = np.mean(ty_base)

        for curve_list, color, z_value, offset_x, offset_y in eye_layers:
            # Ensure we have exactly one curve for the eye
            while len(curve_list) > 1:
                curve = curve_list.pop()
                self.view.removeItem(curve)

            if len(curve_list) == 0:
                curve = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=eye_width))
                curve.setZValue(z_value)
                self.view.addItem(curve)
                curve_list.append(curve)

            # Vectorized transform
            x_points = self.boss_x + offset_x + (px_arr + self.svg_offset_x) * self.svg_scale
            y_points = self.boss_y + offset_y + (-py_arr - self.svg_offset_y) * self.svg_scale

            # Apply Y scale around center for blink animation
            y_points = eye_center_y + (y_points - eye_center_y) * eye_y_scale

            # Apply death Y-scale (collapse toward center Y)
            y_points = self.boss_y + (y_points - self.boss_y) * self.death_y_scale

            # Apply batch distortion
            point_counter = 1000  # Start at offset to differentiate from face points
            x_points, y_points = self._apply_distortion_batch(x_points, y_points, point_counter)

            curve_list[0].setData(x=x_points, y=y_points)
            curve_list[0].setPen(pg.mkPen(color=color, width=eye_width))

            # Track eye center (only on main layer)
            if offset_x == 0 and offset_y == 0:
                self.eye_center = (float(np.mean(x_points)), float(np.mean(y_points)))

        # Update eye fill
        self._update_eye_fill(eye_segment, alpha)

    def _update_eye_fill(self, eye_segment: List[Tuple[float, float]], alpha: int):
        """Update the filled eye shape."""
        # Calculate fill opacity based on glow
        fill_alpha = int(alpha * (0.3 + 0.7 * self.eye_glow))  # 30% base, up to 100% when glowing

        # Fill color - red base, brighter when glowing
        glow_factor = self.eye_glow
        fill_r = 255
        fill_g = int(30 + 100 * glow_factor)
        fill_b = int(30 + 100 * glow_factor)

        # Calculate Y scale for blink animation (same as curves)
        eye_y_scale = 1.0 - 0.9 * self.eye_blink

        # Convert to numpy for vectorized operations
        eye_arr = np.array(eye_segment)
        px_arr = eye_arr[:, 0]
        py_arr = eye_arr[:, 1]

        # Calculate eye center Y for scaling reference (vectorized)
        ty_base = self.boss_y + (-py_arr - self.svg_offset_y) * self.svg_scale
        eye_center_y = np.mean(ty_base)

        # Vectorized transform
        x_points = self.boss_x + (px_arr + self.svg_offset_x) * self.svg_scale
        y_points = self.boss_y + (-py_arr - self.svg_offset_y) * self.svg_scale

        # Apply Y scale around center for blink animation
        y_points = eye_center_y + (y_points - eye_center_y) * eye_y_scale

        # Apply death Y-scale (collapse toward center Y)
        y_points = self.boss_y + (y_points - self.boss_y) * self.death_y_scale

        # Apply batch distortion
        x_points, y_points = self._apply_distortion_batch(x_points, y_points, 2000)

        # Close the polygon
        x_points = np.append(x_points, x_points[0])
        y_points = np.append(y_points, y_points[0])

        # Create or update the fill
        if self.eye_fill is None:
            self.eye_fill = pg.PlotDataItem(
                x=x_points,
                y=y_points,
                pen=pg.mkPen(None),
                brush=pg.mkBrush(fill_r, fill_g, fill_b, fill_alpha),
                fillLevel=0,
            )
            self.eye_fill.setZValue(2)  # Below the outlines
            self.view.addItem(self.eye_fill)
        else:
            self.eye_fill.setData(x=x_points, y=y_points)
            self.eye_fill.setBrush(pg.mkBrush(fill_r, fill_g, fill_b, fill_alpha))

    def _create_face2_visuals(self):
        """Create visual elements for the second face (phase 2)."""
        # Face 2 curves will be created dynamically on first update
        # Initialize morphed path and update face 2 curves
        morphed_path = morph(self.compiled_paths, self.face2_morph_weights)
        self._update_face2_curves(morphed_path)

    def _update_face2_curves(self, path_d: str):  # pylint: disable=too-many-locals
        """Update face 2 curves (for phase 2)."""
        segments = self._parse_path_to_segments(path_d)
        face_segments = segments[:2] if len(segments) >= 2 else segments
        eye_segment = segments[2] if len(segments) > 2 else None

        alpha = int(255 * self.svg_opacity)

        # Apply grey factor and red flash to colors
        color1 = self._apply_red_flash(self._apply_grey((255, 50, 100, alpha)))
        color2 = self._apply_red_flash(self._apply_grey((255, 255, 50, alpha)))
        color_main = self._apply_red_flash(self._apply_grey((100, 200, 255, alpha)))

        # Face 2 layer configurations
        face_layers = [
            (self.face2_curves_layer1, color1, 13, self.layer1_offset_x, self.layer1_offset_y),
            (self.face2_curves_layer2, color2, 14, self.layer2_offset_x, self.layer2_offset_y),
            (self.face2_curves, color_main, 15, 0, 0),
        ]

        stroke_width = int(self.current_stroke_width)
        for curve_list, color, z_value, offset_x, offset_y in face_layers:
            while len(curve_list) > len(face_segments):
                curve = curve_list.pop()
                self.view.removeItem(curve)

            # Create or update curves using numpy for batch operations
            point_counter = 3000  # Offset for face2 distortion
            for i, segment in enumerate(face_segments):
                if i >= len(curve_list):
                    curve = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=stroke_width))
                    curve.setZValue(z_value)
                    self.view.addItem(curve)
                    curve_list.append(curve)

                # Convert segment to numpy arrays for vectorized operations
                segment_arr = np.array(segment)
                px_arr = segment_arr[:, 0]
                py_arr = segment_arr[:, 1]

                # Vectorized transform
                x_points = self.face2_x + offset_x + (px_arr + self.svg_offset_x) * self.face2_scale
                y_points = (
                    self.face2_y + offset_y + (-py_arr - self.svg_offset_y) * self.face2_scale
                )

                # Apply death Y-scale (collapse toward center Y)
                y_points = self.face2_y + (y_points - self.face2_y) * self.death_y_scale

                # Apply batch distortion
                x_points, y_points = self._apply_distortion_batch(x_points, y_points, point_counter)
                point_counter += len(segment)

                curve_list[i].setData(x=x_points, y=y_points)
                curve_list[i].setPen(pg.mkPen(color=color, width=stroke_width))

        # Update eye if present (skip during death animation - eyes are removed)
        if eye_segment and self.phase != "death_animation":
            self._update_face2_eye_curves(eye_segment, alpha)

    def _update_face2_eye_curves(  # pylint: disable=too-many-locals
        self, eye_segment: List[Tuple[float, float]], alpha: int
    ):
        """Update eye curves for face 2."""
        glow_factor = self.face2_eye_glow
        eye_r = 255
        eye_g = int(50 + 205 * glow_factor)
        eye_b = int(50 + 205 * glow_factor)
        eye_width = 3 + int(3 * glow_factor)

        # No blink animation for face2 (blink is damage-only on main face)
        eye_y_scale = 1.0

        # Apply grey
        eye_color = self._apply_grey((eye_r, eye_g, eye_b, alpha))

        eye_layers = [
            (
                self.face2_eye_curves_layer1,
                self._apply_grey((255, 50, 100, alpha)),
                16,
                self.layer1_offset_x,
                self.layer1_offset_y,
            ),
            (
                self.face2_eye_curves_layer2,
                self._apply_grey((255, 255, 50, alpha)),
                17,
                self.layer2_offset_x,
                self.layer2_offset_y,
            ),
            (self.face2_eye_curves, eye_color, 18, 0, 0),
        ]

        # Convert eye segment to numpy array once
        eye_arr = np.array(eye_segment)
        px_arr = eye_arr[:, 0]
        py_arr = eye_arr[:, 1]

        # Calculate eye center Y for scaling reference (vectorized)
        ty_base = self.face2_y + (-py_arr - self.svg_offset_y) * self.face2_scale
        eye_center_y = np.mean(ty_base)

        for curve_list, color, z_value, offset_x, offset_y in eye_layers:
            while len(curve_list) > 1:
                curve = curve_list.pop()
                self.view.removeItem(curve)

            if len(curve_list) == 0:
                curve = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=eye_width))
                curve.setZValue(z_value)
                self.view.addItem(curve)
                curve_list.append(curve)

            # Vectorized transform
            x_points = self.face2_x + offset_x + (px_arr + self.svg_offset_x) * self.face2_scale
            y_points = self.face2_y + offset_y + (-py_arr - self.svg_offset_y) * self.face2_scale

            # Apply Y scale around center for blink animation
            y_points = eye_center_y + (y_points - eye_center_y) * eye_y_scale

            # Apply death Y-scale (collapse toward center Y)
            y_points = self.face2_y + (y_points - self.face2_y) * self.death_y_scale

            # Apply batch distortion
            x_points, y_points = self._apply_distortion_batch(x_points, y_points, 4000)

            curve_list[0].setData(x=x_points, y=y_points)
            curve_list[0].setPen(pg.mkPen(color=color, width=eye_width))

            # Track eye center (only on main layer)
            if offset_x == 0 and offset_y == 0:
                self.face2_eye_center = (float(np.mean(x_points)), float(np.mean(y_points)))

        self._update_face2_eye_fill(eye_segment, alpha)

    def _update_face2_eye_fill(self, eye_segment: List[Tuple[float, float]], alpha: int):
        """Update the filled eye shape for face 2."""
        fill_alpha = int(alpha * (0.3 + 0.7 * self.face2_eye_glow))
        glow_factor = self.face2_eye_glow
        fill_r = 255
        fill_g = int(30 + 100 * glow_factor)
        fill_b = int(30 + 100 * glow_factor)

        # No blink animation for face2 (blink is damage-only on main face)
        eye_y_scale = 1.0

        # Apply grey
        fill_color = self._apply_grey((fill_r, fill_g, fill_b))
        fill_r, fill_g, fill_b = fill_color[0], fill_color[1], fill_color[2]

        # Convert to numpy for vectorized operations
        eye_arr = np.array(eye_segment)
        px_arr = eye_arr[:, 0]
        py_arr = eye_arr[:, 1]

        # Calculate eye center Y for scaling reference (vectorized)
        ty_base = self.face2_y + (-py_arr - self.svg_offset_y) * self.face2_scale
        eye_center_y = np.mean(ty_base)

        # Vectorized transform
        x_points = self.face2_x + (px_arr + self.svg_offset_x) * self.face2_scale
        y_points = self.face2_y + (-py_arr - self.svg_offset_y) * self.face2_scale

        # Apply Y scale around center for blink animation
        y_points = eye_center_y + (y_points - eye_center_y) * eye_y_scale

        # Apply death Y-scale (collapse toward center Y)
        y_points = self.face2_y + (y_points - self.face2_y) * self.death_y_scale

        # Apply batch distortion
        x_points, y_points = self._apply_distortion_batch(x_points, y_points, 5000)

        # Close the polygon
        x_points = np.append(x_points, x_points[0])
        y_points = np.append(y_points, y_points[0])

        if self.face2_eye_fill is None:
            self.face2_eye_fill = pg.PlotDataItem(
                x=x_points,
                y=y_points,
                pen=pg.mkPen(None),
                brush=pg.mkBrush(fill_r, fill_g, fill_b, fill_alpha),
                fillLevel=0,
            )
            self.face2_eye_fill.setZValue(12)
            self.view.addItem(self.face2_eye_fill)
        else:
            self.face2_eye_fill.setData(x=x_points, y=y_points)
            self.face2_eye_fill.setBrush(pg.mkBrush(fill_r, fill_g, fill_b, fill_alpha))

    def _parse_path_to_segments(self, path_d: str) -> List[List[Tuple[float, float]]]:
        """Parse SVG path into drawable segments with bezier interpolation."""
        segments = []
        current_segment = []
        current_x, current_y = 0, 0

        # Split path into commands
        commands = re.findall(r"([MLCZ])\s*([^MLCZ]*)", path_d)

        for cmd, args in commands:
            if cmd == "Z":
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []
                continue

            # Parse numbers
            numbers = [float(n) for n in re.findall(r"-?[\d.]+", args)]

            if cmd == "M":
                if current_segment:
                    segments.append(current_segment)
                current_x, current_y = numbers[0], numbers[1]
                current_segment = [(current_x, current_y)]

            elif cmd == "C":
                # Cubic bezier: C x1 y1, x2 y2, x y
                for idx in range(0, len(numbers), 6):
                    if idx + 5 < len(numbers):
                        ctrl1_x, ctrl1_y = numbers[idx], numbers[idx + 1]
                        ctrl2_x, ctrl2_y = numbers[idx + 2], numbers[idx + 3]
                        end_x, end_y = numbers[idx + 4], numbers[idx + 5]

                        # Interpolate bezier curve
                        bezier_points = self._interpolate_bezier(
                            current_x,
                            current_y,
                            ctrl1_x,
                            ctrl1_y,
                            ctrl2_x,
                            ctrl2_y,
                            end_x,
                            end_y,
                            steps=10,
                        )
                        current_segment.extend(bezier_points[1:])  # Skip first (duplicate)
                        current_x, current_y = end_x, end_y

        if current_segment:
            segments.append(current_segment)

        return segments

    def _interpolate_bezier(
        self,
        start_x,
        start_y,
        ctrl1_x,
        ctrl1_y,
        ctrl2_x,
        ctrl2_y,
        end_x,
        end_y,
        steps=10,
    ) -> List[Tuple[float, float]]:
        """Interpolate a cubic bezier curve."""
        points = []
        for step in range(steps + 1):
            param = step / steps
            param2 = param * param
            param3 = param2 * param
            inv_param = 1 - param
            inv_param2 = inv_param * inv_param
            inv_param3 = inv_param2 * inv_param

            px = (
                inv_param3 * start_x
                + 3 * inv_param2 * param * ctrl1_x
                + 3 * inv_param * param2 * ctrl2_x
                + param3 * end_x
            )
            py = (
                inv_param3 * start_y
                + 3 * inv_param2 * param * ctrl1_y
                + 3 * inv_param * param2 * ctrl2_y
                + param3 * end_y
            )
            points.append((px, py))
        return points

    def update(self, dt: float):
        """Update boss state and animations."""
        # Allow death animation to continue even when defeated
        if self.phase == "death_animation":
            self._update_death_animation(dt)
            self._update_trail()
            return

        if self.completed or self.defeated:
            return

        self.animation_time += dt

        if self.phase == "stars_entering":
            self._update_stars(dt)

            # Check if all stars have arrived
            all_arrived = all(star["arrived"] for star in self.stars)
            if all_arrived or self.animation_time > self.stars_duration + 0.5:
                self.phase = "constellation_forming"
                self.animation_time = 0.0
                self.constellation_line_progress = 0.0
                self._create_constellation_lines()

        elif self.phase == "constellation_forming":
            self._update_constellation_forming(dt)

        elif self.phase == "constellation_glow":
            self._update_constellation_glow(dt)

        elif self.phase == "svg_fading_in":
            # Fade in the SVG
            progress = min(1.0, self.animation_time / self.fade_duration)
            self.svg_opacity = progress

            # Update SVG visual with new opacity
            morphed_path = morph(self.compiled_paths, self.morph_weights)
            self._update_svg_curves(morphed_path)

            # Fade out stars 3x faster than face fades in (with noise)
            star_alpha = int(255 * max(0, 1 - progress * 3))
            if self.stars_plot_item and self.stars:
                positions = []
                for star in self.stars:
                    noise_x = math.sin(self.animation_time * 5 + star["target_x"]) * 3
                    noise_y = math.cos(self.animation_time * 4 + star["target_y"]) * 3
                    positions.append((star["target_x"] + noise_x, star["target_y"] + noise_y))
                self.stars_plot_item.setBrush(pg.mkBrush(100, 200, 255, star_alpha))
                self.stars_plot_item.setData(pos=positions, size=self.star_base_size)

            if progress >= 1.0:
                self.phase = "phase1_active"
                self.animation_time = 0.0
                # Remove stars plot item
                if self.stars_plot_item and self.stars_plot_item.scene():
                    self.view.removeItem(self.stars_plot_item)
                self.stars_plot_item = None
                self.stars.clear()
                # Start word attack sequence for phase 1
                self._start_word_sequence()

        elif self.phase == "phase1_active":
            self._update_phase1(dt)

        elif self.phase == "transition_to_center":
            self._update_transition_to_center(dt)

        elif self.phase == "transition_flash":
            self._update_transition_flash(dt)

        elif self.phase == "transition_split":
            self._update_transition_split(dt)

        elif self.phase == "phase2_active":
            self._update_phase2(dt)

        # Update trail effect (render current frame and fade)
        if self.phase in (
            "svg_fading_in",
            "phase1_active",
            "transition_to_center",
            "transition_flash",
            "transition_split",
            "phase2_active",
        ):
            self._update_trail()

    def _update_phase1(self, dt: float):
        """Update phase 1 - single face oscillating on arc."""
        self.active_time += dt

        # Animate position along arc (oscillate back and forth)
        self.arc_angle = math.pi / 2 + math.sin(self.active_time * self.arc_speed) * (
            math.pi / 3
        )  # Swing 60 degrees each way
        self.boss_x = self.arc_center_x + self.arc_radius * math.cos(self.arc_angle)
        self.boss_y = self.arc_center_y + self.arc_radius * math.sin(self.arc_angle)
        self.center_pos = (self.boss_x, self.boss_y)

        # Calculate target morph weights based on horizontal position
        # When boss is on right side (positive x), look bottom-left (left_down)
        # When boss is on left side (negative x), look bottom-right (right_down)
        # Weights: [left_up, right_up, left_down, right_down]
        position_ratio = self.boss_x / self.arc_radius  # -1 to 1
        position_ratio = max(-1.0, min(1.0, position_ratio))  # Clamp

        # Interpolate between right_down (when left) and left_down (when right)
        left_down_weight = (position_ratio + 1) / 2  # 0 when left, 1 when right
        right_down_weight = 1 - left_down_weight  # 1 when left, 0 when right

        target_weights = [
            0.0,  # left_up
            0.0,  # right_up
            left_down_weight,  # left_down (looking left, used when on right)
            right_down_weight,  # right_down (looking right, used when on left)
        ]

        # Smoothly interpolate current weights towards target weights
        lerp_factor = min(1.0, self.morph_lerp_speed * dt)
        for i in range(4):
            self.morph_weights[i] += (target_weights[i] - self.morph_weights[i]) * lerp_factor

        # Update eye glow animation
        self._update_eye_glow(dt)

        # Update SVG
        morphed_path = morph(self.compiled_paths, self.morph_weights)
        self._update_svg_curves(morphed_path)

        # Update word completion animation
        self._update_word_complete_animation(dt)

        # Update red flash animation
        self._update_red_flash(dt)

        # Update word attack system
        self._update_word_display(dt)
        self._update_charge_particles(dt)
        self._update_projectiles(dt)
        self._update_firing_attack(dt)
        self._update_sequence_cooldown(dt)

        # Update disable cone effect
        self._update_disable_cone(dt)

        # Update exiting cones (finishing their exit animations)
        self._update_exiting_cones(dt)

        # Check for word timeout
        if self.word_active and self.word_timer >= self.word_timeout:
            self._word_timeout_attack()

    def _start_word_sequence(self):
        """Start a new 4-letter word attack sequence."""
        # Clean up any existing word display
        self._cleanup_word_display()

        # Generate new 4-letter word
        self.word_sequence = "".join(random_manager.choice(ALL_BUTTONS) for _ in range(4))
        self.word_typed_count = 0
        self.word_timer = 0.0
        self.word_active = True
        self.mouth_charging = True
        self.mouth_charge_progress = 0.0

        # Position letters above the eye
        self.word_base_y = self.eye_center[1] - 50

        # Determine slide direction based on boss X position
        # Boss on left side: slide in from left, out to right
        # Boss on right side: slide in from right, out to left
        self.word_slide_from_left = self.boss_x < 0
        off_screen_x = -800 if self.word_slide_from_left else 800

        # Create FaceBossLetter instances for each letter
        for _, letter in enumerate(self.word_sequence):
            # All letters start off-screen
            letter_enemy = FaceBossLetter(
                letter,
                (off_screen_x, self.word_base_y),
                self.view,
                self.laser_manager,
                self.waveform,
            )
            letter_enemy.target_y = self.word_base_y
            self.word_letters.append(letter_enemy)

        # Start charge particles
        self._spawn_charge_particles()

    def _update_word_display(self, dt: float):
        """Update word letter positions and animations."""
        if not self.word_active and not self.word_letters:
            return

        # Update timer
        if self.word_active:
            self.word_timer += dt

        # Update charge progress
        if self.mouth_charging:
            self.mouth_charge_progress = min(1.0, self.word_timer / self.word_timeout)

        # Update base Y to follow eye
        self.word_base_y = self.eye_center[1] - 50

        # Track letters to clean up after iteration
        letters_to_cleanup = []

        # Update each letter enemy
        for idx, letter_enemy in enumerate(self.word_letters):
            # Set target position based on state (only for non-fading, non-completed letters)
            if not letter_enemy.fading_out and not letter_enemy.completed:
                if idx < self.word_typed_count:
                    # Already typed but not yet fading - shouldn't happen normally
                    pass
                elif idx == self.word_typed_count:
                    # Active letter - move to eye center
                    letter_enemy.set_target_position(self.eye_center[0], self.word_base_y)
                else:
                    # Future letter - stay off-screen on the slide-in side
                    off_screen_x = -800 if self.word_slide_from_left else 800
                    letter_enemy.set_target_position(off_screen_x, self.word_base_y)

            # Update the letter enemy (including fading and completed letters for animation cleanup)
            letter_enemy.update(dt)

            # Mark for cleanup if completed and all animations finished
            # Only cleanup after word is no longer active to preserve list indices during typing
            if not self.word_active and letter_enemy.completed and not letter_enemy.animations:
                letters_to_cleanup.append(letter_enemy)

        # Clean up completed letters with no remaining animations
        for letter_enemy in letters_to_cleanup:
            letter_enemy.cleanup()
            self.word_letters.remove(letter_enemy)

    def _type_word_letter(self, button: str) -> bool:
        """Handle typing a letter in the word sequence."""
        if not self.word_active or self.word_typed_count >= len(self.word_sequence):
            return False

        if self.word_sequence[self.word_typed_count] != button:
            return False

        # Get the current letter enemy
        current_letter = self.word_letters[self.word_typed_count]

        # Get position before typing
        letter_pos = current_letter.get_center_position()

        # Use the letter enemy's type_button to trigger proper effects (laser, animations)
        current_letter.type_button(button)

        # Get letter color for explosion
        letter = self.word_sequence[self.word_typed_count]
        color = BUTTON_COLORS.get(letter, "#FFFFFF")
        color_rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

        self.game_engine.explosion_manager.create_explosion(
            letter_pos,
            color_rgb,
            "enhanced",
            0.6,  # Smaller scale for single letters
        )
        self.game_engine.sound_manager.play_explosion_sound(volume=0.3)

        # Start slide out animation (opposite direction from slide in)
        slide_out_velocity = 200 if self.word_slide_from_left else -200
        current_letter.start_slide_out(slide_out_velocity)

        self.word_typed_count += 1

        # Check if word complete
        if self.word_typed_count >= len(self.word_sequence):
            self._word_completed()

        return True

    def _word_completed(self):
        """Handle successful word completion - track progress and maybe trigger phase 2."""
        self.word_active = False
        self.mouth_charging = False
        # Don't cleanup word_letters immediately - let them fade out and clean up naturally
        # in _update_word_display when their animations complete
        # Let particles complete their animation to the mouth
        self.charge_particles.start_completing()

        self.words_completed += 1

        # Trigger red flash animation
        self.red_flash_active = True
        self.red_flash_timer = 0.0
        self.red_flash_factor = 1.0

        # Trigger screen shake
        self.game_engine.shake_manager.medium_shake()

        # Start word completion animation (stroke width + face morph)
        self.word_complete_animating = True
        self.word_complete_timer = 0.0

        # Check if enough words completed to trigger phase 2
        if self.words_completed >= self.words_to_phase2:
            # Phase 2 will be triggered after animation completes
            pass
        else:
            # Cooldown will be set after animation completes
            pass

    def _update_red_flash(self, dt: float):
        """Update red flash animation."""
        if not self.red_flash_active:
            return

        self.red_flash_timer += dt
        progress = self.red_flash_timer / self.red_flash_duration

        if progress >= 1.0:
            # Flash complete
            self.red_flash_active = False
            self.red_flash_factor = 0.0
            return

        # Fade from full red back to normal (1 -> 0)
        self.red_flash_factor = 1.0 - progress

    def _update_red_pulse(self, _dt: float):
        """Update red pulse animation for phase 2 transition."""
        if not self.red_pulse_active:
            self.red_flash_factor = max(0.0, self.red_flash_factor)
            return

        # Pulse between 0.3 and 0.8 red factor at ~2Hz
        pulse = 0.55 + 0.25 * math.sin(self.phase2_transition_timer * 4 * math.pi)
        self.red_flash_factor = pulse

    def _update_word_complete_animation(self, dt: float):
        """Update the word completion animation - stroke width pulse and face morph."""
        if not self.word_complete_animating:
            return

        self.word_complete_timer += dt
        progress = self.word_complete_timer / self.word_complete_duration

        if progress >= 1.0:
            # Animation complete
            self.word_complete_animating = False
            self.current_stroke_width = self.base_stroke_width

            # Now trigger phase 2 or cooldown
            if self.words_completed >= self.words_to_phase2:
                self.start_phase2_transition()
            else:
                self.sequence_cooldown = self.sequence_cooldown_duration
            return

        # Stroke width animation: pulse up to 4 and back to 3
        # Use sine curve for smooth in-out
        stroke_pulse = math.sin(progress * math.pi)
        self.current_stroke_width = self.base_stroke_width + stroke_pulse

        # Face morph animation: move halfway up and back
        # First half: morph toward up position, second half: morph back
        if progress < 0.5:
            # Moving up (0 to 0.5 progress -> 0 to 1 morph)
            morph_progress = progress * 2
        else:
            # Moving back (0.5 to 1 progress -> 1 to 0 morph)
            morph_progress = (1.0 - progress) * 2

        # Ease the morph with sine
        morph_factor = math.sin(morph_progress * math.pi / 2)

        # Adjust morph weights toward "up" poses
        # Current weights interpolate toward up poses
        target_up = [0.5, 0.5, 0.0, 0.0]  # left_up and right_up
        current_base = [0.25, 0.25, 0.25, 0.25]  # neutral

        for i in range(4):
            self.morph_weights[i] = (
                current_base[i] + (target_up[i] - current_base[i]) * morph_factor * 0.5
            )

    def _word_timeout_attack(self):
        """Handle word timeout - start firing projectiles."""
        self.word_active = False
        self.mouth_charging = False
        self.firing_projectiles = True
        self.fire_timer = 0.0
        self.fire_last_shot = 0.0

        # Fade out remaining word letters
        for letter_enemy in self.word_letters:
            if not letter_enemy.fading_out:
                letter_enemy.start_slide_out(-150)

        # Let particles continue animating during firing - they will be cleaned up
        # when they reach the mouth or when firing ends

        # Create fire cone effect
        self._create_fire_cone()

    def _complete_charge_particles(self):
        """Start completing charge particles - they will animate to mouth and be removed."""
        self.charge_particles.start_completing()

    def _create_fire_cone(self):
        """Create a translucent cone with animated waveform edges."""
        # If there's an existing cone, start its exit animation
        if self.fire_cone:
            self.fire_cone.start_exit()
            self.exiting_cones.append(self.fire_cone)

        self._calculate_mouth_center()

        # Fire cone color (orange)
        fire_color = (255, 100, 50)

        # Create cone using new ConeEffect class
        self.fire_cone = ConeEffect(
            view=self.view,
            source=self.mouth_center,
            target_y=-280,
            target_width=80,
            color=fire_color,
            num_interior=self.fire_cone_num_interior,
            opacity_mult=3.0,
            width_mult=3.0,
            waveform=self.waveform,
        )

        # Initial update to set positions
        self._update_fire_cone()
        self.game_engine.sound_manager.play_fire_cone_sound()

    def _update_fire_cone(self, dt: float = 0.016):
        """Update fire cone with animated waveform edges."""
        if not self.fire_cone:
            return

        self._calculate_mouth_center()

        # Update source position to follow mouth
        self.fire_cone.set_source(self.mouth_center)

        # Update cone animation
        self.fire_cone.update(dt, self.fire_timer)

    def _cleanup_fire_cone(self, immediate: bool = False):
        """Start fire cone exit animation or immediately cleanup.

        Args:
            immediate: If True, skip exit animation and cleanup immediately.
        """
        if self.fire_cone:
            if immediate:
                self.fire_cone.cleanup()
            else:
                self.fire_cone.start_exit()
                self.exiting_cones.append(self.fire_cone)
            self.fire_cone = None

    def _create_disable_cone(self):
        """Create a grey disable cone from eye to player waveform width."""
        # If there's an existing cone, start its exit animation
        if self.disable_cone:
            self.disable_cone.start_exit()
            self.exiting_cones.append(self.disable_cone)

        # Grey color for disable effect
        disable_color = (128, 128, 128)

        # Player waveform spans roughly -400 to 400, so half-width is ~400
        # Use 350 to leave some margin
        player_waveform_width = 350

        self.disable_cone = ConeEffect(
            view=self.view,
            source=self.eye_center,
            target_y=-280,
            target_width=player_waveform_width,
            color=disable_color,
            num_interior=self.disable_cone_num_interior,
            opacity_mult=2.5,  # Higher opacity for disable cone visibility
            width_mult=3.0,  # Thicker rays for disable cone
            waveform=self.waveform,
        )
        self.disable_cone_active = True
        self.disable_cone_timer = 0.0
        self.game_engine.sound_manager.play_disable_cone_sound()

    def _update_disable_cone(self, dt: float):
        """Update disable cone animation."""
        if not self.disable_cone:
            return

        # Check if player waveform is still disabled - sync cone with waveform state
        if self.disable_cone_active and self.waveform and self.waveform.disabled_flash_timer <= 0:
            self._cleanup_disable_cone()
            # End yellow flash on word letters - animate back to normal
            for letter_enemy in self.word_letters:
                letter_enemy.end_yellow_flash()
            return

        self.disable_cone_timer += dt

        # Update source position to follow eye
        self.disable_cone.set_source(self.eye_center)

        # Update cone animation
        self.disable_cone.update(dt, self.disable_cone_timer)

    def _cleanup_disable_cone(self, immediate: bool = False):
        """Start disable cone exit animation or immediately cleanup.

        Args:
            immediate: If True, skip exit animation and cleanup immediately.
        """
        if self.disable_cone:
            if immediate:
                self.disable_cone.cleanup()
            else:
                self.disable_cone.start_exit()
                self.exiting_cones.append(self.disable_cone)
            self.disable_cone = None
        self.disable_cone_active = False

    def _update_exiting_cones(self, dt: float):
        """Update all exiting cones and clean up completed ones."""
        completed = []
        for cone in self.exiting_cones:
            if cone.is_done():
                cone.cleanup()
                completed.append(cone)
            else:
                cone.update(dt, 0.0)

        for cone in completed:
            self.exiting_cones.remove(cone)

    def _trigger_word_miss_punishment(self):
        """Trigger punishment when player misses a letter during phase 1 word attack.

        This includes:
        - Disabling player waveform for 1 second
        - Eye blink animation
        - Grey cone from eye to player waveform
        - Yellow flash on word letters
        """
        # Clean up any existing disable cone first
        self._cleanup_disable_cone()

        # Disable player waveform for 1 second
        if self.waveform:
            self.waveform.trigger_disabled_flash(duration=1.0)

        # Trigger yellow flash on all word letters
        for letter_enemy in self.word_letters:
            letter_enemy.start_yellow_flash()

        # Trigger eye blink animation (Y-scaling only, not color pulse)
        self.eye_blinking = True
        self.eye_blink_timer = 0.0

        # Create disable cone from eye
        self._create_disable_cone()

    def _cleanup_word_display(self):
        """Remove all word letter enemies."""
        for letter_enemy in self.word_letters:
            letter_enemy.cleanup()
        self.word_letters.clear()

    def _calculate_mouth_center(self):
        """Calculate the center of the mouth from the SVG curves."""
        # Mouth is segment 1 (index 1) of face segments
        if len(self.svg_curves) > 1:
            curve = self.svg_curves[1]
            data = curve.getData()
            if data[0] is not None and len(data[0]) > 0:
                x_data, y_data = data
                center_x = sum(x_data) / len(x_data)
                center_y = sum(y_data) / len(y_data)
                self.mouth_center = (center_x, center_y)
                return
        # Fallback - approximate mouth position based on boss position
        self.mouth_center = (self.boss_x, self.boss_y - 30)

    def _get_phase2_mouth_center(self, face: str) -> tuple:
        """Calculate mouth center for a phase 2 face from its SVG curves."""
        if face == "left":
            curves = self.svg_curves
            corner_x, corner_y = self.corner_left
        else:
            curves = self.face2_curves
            corner_x, corner_y = self.corner_right

        # Mouth is segment 1 (index 1) of face segments
        if len(curves) > 1:
            curve = curves[1]
            data = curve.getData()
            if data[0] is not None and len(data[0]) > 0:
                x_data, y_data = data
                center_x = sum(x_data) / len(x_data)
                center_y = sum(y_data) / len(y_data)
                return (center_x, center_y)

        # Fallback - approximate mouth position based on corner/eye position
        # Mouth is below the eye (corner position) by about 60 units at phase2 scale
        return (corner_x, corner_y - 60)

    def _spawn_charge_particles(self):
        """Spawn particles that will be sucked into the mouth."""
        self._calculate_mouth_center()
        self.charge_particles.set_target(self.mouth_center[0], self.mouth_center[1])
        self.charge_particles.spawn_all(delay_range=(0, 1.0))

    def _update_charge_particles(self, dt: float):
        """Update charge particles - animate toward mouth center."""
        # Continue animating during charging, firing, or completing phases
        if (
            not self.mouth_charging
            and not self.firing_projectiles
            and not self.charge_particles.completing
        ):
            return

        if self.charge_particles.is_empty():
            return

        self._calculate_mouth_center()
        self.charge_particles.set_target(self.mouth_center[0], self.mouth_center[1])

        # Calculate speed based on state
        if self.firing_projectiles or self.charge_particles.completing:
            speed = 200  # Fast finish during firing or completing
        else:
            speed = 50 + 150 * self.mouth_charge_progress  # Speed increases with charge

        # Alpha multiplier based on charge progress
        alpha_multiplier = 0.75 + 0.5 * self.mouth_charge_progress

        self.charge_particles.update(dt, speed=speed, alpha_multiplier=alpha_multiplier)

    def _cleanup_charge_particles(self):
        """Remove all charge particles."""
        self.charge_particles.clear()

    def _spawn_phase2_charge_particles(self, face: str):
        """Spawn particles that will be sucked into the face's mouth during charge."""
        mouth_x, mouth_y = self._get_phase2_mouth_center(face)
        if face == "left":
            particles = self.phase2_left_charge_particles
        else:
            particles = self.phase2_right_charge_particles

        particles.set_target(mouth_x, mouth_y)
        particles.spawn_all(delay_range=(0, 0.5))

    def _update_phase2_charge_particles(self, face: str, dt: float):
        """Update charge particles for a face - animate toward mouth center."""
        mouth_x, mouth_y = self._get_phase2_mouth_center(face)
        if face == "left":
            particles = self.phase2_left_charge_particles
            charge_progress = (
                self.phase2_left_charge_timer / self.phase2_charge_duration
                if self.phase2_left_charging
                else 0.0
            )
        else:
            particles = self.phase2_right_charge_particles
            charge_progress = (
                self.phase2_right_charge_timer / self.phase2_charge_duration
                if self.phase2_right_charging
                else 0.0
            )

        if particles.is_empty():
            return

        particles.set_target(mouth_x, mouth_y)
        speed = 40 + 120 * charge_progress
        alpha_multiplier = 0.7 + 0.55 * charge_progress
        particles.update(dt, speed=speed, alpha_multiplier=alpha_multiplier)

    def _cleanup_phase2_charge_particles(self, face: str):
        """Remove charge particles for a face."""
        if face == "left":
            self.phase2_left_charge_particles.clear()
        else:
            self.phase2_right_charge_particles.clear()

    def _fire_projectile(self):
        """Fire a single letter projectile from mouth toward player waveform."""
        self._calculate_mouth_center()

        # Random letter for projectile
        letter = random_manager.choice(ALL_BUTTONS)

        # Target is center of player waveform
        target_x = 0  # Center of screen
        target_y = -280  # Player waveform Y position

        # Calculate velocity toward target
        dx = target_x - self.mouth_center[0]
        dy = target_y - self.mouth_center[1]
        dist = math.sqrt(dx * dx + dy * dy)
        speed = 400  # Fast projectiles

        # Add slight random spread
        spread = random_manager.uniform(-0.1, 0.1)
        vx = (dx / dist + spread) * speed
        vy = (dy / dist) * speed

        # Create projectile as a standard enemy
        projectile = FaceBossProjectile(
            letter,
            (self.mouth_center[0], self.mouth_center[1]),
            (vx, vy),
            self.view,
            self.laser_manager,
            self.waveform,
            damage=0.05,  # 5% damage per projectile
        )

        # Track in our projectiles list
        self.projectiles.append(projectile)

        # Add to game engine's enemies list for standard collision detection
        self.game_engine.enemies.append(projectile)

    def _update_projectiles(self, _dt: float):
        """Clean up projectiles that have been destroyed or completed.

        Note: Projectile movement and collision detection are now handled by the
        game engine since projectiles are standard enemies.
        """
        # Remove completed/destroyed projectiles from our tracking list
        to_remove = []
        for proj in self.projectiles:
            # Check if projectile was destroyed (typed) or completed
            if proj.completed or proj not in self.game_engine.enemies:
                to_remove.append(proj)

        for proj in to_remove:
            self.projectiles.remove(proj)

    def _cleanup_projectiles(self):
        """Remove all projectiles from game."""
        for proj in self.projectiles:
            # Remove from game engine's enemy list
            if self.game_engine and proj in self.game_engine.enemies:
                self.game_engine.enemies.remove(proj)
            # Cleanup visuals
            proj.cleanup()
        self.projectiles.clear()

    def _update_firing_attack(self, dt: float):
        """Update the firing attack state."""
        # Always update fire cone (including during exit animation)
        self._update_fire_cone(dt)

        if not self.firing_projectiles:
            return

        self.fire_timer += dt
        self.fire_last_shot += dt

        # Fire projectiles at interval
        if self.fire_last_shot >= self.fire_interval:
            self._fire_projectile()
            self.fire_last_shot = 0.0

        # Check if attack duration complete
        if self.fire_timer >= self.fire_duration:
            self.firing_projectiles = False
            self._cleanup_word_display()
            # Let any remaining particles complete their animation to mouth
            if not self.charge_particles.is_empty():
                self.charge_particles.start_completing()
            self._cleanup_fire_cone()
            self.sequence_cooldown = self.sequence_cooldown_duration

    def _update_sequence_cooldown(self, dt: float):
        """Update cooldown between sequences."""
        if self.sequence_cooldown > 0:
            self.sequence_cooldown -= dt
            if self.sequence_cooldown <= 0:
                self.sequence_cooldown = 0
                # Start new word sequence
                self._start_word_sequence()

    def _update_transition_to_center(self, dt: float):
        """Transition: move face to center and turn grey with screen shake."""
        self.animation_time += dt
        self.rumble_timer += dt
        self.phase2_transition_timer += dt
        self._update_red_pulse(dt)
        progress = min(1.0, self.animation_time / self.transition_duration)

        # Ease out for smooth deceleration
        eased = 1 - (1 - progress) ** 2

        # Move towards center (0, 150)
        target_x, target_y = 0, 150
        start_x, start_y = self.transition_start_pos
        self.boss_x = start_x + (target_x - start_x) * eased
        self.boss_y = start_y + (target_y - start_y) * eased
        self.center_pos = (self.boss_x, self.boss_y)

        # Continuous screen shake during movement - intensity INCREASES over time
        # Shake intensity increases as we approach center (0.5 to 4.0)
        shake_intensity = 0.5 + 3.5 * progress
        self.game_engine.shake_manager.trigger_shake(
            magnitude=shake_intensity, duration=0.1, pattern="continuous"
        )

        # Play rumbling explosion sounds at intervals with increasing volume
        if self.rumble_timer >= self.rumble_interval:
            self.rumble_timer = 0.0
            # Volume increases from 0.1 to 0.5 during transition
            rumble_volume = 0.1 + 0.4 * progress
            self.game_engine.sound_manager.play_explosion_sound(volume=rumble_volume)

        # Fade to grey
        self.grey_factor = eased

        # Update SVG
        morphed_path = morph(self.compiled_paths, self.morph_weights)
        self._update_svg_curves(morphed_path)

        if progress >= 1.0:
            self.phase = "transition_flash"
            self.animation_time = 0.0
            # Trigger screen flash via starfield background
            self.game_engine.starfield.start_flash(self.flash_duration)
            # Play loud explosion when screen flashes
            self.game_engine.sound_manager.play_explosion_sound(volume=1.0)

    def _update_transition_flash(self, dt: float):
        """Transition: screen flash and face split."""
        self.animation_time += dt
        progress = min(1.0, self.animation_time / self.flash_duration)

        # Keep face at center during flash
        morphed_path = morph(self.compiled_paths, self.morph_weights)
        self._update_svg_curves(morphed_path)

        if progress >= 1.0:
            self.phase = "transition_split"
            self.animation_time = 0.0
            self.boss_phase = 2
            # Stop red pulse animation when split occurs
            self.red_pulse_active = False
            self.red_flash_factor = 0.0
            # Clean up phase 1 particles
            self._cleanup_charge_particles()
            # Initialize face 2 at same position
            self.face2_x = self.boss_x
            self.face2_y = self.boss_y
            self.face2_scale = self.svg_scale
            self.face2_morph_weights = self.morph_weights.copy()
            # Create face 2 visual elements
            self._create_face2_visuals()

    def _update_transition_split(self, dt: float):
        """Transition: split faces and move to corners."""
        self.animation_time += dt
        progress = min(1.0, self.animation_time / self.split_duration)

        # Ease out for smooth deceleration
        eased = 1 - (1 - progress) ** 2

        # Move face 1 to left corner
        start_x, start_y = 0, 150
        self.boss_x = start_x + (self.corner_left[0] - start_x) * eased
        self.boss_y = start_y + (self.corner_left[1] - start_y) * eased
        self.center_pos = (self.boss_x, self.boss_y)

        # Move face 2 to right corner
        self.face2_x = start_x + (self.corner_right[0] - start_x) * eased
        self.face2_y = start_y + (self.corner_right[1] - start_y) * eased

        # Scale up both faces gradually (20% increase)
        scale_factor = 1.0 + 0.2 * eased
        self.svg_scale = 2.0 * scale_factor
        self.face2_scale = 2.0 * scale_factor

        # Fade grey back to colors
        self.grey_factor = 1.0 - eased

        # Morph faces to look toward center
        # Face 1 (left corner) should use right-facing poses (looking right toward center)
        # Face 2 (right corner) should use left-facing poses (looking left toward center)
        target_weights_1 = [0.0, 1.0, 0.0, 0.0]  # right_up (looking right)
        target_weights_2 = [1.0, 0.0, 0.0, 0.0]  # left_up (looking left)
        lerp_factor = min(1.0, 3.0 * dt)
        for i in range(4):
            self.morph_weights[i] += (target_weights_1[i] - self.morph_weights[i]) * lerp_factor
            self.face2_morph_weights[i] += (
                target_weights_2[i] - self.face2_morph_weights[i]
            ) * lerp_factor

        # Update both faces
        morphed_path = morph(self.compiled_paths, self.morph_weights)
        self._update_svg_curves(morphed_path)
        morphed_path2 = morph(self.compiled_paths, self.face2_morph_weights)
        self._update_face2_curves(morphed_path2)

        if progress >= 1.0:
            self.phase = "phase2_active"
            self.animation_time = 0.0
            self.active_time = 0.0
            self.phase2_attack_timer = 0.0

    def _update_phase2(self, dt: float):
        """Update phase 2 - player must rapidly attack left/right faces to prevent attacks."""
        self.active_time += dt

        # Handle switchover animation
        if self.phase2_switchover_active:
            self._update_phase2_switchover(dt)
            self._update_phase2_visuals(dt)
            return

        # Both faces' idle timers always increment
        # Each face can charge and fire independently, even while the other is engaged
        # Timers are only reset when a word is completed on that face
        self.phase2_left_idle_timer += dt
        self.phase2_right_idle_timer += dt

        # Start charging when approaching idle timeout
        charge_start_threshold = self.phase2_idle_timeout - self.phase2_charge_duration
        if (
            self.phase2_left_idle_timer >= charge_start_threshold
            and not self.phase2_left_charging
            and not self.phase2_left_firing
        ):
            self._start_phase2_charge("left")

        if (
            self.phase2_right_idle_timer >= charge_start_threshold
            and not self.phase2_right_charging
            and not self.phase2_right_firing
        ):
            self._start_phase2_charge("right")

        # Update charging state
        self._update_phase2_charging(dt)

        # Check for idle timeout punishment (charge complete)
        if self.phase2_left_idle_timer >= self.phase2_idle_timeout:
            self._phase2_idle_punishment("left")
            self.phase2_left_idle_timer = 0.0

        if self.phase2_right_idle_timer >= self.phase2_idle_timeout:
            self._phase2_idle_punishment("right")
            self.phase2_right_idle_timer = 0.0

        # Spawn words if needed (don't spawn while that face is firing)
        if (
            self.phase2_engaged_face == "left"
            and not self.phase2_left_letters
            and not self.phase2_left_firing
        ):
            self._spawn_phase2_word("left")
        elif (
            self.phase2_engaged_face == "right"
            and not self.phase2_right_letters
            and not self.phase2_right_firing
        ):
            self._spawn_phase2_word("right")

        # Update word letters
        self._update_phase2_letters(dt)

        # Update eye glow for face 1
        self._update_eye_glow(dt)
        # Update eye glow for face 2
        self._update_face2_eye_glow(dt)

        # Update fire cone attacks
        self._update_phase2_fire_attacks(dt)

        # Update exiting cones (finishing their exit animations)
        self._update_exiting_cones(dt)

        # Update projectiles
        self._update_projectiles(dt)

        self._update_phase2_visuals(dt)

    def _update_phase2_visuals(self, dt: float):
        """Update face morphing and visuals for phase 2."""
        # Update damage distortion
        self._update_damage_distortion(dt)

        # Morph faces based on engagement state and charging state
        # Face 1 (left corner): uses right-facing poses (looking toward center)
        # Face 2 (right corner): uses left-facing poses (looking toward center)
        # Weights: [left_up, right_up, left_down, right_down]

        # Determine target weights for face 1 (left corner)
        if self.phase2_engaged_face == "left":
            target_weights_1 = [0.0, 1.0, 0.0, 0.0]  # right_up (being attacked)
        elif self.phase2_left_charging or self.phase2_left_firing:
            # Left face is charging/firing - animate toward right_up
            charge_progress = (
                self.phase2_left_charge_timer / self.phase2_charge_duration
                if self.phase2_left_charging
                else 1.0
            )
            # Blend from right_down to right_up based on charge progress
            target_weights_1 = [
                0.0,
                charge_progress,  # right_up
                0.0,
                1.0 - charge_progress,  # right_down
            ]
        else:
            target_weights_1 = [0.0, 0.0, 0.0, 1.0]  # right_down (idle)

        # Determine target weights for face 2 (right corner)
        if self.phase2_engaged_face == "right":
            target_weights_2 = [1.0, 0.0, 0.0, 0.0]  # left_up (being attacked)
        elif self.phase2_right_charging or self.phase2_right_firing:
            # Right face is charging/firing - animate toward left_up
            charge_progress = (
                self.phase2_right_charge_timer / self.phase2_charge_duration
                if self.phase2_right_charging
                else 1.0
            )
            # Blend from left_down to left_up based on charge progress
            target_weights_2 = [
                charge_progress,  # left_up
                0.0,
                1.0 - charge_progress,  # left_down
                0.0,
            ]
        else:
            target_weights_2 = [0.0, 0.0, 1.0, 0.0]  # left_down (idle)

        lerp_factor = min(1.0, self.morph_lerp_speed * dt)
        for i in range(4):
            self.morph_weights[i] += (target_weights_1[i] - self.morph_weights[i]) * lerp_factor
            self.face2_morph_weights[i] += (
                target_weights_2[i] - self.face2_morph_weights[i]
            ) * lerp_factor

        # Update stroke width based on charging/firing state
        # During charging: increase from base (3) to max (10)
        # During firing: stay at max (10)
        # Otherwise: return to base (3)
        max_stroke_width = 20.0
        is_charging = self.phase2_left_charging or self.phase2_right_charging
        is_firing = self.phase2_left_firing or self.phase2_right_firing

        if is_firing:
            # During firing, keep at max width
            target_stroke = max_stroke_width
        elif is_charging:
            # During charging, interpolate based on charge progress
            if self.phase2_left_charging:
                charge_progress = self.phase2_left_charge_timer / self.phase2_charge_duration
            else:
                charge_progress = self.phase2_right_charge_timer / self.phase2_charge_duration
            charge_progress = min(1.0, charge_progress)
            target_stroke = (
                self.base_stroke_width
                + (max_stroke_width - self.base_stroke_width) * charge_progress
            )

        target_stroke = self.base_stroke_width

        # Smoothly lerp toward target stroke width
        stroke_lerp = min(1.0, 5.0 * dt)
        # self.current_stroke_width += (target_stroke - self.current_stroke_width) * stroke_lerp

        # Update both faces
        morphed_path = morph(self.compiled_paths, self.morph_weights)
        self._update_svg_curves(morphed_path)
        morphed_path2 = morph(self.compiled_paths, self.face2_morph_weights)
        self._update_face2_curves(morphed_path2)

    def _get_phase2_word_length(self, face: str) -> int:
        """Calculate word length based on letters destroyed on a face."""
        # Calculate length: starts at min, increases by 1 for each threshold
        length_increase = self.phase2_letters_destroyed // self.phase2_letters_per_length_increase
        word_length = self.phase2_min_word_length + length_increase
        return min(word_length, self.phase2_max_word_length)

    def _spawn_phase2_word(self, face: str):
        """Spawn a new word for the specified face."""
        # Get word length based on progression
        word_length = self._get_phase2_word_length(face)

        # Generate word using appropriate hand buttons
        if face == "left":
            buttons = LEFT_HAND_BUTTONS
            self.phase2_left_word = "".join(
                random_manager.choice(buttons) for _ in range(word_length)
            )
            self.phase2_left_typed = 0
            self._create_phase2_letters("left")
        else:
            buttons = RIGHT_HAND_BUTTONS
            self.phase2_right_word = "".join(
                random_manager.choice(buttons) for _ in range(word_length)
            )
            self.phase2_right_typed = 0
            self._create_phase2_letters("right")

    def _create_phase2_letters(self, face: str):
        """Create FaceBossLetter instances for a face's word - all visible, centered below eye."""
        if face == "left":
            word = self.phase2_left_word
            letters_list = self.phase2_left_letters
            eye_x = self.corner_left[0]
            eye_y = self.corner_left[1] - 60  # Below eye
            off_screen_x = -600  # For slide-in animation
        else:
            word = self.phase2_right_word
            letters_list = self.phase2_right_letters
            eye_x = self.corner_right[0]
            eye_y = self.corner_right[1] - 60  # Below eye
            off_screen_x = 600  # For slide-in animation

        # Clean up any existing letters
        for letter in letters_list:
            letter.cleanup()
        letters_list.clear()

        # Letter spacing for the word
        letter_spacing = 35
        word_len = len(word)

        # Calculate starting X to center the word below the eye
        word_width = (word_len - 1) * letter_spacing
        start_x = eye_x - word_width / 2

        # Create letter instances - all start off-screen but with correct target positions
        for idx, letter_char in enumerate(word):
            target_x = start_x + idx * letter_spacing
            letter_enemy = FaceBossLetter(
                letter_char,
                (off_screen_x, eye_y),  # Start off-screen
                self.view,
                self.laser_manager,
                self.waveform,
            )
            letter_enemy.set_target_position(target_x, eye_y)
            # Right face types right-to-left, so set sweep direction accordingly (dashed style)
            if face == "right":
                letter_enemy.set_typing_direction(False)
            letters_list.append(letter_enemy)

        # Highlight first letter for left face, last letter for right face (right-to-left typing)
        if letters_list:
            if face == "left":
                letters_list[0].set_highlighted(True)
            else:
                letters_list[-1].set_highlighted(True)

    def _update_phase2_letters(self, dt: float):
        """Update letter positions and animations for both faces."""
        self._update_phase2_face_letters("left", dt)
        self._update_phase2_face_letters("right", dt)

    def _update_phase2_face_letters(self, face: str, dt: float):
        """Update letters for a specific face - all letters visible, just update animations."""
        if face == "left":
            letters = self.phase2_left_letters
            word = self.phase2_left_word
            typed_count = self.phase2_left_typed
        else:
            letters = self.phase2_right_letters
            word = self.phase2_right_word
            typed_count = self.phase2_right_typed

        # Word is complete when we've typed all letters AND there's an active word
        # (empty word means switchover/reset, not completion)
        word_complete = word and typed_count >= len(word)

        # Only clean up completed letters after the word is complete
        # to preserve list indices during active typing
        if word_complete:
            for letter in letters[:]:
                if letter.completed:
                    letter.cleanup()
                    letters.remove(letter)

        # Update all letters - they already have their target positions set
        for letter in letters:
            letter.update(dt)

    def _start_phase2_charge(self, face: str):
        """Start charging animation for a face before it attacks."""
        if face == "left":
            self.phase2_left_charging = True
            self.phase2_left_charge_timer = 0.0
        else:
            self.phase2_right_charging = True
            self.phase2_right_charge_timer = 0.0

        # Spawn charge particles
        self._spawn_phase2_charge_particles(face)

    def _cancel_phase2_charge(self, face: str):
        """Cancel charging animation when player engages the face."""
        if face == "left":
            self.phase2_left_charging = False
            self.phase2_left_charge_timer = 0.0
        else:
            self.phase2_right_charging = False
            self.phase2_right_charge_timer = 0.0

        # Clean up charge particles
        self._cleanup_phase2_charge_particles(face)

    def _update_phase2_charging(self, dt: float):
        """Update charging state for both faces."""
        # Update left face charging
        if self.phase2_left_charging:
            self.phase2_left_charge_timer += dt
            self._update_phase2_charge_particles("left", dt)

            # Check if charge complete
            if self.phase2_left_charge_timer >= self.phase2_charge_duration:
                self.phase2_left_charging = False
                self._cleanup_phase2_charge_particles("left")

        # Update right face charging
        if self.phase2_right_charging:
            self.phase2_right_charge_timer += dt
            self._update_phase2_charge_particles("right", dt)

            # Check if charge complete
            if self.phase2_right_charge_timer >= self.phase2_charge_duration:
                self.phase2_right_charging = False
                self._cleanup_phase2_charge_particles("right")

    def _phase2_idle_punishment(self, face: str):
        """Trigger punishment when a face has been idle too long - start fire cone attack."""
        # Stop charging state (it completed)
        if face == "left":
            self.phase2_left_charging = False
            self._cleanup_phase2_charge_particles("left")
        else:
            self.phase2_right_charging = False
            self._cleanup_phase2_charge_particles("right")

        # Trigger eye glow/blink on the punishing face
        if face == "left":
            self.eye_glowing = True
            self.eye_glow_timer = 0.0
            self.eye_blinking = True
            self.eye_blink_timer = 0.0
        else:
            self.face2_eye_glowing = True
            self.face2_eye_glow_timer = 0.0

        # Flash word letters yellow if there are any
        if face == "left":
            for letter in self.phase2_left_letters:
                letter.start_yellow_flash()
        else:
            for letter in self.phase2_right_letters:
                letter.start_yellow_flash()

        # Start fire cone attack from this face
        self._start_phase2_fire_attack(face)

    def _start_phase2_fire_attack(self, face: str):
        """Start fire cone attack from a face."""
        # Cancel engagement if player was engaged with this face's word
        if self.phase2_engaged_face == face:
            self.phase2_engaged_face = None
            # Slide out and reset letters for this face
            if face == "left":
                self.phase2_left_typed = 0
                self.phase2_left_word = ""
                for letter in self.phase2_left_letters:
                    letter.start_slide_out(-300)  # Slide out to left
            else:
                self.phase2_right_typed = 0
                self.phase2_right_word = ""
                for letter in self.phase2_right_letters:
                    letter.start_slide_out(300)  # Slide out to right
            # Clear game engine engagement
            if self.game_engine and self.game_engine.engaged_enemy == self:
                self.game_engine.clear_engagement()

        # Get mouth position for this face
        mouth_x, mouth_y = self._get_phase2_mouth_center(face)

        if face == "left":
            # If there's an existing cone, start its exit animation
            if self.phase2_left_fire_cone:
                self.phase2_left_fire_cone.start_exit()
                self.exiting_cones.append(self.phase2_left_fire_cone)

            self.phase2_left_firing = True
            self.phase2_left_fire_timer = 0.0
            self.phase2_left_fire_last_shot = 0.0

            # Create fire cone from mouth
            fire_color = (255, 100, 50)
            self.phase2_left_fire_cone = ConeEffect(
                view=self.view,
                source=(mouth_x, mouth_y),
                target_y=-280,
                target_width=60,
                color=fire_color,
                num_interior=8,
                opacity_mult=2.5,
                width_mult=2.5,
                waveform=self.waveform,
            )
        else:
            # If there's an existing cone, start its exit animation
            if self.phase2_right_fire_cone:
                self.phase2_right_fire_cone.start_exit()
                self.exiting_cones.append(self.phase2_right_fire_cone)

            self.phase2_right_firing = True
            self.phase2_right_fire_timer = 0.0
            self.phase2_right_fire_last_shot = 0.0

            # Create fire cone from mouth
            fire_color = (255, 100, 50)
            self.phase2_right_fire_cone = ConeEffect(
                view=self.view,
                source=(mouth_x, mouth_y),
                target_y=-280,
                target_width=60,
                color=fire_color,
                num_interior=8,
                opacity_mult=2.5,
                width_mult=2.5,
                waveform=self.waveform,
            )

    def _update_phase2_fire_attacks(self, dt: float):
        """Update fire cone attacks for both faces."""
        self._update_phase2_face_fire("left", dt)
        self._update_phase2_face_fire("right", dt)

    def _update_phase2_face_fire(self, face: str, dt: float):
        """Update fire attack for a specific face."""
        mouth_x, mouth_y = self._get_phase2_mouth_center(face)

        if face == "left":
            # Update cone source to follow mouth position
            if self.phase2_left_fire_cone:
                self.phase2_left_fire_cone.set_source((mouth_x, mouth_y))
                self.phase2_left_fire_cone.update(dt, self.phase2_left_fire_timer)

            if not self.phase2_left_firing:
                return
            self.phase2_left_fire_timer += dt
            self.phase2_left_fire_last_shot += dt

            # Fire projectiles at interval
            if self.phase2_left_fire_last_shot >= self.phase2_fire_interval:
                self._fire_phase2_projectile("left")
                self.phase2_left_fire_last_shot = 0.0

            # Check if attack complete
            if self.phase2_left_fire_timer >= self.phase2_fire_duration:
                self.phase2_left_firing = False
                if self.phase2_left_fire_cone:
                    self.phase2_left_fire_cone.start_exit()
                    self.exiting_cones.append(self.phase2_left_fire_cone)
                    self.phase2_left_fire_cone = None
        else:
            # Update cone source to follow mouth position
            if self.phase2_right_fire_cone:
                self.phase2_right_fire_cone.set_source((mouth_x, mouth_y))
                self.phase2_right_fire_cone.update(dt, self.phase2_right_fire_timer)

            if not self.phase2_right_firing:
                return
            self.phase2_right_fire_timer += dt
            self.phase2_right_fire_last_shot += dt

            # Fire projectiles at interval
            if self.phase2_right_fire_last_shot >= self.phase2_fire_interval:
                self._fire_phase2_projectile("right")
                self.phase2_right_fire_last_shot = 0.0

            # Check if attack complete
            if self.phase2_right_fire_timer >= self.phase2_fire_duration:
                self.phase2_right_firing = False
                if self.phase2_right_fire_cone:
                    self.phase2_right_fire_cone.start_exit()
                    self.exiting_cones.append(self.phase2_right_fire_cone)
                    self.phase2_right_fire_cone = None

    def _fire_phase2_projectile(self, face: str):
        """Fire a single projectile from a face's mouth toward player."""
        mouth_x, mouth_y = self._get_phase2_mouth_center(face)

        if face == "left":
            buttons = LEFT_HAND_BUTTONS
        else:
            buttons = RIGHT_HAND_BUTTONS

        # Target is player waveform
        target_x = 0
        target_y = -280

        # Calculate velocity toward target from mouth position
        dx = target_x - mouth_x
        dy = target_y - mouth_y
        dist = math.sqrt(dx * dx + dy * dy)
        speed = 350

        # Add slight random spread
        spread = random_manager.uniform(-0.15, 0.15)
        if dist > 0:
            vx = (dx / dist + spread) * speed
            vy = (dy / dist) * speed
        else:
            vx = spread * speed
            vy = -speed

        # Choose random button from the face's hand
        button = random_manager.choice(buttons)

        # Create projectile from mouth position
        projectile = FaceBossProjectile(
            button,
            (mouth_x, mouth_y),
            (vx, vy),
            self.view,
            self.laser_manager,
            self.waveform,
            damage=0.05,
        )

        # Track in our projectiles list
        self.projectiles.append(projectile)

        # Add to game engine's enemies list
        self.game_engine.enemies.append(projectile)

    def _start_phase2_switchover(self, new_face: str):
        """Start the switchover animation to a new face."""
        self.phase2_switchover_active = True
        self.phase2_switchover_timer = 0.0

        # Clean up and reset BOTH faces to ensure clean state
        # Old face: slide out letters
        old_face = self.phase2_engaged_face
        if old_face == "left":
            for letter in self.phase2_left_letters:
                letter.start_slide_out(-300)  # Slide out to left
        elif old_face == "right":
            for letter in self.phase2_right_letters:
                letter.start_slide_out(300)  # Slide out to right

        # Reset both faces' state
        self.phase2_left_typed = 0
        self.phase2_left_word = ""
        self.phase2_right_typed = 0
        self.phase2_right_word = ""

        # Set the new engaged face
        self.phase2_engaged_face = new_face

        # Spawn word for new face (will slide in) - but not if that face is firing
        # This also cleans up any existing letters for that face
        is_firing = (new_face == "left" and self.phase2_left_firing) or (
            new_face == "right" and self.phase2_right_firing
        )
        if not is_firing:
            self._spawn_phase2_word(new_face)

    def _update_phase2_switchover(self, dt: float):
        """Update the switchover animation."""
        self.phase2_switchover_timer += dt

        # Update letters during switchover
        self._update_phase2_letters(dt)

        if self.phase2_switchover_timer >= self.phase2_switchover_duration:
            self.phase2_switchover_active = False
            # Clean up non-engaged face letters completely
            # The engaged face should only have the newly spawned word
            if self.phase2_engaged_face == "right":
                # Clean up all left face letters
                for letter in self.phase2_left_letters[:]:
                    letter.cleanup()
                self.phase2_left_letters.clear()
            elif self.phase2_engaged_face == "left":
                # Clean up all right face letters
                for letter in self.phase2_right_letters[:]:
                    letter.cleanup()
                self.phase2_right_letters.clear()

            # Also remove any completed/sliding-out letters from engaged face
            # (in case there were old letters that didn't get cleaned up)
            if self.phase2_engaged_face == "left":
                for letter in self.phase2_left_letters[:]:
                    if letter.fading_out or letter.completed:
                        letter.cleanup()
                        self.phase2_left_letters.remove(letter)
            elif self.phase2_engaged_face == "right":
                for letter in self.phase2_right_letters[:]:
                    if letter.fading_out or letter.completed:
                        letter.cleanup()
                        self.phase2_right_letters.remove(letter)

    def _type_phase2_letter(self, button: str) -> bool:
        """Handle typing a letter in phase 2."""
        # Block all typing during switchover animation
        if self.phase2_switchover_active:
            return False

        # Determine which hand the button belongs to
        is_left_hand = button in LEFT_HAND_BUTTONS
        is_right_hand = button in RIGHT_HAND_BUTTONS

        if not is_left_hand and not is_right_hand:
            return False

        target_face = "left" if is_left_hand else "right"

        # If pressing wrong hand while engaged, trigger switchover
        if self.phase2_engaged_face is not None and self.phase2_engaged_face != target_face:
            self._start_phase2_switchover(target_face)
            return False

        # If not engaged yet, start engagement (but not if that face is firing)
        if self.phase2_engaged_face is None:
            is_firing = (target_face == "left" and self.phase2_left_firing) or (
                target_face == "right" and self.phase2_right_firing
            )
            if is_firing:
                return False  # Can't engage a firing face
            self.phase2_engaged_face = target_face
            self._spawn_phase2_word(target_face)
            # Don't count this keypress as typing - just engagement

        # Now try to type the letter
        if target_face == "left":
            return self._type_phase2_left_letter(button)
        else:
            return self._type_phase2_right_letter(button)

    def _type_phase2_left_letter(self, button: str) -> bool:
        """Handle typing a letter on the left face (left-to-right)."""
        if not self.phase2_left_letters or not self.phase2_left_word:
            return False

        if self.phase2_left_typed >= len(self.phase2_left_word):
            return False

        if self.phase2_left_typed >= len(self.phase2_left_letters):
            return False

        current_letter = self.phase2_left_letters[self.phase2_left_typed]
        expected = self.phase2_left_word[self.phase2_left_typed]

        if button != expected:
            return False

        # Get position for explosion
        letter_pos = current_letter.get_center_position()

        # Type the letter
        current_letter.type_button(button)

        # Create explosion
        color = BUTTON_COLORS.get(button, "#FFFFFF")
        color_rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        self.game_engine.explosion_manager.create_explosion(letter_pos, color_rgb, "enhanced", 0.6)
        self.game_engine.sound_manager.play_explosion_sound(volume=0.3)

        # Slide out the letter
        current_letter.start_slide_out(200)  # Slide to right
        current_letter.set_highlighted(False)

        self.phase2_left_typed += 1
        self.phase2_letters_destroyed += 1

        # Highlight next letter
        if self.phase2_left_typed < len(self.phase2_left_letters):
            self.phase2_left_letters[self.phase2_left_typed].set_highlighted(True)

        # Check if word complete
        if self.phase2_left_typed >= len(self.phase2_left_letters):
            self._phase2_word_completed("left")

        return True

    def _type_phase2_right_letter(self, button: str) -> bool:
        """Handle typing a letter on the right face (right-to-left)."""
        if not self.phase2_right_letters or not self.phase2_right_word:
            return False

        word_len = len(self.phase2_right_word)
        if self.phase2_right_typed >= word_len:
            return False

        # Right-to-left: type from end of word backward
        letter_idx = word_len - 1 - self.phase2_right_typed
        if letter_idx >= len(self.phase2_right_letters):
            return False
        current_letter = self.phase2_right_letters[letter_idx]
        expected = self.phase2_right_word[letter_idx]

        if button != expected:
            return False

        # Get position for explosion
        letter_pos = current_letter.get_center_position()

        # Type the letter
        current_letter.type_button(button)

        # Create explosion
        color = BUTTON_COLORS.get(button, "#FFFFFF")
        color_rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        self.game_engine.explosion_manager.create_explosion(letter_pos, color_rgb, "enhanced", 0.6)
        self.game_engine.sound_manager.play_explosion_sound(volume=0.3)

        # Slide out the letter
        current_letter.start_slide_out(-200)  # Slide to left
        current_letter.set_highlighted(False)

        self.phase2_right_typed += 1
        self.phase2_letters_destroyed += 1

        # Highlight next letter (going right-to-left)
        next_letter_idx = word_len - 1 - self.phase2_right_typed
        if self.phase2_right_typed < word_len and next_letter_idx >= 0:
            self.phase2_right_letters[next_letter_idx].set_highlighted(True)

        # Check if word complete
        if self.phase2_right_typed >= word_len:
            self._phase2_word_completed("right")

        return True

    def _phase2_word_completed(self, face: str):
        """Handle word completion on a face."""
        # Reset idle timer and cancel charging on this face since word was destroyed
        if face == "left":
            self.phase2_left_idle_timer = 0.0
            print("Left Damaged")
            if self.phase2_left_charging:
                self._cancel_phase2_charge("left")
        else:
            self.phase2_right_idle_timer = 0.0
            print("Right Damaged")
            if self.phase2_right_charging:
                self._cancel_phase2_charge("right")

        # Trigger red flash on the face
        self.red_flash_active = True
        self.red_flash_timer = 0.0

        # Trigger damage distortion
        self._trigger_damage_distortion()

        # Screen shake
        self.game_engine.shake_manager.medium_shake()

        # Damage the boss
        damage = 5  # Each word does 5% damage
        self.phase2_health -= damage

        # Check for defeat
        if self.phase2_health <= 0:
            self.phase2_health = 0
            self._start_defeat_sequence()
            return

        # Clean up completed letters and spawn new word
        if face == "left":
            for letter in self.phase2_left_letters:
                letter.cleanup()
            self.phase2_left_letters.clear()
            self.phase2_left_typed = 0
            self.phase2_left_word = ""
            # Spawn new word immediately if not firing
            if not self.phase2_left_firing:
                self._spawn_phase2_word("left")
        else:
            for letter in self.phase2_right_letters:
                letter.cleanup()
            self.phase2_right_letters.clear()
            self.phase2_right_typed = 0
            self.phase2_right_word = ""
            # Spawn new word immediately if not firing
            if not self.phase2_right_firing:
                self._spawn_phase2_word("right")

    def _start_defeat_sequence(self):
        """Start the boss defeat sequence with death animation."""
        self.phase = "death_animation"
        self.death_animation_active = True
        self.death_animation_timer = 0.0
        self.distortion_seed = random_manager.randint(0, 1000)

        # Clean up all phase 2 letters
        for letter in self.phase2_left_letters:
            letter.cleanup()
        self.phase2_left_letters.clear()

        for letter in self.phase2_right_letters:
            letter.cleanup()
        self.phase2_right_letters.clear()

        # Clean up phase 2 fire cones
        if self.phase2_left_fire_cone:
            self.phase2_left_fire_cone.cleanup()
            self.phase2_left_fire_cone = None
        self.phase2_left_firing = False

        if self.phase2_right_fire_cone:
            self.phase2_right_fire_cone.cleanup()
            self.phase2_right_fire_cone = None
        self.phase2_right_firing = False

        # Clean up projectiles
        self._cleanup_projectiles()
        self._cleanup_charge_particles()

        # Remove all face and eye curves for performance during death animation
        # Face 1 - all curves and fills
        for curve_list in [
            self.svg_curves,
            self.svg_curves_layer1,
            self.svg_curves_layer2,
            self.eye_curves,
            self.eye_curves_layer1,
            self.eye_curves_layer2,
        ]:
            for curve in curve_list:
                self.view.removeItem(curve)
            curve_list.clear()

        if self.eye_fill is not None:
            self.view.removeItem(self.eye_fill)
            self.eye_fill = None

        # Face 2 - all curves and fills
        for curve_list in [
            self.face2_curves,
            self.face2_curves_layer1,
            self.face2_curves_layer2,
            self.face2_eye_curves,
            self.face2_eye_curves_layer1,
            self.face2_eye_curves_layer2,
        ]:
            for curve in curve_list:
                self.view.removeItem(curve)
            curve_list.clear()

        if self.face2_eye_fill is not None:
            self.view.removeItem(self.face2_eye_fill)
            self.face2_eye_fill = None

        # Don't trigger destruction callback yet - wait for death animation to complete

    def _update_death_animation(self, dt: float):
        """Update the death animation - Y-collapse with explosions, then fade with final flash."""
        self.death_animation_timer += dt
        total_duration = self.death_collapse_duration + self.death_fade_duration

        # Get face centers for explosions
        face1_center = (self.boss_x, self.boss_y)
        face2_center = (self.face2_x, self.face2_y) if self.boss_phase == 2 else None

        if self.death_animation_timer < self.death_collapse_duration:
            # Phase 1: Collapse into horizontal band over 3 seconds with explosions
            progress = self.death_animation_timer / self.death_collapse_duration

            # Y-scale collapses from 1.0 to 0.05 with ease-in
            eased_progress = progress**2  # Ease-in (slow start, fast end)
            self.death_y_scale = 1.0 - eased_progress * 0.95  # 1.0 -> 0.05

            # Increasing distortion as it collapses
            self.distortion_amount = eased_progress * 40
            self.distortion_seed = int(self.death_animation_timer * 15) % 1000

            # Screen shake that intensifies
            shake_intensity = 2.0 + progress * 6.0
            self.game_engine.shake_manager.trigger_shake(magnitude=shake_intensity, duration=0.1)

            # Spawn explosions at face centers
            self.death_explosion_timer += dt
            if self.death_explosion_timer >= self.death_explosion_interval:
                self.death_explosion_timer = 0.0
                self._spawn_death_explosion(face1_center, progress)
                self._spawn_death_explosion(face2_center, progress)

        else:
            # Phase 2: Fade out with continued explosions and flashes over 3 seconds
            fade_time = self.death_animation_timer - self.death_collapse_duration
            fade_progress = fade_time / self.death_fade_duration

            # Keep collapsed and distorted
            self.death_y_scale = 0.05
            self.distortion_amount = 40
            self.distortion_seed = int(self.death_animation_timer * 15) % 1000

            # Fade out opacity
            self.svg_opacity = max(0.0, 1.0 - fade_progress)

            # Continue spawning explosions (slower rate as we fade)
            explosion_interval = self.death_explosion_interval * (1 + fade_progress)
            self.death_explosion_timer += dt
            if self.death_explosion_timer >= explosion_interval:
                self.death_explosion_timer = 0.0
                self._spawn_death_explosion(face1_center, 1.0)
                self._spawn_death_explosion(face2_center, 1.0)

            # Flash effects
            self.death_flash_timer += dt
            if self.death_flash_timer >= self.death_flash_interval:
                self.death_flash_timer = 0.0
                self._spawn_death_flash(fade_progress)

            # Final flash sequence in the last 0.5 seconds
            if fade_progress > 0.85:
                final_progress = (fade_progress - 0.85) / 0.15  # 0 to 1 over last 0.5s
                self._spawn_final_flash_sequence(face1_center, face2_center, final_progress, dt)

        # Face curves are removed at start of death - no updates needed
        # Just show explosions during death animation

        # Check if animation is complete
        if self.death_animation_timer >= total_duration:
            self.phase = "destroyed"
            self.defeated = True
            self.completed = True

            # Now trigger destruction callback
            if self.destruction_callback:
                self.destruction_callback(self, is_boss=True)  # pylint: disable=not-callable

    def _spawn_death_explosion(self, center: Tuple[float, float], intensity: float):
        """Spawn an explosion at a face center during death animation."""

        # Random offset from center
        offset_x = random_manager.uniform(-50, 50) * (1 + intensity)
        offset_y = random_manager.uniform(-30, 30) * self.death_y_scale
        pos = (center[0] + offset_x, center[1] + offset_y)

        # Random color from face palette
        colors = [(255, 50, 100), (255, 255, 50), (100, 200, 255), (255, 150, 50)]
        color = random_manager.choice(colors)

        # Scale increases with intensity
        scale = 0.5 + intensity * 0.8

        self.game_engine.explosion_manager.create_explosion(pos, color, "enhanced", scale)

        # Play explosion sound at reduced volume
        self.game_engine.sound_manager.play_explosion_sound(volume=0.2 + intensity * 0.2)

    def _spawn_death_flash(self, fade_progress: float):
        """Spawn a flash effect during death fade."""
        # Trigger starfield flash
        flash_intensity = 0.05 + fade_progress * 0.1
        self.game_engine.starfield.start_flash(flash_intensity)

    def _spawn_final_flash_sequence(
        self,
        face1_center: Tuple[float, float],
        face2_center: Tuple[float, float],
        final_progress: float,
        dt: float,
    ):
        """Spawn the final flash sequence at the very end of death animation."""
        # Rapid flashes that increase in frequency
        flash_rate = 0.1 - final_progress * 0.08  # 0.1s -> 0.02s intervals
        self.death_flash_timer += dt * 2  # Double counting for faster flashes

        if self.death_flash_timer >= flash_rate:
            self.death_flash_timer = 0.0

            # Large explosions - only spawn 1/3 of them for performance
            if random_manager.random() < 0.33:
                scale = 1.5 + final_progress * 1.5  # 1.5 -> 3.0
                self.game_engine.explosion_manager.create_explosion(
                    face1_center, (255, 255, 255), "mega", scale
                )
                self.game_engine.explosion_manager.create_explosion(
                    face2_center, (255, 255, 255), "mega", scale
                )

            # Screen flash
            self.game_engine.starfield.start_flash(0.2 + final_progress * 0.3)

            # Screen shake
            self.game_engine.shake_manager.trigger_shake(
                magnitude=5.0 + final_progress * 10.0, duration=0.15
            )

            # Sound
            self.game_engine.sound_manager.play_explosion_sound(volume=0.5 + final_progress * 0.5)

    def _update_face2_eye_glow(self, dt: float):
        """Update eye glow animation for face 2."""
        self.face2_eye_glow_timer += dt

        if self.face2_eye_glowing:
            glow_progress = self.face2_eye_glow_timer / self.eye_glow_duration
            if glow_progress < 0.5:
                self.face2_eye_glow = glow_progress * 2
            else:
                self.face2_eye_glow = (1 - glow_progress) * 2

            if self.face2_eye_glow_timer >= self.eye_glow_duration:
                self.face2_eye_glowing = False
                self.face2_eye_glow = 0.0
                self.face2_eye_glow_timer = 0.0
        else:
            self.face2_eye_glow = 0.0

    def start_phase2_transition(self):
        """Called when player attacks - start transition to phase 2."""
        if self.phase == "phase1_active" and self.boss_phase == 1:
            self.phase = "transition_to_center"
            self.animation_time = 0.0
            self.rumble_timer = 0.0
            self.transition_start_pos = (self.boss_x, self.boss_y)
            self.phase2_transition_timer = 0.0

            # Start red pulse animation
            self.red_pulse_active = True
            self.red_flash_active = False  # Disable single flash

            # Trigger initial screen shake and low volume explosion
            self.game_engine.shake_manager.medium_shake()
            self.game_engine.sound_manager.play_explosion_sound(volume=0.4)

            # Clean up target enemy from phase 1
            if self.target_enemy:
                self.target_enemy.cleanup()
                self.target_enemy = None

    def _update_eye_glow(self, dt: float):
        """Update eye glow animation - triggers every 2 seconds."""
        self.eye_glow_timer += dt

        # Check if it's time to trigger a new glow
        if not self.eye_glowing and self.eye_glow_timer >= self.eye_glow_interval:
            self.eye_glowing = True
            self.eye_glow_timer = 0.0

        # Animate glow intensity
        if self.eye_glowing:
            # Glow in then out over the duration
            glow_progress = self.eye_glow_timer / self.eye_glow_duration
            if glow_progress < 0.5:
                # Ramp up
                self.eye_glow = glow_progress * 2  # 0 -> 1 over first half
            else:
                # Ramp down
                self.eye_glow = (1 - glow_progress) * 2  # 1 -> 0 over second half

            # End glow when duration is complete
            if self.eye_glow_timer >= self.eye_glow_duration:
                self.eye_glowing = False
                self.eye_glow = 0.0
                self.eye_glow_timer = 0.0
        else:
            self.eye_glow = 0.0

        # Update eye blink animation (Y-scaling for damage, separate from color pulse)
        if self.eye_blinking:
            self.eye_blink_timer += dt
            blink_progress = self.eye_blink_timer / self.eye_blink_duration
            if blink_progress < 0.5:
                # Close eye
                self.eye_blink = blink_progress * 2  # 0 -> 1 over first half
            else:
                # Open eye
                self.eye_blink = (1 - blink_progress) * 2  # 1 -> 0 over second half

            # End blink when duration is complete
            if self.eye_blink_timer >= self.eye_blink_duration:
                self.eye_blinking = False
                self.eye_blink = 0.0
                self.eye_blink_timer = 0.0
        else:
            self.eye_blink = 0.0

    def _update_stars(self, dt: float):
        """Update star positions during entry animation."""
        for star in self.stars:
            # Track motion time for color pulse
            star["motion_time"] += dt

            if star["arrived"]:
                # Add noise to position around target
                noise_x = math.sin(star["motion_time"] * 5 + star["target_x"]) * 3
                noise_y = math.cos(star["motion_time"] * 4 + star["target_y"]) * 3
                star["current_x"] = star["target_x"] + noise_x
                star["current_y"] = star["target_y"] + noise_y
                continue

            # Wait for delay
            if self.animation_time < star["delay"]:
                continue

            # Calculate progress - use fixed travel duration so stars arrive at staggered times
            progress_time = self.animation_time - star["delay"]
            travel_duration = 1.5  # Fixed travel time for all stars
            progress = min(1.0, progress_time / travel_duration)

            # Ease-out cubic for smooth deceleration
            eased_progress = 1 - (1 - progress) ** 3

            # Interpolate position
            star["current_x"] = (
                star["start_x"] + (star["target_x"] - star["start_x"]) * eased_progress
            )
            star["current_y"] = (
                star["start_y"] + (star["target_y"] - star["start_y"]) * eased_progress
            )

            # Check if arrived
            if progress >= 1.0:
                star["arrived"] = True

        # Update single ScatterPlotItem with all star positions
        if self.stars_plot_item and self.stars:
            positions = [(star["current_x"], star["current_y"]) for star in self.stars]

            # Calculate average color pulse for all stars
            avg_motion_time = sum(s["motion_time"] for s in self.stars) / len(self.stars)
            pulse = 0.5 + 0.5 * math.sin(avg_motion_time * 2 * math.pi)
            star_r = int(100 + (255 - 100) * pulse)
            star_g = int(200 + (255 - 200) * pulse)
            star_b = int(255 + (100 - 255) * pulse)

            self.stars_plot_item.setBrush(pg.mkBrush(star_r, star_g, star_b, 255))
            self.stars_plot_item.setData(pos=positions, size=self.star_base_size)

    def _create_constellation_lines(self):
        """Create line items connecting stars in order to form constellation."""
        # Sort stars by their index to get them in path order
        sorted_stars = sorted(self.stars, key=lambda s: s["index"])

        # Create lines connecting adjacent stars
        for i in range(len(sorted_stars) - 1):
            star1 = sorted_stars[i]
            star2 = sorted_stars[i + 1]

            # Create line item (initially invisible)
            line = pg.PlotCurveItem(
                x=[star1["target_x"], star1["target_x"]],  # Start as a point
                y=[star1["target_y"], star1["target_y"]],
                pen=pg.mkPen(color=(100, 200, 255, 0), width=2),
            )
            line.setZValue(9)  # Below stars (z=10)
            self.view.addItem(line)

            # Store line with its endpoints
            self.constellation_lines.append(
                {
                    "item": line,
                    "x1": star1["target_x"],
                    "y1": star1["target_y"],
                    "x2": star2["target_x"],
                    "y2": star2["target_y"],
                    "index": i,
                }
            )

    def _update_constellation_forming(self, dt: float):
        """Update constellation line drawing animation."""
        self.animation_time += dt
        progress = min(1.0, self.animation_time / self.constellation_draw_duration)
        self.constellation_line_progress = progress

        num_lines = len(self.constellation_lines)
        if num_lines == 0:
            self.phase = "constellation_glow"
            self.animation_time = 0.0
            return

        # Determine how many lines should be fully drawn
        lines_progress = progress * num_lines

        for i, line_data in enumerate(self.constellation_lines):
            line = line_data["item"]
            x1, y1 = line_data["x1"], line_data["y1"]
            x2, y2 = line_data["x2"], line_data["y2"]

            if i < lines_progress - 1:
                # This line is fully drawn
                line.setData(x=[x1, x2], y=[y1, y2])
                line.setPen(pg.mkPen(color=(100, 200, 255, 255), width=2))
            elif i < lines_progress:
                # This line is being drawn
                line_progress = lines_progress - i
                curr_x = x1 + (x2 - x1) * line_progress
                curr_y = y1 + (y2 - y1) * line_progress
                line.setData(x=[x1, curr_x], y=[y1, curr_y])
                line.setPen(pg.mkPen(color=(100, 200, 255, 255), width=2))
            else:
                # This line hasn't started yet
                line.setPen(pg.mkPen(color=(100, 200, 255, 0), width=2))

        # Keep stars visible and pulsing with noise
        if self.stars_plot_item and self.stars:
            positions = []
            for star in self.stars:
                noise_x = math.sin(self.animation_time * 5 + star["target_x"]) * 3
                noise_y = math.cos(self.animation_time * 4 + star["target_y"]) * 3
                positions.append((star["target_x"] + noise_x, star["target_y"] + noise_y))
            pulse = 0.5 + 0.5 * math.sin(self.animation_time * 4 * math.pi)
            star_r = int(100 + 155 * pulse)
            star_g = int(200 + 55 * pulse)
            star_b = 255
            self.stars_plot_item.setBrush(pg.mkBrush(star_r, star_g, star_b, 255))
            self.stars_plot_item.setData(pos=positions, size=self.star_base_size)

        # Transition to glow phase when done
        if progress >= 1.0:
            self.phase = "constellation_glow"
            self.animation_time = 0.0
            self.constellation_glow_timer = 0.0
            self.constellation_pulse_count = 0

    def _update_constellation_glow(self, dt: float):
        """Update constellation glow/pulse animation before face reveal."""
        self.animation_time += dt
        self.constellation_glow_timer += dt

        # Pulse frequency increases over time (heartbeat building to climax)
        base_freq = 2.0  # Hz
        freq_increase = self.animation_time * 2.0  # Accelerate over time
        pulse_freq = base_freq + freq_increase

        # Pulse intensity
        pulse = 0.5 + 0.5 * math.sin(self.constellation_glow_timer * pulse_freq * 2 * math.pi)

        # Count pulses for dramatic effect
        if pulse > 0.9 and self.constellation_pulse_count < int(self.animation_time * pulse_freq):
            self.constellation_pulse_count = int(self.animation_time * pulse_freq)
            # Screen shake on each pulse (increasing intensity)
            if self.game_engine and self.game_engine.shake_manager:
                intensity = 0.15 + self.animation_time * 0.15
                self.game_engine.shake_manager.trigger_shake(intensity, 0.15)
            # Rumble sound on each pulse
            if self.game_engine and self.game_engine.sound_manager:
                rumble_volume = 0.2 + self.animation_time * 0.2
                self.game_engine.sound_manager.play_explosion_sound(volume=rumble_volume)

        # Update line colors with pulse
        alpha = int(150 + 105 * pulse)
        width = 2 + int(3 * pulse)
        line_r = int(100 + 155 * pulse)
        line_g = int(200 + 55 * pulse)
        line_b = 255

        for line_data in self.constellation_lines:
            line = line_data["item"]
            line.setPen(pg.mkPen(color=(line_r, line_g, line_b, alpha), width=width))

        # Update stars with pulse and noise
        if self.stars_plot_item and self.stars:
            positions = []
            for star in self.stars:
                noise_x = math.sin(self.animation_time * 5 + star["target_x"]) * 3
                noise_y = math.cos(self.animation_time * 4 + star["target_y"]) * 3
                positions.append((star["target_x"] + noise_x, star["target_y"] + noise_y))
            star_size = self.star_base_size + 6 * pulse
            self.stars_plot_item.setBrush(pg.mkBrush(line_r, line_g, line_b, alpha))
            self.stars_plot_item.setData(pos=positions, size=star_size)

        # Transition to face reveal after glow duration
        if self.animation_time >= self.constellation_glow_duration:
            # Dramatic flash before face appears
            self.game_engine.starfield.start_flash(0.5)
            self.game_engine.shake_manager.trigger_shake(0.5, 0.3)

            self.phase = "svg_fading_in"
            self.animation_time = 0.0
            self._create_svg_visual()

            # Clean up constellation lines
            for line_data in self.constellation_lines:
                if line_data["item"].scene():
                    self.view.removeItem(line_data["item"])
            self.constellation_lines.clear()

    def type_button(self, button: str) -> bool:
        """Handle button press - use word attack system.

        Note: Projectiles are now standard enemies and handled by the game engine.
        """
        if self.phase == "phase1_active" and self.word_active:
            result = self._type_word_letter(button)
            if not result:
                # Wrong letter typed - trigger punishment
                self._trigger_word_miss_punishment()
            return result
        elif self.phase == "phase2_active":
            return self._type_phase2_letter(button)
        return False

    def can_type_button(self, button: str) -> bool:
        """Check if button can be typed.

        Note: Projectiles are now standard enemies and handled by the game engine.
        """
        if self.phase == "phase1_active" and self.word_active:
            if self.word_typed_count < len(self.word_sequence):
                return self.word_sequence[self.word_typed_count] == button
        elif self.phase == "phase2_active":
            return self._can_type_phase2_button(button)
        return False

    def on_unmatched_input(self, key: str) -> bool:
        """Handle wrong key press by triggering punishment."""
        if self.phase != "phase1_active" or not self.word_active:
            return False
        self._trigger_word_miss_punishment()
        return True

    def _can_type_phase2_button(self, button: str) -> bool:
        """Check if a button can be typed in phase 2."""
        is_left_hand = button in LEFT_HAND_BUTTONS
        is_right_hand = button in RIGHT_HAND_BUTTONS

        if not is_left_hand and not is_right_hand:
            return False

        target_face = "left" if is_left_hand else "right"

        # Can always switch faces
        if self.phase2_engaged_face is not None and self.phase2_engaged_face != target_face:
            return True

        # Can engage if not yet engaged
        if self.phase2_engaged_face is None:
            return True

        # Check if button matches expected letter
        if target_face == "left":
            if not self.phase2_left_letters:
                return False
            if self.phase2_left_typed >= len(self.phase2_left_word):
                return False
            return button == self.phase2_left_word[self.phase2_left_typed]
        else:
            if not self.phase2_right_letters:
                return False
            word_len = len(self.phase2_right_word)
            if self.phase2_right_typed >= word_len:
                return False
            # Right-to-left: check from end of word
            letter_idx = word_len - 1 - self.phase2_right_typed
            return button == self.phase2_right_word[letter_idx]

    def is_complete(self) -> bool:
        """Check if boss is defeated."""
        return self.completed or self.defeated

    def get_width(self) -> float:
        """Get total width of boss."""
        return 300.0  # Approximate width of the SVG face

    def is_below_screen(self, bottom_y: float) -> bool:
        """Check if boss has moved below screen."""
        return self.boss_y - 150 < bottom_y

    def reset_typing_progress(self):
        """Boss doesn't reset typing progress."""

    def get_boss_radius(self) -> float:
        """Get boss radius for death animations."""
        return 150.0

    def get_center_position(self) -> Tuple[float, float]:
        """Get center position of boss."""
        return self.center_pos

    def _cleanup_curve_lists(self, curve_lists: List[List[pg.PlotCurveItem]]):
        """Helper to remove curves from multiple lists."""
        for curve_list in curve_lists:
            for curve in curve_list:
                if curve.scene():
                    self.view.removeItem(curve)
            curve_list.clear()

    def _cleanup_fill_item(self, fill_item: Optional[pg.PlotDataItem]) -> None:
        """Helper to remove a fill item."""
        if fill_item is not None and fill_item.scene():
            self.view.removeItem(fill_item)

    def cleanup(self):
        """Remove all visual elements."""
        # Remove stars plot item
        if self.stars_plot_item and self.stars_plot_item.scene():
            self.view.removeItem(self.stars_plot_item)
        self.stars_plot_item = None
        self.stars.clear()

        # Remove constellation lines
        for line_data in self.constellation_lines:
            if line_data["item"].scene():
                self.view.removeItem(line_data["item"])
        self.constellation_lines.clear()

        # Remove all face 1 curves
        self._cleanup_curve_lists(
            [
                self.svg_curves,
                self.svg_curves_layer1,
                self.svg_curves_layer2,
                self.eye_curves,
                self.eye_curves_layer1,
                self.eye_curves_layer2,
            ]
        )
        self._cleanup_fill_item(self.eye_fill)
        self.eye_fill = None

        # Remove all face 2 curves (phase 2)
        self._cleanup_curve_lists(
            [
                self.face2_curves,
                self.face2_curves_layer1,
                self.face2_curves_layer2,
                self.face2_eye_curves,
                self.face2_eye_curves_layer1,
                self.face2_eye_curves_layer2,
            ]
        )
        self._cleanup_fill_item(self.face2_eye_fill)
        self.face2_eye_fill = None

        # Remove target enemy (legacy, can remove later)
        if self.target_enemy:
            self.target_enemy.cleanup()
            self.target_enemy = None

        # Remove word attack elements
        self._cleanup_word_display()
        # Fully cleanup charge particle systems (removes ScatterPlotItems from view)
        self.charge_particles.cleanup()
        self.phase2_left_charge_particles.cleanup()
        self.phase2_right_charge_particles.cleanup()
        self._cleanup_projectiles()
        self._cleanup_fire_cone(immediate=True)
        self._cleanup_disable_cone(immediate=True)

        # Cleanup all exiting cones
        for cone in self.exiting_cones:
            cone.cleanup()
        self.exiting_cones.clear()

        # Cleanup phase 2 letters
        for letter in self.phase2_left_letters:
            letter.cleanup()
        self.phase2_left_letters.clear()

        for letter in self.phase2_right_letters:
            letter.cleanup()
        self.phase2_right_letters.clear()

        # Cleanup phase 2 fire cones
        if self.phase2_left_fire_cone:
            self.phase2_left_fire_cone.cleanup()
            self.phase2_left_fire_cone = None

        if self.phase2_right_fire_cone:
            self.phase2_right_fire_cone.cleanup()
            self.phase2_right_fire_cone = None

        # Remove trail surface
        if self.trail_image_item is not None and self.trail_image_item.scene():
            self.view.removeItem(self.trail_image_item)
            self.trail_image_item = None
        self.trail_pixmap = None

    def create_victory_animations(self):
        """Create victory animation for face boss defeat."""
        # pylint: disable=import-outside-toplevel
        from effects.boss_death_animation import BossDeathAnimation

        animation = BossDeathAnimation(self, self.view)
        animation.is_boss = True
        return [animation]
