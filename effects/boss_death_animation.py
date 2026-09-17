"""Boss death animation effect."""

import numpy as np
import pyqtgraph as pg


class BossDeathAnimation:
    """Custom death animation for bosses with expanding shield rings."""

    def __init__(self, boss, view):
        """Initialize boss death animation."""
        self.boss = boss
        self.enemy = boss  # Alias for compatibility with game engine
        self.view = view
        self.duration = 3.0  # Total animation duration
        self.elapsed = 0.0
        self.completed = False

        # Finale effects (last 0.8s)
        self.finale_start = 2.2
        self.finale_flash_interval = 0.12
        self.last_finale_flash = 0.0
        self.finale_callback = None  # Set by game engine for starfield/shake access

        # Get boss position - all bosses should have get_center_position()
        if hasattr(boss, "center_pos"):
            self.center_pos = boss.center_pos
        else:
            self.center_pos = boss.get_center_position()

        # Get boss radius - use new get_boss_radius() method
        if hasattr(boss, "get_boss_radius"):
            self.boss_radius = boss.get_boss_radius()
        elif hasattr(boss, "forcefield_radius"):
            self.boss_radius = boss.forcefield_radius
        elif hasattr(boss, "get_width"):
            self.boss_radius = boss.get_width() / 2
        else:
            self.boss_radius = 100  # Default radius

        # Create expanding shield rings
        self.shield_rings = []
        self.max_rings = 10
        self.ring_spawn_interval = 0.15
        self.last_ring_spawn = 0.0

        # Track explosion spawning
        self.explosion_interval = 0.15  # Trigger explosion callback every 0.15 seconds
        self.last_explosion_time = 0.0
        self.explosion_callback = None  # Will be set by game engine

        # Track screen shake
        self.shake_interval = 0.1  # Trigger shake every 0.1 seconds for continuous rumble
        self.last_shake_time = 0.0
        self.shake_callback = None  # Will be set by game engine

        # Store references to boss visual elements for flicker effect
        self.boss_core_enemies = getattr(boss, "core_enemies", [])
        self.boss_visuals = []
        if hasattr(boss, "forcefield_arc") and boss.forcefield_arc:
            self.boss_visuals.append(boss.forcefield_arc)
        if hasattr(boss, "forcefield_glow") and boss.forcefield_glow:
            self.boss_visuals.append(boss.forcefield_glow)

        # Create initial ring
        self._spawn_ring()

    def _cleanup_boss_visuals(self):
        """Clean up boss's static visual elements when death animation starts."""
        # Remove force field
        if hasattr(self.boss, "forcefield_arc"):
            self.view.removeItem(self.boss.forcefield_arc)
        if hasattr(self.boss, "forcefield_glow"):
            self.view.removeItem(self.boss.forcefield_glow)
        if hasattr(self.boss, "hold_indicator"):
            self.view.removeItem(self.boss.hold_indicator)

        # Remove vulnerability indicators
        if hasattr(self.boss, "vulnerability_indicators"):
            for indicator in self.boss.vulnerability_indicators:
                self.view.removeItem(indicator)

        # Clean up particles
        if hasattr(self.boss, "particles"):
            for particle in self.boss.particles:
                self.view.removeItem(particle["item"])
            self.boss.particles.clear()

    def _spawn_ring(self):
        """Spawn a new expanding ring."""
        # Create circle points - use 101 points so start and end meet
        angles = np.linspace(0, 2 * np.pi, 101)
        radius = self.boss_radius
        x = self.center_pos[0] + radius * np.cos(angles)
        y = self.center_pos[1] + radius * np.sin(angles)

        # Create ring with initial color - use connect='all' to close the circle
        ring = pg.PlotDataItem(
            x=x, y=y, pen=pg.mkPen(color=(100, 200, 255, 200), width=3), connect="all"
        )
        self.view.addItem(ring)

        # Store ring info
        self.shield_rings.append({"item": ring, "radius": radius, "opacity": 200, "age": 0.0})

    def update(self, dt):
        """Update the animation."""
        self.elapsed += dt

        # Phase 1: Flicker and fade effect (0-1 seconds)
        if self.elapsed < 1.0:
            # Flicker rate accelerates over time
            flicker_rate = 10 + self.elapsed * 20  # 10Hz to 30Hz
            phase_flicker = int(self.elapsed * flicker_rate) % 2

            # Calculate overall fade progress (1.0 to 0.3 over first second)
            fade_progress = 1.0 - (self.elapsed * 0.7)  # Goes from 1.0 to 0.3

            # Flash opacity between 0 and decreasing max value
            flash_opacity = 0 if phase_flicker == 0 else fade_progress

            # Update core enemies' opacity if they exist
            for enemy in self.boss_core_enemies:
                if hasattr(enemy, "letter_items"):
                    for letter_item in enemy.letter_items:
                        letter_item.setOpacity(flash_opacity)
                if hasattr(enemy, "letter_backgrounds"):
                    for bg in enemy.letter_backgrounds:
                        bg.setOpacity(flash_opacity * 0.5)

            # Update boss visual elements
            for visual in self.boss_visuals:
                if visual:
                    visual.setOpacity(flash_opacity)

        # Phase 2: Keep elements faded (after 1 second)
        elif self.elapsed < 2.5:
            remaining_opacity = 0.3
            # Keep core enemies at low opacity
            for enemy in self.boss_core_enemies:
                if hasattr(enemy, "letter_items"):
                    for letter_item in enemy.letter_items:
                        letter_item.setOpacity(remaining_opacity)
                if hasattr(enemy, "letter_backgrounds"):
                    for bg in enemy.letter_backgrounds:
                        bg.setOpacity(remaining_opacity * 0.5)

            # Keep boss visuals very faded
            for visual in self.boss_visuals:
                if visual:
                    visual.setOpacity(remaining_opacity * 0.2)

            # Clean up boss visuals after initial flicker phase
            if self.elapsed > 1.1 and self.boss_visuals:
                self._cleanup_boss_visuals()
                self.boss_visuals = []  # Clear so we don't try again

        # Spawn new rings periodically (only during first half of animation)
        if len(self.shield_rings) < self.max_rings and self.elapsed < self.duration / 2:
            if self.elapsed - self.last_ring_spawn > self.ring_spawn_interval:
                self._spawn_ring()
                self.last_ring_spawn = self.elapsed

        # Trigger explosion callback for game engine to spawn explosions
        if (
            self.explosion_callback
            and self.elapsed - self.last_explosion_time > self.explosion_interval
        ):
            self.last_explosion_time = self.elapsed
            self.explosion_callback()

        # Trigger shake callback for continuous screen shake
        if self.shake_callback and self.elapsed - self.last_shake_time > self.shake_interval:
            self.last_shake_time = self.elapsed
            self.shake_callback()

        # Update existing rings
        for ring_info in self.shield_rings[:]:
            ring_info["age"] += dt

            # Expand radius
            expansion_speed = 150  # pixels per second
            ring_info["radius"] += expansion_speed * dt

            # Fade out
            fade_speed = 150  # opacity per second
            ring_info["opacity"] = max(0, ring_info["opacity"] - fade_speed * dt)

            # Update ring position and appearance
            angles = np.linspace(0, 2 * np.pi, 101)
            x = self.center_pos[0] + ring_info["radius"] * np.cos(angles)
            y = self.center_pos[1] + ring_info["radius"] * np.sin(angles)

            # Color shifts from blue to purple as it expands
            color_shift = min(1.0, ring_info["age"] / 2.0)
            r = int(100 + 155 * color_shift)
            g = int(200 * (1 - color_shift))
            b = 255

            # Update the ring data
            ring_info["item"].setData(x=x, y=y)
            ring_info["item"].setPen(pg.mkPen(color=(r, g, b, int(ring_info["opacity"])), width=3))

            # Remove if faded out
            if ring_info["opacity"] <= 0:
                self.view.removeItem(ring_info["item"])
                self.shield_rings.remove(ring_info)

        # Finale phase: rapid flashes and shakes near the end
        self._update_finale()

        # Check if animation is complete
        if self.elapsed >= self.duration:
            # Clean up any remaining rings and mark as complete
            for ring_info in self.shield_rings[:]:
                self.view.removeItem(ring_info["item"])
                self.shield_rings.remove(ring_info)
            self.completed = True
            return False

        return True

    def _update_finale(self):
        """Update finale effects — call from update() in subclasses too."""
        if self.elapsed < self.finale_start or not self.finale_callback:
            return
        if self.elapsed - self.last_finale_flash > self.finale_flash_interval:
            self.last_finale_flash = self.elapsed
            progress = (self.elapsed - self.finale_start) / (self.duration - self.finale_start)
            self.finale_callback(progress)
            self.finale_flash_interval = max(0.04, 0.12 - progress * 0.08)

    def is_completed(self) -> bool:
        """Check if animation is completed."""
        return self.completed

    def cleanup(self):
        """Clean up animation elements."""
        # Remove any remaining rings
        for ring_info in self.shield_rings:
            self.view.removeItem(ring_info["item"])
        self.shield_rings.clear()
