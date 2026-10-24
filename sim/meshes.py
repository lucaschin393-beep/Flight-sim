"""Low-poly shape builders. A polygon is (vertices, colour, outward_normal)."""
import math

from .vec import cross, dot, normalize, sub


def oriented_poly(verts, color, center):
    """Build a polygon whose normal points away from `center`."""
    n = normalize(cross(sub(verts[1], verts[0]), sub(verts[2], verts[0])))
    cx = sum(v[0] for v in verts) / len(verts)
    cy = sum(v[1] for v in verts) / len(verts)
    cz = sum(v[2] for v in verts) / len(verts)
    if dot(n, (cx - center[0], cy - center[1], cz - center[2])) < 0:
        n = (-n[0], -n[1], -n[2])
    return (verts, color, n)


def box(cx, cy, cz, sx, sy, sz, color):
    h = (sx / 2.0, sy / 2.0, sz / 2.0)
    center = (cx, cy, cz)
    polys = []
    for axis in range(3):
        for sign in (-1, 1):
            a, b = [i for i in range(3) if i != axis]
            quad = []
            for da, db in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                p = [0.0, 0.0, 0.0]
                p[axis] = center[axis] + sign * h[axis]
                p[a] = center[a] + da * h[a]
                p[b] = center[b] + db * h[b]
                quad.append(tuple(p))
            polys.append(oriented_poly(quad, color, center))
    return polys


def cone(cx, base_y, cz, radius, height, sides, colors):
    """Upright pyramid/cone. `colors` is a list cycled per side."""
    apex = (cx, base_y + height, cz)
    center = (cx, base_y + height * 0.3, cz)
    ring = [(cx + radius * math.cos(2 * math.pi * i / sides), base_y,
             cz + radius * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
    return [oriented_poly([ring[i], ring[(i + 1) % sides], apex],
                          colors[i % len(colors)], center)
            for i in range(sides)]


def pyramid_z(cx, cy, z_base, z_tip, half_w, half_h, color, center):
    """Four-sided pyramid pointing along z (used for the plane's nose)."""
    corners = [(cx - half_w, cy - half_h, z_base), (cx + half_w, cy - half_h, z_base),
               (cx + half_w, cy + half_h, z_base), (cx - half_w, cy + half_h, z_base)]
    tip = (cx, cy, z_tip)
    return [oriented_poly([corners[i], corners[(i + 1) % 4], tip], color, center)
            for i in range(4)]


def airplane_mesh():
    """Plane in local coords: x = right, y = up, z = forward."""
    white, red, grey = (236, 236, 240), (200, 50, 50), (70, 76, 86)
    polys = []
    polys += box(0, 0, 0, 1.3, 1.3, 7.0, white)                      # fuselage
    polys += pyramid_z(0, 0, 3.5, 5.6, 0.65, 0.65, red, (0, 0, 0))   # nose
    polys += box(0, 0.5, 0.3, 1.0, 0.5, 2.0, grey)                   # canopy
    polys += box(0, -0.1, 0.5, 11.0, 0.15, 2.0, red)                 # wings
    polys += box(0, 0.15, -3.4, 4.0, 0.12, 1.1, red)                 # tailplane
    polys += box(0, 0.95, -3.4, 0.12, 1.6, 1.3, red)                 # fin
    return polys
