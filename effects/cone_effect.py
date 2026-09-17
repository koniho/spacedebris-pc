"""Cone effect with animated waveform edges and smooth entry/exit animations."""

import math
from typing import List, Tuple

import pyqtgraph as pg


class ConeEffect:
    """A translucent cone with animated waveform edges.

    Supports smooth entry and exit animations:
    - Entry Phase 1 (0.3s): All rays animate from source to target center
    - Entry Phase 2 (0.3s): Rays spread out from target center to final positions
    - Exit (0.3s): Ray start points animate from source to target point
    """

    # Animation phases
    PHASE_ENTRY_CONVERGE = "entry_converge"  # Rays go from source to target center
    PHASE_ENTRY_SPREAD = "entry_spread"  # Rays spread from center to final positions
    PHASE_ACTIVE = "active"  # Normal operation
    PHASE_EXIT = "exit"  # Ray starts move toward target
    PHASE_DONE = "done"  # Animation complete, ready for cleanup

    def __init__(
        self,
        view,
        source: Tuple[float, float],
        target_y: float,
        target_width: float,
        color: Tuple[int, int, int],
        num_interior: int = 10,
        opacity_mult: float = 1.0,
        width_mult: float = 1.0,
        waveform=None,
    ):
        """Create a cone effect.

        Args:
            view: PyQtGraph view to add items to
            source: (x, y) origin point of the cone
            target_y: Y position of the target (cone extends to this Y)
            target_width: Half-width of the cone at the target
            color: RGB tuple for cone color
            num_interior: Number of interior waveform lines
            opacity_mult: Multiplier for opacity (1.0 = normal)
            width_mult: Multiplier for line width (1.0 = normal)
            waveform: Optional player waveform to extend rays to
        """
        self.view = view
        self.source = source
        self.target_y = target_y
        self.target_width = target_width
        self.color = color
        self.num_interior = num_interior
        self.opacity_mult = opacity_mult
        self.width_mult = width_mult
        self.waveform = waveform

        # Animation state
        self.time = 0.0
        self.phase = self.PHASE_ENTRY_CONVERGE
        self.phase_timer = 0.0
        self.entry_duration = 0.3
        self.exit_duration = 0.3
        self.active = True

        # Calculate target center (used for animations)
        self.target_x = 0  # Center of screen
        self.target_center = (self.target_x, self.target_y)

        # Create visual elements
        self._create_visual_elements()

    def _create_visual_elements(self):
        """Create all the visual elements for the cone."""
        # Z values: face is 3-5, cones should be 6-7 (above face, below enemies)
        edge_color = (*self.color, 150)

        self.edge_left = pg.PlotCurveItem(pen=pg.mkPen(color=edge_color, width=2))
        self.edge_left.setZValue(7)
        self.view.addItem(self.edge_left)

        self.edge_right = pg.PlotCurveItem(pen=pg.mkPen(color=edge_color, width=2))
        self.edge_right.setZValue(7)
        self.view.addItem(self.edge_right)

        # Create interior waveforms
        interior_color = (
            int(self.color[0] * 0.8),
            int(self.color[1] * 0.6),
            int(self.color[2] * 0.5),
            80,
        )
        self.interior: List[pg.PlotCurveItem] = []
        for _ in range(self.num_interior):
            curve = pg.PlotCurveItem(pen=pg.mkPen(color=interior_color, width=1))
            curve.setZValue(6.5)
            self.view.addItem(curve)
            self.interior.append(curve)

    def set_source(self, source: Tuple[float, float]):
        """Update the source position."""
        self.source = source

    def start_exit(self):
        """Begin exit animation."""
        if self.phase not in (self.PHASE_EXIT, self.PHASE_DONE):
            self.phase = self.PHASE_EXIT
            self.phase_timer = 0.0

    def is_done(self) -> bool:
        """Check if cone is done and ready for cleanup."""
        return self.phase == self.PHASE_DONE

    def update(self, dt: float, external_timer: float = 0.0):
        """Update the cone effect.

        Args:
            dt: Delta time
            external_timer: External timer for pulsing effects (e.g., fire_timer)
        """
        if not self.active:
            return

        self.time += dt
        self.phase_timer += dt

        # Handle phase transitions
        if self.phase == self.PHASE_ENTRY_CONVERGE:
            if self.phase_timer >= self.entry_duration:
                self.phase = self.PHASE_ENTRY_SPREAD
                self.phase_timer = 0.0
        elif self.phase == self.PHASE_ENTRY_SPREAD:
            if self.phase_timer >= self.entry_duration:
                self.phase = self.PHASE_ACTIVE
                self.phase_timer = 0.0
        elif self.phase == self.PHASE_EXIT:
            if self.phase_timer >= self.exit_duration:
                self.phase = self.PHASE_DONE
                self.active = False
                return

        # Calculate animation factors
        entry_converge_factor = self._get_entry_converge_factor()
        entry_spread_factor = self._get_entry_spread_factor()
        exit_factor = self._get_exit_factor()

        # Update visual elements
        self._update_visuals(
            external_timer, entry_converge_factor, entry_spread_factor, exit_factor
        )

    def _get_entry_converge_factor(self) -> float:
        """Get the entry converge animation factor (0 = at source, 1 = at target center)."""
        if self.phase == self.PHASE_ENTRY_CONVERGE:
            progress = min(1.0, self.phase_timer / self.entry_duration)
            # Ease out for smooth arrival
            return 1.0 - (1.0 - progress) ** 2
        if self.phase in (
            self.PHASE_ENTRY_SPREAD,
            self.PHASE_ACTIVE,
            self.PHASE_EXIT,
            self.PHASE_DONE,
        ):
            return 1.0
        return 0.0

    def _get_entry_spread_factor(self) -> float:
        """Get the entry spread animation factor (0 = at center, 1 = fully spread)."""
        if self.phase == self.PHASE_ENTRY_CONVERGE:
            return 0.0
        if self.phase == self.PHASE_ENTRY_SPREAD:
            progress = min(1.0, self.phase_timer / self.entry_duration)
            # Ease out for smooth spread
            return 1.0 - (1.0 - progress) ** 2
        return 1.0

    def _get_exit_factor(self) -> float:
        """Get the exit animation factor (0 = normal, 1 = ray starts at target)."""
        if self.phase == self.PHASE_EXIT:
            progress = min(1.0, self.phase_timer / self.exit_duration)
            # Ease in for accelerating exit
            return progress**2
        return 0.0

    def _update_visuals(
        self,
        timer: float,
        entry_converge: float,
        entry_spread: float,
        exit_factor: float,
    ):
        """Update all visual elements based on animation state."""
        # Calculate base cone geometry
        dx = self.target_x - self.source[0]
        dy = self.target_y - self.source[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return

        dir_x = dx / dist
        dir_y = dy / dist
        perp_x = -dir_y
        perp_y = dir_x

        # Calculate animated target width (for entry spread animation)
        # During entry converge, width is 0 (all rays go to center)
        # During entry spread, width expands from 0 to target_width
        animated_width = self.target_width * entry_spread

        # Calculate target X positions for left and right edges
        target_left_x = self.target_x + perp_x * animated_width
        target_right_x = self.target_x - perp_x * animated_width

        # Get waveform Y at each edge position (or use fallback)
        if self.waveform:
            target_center_y = self.waveform.get_y_at_x(self.target_x)
            target_left_y = self.waveform.get_y_at_x(target_left_x)
            target_right_y = self.waveform.get_y_at_x(target_right_x)
        else:
            target_center_y = self.target_y
            target_left_y = self.target_y
            target_right_y = self.target_y

        # Calculate animated end positions
        # During entry converge, rays go from source toward target center
        if entry_converge < 1.0:
            # Entry converge phase: rays going from source to target center
            end_x = self.source[0] + (self.target_x - self.source[0]) * entry_converge
            end_y = self.source[1] + (target_center_y - self.source[1]) * entry_converge
            end_left_x = end_x
            end_left_y = end_y
            end_right_x = end_x
            end_right_y = end_y
        else:
            # Entry spread or active phase: rays reach waveform at their X positions
            end_left_x = target_left_x
            end_left_y = target_left_y
            end_right_x = target_right_x
            end_right_y = target_right_y

        # Calculate start positions for edges
        # During exit, each ray's start moves independently toward its end
        left_start_x = self.source[0] + (end_left_x - self.source[0]) * exit_factor
        left_start_y = self.source[1] + (end_left_y - self.source[1]) * exit_factor
        right_start_x = self.source[0] + (end_right_x - self.source[0]) * exit_factor
        right_start_y = self.source[1] + (end_right_y - self.source[1]) * exit_factor

        # Generate waveform edges
        left_x, left_y = self._generate_waveform_edge(
            left_start_x, left_start_y, end_left_x, end_left_y, 1
        )
        right_x, right_y = self._generate_waveform_edge(
            right_start_x, right_start_y, end_right_x, end_right_y, -1
        )

        self.edge_left.setData(x=left_x, y=left_y)
        self.edge_right.setData(x=right_x, y=right_y)

        pulse = 0.5 + 0.5 * math.sin(timer * 10)

        # Update interior waveforms
        for i, interior_curve in enumerate(self.interior):
            blend = (i + 1) / (self.num_interior + 1)
            center_factor = 1.0 - abs(blend - 0.5) * 2
            line_width = (1 + center_factor * 4) * self.width_mult

            # Calculate this ray's end position
            if entry_converge < 1.0:
                # All rays converge to same point during entry
                int_end_x = end_left_x
                int_end_y = end_left_y
            else:
                # Calculate this ray's X position based on blend
                int_end_x = target_left_x + (target_right_x - target_left_x) * blend
                # Get waveform Y at this ray's X position
                if self.waveform:
                    int_end_y = self.waveform.get_y_at_x(int_end_x)
                else:
                    int_end_y = self.target_y

            # Calculate this ray's start position (independent exit animation)
            int_start_x = self.source[0] + (int_end_x - self.source[0]) * exit_factor
            int_start_y = self.source[1] + (int_end_y - self.source[1]) * exit_factor

            interior_x, interior_y = self._generate_interior_waveform(
                int_start_x, int_start_y, int_end_x, int_end_y, blend, center_factor
            )

            interior_alpha = min(
                255, int((40 + 40 * center_factor) * (0.7 + 0.3 * pulse) * self.opacity_mult)
            )
            interior_color = (
                int(self.color[0] * 0.8),
                int(self.color[1] * 0.6),
                int(self.color[2] * 0.5),
                interior_alpha,
            )

            interior_curve.setData(x=interior_x, y=interior_y)
            interior_curve.setPen(pg.mkPen(color=interior_color, width=int(line_width)))

        # Update edge colors
        edge_alpha = min(255, int((100 + 80 * pulse) * self.opacity_mult))
        edge_color = (*self.color, edge_alpha)
        self.edge_left.setPen(pg.mkPen(color=edge_color, width=2))
        self.edge_right.setPen(pg.mkPen(color=edge_color, width=2))

    def _generate_waveform_edge(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        side: int,
    ) -> Tuple[List[float], List[float]]:
        """Generate a waveform along a cone edge."""
        num_points = 30
        edge_x = []
        edge_y = []

        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return [start_x], [start_y]

        dir_x = dx / length
        dir_y = dy / length
        perp_x = -dir_y * side
        perp_y = dir_x * side

        for idx in range(num_points + 1):
            progress = idx / num_points
            base_x = start_x + dx * progress
            base_y = start_y + dy * progress

            amplitude = 8 * progress
            wave1 = math.sin(progress * 20 + self.time * 15) * amplitude
            wave2 = math.sin(progress * 35 + self.time * 25) * amplitude * 0.5
            wave = wave1 + wave2

            edge_x.append(base_x + perp_x * wave)
            edge_y.append(base_y + perp_y * wave)

        return edge_x, edge_y

    def _generate_interior_waveform(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        blend: float,
        center_factor: float,
    ) -> Tuple[List[float], List[float]]:
        """Generate an interior waveform for a cone."""
        num_points = 25
        wave_x = []
        wave_y = []

        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return [start_x], [start_y]

        dir_x = dx / length
        dir_y = dy / length
        perp_x = -dir_y
        perp_y = dir_x

        phase_offset = blend * 10 + self.time * 12

        for idx in range(num_points + 1):
            progress = idx / num_points
            base_x = start_x + dx * progress
            base_y = start_y + dy * progress

            base_amplitude = 6 * progress
            amplitude = base_amplitude * (0.5 + center_factor * 0.8)

            wave = math.sin(progress * 18 + phase_offset) * amplitude
            wave += math.sin(progress * 30 + phase_offset * 1.5) * amplitude * 0.4

            wave_x.append(base_x + perp_x * wave)
            wave_y.append(base_y + perp_y * wave)

        return wave_x, wave_y

    def cleanup(self):
        """Remove all visual elements from the view."""
        if self.edge_left and self.edge_left.scene():
            self.view.removeItem(self.edge_left)
        if self.edge_right and self.edge_right.scene():
            self.view.removeItem(self.edge_right)
        for curve in self.interior:
            if curve.scene():
                self.view.removeItem(curve)
        self.active = False
