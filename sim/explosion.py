"""Crash explosion: a flash, a fireball, flying debris and a column of smoke."""
import math
import random

FIRE = [(0.0, (255, 246, 190)), (0.3, (255, 180, 50)), (0.65, (220, 70, 25)), (1.0, (60, 44, 40))]
DEBRIS_COLORS = [(236, 236, 240), (196, 44, 44), (60, 62, 68), (30, 30, 34), (140, 140, 150)]
LINGER = 6.0           # seconds the wreck burns fiercely
SMOULDER = 25.0        # seconds it keeps smoking


def _ramp(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
    return stops[-1][1]


def _rot_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _axis_angle(axis, angle):
    """Rotation matrix about `axis` (any length) by `angle`."""
    n = math.sqrt(sum(c * c for c in axis)) or 1.0
    x, y, z = (c / n for c in axis)
    c, s_, t = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return [[t * x * x + c, t * x * y - s_ * z, t * x * z + s_ * y],
            [t * x * y + s_ * z, t * y * y + c, t * y * z - s_ * x],
            [t * x * z - s_ * y, t * y * z + s_ * x, t * z * z + c]]


def _apply(m, v):
    return tuple(m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] for i in range(3))


def _cluster(polys, count, rng):
    """Split a mesh into `count` roughly spatially-compact groups of polygons."""
    cents = [tuple(sum(v[i] for v in verts) / len(verts) for i in range(3)) for verts, _, _ in polys]
    seeds = [rng.randrange(len(polys))]
    nearest = [math.dist(c, cents[seeds[0]]) for c in cents]
    while len(seeds) < min(count, len(polys)):
        i = max(range(len(polys)), key=nearest.__getitem__)
        seeds.append(i)
        nearest = [min(d, math.dist(c, cents[i])) for d, c in zip(nearest, cents)]
    groups = [[] for _ in seeds]
    for poly, c in zip(polys, cents):
        groups[min(range(len(seeds)), key=lambda k: math.dist(c, cents[seeds[k]]))].append(poly)
    return groups


class Piece:
    """A chunk of the broken plane: a rigid group of polygons that tumbles and lands."""

    def __init__(self, polys, origin, velocity, rng, intensity, inherit, drag=0.0, burn=True,
                 water_at=None):
        verts = [v for p in polys for v in p[0]]
        self.center = tuple(sum(v[i] for v in verts) / len(verts) for i in range(3))
        self.rel = [([tuple(v[i] - self.center[i] for i in range(3)) for v in p[0]], p[1], p[2])
                    for p in polys]
        self.radius = max(math.dist(v, self.center) for v in verts)
        out = [self.center[0] - origin[0], self.center[1] - origin[1] + 1.5, self.center[2] - origin[2]]
        n = math.sqrt(sum(c * c for c in out)) or 1.0
        speed = rng.uniform(6, 28) * intensity
        self.vel = tuple(velocity[i] * inherit + out[i] / n * speed for i in range(3))
        self.spin = tuple(rng.uniform(-1, 1) * rng.uniform(1.5, 6.0) * intensity for _ in range(3))
        self.rot = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
        self.bounces, self.resting, self.age = 0, False, 0.0
        self.burning = burn and rng.random() < 0.5
        self.drag, self.burn, self.water_at = drag, burn, water_at
        self.sinking = self.sunk = False

    def update(self, dt):
        self.age += dt
        if self.resting:
            return
        if self.sinking:                                               # settling slowly under the surface
            (cx, cy, cz), (vx, vy, vz) = self.center, self.vel
            damp = max(0.0, 1.0 - 2.0 * dt)
            self.vel = (vx * damp, 0.0, vz * damp)
            self.center = (cx + vx * dt, cy - 2.2 * dt, cz + vz * dt)
            w = math.sqrt(sum(c * c for c in self.spin))
            if w > 1e-6:
                self.rot = _rot_mul(_axis_angle(self.spin, w * dt), self.rot)
            if cy < -self.radius * 1.2:
                self.sunk = self.resting = True
            return
        vx, vy, vz = self.vel
        vy -= 24.0 * dt
        if self.drag:                                                  # air slows a light, flat wing
            damp = max(0.0, 1.0 - self.drag * dt)
            vx, vz = vx * damp, vz * damp
        cx, cy, cz = self.center
        self.center = (cx + vx * dt, cy + vy * dt, cz + vz * dt)
        self.vel = (vx, vy, vz)
        w = math.sqrt(sum(c * c for c in self.spin))
        if w > 1e-6:
            self.rot = _rot_mul(_axis_angle(self.spin, w * dt), self.rot)
        low = self.center[1] + min(_apply(self.rot, v)[1] for poly in self.rel for v in poly[0])
        if low < 0.0 and self.water_at and self.water_at(self.center[0], self.center[2]):
            self.sinking, self.spin = True, tuple(c * 0.3 for c in self.spin)      # splashes down
            self.vel = (self.vel[0] * 0.3, 0.0, self.vel[2] * 0.3)
        elif low < 0.0:                                                # hit the ground
            cx, cy, cz = self.center
            self.center = (cx, cy - low, cz)
            vx, vy, vz = self.vel
            self.bounces += 1
            if self.bounces >= 3 or abs(vy) < 3.0:
                self.resting, self.vel, self.spin = True, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
            else:
                self.vel = (vx * 0.6, -vy * 0.3, vz * 0.6)
                self.spin = tuple(c * 0.5 for c in self.spin)

    def polys(self):
        if self.sunk:
            return []
        # fire chars the paint (a wing that just broke off isn't burning)
        soot = min(self.age / 4.0, 1.0) * 0.8 if self.burn else 0.0
        out = []
        for verts, color, normal in self.rel:
            col = tuple(int(c * (1 - soot) + 34 * soot) for c in color)
            out.append(([tuple(self.center[i] + w for i, w in enumerate(_apply(self.rot, v)))
                         for v in verts], col, _apply(self.rot, normal)))
        return out


class _Particle:
    __slots__ = ("pos", "vel", "age", "life", "radius", "kind", "color")

    def __init__(self, pos, vel, life, radius, kind, color=None):
        self.pos, self.vel, self.life, self.radius, self.kind, self.color = pos, vel, life, radius, kind, color
        self.age = 0.0


class Explosion:
    def __init__(self, pos, velocity, scale=1.0, rng=None, polys=None, intensity=1.0, water=False,
                 water_at=None, water_color=(40, 100, 160)):
        """`polys`: the plane's world-space mesh, broken into tumbling wreckage.
        `intensity` (~0.3 slow bump .. 1.3 high-speed impact) scales the blast."""
        self.rng = rng or random.Random()
        self.pos = (pos[0], max(pos[1], 1.0), pos[2])
        self.velocity = tuple(c * 0.3 for c in velocity)      # wreckage keeps some momentum
        self.scale = max(scale, 1.0)
        self.intensity = intensity
        self.water, self.water_color = water, water_color
        self.age = 0.0
        self.particles = []
        if water:                                         # a splash and spray instead of a fireball
            for _ in range(int(90 * intensity)):
                self._spawn("spray", speed=(10, 45 * intensity), life=(0.8, 2.0), radius=(1.2, 3.5))
            for _ in range(24):
                self._spawn("mist", speed=(2, 9), life=(1.5, 3.2), radius=(3.0, 7.0))
            for _ in range(int(14 * intensity)):
                self._spawn("debris", speed=(10, 35 * intensity), life=(2.0, 3.5), radius=(0.35, 0.8))
        else:
            for _ in range(int(70 * intensity)):
                self._spawn("fire", speed=(8, 40 * intensity), life=(0.6, 1.6), radius=(2.5, 6.0 * intensity))
            for _ in range(40):
                self._spawn("smoke", speed=(3, 18), life=(2.5, 5.5), radius=(2.0, 4.5))
            for _ in range(int(40 * intensity)):
                self._spawn("debris", speed=(20, 65 * intensity), life=(3.0, 5.0), radius=(0.35, 0.9))
        self.pieces = []
        if polys:
            for group in _cluster(polys, 16, self.rng):
                if group:
                    self.pieces.append(Piece(group, self.pos, velocity, self.rng, intensity, 0.45,
                                        burn=not water, water_at=water_at))
        blob = [self.rng.uniform(0.7, 1.3) for _ in range(14)]         # irregular scorch outline
        self._scorch = [(math.cos(2 * math.pi * i / 14) * r, math.sin(2 * math.pi * i / 14) * r)
                        for i, r in enumerate(blob)]
        self._shake_dir = [self.rng.uniform(-1, 1) for _ in range(3)]

    def _spawn(self, kind, speed, life, radius, jitter=1.0, at=None):
        r, s = self.rng, self.scale
        origin = at or self.pos
        a, b = r.uniform(0, 2 * math.pi), r.uniform(-0.3, 1.0)       # biased upwards
        d = (math.cos(a) * math.sqrt(1 - b * b), b, math.sin(a) * math.sqrt(1 - b * b))
        v = r.uniform(*speed) * s ** 0.5
        vel = tuple(self.velocity[i] + d[i] * v for i in range(3))
        pos = tuple(origin[i] + r.uniform(-1, 1) * jitter * s for i in range(3))
        color = r.choice(DEBRIS_COLORS) if kind == "debris" else None
        self.particles.append(_Particle(pos, vel, r.uniform(*life), r.uniform(*radius) * s, kind, color))

    @property
    def done(self):
        return self.age > (9.0 if self.water else SMOULDER + 6.0)

    def update(self, dt):
        self.age += dt
        if self.water:
            pass                                                       # no fire on the water
        elif self.age < LINGER:                                        # the wreck keeps burning
            if self.rng.random() < 60 * dt:
                self._spawn("fire", (1, 6), (0.5, 1.1), (1.0, 2.2), jitter=0.8)
            if self.rng.random() < 35 * dt:
                self._spawn("smoke", (1, 4), (3.0, 5.0), (1.5, 3.0), jitter=0.8)
        elif self.age < SMOULDER and self.rng.random() < 6 * dt:
            self._spawn("smoke", (0.5, 2), (4.0, 7.0), (1.2, 2.4), jitter=1.2)
        for piece in self.pieces:
            piece.update(dt)
            if piece.burning and piece.age < 6.0 and self.rng.random() < 10 * dt:
                self._spawn("smoke", (0.5, 3), (1.5, 3.0), (0.6, 1.4), jitter=0.2, at=piece.center)
        alive = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.life:
                continue
            x, y, z = p.pos
            vx, vy, vz = p.vel
            if p.kind == "spray":                                      # water thrown up falls back
                vy -= 22.0 * dt
                x, y, z = x + vx * dt, y + vy * dt, z + vz * dt
                if y < 0.2:
                    continue
            elif p.kind == "debris":
                vy -= 28.0 * dt
                x, y, z = x + vx * dt, y + vy * dt, z + vz * dt
                if y <= p.radius:                                      # lands and skids to a stop
                    y, vy = p.radius, 0.0
                    vx, vz = vx * 0.85, vz * 0.85
            else:
                rise = 9.0 if p.kind == "smoke" else 5.0
                damp = max(0.0, 1.0 - 1.8 * dt)
                vx, vz, vy = vx * damp, vz * damp, vy * damp + rise * dt
                x, y, z = x + vx * dt, y + vy * dt, z + vz * dt
                y = max(y, p.radius * 0.3)
            p.pos, p.vel = (x, y, z), (vx, vy, vz)
            alive.append(p)
        self.particles = alive

    def draw(self, surface, cam):
        import pygame
        w, h = surface.get_size()
        visible = []
        for p in self.particles:
            pc = cam.to_camera(p.pos)
            if pc[2] > 1.0:
                visible.append((pc[2], p))
        visible.sort(key=lambda it: -it[0])                            # far to near
        for z, p in visible:
            t = p.age / p.life
            sx, sy = cam.project(cam.to_camera(p.pos))
            if p.kind == "debris":
                r, color, alpha = p.radius, p.color, 255
            elif p.kind == "spray":
                r, color, alpha = p.radius * (1.0 - 0.3 * t), (226, 240, 250), int(235 * (1 - t * t))
            elif p.kind == "mist":
                r, color, alpha = p.radius * (1.0 + 1.2 * t), (205, 222, 236), int(110 * (1 - t))
            elif p.kind == "fire":
                r, color, alpha = p.radius * (0.6 + 0.8 * t), _ramp(FIRE, t), 255
            else:
                shade = int(40 + 50 * t)
                r, color, alpha = p.radius * (1.0 + 1.6 * t), (shade, shade, shade), int(170 * (1 - t))
            px = max(1, min(int(r * cam.focal / z), 420))
            if sx < -px or sx > w + px or sy < -px or sy > h + px:
                continue
            if alpha >= 255:
                pygame.draw.circle(surface, color, (int(sx), int(sy)), px)
            else:
                blob = pygame.Surface((px * 2, px * 2), pygame.SRCALPHA)
                pygame.draw.circle(blob, color + (alpha,), (px, px), px)
                surface.blit(blob, (int(sx) - px, int(sy) - px))

    def draw_flash(self, surface):
        """White-out that fades in the first third of a second."""
        if self.age < 0.35:
            import pygame
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((255, 240, 200, int(220 * (1 - self.age / 0.35))))
            surface.blit(veil, (0, 0))

    # -- things the renderer draws with the world -------------------------
    def wreckage_polys(self):
        return [poly for piece in self.pieces for poly in piece.polys()]

    def ground_decals(self):
        """Scorch mark that grows then stays, plus a brief expanding dust ring: (verts, colour, None).

        On water: a few ripple rings of foam spreading out and fading instead.
        """
        x, _, z = self.pos
        size = 12.0 * self.scale * self.intensity
        if self.water:
            return self._ripples(x, z, size)
        grow = min(self.age / 0.6, 1.0)
        out = [([(x + px * size * grow, 0.12, z + pz * size * grow) for px, pz in self._scorch],
                (38, 46, 36), None)]
        if self.age < 1.1:
            r0, r1 = size * 3.2 * self.age, size * 3.2 * self.age + size * 0.5
            fade = self.age / 1.1
            color = tuple(int(a + (b - a) * fade) for a, b in ((196, 90), (184, 88), (160, 84)))
            out += self._ring(x, z, r0, r1, color)
        return out

    @staticmethod
    def _ring(x, z, r0, r1, color, segments=20):
        out = []
        for i in range(segments):
            a0, a1 = 2 * math.pi * i / segments, 2 * math.pi * (i + 1) / segments
            out.append(([(x + math.cos(a) * r, 0.14, z + math.sin(a) * r)
                         for a, r in ((a0, r0), (a1, r0), (a1, r1), (a0, r1))], color, None))
        return out

    def _ripples(self, x, z, size):
        out = []
        for k in range(4):                                             # rings leave one after another
            t = self.age - k * 0.45
            if 0 < t < 3.2:
                r0 = size * 0.9 * t
                fade = t / 3.2
                foam = (232, 242, 250)
                color = tuple(int(a + (b - a) * fade) for a, b in zip(foam, self.water_color))
                out += self._ring(x, z, r0, r0 + size * 0.22, color, 24)
        return out

    def camera_shake(self):
        """Offset for the camera: a hard jolt that dies away over ~0.9 s."""
        k = max(0.0, 1.0 - self.age / 0.9) ** 2 * 1.6 * self.scale ** 0.5 * self.intensity
        k *= 0.5 if self.water else 1.0
        return tuple(self.rng.uniform(-1, 1) * k for _ in range(3))
