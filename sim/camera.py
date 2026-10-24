"""Camera with first-person and chase (third-person) modes."""
import math

from . import config as cfg
from .vec import add, cross, lerp, normalize, scale, sub

FIRST_PERSON = "1st person"
THIRD_PERSON = "3rd person"
VIEWS = [THIRD_PERSON, FIRST_PERSON]


class Camera:
    def __init__(self, width, height):
        self.cx, self.cy = width / 2.0, height / 2.0
        self.focal = self.cx / math.tan(math.radians(cfg.FOV_DEGREES) / 2.0)
        self.pos = (0.0, 0.0, 0.0)
        self.fwd, self.right, self.up = (0, 0, 1), (1, 0, 0), (0, 1, 0)
        self._snap = True

    def set_basis(self, pos, fwd, up):
        self.pos = pos
        self.fwd = normalize(fwd)
        self.right = normalize(cross(up, self.fwd))
        self.up = cross(self.fwd, self.right)

    def snap_next_update(self):
        """Jump straight to the target on the next chase update (after a view change)."""
        self._snap = True

    def follow(self, plane, view, dt):
        fwd, _, up = plane.basis
        if view == FIRST_PERSON:
            pos = add(add(plane.pos, scale(up, 0.9)), scale(fwd, 2.2))
            self.set_basis(pos, fwd, up)
            return

        # Chase camera: behind and above, easing toward the target.
        soft_up = normalize(lerp((0.0, 1.0, 0.0), up, 0.35))
        target = add(add(plane.pos, scale(fwd, -20.0)), scale(soft_up, 6.0))
        pos = target if self._snap else lerp(self.pos, target, min(1.0, 6.0 * dt))
        self._snap = False
        pos = (pos[0], max(pos[1], 2.0), pos[2])
        look_at = add(plane.pos, scale(fwd, 10.0))
        self.set_basis(pos, sub(look_at, pos), soft_up)

    def to_camera(self, p):
        d = sub(p, self.pos)
        return (d[0] * self.right[0] + d[1] * self.right[1] + d[2] * self.right[2],
                d[0] * self.up[0] + d[1] * self.up[1] + d[2] * self.up[2],
                d[0] * self.fwd[0] + d[1] * self.fwd[1] + d[2] * self.fwd[2])

    def project(self, pc):
        z = pc[2]
        return (self.cx + pc[0] / z * self.focal, self.cy - pc[1] / z * self.focal)
