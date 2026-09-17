"""Arcade high score board screen."""

import math
import random_manager
import numpy as np
import pyqtgraph as pg
from font_manager import font_manager
from config import (
    BUTTON_COLORS,
    ALL_BUTTONS,
    LEFT_HAND_BUTTONS,
    RIGHT_HAND_BUTTONS,
    get_button_label,
)
from effects.explosions import ExplosionRing
from effects.intro_effects import ExpandingRingEffect, IntroLaserEffect
from typing_handler import SimultaneousInputTracker

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class HighScoreScreen:
    """High score board with name entry and animated insertion."""

    def __init__(self, view, config, final_score, final_wave, game_engine=None, stats=None):
        self.view = view
        self.config = config
        self.game_engine = game_engine
        self.final_score = final_score
        self.final_wave = final_wave
        self.stats = stats or {"key_presses": 0, "enemies_destroyed": 0, "misses": 0, "perfect_waves": 0}
        self.elapsed_time = 0.0
        self.active = True

        self.high_score_board = game_engine.high_score_board
        self.qualifies = self.high_score_board.qualifies(final_score)
        self.qualifying_rank = (
            self.high_score_board.get_qualifying_rank(final_score) if self.qualifies else -1
        )

        # Compute bosses defeated
        from wave_transition import WAVES_PER_BOSS
        self.bosses = (final_wave - 1) // WAVES_PER_BOSS
        self.difficulty = getattr(config.spawning, "current_difficulty", "normal").upper()
        self.perfect_waves = self.stats.get("perfect_waves", 0)

        # Input tracking with simultaneous press detection
        self.input_tracker = SimultaneousInputTracker(sync_window_ms=100)
        self.confirm_buttons = {LEFT_HAND_BUTTONS[-1], RIGHT_HAND_BUTTONS[0]}
        self.left_button = LEFT_HAND_BUTTONS[-1]
        self.right_button = RIGHT_HAND_BUTTONS[0]

        # Deferred cycle: queue direction on key press, flush after sync window
        self.pending_cycle = None  # direction int
        self.pending_cycle_age = 0  # ms since queued, advanced in update

        # Phase: "name_entry", "insertion", "display"
        if self.qualifies:
            self.phase = "name_entry"
        else:
            self.phase = "display"

        # Name entry state
        self.letters = [0, 0, 0]  # Indices into LETTERS
        self.current_pos = 0
        self.name_confirmed = False
        self.name_entry_pause_timer = 0.0
        self.name_entry_items = []
        self.letter_explosions = []

        # Insertion animation state
        self.insertion_timer = 0.0
        self.insertion_duration = 2.5
        self.insertion_phase = "idle"  # "slide_in", "impact", "cascade", "settle", "done"
        self.new_rank = -1
        self.row_items = []  # List of dicts with items and positions per row
        self.displaced_explosions = []
        self.cascade_index = 0
        self.cascade_timer = 0.0

        # Exit explosion state (same pattern as GameOverScreen)
        self.exploding = False
        self.explosion_start_time = 0.0
        self.explosion_duration = 0.8
        self.elements_cleared = False
        self.on_restart_callback = None
        self.all_elements = []
        self.center_ring = None

        # Fade-in
        self.fade_in_duration = 0.5
        self.fade_in_progress = 0.0

        # Display phase input gating — blocked until exit buttons are shown
        self.exit_ready = False

        # Button press effects (rings + lasers like intro screen)
        self.active_effects = []
        self.button_positions = {}  # Set by _create_button_indicators

        # Waveform animation on link line (partial press feedback)
        self.waveform_intensity = 0.0
        self.waveform_decay_rate = 3.0
        self.waveform_time = 0.0
        self.link_waveform = None
        self.combo_line = None
        self.combo_line_glow = None
        self.line_start_x = 0
        self.line_end_x = 0
        self.line_y = 0

        # Partial press flash
        self.partial_press_triggered = False
        self.partial_press_flash_time = 0.0
        self.partial_press_flash_duration = 0.2
        self.partial_flash_button = None

        # Board layout
        self.title_y = 260
        self.row_start_y = 200
        self.row_spacing = 38
        self.row_target_positions = []  # Final y positions per row

        if self.phase == "name_entry":
            self._create_name_entry()
        else:
            self._create_board()

        self._set_initial_opacity()

    # ── Name Entry ──────────────────────────────────────────────

    def _create_name_entry(self):
        """Create the name entry UI."""
        # Title
        title = pg.TextItem(text="NEW HIGH SCORE!", color=(255, 255, 0), anchor=(0.5, 0.5))
        title.setFont(font_manager.get_title_font(48, bold=True))
        title.setPos(0, 180)
        self.view.addItem(title)
        self.all_elements.append({"item": title, "pos": (0, 180)})
        self.name_entry_items.append(title)

        # Score display
        score_text = pg.TextItem(
            text=f"SCORE: {self.final_score:,}", color=(0, 255, 255), anchor=(0.5, 0.5)
        )
        score_text.setFont(font_manager.get_subtitle_font(24, bold=True))
        score_text.setPos(0, 120)
        self.view.addItem(score_text)
        self.all_elements.append({"item": score_text, "pos": (0, 120)})
        self.name_entry_items.append(score_text)

        # Instruction
        instr = pg.TextItem(text="ENTER YOUR NAME", color=(180, 180, 180), anchor=(0.5, 0.5))
        instr.setFont(font_manager.get_subtitle_font(18))
        instr.setPos(0, 70)
        self.view.addItem(instr)
        self.all_elements.append({"item": instr, "pos": (0, 70)})
        self.name_entry_items.append(instr)

        # Letter slots with underlines
        self.letter_texts = []
        self.letter_underlines = []
        spacing = 70
        for i in range(3):
            x = (i - 1) * spacing
            y = 0

            # Letter text
            letter = pg.TextItem(text=LETTERS[0], color=(255, 255, 255), anchor=(0.5, 0.5))
            letter.setFont(font_manager.get_title_font(40, bold=True))
            letter.setPos(x, y)
            self.view.addItem(letter)
            self.all_elements.append({"item": letter, "pos": (x, y)})
            self.name_entry_items.append(letter)
            self.letter_texts.append(letter)

            # Thick underline
            underline_hw = 18  # half-width
            underline_y = y - 28
            underline = pg.PlotCurveItem(
                x=np.array([x - underline_hw, x + underline_hw]),
                y=np.array([underline_y, underline_y]),
                pen=pg.mkPen(color=(0, 255, 255, 120), width=4),
            )
            self.view.addItem(underline)
            self.all_elements.append({"item": underline, "pos": (x, underline_y)})
            self.name_entry_items.append(underline)
            self.letter_underlines.append(underline)

        # Hexagon button indicators for name entry
        self._create_button_indicators(y=-100, include_all=True, items_list=self.name_entry_items)

    def _update_name_entry(self, dt):
        """Update name entry animations."""
        if self.name_confirmed:
            self.name_entry_pause_timer += dt

            # Flash all letters white then glow bright before transition
            t = self.name_entry_pause_timer
            if t < 0.15:
                # Snap to white
                for text in self.letter_texts:
                    text.setColor((255, 255, 255))
                    text.setOpacity(1.0)
                for underline in self.letter_underlines:
                    underline.setPen(pg.mkPen(color=(255, 255, 255, 255), width=5))
            elif t < 0.6:
                # Glow bright then fade
                glow = 0.6 + 0.4 * math.sin((t - 0.15) / 0.45 * math.pi)
                for text in self.letter_texts:
                    text.setOpacity(glow)
                for underline in self.letter_underlines:
                    alpha = int(255 * glow)
                    underline.setPen(pg.mkPen(color=(255, 255, 255, alpha), width=6))

            # Keep updating explosions so they can complete
            for expl in self.letter_explosions[:]:
                expl.update(dt)
                if expl.completed:
                    expl.cleanup()
                    self.letter_explosions.remove(expl)

            if t >= 0.7 and not self.letter_explosions:
                self._transition_to_insertion()
            return

        # Flush pending cycle after sync window expires
        if self.pending_cycle is not None:
            self.pending_cycle_age += dt * 1000  # convert to ms
            if self.pending_cycle_age > self.input_tracker.sync_window_ms:
                self._cycle_letter(self.pending_cycle)
                self.pending_cycle = None

        # Pulse the current letter slot
        for i, (text, underline) in enumerate(zip(self.letter_texts, self.letter_underlines)):
            if i == self.current_pos:
                pulse = 0.7 + 0.3 * math.sin(self.elapsed_time * 6)
                text.setOpacity(pulse)
                underline.setPen(pg.mkPen(color=(255, 255, 0, int(255 * pulse)), width=5))
            elif i < self.current_pos:
                # Confirmed - bright yellow and locked
                text.setOpacity(1.0)
                underline.setPen(pg.mkPen(color=(255, 255, 0, 255), width=5))

        # Update letter explosions
        for expl in self.letter_explosions[:]:
            expl.update(dt)
            if expl.completed:
                expl.cleanup()
                self.letter_explosions.remove(expl)

    def _cycle_letter(self, direction):
        """Cycle the current letter forward or backward."""
        if self.name_confirmed or self.current_pos >= 3:
            return
        self.letters[self.current_pos] = (self.letters[self.current_pos] + direction) % len(LETTERS)
        self.letter_texts[self.current_pos].setText(LETTERS[self.letters[self.current_pos]])

        if self.game_engine and self.game_engine.sound_manager:
            self.game_engine.sound_manager.play_laser_sound()

    def _confirm_letter(self):
        """Confirm the current letter and advance."""
        if self.name_confirmed or self.current_pos >= 3:
            return

        # Intense explosion at confirmed letter
        spacing = 70
        x = (self.current_pos - 1) * spacing
        # Main ring
        expl = ExplosionRing(center=(x, 0), max_radius=60, color=(255, 255, 0), view=self.view)
        self.letter_explosions.append(expl)
        # Inner bright ring
        expl2 = ExplosionRing(center=(x, 0), max_radius=35, color=(255, 255, 200), view=self.view)
        self.letter_explosions.append(expl2)

        if self.game_engine:
            self.game_engine.sound_manager.play_explosion_sound(volume=0.25)
            if self.game_engine.shake_manager:
                self.game_engine.shake_manager.trigger_shake(magnitude=4.0, duration=0.2)
            if self.game_engine.starfield:
                self.game_engine.starfield.start_flash(0.08)

        self.current_pos += 1
        if self.current_pos >= 3:
            self.name_confirmed = True

    def _get_entered_name(self):
        return "".join(LETTERS[i] for i in self.letters)

    def _transition_to_insertion(self):
        """Clean up name entry and start insertion animation."""
        for item in self.name_entry_items:
            try:
                self.view.removeItem(item)
            except Exception:
                pass
        # Remove from all_elements too
        self.all_elements = [
            e for e in self.all_elements if e["item"] not in self.name_entry_items
        ]
        self.name_entry_items.clear()
        self.letter_texts.clear()
        self.letter_underlines.clear()

        # Clean up any still-running letter explosions
        for expl in self.letter_explosions:
            expl.cleanup()
        self.letter_explosions.clear()

        # Insert into high score board
        name = self._get_entered_name()
        entry = self.high_score_board.create_entry(
            name=name,
            score=self.final_score,
            wave=self.final_wave,
            bosses=self.bosses,
            difficulty=self.difficulty,
            perfect_waves=self.perfect_waves,
        )
        self.new_rank = self.high_score_board.insert(entry)

        self.phase = "insertion"
        self.insertion_phase = "slide_in"
        self.insertion_timer = 0.0
        self._create_board(highlight_rank=self.new_rank, animate=True)

    # ── Board Display ───────────────────────────────────────────

    def _create_board(self, highlight_rank=-1, animate=False):
        """Create the high score board display."""
        # Title
        title = pg.TextItem(text="HIGH SCORES", color=(0, 255, 255), anchor=(0.5, 0.5))
        title.setFont(font_manager.get_title_font(42, bold=True))
        title.setPos(0, self.title_y)
        self.view.addItem(title)
        self.all_elements.append({"item": title, "pos": (0, self.title_y)})

        entries = self.high_score_board.entries
        self.row_items = []
        self.row_target_positions = []

        for i in range(min(10, max(len(entries), 1 if not entries else len(entries)))):
            if i >= len(entries):
                break

            entry = entries[i]
            y = self.row_start_y - i * self.row_spacing
            self.row_target_positions.append(y)

            is_new = i == highlight_rank
            row_data = self._create_row(i, entry, y, is_new, animate and is_new)
            self.row_items.append(row_data)

        # If score doesn't qualify, show player's run as a dimmed row below the list
        if not self.qualifies:
            from high_scores import HighScoreEntry
            your_entry = HighScoreEntry(
                name="YOU",
                score=self.final_score,
                wave=self.final_wave,
                bosses=self.bosses,
                difficulty=self.difficulty,
                perfect_waves=self.perfect_waves,
                timestamp="",
            )
            num_rows = min(len(entries), 10)
            # Small gap then the player's row
            your_y = self.row_start_y - num_rows * self.row_spacing - 15
            self._create_row(num_rows, your_entry, your_y, is_new=False, start_offscreen=False, dimmed=True)

        # F+J exit hint at bottom
        if not animate:
            self._create_exit_hint()

    def _create_row(self, rank, entry, y, is_new=False, start_offscreen=False, dimmed=False):
        """Create a single row of the high score board."""
        if dimmed:
            alpha = 100
        else:
            alpha = max(80, 255 - rank * 18)
            # CRT scanline effect
            if rank % 2 == 1:
                alpha = int(alpha * 0.85)

        if is_new or dimmed:
            name_color = (220, 80, 255, alpha if dimmed else 255)  # Magenta for player's entry
            score_color = (220, 80, 255, alpha if dimmed else 255)
        else:
            name_color = (0, 255, 255, alpha)
            score_color = (200, 200, 200, alpha)

        difficulty_colors = {
            "EASY": (0, 255, 100),
            "NORMAL": (255, 200, 0),
            "HARD": (255, 50, 50),
            "IMPOSSIBLE": (255, 50, 50),
        }
        diff_rgb = difficulty_colors.get(entry.difficulty, (200, 200, 200))

        x_start = start_offscreen if start_offscreen else 0
        x_offset = 500 if start_offscreen else 0

        items = []

        # Rank
        rank_label = " --" if dimmed else f"{rank + 1:>2}."
        rank_text = pg.TextItem(
            text=rank_label, color=(*score_color[:3], alpha), anchor=(0, 0.5)
        )
        rank_text.setFont(font_manager.get_hud_font(16, bold=True))
        rank_text.setPos(-350 + x_offset, y)
        self.view.addItem(rank_text)
        items.append(rank_text)
        self.all_elements.append({"item": rank_text, "pos": (-350, y)})

        # Name
        name_text = pg.TextItem(
            text=entry.name, color=name_color, anchor=(0, 0.5)
        )
        name_text.setFont(font_manager.get_hud_font(16, bold=True))
        name_text.setPos(-300 + x_offset, y)
        self.view.addItem(name_text)
        items.append(name_text)
        self.all_elements.append({"item": name_text, "pos": (-300, y)})

        # Score
        score_text = pg.TextItem(
            text=f"{entry.score:>6,}", color=score_color, anchor=(0, 0.5)
        )
        score_text.setFont(font_manager.get_hud_font(16, bold=False))
        score_text.setPos(-200 + x_offset, y)
        self.view.addItem(score_text)
        items.append(score_text)
        self.all_elements.append({"item": score_text, "pos": (-200, y)})

        # Wave
        wave_text = pg.TextItem(
            text=f"W{entry.wave - 1:>2}", color=(*score_color[:3], alpha), anchor=(0, 0.5)
        )
        wave_text.setFont(font_manager.get_hud_font(14, bold=False))
        wave_text.setPos(-80 + x_offset, y)
        self.view.addItem(wave_text)
        items.append(wave_text)
        self.all_elements.append({"item": wave_text, "pos": (-80, y)})

        # Boss diamonds
        boss_str = ""
        for _ in range(min(entry.bosses, 5)):
            boss_str += "\u25C6"  # Filled diamond
        if entry.bosses > 5:
            boss_str += f"+{entry.bosses - 5}"
        boss_text = pg.TextItem(
            text=boss_str, color=(255, 80, 80, alpha), anchor=(0, 0.5)
        )
        boss_text.setFont(font_manager.get_hud_font(14, bold=False))
        boss_text.setPos(0 + x_offset, y)
        self.view.addItem(boss_text)
        items.append(boss_text)
        self.all_elements.append({"item": boss_text, "pos": (0, y)})

        # Perfect waves
        perf_str = ""
        for _ in range(min(entry.perfect_waves, 5)):
            perf_str += "\u2605"  # Star
        if entry.perfect_waves > 5:
            perf_str += f"+{entry.perfect_waves - 5}"
        perf_text = pg.TextItem(
            text=perf_str, color=(255, 255, 0, alpha), anchor=(0, 0.5)
        )
        perf_text.setFont(font_manager.get_hud_font(14, bold=False))
        perf_text.setPos(120 + x_offset, y)
        self.view.addItem(perf_text)
        items.append(perf_text)
        self.all_elements.append({"item": perf_text, "pos": (120, y)})

        # Difficulty
        diff_text = pg.TextItem(
            text=entry.difficulty[:4], color=(*diff_rgb, alpha), anchor=(0, 0.5)
        )
        diff_text.setFont(font_manager.get_hud_font(12, bold=False))
        diff_text.setPos(240 + x_offset, y)
        self.view.addItem(diff_text)
        items.append(diff_text)
        self.all_elements.append({"item": diff_text, "pos": (240, y)})

        # Thin connecting line
        line = pg.PlotCurveItem(
            x=np.array([-350 + x_offset, 300 + x_offset]),
            y=np.array([y - 16, y - 16]),
            pen=pg.mkPen(color=(0, 255, 255, max(20, alpha // 4)), width=1),
        )
        self.view.addItem(line)
        items.append(line)
        self.all_elements.append({"item": line, "pos": (0, y - 16)})

        return {"items": items, "y": y, "target_y": y, "is_new": is_new}

    def _create_exit_hint(self):
        """Create F+J hexagon button indicators for exit."""
        num_rows = min(len(self.high_score_board.entries), 10)
        extra = self.row_spacing + 15 if not self.qualifies else 0  # Space for "YOU" row
        hint_y = self.row_start_y - num_rows * self.row_spacing - extra - 40
        self._create_button_indicators(y=hint_y, include_all=False, items_list=None)
        self.exit_ready = True

    def _create_button_indicators(self, y=-260, include_all=False, items_list=None):
        """Create hexagon button indicators.

        Args:
            y: vertical position
            include_all: if True, show all 6 buttons; if False, show only F and J
            items_list: optional list to also track items in (for name_entry cleanup)
        """
        self.button_items = {}
        self.button_circles = {}

        if include_all:
            # All 6 buttons centered with gap between hands
            positions = {}
            button_spacing = 60
            hand_gap = 60
            hex_size = 25
            num_left = len(LEFT_HAND_BUTTONS)
            left_group_width = (num_left - 1) * button_spacing if num_left > 1 else 0
            left_x_start = -hand_gap / 2 - left_group_width - hex_size
            for i, button in enumerate(LEFT_HAND_BUTTONS):
                positions[button] = (left_x_start + i * button_spacing, y)
            right_x_start = hand_gap / 2 + hex_size
            for i, button in enumerate(RIGHT_HAND_BUTTONS):
                positions[button] = (right_x_start + i * button_spacing, y)
        else:
            # Only F and J for exit
            positions = {
                self.left_button: (-60, y),
                self.right_button: (60, y),
            }

        self.button_positions = positions

        for button, pos in positions.items():
            color = BUTTON_COLORS[button]
            rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))

            hexagon = self._create_hexagon_button(pos, rgb, button)
            self.view.addItem(hexagon)
            self.button_circles[button] = hexagon
            self.all_elements.append({"item": hexagon, "pos": pos})
            if items_list is not None:
                items_list.append(hexagon)
                items_list.append(hexagon._fill)

            text = pg.TextItem(
                text=get_button_label(button), color=(255, 255, 255), anchor=(0.5, 0.5)
            )
            text.setFont(font_manager.get_button_font(20, bold=True))
            text.setPos(pos[0], pos[1])
            self.view.addItem(text)
            self.button_items[button] = text
            self.all_elements.append({"item": text, "pos": pos})
            if items_list is not None:
                items_list.append(text)

        # Combo line between F and J
        left_pos = positions.get(self.left_button)
        right_pos = positions.get(self.right_button)
        if left_pos and right_pos:
            line_start_x = left_pos[0] + 25
            line_end_x = right_pos[0] - 25
            line_y = y

            self.combo_line = pg.PlotCurveItem(
                x=[line_start_x, line_end_x],
                y=[line_y, line_y],
                pen=pg.mkPen(color=(255, 255, 0, 150), width=12),
            )
            self.combo_line.setZValue(-5)
            self.view.addItem(self.combo_line)
            self.all_elements.append({"item": self.combo_line, "pos": (0, line_y)})
            if items_list is not None:
                items_list.append(self.combo_line)

            self.combo_line_glow = pg.PlotCurveItem(
                x=[line_start_x, line_end_x],
                y=[line_y, line_y],
                pen=pg.mkPen(color=(255, 255, 0, 60), width=20),
            )
            self.combo_line_glow.setZValue(-6)
            self.view.addItem(self.combo_line_glow)
            self.all_elements.append({"item": self.combo_line_glow, "pos": (0, line_y)})
            if items_list is not None:
                items_list.append(self.combo_line_glow)

            # Waveform overlay for partial press animation
            self.link_waveform = pg.PlotCurveItem(
                pen=pg.mkPen(color=(255, 255, 255, 200), width=3)
            )
            self.link_waveform.setZValue(-4)
            self.view.addItem(self.link_waveform)
            self.all_elements.append({"item": self.link_waveform, "pos": (0, line_y)})
            if items_list is not None:
                items_list.append(self.link_waveform)

            self.line_start_x = line_start_x
            self.line_end_x = line_end_x
            self.line_y = line_y

    def _create_hexagon_button(self, pos, rgb, button):
        """Create a hexagon button with fill."""
        angles = np.linspace(0, 2 * np.pi, 7)
        x_points = pos[0] + 25 * np.cos(angles)
        y_points = pos[1] + 25 * np.sin(angles)

        hexagon_fill = pg.PlotCurveItem(
            x=x_points, y=y_points, pen=None,
            brush=pg.mkBrush(*rgb, 120), fillLevel="enclosed",
        )
        self.view.addItem(hexagon_fill)

        hexagon_outline = pg.PlotCurveItem(
            x=x_points, y=y_points,
            pen=pg.mkPen(color=(*rgb, 255), width=3), brush=None,
        )
        hexagon_outline._fill = hexagon_fill
        return hexagon_outline

    # ── Insertion Animation ─────────────────────────────────────

    def _update_insertion(self, dt):
        """Update the insertion animation."""
        self.insertion_timer += dt

        if self.insertion_phase == "slide_in":
            # Slide new entry in from right over 0.4s
            t = min(self.insertion_timer / 0.4, 1.0)
            eased = 1 - (1 - t) ** 3  # Ease-out

            if self.new_rank < len(self.row_items):
                row = self.row_items[self.new_rank]
                if row["is_new"]:
                    x_offset = 500 * (1 - eased)
                    for item in row["items"]:
                        elem = next(
                            (e for e in self.all_elements if e["item"] is item), None
                        )
                        if elem:
                            item.setPos(elem["pos"][0] + x_offset, elem["pos"][1])

            if t >= 1.0:
                self.insertion_phase = "impact"
                self.insertion_timer = 0.0

        elif self.insertion_phase == "impact":
            # Flash and shake on impact
            if self.insertion_timer < dt * 2:  # First frame
                if self.game_engine:
                    if self.game_engine.starfield:
                        self.game_engine.starfield.start_flash(duration=0.3)
                    self.game_engine.sound_manager.play_thunder_sound()
                    self.game_engine.shake_manager.trigger_shake(magnitude=8.0, duration=0.5)

            # Brief pause before cascade
            if self.insertion_timer >= 0.2:
                self.insertion_phase = "cascade"
                self.insertion_timer = 0.0
                self.cascade_index = self.new_rank + 1
                self.cascade_timer = 0.0

        elif self.insertion_phase == "cascade":
            # Entries below cascade downward with staggered timing
            # This phase is visual only - entries were already inserted into the data
            self.cascade_timer += dt

            if self.cascade_timer >= 0.8:
                self.insertion_phase = "settle"
                self.insertion_timer = 0.0

        elif self.insertion_phase == "settle":
            # New entry glows
            if self.new_rank < len(self.row_items):
                row = self.row_items[self.new_rank]
                pulse = 0.7 + 0.3 * math.sin(self.elapsed_time * 5)
                for item in row["items"]:
                    try:
                        item.setOpacity(pulse)
                    except Exception:
                        pass

            if self.insertion_timer >= 1.5:
                self.insertion_phase = "done"
                self.phase = "display"
                self._create_exit_hint()

        # Update displaced explosions
        for expl in self.displaced_explosions[:]:
            expl.update(dt)
            if expl.completed:
                expl.cleanup()
                self.displaced_explosions.remove(expl)

    # ── Input ───────────────────────────────────────────────────

    def on_key_press(self, key: str, timestamp: int) -> str:
        if self.exploding:
            return "continue"

        if key == "\x1b":
            return "quit"

        if key in ALL_BUTTONS:
            self.input_tracker.on_button_press(key, timestamp)
            self._highlight_button(key, pressed=True)
            self._create_button_effect(key)

        # Check simultaneous F+J
        if self.input_tracker.check_simultaneous_press(self.confirm_buttons, timestamp):
            if self.phase == "name_entry":
                self.pending_cycle = None
                self._confirm_letter()
            elif self.phase == "display" and self.exit_ready:
                self._trigger_exit_sequence()
            return "continue"

        # Block all other input in display phase until exit buttons visible
        if self.phase == "display" and not self.exit_ready:
            return "continue"

        # Partial press feedback (F or J pressed alone)
        if key in (self.left_button, self.right_button):
            other = self.right_button if key == self.left_button else self.left_button
            if other not in self.input_tracker.held_buttons:
                self._show_partial_press_feedback(other)

        # Queue cycle direction (don't apply yet — wait for sync window to expire)
        if self.phase == "name_entry" and key in ALL_BUTTONS:
            if key in LEFT_HAND_BUTTONS:
                self.pending_cycle = -1
                self.pending_cycle_age = 0
            elif key in RIGHT_HAND_BUTTONS:
                self.pending_cycle = 1
                self.pending_cycle_age = 0

        return "continue"

    def on_key_release(self, key: str):
        if key in ALL_BUTTONS:
            self.input_tracker.on_button_release(key)
            self._highlight_button(key, pressed=False)

    def _highlight_button(self, key, pressed):
        """Visual feedback for hexagon button press/release."""
        if key not in self.button_circles:
            return
        hexagon = self.button_circles[key]
        rgb = tuple(int(BUTTON_COLORS[key][i : i + 2], 16) for i in (1, 3, 5))
        if pressed:
            bright = tuple(min(255, c + 50) for c in rgb)
            hexagon.setPen(pg.mkPen(color=(*bright, 255), width=6))
            hexagon._fill.setBrush(pg.mkBrush(*bright, 200))
        else:
            hexagon.setPen(pg.mkPen(color=(*rgb, 255), width=3))
            hexagon._fill.setBrush(pg.mkBrush(*rgb, 120))

    def _create_button_effect(self, button):
        """Create expanding ring + laser effect on button press (like intro screen)."""
        if button not in self.button_positions:
            return
        pos = self.button_positions[button]
        color = BUTTON_COLORS[button]
        self.active_effects.append(ExpandingRingEffect(self.view, pos, color))
        self.active_effects.append(IntroLaserEffect(self.view, pos, color))

    def _show_partial_press_feedback(self, unpressed_button):
        """Flash the unpressed button and pulse the waveform link."""
        self.waveform_intensity = 1.0
        self.waveform_time = 0.0
        self.partial_press_triggered = True
        self.partial_press_flash_time = 0.0
        self.partial_flash_button = unpressed_button
        if unpressed_button in self.button_circles:
            hexagon = self.button_circles[unpressed_button]
            hexagon.setPen(pg.mkPen(color=(255, 255, 0, 255), width=6))
            hexagon._fill.setBrush(pg.mkBrush(255, 255, 0, 150))

    def _update_waveform_animation(self, dt):
        """Update waveform overlay on the combo link line."""
        if self.waveform_intensity > 0:
            self.waveform_intensity = max(0, self.waveform_intensity - dt * self.waveform_decay_rate)
            self.waveform_time += dt

        if not self.link_waveform or self.waveform_intensity <= 0.01:
            if self.link_waveform:
                self.link_waveform.setData(x=[], y=[])
            return

        num_points = 50
        base_x = np.linspace(self.line_start_x, self.line_end_x, num_points)
        base_y = self.line_y
        amplitude = 15.0 * self.waveform_intensity
        wave_speed = 3.0
        wave_frequency = 6.0

        t_normalized = np.linspace(0, 1, num_points)
        center_offset = self.waveform_time * wave_speed
        wave_arg = (t_normalized - 0.5) * wave_frequency * np.pi
        safe_arg = np.where(np.abs(wave_arg) < 0.001, 0.001, wave_arg)
        sinc_wave = np.sin(safe_arg + center_offset) / safe_arg
        sinc_wave = np.where(np.abs(wave_arg) < 0.001, 1.0, sinc_wave)
        envelope = np.sin(t_normalized * np.pi)
        displacement = amplitude * sinc_wave * envelope
        wave_y = base_y + displacement

        alpha = int(200 * self.waveform_intensity)
        self.link_waveform.setData(
            x=base_x, y=wave_y, pen=pg.mkPen(color=(255, 255, 255, alpha), width=3)
        )

    def _update_partial_press_flash(self, dt):
        """Update partial press button flash."""
        if not self.partial_press_triggered:
            return
        self.partial_press_flash_time += dt
        if self.partial_press_flash_time >= self.partial_press_flash_duration:
            self.partial_press_triggered = False
            if self.partial_flash_button in self.button_circles:
                hexagon = self.button_circles[self.partial_flash_button]
                rgb = tuple(
                    int(BUTTON_COLORS[self.partial_flash_button][i : i + 2], 16) for i in (1, 3, 5)
                )
                hexagon.setPen(pg.mkPen(color=(*rgb, 255), width=3))
                hexagon._fill.setBrush(pg.mkBrush(*rgb, 120))

    # ── Exit Explosion ──────────────────────────────────────────

    def _trigger_exit_sequence(self):
        """Trigger exit explosion sequence (same as GameOverScreen)."""
        if self.exploding:
            return

        self.exploding = True
        self.explosion_start_time = self.elapsed_time

        self.center_ring = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 255, 255, 255), width=5))
        self.view.addItem(self.center_ring)

        for elem_data in self.all_elements:
            pos = elem_data["pos"]
            dx, dy = pos[0], pos[1]
            distance = math.sqrt(dx * dx + dy * dy) if dx != 0 or dy != 0 else 1
            speed = 500.0
            elem_data["velocity"] = (dx / distance * speed, dy / distance * speed)

        if self.game_engine:
            self.game_engine.sound_manager.play_twinkle_sound()
            self.game_engine.shake_manager.trigger_shake(magnitude=10.0, duration=0.8)

    # ── Update ──────────────────────────────────────────────────

    def update(self, dt: float):
        if not self.active:
            return

        self.elapsed_time += dt

        # Handle exit explosion
        if self.exploding:
            explosion_time = self.elapsed_time - self.explosion_start_time
            explosion_progress = explosion_time / self.explosion_duration

            if explosion_progress < 1.0:
                ring_radius = explosion_progress * 600
                ring_opacity = max(0, 1.0 - explosion_progress)
                angles = np.linspace(0, 2 * np.pi, 100)
                self.center_ring.setData(
                    x=ring_radius * np.cos(angles), y=ring_radius * np.sin(angles)
                )
                self.center_ring.setPen(
                    pg.mkPen(color=(255, 255, 255, int(255 * ring_opacity)), width=5)
                )

                for elem_data in self.all_elements:
                    if "velocity" in elem_data:
                        vx, vy = elem_data["velocity"]
                        ox, oy = elem_data["pos"]
                        new_x = ox + vx * explosion_time
                        new_y = oy + vy * explosion_time
                        try:
                            elem_data["item"].setPos(new_x, new_y)
                            if hasattr(elem_data["item"], "_fill"):
                                if explosion_progress < 0.2:
                                    elem_data["item"]._fill.setOpacity(explosion_progress * 5.0)
                                else:
                                    elem_data["item"]._fill.setOpacity(
                                        1.0 - (explosion_progress - 0.2) / 0.8
                                    )
                                elem_data["item"].setOpacity(1.0 - explosion_progress)
                            else:
                                elem_data["item"].setOpacity(1.0 - explosion_progress)
                        except Exception:
                            pass
            else:
                if not self.elements_cleared:
                    self.elements_cleared = True
                    self.cleanup()
                    if self.on_restart_callback:
                        self.on_restart_callback()
            return

        # Fade-in
        if self.fade_in_progress < self.fade_in_duration:
            self.fade_in_progress += dt
            opacity = min(1.0, self.fade_in_progress / self.fade_in_duration)
            for elem_data in self.all_elements:
                try:
                    elem_data["item"].setOpacity(opacity)
                except Exception:
                    pass

        # Phase updates
        if self.phase == "name_entry":
            self._update_name_entry(dt)
        elif self.phase == "insertion":
            self._update_insertion(dt)

        # Continuous pulse on the player's new entry
        if self.new_rank >= 0 and self.new_rank < len(self.row_items) and not self.exploding:
            pulse = 0.7 + 0.3 * math.sin(self.elapsed_time * 5)
            for item in self.row_items[self.new_rank]["items"]:
                try:
                    item.setOpacity(pulse)
                except Exception:
                    pass

        # Update button press effects (rings + lasers)
        completed = []
        for effect in self.active_effects:
            if not effect.update(dt):
                completed.append(effect)
        for effect in completed:
            effect.cleanup()
            self.active_effects.remove(effect)

        # Update waveform and partial press animations
        self._update_waveform_animation(dt)
        self._update_partial_press_flash(dt)

    # ── Cleanup ─────────────────────────────────────────────────

    def _set_initial_opacity(self):
        for elem_data in self.all_elements:
            try:
                elem_data["item"].setOpacity(0.0)
            except Exception:
                pass

    def cleanup(self):
        if not self.active:
            return

        if self.center_ring:
            try:
                self.view.removeItem(self.center_ring)
            except Exception:
                pass

        for elem_data in self.all_elements:
            try:
                self.view.removeItem(elem_data["item"])
                if hasattr(elem_data["item"], "_fill"):
                    self.view.removeItem(elem_data["item"]._fill)
            except Exception:
                pass

        for button_text in getattr(self, "button_items", {}).values():
            try:
                self.view.removeItem(button_text)
            except Exception:
                pass
        for hexagon in getattr(self, "button_circles", {}).values():
            try:
                self.view.removeItem(hexagon)
                if hasattr(hexagon, "_fill"):
                    self.view.removeItem(hexagon._fill)
            except Exception:
                pass

        for expl in self.letter_explosions:
            expl.cleanup()
        self.letter_explosions.clear()

        for expl in self.displaced_explosions:
            expl.cleanup()
        self.displaced_explosions.clear()

        for effect in self.active_effects:
            effect.cleanup()
        self.active_effects.clear()

        self.all_elements.clear()
        self.active = False
