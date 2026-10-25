"""Selectable maps: terrain colours, sky and where the seas and lakes are.

Water is decided by a smooth "land height" field made of a few sine waves (plus an optional
slope for a coastline). Anywhere that field is below the map's sea level is water. The field is
always pushed up around the runway so the start is on land. Land/water is evaluated on a fixed
100 m grid so what you see and what the physics uses always agree.
"""
import math
import random

CELL = 100.0                 # land/water grid, metres
TILE = 400.0                 # the renderer's ground tile (4 x 4 cells)
START_ZONE = (350.0, 1150.0)  # half sizes (x, z) kept dry around the runway


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class _Waves:
    """Smooth pseudo-noise: a seeded sum of sine waves, roughly in -1.7 .. 1.7."""

    def __init__(self, seed, wavelength, stretch=(1.0, 1.0), count=7):
        rng = random.Random(seed)
        self.waves = []
        for i in range(count):
            ang = rng.uniform(0, 2 * math.pi)
            k = 2 * math.pi / (wavelength * rng.uniform(0.35, 1.6) / (1 + 0.45 * i))
            self.waves.append((k * math.cos(ang) * stretch[0], k * math.sin(ang) * stretch[1],
                               rng.uniform(0, 2 * math.pi), 1.0 / (1 + 0.35 * i)))
        self.scale = 2.0 / sum(w[3] for w in self.waves)

    def __call__(self, x, z):
        return self.scale * sum(a * math.sin(kx * x + kz * z + ph) for kx, kz, ph, a in self.waves)


class GameMap:
    def __init__(self, name, description, seed, *, level, wavelength=3000.0, stretch=(1.0, 1.0),
                 slope=(0.0, 0.0), amp=1.0, land=((98, 150, 92), (90, 140, 84)),
                 sand=(214, 200, 150), shallow=(70, 150, 200), deep=(30, 86, 150),
                 far=(120, 156, 116), sky_top=(70, 120, 200), horizon=(190, 214, 232),
                 mountains=0.4, buildings=(2, 5), trees=8, tree_tint=(40, 1.0, 55),
                 rock=((118, 108, 96), (104, 96, 86)), cap=(245, 247, 250)):
        self.name, self.description, self.seed = name, description, seed
        self.level, self.slope, self.amp = level, slope, amp
        self.land, self.sand, self.shallow, self.deep, self.far = land, sand, shallow, deep, far
        self.sky_top, self.horizon = sky_top, horizon
        self.mountains, self.buildings, self.trees = mountains, buildings, trees
        self.tree_tint, self.rock, self.cap = tree_tint, rock, cap
        self._noise = _Waves(seed, wavelength, stretch)
        self._tiles = {}

    # -- the land height field ---------------------------------------------
    def height(self, x, z):
        zx, zz = START_ZONE
        d = math.hypot(x / zx, z / zz)
        dry = 4.0 * _smooth((1.9 - d) / 0.9)                 # forced land at the runway, easing off
        return (self._noise(x, z) * self.amp + self.slope[0] * x + self.slope[1] * z + dry)

    def _cell_centre(self, ix, iz):
        return (ix + 0.5) * CELL, (iz + 0.5) * CELL

    def water_at(self, x, z):
        """Whether the ground at (x, z) is water (decided per 100 m cell)."""
        cx, cz = self._cell_centre(math.floor(x / CELL), math.floor(z / CELL))
        return self.height(cx, cz) < self.level

    def has_water(self):
        return self.level > -50

    def _cell(self, ix, iz):
        """(colour, is_water) of one 100 m cell."""
        x, z = self._cell_centre(ix, iz)
        h = self.height(x, z) - self.level
        if h < 0:
            return (self.deep if h < -0.3 else self.shallow), True
        if h < 0.08:
            return self.sand, False
        return self.land[(ix + iz) & 1], False

    def tile(self, tx, tz):
        """Colours for the 400 m tile (tx, tz): ((colour, is_water),) if uniform, else 16 cells."""
        key = (tx, tz)
        cached = self._tiles.get(key)
        if cached is None:
            if len(self._tiles) > 6000:
                self._tiles.clear()
            n = int(TILE / CELL)
            cells = [self._cell(tx * n + i, tz * n + j) for j in range(n) for i in range(n)]
            cached = (cells[0],) if all(c[0] == cells[0][0] for c in cells) else cells
            self._tiles[key] = cached
        return cached

    def water_fraction(self, extent=12000.0, step=200.0):
        """Share of the ground within `extent` metres of the runway that is water."""
        n = int(2 * extent / step)
        wet = sum(self.water_at(-extent + i * step, -extent + j * step) for i in range(n) for j in range(n))
        return wet / float(n * n)


MAPS = [
    GameMap("Home Fields", "The original: green plains, no water.", 7, level=-99.0),
    GameMap("Emerald Lakes", "Green hills dotted with lakes.", 11, level=-0.55, wavelength=2600.0,
            land=((88, 150, 84), (78, 138, 76)), mountains=0.3, trees=10,
            sand=(200, 196, 140), shallow=(74, 164, 190), deep=(28, 100, 140)),
    GameMap("Island Chain", "A warm sea scattered with islands; the runway is on one.", 23, level=0.25,
            wavelength=2300.0, amp=1.1, land=((118, 168, 92), (108, 158, 84)), sand=(232, 218, 160),
            shallow=(64, 190, 210), deep=(20, 110, 170), sky_top=(60, 130, 220), horizon=(196, 226, 240),
            far=(70, 160, 195), mountains=0.2, buildings=(1, 3), trees=9, tree_tint=(30, 1.05, 50)),
    GameMap("Sunset Coast", "Dry shores on the west, open ocean to the east, with a few ponds.", 37,
            level=0.0, wavelength=2400.0, amp=0.55, slope=(-0.0005, 0.0), land=((196, 170, 112), (188, 160, 102)),
            sand=(230, 206, 150), shallow=(80, 150, 176), deep=(34, 82, 130), far=(176, 166, 130),
            sky_top=(220, 120, 80), horizon=(246, 196, 150), mountains=0.35, buildings=(2, 4), trees=4,
            tree_tint=(118, 0.9, 52), rock=((156, 112, 84), (140, 98, 74)), cap=(220, 190, 160)),
    GameMap("Frozen Fjords", "Snowy highlands cut by long, dark fjords and mountain lakes.", 51,
            level=-0.25, wavelength=2800.0, stretch=(2.6, 0.7), land=((236, 240, 246), (224, 230, 240)),
            sand=(202, 210, 220), shallow=(120, 170, 200), deep=(34, 70, 110), far=(196, 206, 220),
            sky_top=(96, 130, 190), horizon=(208, 220, 236), mountains=0.7, buildings=(0, 2), trees=10,
            tree_tint=(30, 0.85, 70), rock=((120, 124, 134), (104, 108, 120)), cap=(250, 252, 255)),
]
