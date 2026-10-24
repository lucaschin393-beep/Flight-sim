"""Airplane simulator: fly with W/A/S/D, switch 1st/3rd person with P."""
import sys

import pygame

from sim import config as cfg
from sim.camera import FIRST_PERSON, VIEWS, Camera
from sim.hud import Hud
from sim.plane import Plane
from sim.renderer import Renderer
from sim.world import World, on_runway

GROUND_CLEARANCE = 1.0


def landing_status(plane):
    """Called when the plane reaches the ground: ('Landed!' | 'Crashed!', colour)."""
    gentle = (plane.speed < 55 and abs(plane.pitch) < 0.2 and abs(plane.roll) < 0.2
              and plane.vertical_speed > -6)
    if on_runway(plane.pos) and gentle:
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
    world, plane = World(), Plane()
    view_index, status = 0, None

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
                elif event.key == pygame.K_h:
                    hud.show_help = not hud.show_help
                elif event.key == pygame.K_r:
                    plane.reset()
                    camera.snap_next_update()
                    status = None

        if status is None:
            keys = pygame.key.get_pressed()
            pitch_in = (keys[pygame.K_s] - keys[pygame.K_w]) * (-1 if cfg.INVERT_PITCH else 1)
            roll_in = keys[pygame.K_d] - keys[pygame.K_a]
            throttle_in = ((keys[pygame.K_LSHIFT] or keys[pygame.K_UP])
                           - (keys[pygame.K_LCTRL] or keys[pygame.K_DOWN]))
            plane.update(dt, pitch_in, roll_in, throttle_in)

            if plane.altitude <= GROUND_CLEARANCE:
                status = landing_status(plane)
                if status[0] != "CRASHED!":
                    plane.pos = (plane.pos[0], GROUND_CLEARANCE, plane.pos[2])
            elif world.hits_obstacle(plane.pos):
                status = ("CRASHED!", (255, 90, 80))

        view = VIEWS[view_index]
        camera.follow(plane, view, dt)
        renderer.render(screen, camera, world, plane, draw_plane=(view != FIRST_PERSON))
        if view == FIRST_PERSON:
            hud.cockpit(screen)
        hud.draw(screen, plane, view, status)
        pygame.display.flip()


if __name__ == "__main__":
    main()
    pygame.quit()
    sys.exit()
