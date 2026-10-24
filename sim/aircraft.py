"""The selectable aircraft: handling numbers, mesh and camera settings for each."""
import math
from functools import partial

from . import config as cfg
from . import meshes


def _sample_points(polys, count):
    """`count` well-spread vertices of a mesh (farthest-point sampling) to stand for its shape."""
    pool = list({tuple(round(c, 1) for c in v) for verts, _, _ in polys for v in verts})
    if not pool:
        return []
    chosen = [max(pool, key=lambda v: math.hypot(*v))]
    nearest = [math.dist(v, chosen[0]) for v in pool]
    while len(chosen) < min(count, len(pool)):
        i = max(range(len(pool)), key=nearest.__getitem__)
        chosen.append(pool[i])
        nearest = [min(d, math.dist(v, pool[i])) for d, v in zip(nearest, pool)]
    return chosen


class Aircraft:
    """Handling and look of one plane type. Unset numbers fall back to sim/config.py."""

    def __init__(self, name, mesh, propeller=None, *, min_speed, max_speed, stall_speed, drag,
                 land_speed, ground_clearance=1.0, chase_distance=20.0, chase_height=6.0,
                 eye=(0.9, 2.2), exhaust=None, engine="prop", pitch_rate=cfg.PITCH_RATE, roll_rate=cfg.ROLL_RATE,
                 control_speed=cfg.CONTROL_SPEED, bank_nose_drop=cfg.BANK_NOSE_DROP,
                 turn_factor=cfg.TURN_FACTOR, max_turn_rate=cfg.MAX_TURN_RATE,
                 max_pitch=cfg.MAX_PITCH, max_roll=cfg.MAX_ROLL):
        self.name, (self.mesh, self.gear_mesh), self.propeller = name, mesh, propeller
        self.min_speed, self.max_speed, self.stall_speed = min_speed, max_speed, stall_speed
        self.drag, self.land_speed = drag, land_speed
        self.engine = engine          # key into sim.sound.ENGINES
        self.exhaust = exhaust        # (z, y, radius) of a jet nozzle that shows a flame
        self.ground_clearance = ground_clearance
        self.chase_distance, self.chase_height, self.eye = chase_distance, chase_height, eye
        self.pitch_rate, self.roll_rate, self.control_speed = pitch_rate, roll_rate, control_speed
        self.bank_nose_drop, self.turn_factor = bank_nose_drop, turn_factor
        self.max_turn_rate, self.max_pitch, self.max_roll = max_turn_rate, max_pitch, max_roll
        # Thrust is chosen so level flight settles at min_speed (idle) / max_speed (full throttle).
        self.idle_thrust = drag * min_speed ** 2
        self.max_thrust = drag * max_speed ** 2
        self.start_speed = (min_speed + max_speed) / 2.0
        # Points that stand for the plane's body (incl. propeller) and its wheels, for collisions.
        spinning = self.prop_polys(0.0) + self.prop_polys(math.pi / 2)
        self.hit_points = _sample_points(self.mesh + spinning, 40)
        self.gear_hit_points = _sample_points(self.gear_mesh, 12)
        self.bounding_radius = max(math.hypot(*p) for p in self.hit_points + self.gear_hit_points)

    @property
    def rotate_speed(self):
        """Speed at which the nose can be raised to leave the ground."""
        return self.stall_speed * 1.1

    def exhaust_power(self, throttle):
        """0..1 strength of the afterburner (flame and roar); 0 for aircraft without one."""
        return max(0.0, (throttle - 0.3) / 0.7) if self.exhaust else 0.0

    def flame_polys(self, throttle, t):
        return meshes.exhaust_flame(throttle, t, *self.exhaust) if self.exhaust else []

    def prop_polys(self, angle):
        return self.propeller(angle) if self.propeller else []


AIRCRAFT = [
    Aircraft("Skylark trainer", meshes.trainer_mesh(), meshes.propeller,
             min_speed=cfg.MIN_SPEED, max_speed=cfg.MAX_SPEED, stall_speed=cfg.STALL_SPEED,
             drag=cfg.DRAG, land_speed=55.0),
    Aircraft("Barnstormer biplane", meshes.biplane_mesh(), partial(meshes.propeller, z=3.4, length=1.1),
             engine="radial",
             min_speed=22.0, max_speed=70.0, stall_speed=18.0, drag=0.0007, land_speed=40.0,
             eye=(1.0, 1.2), pitch_rate=1.0, roll_rate=2.0, control_speed=40.0,
             turn_factor=2.4, max_turn_rate=1.1),
    Aircraft("Falcon jet", meshes.jet_mesh(),
             min_speed=45.0, max_speed=220.0, stall_speed=40.0, drag=0.00025, land_speed=70.0,
             exhaust=(-5.25, 0.05, 0.42), engine="jet", ground_clearance=1.2, chase_distance=28.0, chase_height=7.0, eye=(0.9, 2.6),
             pitch_rate=1.0, roll_rate=3.0, control_speed=90.0, turn_factor=1.8,
             max_turn_rate=1.0, max_roll=1.5),
    Aircraft("Atlas airliner", meshes.airliner_mesh(), engine="airliner",
             min_speed=50.0, max_speed=140.0, stall_speed=40.0, drag=0.0003, land_speed=62.0,
             ground_clearance=3.4, chase_distance=60.0, chase_height=16.0, eye=(2.2, 14.0),
             pitch_rate=0.45, roll_rate=0.7, control_speed=80.0, bank_nose_drop=0.3,
             turn_factor=1.0, max_turn_rate=0.35, max_pitch=0.6, max_roll=0.9),
]
