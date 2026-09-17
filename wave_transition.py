"""Wave transition animation with waveform effect."""

import math
import time
import numpy as np
import pyqtgraph as pg
from font_manager import font_manager

WAVES_PER_BOSS = 4


class WaveTransition:
    """Animated wave transition effect between waves."""

    def __init__(
        self,
        view,
        wave_num: int,
        crosshair=None,
        player_waveform=None,
        is_first_wave=False,
        is_perfect_wave=False,
        sound_manager=None,
        cycle_perfect_waves=None,
    ):
        """Initialize wave transition."""
        self.view = view
        self.wave_num = wave_num
        self.sound_manager = sound_manager
        self.cycle_perfect_waves = cycle_perfect_waves or set()
        self.elapsed = 0.0
        self.phase = "entering"  # "entering", "displaying", "exiting"
        self.completed = False
        self.is_first_wave = is_first_wave  # Skip initial hide animation if first wave
        self.is_perfect_wave = is_perfect_wave  # Previous wave was perfect

        # Boss proximity: 0.0 = just after boss, 1.0 = boss wave
        position_in_cycle = wave_num % WAVES_PER_BOSS
        if position_in_cycle == 0 and wave_num > 0:
            self.boss_proximity = 1.0
            self.is_boss_wave = True
        else:
            self.boss_proximity = position_in_cycle / WAVES_PER_BOSS
            self.is_boss_wave = False

        # References to game elements to animate
        self.crosshair = crosshair
        self.player_waveform = player_waveform

        # Store original positions for restoration
        self.crosshair_original_y = -250 if crosshair else None
        self.waveform_original_y = -300 if player_waveform else None  # Bottom edge

        # Animation state for game elements
        self.elements_hidden = is_first_wave  # Already hidden if first wave
        self.elements_returning = False
        self.spawning_started = False  # Track if we've signaled to start spawning
        self.perfect_bonus_applied = False  # Track if we've applied the perfect wave bonus

        # Animation timing
        self.enter_duration = 0.8  # Time to animate in
        self.display_duration = 1.5 if is_perfect_wave else 1.0  # Longer display for perfect
        self.exit_duration = 0.6  # Time to animate out

        # Perfect wave color animation
        self.perfect_flash_timer = 0.0

        # Continuous time for waveform animation (doesn't reset between phases)
        self.total_time = 0.0

        # Waveform parameters
        self.amplitude = 60
        self.frequency = 8
        self.wave_width = 600
        self.num_points = 200

        # Visual elements
        self.waveform_lines = []
        self.wave_text = None
        self.background_glow = None
        self.pip_items = []

        self._create_waveform()
        self._create_text()
        self._create_pips()

        # Initial position (above screen)
        self.current_y = 400
        self._dt = 0.0

        # Pip slide-in animation: start off-screen right, slide in after title arrives
        self.pip_x_offset = 500  # Start off-screen to the right
        self.pip_slide_duration = 0.4
        self.pip_slide_timer = 0.0
        self.pip_sliding_in = False
        self.pip_arrived = False

        self._update_positions()

    def _create_waveform(self):
        """Create the animated waveform visual."""
        # Generate multiple waveform layers for depth
        # Always start with cyan colors - yellow flash happens during animation
        self.cyan_colors = [
            (0, 255, 255, 255),  # Bright cyan - main wave
            (0, 200, 255, 150),  # Blue - secondary wave
            (100, 255, 200, 100),  # Turquoise - tertiary wave
            (0, 150, 255, 80),  # Darker blue - background wave
        ]
        self.yellow_colors = [
            (255, 255, 0, 255),  # Bright yellow - main wave
            (255, 200, 0, 150),  # Gold - secondary wave
            (255, 255, 100, 100),  # Light yellow - tertiary wave
            (255, 180, 0, 80),  # Orange-gold - background wave
        ]
        self.cyan_glow = (0, 255, 255, 30)
        self.yellow_glow = (255, 255, 0, 30)

        # Start with cyan
        colors = self.cyan_colors
        glow_color = self.cyan_glow

        self.widths = [6, 8, 12, 16]  # Line widths for each layer

        for i, (color, width) in enumerate(zip(colors, self.widths)):
            # Create waveform line
            waveform = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=width))
            self.view.addItem(waveform)
            self.waveform_lines.append(waveform)

        # Create background glow effect
        self.background_glow = pg.PlotCurveItem(pen=pg.mkPen(color=glow_color, width=40))
        self.view.addItem(self.background_glow)

    def _create_text(self):
        """Create wave number text."""
        # Always start with white - yellow flash happens during animation
        text_color = (255, 255, 255)
        self.wave_text = pg.TextItem(
            text=f"WAVE {self.wave_num}", color=text_color, anchor=(0.5, 0.5)
        )
        self.wave_text.setFont(font_manager.get_title_font(36, bold=True))
        self.view.addItem(self.wave_text)

    def _create_pips(self):
        """Create progress pips showing position in boss cycle."""
        pip_count = WAVES_PER_BOSS
        self.pip_spacing = 28
        pip_radius = 7
        boss_pip_radius = 9
        total_width = (pip_count - 1) * self.pip_spacing

        position_in_cycle = self.wave_num % WAVES_PER_BOSS
        # How many waves completed in this cycle (for filling pips)
        if position_in_cycle == 0:
            completed = WAVES_PER_BOSS  # Boss wave = all completed
        else:
            completed = position_in_cycle

        # Current pip index (0-based)
        current_index = completed - 1
        prev_index = current_index - 1

        # First wave of a cycle: orb starts and ends on first pip
        is_cycle_start = position_in_cycle == 1
        if is_cycle_start:
            prev_index = 0

        # Store x positions for orb animation
        self.pip_start_x = -total_width / 2 + max(0, prev_index) * self.pip_spacing
        self.pip_end_x = -total_width / 2 + current_index * self.pip_spacing
        # Orb starts on the start pip, so it slides in with that pip's direction
        half = WAVES_PER_BOSS / 2
        self.orb_start_slide_dir = -1 if max(0, prev_index) < half else 1

        self.current_pip_is_boss = False

        # Map pip index to wave number for perfect wave lookup
        # Cycle start wave: e.g., for wave 6 with position_in_cycle=2, cycle started at wave 5
        cycle_start_wave = self.wave_num - completed + 1

        # Previous pip is perfect if current wave's previous wave was perfect
        perfect_index = prev_index if self.is_perfect_wave and not is_cycle_start else -1

        half = pip_count / 2
        for i in range(pip_count):
            x = -total_width / 2 + i * self.pip_spacing
            is_boss_pip = i == pip_count - 1
            is_current = i == current_index
            is_filled = i < completed
            radius = boss_pip_radius if is_boss_pip else pip_radius

            # Check if this pip's wave was perfect (from history or current transition)
            pip_wave = cycle_start_wave + i
            is_perfect = (
                i == perfect_index
                or (not is_boss_pip and is_filled and pip_wave in self.cycle_perfect_waves)
            )

            if is_boss_pip:
                pip = self._create_diamond_pip(x, radius, is_filled)
            elif is_perfect:
                pip = self._create_circle_pip(x, radius, is_filled, perfect=True)
            else:
                pip = self._create_circle_pip(x, radius, is_filled)

            # Left half slides in from left, right half from right
            pip._slide_dir = -1 if i < half else 1

            self.view.addItem(pip)
            self.pip_items.append(pip)

            if is_current:
                self.current_pip_is_boss = is_boss_pip

        # Store perfect pip x for explosion (only the just-completed perfect wave)
        self.perfect_pip_x = (
            -total_width / 2 + perfect_index * self.pip_spacing
            if perfect_index >= 0
            else None
        )

        # Create perfect pip explosion (hidden until orb departs)
        self._create_perfect_explosion()

        # Create arrival glow ring (hidden until orb arrives)
        self._create_arrival_glow()

        # Create traveling orb
        self._create_orb()

    def _create_circle_pip(self, x, radius, filled, perfect=False):
        """Create a circular pip marker."""
        angles = np.linspace(0, 2 * np.pi, 24)
        xs = x + radius * np.cos(angles)
        ys = radius * np.sin(angles)  # y offset applied in _update_positions

        if perfect:
            color = (255, 255, 0, 255)
            width = 3
        elif filled:
            color = (0, 255, 255, 230)
            width = 3
        else:
            color = (0, 255, 255, 100)
            width = 2

        pip = pg.PlotCurveItem(
            x=xs, y=ys, pen=pg.mkPen(color=color, width=width)
        )
        if filled or perfect:
            pip.setFillLevel(0)
            pip.setBrush(pg.mkBrush(*color[:3], 120 if not perfect else 180))

        return pip

    def _create_current_marker(self, x):
        """Create a small downward triangle above the current pip."""
        size = 5
        xs = np.array([x - size, x + size, x, x - size])
        ys = np.array([size * 2, size * 2, size * 0.5, size * 2])
        color = (255, 255, 255, 220)
        marker = pg.PlotCurveItem(
            x=xs, y=ys, pen=pg.mkPen(color=color, width=2)
        )
        marker.setFillLevel(0)
        marker.setBrush(pg.mkBrush(*color[:3], 140))
        return marker

    def _create_perfect_explosion(self):
        """Create explosion effect for perfect wave pip."""
        self.perfect_explosion = None
        self.perfect_triggered = False

        if not self.perfect_pip_x:
            return

    def _trigger_perfect_explosion(self):
        """Spawn a small explosion ring at the perfect pip."""
        from effects.explosions import ExplosionRing

        pip_y = self.current_y - 90
        self.perfect_explosion = ExplosionRing(
            center=(self.perfect_pip_x, pip_y),
            max_radius=15,
            color=(255, 255, 0),
            view=self.view,
            ring_type="normal",
        )

    def _update_perfect_explosion(self, dt):
        """Update the perfect wave pip explosion."""
        if not self.perfect_triggered or not self.perfect_explosion:
            return

        self.perfect_explosion.update(dt)
        if self.perfect_explosion.completed:
            self.perfect_explosion.cleanup()
            self.perfect_explosion = None

    def _create_arrival_glow(self):
        """Create an expanding glow ring that plays when the orb arrives."""
        if self.current_pip_is_boss:
            color = (255, 80, 80)
        else:
            color = (0, 255, 255)
        self.arrival_color = color

        angles = np.linspace(0, 2 * np.pi, 30)
        self.arrival_ring = pg.PlotCurveItem(
            x=np.cos(angles), y=np.sin(angles),
            pen=pg.mkPen(color=(*color, 0), width=2),
        )
        self.arrival_ring.setVisible(False)
        self.view.addItem(self.arrival_ring)

        self.arrival_triggered = False
        self.arrival_timer = 0.0
        self.arrival_duration = 0.6

    def _update_arrival_glow(self, dt):
        """Animate the expanding glow ring after orb arrives."""
        if not self.arrival_triggered:
            return

        self.arrival_timer += dt
        t = min(self.arrival_timer / self.arrival_duration, 1.0)
        # Expand radius, fade out alpha
        radius = 6 + 20 * t
        alpha = int(255 * (1 - t))

        pip_y = self.current_y - 90
        angles = np.linspace(0, 2 * np.pi, 30)
        self.arrival_ring.setVisible(True)
        self.arrival_ring.setData(
            x=self.pip_end_x + radius * np.cos(angles),
            y=pip_y + radius * np.sin(angles),
        )
        self.arrival_ring.setPen(
            pg.mkPen(color=(*self.arrival_color, alpha), width=max(1, 3 - 2 * t))
        )

        if t >= 1.0:
            self.arrival_ring.setVisible(False)

    def _create_orb(self):
        """Create a glowing orb that travels from previous pip to current."""
        orb_color = (220, 80, 255, 255)
        glow_color = (220, 80, 255, 60)

        orb_radius = 4
        glow_radius = 12
        angles = np.linspace(0, 2 * np.pi, 20)

        # Bright core
        self.orb_core = pg.PlotCurveItem(
            x=orb_radius * np.cos(angles),
            y=orb_radius * np.sin(angles),
            pen=pg.mkPen(color=orb_color, width=2),
        )
        self.orb_core.setFillLevel(0)
        self.orb_core.setBrush(pg.mkBrush(*orb_color[:3], 200))
        self.view.addItem(self.orb_core)

        # Soft glow
        self.orb_glow = pg.PlotCurveItem(
            x=glow_radius * np.cos(angles),
            y=glow_radius * np.sin(angles),
            pen=pg.mkPen(color=(*glow_color[:3], 0), width=1),
        )
        self.orb_glow.setFillLevel(0)
        self.orb_glow.setBrush(pg.mkBrush(*glow_color))
        self.view.addItem(self.orb_glow)

        self.orb_progress = 0.0
        self.orb_duration = 0.5  # Fast travel

    def _update_orb(self):
        """Update orb position along the pip track."""
        if not hasattr(self, 'orb_core'):
            return

        # Ease-in-out for snappy travel with smooth start and stop
        t = min(self.orb_progress / self.orb_duration, 1.0)
        if t < 0.5:
            eased = 4 * t * t * t
        else:
            eased = 1 - (-2 * t + 2) ** 3 / 2

        # Trigger arrival glow when orb reaches destination
        if t >= 1.0 and not self.arrival_triggered:
            self.arrival_triggered = True

        orb_x = self.pip_start_x + (self.pip_end_x - self.pip_start_x) * eased
        # Apply slide offset so orb moves with start pip during slide-in
        orb_x += self.pip_x_offset * self.orb_start_slide_dir
        pip_y = self.current_y - 90

        # Pulse the glow
        pulse = 1.0 + 0.3 * math.sin(self.total_time * 8)
        glow_radius = 12 * pulse
        angles = np.linspace(0, 2 * np.pi, 20)

        orb_radius = 4
        self.orb_core.setData(
            x=orb_x + orb_radius * np.cos(angles),
            y=pip_y + orb_radius * np.sin(angles),
        )
        self.orb_glow.setData(
            x=orb_x + glow_radius * np.cos(angles),
            y=pip_y + glow_radius * np.sin(angles),
        )

    def _create_diamond_pip(self, x, radius, filled):
        """Create a diamond-shaped pip for boss wave."""
        r = radius * 1.3
        xs = np.array([x, x + r, x, x - r, x])
        ys = np.array([r, 0, -r, 0, r])

        if filled:
            color = (255, 80, 80, 255)
            width = 3
        else:
            color = (255, 80, 80, 140)
            width = 2

        pip = pg.PlotCurveItem(
            x=xs, y=ys, pen=pg.mkPen(color=color, width=width)
        )
        if filled:
            pip.setFillLevel(0)
            pip.setBrush(pg.mkBrush(*color[:3], 140))

        return pip

    def _generate_waveform_points(self, y_center: float, time_offset: float = 0):
        """Generate waveform points for given center Y and time."""
        x_points = np.linspace(-self.wave_width / 2, self.wave_width / 2, self.num_points)

        # Create complex waveform with multiple frequencies
        base_wave = np.sin(x_points / 30 + time_offset * 3)
        detail_wave = 0.3 * np.sin(x_points / 8 + time_offset * 8)
        modulation = 0.2 * np.sin(time_offset * 5)

        y_points = y_center + self.amplitude * (base_wave + detail_wave) * (1 + modulation)

        # Boss proximity interference: subtle noise and discordant frequencies
        if self.boss_proximity > 0.25:
            intensity = (self.boss_proximity - 0.25) / 0.75  # 0 to 1 over the ramp

            # High-frequency jagged interference (subtle)
            noise_freq = 20 + intensity * 20
            interference = intensity * self.amplitude * 0.12 * np.sin(
                x_points / 5 + time_offset * noise_freq
            )

            # Gentle glitch using multiplied incommensurate sines
            glitch = (
                intensity
                * self.amplitude
                * 0.08
                * np.sin(x_points * 0.7 + time_offset * 17.3)
                * np.sin(x_points * 0.13 + time_offset * 7.1)
            )

            # Occasional stutter: dampen short segments slightly
            if self.boss_proximity > 0.5:
                stutter_intensity = (self.boss_proximity - 0.5) / 0.5
                gap_wave = np.sin(x_points / 20 + time_offset * 4.7)
                gap_mask = np.where(gap_wave > (1.0 - stutter_intensity * 0.3), 0.7, 1.0)
                y_points = y_center + (y_points - y_center) * gap_mask

            y_points += interference + glitch

        return x_points, y_points

    def _update_positions(self):
        """Update positions of all visual elements."""
        # Use total_time for continuous waveform animation (no jumps between phases)
        time_offset = self.total_time * 2  # Animation speed multiplier

        # Calculate yellow flash blend for perfect wave (0.5 second flash)
        # Uses total elapsed time from start of transition, not just display phase
        yellow_blend = 0.0
        total_elapsed = self.perfect_flash_timer
        if self.is_perfect_wave and total_elapsed < 1.5:
            # Flash to yellow and back over 0.5 seconds using sine curve
            flash_progress = total_elapsed / 1.5
            yellow_blend = math.sin(flash_progress * math.pi)

        # Generate waveform points for each layer with slight offsets
        for i, waveform in enumerate(self.waveform_lines):
            layer_offset = i * 0.2  # Slight phase offset between layers
            layer_amplitude = self.amplitude * (1.0 - i * 0.1)  # Decreasing amplitude

            # Temporarily adjust amplitude for this layer
            original_amplitude = self.amplitude
            self.amplitude = layer_amplitude

            x_points, y_points = self._generate_waveform_points(
                self.current_y, time_offset + layer_offset
            )

            self.amplitude = original_amplitude  # Restore original amplitude

            # Blend colors for perfect wave flash
            if yellow_blend > 0:
                cyan = self.cyan_colors[i]
                yellow = self.yellow_colors[i]
                blended = tuple(
                    int(cyan[j] + (yellow[j] - cyan[j]) * yellow_blend) for j in range(4)
                )
                waveform.setData(
                    x=x_points, y=y_points, pen=pg.mkPen(color=blended, width=self.widths[i])
                )
            else:
                waveform.setData(x=x_points, y=y_points)

        # Update background glow with color blending
        glow_x, glow_y = self._generate_waveform_points(self.current_y, time_offset)
        if yellow_blend > 0:
            blended_glow = tuple(
                int(self.cyan_glow[j] + (self.yellow_glow[j] - self.cyan_glow[j]) * yellow_blend)
                for j in range(4)
            )
            self.background_glow.setData(
                x=glow_x, y=glow_y, pen=pg.mkPen(color=blended_glow, width=40)
            )
        else:
            self.background_glow.setData(x=glow_x, y=glow_y)

        # Update text position and color
        self.wave_text.setPos(0, self.current_y)

        # Update pip positions (below the waveform, slide in from sides)
        pip_y = self.current_y - 90
        for pip in self.pip_items:
            data = pip.getData()
            if data[0] is not None and data[1] is not None:
                if not hasattr(pip, '_base_x'):
                    pip._base_x = data[0].copy()
                    pip._base_y = data[1].copy()
                slide_dir = pip._slide_dir if hasattr(pip, '_slide_dir') else 1
                pip.setData(
                    x=pip._base_x + self.pip_x_offset * slide_dir,
                    y=pip._base_y + pip_y,
                )

        # Update orb position
        self._update_orb()

        # Update arrival glow
        self._update_arrival_glow(self._dt)
        self._update_perfect_explosion(self._dt)

    def _animate_elements_off_screen(self, progress):
        """Animate crosshair and player waveform off the bottom of the screen."""
        if not self.crosshair and not self.player_waveform:
            return

        # Smooth easing for sliding off
        eased_progress = progress**2  # Ease in

        # Animate crosshair down and off screen
        if self.crosshair:
            crosshair_offset = 200 * eased_progress  # Move 200 pixels down
            new_crosshair_y = self.crosshair_original_y - crosshair_offset
            # Update crosshair's resting position temporarily
            self.crosshair.current_pos = (
                self.crosshair.current_pos[0],
                new_crosshair_y,
            )
            self.crosshair._update_crosshair_position(self.crosshair.current_pos)

        # Animate player waveform down and off screen
        if self.player_waveform:
            waveform_offset = 150 * eased_progress  # Move 150 pixels down
            self.player_waveform.base_y = self.waveform_original_y - waveform_offset

    def _animate_elements_on_screen(self, progress):
        """Animate crosshair and player waveform back to original positions."""
        if not self.crosshair and not self.player_waveform:
            return

        # Smooth easing for sliding back on
        eased_progress = 1 - (1 - progress) ** 3  # Ease out

        # Animate crosshair back up
        if self.crosshair:
            crosshair_offset = 200 * (1 - eased_progress)  # Restore from offset
            new_crosshair_y = self.crosshair_original_y - crosshair_offset
            self.crosshair.current_pos = (
                self.crosshair.current_pos[0],
                new_crosshair_y,
            )
            self.crosshair._update_crosshair_position(self.crosshair.current_pos)

        # Animate player waveform back up
        if self.player_waveform:
            waveform_offset = 150 * (1 - eased_progress)  # Restore from offset
            self.player_waveform.base_y = self.waveform_original_y - waveform_offset

            # Apply perfect wave bonus when elements start returning
            if self.is_perfect_wave and not self.perfect_bonus_applied:
                self.perfect_bonus_applied = True
                # Trigger yellow flash animation
                self.player_waveform.trigger_perfect_wave_bonus()

    def update(self, dt: float) -> bool:
        """Update animation. Returns True if still active."""
        if self.completed:
            return False

        self.elapsed += dt
        self.total_time += dt  # Continuous time for waveform animation
        self._dt = dt

        # Advance orb only after pips have slid into position
        if self.pip_arrived and hasattr(self, 'orb_progress'):
            # Trigger perfect explosion when orb first starts moving
            if self.orb_progress == 0.0 and self.is_perfect_wave and not self.perfect_triggered:
                self.perfect_triggered = True
                self._trigger_perfect_explosion()
                if self.sound_manager:
                    self.sound_manager.play_explosion_sound(volume=0.15)
            self.orb_progress += dt

        if self.phase == "entering":
            # Update perfect flash timer from the start
            if self.is_perfect_wave:
                self.perfect_flash_timer += dt

            # Animate from top to center
            progress = min(self.elapsed / self.enter_duration, 1.0)
            # Smooth easing function
            eased_progress = 1 - (1 - progress) ** 3

            # Animate from Y=400 to Y=0 (screen center)
            self.current_y = 400 - (400 * eased_progress)

            # Also animate game elements off screen during wave enter
            # Skip this for first wave since elements already start off-screen
            if not self.is_first_wave:
                self._animate_elements_off_screen(progress)

            if progress >= 1.0:
                self.phase = "displaying"
                self.elapsed = 0.0
                self.elements_hidden = True
                self.pip_sliding_in = True

        elif self.phase == "displaying":
            # Continue updating perfect flash timer
            if self.is_perfect_wave:
                self.perfect_flash_timer += dt

            # Animate pips sliding in from right
            if self.pip_sliding_in and not self.pip_arrived:
                self.pip_slide_timer += dt
                t = min(self.pip_slide_timer / self.pip_slide_duration, 1.0)
                eased = 1 - (1 - t) ** 3  # Ease-out
                self.pip_x_offset = 500 * (1 - eased)
                if t >= 1.0:
                    self.pip_x_offset = 0
                    self.pip_arrived = True

            # Hold in center with pulsing effect
            if self.elapsed >= self.display_duration:
                self.phase = "exiting"
                self.elapsed = 0.0
                # Don't return True here - wait for exiting phase
            else:
                # Gentle pulse effect while displaying
                pulse = 1.0 + 0.1 * math.sin(self.elapsed * 8)
                original_amplitude = self.amplitude
                self.amplitude *= pulse
                self._update_positions()
                self.amplitude = original_amplitude
            return False

        elif self.phase == "exiting":
            # Animate from center to bottom
            progress = min(self.elapsed / self.exit_duration, 1.0)

            # Return True once when exiting phase starts to signal spawning should begin
            if not self.spawning_started:
                self.spawning_started = True
                return True  # Signal that wave spawning should start

            # Smooth easing function
            eased_progress = progress**3

            # Animate from Y=0 to Y=-400 (off bottom)
            self.current_y = 0 - (400 * eased_progress)

            # Animate game elements back on screen as wave title exits
            self._animate_elements_on_screen(progress)
            self.elements_returning = True

            if progress >= 1.0:
                self.completed = True
                # Ensure elements are fully restored
                if self.crosshair:
                    self.crosshair.current_pos = (
                        self.crosshair.current_pos[0],
                        self.crosshair_original_y,
                    )
                    self.crosshair.resting_pos = (
                        0,
                        self.crosshair_original_y,
                    )  # Restore resting position
                    self.crosshair._update_crosshair_position(self.crosshair.current_pos)
                if self.player_waveform:
                    self.player_waveform.base_y = self.waveform_original_y
                return False

        self._update_positions()
        return False  # Don't start spawning during enter/exit phases

    def is_ready_to_spawn(self) -> bool:
        """Check if wave is ready to start spawning enemies."""
        return self.phase == "exiting"

    def is_completed(self) -> bool:
        """Check if transition is completely finished."""
        return self.completed

    def cleanup(self):
        """Remove all visual elements."""
        for waveform in self.waveform_lines:
            self.view.removeItem(waveform)

        if self.background_glow:
            self.view.removeItem(self.background_glow)

        if self.wave_text:
            self.view.removeItem(self.wave_text)

        for pip in self.pip_items:
            self.view.removeItem(pip)

        if hasattr(self, 'perfect_explosion') and self.perfect_explosion:
            self.perfect_explosion.cleanup()
            self.perfect_explosion = None
        if hasattr(self, 'arrival_ring') and self.arrival_ring:
            self.view.removeItem(self.arrival_ring)
            self.arrival_ring = None
        if hasattr(self, 'orb_core') and self.orb_core:
            self.view.removeItem(self.orb_core)
            self.orb_core = None
        if hasattr(self, 'orb_glow') and self.orb_glow:
            self.view.removeItem(self.orb_glow)
            self.orb_glow = None

        self.waveform_lines.clear()
        self.background_glow = None
        self.wave_text = None
        self.pip_items.clear()
