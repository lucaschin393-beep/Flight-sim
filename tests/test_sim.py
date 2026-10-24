"""Logic tests that need no display (run: python -m unittest discover -s tests)."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sim import config as cfg  # noqa: E402
from sim.aircraft import AIRCRAFT  # noqa: E402
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


class BrakeTests(unittest.TestCase):
    def test_air_brake_slows_faster_without_stalling(self):
        free, braked = Plane(), Plane()
        for p, b in ((free, False), (braked, True)):
            for _ in range(60 * 6):
                p.update(1 / 60.0, 0, 0, -1, b)
        self.assertLess(braked.speed, free.speed - 5)
        fly_on = Plane()
        for _ in range(60 * 60):
            fly_on.update(1 / 60.0, 0, 0, -1, True)
        self.assertGreater(fly_on.speed, cfg.STALL_SPEED)


class GearTests(unittest.TestCase):
    def test_gear_takes_time_and_unlocks_landing(self):
        p = Plane()
        self.assertFalse(p.gear_locked_down)
        p.toggle_gear()
        fly(p, 0.5)
        self.assertFalse(p.gear_locked_down)
        fly(p, 2.0)
        self.assertTrue(p.gear_locked_down)
        self.assertGreater(len(p.world_polys()), 0)
        p.toggle_gear()
        fly(p, 2.5)
        self.assertEqual(p.gear, 0.0)


class GroundTests(unittest.TestCase):
    def test_restart_on_ground_then_take_off(self):
        p = Plane()
        p.reset_at((100.0, 0.0, 200.0), 1.0)
        self.assertTrue(p.on_ground)
        self.assertEqual((p.pos[0], p.pos[2], p.yaw, p.speed), (100.0, 200.0, 1.0, 0.0))
        fly(p, 3)                                    # idle: stays parked
        self.assertEqual(p.speed, 0.0)
        for _ in range(60 * 30):
            p.update(1 / 60.0, 1 if p.speed > p.spec.rotate_speed else 0, 0, 1)
            if not p.on_ground:
                break
        self.assertFalse(p.on_ground)
        self.assertFalse(p.stalled)

    def test_gear_cannot_be_raised_while_on_ground(self):
        p = Plane()
        p.reset_at((0.0, 0.0, 0.0), 0.0)
        self.assertFalse(p.toggle_gear())
        fly(p, 3)
        self.assertTrue(p.gear_locked_down)

    def test_ground_speed_is_capped_at_300_kmh(self):
        p = Plane()
        p.reset_at((0.0, 0.0, 0.0), 0.0)
        fly(p, 60, throttle=1)               # never pulls up, so stays on the ground
        self.assertTrue(p.on_ground)
        self.assertLessEqual(p.speed * 3.6, 300.0 + 1e-6)

    def test_cannot_rotate_below_rotate_speed(self):
        p = Plane()
        p.reset_at((0.0, 0.0, 0.0), 0.0)
        fly(p, 2, pitch=1, throttle=0)
        self.assertEqual(p.pitch, 0.0)
        self.assertTrue(p.on_ground)


class CollisionTests(unittest.TestCase):
    def _tree(self, world):
        return next(o for o in world.nearby_objects((0, 0, 0))
                    if o.hit and o.polys and len(o.polys) == 4 and o.radius < 30)

    def test_wingtip_touching_a_tree_crashes(self):
        w, p = World(), Plane()
        tree = self._tree(w)
        x, _, z = tree.center
        p.yaw = p.pitch = p.roll = 0.0
        tip = max(p.spec.hit_points, key=lambda q: q[0])          # right wingtip, plane-local
        self.assertGreater(tip[0], 4.0)
        p.pos = (x - tip[0], 6.0 - tip[1], z - tip[2])
        self.assertTrue(w.hits_plane(p))
        p.pos = (x - tip[0] - 40.0, 6.0, z - tip[2])               # well clear
        self.assertFalse(w.hits_plane(p))

    def test_fast_plane_cannot_skip_through_a_tree(self):
        w, p = World(), Plane()
        x, _, z = self._tree(w).center
        p.set_spec(AIRCRAFT[2])
        p.pos = (x, 5.0, z - 1.0)
        prev = (x, 5.0, z - 5.0)
        self.assertTrue(w.hits_plane(p, prev))

    def test_open_air_is_clear(self):
        self.assertFalse(World().hits_plane(Plane()))


class WingLossTests(unittest.TestCase):
    def _plane(self):
        p = Plane()
        p.yaw = p.pitch = p.roll = 0.0
        return p

    def test_wing_points_are_classified_by_side(self):
        sp = AIRCRAFT[0]
        wing = [i for i, q in enumerate(sp.hit_points) if sp.is_wing_point(q)]
        self.assertTrue(wing)
        self.assertEqual({sp.wing_side(sp.hit_points[i]) for i in wing}, {"left", "right"})
        p = self._plane()
        right = [i for i in wing if sp.wing_side(sp.hit_points[i]) == "right"]
        left = [i for i in wing if sp.wing_side(sp.hit_points[i]) == "left"]
        self.assertEqual(p.collision_result(right), ("wing", "right"))
        self.assertEqual(p.collision_result(left + right), "crash")             # both wings at once
        fuselage = next(i for i, q in enumerate(sp.hit_points) if not sp.is_wing_point(q))
        self.assertEqual(p.collision_result([fuselage]), "crash")
        self.assertEqual(p.collision_result(right + [fuselage]), "crash")

    def test_wing_comes_off_then_second_wing_or_repeat_is_a_crash(self):
        sp = AIRCRAFT[0]
        p = self._plane()
        before = len(p.world_polys())
        gone = p.lose_wing("left")
        self.assertGreater(len(gone), 5)
        self.assertEqual(len(p.world_polys()), before - len(gone))
        self.assertTrue(all(v[0] < 0 for verts, _, _ in gone for v in verts[:1]))   # left of the plane
        left = [i for i, q in enumerate(sp.hit_points) if sp.is_wing_point(q) and sp.wing_side(q) == "left"]
        live = {i for i, _ in p.collision_points()}
        self.assertFalse(set(left) & live)                       # the missing wing can't hit anything
        right = [i for i, q in enumerate(sp.hit_points) if sp.is_wing_point(q) and sp.wing_side(q) == "right"]
        self.assertEqual(p.collision_result(right), "crash")     # losing the other one is fatal

    def test_plane_keeps_turning_toward_the_missing_wing(self):
        for side, sign in (("left", -1), ("right", 1)):
            p = self._plane()
            p.lose_wing(side)
            start = p.yaw
            fly(p, 4)                                             # hands off
            self.assertGreater(p.roll * sign, 0.8, side)
            self.assertGreater((p.yaw - start) * sign, 0.3, side)
            self.assertGreater(p.speed, 0)                        # still flying

    def test_a_clipped_wingtip_in_the_world_breaks_the_wing(self):
        w, p = World(), self._plane()
        tree = next(o for o in w.nearby_objects((0, 0, 0))
                    if o.hit and o.polys and len(o.polys) == 4 and o.radius < 30)
        sp = p.spec
        tip = max(sp.hit_points, key=lambda q: q[0])
        x, _, z = tree.center
        p.pos = (x - tip[0], 6.0 - tip[1], z - tip[2])
        hits = w.hit_indices(p)
        self.assertTrue(hits)
        self.assertEqual(p.collision_result(hits), ("wing", "right"))


class ExplosionTests(unittest.TestCase):
    def test_explosion_spawns_debris_burns_then_finishes(self):
        import random
        from sim.explosion import Explosion
        ex = Explosion((0, 0, 0), (0, 0, 50), 1.0, random.Random(1))
        self.assertGreater(len(ex.particles), 100)
        self.assertTrue(all(p.pos[1] >= 0 for p in ex.particles))
        for _ in range(60 * 40):
            ex.update(1 / 60.0)
        self.assertTrue(ex.done)
        self.assertEqual(ex.particles, [])

    def test_plane_breaks_into_pieces_that_land_and_stay(self):
        import random
        from sim.explosion import Explosion
        p = Plane()
        p.pos = (0.0, 30.0, 0.0)
        polys = p.world_polys()
        ex = Explosion(p.pos, (0, 0, 60), 1.0, random.Random(2), polys=polys, intensity=1.0)
        self.assertGreaterEqual(len(ex.pieces), 8)
        self.assertEqual(sum(len(pc.rel) for pc in ex.pieces), len(polys))   # nothing lost
        for _ in range(60 * 15):
            ex.update(1 / 60.0)
        self.assertTrue(all(pc.resting for pc in ex.pieces))
        for verts, _, _ in ex.wreckage_polys():
            self.assertTrue(all(v[1] > -0.01 for v in verts))              # nothing under ground
        self.assertGreater(len(ex.ground_decals()), 0)


class FlameTests(unittest.TestCase):
    def test_only_the_jet_has_a_flame_and_it_grows_with_throttle(self):
        jet, trainer = AIRCRAFT[2], AIRCRAFT[0]
        self.assertEqual(trainer.flame_polys(1.0, 0.0), [])
        self.assertEqual(jet.flame_polys(0.1, 0.0), [])             # idle: no flame
        def tail(throttle):
            return min(v[2] for verts, _, _ in jet.flame_polys(throttle, 0.0) for v in verts)
        self.assertLess(tail(1.0), tail(0.6) - 1.0)                  # longer plume at full power
        self.assertLess(tail(0.6), -5.25)                            # extends behind the nozzle


class SoundTests(unittest.TestCase):
    def test_generated_waveforms(self):
        import random
        from sim import sound
        boom = sound.make_boom(random.Random(1), seconds=1.0)
        fire = sound.make_fire(random.Random(1), seconds=1.0)
        self.assertEqual(len(boom), sound.RATE)
        self.assertEqual(len(fire), sound.RATE)
        loud = max(abs(x) for x in boom[:2000])
        tail = max(abs(x) for x in boom[-500:])
        self.assertGreater(loud, 10 * tail)                       # a bang that dies away
        self.assertGreater(max(abs(x) for x in fire), 0.3)
        jet = sound.make_jet(random.Random(1), seconds=1.0)
        self.assertEqual(len(jet), sound.RATE)
        self.assertGreater(max(abs(x) for x in jet), 0.3)

    def test_every_aircraft_has_an_engine_sound_with_seamless_loops(self):
        import random
        from sim import sound
        for spec in AIRCRAFT:
            prof = sound.ENGINES[spec.engine]
            self.assertEqual(len(prof["layers"]), 3, spec.name)
            for params in prof["layers"]:
                loop = sound.make_engine_layer(random.Random(1), prof["kind"], params)
                self.assertEqual(len(loop), sound.RATE)
                step = max(abs(loop[i + 1] - loop[i]) for i in range(0, 2000))
                self.assertLess(abs(loop[0] - loop[-1]), 3 * max(step, 0.05), spec.name)  # no seam click
                self.assertGreater(max(abs(x) for x in loop), 0.1)

    def test_no_engine_has_a_whine(self):
        from sim import sound
        for name, prof in sound.ENGINES.items():
            if prof["kind"] == "turbine":
                self.assertTrue(all(layer["whine"] == 0 for layer in prof["layers"]), name)
        self.assertFalse(hasattr(sound, "make_squeal"))
        for method in ("wing_snap", "touchdown", "gear", "wheels", "crash", "engine", "afterburner"):
            self.assertTrue(hasattr(sound.Sounds, method), method)       # nothing lost in edits

    def test_gear_and_wheel_effects_exist(self):
        import random
        from sim import sound
        for make in (sound.make_thunk, sound.make_gear_motor, sound.make_roll,
                     sound.make_touchdown, sound.make_snap):
            wave = make(random.Random(1))
            self.assertGreater(len(wave), 1000, make.__name__)
            self.assertGreater(max(abs(x) for x in wave), 0.1, make.__name__)
        for make in (sound.make_gear_motor, sound.make_roll):   # loops
            wave = make(random.Random(1))
            self.assertEqual(len(wave), sound.RATE)
            self.assertLess(abs(wave[0] - wave[-1]), 0.5, make.__name__)

    def test_only_the_jet_has_afterburner_power(self):
        self.assertEqual(AIRCRAFT[0].exhaust_power(1.0), 0.0)
        self.assertEqual(AIRCRAFT[2].exhaust_power(0.2), 0.0)
        self.assertAlmostEqual(AIRCRAFT[2].exhaust_power(1.0), 1.0)


class AircraftTests(unittest.TestCase):
    def test_every_aircraft_flies_level_and_has_geometry(self):
        for spec in AIRCRAFT:
            p = Plane()
            p.set_spec(spec)
            p.reset()
            fly(p, 2)
            self.assertAlmostEqual(p.altitude, cfg.START_POSITION[1], delta=1.0, msg=spec.name)
            self.assertGreater(len(p.world_polys()), 50, spec.name)

    def test_jet_outruns_biplane(self):
        speeds = {}
        for spec in AIRCRAFT:
            p = Plane()
            p.set_spec(spec)
            fly(p, 40, throttle=1)
            speeds[spec.name] = p.speed
        self.assertGreater(speeds["Falcon jet"], 2 * speeds["Barnstormer biplane"])

    def test_switching_keeps_position(self):
        p = Plane()
        fly(p, 1)
        pos = p.pos
        p.set_spec(AIRCRAFT[2])
        self.assertEqual(p.pos, pos)


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
