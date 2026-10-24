"""On-screen display: flight data, throttle, help and the cockpit frame."""
import pygame

INK = (255, 255, 255)
SHADOW = (20, 28, 40)

HELP = [
    "W / S   nose down / up",
    "A / D   bank left / right",
    "Shift / Ctrl   throttle up / down",
    "P   change view      R   restart",
    "H   hide help        Esc   quit",
]


class Hud:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.font = pygame.font.Font(None, 26)
        self.big = pygame.font.Font(None, 54)
        self.small = pygame.font.Font(None, 22)
        self.show_help = True

    def _text(self, surface, font, text, pos, color=INK, anchor="topleft"):
        shadow = font.render(text, True, SHADOW)
        label = font.render(text, True, color)
        rect = label.get_rect(**{anchor: pos})
        surface.blit(shadow, rect.move(2, 2))
        surface.blit(label, rect)

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

        # throttle bar
        bx, by, bw, bh = 16, self.h - 40, 200, 16
        pygame.draw.rect(surface, SHADOW, (bx - 2, by - 2, bw + 4, bh + 4))
        pygame.draw.rect(surface, (60, 70, 84), (bx, by, bw, bh))
        pygame.draw.rect(surface, (90, 200, 120), (bx, by, int(bw * plane.throttle), bh))
        self._text(surface, self.small, "THROTTLE", (bx + bw + 10, by))

        if plane.stalled:
            self._text(surface, self.big, "STALL - nose down!", (self.w // 2, 90),
                       (255, 190, 60), "midtop")

        if self.show_help:
            for i, text in enumerate(HELP):
                self._text(surface, self.small, text, (16, 48 + i * 20))

        if status:
            self._text(surface, self.big, status[0], (self.w // 2, self.h // 2 - 40),
                       status[1], "midtop")
            self._text(surface, self.font, "Press R to fly again", (self.w // 2, self.h // 2 + 20),
                       INK, "midtop")
