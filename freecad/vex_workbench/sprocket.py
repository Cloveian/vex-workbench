# 3P sprockets off the fusion library's f3ds, the small ones with a plain web. a 2 mm toothed plate on a hub, 1/8 square bore
import Part
from FreeCAD import Vector

from .metal import IN, square
from .ratchet import BORE, BORE_ROUND
from .slide import section

FAMILIES = ("sprocket-3p",)
Z = Vector(0, 0, 1)

# in, axis on z. 3.75 mm pitch, seats r 0.0467 on the pitch circle
PLATE = 0.0787  # z -PLATE..0
HUB_Z = -0.2854, 0.2067  # 1 deg draft, 0.3 mm end rounds and the crush ribs in the bore left off
CHAMFER = 0.015  # 45 deg off both faces at the tips, flanks inlcuded
FIRST_GAP = 98  # deg, like fusion's
BORE_TURN = -10  # deg
# teeth: tip radius, hub radius, one side of a gap on +y out to the middle of the next tooth and back in to x = 0
SIZES = {
    10: (0.2645, 0.1396, [(0, 0.1920), ((0.0352, 0.2080), (0, 0.2387)), ((0.0498, 0.2289), (-0.0537, 0.2854)), (0.0526, 0.2342), ((0.0705, 0.2549), (0.1100, 0.2029)), ((0.0817, 0.2516), (0, 0)), (0.1226, 0.3774), (0, 0.3774)]),
    15: (0.3805, 0.1592, [(0, 0.3080), ((0.0363, 0.3253), (0, 0.3547)), ((0.0517, 0.3502), (-0.0553, 0.3995)), (0.0551, 0.3574), ((0.0667, 0.3746), (0.1132, 0.3307)), ((0.0791, 0.3722), (0, 0)), (0.1187, 0.5583), (0, 0.5583)]),
}


def make(part, cat):
    n = part["params"]["teeth"]
    tip, hub, gap = SIZES[n]
    cut = section(gap).rotated(Vector(), Vector(1, 0, 0), -90)
    teeth = Part.Face(Part.Wire(Part.makeCircle(tip * IN))).cut([cut.rotated(Vector(), Z, FIRST_GAP - 90 + 360 * k / n) for k in range(n)]).Faces[0]
    plate = teeth.extrude(Vector(0, 0, PLATE * IN)).translated(Vector(0, 0, -PLATE * IN))
    # a ring off the top face round the tips, and the same off the bottom
    edge = Part.Face(Part.makePolygon([Vector(tip - CHAMFER, 0, 0.0001), Vector(tip + 0.1, 0, 0.0001), Vector(tip + 0.1, 0, -0.1 - CHAMFER), Vector(tip - CHAMFER, 0, 0.0001)])).revolve(Vector(), Z, 360)
    edge.scale(IN)
    chamfers = [edge, edge.mirror(Vector(0, 0, -PLATE / 2 * IN), Z)]
    body = Part.makeCylinder(hub * IN, (HUB_Z[1] - HUB_Z[0]) * IN, Vector(0, 0, HUB_Z[0] * IN))
    bore = square(BORE * IN, BORE_ROUND * IN).rotated(Vector(), Z, BORE_TURN).extrude(Vector(0, 0, 2 * IN)).translated(Vector(0, 0, -IN))
    return plate.cut(chamfers).fuse(body).cut(bore).removeSplitter()
