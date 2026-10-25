"""Software 3D renderer: perspective projection + painter's algorithm."""
import math

import pygame

from . import config as cfg
from .vec import dot, normalize, sub
from .maps import CELL, MAPS
from .world import runway_polys

NEAR = 0.5
LIGHT = normalize((0.4, 0.8, -0.3))
SUN_FOR_SHADOW = (0.15, 1.0, -0.1)     # steeper than LIGHT so the shadow stays close below you
TILE = 400.0                           # must match sim.maps.TILE
TILE_RADIUS = 7


def clip_near(poly):
    """Clip a camera-space polygon against the near plane (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        a_in, b_in = a[2] >= NEAR, b[2] >= NEAR
        if a_in:
            out.append(a)
        if a_in != b_in:
            t = (NEAR - a[2]) / (b[2] - a[2])
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, NEAR))
    return out


def clip_screen(pts, w, h):
    """Clip a 2D polygon to the screen rectangle.

    Keeps pygame from scan-converting enormous off-screen polygons (the
    ground plane reaches millions of pixels when projected near the camera).
    """
    m = 2
    for axis, bound, keep_less in ((0, -m, False), (0, w + m, True),
                                   (1, -m, False), (1, h + m, True)):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            a_in = (a[axis] <= bound) if keep_less else (a[axis] >= bound)
            b_in = (b[axis] <= bound) if keep_less else (b[axis] >= bound)
            if a_in:
                out.append(a)
            if a_in != b_in:
                t = (bound - a[axis]) / (b[axis] - a[axis])
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        pts = out
        if not pts:
            break
    return pts


def apply_fog(color, depth, fog=cfg.FOG_COLOR):
    t = (depth - cfg.FOG_START) / (cfg.FOG_END - cfg.FOG_START)
    if t <= 0:
        return color
    t = min(t, 1.0)
    return tuple(int(c + (f - c) * t) for c, f in zip(color, fog))


def shade(color, normal):
    k = 0.45 + 0.55 * max(0.0, dot(normal, LIGHT))
    return (int(color[0] * k), int(color[1] * k), int(color[2] * k))


class Renderer:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.time = 0.0                      # seconds, makes the water shimmer
        self.set_map(MAPS[0])
        self.runway = runway_polys()

    def set_map(self, game_map):
        """Switch sky, fog and ground colours to a map's."""
        self.map = game_map
        self.fog = game_map.horizon
        self.sky = self._make_sky()

    def _make_sky(self):
        surf = pygame.Surface((self.w, self.h))
        horizon = self.h // 2
        for y in range(self.h):
            t = min(1.0, y / float(horizon))
            color = tuple(int(a + (b - a) * t) for a, b in zip(self.map.sky_top, self.map.horizon))
            pygame.draw.line(surf, color, (0, y), (self.w, y))
        return surf

    # -- polygon pipeline ------------------------------------------------
    def _project(self, cam, verts):
        """World polygon -> (mean depth, screen points) or None if not visible."""
        pc = clip_near([cam.to_camera(v) for v in verts])
        if len(pc) < 3:
            return None
        pts = [cam.project(p) for p in pc]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < 0 or min(xs) > self.w or max(ys) < 0 or min(ys) > self.h:
            return None
        pts = clip_screen(pts, self.w, self.h)
        if len(pts) < 3:
            return None
        return sum(p[2] for p in pc) / len(pc), pts

    def _items(self, cam, polys, lit):
        items = []
        for poly in polys:
            r = self._project(cam, poly[0])
            if r is None or r[0] > cfg.FOG_END:
                continue
            color = shade(poly[1], poly[2]) if lit and poly[2] is not None else poly[1]
            items.append((r[0], apply_fog(color, r[0], self.fog), r[1]))
        return items

    @staticmethod
    def _paint(surface, items, sort=True):
        if sort:
            items.sort(key=lambda it: -it[0])
        for _, color, pts in items:
            pygame.draw.polygon(surface, color, pts)

    # -- scene -----------------------------------------------------------
    def _shimmer(self, cell, x, z):
        """Water slowly glints; land is left as it is."""
        color, is_water = cell
        if not is_water:
            return color
        k = 7.0 * math.sin(self.time * 0.9 + x * 0.004 + z * 0.0031) + 3.0 * math.sin(self.time * 1.7 + z * 0.006)
        return tuple(max(0, min(255, int(c + k))) for c in color)

    def _ground(self, surface, cam):
        px, pz = cam.pos[0], cam.pos[2]
        big = 60000.0
        base = [(px - big, 0, pz - big), (px + big, 0, pz - big),
                (px + big, 0, pz + big), (px - big, 0, pz + big)]
        self._paint(surface, self._items(cam, [(base, self.map.far, None)], False))

        reach = max(cam.cx, cam.cy) / cam.focal * 1.15      # sideways extent of the view per metre ahead
        ix, iz = int(math.floor(px / TILE)), int(math.floor(pz / TILE))
        tiles = []
        for dx in range(-TILE_RADIUS, TILE_RADIUS + 1):
            for dz in range(-TILE_RADIUS, TILE_RADIUS + 1):
                x0, z0 = (ix + dx) * TILE, (iz + dz) * TILE
                center = (x0 + TILE / 2, 0, z0 + TILE / 2)
                d = sub(center, cam.pos)
                ahead = dot(d, cam.fwd)
                if ahead < -TILE:                  # behind the camera
                    continue
                if abs(dot(d, cam.right)) > ahead * reach + TILE * 1.5:   # outside the view sideways
                    continue
                cells = self.map.tile(ix + dx, iz + dz)
                if len(cells) == 1:
                    tiles.append(([(x0, 0, z0), (x0 + TILE, 0, z0), (x0 + TILE, 0, z0 + TILE),
                                   (x0, 0, z0 + TILE)], self._shimmer(cells[0], x0, z0), None))
                    continue
                n = int(TILE / CELL)                    # a shoreline tile: draw its 100 m cells
                for k, cell in enumerate(cells):
                    cx0, cz0 = x0 + (k % n) * CELL, z0 + (k // n) * CELL
                    tiles.append(([(cx0, 0, cz0), (cx0 + CELL, 0, cz0), (cx0 + CELL, 0, cz0 + CELL),
                                   (cx0, 0, cz0 + CELL)], self._shimmer(cell, cx0, cz0), None))
        self._paint(surface, self._items(cam, tiles, False))

    def _draw_shadow(self, surface, cam, plane):
        """The plane's real silhouette cast along the sun direction onto the ground.

        Drawn as one translucent layer, so overlapping parts don't darken twice; it fades
        with altitude.
        """
        lx, ly, lz = SUN_FOR_SHADOW
        shapes = []
        for verts, _, _ in plane.world_polys(flame=False):
            ground = [(x - lx / ly * y, 0.12, z - lz / ly * y) for x, y, z in verts]
            r = self._project(cam, ground)
            if r:
                shapes.append(r[1])
        if not shapes:
            return
        xs = [p[0] for pts in shapes for p in pts]
        ys = [p[1] for pts in shapes for p in pts]
        x0, y0 = int(max(min(xs), 0)), int(max(min(ys), 0))
        x1, y1 = int(min(max(xs), self.w)) + 1, int(min(max(ys), self.h)) + 1
        if x1 <= x0 or y1 <= y0:
            return
        layer = pygame.Surface((x1 - x0, y1 - y0), pygame.SRCALPHA)
        alpha = int(120 - 80 * min(plane.altitude / 500.0, 1.0))
        for pts in shapes:
            pygame.draw.polygon(layer, (10, 14, 10, alpha), [(px - x0, py - y0) for px, py in pts])
        surface.blit(layer, (x0, y0))

    def render(self, surface, cam, world, plane, draw_plane, wrecked=False, extra_decals=(),
               extra_polys=()):
        surface.blit(self.sky, (0, 0))
        self._ground(surface, cam)

        decals = list(self.runway)
        decals = [(v, c, None) for v, c in decals] + list(extra_decals)
        self._paint(surface, self._items(cam, decals, False), sort=False)
        if plane.altitude < 700 and not wrecked:
            self._draw_shadow(surface, cam, plane)

        items = []
        for obj in world.nearby_objects(cam.pos):
            d = sub(obj.center, cam.pos)
            if dot(d, cam.fwd) < -obj.radius:
                continue
            if dot(d, d) > (cfg.FOG_END + obj.radius) ** 2:
                continue
            items += self._items(cam, obj.polys, True)
        items += self._items(cam, extra_polys, True)
        if draw_plane and not wrecked:
            items += self._items(cam, plane.world_polys(), True)
        self._paint(surface, items)
