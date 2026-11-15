# 3P sprockets off the fusion library's f3ds. a 2 mm toothed plate on a hub, 1/8 square bore
import math

import Part
from FreeCAD import Vector

from .metal import IN, square
from .ratchet import BORE, BORE_ROUND, revolved
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
    40: (0.9660, 0.1592, 98, [(0, 0.8933), ((0.0375, 0.9122), (0, 0.9400)), ((0.0536, 0.9422), (-0.0572, 0.9823)), (0.0572, 0.9520), ((0.0630, 0.96394), (0.1153, 0.9309)), ((0.0758, 0.9630), (0, 0)), (0.0866, 1.1), (0, 1.1)]),  # 0.96394 puts the round's end on the 0.966 tip, 0.9639 left the box 0.0005 short
    48: (1.1535, 0.1592, 95, [(0, 1.0809), ((0.0377, 1.1000), (0, 1.1276)), ((0.0538, 1.1305), (-0.0574, 1.1697)), (0.0573, 1.1406), ((0.0626, 1.1518), (0.1155, 1.1201)), ((0.0754, 1.1510), (0, 0)), (0.0852, 1.3), (0, 1.3)]),
}
# web down this far off each face out to r0, then an arc of radius r back up to the face. the 40T's and 48T's run into the rib frist
WEB = {24: (0.0098, 0.3238, 0.9843), 40: (0.0098, 0.5584, 3.937), 48: (0.0098, 0.6828, 6.0)}
# 6 windows, in / out radius, the spoke arcs (center, r) its inside and outside of, and about where its middle is (deg), the cut leaves two pieces. 0.15 mm corner rounds left off
WINDOWS = {
    24: (0.1969, 0.3543, ((-0.0978, 0.12), 0.2446), ((-0.1295, 0.1096), 0.2235), 80),
    40: (0.2953, 0.6890, ((0.0117, -0.3469), 0.5342), ((0.0237, -0.3688), 0.4784), -17.9),
    48: (0.5118, 0.8858, ((0.3420, 0.0739), 0.6531), ((0.3742, 0.0881), 0.5945), 74),
}
# a ring rib standing off both faces, (r, z) points and (end, center) arcs like the ratchet's pockets. 0.5 mm rounds on its outside corners. the 40T's is the 48T's moved in
RIB = {
    40: [(0.7880, -0.1673), (0.7880, 0.0886), (0.8155, 0.0886), ((0.8352, 0.0689), (0.8155, 0.0689)), (0.8352, -0.1476), ((0.8155, -0.1673), (0.8155, -0.1476)), (0.7880, -0.1673)],
    48: [(0.9752, -0.1673), (0.9752, 0.0886), (1.0027, 0.0886), ((1.0224, 0.0689), (1.0027, 0.0689)), (1.0224, -0.1476), ((1.0027, -0.1673), (1.0027, -0.1476)), (0.9752, -0.1673)],
}
# 4 bosses, r 0.5 at this deg + 90k, boss / hole radius, z from / to (one end on a web face) and the round on the far end. the 48T's go out the back, the 40T's the front, and they sit across 2 of its slots
BOSSES = {40: (41, 0.1299, 0.0827, -0.0689, 0.2067, 0.0197), 48: (37.31, 0.1181, 0.0888, -0.2854, -0.0098, 0.0197)}


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
        inner, outer, (a, ra), (b, rb), at = WINDOWS[n]
        pieces = disc(outer).cut(disc(inner)).common(disc(ra, *a)).cut(disc(rb, *b)).Faces
        w = min(pieces, key=lambda f: abs(math.remainder(math.degrees(math.atan2(f.CenterOfMass.y, f.CenterOfMass.x)) - at, 360)))
        cuts += [w.extrude(Vector(0, 0, 2 * IN)).translated(Vector(0, 0, -IN)).rotated(Vector(), Z, 60 * k) for k in range(6)]
    body = [Part.makeCylinder(hub * IN, (HUB_Z[1] - HUB_Z[0]) * IN, Vector(0, 0, HUB_Z[0] * IN))]
    bore = [square(BORE * IN, BORE_ROUND * IN).rotated(Vector(), Z, BORE_TURN).extrude(Vector(0, 0, 2 * IN)).translated(Vector(0, 0, -IN))]
    if n in RIB:
        body.append(revolved(RIB[n]))
    if n in BOSSES:
        at, br, hr, z0, z1, rr = BOSSES[n]
        far = z0 if abs(z0) > abs(z1) else z1
        for k in range(4):
            c = Vector(math.cos(math.radians(at + 90 * k)), math.sin(math.radians(at + 90 * k)), 0) * 0.5 * IN
            boss = Part.makeCylinder(br * IN, (z1 - z0) * IN, c + Vector(0, 0, z0 * IN))
            body.append(boss.makeFillet(rr * IN, [e for e in boss.Edges if abs(e.BoundBox.Center.z - far * IN) < 0.001 * IN]))
            bore.append(Part.makeCylinder(hr * IN, 2 * IN, c - Vector(0, 0, IN)))
    return plate.cut(cuts).fuse(body).cut(bore).removeSplitter()
