"""On-screen display: flight data, throttle, help and the cockpit frame."""
import pygame

from . import config as cfg

INK = (255, 255, 255)
GOOD, WARN = (120, 230, 140), (255, 190, 60)
SHADOW = (20, 28, 40)

HELP = [
    "W / S   nose down / up",
    "A / D   bank left / right",
    "Shift / Ctrl   throttle up / down",
    "G   landing gear up / down",
    "B (hold)   air brake - slows you down",
    "C or 1-4   change aircraft",
    "Space   pause / resume",
    "P   change view      R   restart",
    "M   mute sound       H   hide help",
    "Esc   quit",
]


class Hud:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.font = pygame.font.Font(None, 26)
        self.big = pygame.font.Font(None, 54)
        self.small = pygame.font.Font(None, 22)
        self.show_help = True
        self._notice, self._notice_until = "", 0

    def _text(self, surface, font, text, pos, color=INK, anchor="topleft"):
        shadow = font.render(text, True, SHADOW)
        label = font.render(text, True, color)
        rect = label.get_rect(**{anchor: pos})
        surface.blit(shadow, rect.move(2, 2))
        surface.blit(label, rect)

    def notify(self, text, seconds=2.5):
        self._notice, self._notice_until = text, pygame.time.get_ticks() + int(seconds * 1000)

    def cockpit(self, surface):
        """A simple canopy frame and dashboard for the first-person view."""
        w, h = self.w, self.h
        frame = (34, 38, 46)
        pygame.draw.polygon(surface, frame, [(0, h), (0, h - 120), (w * 0.3, h - 70),
                                             (w * 0.7, h - 70), (w, h - 120), (w, h)])
        pygame.draw.polygon(surface, (24, 27, 33), [(0, h), (0, h - 60), (w * 0.35, h - 40),
                                                    (w * 0.65, h - 40), (w, h - 60), (w, h)])
        for pts in ([(0, 0), (70, 0), (0, h - 120)], [(w, 0), (w - 70, 0), (w, h - 120)]):
            pygame.draw.polygon(surface, frame, pts)
        pygame.draw.rect(surface, frame, (0, 0, w, 14))
        # gunsight
        cx, cy = w // 2, h // 2
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 18, 1)
        pygame.draw.line(surface, (255, 255, 255), (cx - 30, cy), (cx - 8, cy), 1)
        pygame.draw.line(surface, (255, 255, 255), (cx + 8, cy), (cx + 30, cy), 1)

    def draw(self, surface, plane, view_name, status):
        kmh = plane.speed * 3.6
        line = "SPD %3d km/h    ALT %4d m    HDG %03d    VS %+d m/s" % (
            kmh, plane.altitude, plane.heading_degrees, plane.vertical_speed)
        self._text(surface, self.font, line, (16, 12))
        self._text(surface, self.font, "View: %s  (P to change)" % view_name,
                   (self.w - 16, 12), anchor="topright")
        self._text(surface, self.font, "%s  (C to change)" % plane.spec.name,
                   (self.w - 16, 36), anchor="topright")

        # throttle bar
        bx, by, bw, bh = 16, self.h - 40, 200, 16
        pygame.draw.rect(surface, SHADOW, (bx - 2, by - 2, bw + 4, bh + 4))
        pygame.draw.rect(surface, (60, 70, 84), (bx, by, bw, bh))
        pygame.draw.rect(surface, (90, 200, 120), (bx, by, int(bw * plane.throttle), bh))
        self._text(surface, self.small, "THROTTLE", (bx + bw + 10, by))

        self._gear_indicator(surface, plane)
        if pygame.time.get_ticks() < self._notice_until:
            self._text(surface, self.font, self._notice, (self.w // 2, self.h - 70), WARN, "midtop")
        if plane.on_ground:
            self._text(surface, self.font, "ON GROUND  Shift = throttle, A/D steer, B brakes; pull back (S) above %d km/h"
                       % (plane.spec.rotate_speed * 3.6), (self.w // 2, 90), WARN, "midtop")
        if plane.gear_down and not plane.on_ground:
            self._landing_panel(surface, plane)
        elif not plane.on_ground and plane.altitude < 150 and plane.speed < plane.spec.land_speed * 1.8:
            self._text(surface, self.font, "LANDING GEAR UP - press G", (16, self.h - 168), WARN)

        if plane.wing_lost:
            self._text(surface, self.big, "%s WING LOST!" % plane.wing_lost.upper(),
                       (self.w // 2, 140), (255, 90, 80), "midtop")

        if plane.stalled:
            self._text(surface, self.big, "STALL - nose down!", (self.w // 2, 90),
                       (255, 190, 60), "midtop")

        if self.show_help:
            for i, text in enumerate(HELP):
                self._text(surface, self.small, text, (16, 48 + i * 20))

        if status:
            self._text(surface, self.big, status[0], (self.w // 2, self.h // 2 - 40),
                       status[1], "midtop")
            again = "Press R to take off from here" if status[0].startswith("Landed") else "Press R to fly again"
            self._text(surface, self.font, again, (self.w // 2, self.h // 2 + 20),
                       INK, "midtop")

    def _gear_indicator(self, surface, plane):
        if plane.gear_locked_down:
            text, color = "GEAR DOWN", GOOD
        elif plane.gear <= 0.0:
            text, color = "GEAR UP", INK
        else:
            text, color = "GEAR MOVING", WARN
        self._text(surface, self.small, text, (self.w - 16, self.h - 36), color, "topright")

    def _landing_panel(self, surface, plane):
        """What this aircraft needs to land, with live values coloured green when met."""
        spec = plane.spec
        x, y = 16, self.h - 140
        fast = plane.speed >= spec.land_speed
        sink = -plane.vertical_speed
        rows = [
            ("LANDING  speed under %d km/h  (now %d)" % (spec.land_speed * 3.6, plane.speed * 3.6),
             WARN if fast else GOOD),
            ("sink under %d m/s  (now %d)" % (cfg.LAND_MAX_SINK, max(sink, 0)),
             WARN if sink >= cfg.LAND_MAX_SINK else GOOD),
            ("wings and nose level - land anywhere", INK),
        ]
        for i, (text, color) in enumerate(rows):
            self._text(surface, self.small, text, (x, y + i * 20), color)
        if fast and plane.altitude < 250:
            self._text(surface, self.font, "TOO FAST - cut throttle, hold B", (x, y - 28), WARN)
        if plane.brake > 0.05:
            self._text(surface, self.small, "AIR BRAKE", (x, y + 66), WARN)

    def paused(self, surface):
        veil = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        veil.fill((10, 16, 28, 120))
        surface.blit(veil, (0, 0))
        self._text(surface, self.big, "PAUSED", (self.w // 2, self.h // 2 - 40), anchor="midtop")
        self._text(surface, self.font, "Press Space to resume", (self.w // 2, self.h // 2 + 20),
                   anchor="midtop")
