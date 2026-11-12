# ratchet gear and winch pawl off the fusion library's f3ds. the gear is a sawtooth rim, round pockets both faces, a hub and four bossed holes in the web, 1/8 square bore
import math

import Part
from FreeCAD import Vector

from . import metal, slide
from .metal import IN, square
from .slide import half

FAMILIES = ("ratchet-gear", "winch-pawl")

# in. built round z with y as the second number of the profiles, turned onto y at the end like fusion's
TEETH, ROOT, TIP, TIP_ROUND = 25, 0.75, 0.8705, 0.01  # steep face radial, TIP is the sharp tip, unrounded
FRONT, BACK, HUB, HUB_TOP = 0.0, -0.25, 0.1562, 0.07
# pockets revolved, (r, y), with 1 deg draft and 0.5 mm rounds at the floors and the hub
FRONT_POCKET = [(0.1562, 0.01), (0.70, 0.01), (0.70, 0), (0.6966, -0.0966), ((0.677, -0.1156), (0.677, -0.0959)), (0.1759, -0.1156), ((0.1562, -0.0959), (0.1759, -0.0959)), (0.1562, 0.01)]
BACK_POCKET = [(0, -0.26), (0.70, -0.26), (0.70, -0.25), (0.6987, -0.2134), ((0.679, -0.1944), (0.679, -0.2141)), (0, -0.1944), (0, -0.26)]
BOSS, BOSS_FACES, HOLE, HOLES_AT = 0.1476, (-0.205, -0.105), 0.0875, 0.5
BORE, BORE_ROUND, SQUARE_BOSS = 0.127, 0.0098, 0.0591  # the back boss is the bore grown by that

# pawl, (x, z) halfway up one half, so its 1 deg draft both ways off the middle evens out. the hub arc goes the long way, so it gets a point on +x
PAWL = [(0.0100, 0.2997), ((-0.0147, 0.2063), (-0.0024, 0.2530)), ((-0.0779, 0.1695), (-0.0279, 0.1563)), (-0.0790, 0.1653), ((-0.0506, 0.1394), (-0.0580, 0.1598)), ((0.1483, 0), (0, 0)), ((0.0159, -0.1474), (0, 0)),
        (-0.2747, -0.1787), ((-0.2962, -0.1861), (-0.2692, -0.2301)), (-0.4666, -0.2905), ((-0.4942, -0.2775), (-0.4761, -0.2749)), (-0.5096, -0.1717), ((-0.5016, -0.1538), (-0.4915, -0.1690)), (-0.2293, 0.0262),
        ((-0.2078, 0.0562), (-0.2578, 0.0694)), (-0.1458, 0.2908), ((-0.0867, 0.3252), (-0.0991, 0.2785)), (0.0100, 0.2997)]
WINDOW = [(-0.1461, -0.0126), ((-0.1643, -0.0038), (-0.1578, -0.0137)), (-0.3092, -0.0989), ((-0.3014, -0.1205), (-0.3027, -0.1088)), (-0.1290, -0.1019), ((-0.1205, -0.0835), (-0.1302, -0.0902)), ((-0.1461, -0.0126), (0, 0))]
PAWL_THICK, WINDOW_DEPTH = 0.39, 0.1655  # window in that far from each face, 0.059 web left between
BEVEL = (0.2106, 0.9776, 0.047)  # x, y of the plane's normal, 12 deg off the y = 0 face, and how far out it sits


def revolved(pts):
    return Part.Face(Part.Wire(half(pts))).revolve(Vector(), Vector(0, 0, 1), 360)


def along(face, z0, z1):
    return face.extrude(Vector(0, 0, (z1 - z0) * IN)).translated(Vector(0, 0, z0 * IN))


def gear():
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


def pawl():
    # straight in fusion's frame, the profiles are x, z already
    body = slide.along(Part.Face(Part.Wire(half(PAWL))), 0, PAWL_THICK)
    window = Part.Face(Part.Wire(half(WINDOW)))
    bore = square(BORE * IN, BORE_ROUND * IN).rotated(Vector(), Vector(1, 0, 0), 90)
    cuts = [slide.along(window, 0, WINDOW_DEPTH), slide.along(window, PAWL_THICK - WINDOW_DEPTH, PAWL_THICK), slide.along(bore, -0.5, 1.5)]
    # arm end beveled back off both faces
    bevel = metal.half(Vector(), Vector(-BEVEL[0], -BEVEL[1], 0), Vector(0, 0, 1), BEVEL[2] * IN)
    cuts += [bevel, bevel.mirror(Vector(0, PAWL_THICK * IN / 2, 0), Vector(0, 1, 0))]
    return body.cut(cuts).removeSplitter()


def make(part, cat):
    return {"ratchet-gear": gear, "winch-pawl": pawl}[part["family"]]()
