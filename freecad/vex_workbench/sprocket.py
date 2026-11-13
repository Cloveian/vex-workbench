# 3P sprockets off the fusion library's f3ds. a 2 mm toothed plate on a hub, 1/8 square bore
import math

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
BORE_TURN = -10  # deg
# teeth: tip radius, hub radius, first gap (deg, like fusion's), one side of a gap on +y out to the middle of the next tooth and back in to x = 0
SIZES = {
    10: (0.2645, 0.1396, 98, [(0, 0.1920), ((0.0352, 0.2080), (0, 0.2387)), ((0.0498, 0.2289), (-0.0537, 0.2854)), (0.0526, 0.2342), ((0.0705, 0.2549), (0.1100, 0.2029)), ((0.0817, 0.2516), (0, 0)), (0.1226, 0.3774), (0, 0.3774)]),
    15: (0.3805, 0.1592, 98, [(0, 0.3080), ((0.0363, 0.3253), (0, 0.3547)), ((0.0517, 0.3502), (-0.0553, 0.3995)), (0.0551, 0.3574), ((0.0667, 0.3746), (0.1132, 0.3307)), ((0.0791, 0.3722), (0, 0)), (0.1187, 0.5583), (0, 0.5583)]),
    24: (0.5910, 0.1592, 95, [(0, 0.5183), ((0.0370, 0.5366), (0, 0.5650)), ((0.0529, 0.5645), (-0.0565, 0.6084)), (0.0564, 0.5733), ((0.0644, 0.5875), (0.1147, 0.5499)), ((0.0771, 0.5860), (0, 0)), (0.1157, 0.8790), (0, 0.8790)]),
}
# 24T: web down this far off each face out to r0, then an arc of radius r back up to the face
WEB = {24: (0.0098, 0.3238, 0.9843)}
# 24T: 6 windows, in / out radius, then the spoke arcs (center, r) its inside and outside of. 0.15 mm corner rounds left off
WINDOWS = {24: (0.1969, 0.3543, ((-0.0978, 0.12), 0.2446), ((-0.1295, 0.1096), 0.2235))}


def disc(r, x=0, y=0):
    return Part.Face(Part.Wire(Part.makeCircle(r * IN, Vector(x, y, 0) * IN)))


def both_faces(ring):
    # a revolved cut off the top face, and the same off the bottom
    ring = ring.revolve(Vector(), Z, 360)
    ring.scale(IN)
    return [ring, ring.mirror(Vector(0, 0, -PLATE / 2 * IN), Z)]


def make(part, cat):
    n = part["params"]["teeth"]
    tip, hub, first, gap = SIZES[n]
    cut = section(gap).rotated(Vector(), Vector(1, 0, 0), -90)
    teeth = disc(tip).cut([cut.rotated(Vector(), Z, first - 90 + 360 * k / n) for k in range(n)]).Faces[0]
    plate = teeth.extrude(Vector(0, 0, PLATE * IN)).translated(Vector(0, 0, -PLATE * IN))
    cuts = both_faces(Part.Face(Part.makePolygon([Vector(tip - CHAMFER, 0, 0.0001), Vector(tip + 0.1, 0, 0.0001), Vector(tip + 0.1, 0, -0.1 - CHAMFER), Vector(tip - CHAMFER, 0, 0.0001)])))
    if n in WEB:
        d, r0, r = WEB[n]
        out = r0 + math.sqrt(r**2 - (r - d)**2)  # where the arc meats the face
        mid = (r0 + out) / 2
        arc = Part.Arc(Vector(r0, 0, -d), Vector(mid, 0, r - d - math.sqrt(r**2 - (mid - r0)**2)), Vector(out, 0, 0)).toShape()
        lines = [Part.makeLine(*p) for p in ((Vector(out, 0, 0), Vector(out, 0, 0.001)), (Vector(out, 0, 0.001), Vector(0, 0, 0.001)), (Vector(0, 0, 0.001), Vector(0, 0, -d)), (Vector(0, 0, -d), Vector(r0, 0, -d)))]
        cuts += both_faces(Part.Face(Part.Wire([arc] + lines)))
    if n in WINDOWS:
        inner, outer, (a, ra), (b, rb) = WINDOWS[n]
        w = max(disc(outer).cut(disc(inner)).common(disc(ra, *a)).cut(disc(rb, *b)).Faces, key=lambda f: f.Area)  # and a sliver
        cuts += [w.extrude(Vector(0, 0, 2 * IN)).translated(Vector(0, 0, -IN)).rotated(Vector(), Z, 60 * k) for k in range(6)]
    body = Part.makeCylinder(hub * IN, (HUB_Z[1] - HUB_Z[0]) * IN, Vector(0, 0, HUB_Z[0] * IN))
    bore = square(BORE * IN, BORE_ROUND * IN).rotated(Vector(), Z, BORE_TURN).extrude(Vector(0, 0, 2 * IN)).translated(Vector(0, 0, -IN))
    return plate.cut(cuts).fuse(body).cut(bore).removeSplitter()
