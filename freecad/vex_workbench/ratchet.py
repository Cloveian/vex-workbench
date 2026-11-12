# the ratchet gear off the fusion library's f3d: sawtooth rim, round pockets both faces, a hub and four bossed holes in the web, 1/8 square bore
import math

import Part
from FreeCAD import Vector

from .metal import IN, square
from .slide import half

FAMILIES = ("ratchet-gear",)

# in. built round z with y as the second number of the profiles, turned onto y at the end like fusion's
TEETH, ROOT, TIP, TIP_ROUND = 25, 0.75, 0.8705, 0.01  # steep face radial, TIP is the sharp tip, unrounded
FRONT, BACK, HUB, HUB_TOP = 0.0, -0.25, 0.1562, 0.07
# pockets revolved, (r, y), with 1 deg draft and 0.5 mm rounds at the floors and the hub
FRONT_POCKET = [(0.1562, 0.01), (0.70, 0.01), (0.70, 0), (0.6966, -0.0966), ((0.677, -0.1156), (0.677, -0.0959)), (0.1759, -0.1156), ((0.1562, -0.0959), (0.1759, -0.0959)), (0.1562, 0.01)]
BACK_POCKET = [(0, -0.26), (0.70, -0.26), (0.70, -0.25), (0.6987, -0.2134), ((0.679, -0.1944), (0.679, -0.2141)), (0, -0.1944), (0, -0.26)]
BOSS, BOSS_FACES, HOLE, HOLES_AT = 0.1476, (-0.205, -0.105), 0.0875, 0.5
BORE, BORE_ROUND, SQUARE_BOSS = 0.127, 0.0098, 0.0591  # the back boss is the bore grown by that


def revolved(pts):
    return Part.Face(Part.Wire(half(pts))).revolve(Vector(), Vector(0, 0, 1), 360)


def along(face, z0, z1):
    return face.extrude(Vector(0, 0, (z1 - z0) * IN)).translated(Vector(0, 0, z0 * IN))


def make(part, cat):
    step = 2 * math.pi / TEETH
    rim = []
    for k in range(TEETH):
        rim += [(ROOT, k * step - step / 2), (TIP, k * step + step / 2)]
    # fusion's x, z are x, -y here
    rim = Part.Face(Part.makePolygon([Vector(r * math.cos(a), -r * math.sin(a), 0) * IN for r, a in rim + rim[:1]]))
    body = along(rim, BACK, FRONT)
    body = body.makeFillet(TIP_ROUND * IN, [e for e in body.Edges if e.BoundBox.ZLength > 1 and math.hypot(e.BoundBox.XMin, e.BoundBox.YMin) > (ROOT + 0.05) * IN])
    body = body.cut([revolved(FRONT_POCKET), revolved(BACK_POCKET)])
    holes = [(HOLES_AT * math.cos(a), HOLES_AT * math.sin(a)) for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    bosses = [Part.makeCylinder(BOSS * IN, (BOSS_FACES[1] - BOSS_FACES[0]) * IN, Vector(x, y, BOSS_FACES[0]) * IN) for x, y in holes]
    hub = Part.makeCylinder(HUB * IN, (HUB_TOP + 0.1) * IN, Vector(0, 0, -0.1) * IN)
    back = along(square((BORE + 2 * SQUARE_BOSS) * IN, (BORE_ROUND + SQUARE_BOSS) * IN), BOSS_FACES[0], -0.19)
    body = body.fuse(bosses + [hub, back])
    cuts = [Part.makeCylinder(HOLE * IN, 2 * IN, Vector(x, y, -1) * IN) for x, y in holes] + [along(square(BORE * IN, BORE_ROUND * IN), -1, 1)]
    body = body.cut(cuts).removeSplitter()
    body.rotate(Vector(), Vector(1, 0, 0), -90)
    return body
