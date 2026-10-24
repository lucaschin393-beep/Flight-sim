"""Tiny 3-vector helpers. World axes: x = east/right, y = up, z = north/forward."""
import math


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    n = length(a)
    return (0.0, 0.0, 0.0) if n < 1e-9 else scale(a, 1.0 / n)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def euler_basis(yaw, pitch, roll):
    """Return (forward, right, up) for the given angles in radians.

    yaw 0 faces +z and positive yaw turns toward +x; positive pitch is
    nose up; positive roll banks to the right (right wing down).
    """
    cy, sy = math.cos(yaw), math.sin(yaw)
    fwd0, right0, up0 = (sy, 0.0, cy), (cy, 0.0, -sy), (0.0, 1.0, 0.0)

    cp, sp = math.cos(pitch), math.sin(pitch)
    fwd = add(scale(fwd0, cp), scale(up0, sp))
    up = add(scale(up0, cp), scale(fwd0, -sp))

    cr, sr = math.cos(roll), math.sin(roll)
    right = add(scale(right0, cr), scale(up, -sr))
    up = add(scale(up, cr), scale(right0, sr))
    return fwd, right, up
