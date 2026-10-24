"""Simplified flight model: thrust, drag, gravity, lagged controls, coordinated turns."""
import math

from . import config as cfg
from .aircraft import AIRCRAFT
from .vec import add, euler_basis, scale

GRAVITY = 9.81


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Plane:
    def __init__(self):
        self.spec = AIRCRAFT[0]
        self.reset()

    def set_spec(self, spec):
        """Swap aircraft type in flight, keeping position and attitude."""
        self.spec = spec
        self.wing_lost = None             # a new aircraft has both wings
        self.speed = _clamp(self.speed, 0.0, spec.max_speed * 1.5)
        self.pitch = _clamp(self.pitch, -spec.max_pitch, spec.max_pitch)
        self.roll = _clamp(self.roll, -spec.max_roll, spec.max_roll)

    def reset(self):
        self.pos = cfg.START_POSITION
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.speed = self.spec.start_speed
        self.throttle = 0.5
        self.stalled = False
        self.vertical_speed = 0.0
        self.prop_angle = 0.0
        self.brake = 0.0
        self.on_ground = False
        self.wing_lost = None       # None, "left" or "right"
        self.gear_down = False      # selected position
        self.gear = 0.0             # actual position: 0 up .. 1 down
        self._pitch_cmd = 0.0
        self._roll_cmd = 0.0

    def reset_at(self, pos, yaw):
        """Parked on the ground at `pos`, facing `yaw`, ready to taxi and take off."""
        self.reset()
        self.pos = (pos[0], self.spec.ground_clearance, pos[2])
        self.yaw = yaw
        self.speed = 0.0
        self.throttle = 0.0
        self.gear_down, self.gear = True, 1.0
        self.on_ground = True

    @property
    def gear_locked_down(self):
        return self.gear >= 1.0

    def toggle_gear(self):
        """Raise/lower the gear. Returns False if refused (can't retract on the ground)."""
        if self.on_ground and self.gear_down:
            return False
        self.gear_down = not self.gear_down
        return True

    @property
    def basis(self):
        return euler_basis(self.yaw, self.pitch, self.roll)

    @property
    def altitude(self):
        return self.pos[1]

    @property
    def heading_degrees(self):
        return math.degrees(self.yaw) % 360.0

    def update(self, dt, pitch_in, roll_in, throttle_in, brake_in=False):
        """pitch_in: +1 nose up. roll_in: +1 bank right. throttle_in: +1 more. brake_in: air brake held."""
        sp = self.spec
        self.throttle = _clamp(self.throttle + throttle_in * cfg.THROTTLE_RATE * dt, 0.0, 1.0)

        step = dt / cfg.GEAR_TIME
        self.gear = _clamp(self.gear + (step if self.gear_down else -step), 0.0, 1.0)

        # Air brake extends smoothly; it fades out near the stall so it can't cause one.
        target = 1.0 if brake_in else 0.0
        self.brake += _clamp(target - self.brake, -cfg.BRAKE_RATE * dt, cfg.BRAKE_RATE * dt)
        brake = self.brake * _clamp((self.speed - sp.stall_speed * 1.05) / (sp.stall_speed * 0.3), 0.0, 1.0)

        # Control surfaces lag the stick, and bite less in slow air.
        lag = min(1.0, cfg.CONTROL_LAG * dt)
        self._pitch_cmd += (pitch_in - self._pitch_cmd) * lag
        self._roll_cmd += (roll_in - self._roll_cmd) * lag
        authority = _clamp(self.speed / sp.control_speed, 0.25, 1.25)

        self.pitch += self._pitch_cmd * sp.pitch_rate * authority * dt
        # A banked wing loses vertical lift, so the nose sags in a turn.
        self.pitch -= sp.bank_nose_drop * (1.0 - math.cos(self.roll)) * dt
        self.pitch = _clamp(self.pitch, -sp.max_pitch, sp.max_pitch)
        if self.on_ground:                    # the nose only lifts once there is enough airspeed
            self.pitch = max(self.pitch, 0.0) if self.speed >= sp.rotate_speed else 0.0

        aileron = cfg.WING_LOSS_AILERON if self.wing_lost else 1.0
        self.roll = _clamp(self.roll + self._roll_cmd * sp.roll_rate * authority * aileron * dt,
                           -sp.max_roll, sp.max_roll)
        if self.wing_lost and not self.on_ground:
            # Lift is lost on the broken side, so the plane keeps rolling and turning toward it.
            side = -1.0 if self.wing_lost == "left" else 1.0
            self.roll = _clamp(self.roll + side * cfg.WING_LOSS_ROLL * dt, -sp.max_roll, sp.max_roll)
        elif roll_in == 0:                    # dihedral effect: wings level themselves
            self.roll -= self.roll * min(1.0, 0.35 * dt)

        if self.on_ground:                    # taxiing: steer with the nose wheel, wings stay level
            self.roll = 0.0
            self.yaw += roll_in * cfg.TAXI_TURN_RATE * min(self.speed / 8.0, 1.0) * dt
        else:
            # Coordinated turn: turn rate = g * tan(bank) / speed.
            turn = sp.turn_factor * GRAVITY * math.tan(self.roll) / max(self.speed, 20.0)
            self.yaw += _clamp(turn, -sp.max_turn_rate, sp.max_turn_rate) * dt

        # Speed: thrust - drag (grows with speed squared) - gravity along the flight path.
        thrust = sp.idle_thrust + self.throttle * (sp.max_thrust - sp.idle_thrust)
        if self.on_ground:
            thrust = self.throttle * sp.max_thrust
        drag = sp.drag * (1.0 + cfg.BRAKE_DRAG * brake + cfg.GEAR_DRAG * self.gear)
        accel = thrust - drag * self.speed ** 2 - GRAVITY * math.sin(self.pitch)
        # Pulling g in a steep bank adds induced drag.
        accel -= cfg.INDUCED_DRAG * (1.0 / max(math.cos(self.roll), 0.2) - 1.0)
        if self.on_ground:
            accel -= cfg.GROUND_FRICTION + (cfg.WHEEL_BRAKE if brake_in else 0.0)
        top = cfg.MAX_GROUND_SPEED if self.on_ground else sp.max_speed * 1.5
        self.speed = _clamp(self.speed + accel * dt, 0.0, top)

        self.prop_angle += (12.0 + 40.0 * self.throttle) * dt

        fwd, _, _ = self.basis
        x, y, z = add(self.pos, scale(fwd, self.speed * dt))

        # Stall: lose lift and the nose drops.
        self.stalled = self.speed < sp.stall_speed and not self.on_ground
        if self.stalled:
            y -= (sp.stall_speed - self.speed) * 0.6 * dt
            self.pitch = _clamp(self.pitch - 0.6 * dt, -sp.max_pitch, sp.max_pitch)

        if self.on_ground:
            if y > sp.ground_clearance + 0.05:
                self.on_ground = False        # wheels have left the ground
            else:
                y = sp.ground_clearance

        if self.wing_lost and not self.on_ground:
            y -= cfg.WING_LOSS_SINK * dt

        self.vertical_speed = (y - self.pos[1]) / dt if dt > 0 else 0.0
        self.pos = (x, y, z)

    def collision_points(self, pos=None):
        """(index, world position) of the points standing for the plane's body, and wheels if down.

        Indices count the body points first, then the wheel points. Points on a wing that has
        already broken off are skipped.
        """
        fwd, right, up = self.basis
        px, py, pz = self.pos if pos is None else pos
        sp = self.spec
        local = list(enumerate(sp.hit_points))
        if self.gear > 0.5:
            local += [(len(sp.hit_points) + i, p) for i, p in enumerate(sp.gear_hit_points)]
        out = []
        for i, (x, y, z) in local:
            if self.wing_lost and i < len(sp.hit_points) and sp.is_wing_point((x, y, z)) \
                    and sp.wing_side((x, y, z)) == self.wing_lost:
                continue
            out.append((i, (px + right[0] * x + up[0] * y + fwd[0] * z,
                            py + right[1] * x + up[1] * y + fwd[1] * z,
                            pz + right[2] * x + up[2] * y + fwd[2] * z)))
        return out

    def collision_result(self, indices):
        """What hitting something with these collision points means.

        Returns "crash", or ("wing", side) if only one wing's outer part touched and that wing is
        still on. Touching anything but a wing, or losing the second wing, is a crash.
        """
        sp, sides = self.spec, set()
        for i in indices:
            if i >= len(sp.hit_points) or not sp.is_wing_point(sp.hit_points[i]):
                return "crash"
            sides.add(sp.wing_side(sp.hit_points[i]))
        if len(sides) != 1 or self.wing_lost:
            return "crash"
        return ("wing", sides.pop())

    def lose_wing(self, side):
        """Break the wing off. Returns its polygons in world space (to fall away as wreckage)."""
        self.wing_lost = side
        return self._to_world(self.spec.lost_wing_polys[side])

    def _to_world(self, polys):
        fwd, right, up = self.basis
        px, py, pz = self.pos

        def to_world(p):
            return (px + right[0] * p[0] + up[0] * p[1] + fwd[0] * p[2],
                    py + right[1] * p[0] + up[1] * p[1] + fwd[1] * p[2],
                    pz + right[2] * p[0] + up[2] * p[1] + fwd[2] * p[2])

        return [([to_world(v) for v in verts], color,
                 None if n is None else
                 (right[0] * n[0] + up[0] * n[1] + fwd[0] * n[2],
                  right[1] * n[0] + up[1] * n[1] + fwd[1] * n[2],
                  right[2] * n[0] + up[2] * n[1] + fwd[2] * n[2])) for verts, color, n in polys]

    def world_polys(self, flame=True):
        """The plane's mesh transformed into world space."""
        body, gear = self.spec.parts(self.wing_lost)
        mesh = body + (gear if self.gear > 0.5 else [])
        mesh = mesh + self.spec.prop_polys(self.prop_angle)
        if flame:
            mesh = mesh + self.spec.flame_polys(self.throttle, self.prop_angle)
        return self._to_world(mesh)
