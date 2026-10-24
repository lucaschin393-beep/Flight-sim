"""Procedurally generated world: runway, mountains, buildings and trees."""
import math
import random

from .meshes import box, cone

CHUNK = 1600.0
LOAD_RADIUS = 2
RUNWAY_HALF_WIDTH = 30.0
RUNWAY_HALF_LENGTH = 800.0


class Obj:
    def __init__(self, polys, center, radius, hit=None):
        self.polys, self.center, self.radius, self.hit = polys, center, radius, hit


def on_runway(pos):
    return abs(pos[0]) < RUNWAY_HALF_WIDTH and abs(pos[2]) < RUNWAY_HALF_LENGTH


def runway_polys():
    """Flat ground decals as (vertices, colour) with no shading."""
    w, l = RUNWAY_HALF_WIDTH, RUNWAY_HALF_LENGTH
    out = [([(-w, 0.05, -l), (w, 0.05, -l), (w, 0.05, l), (-w, 0.05, l)], (64, 66, 72))]
    z = -l + 40
    while z < l - 40:
        out.append(([(-1.5, 0.1, z), (1.5, 0.1, z), (1.5, 0.1, z + 40), (-1.5, 0.1, z + 40)],
                    (240, 240, 235)))
        z += 80
    return out


def _mountain(rng, x, z):
    radius = rng.uniform(300, 700)
    height = rng.uniform(250, 600)
    body = cone(x, 0, z, radius, height, 8, [(118, 108, 96), (104, 96, 86)])
    cap_h = height * 0.28
    cap = cone(x, height - cap_h, z, radius * 0.28 * 1.04, cap_h * 1.01, 8, [(245, 247, 250)])

    def hit(p):
        r = math.hypot(p[0] - x, p[2] - z)
        return r < radius and p[1] < height * (1.0 - r / radius)

    return Obj(body + cap, (x, height / 2, z), math.hypot(radius, height), hit)


def _building(rng, x, z):
    sx, sz = rng.uniform(20, 60), rng.uniform(20, 60)
    h = rng.uniform(25, 140)
    color = rng.choice([(170, 170, 176), (196, 180, 150), (150, 160, 175), (180, 120, 110)])

    def hit(p):
        return abs(p[0] - x) < sx / 2 and abs(p[2] - z) < sz / 2 and p[1] < h

    return Obj(box(x, h / 2, z, sx, h, sz, color), (x, h / 2, z), math.hypot(sx, sz, h), hit)


def _tree(rng, x, z):
    h = rng.uniform(10, 22)
    g = rng.randint(80, 130)
    base = h * 0.35

    def hit(p):
        return 0.0 <= p[1] < h and math.hypot(p[0] - x, p[2] - z) < base * (1.0 - p[1] / h)

    return Obj(cone(x, 0, z, base, h, 4, [(40, g, 55), (30, g - 15, 45)]), (x, h / 2, z), h, hit)


class World:
    def __init__(self, seed=7):
        self.seed = seed
        self._chunks = {}
        self.runway = runway_polys()

    def _generate(self, cx, cz):
        rng = random.Random(self.seed * 1_000_003 + cx * 7919 + cz * 104729)
        x0, z0 = cx * CHUNK, cz * CHUNK
        objs = []

        def spot():
            while True:
                x, z = x0 + rng.uniform(0, CHUNK), z0 + rng.uniform(0, CHUNK)
                if abs(x) > 140 or abs(z) > RUNWAY_HALF_LENGTH + 200:
                    return x, z

        if rng.random() < 0.4:
            objs.append(_mountain(rng, *spot()))
        for _ in range(rng.randint(2, 5)):
            objs.append(_building(rng, *spot()))
        for _ in range(8):
            objs.append(_tree(rng, *spot()))
        return objs

    def _chunk(self, cx, cz):
        key = (cx, cz)
        if key not in self._chunks:
            self._chunks[key] = self._generate(cx, cz)
        return self._chunks[key]

    def nearby_objects(self, pos):
        ccx, ccz = int(math.floor(pos[0] / CHUNK)), int(math.floor(pos[2] / CHUNK))
        if len(self._chunks) > 80:        # keep memory bounded
            self._chunks = {k: v for k, v in self._chunks.items()
                            if abs(k[0] - ccx) <= LOAD_RADIUS + 1 and abs(k[1] - ccz) <= LOAD_RADIUS + 1}
        for dx in range(-LOAD_RADIUS, LOAD_RADIUS + 1):
            for dz in range(-LOAD_RADIUS, LOAD_RADIUS + 1):
                for obj in self._chunk(ccx + dx, ccz + dz):
                    yield obj

    def hits_obstacle(self, pos):
        for obj in self.nearby_objects(pos):
            if obj.hit and obj.hit(pos):
                return True
        return False

    def hits_plane(self, plane, prev_pos=None):
        """True if any sampled point of the plane is inside a mountain, building or tree.

        Also tests halfway along the last step so fast planes can't skip through thin trees.
        """
        reach = plane.spec.bounding_radius
        spots = [plane.pos] if prev_pos is None else [
            tuple((a + b) / 2.0 for a, b in zip(prev_pos, plane.pos)), plane.pos]
        for spot in spots:
            points = None
            for obj in self.nearby_objects(spot):
                if not obj.hit or math.dist(obj.center, spot) > obj.radius + reach:
                    continue
                if points is None:
                    points = plane.collision_points(spot)
                if any(obj.hit(p) for p in points):
                    return True
        return False
