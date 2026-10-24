"""Logic tests that need no display (run: python -m unittest discover -s tests)."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sim import config as cfg  # noqa: E402
from sim.camera import Camera, FIRST_PERSON, THIRD_PERSON  # noqa: E402
from sim.plane import Plane  # noqa: E402
from sim.vec import cross, dot, euler_basis, length  # noqa: E402
from sim.world import World  # noqa: E402


def fly(plane, seconds, pitch=0, roll=0, throttle=0, dt=1 / 60.0):
    for _ in range(int(seconds / dt)):
        plane.update(dt, pitch, roll, throttle)


class VectorTests(unittest.TestCase):
    def test_basis_is_orthonormal_and_right_handed_for_camera(self):
        for yaw, pitch, roll in [(0, 0, 0), (1.0, 0.4, -0.7), (-2.0, -0.9, 1.2)]:
            f, r, u = euler_basis(yaw, pitch, roll)
            for v in (f, r, u):
                self.assertAlmostEqual(length(v), 1.0, places=6)
            self.assertAlmostEqual(dot(f, r), 0.0, places=6)
            self.assertAlmostEqual(dot(f, u), 0.0, places=6)
            for a, b in zip(cross(u, f), r):          # right = up x forward
                self.assertAlmostEqual(a, b, places=6)

    def test_bank_right_drops_right_wing(self):
        _, right, _ = euler_basis(0, 0, 0.5)
        self.assertLess(right[1], 0)


class PlaneTests(unittest.TestCase):
    def test_level_flight_holds_altitude(self):
        p = Plane()
        fly(p, 3)
        self.assertAlmostEqual(p.altitude, cfg.START_POSITION[1], delta=1.0)
        self.assertGreater(p.pos[2], cfg.START_POSITION[2] + 100)    # moved forward

    def test_nose_up_climbs_and_nose_down_descends(self):
        up, down = Plane(), Plane()
        fly(up, 2, pitch=1)
        fly(down, 2, pitch=-1)
        self.assertGreater(up.altitude, cfg.START_POSITION[1] + 20)
        self.assertLess(down.altitude, cfg.START_POSITION[1] - 20)

    def test_banking_right_turns_right(self):
        p = Plane()
        fly(p, 1, roll=1)
        yaw_before = p.yaw
        fly(p, 2)
        self.assertGreater(p.yaw, yaw_before)
        self.assertGreater(p.heading_degrees, 0)

    def test_steep_climb_stalls_then_nose_drops(self):
        p = Plane()
        stalled_at_pitch = None
        for _ in range(60 * 30):
            p.update(1 / 60.0, 1, 0, 0)
            if p.stalled and stalled_at_pitch is None:
                stalled_at_pitch = p.pitch
        self.assertIsNotNone(stalled_at_pitch, "holding full nose-up should stall")
        # once stalled the nose is forced down even while still pulling up
        self.assertLess(p.pitch, cfg.MAX_PITCH)

    def test_throttle_changes_speed(self):
        slow, fast = Plane(), Plane()
        fly(slow, 15, throttle=-1)
        fly(fast, 15, throttle=1)
        self.assertLess(slow.speed, fast.speed)
        self.assertEqual(fast.throttle, 1.0)
        self.assertEqual(slow.throttle, 0.0)

    def test_reset_restores_start(self):
        p = Plane()
        fly(p, 2, pitch=1, roll=1)
        p.reset()
        self.assertEqual(p.pos, cfg.START_POSITION)
        self.assertEqual((p.yaw, p.pitch, p.roll), (0, 0, 0))


class CameraTests(unittest.TestCase):
    def test_point_ahead_projects_to_screen_centre(self):
        cam = Camera(1000, 600)
        cam.set_basis((0, 0, 0), (0, 0, 1), (0, 1, 0))
        pc = cam.to_camera((0, 0, 50))
        self.assertEqual(cam.project(pc), (500.0, 300.0))

    def test_right_is_screen_right_and_up_is_screen_up(self):
        cam = Camera(1000, 600)
        cam.set_basis((0, 0, 0), (0, 0, 1), (0, 1, 0))
        x, y = cam.project(cam.to_camera((10, 10, 50)))
        self.assertGreater(x, 500)
        self.assertLess(y, 300)

    def test_first_person_looks_where_plane_points(self):
        cam, p = Camera(1000, 600), Plane()
        cam.follow(p, FIRST_PERSON, 1 / 60.0)
        for a, b in zip(cam.fwd, p.basis[0]):
            self.assertAlmostEqual(a, b, places=6)

    def test_third_person_sits_behind_and_above(self):
        cam, p = Camera(1000, 600), Plane()
        cam.follow(p, THIRD_PERSON, 1 / 60.0)
        self.assertLess(cam.pos[2], p.pos[2] - 10)
        self.assertGreater(cam.pos[1], p.pos[1])


class WorldTests(unittest.TestCase):
    def test_generation_is_deterministic(self):
        a = list(World(seed=3).nearby_objects((100, 50, 100)))
        b = list(World(seed=3).nearby_objects((100, 50, 100)))
        self.assertEqual(len(a), len(b))
        self.assertEqual(a[0].center, b[0].center)

    def test_runway_is_clear_of_obstacles(self):
        w = World()
        for z in range(-800, 801, 50):
            self.assertFalse(w.hits_obstacle((0.0, 5.0, float(z))))

    def test_building_collision(self):
        w = World()
        obj = next(o for o in w.nearby_objects((0, 0, 0)) if o.hit and o.polys and len(o.polys) == 6)
        cx, cy, cz = obj.center
        self.assertTrue(obj.hit((cx, 1.0, cz)))
        self.assertFalse(obj.hit((cx, cy * 2 + 50, cz)))


if __name__ == "__main__":
    unittest.main()
