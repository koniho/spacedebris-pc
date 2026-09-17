"""Optimized particle effects system using batched rendering."""

import math
from typing import Tuple, List, Optional
import pyqtgraph as pg
import random_manager


class ParticleSystem:
    """Optimized particle system using a single ScatterPlotItem for batch rendering."""

    def __init__(self, view):
        """Initialize the particle system.

        Args:
            view: The pyqtgraph view to add particles to.
        """
        self.view = view
        self.particles: List[dict] = []

        # Single ScatterPlotItem for all particles (optimized)
        self.scatter = pg.ScatterPlotItem(
            pos=[],
            size=[],
            pen=pg.mkPen(None),
            brush=[],
            pxMode=True,
        )
        self.view.addItem(self.scatter)

    def emit(
        self,
        x: float,
        y: float,
        color: Tuple[int, int, int],
        count: int = 15,
        speed_range: Tuple[float, float] = (30, 100),
        size_range: Tuple[float, float] = (2, 5),
        lifetime: float = 0.6,
        lifetime_variance: float = 0.0,
        gravity: float = 100,
        color_variance: Optional[Tuple[int, int, int]] = None,
        fade_start_alpha: int = 200,
        shrink_factor: float = 0.5,
    ):
        """Emit particles at a position.

        Args:
            x: X position to emit from.
            y: Y position to emit from.
            color: Base RGB color tuple.
            count: Number of particles to emit.
            speed_range: (min_speed, max_speed) for particle velocity.
            size_range: (min_size, max_size) for particle size.
            lifetime: Base lifetime in seconds.
            lifetime_variance: Random variance to add/subtract from lifetime (0.0-1.0 as fraction).
            gravity: Gravity strength (positive = downward pull).
            color_variance: Optional (r, g, b) variance to add randomness to color.
            fade_start_alpha: Starting alpha value for fade out (0-255).
            shrink_factor: How much particles shrink over lifetime (0.0-1.0).
        """
        for _ in range(count):
            speed = random_manager.uniform(speed_range[0], speed_range[1])
            angle = random_manager.uniform(0, 2 * math.pi)

            # Apply color variance if specified
            if color_variance:
                r = min(255, color[0] + random_manager.randint(0, color_variance[0]))
                g = min(255, color[1] + random_manager.randint(0, color_variance[1]))
                b = min(255, color[2] + random_manager.randint(0, color_variance[2]))
            else:
                r, g, b = color

            # Apply lifetime variance
            particle_lifetime = lifetime
            if lifetime_variance > 0:
                variance = lifetime * lifetime_variance
                particle_lifetime = lifetime * random_manager.uniform(1.0 - lifetime_variance, 1.0)

            particle = {
                "x": x,
                "y": y,
                "vx": speed * math.cos(angle),
                "vy": speed * math.sin(angle),
                "lifetime": particle_lifetime,
                "age": 0.0,
                "color": (r, g, b),
                "size": random_manager.uniform(size_range[0], size_range[1]),
                "gravity": gravity,
                "fade_start_alpha": fade_start_alpha,
                "shrink_factor": shrink_factor,
            }
            self.particles.append(particle)

    def emit_shield_hit(self, x: float, y: float):
        """Emit particles for a shield hit effect (blue/cyan sparks)."""
        self.emit(
            x, y,
            color=(100, 150, 255),
            count=25,
            speed_range=(50, 150),
            size_range=(2, 5),
            lifetime=0.8,
            gravity=100,
            color_variance=(155, 105, 0),
        )

    def emit_hit(self, x: float, y: float, color: Tuple[int, int, int]):
        """Emit particles for a standard hit effect."""
        self.emit(
            x, y,
            color=color,
            count=15,
            speed_range=(30, 100),
            size_range=(2, 5),
            lifetime=0.6,
            gravity=100,
        )

    def emit_explosion(
        self,
        x: float,
        y: float,
        color: Tuple[int, int, int],
        intensity: float = 1.0,
    ):
        """Emit particles for an explosion effect.

        Args:
            x: X position of explosion center.
            y: Y position of explosion center.
            color: RGB color tuple.
            intensity: Explosion intensity multiplier (affects count and speed).
        """
        self.emit(
            x, y,
            color=color,
            count=int(20 * intensity),
            speed_range=(50 * intensity, 150 * intensity),
            size_range=(2, 6),
            lifetime=0.8,
            lifetime_variance=0.5,  # Particles live 50-100% of base lifetime
            gravity=150,
        )

    def update(self, dt: float):
        """Update all particles and render to ScatterPlotItem.

        Args:
            dt: Delta time in seconds.
        """
        if not self.particles:
            self.scatter.setData(pos=[])
            return

        # Update particle physics and remove expired ones
        active_particles = []
        for particle in self.particles:
            particle["age"] += dt

            # Update position
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt

            # Apply gravity
            particle["vy"] -= particle["gravity"] * dt

            # Keep if not expired
            if particle["age"] < particle["lifetime"]:
                active_particles.append(particle)

        self.particles = active_particles

        if not self.particles:
            self.scatter.setData(pos=[])
            return

        # Build arrays for batch update
        positions = []
        sizes = []
        brushes = []

        for particle in self.particles:
            progress = particle["age"] / particle["lifetime"]
            fade_alpha = particle.get("fade_start_alpha", 200)
            shrink = particle.get("shrink_factor", 0.5)
            alpha = int(fade_alpha * (1 - progress))
            size = particle["size"] * (1 - progress * shrink)

            positions.append((particle["x"], particle["y"]))
            sizes.append(size)
            brushes.append(pg.mkBrush(*particle["color"], alpha))

        # Single batch update to ScatterPlotItem
        self.scatter.setData(
            pos=positions,
            size=sizes,
            brush=brushes,
        )

    def clear(self):
        """Clear all particles."""
        self.particles.clear()
        self.scatter.setData(pos=[])

    def cleanup(self):
        """Remove the scatter plot item from the view."""
        self.view.removeItem(self.scatter)
        self.particles.clear()


class ContainedParticleSystem:
    """Particle system where particles are contained within a radius and pulled back to center."""

    def __init__(
        self,
        view,
        center_x: float = 0,
        center_y: float = 0,
        contain_radius: float = 75,
        pull_strength: float = 2.0,
        max_particles: int = 100,
        spawn_interval: float = 0.02,
        default_pen_width: int = 5,
    ):
        """Initialize the contained particle system.

        Args:
            view: The pyqtgraph view to add particles to.
            center_x: X coordinate of containment center.
            center_y: Y coordinate of containment center.
            contain_radius: Radius beyond which particles are pulled back.
            pull_strength: How strongly particles are pulled back to center.
            max_particles: Maximum number of particles allowed.
            spawn_interval: Minimum time between auto-spawns.
            default_pen_width: Default pen width for particles (0 = no outline).
        """
        self.view = view
        self.particles: List[dict] = []
        self.center_x = center_x
        self.center_y = center_y
        self.contain_radius = contain_radius
        self.pull_strength = pull_strength
        self.max_particles = max_particles
        self.spawn_interval = spawn_interval
        self.spawn_timer = 0.0
        self.default_pen_width = default_pen_width

        # Single ScatterPlotItem for all particles (optimized)
        self.scatter = pg.ScatterPlotItem(
            pos=[],
            size=[],
            pen=[],
            brush=[],
            pxMode=True,
        )
        self.view.addItem(self.scatter)

    def set_center(self, x: float, y: float):
        """Set the containment center point.

        Args:
            x: X coordinate of center.
            y: Y coordinate of center.
        """
        self.center_x = x
        self.center_y = y

    def spawn(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        color: Optional[Tuple[int, int, int]] = None,
        pen_color: Optional[Tuple[int, int, int]] = None,
        size_range: Tuple[float, float] = (15, 30),
        speed_range: Tuple[float, float] = (10, 50),
        lifetime_range: Tuple[float, float] = (0.8, 1.5),
        brush_alpha: int = 150,
        pen_alpha: int = 150,
        pen_width: Optional[int] = None,
    ):
        """Spawn a contained particle.

        Args:
            x: X position (random within radius if None).
            y: Y position (random within radius if None).
            color: RGB color tuple (random rainbow if None).
            pen_color: RGB outline color (complementary if None).
            size_range: (min, max) particle size.
            speed_range: (min, max) initial speed.
            lifetime_range: (min, max) lifetime in seconds.
            brush_alpha: Brush alpha value.
            pen_alpha: Pen alpha value.
            pen_width: Pen width (uses default_pen_width if None, 0 = no outline).
        """
        # Use default pen width if not specified
        if pen_width is None:
            pen_width = self.default_pen_width
        if len(self.particles) >= self.max_particles:
            return

        # Random position within contain_radius if not specified
        if x is None or y is None:
            angle = random_manager.uniform(0, 2 * math.pi)
            distance = random_manager.uniform(0, self.contain_radius)
            x = self.center_x + distance * math.cos(angle)
            y = self.center_y + distance * math.sin(angle)

        # Random velocity
        speed = random_manager.uniform(speed_range[0], speed_range[1])
        vel_angle = random_manager.uniform(0, 2 * math.pi)
        vx = speed * math.cos(vel_angle)
        vy = speed * math.sin(vel_angle)

        # Random rainbow color if not specified
        if color is None:
            hue = random_manager.uniform(0, 1)
            color = self._hsv_to_rgb(hue, 1.0, 1.0)

        # Complementary color for outline if not specified
        if pen_color is None:
            # Shift hue by 0.5 (180 degrees) for complementary
            hue = random_manager.uniform(0, 1)
            comp_hue = (hue + 0.5) % 1.0
            pen_color = self._hsv_to_rgb(comp_hue, 0.8, 1.0)

        self.particles.append({
            "x": x,
            "y": y,
            "vx": vx,
            "vy": vy,
            "color": color,
            "pen_color": pen_color,
            "size": random_manager.uniform(size_range[0], size_range[1]),
            "lifetime": random_manager.uniform(lifetime_range[0], lifetime_range[1]),
            "age": 0.0,
            "brush_alpha": brush_alpha,
            "pen_alpha": pen_alpha,
            "pen_width": pen_width,
        })

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        """Convert HSV to RGB. h, s, v are floats in [0, 1]."""
        i = int(h * 6.0)
        f = h * 6.0 - i
        p = v * (1.0 - s)
        q = v * (1.0 - f * s)
        t = v * (1.0 - (1.0 - f) * s)

        if i % 6 == 0:
            r, g, b = v, t, p
        elif i % 6 == 1:
            r, g, b = q, v, p
        elif i % 6 == 2:
            r, g, b = p, v, t
        elif i % 6 == 3:
            r, g, b = p, q, v
        elif i % 6 == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

        return int(r * 255), int(g * 255), int(b * 255)

    def update(self, dt: float, auto_spawn: bool = True):
        """Update all contained particles and render to ScatterPlotItem.

        Args:
            dt: Delta time in seconds.
            auto_spawn: Whether to auto-spawn new particles.
        """
        # Auto-spawn new particles
        if auto_spawn:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval and len(self.particles) < self.max_particles:
                self.spawn()
                self.spawn_timer = 0.0

        # Update particles
        active_particles = []
        for particle in self.particles:
            particle["age"] += dt

            # Update position
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt

            # Pull back towards center if too far
            dist_x = particle["x"] - self.center_x
            dist_y = particle["y"] - self.center_y
            distance = math.sqrt(dist_x**2 + dist_y**2)

            if distance > self.contain_radius * 1.5:
                particle["vx"] -= dist_x * dt * self.pull_strength
                particle["vy"] -= dist_y * dt * self.pull_strength

            # Keep if not expired
            if particle["age"] < particle["lifetime"]:
                active_particles.append(particle)

        self.particles = active_particles

        # Batch update to ScatterPlotItem
        if not self.particles:
            self.scatter.setData(pos=[])
            return

        positions = []
        sizes = []
        brushes = []
        pens = []

        for particle in self.particles:
            progress = particle["age"] / particle["lifetime"]
            alpha_mult = 1 - progress
            size = particle["size"] * (1 - progress * 0.5)

            brush_alpha = int(particle["brush_alpha"] * alpha_mult)

            positions.append((particle["x"], particle["y"]))
            sizes.append(size)
            brushes.append(pg.mkBrush(*particle["color"], brush_alpha))

            # Only create pen if pen_width > 0
            if particle["pen_width"] > 0:
                pen_alpha = int(particle["pen_alpha"] * alpha_mult)
                pens.append(pg.mkPen(color=(*particle["pen_color"], pen_alpha), width=particle["pen_width"]))
            else:
                pens.append(pg.mkPen(None))

        self.scatter.setData(pos=positions, size=sizes, brush=brushes, pen=pens)

    def clear(self):
        """Clear all particles."""
        self.particles.clear()
        self.scatter.setData(pos=[])

    def cleanup(self):
        """Remove the scatter plot item from the view."""
        self.view.removeItem(self.scatter)
        self.particles.clear()


class AttractionParticleSystem:
    """Particle system where particles are attracted toward a target point."""

    def __init__(
        self,
        view,
        target_x: float = 0,
        target_y: float = 0,
        spawn_distance_range: Tuple[float, float] = (80, 150),
        num_particles: int = 80,
        color: Tuple[int, int, int] = (255, 100, 100),
        base_size: float = 6,
        base_alpha: int = 200,
        z_value: Optional[int] = None,
    ):
        """Initialize the attraction particle system.

        Args:
            view: The pyqtgraph view to add particles to.
            target_x: X coordinate of attraction target.
            target_y: Y coordinate of attraction target.
            spawn_distance_range: (min, max) distance from target to spawn particles.
            num_particles: Number of particles to maintain.
            color: RGB color tuple for particles.
            base_size: Base particle size.
            base_alpha: Base alpha value.
            z_value: Optional z-value for rendering order.
        """
        self.view = view
        self.particles: List[dict] = []
        self.target_x = target_x
        self.target_y = target_y
        self.spawn_distance_range = spawn_distance_range
        self.num_particles = num_particles
        self.color = color
        self.base_size = base_size
        self.base_alpha = base_alpha
        self.z_value = z_value
        self.completing = False  # When True, particles don't respawn

        # Single ScatterPlotItem for all particles (optimized)
        self.scatter = pg.ScatterPlotItem(
            pos=[],
            size=[],
            pen=pg.mkPen(None),
            brush=[],
            pxMode=True,
        )
        if z_value is not None:
            self.scatter.setZValue(z_value)
        self.view.addItem(self.scatter)

    def set_target(self, x: float, y: float):
        """Set the attraction target point.

        Args:
            x: X coordinate of target.
            y: Y coordinate of target.
        """
        self.target_x = x
        self.target_y = y

    def spawn_all(self, delay_range: Tuple[float, float] = (0, 1.0)):
        """Spawn all particles with random positions and delays.

        Args:
            delay_range: (min, max) delay before particle becomes active.
        """
        self.particles.clear()
        self.completing = False

        for _ in range(self.num_particles):
            angle = random_manager.uniform(0, 2 * math.pi)
            distance = random_manager.uniform(self.spawn_distance_range[0], self.spawn_distance_range[1])
            start_x = self.target_x + distance * math.cos(angle)
            start_y = self.target_y + distance * math.sin(angle)
            delay = random_manager.uniform(delay_range[0], delay_range[1])

            self.particles.append({
                "x": start_x,
                "y": start_y,
                "delay": delay,
                "active": False,
            })

    def start_completing(self):
        """Start completing mode - particles won't respawn when reaching target."""
        self.completing = True

    def update(self, dt: float, speed: float = 100, alpha_multiplier: float = 1.0):
        """Update all particles and render to ScatterPlotItem.

        Args:
            dt: Delta time in seconds.
            speed: Movement speed toward target.
            alpha_multiplier: Multiplier for alpha (0.0-1.0+), useful for charge progress.
        """
        if not self.particles:
            self.scatter.setData(pos=[])
            if self.completing:
                self.completing = False  # Reset when all particles gone
            return

        particles_to_remove = []

        for particle in self.particles:
            # Handle delay
            if particle["delay"] > 0:
                particle["delay"] -= dt
                continue

            particle["active"] = True

            # Move toward target
            dx = self.target_x - particle["x"]
            dy = self.target_y - particle["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist > 5:
                # Move toward target
                particle["x"] += (dx / dist) * speed * dt
                particle["y"] += (dy / dist) * speed * dt
            else:
                # Reached target
                if self.completing:
                    particles_to_remove.append(particle)
                else:
                    # Respawn at edge
                    angle = random_manager.uniform(0, 2 * math.pi)
                    distance = random_manager.uniform(self.spawn_distance_range[0], self.spawn_distance_range[1])
                    particle["x"] = self.target_x + distance * math.cos(angle)
                    particle["y"] = self.target_y + distance * math.sin(angle)

        # Remove completed particles
        for particle in particles_to_remove:
            self.particles.remove(particle)

        # Batch render active particles
        positions = []
        sizes = []
        brushes = []

        for particle in self.particles:
            if not particle["active"]:
                continue

            dx = self.target_x - particle["x"]
            dy = self.target_y - particle["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            # Size based on distance (smaller as it gets closer)
            size = max(2, self.base_size * (dist / 100))

            # Alpha based on multiplier
            alpha = int(min(255, self.base_alpha * alpha_multiplier))

            positions.append((particle["x"], particle["y"]))
            sizes.append(size)
            brushes.append(pg.mkBrush(*self.color, alpha))

        if positions:
            self.scatter.setData(pos=positions, size=sizes, brush=brushes)
        else:
            self.scatter.setData(pos=[])

    def is_empty(self) -> bool:
        """Check if all particles have been removed."""
        return len(self.particles) == 0

    def clear(self):
        """Clear all particles."""
        self.particles.clear()
        self.scatter.setData(pos=[])
        self.completing = False

    def cleanup(self):
        """Remove the scatter plot item from the view."""
        self.view.removeItem(self.scatter)
        self.particles.clear()


class LineParticleSystem:
    """Particle system where particles move perpendicular to a line segment."""

    def __init__(
        self,
        view,
        start_pos: Tuple[float, float] = (0, 0),
        end_pos: Tuple[float, float] = (100, 0),
        num_particles: int = 10,
        colors: Optional[List[Tuple[int, int, int]]] = None,
        size_range: Tuple[float, float] = (4, 8),
        perpendicular_speed_range: Tuple[float, float] = (10, 30),
        perpendicular_amplitude: float = 15,
        z_value: Optional[int] = None,
    ):
        """Initialize the line particle system.

        Args:
            view: The pyqtgraph view to add particles to.
            start_pos: Start point of the line (x, y).
            end_pos: End point of the line (x, y).
            num_particles: Number of particles along the line.
            colors: List of RGB color tuples to randomly choose from.
            size_range: (min, max) particle size.
            perpendicular_speed_range: (min, max) speed of perpendicular motion.
            perpendicular_amplitude: Max distance from line center.
            z_value: Optional z-value for rendering order.
        """
        self.view = view
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.num_particles = num_particles
        self.colors = colors or [(128, 0, 255), (0, 255, 255)]  # Purple and cyan default
        self.size_range = size_range
        self.perpendicular_speed_range = perpendicular_speed_range
        self.perpendicular_amplitude = perpendicular_amplitude
        self.particles: List[dict] = []
        self.flash_timer = 0.0  # Timer for yellow flash effect
        self.flash_duration = 0.3
        self.color_blend = 0.0  # 0 = base colors, 1 = blend target (golden)
        self.blend_target_color = (255, 220, 100)  # Golden/yellow color for hold state

        # Single ScatterPlotItem for all particles
        self.scatter = pg.ScatterPlotItem(
            pos=[],
            size=[],
            pen=pg.mkPen(None),
            brush=[],
            pxMode=True,
        )
        if z_value is not None:
            self.scatter.setZValue(z_value)
        self.view.addItem(self.scatter)

        # Create particles
        self._create_particles()

    def _create_particles(self):
        """Create particles distributed along the line."""
        self.particles.clear()

        for i in range(self.num_particles):
            # Position along line (0 to 1)
            t = i / max(1, self.num_particles - 1) if self.num_particles > 1 else 0.5

            # Random perpendicular offset parameters
            phase = random_manager.uniform(0, 2 * math.pi)
            speed = random_manager.uniform(
                self.perpendicular_speed_range[0], self.perpendicular_speed_range[1]
            )
            amplitude = random_manager.uniform(
                self.perpendicular_amplitude * 0.5, self.perpendicular_amplitude
            )

            self.particles.append({
                "t": t,  # Position along line (0-1)
                "phase": phase,  # Phase offset for oscillation
                "speed": speed,  # Angular speed of oscillation
                "amplitude": amplitude,  # Max perpendicular distance
                "size": random_manager.uniform(self.size_range[0], self.size_range[1]),
                "color": random_manager.choice(self.colors),
                "timer": random_manager.uniform(0, 2 * math.pi),  # Random start time
            })

    def set_line(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float]):
        """Update the line segment position.

        Args:
            start_pos: New start point (x, y).
            end_pos: New end point (x, y).
        """
        self.start_pos = start_pos
        self.end_pos = end_pos

    def trigger_flash(self):
        """Trigger a yellow flash effect on all particles."""
        self.flash_timer = self.flash_duration

    def set_color_blend(self, blend: float):
        """Set color blend towards golden/yellow (0 = base colors, 1 = golden).

        Args:
            blend: Blend amount from 0.0 to 1.0.
        """
        self.color_blend = max(0.0, min(1.0, blend))

    def update(self, dt: float):
        """Update all particles and render to ScatterPlotItem.

        Args:
            dt: Delta time in seconds.
        """
        # Update flash timer
        if self.flash_timer > 0:
            self.flash_timer -= dt

        # Calculate line direction and perpendicular
        dx = self.end_pos[0] - self.start_pos[0]
        dy = self.end_pos[1] - self.start_pos[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length < 0.001:
            # Degenerate line - hide particles
            self.scatter.setData(pos=[])
            return

        # Unit vectors
        dir_x = dx / length
        dir_y = dy / length
        # Perpendicular (90 degrees rotation)
        perp_x = -dir_y
        perp_y = dir_x

        positions = []
        sizes = []
        brushes = []

        for particle in self.particles:
            particle["timer"] += dt

            # Base position along line
            base_x = self.start_pos[0] + particle["t"] * dx
            base_y = self.start_pos[1] + particle["t"] * dy

            # Perpendicular offset (oscillating)
            offset = particle["amplitude"] * math.sin(
                particle["timer"] * particle["speed"] + particle["phase"]
            )

            # Final position
            x = base_x + perp_x * offset
            y = base_y + perp_y * offset

            positions.append((x, y))
            sizes.append(particle["size"])

            # Calculate blended base color (blend towards golden when holding)
            base_color = particle["color"]
            if self.color_blend > 0:
                # Blend base color towards golden
                blended_r = int(base_color[0] + (self.blend_target_color[0] - base_color[0]) * self.color_blend)
                blended_g = int(base_color[1] + (self.blend_target_color[1] - base_color[1]) * self.color_blend)
                blended_b = int(base_color[2] + (self.blend_target_color[2] - base_color[2]) * self.color_blend)
                base_color = (blended_r, blended_g, blended_b)

            # Color - flash to yellow if triggered (overrides blend)
            if self.flash_timer > 0:
                flash_progress = self.flash_timer / self.flash_duration
                # Interpolate to bright yellow
                r = int(base_color[0] + (255 - base_color[0]) * flash_progress)
                g = int(base_color[1] + (255 - base_color[1]) * flash_progress)
                b = int(base_color[2] * (1 - flash_progress))
                brushes.append(pg.mkBrush(r, g, b, 200))
            else:
                brushes.append(pg.mkBrush(*base_color, 200))

        self.scatter.setData(pos=positions, size=sizes, brush=brushes)

    def clear(self):
        """Clear all particles."""
        self.particles.clear()
        self.scatter.setData(pos=[])

    def cleanup(self):
        """Remove the scatter plot item from the view."""
        if self.scatter.scene():
            self.view.removeItem(self.scatter)
        self.particles.clear()


class OrbitalParticleSystem:
    """Particle system for particles that orbit around a center point."""

    def __init__(
        self,
        view,
        size: float = 5,
        base_radius: float = 60,
        radius_variance: float = 20,
        radius_oscillation_speed: float = 3.0,
        orbit_speed: float = 2.0,
        fade_rate: float = 100,
    ):
        """Initialize the orbital particle system.

        Args:
            view: The pyqtgraph view to add particles to.
            size: Default particle size.
            base_radius: Default base orbital radius.
            radius_variance: Default amplitude of radius oscillation.
            radius_oscillation_speed: Speed of radius oscillation (radians per second).
            orbit_speed: Default angular velocity (radians per second).
            fade_rate: Default alpha decrease per second (higher = faster fade).
        """
        self.view = view
        self.particles: List[dict] = []
        self.center_x = 0.0
        self.center_y = 0.0
        self.size = size

        # Default orbital parameters
        self.default_base_radius = base_radius
        self.default_radius_variance = radius_variance
        self.default_radius_oscillation_speed = radius_oscillation_speed
        self.default_orbit_speed = orbit_speed
        self.default_fade_rate = fade_rate

        # Single ScatterPlotItem for all particles (optimized)
        self.scatter = pg.ScatterPlotItem(
            pos=[],
            size=size,
            pen=pg.mkPen(None),
            brush=[],
            pxMode=True,
        )
        self.view.addItem(self.scatter)

    def set_center(self, x: float, y: float):
        """Set the center point for orbital motion.

        Args:
            x: X coordinate of center.
            y: Y coordinate of center.
        """
        self.center_x = x
        self.center_y = y

    def spawn(
        self,
        color: Tuple[int, int, int],
        count: int = 1,
        base_radius: Optional[float] = None,
        radius_variance: Optional[float] = None,
        radius_oscillation_speed: Optional[float] = None,
        orbit_speed: Optional[float] = None,
        fade_rate: Optional[float] = None,
        angle_range: Tuple[float, float] = (0, 2 * math.pi),
    ):
        """Spawn orbital particles.

        Args:
            color: RGB color tuple.
            count: Number of particles to spawn.
            base_radius: Base orbital radius (uses default if None).
            radius_variance: Amplitude of radius oscillation (uses default if None).
            radius_oscillation_speed: Speed of radius oscillation (uses default if None).
            orbit_speed: Angular velocity in radians per second (uses default if None).
            fade_rate: Alpha decrease per second (uses default if None).
            angle_range: (min, max) starting angle range in radians.
        """
        # Use defaults if not specified
        base_radius = base_radius if base_radius is not None else self.default_base_radius
        radius_variance = radius_variance if radius_variance is not None else self.default_radius_variance
        radius_oscillation_speed = radius_oscillation_speed if radius_oscillation_speed is not None else self.default_radius_oscillation_speed
        orbit_speed = orbit_speed if orbit_speed is not None else self.default_orbit_speed
        fade_rate = fade_rate if fade_rate is not None else self.default_fade_rate

        for _ in range(count):
            self.particles.append({
                "angle": random_manager.uniform(angle_range[0], angle_range[1]),
                "timer": 0.0,
                "phase": random_manager.uniform(0, 2 * math.pi),
                "color": color,
                "base_radius": base_radius,
                "radius_variance": radius_variance,
                "radius_oscillation_speed": radius_oscillation_speed,
                "orbit_speed": orbit_speed,
                "fade_rate": fade_rate,
            })

    def update(self, dt: float):
        """Update all orbital particles and render to ScatterPlotItem.

        Args:
            dt: Delta time in seconds.
        """
        # Update particles and remove faded ones
        active_particles = []
        for particle in self.particles:
            particle["timer"] += dt
            particle["angle"] += particle["orbit_speed"] * dt

            # Calculate alpha
            alpha = max(0, 255 - int(particle["timer"] * particle["fade_rate"]))
            if alpha > 0:
                active_particles.append(particle)

        self.particles = active_particles

        # Batch update all particles to single ScatterPlotItem
        if not self.particles:
            self.scatter.setData(pos=[])
            return

        positions = []
        brushes = []
        for particle in self.particles:
            # Calculate oscillating orbital radius
            osc_speed = particle["radius_oscillation_speed"]
            orbit_radius = particle["base_radius"] + particle["radius_variance"] * math.sin(particle["timer"] * osc_speed + particle["phase"])
            x = self.center_x + orbit_radius * math.cos(particle["angle"])
            y = self.center_y + orbit_radius * math.sin(particle["angle"])
            positions.append((x, y))

            # Calculate alpha
            alpha = max(0, 255 - int(particle["timer"] * particle["fade_rate"]))
            brushes.append(pg.mkBrush(*particle["color"], alpha))

        self.scatter.setData(pos=positions, brush=brushes)

    def clear(self):
        """Clear all particles."""
        self.particles.clear()
        self.scatter.setData(pos=[])

    def cleanup(self):
        """Remove the scatter plot item from the view."""
        self.view.removeItem(self.scatter)
        self.particles.clear()
