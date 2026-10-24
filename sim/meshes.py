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


def prism(v, color):
    """Convex hexahedron from 8 vertices: 0-3 one quad, 4-7 the quad opposite it."""
    center = tuple(sum(p[i] for p in v) / 8.0 for i in range(3))
    faces = ([0, 1, 2, 3], [4, 5, 6, 7], [0, 3, 7, 4], [1, 5, 6, 2], [0, 4, 5, 1], [3, 2, 6, 7])
    return [oriented_poly([v[i] for i in f], color, center) for f in faces]


def loft(stations, sides, color_fn, dx=0.0):
    """Smooth body along z. stations: (z, half_width, half_height, centre_y), nose first."""
    rings = [[(dx + rx * math.cos(2 * math.pi * i / sides), cy + ry * math.sin(2 * math.pi * i / sides), z)
              for i in range(sides)] for z, rx, ry, cy in stations]
    polys = []
    for k in range(len(stations) - 1):
        axis = (dx, (stations[k][3] + stations[k + 1][3]) / 2.0,
                (stations[k][0] + stations[k + 1][0]) / 2.0)
        for i in range(sides):
            j = (i + 1) % sides
            polys.append(oriented_poly([rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]],
                                       color_fn(k, i), axis))
    for ring, nxt, st in ((rings[0], stations[1], stations[0]), (rings[-1], stations[-2], stations[-1])):
        polys.append(oriented_poly(ring, color_fn(0, 0), (dx, nxt[3], nxt[0])))
    return polys


def cylinder_x(cx, cy, cz, radius, width, sides, color):
    """Wheel: a short cylinder whose axis is x."""
    polys, ends = [], []
    for sx in (-1, 1):
        ends.append([(cx + sx * width / 2.0, cy + radius * math.cos(2 * math.pi * i / sides),
                      cz + radius * math.sin(2 * math.pi * i / sides)) for i in range(sides)])
    for i in range(sides):
        j = (i + 1) % sides
        polys.append(oriented_poly([ends[0][i], ends[0][j], ends[1][j], ends[1][i]], color,
                                   (cx, cy, cz)))
    for ring in ends:
        polys.append(oriented_poly(ring, (30, 32, 36), (cx, cy, cz)))
    return polys


def wing_panel(t0, t1, side, color, x0, span, le, te, y, thick):
    """A tapered, swept wing section between span fractions t0..t1; le/te/y/thick are (root, tip)."""
    def at(t, pair):
        return pair[0] + (pair[1] - pair[0]) * t
    v = []
    for sign in (1, -1):                               # top then bottom surface
        for t, lead in ((t0, True), (t0, False), (t1, False), (t1, True)):
            z = at(t, le if lead else te)
            v.append((side * (x0 + span * t), at(t, y) + sign * at(t, thick) / 2.0, z))
    return prism(v, color)


def fin_panel(color, x=0.0, y=(0.3, 1.95), le=(-2.9, -3.75), te=(-4.25, -4.3), w=(0.07, 0.035)):
    """Swept vertical fin at lateral offset x; y/le/te/w are (root, tip)."""
    v = []
    for sign in (1, -1):
        v += [(x + sign * w[0], y[0], le[0]), (x + sign * w[0], y[0], te[0]),
              (x + sign * w[1], y[1], te[1]), (x + sign * w[1], y[1], le[1])]
    return prism(v, color)


def propeller(angle, z=4.95, length=1.35):
    """Two-blade propeller turned by `angle` about the z axis, in front of the spinner."""
    polys = []
    for k in range(2):
        a = angle + k * math.pi
        ca, sa = math.cos(a), math.sin(a)
        def pt(r, w, z):
            return (ca * r - sa * w, sa * r + ca * w, z)
        v = [pt(0.15, -0.11, z), pt(length, -0.07, z), pt(length, 0.07, z), pt(0.15, 0.11, z),
             pt(0.15, -0.11, z - 0.07), pt(length, -0.07, z - 0.07), pt(length, 0.07, z - 0.07),
             pt(0.15, 0.11, z - 0.07)]
        polys += prism(v, (40, 42, 48))
    return polys


def trainer_mesh():
    """Single-engine light plane in local coords: x = right, y = up, z = forward."""
    white, red, grey = (238, 238, 242), (196, 44, 44), (200, 204, 212)
    glass, dark = (46, 78, 112), (44, 46, 52)

    def body_color(k, i):
        if k <= 1:
            return red                               # engine cowling
        if i in (9, 0, 4, 5):
            return red                               # cheat line
        return grey if i in (6, 7, 8) else white

    polys = loft([(4.3, 0.25, 0.25, 0.0), (4.0, 0.55, 0.55, 0.0), (3.2, 0.66, 0.66, 0.0),
                  (1.5, 0.7, 0.8, 0.05), (-0.5, 0.65, 0.8, 0.1), (-2.5, 0.45, 0.5, 0.2),
                  (-4.2, 0.12, 0.2, 0.3)], 10, body_color)
    polys += loft([(2.0, 0.05, 0.05, 0.8), (1.5, 0.52, 0.38, 0.9), (0.2, 0.6, 0.42, 0.92),
                   (-1.0, 0.45, 0.34, 0.86), (-1.7, 0.05, 0.05, 0.8)], 8, lambda k, i: glass)
    polys += loft([(4.5, 0.02, 0.02, 0.0), (4.3, 0.2, 0.2, 0.0), (4.9, 0.05, 0.05, 0.0)],
                  8, lambda k, i: dark)                                    # spinner

    wing = dict(x0=0.4, span=5.1, le=(0.9, 0.6), te=(-1.1, -0.6), y=(-0.35, -0.15), thick=(0.22, 0.1))
    for side in (1, -1):
        polys += wing_panel(0.0, 0.8, side, white, **wing)
        polys += wing_panel(0.8, 1.0, side, red, **wing)                   # wing tip
    stab = dict(x0=0.1, span=2.0, le=(-3.2, -3.75), te=(-4.3, -4.15), y=(0.22, 0.28), thick=(0.1, 0.06))
    for side in (1, -1):
        polys += wing_panel(0.0, 1.0, side, white, **stab)
    polys += fin_panel(red)

    gear = []
    for x in (-1.3, 1.3):                                                  # main gear
        gear += box(x * 0.85, -0.55, 0.5, 0.08, 0.5, 0.1, dark)
        gear += cylinder_x(x, -0.7, 0.5, 0.3, 0.2, 8, (22, 24, 28))
    gear += box(0, -0.5, 3.0, 0.08, 0.4, 0.1, dark)                       # nose gear
    gear += cylinder_x(0, -0.7, 3.0, 0.28, 0.16, 8, (22, 24, 28))
    return polys, gear


def _wheel(x, y, z, r=0.3, w=0.2):
    return cylinder_x(x, y, z, r, w, 8, (22, 24, 28))


def biplane_mesh():
    """Open-cockpit biplane (yellow with blue trim)."""
    yellow, blue, dark, fabric = (236, 200, 60), (40, 76, 150), (44, 46, 52), (226, 190, 70)

    def body_color(k, i):
        if k <= 1:
            return blue
        return fabric if i in (1, 2, 3, 4, 9, 0) else (200, 168, 60)

    polys = loft([(3.2, 0.3, 0.3, 0.0), (2.9, 0.62, 0.62, 0.0), (2.2, 0.68, 0.68, 0.0),
                  (0.8, 0.6, 0.7, 0.05), (-1.0, 0.5, 0.6, 0.12), (-3.0, 0.3, 0.35, 0.2),
                  (-4.4, 0.1, 0.15, 0.25)], 10, body_color)
    polys += box(0, 0.78, 0.7, 0.7, 0.12, 0.5, dark)                       # windscreen / cockpit rim
    low = dict(x0=0.4, span=4.6, le=(0.6, 0.6), te=(-0.9, -0.9), y=(-0.35, -0.2), thick=(0.14, 0.12))
    up = dict(x0=0.0, span=5.0, le=(0.8, 0.8), te=(-0.8, -0.8), y=(1.15, 1.15), thick=(0.14, 0.12))
    for side in (1, -1):
        polys += wing_panel(0.0, 1.0, side, yellow, **low)
        polys += wing_panel(0.0, 1.0, side, yellow, **up)
        for x in (1.6, 4.4):                                              # interplane struts
            polys += box(side * x, 0.45, 0.45, 0.07, 1.4, 0.07, dark)
            polys += box(side * x, 0.45, -0.6, 0.07, 1.4, 0.07, dark)
    polys += box(0, 0.8, 0.3, 0.1, 0.5, 0.1, dark) + box(0.6, 0.9, 0.3, 0.1, 0.4, 0.1, dark)
    polys += box(0.3, 0.9, 0.9, 0.1, 0.3, 0.1, dark)
    stab = dict(x0=0.1, span=1.9, le=(-3.5, -3.9), te=(-4.6, -4.5), y=(0.22, 0.25), thick=(0.1, 0.06))
    for side in (1, -1):
        polys += wing_panel(0.0, 1.0, side, yellow, **stab)
    polys += fin_panel(blue, y=(0.3, 1.7), le=(-3.2, -4.0), te=(-4.55, -4.6))
    gear = []
    for x in (-1.1, 1.1):
        gear += box(x * 0.8, -0.3, 0.9, 0.07, 0.8, 0.07, dark)
        gear += _wheel(x, -0.7, 0.9, 0.32, 0.16)
    gear += box(0, -0.15, -3.5, 0.06, 0.1, 0.3, dark)                    # tail skid
    return polys, gear


def jet_mesh():
    """Swept-wing fighter with twin fins (grey)."""
    grey, light, dark, glass = (122, 130, 142), (168, 176, 188), (44, 46, 52), (60, 96, 130)

    def body_color(k, i):
        if k >= 5:
            return dark                                                    # exhaust
        return light if i in (6, 7, 8) else grey

    polys = loft([(6.2, 0.05, 0.05, 0.0), (5.0, 0.35, 0.35, 0.0), (3.0, 0.7, 0.62, 0.05),
                  (0.0, 0.8, 0.7, 0.05), (-3.0, 0.78, 0.66, 0.05), (-4.6, 0.62, 0.5, 0.05),
                  (-5.2, 0.5, 0.42, 0.05)], 10, body_color)
    polys += loft([(3.4, 0.05, 0.05, 0.55), (2.7, 0.4, 0.35, 0.7), (1.4, 0.48, 0.42, 0.78),
                   (0.0, 0.4, 0.3, 0.7), (-0.8, 0.05, 0.05, 0.6)], 8, lambda k, i: glass)
    wing = dict(x0=0.5, span=4.2, le=(0.5, -2.6), te=(-3.1, -3.5), y=(-0.2, -0.1), thick=(0.18, 0.07))
    stab = dict(x0=0.6, span=2.2, le=(-3.2, -4.8), te=(-5.0, -5.4), y=(0.0, 0.0), thick=(0.14, 0.06))
    for side in (1, -1):
        polys += wing_panel(0.0, 1.0, side, grey, **wing)
        polys += wing_panel(0.0, 1.0, side, light, **stab)
        polys += fin_panel(grey, x=side * 0.95, y=(0.5, 2.0), le=(-3.4, -4.7), te=(-5.0, -5.3),
                           w=(0.06, 0.03))
    for x in (-0.6, 0.6):                                                  # intakes
        polys += box(x * 1.4, 0.0, 2.4, 0.5, 0.55, 1.6, dark)
    gear = []
    gear += box(0, -0.65, 3.4, 0.08, 0.4, 0.1, dark)
    gear += _wheel(0, -0.95, 3.4, 0.25, 0.14)
    for x in (-1.2, 1.2):
        gear += box(x, -0.7, -0.5, 0.08, 0.5, 0.1, dark)
        gear += _wheel(x, -0.95, -0.5, 0.25, 0.16)
    return polys, gear


def airliner_mesh():
    """Twin-engine airliner (white, blue tail), roughly 6x the trainer's size."""
    white, blue, grey, dark, glass = (240, 240, 244), (40, 80, 170), (206, 210, 218), (44, 46, 52), (40, 60, 90)

    def body_color(k, i):
        if i in (1, 2, 3):
            return white
        if i in (9, 0, 4, 5):
            return blue if k not in (0,) else white                        # window / cheat line
        return grey

    gear = []
    polys = loft([(15.5, 0.3, 0.3, 0.3), (14.0, 1.2, 1.2, 0.3), (11.0, 1.9, 1.95, 0.3),
                  (5.0, 2.05, 2.1, 0.3), (-6.0, 2.05, 2.1, 0.3), (-11.0, 1.6, 1.7, 0.7),
                  (-15.0, 0.9, 1.1, 1.3), (-16.0, 0.3, 0.4, 1.5)], 10, body_color)
    polys += loft([(15.0, 0.9, 0.5, 1.0), (14.2, 1.15, 0.7, 1.05), (13.4, 1.2, 0.5, 1.1)], 6,
                  lambda k, i: glass)                                      # cockpit windscreen
    wing = dict(x0=1.6, span=15.0, le=(3.0, -4.5), te=(-3.5, -7.5), y=(-1.1, 0.4), thick=(0.9, 0.25))
    stab = dict(x0=0.8, span=5.2, le=(-11.5, -15.0), te=(-15.0, -16.5), y=(1.1, 1.8), thick=(0.4, 0.15))
    for side in (1, -1):
        polys += wing_panel(0.0, 1.0, side, white, **wing)
        polys += wing_panel(0.0, 1.0, side, white, **stab)
        ex = side * 6.2                                                    # under-wing engine
        polys += loft([(4.2, 0.0, 0.0, -2.2), (4.0, 1.0, 1.0, -2.2), (1.5, 1.15, 1.15, -2.2),
                       (-2.0, 1.0, 1.0, -2.2), (-2.8, 0.6, 0.6, -2.2)], 10,
                      lambda k, i: dark if k == 0 else grey, dx=ex)
        for z in (-0.8,):
            polys += box(ex, -1.5, z, 0.3, 0.8, 1.6, grey)                 # pylon
        gear += box(side * 4.5, -2.0, 0.5, 0.2, 1.4, 0.2, dark)
        gear += cylinder_x(side * 4.5, -2.9, 0.5, 0.5, 0.5, 8, (22, 24, 28))
    polys += fin_panel(blue, y=(1.6, 6.8), le=(-9.0, -14.5), te=(-15.0, -16.2), w=(0.25, 0.1))
    gear += box(0, -2.0, 11.0, 0.2, 1.2, 0.2, dark)
    gear += cylinder_x(0, -2.8, 11.0, 0.45, 0.4, 8, (22, 24, 28))
    return polys, gear


def exhaust_flame(throttle, t, z, y, radius):
    """Afterburner plume behind a nozzle at (0, y, z): glows from mid throttle, roars at full.

    Returns unlit polygons (normal None); `t` drives the flicker.
    """
    power = (throttle - 0.3) / 0.7
    if power <= 0:
        return []
    flick = 1.0 + 0.12 * math.sin(t * 9.0) + 0.08 * math.sin(t * 23.0 + 1.0)
    length = radius * (3.0 + 9.0 * power ** 1.5) * flick
    polys = []
    for scale, length_k, outer, inner in ((1.0, 1.0, (255, 120, 30), (255, 180, 60)),
                                          (0.6, 0.62, (255, 200, 90), (255, 244, 200))):
        r, ln = radius * scale, length * length_k
        stations = [(z + 0.05, r * 0.85, r * 0.85, y), (z - ln * 0.3, r, r, y),
                    (z - ln * 0.65, r * 0.55, r * 0.55, y), (z - ln, 0.03, 0.03, y)]
        for verts, color, _ in loft(stations, 8, lambda k, i: outer if k < 2 else inner):
            polys.append((verts, color, None))
    return polys
