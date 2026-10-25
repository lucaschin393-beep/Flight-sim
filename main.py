"""Airplane simulator: fly with W/A/S/D, switch 1st/3rd person with P."""
import random
import sys

import pygame

from sim import config as cfg
from sim.aircraft import AIRCRAFT
from sim.camera import FIRST_PERSON, VIEWS, Camera
from sim.explosion import LINGER, SMOULDER, Explosion, Piece
from sim.hud import Hud
from sim.maps import MAPS
from sim.sound import Sounds
from sim.plane import Plane
from sim.renderer import Renderer
from sim.world import World

def landing_status(plane):
    """Called when the plane reaches the ground: ('Landed!' | 'Crashed!', colour)."""
    gentle = (plane.speed < plane.spec.land_speed
              and abs(plane.pitch) < cfg.LAND_MAX_ATTITUDE and abs(plane.roll) < cfg.LAND_MAX_ATTITUDE
              and plane.vertical_speed > -cfg.LAND_MAX_SINK)
    if not plane.gear_locked_down:
        return ("CRASHED - landing gear not down!", (255, 90, 80))
    if gentle:
        return ("Landed safely!", (120, 230, 140))
    return ("CRASHED!", (255, 90, 80))


def main():
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Airplane Simulator")
    screen = pygame.display.set_mode(cfg.WINDOW_SIZE)
    clock = pygame.time.Clock()

    width, height = cfg.WINDOW_SIZE
    camera, renderer, hud = Camera(width, height), Renderer(width, height), Hud(width, height)
    map_index = 0
    world, plane = World(game_map=MAPS[map_index]), Plane()
    renderer.set_map(world.map)
    view_index, status, paused = 0, None, False
    crash_in_water = False
    sounds = Sounds()
    explosion = None
    wing_pieces = []          # broken-off wings tumbling to the ground
    landed_at = None          # (position, heading) of the last safe landing

    def switch_map(index):
        """Load another map and start again at its runway (the aircraft type is kept)."""
        nonlocal map_index, world, status, paused, explosion, wing_pieces, landed_at, crash_in_water
        map_index = index % len(MAPS)
        world = World(game_map=MAPS[map_index])
        renderer.set_map(world.map)
        plane.reset()
        camera.snap_next_update()
        status, paused, explosion, wing_pieces = None, False, None, []
        landed_at, crash_in_water = None, False
        sounds.stop()
        hud.notify("Map: %s" % world.map.name)

    while True:
        dt = min(clock.tick(cfg.FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_p:
                    view_index = (view_index + 1) % len(VIEWS)
                    camera.snap_next_update()
                elif event.key in (pygame.K_SPACE, pygame.K_PAUSE):
                    paused = not paused
                    sounds.pause(paused)
                elif event.key == pygame.K_c or pygame.K_1 <= event.key < pygame.K_1 + len(AIRCRAFT):
                    if status is None:
                        i = (AIRCRAFT.index(plane.spec) + 1) % len(AIRCRAFT) if event.key == pygame.K_c \
                            else event.key - pygame.K_1
                        plane.set_spec(AIRCRAFT[i])
                        camera.snap_next_update()
                elif event.key == pygame.K_n:
                    switch_map(map_index + 1)
                elif pygame.K_F1 <= event.key < pygame.K_F1 + len(MAPS):
                    switch_map(event.key - pygame.K_F1)
                elif event.key == pygame.K_g:
                    if status is None:
                        if not plane.toggle_gear():
                            hud.notify("Can't raise the landing gear on the ground")
                elif event.key == pygame.K_m:
                    hud.notify("Sound off" if sounds.toggle_mute() else "Sound on")
                elif event.key == pygame.K_h:
                    hud.show_help = not hud.show_help
                elif event.key == pygame.K_r:
                    if landed_at and status and status[0].startswith("Landed"):
                        plane.reset_at(*landed_at)         # carry on from where you touched down
                    else:
                        plane.reset()
                    camera.snap_next_update()
                    status = None
                    explosion = None
                    wing_pieces = []
                    crash_in_water = False
                    sounds.stop()
                    paused = False

        if status is None and not paused:
            keys = pygame.key.get_pressed()
            pitch_in = (keys[pygame.K_s] - keys[pygame.K_w]) * (-1 if cfg.INVERT_PITCH else 1)
            roll_in = keys[pygame.K_d] - keys[pygame.K_a]
            throttle_in = ((keys[pygame.K_LSHIFT] or keys[pygame.K_UP])
                           - (keys[pygame.K_LCTRL] or keys[pygame.K_DOWN]))
            prev_pos = plane.pos
            plane.update(dt, pitch_in, roll_in, throttle_in, keys[pygame.K_b])

            hits = world.hit_indices(plane, prev_pos)
            outcome = plane.collision_result(hits) if hits else None
            if outcome and outcome != "crash":                 # clipped a wing: it breaks off
                side = outcome[1]
                velocity = tuple(c * plane.speed for c in plane.basis[0])
                broken = Piece(plane.lose_wing(side), plane.pos, velocity, random.Random(), 0.35,
                               0.9, drag=1.0, burn=False, water_at=world.water_at)
                broken.spin = tuple(c * 2.0 for c in broken.spin)
                wing_pieces.append(broken)
                sounds.wing_snap()
                outcome = None
            in_water = world.water_at(plane.pos[0], plane.pos[2])
            touching = plane.on_ground or plane.altitude <= plane.spec.ground_clearance
            if outcome == "crash":
                status = ("CRASHED!", (255, 90, 80))
            elif in_water and touching:
                status, crash_in_water = ("CRASHED - hit the water!", (255, 90, 80)), True
            elif not plane.on_ground and plane.altitude <= plane.spec.ground_clearance:
                status = landing_status(plane)
                if not status[0].startswith("CRASHED"):
                    plane.pos = (plane.pos[0], plane.spec.ground_clearance, plane.pos[2])
                    landed_at = (plane.pos, plane.yaw)
                    sounds.touchdown(-plane.vertical_speed)

        if explosion is None and status and status[0].startswith("CRASHED"):
            fwd = plane.basis[0]
            explosion = Explosion(plane.pos, tuple(c * plane.speed for c in fwd),
                                  plane.spec.bounding_radius / 5.5, polys=plane.world_polys(flame=False),
                                  intensity=max(0.35, min(1.3, plane.speed / 60.0)),
                                  water=crash_in_water, water_at=world.water_at,
                                  water_color=world.map.shallow)
            sounds.crash(plane.speed / 60.0, water=crash_in_water)
            view_index = 0                    # watch it from outside, in 3rd person
            camera.snap_next_update()
        if not paused:
            for piece in wing_pieces:
                piece.update(dt)
        if explosion and not paused:
            explosion.update(dt)
            # fire roars while the wreck burns hard, then dies down as it smoulders
            ramp_in = min(explosion.age / 0.6, 1.0)
            burn_down = 1.0 if explosion.age < LINGER else max(0.0, (SMOULDER - explosion.age) / (SMOULDER - LINGER))
            sounds.fire_level(ramp_in * (0.25 + 0.75 * burn_down))

        quiet = paused or status is not None
        sounds.engine(plane.spec.engine, plane.throttle, dt, quiet)
        sounds.gear(plane.gear, dt, quiet)
        sounds.wheels(plane.wheels_rolling, plane.speed, dt, quiet)
        sounds.afterburner(0.0 if quiet else plane.spec.exhaust_power(plane.throttle), dt)

        view = VIEWS[view_index]
        camera.follow(plane, view, 0.0 if paused else dt)
        true_pos = camera.pos
        if explosion and not paused:          # jolt the view with the blast
            camera.pos = tuple(c + o for c, o in zip(true_pos, explosion.camera_shake()))
        renderer.time = pygame.time.get_ticks() / 1000.0
        renderer.render(screen, camera, world, plane, draw_plane=(view != FIRST_PERSON),
                        wrecked=explosion is not None,
                        extra_decals=explosion.ground_decals() if explosion else (),
                        extra_polys=(explosion.wreckage_polys() if explosion else [])
                        + [poly for piece in wing_pieces for poly in piece.polys()])
        camera.pos = true_pos
        if explosion:
            explosion.draw(screen, camera)
            explosion.draw_flash(screen)
        if view == FIRST_PERSON:
            hud.cockpit(screen)
        hud.draw(screen, plane, view, status, world.map.name)
        if paused:
            hud.paused(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
    pygame.quit()
    sys.exit()
