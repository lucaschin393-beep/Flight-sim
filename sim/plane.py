"""Simple arcade flight model."""
import math

from . import config as cfg
from .meshes import airplane_mesh
from .vec import add, euler_basis, scale

_MESH = airplane_mesh()
GRAVITY_SPEED_LOSS = 25.0


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Plane:
    def __init__(self):
        self.reset()

    def reset(self):
        self.pos = cfg.START_POSITION
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.speed = cfg.START_SPEED
        self.throttle = 0.5
        self.stalled = False
        self.vertical_speed = 0.0

    @property
    def basis(self):
        return euler_basis(self.yaw, self.pitch, self.roll)

    @property
    def altitude(self):
        return self.pos[1]

    @property
    def heading_degrees(self):
        return math.degrees(self.yaw) % 360.0

    def update(self, dt, pitch_in, roll_in, throttle_in):
        """pitch_in: +1 nose up. roll_in: +1 bank right. throttle_in: +1 more."""
        self.throttle = _clamp(self.throttle + throttle_in * cfg.THROTTLE_RATE * dt, 0.0, 1.0)

        self.pitch = _clamp(self.pitch + pitch_in * cfg.PITCH_RATE * dt,
                            -cfg.MAX_PITCH, cfg.MAX_PITCH)
        self.roll = _clamp(self.roll + roll_in * cfg.ROLL_RATE * dt,
                           -cfg.MAX_ROLL, cfg.MAX_ROLL)
        if roll_in == 0:                      # gently level the wings
            self.roll -= self.roll * min(1.0, 0.35 * dt)

        # A banked aircraft turns.
        self.yaw += 0.8 * math.sin(self.roll) * min(self.speed / 60.0, 1.5) * dt

        # Speed: thrust pulls toward a target, climbing bleeds speed.
        target = cfg.MIN_SPEED + self.throttle * (cfg.MAX_SPEED - cfg.MIN_SPEED)
        self.speed += (target - self.speed) * 0.4 * dt
        self.speed -= math.sin(self.pitch) * GRAVITY_SPEED_LOSS * dt
        self.speed = _clamp(self.speed, 0.0, cfg.MAX_SPEED * 1.4)

        fwd, _, _ = self.basis
        x, y, z = add(self.pos, scale(fwd, self.speed * dt))

        # Stall: lose lift and the nose drops.
        self.stalled = self.speed < cfg.STALL_SPEED
        if self.stalled:
            y -= (cfg.STALL_SPEED - self.speed) * 0.6 * dt
            self.pitch = _clamp(self.pitch - 0.6 * dt, -cfg.MAX_PITCH, cfg.MAX_PITCH)

        self.vertical_speed = (y - self.pos[1]) / dt if dt > 0 else 0.0
        self.pos = (x, y, z)

    def world_polys(self):
        """The plane's mesh transformed into world space."""
        fwd, right, up = self.basis
        px, py, pz = self.pos

        def to_world(p):
            return (px + right[0] * p[0] + up[0] * p[1] + fwd[0] * p[2],
                    py + right[1] * p[0] + up[1] * p[1] + fwd[1] * p[2],
                    pz + right[2] * p[0] + up[2] * p[1] + fwd[2] * p[2])

        out = []
        for verts, color, n in _MESH:
            out.append(([to_world(v) for v in verts], color,
                        (right[0] * n[0] + up[0] * n[1] + fwd[0] * n[2],
                         right[1] * n[0] + up[1] * n[1] + fwd[1] * n[2],
                         right[2] * n[0] + up[2] * n[1] + fwd[2] * n[2])))
        return out
