# the 4 legacy round traction wheel off the fusion library's f3d. a hub with 6 grooved swirl spokes and 30 teeth round its rim, a round tire over them
import Part
from FreeCAD import Vector

from .metal import IN, X, square
from .omni import both, polar, turned
from .ratchet import BORE, BORE_ROUND, along, revolved
from .slide import box, half

FAMILIES = ("round-wheel",)
Z = Vector(0, 0, 1)

DISC, SPOKES = 0.0295, 0.2756  # z of the middle disc's faces and the spoke tops
INSIDE = (0.6619, 0.3593)  # the rim's inside is an arc round this, r 1.4567 at the disc to 1.5193 at the top
RIM = [(0, DISC), (1.4459, DISC), (1.4567, 0.0369), ((1.5193, 0.3307), INSIDE), (1.5193, 1), (0, 1), (0, DISC)]  # inside the rim, over the disc
# half the hub round z, (r, z) like slide.half. tooth roots out to the rim's sides, a channel under them, the rim's inside in to the spoke tops, the tube and the boss with its dished end
HUB = [(0, 0), (1.75, 0), (1.75, 0.2431), (1.7106, 0.2466), (1.6909, 0.2466), (1.6873, 0.0394), (1.6196, 0.0394), (1.6139, 0.3634), ((1.6021, 0.375), (1.6021, 0.3632)), (1.5639, 0.375), (1.5556, 0.3715), (1.5227, 0.3387),
       ((1.5193, 0.3307), (1.5311, 0.3303)), ((1.5155, SPOKES), INSIDE), (0.3518, SPOKES), ((0.3395, 0.2868), (0.3513, 0.2874)), (0.3381, 0.3634), ((0.3263, 0.375), (0.3263, 0.3634)), (0.3036, 0.375), ((0.2918, 0.3634), (0.3036, 0.3634)),
       (0.2902, SPOKES), (0.192, SPOKES), (0.1905, 0.3634), ((0.1787, 0.375), (0.1787, 0.3634)), (0.1575, 0.375), ((0, 0.3623), (0, 1.3466)), (0, 0)]
# one of 6 each, +60k, closed outlines like slide.half. the disc's windows, the ones over it between the spokes, the groove down a spoke, the hole beside it in the gap round the boss
# all but the disc's off z 0.15, halfway up their 7.7, 1.7 and 1 deg drafts (left off). the ones between the spokes run out past the rim to get cut off on its inside
WINDOW = [(0.3487, 0.0742), ((0.6486, 0.2308), (0.1866, 0.7528)), ((0.829, 0.5163), (0.2215, 0.6999)), ((0.8549, 0.8544), (0.0597, 0.7435)), ((0.7612, 1.1746), (-0.2373, 0.7071)), (0.7569, 1.1796), ((-0.0129, 1.4015), (0, 0)),
          ((-0.062, 1.2183), (-0.012, 1.3031)), ((0.318, 0.7523), (-0.4809, 0.4874)), ((0.3619, 0.4495), (-0.5418, 0.4739)), ((0.312, 0.1535), (-0.7088, 0.4787)), (0.3125, 0.1449), ((0.3344, 0.0828), (0, 0)), ((0.3487, 0.0742), (0.3459, 0.0856))]
OPEN = [(-0.588, 1.3485), (-0.6116, 1.4025), ((0.7245, 1.3476), (0, 0)), (0.7044, 1.3103), ((0.8503, 0.9554), (-0.3429, 0.6704)), ((0.8576, 0.5733), (-0.0048, 0.7458)), ((0.6767, 0.2393), (0.2127, 0.7055)),
        ((0.3491, 0.0607), (0.1889, 0.7476)), ((0.3347, 0.0698), (0.3462, 0.0722)), ((0.3032, 0.1579), (0, 0)), (0.3024, 0.1669), ((0.3407, 0.5951), (-0.6585, 0.4705)), ((0.1774, 0.9911), (-0.4812, 0.4886)), ((-0.1609, 1.2546), (-0.5116, 0.4534)),
        ((-0.5725, 1.348), (-0.6063, 0.2369)), ((-0.588, 1.3485), (-0.6246, 0.0388))]
GROOVE = [(0.1871, 0.2963), ((0.1918, 0.283), (0.1984, 0.2928)), ((0.2317, 0.2514), (0, 0)), ((0.2512, 0.2574), (0.2397, 0.2601)), ((0.2244, 0.7591), (-0.5829, 0.4672)), ((0.1946, 0.749), (0.2092, 0.7551)), ((0.1871, 0.2963), (-0.5511, 0.5369))]
GAP = [(0.2287, 0.1752), ((0.166, 0.2354), (0, 0)), ((0.1273, 0.1467), (-0.8859, 0.6418)), ((0.1848, 0.0597), (0, 0)), ((0.2287, 0.1752), (-0.869, 0.5263))]
# 30 teeth on 12s from 90 deg, top r and half its angle, root r and half the angle there, out to z
TEETH = 30, 1.8287, 2.296, 1.75, 3.05, 0.2378
# the channel under the teeth comes in 15 slots, a brige 0.0716 wide on every 24 deg
BRIDGE = 15, 0.0716, 1.6177, 1.6893, 0.0394, 0.1969
# tire (r, z), lips under the rim's sides, down between the teeth. round on two arcs a side, a bit flatter on top than a circle
TIRE = [(1.62, -0.375), (1.62, -0.25), (1.7106, -0.25), (1.75, -0.2469), (1.75, 0.2469), (1.7106, 0.25), (1.62, 0.25), (1.62, 0.375),
        ((1.8913, 0.2752), (1.6295, -0.0166)), ((2.0, 0), (1.6277, 0.0142)), ((1.8913, -0.2752), (1.6277, -0.0142)), ((1.62, -0.375), (1.6295, 0.0166))]


def outline(pts):
    return Part.Face(Part.Wire(half(pts))).rotated(Vector(), X, -90)  # off x-z


def cutouts():
    # both sides, the disc's straight through it
    rim = revolved(RIM)
    top = [along(outline(pts), DISC, SPOKES + 0.01).common(rim) for pts in (OPEN, GROOVE, GAP)]
    one = [along(outline(WINDOW), -DISC - 0.01, DISC + 0.01)] + top + [s.mirror(Vector(), Z) for s in top]
    return [turned(s, 60 * k) for s in one for k in range(6)]


def teeth():
    n, top, a, root, b, z = TEETH
    out = []
    for k in range(n):
        d = 90 + 360 * k / n
        # in past the root so it fuses, the top on its circle
        p = [Vector(*polar(r, d + e), 0) * IN for r, e in ((root - 0.02, -b), (root, -b), (top, -a), (top, 0), (top, a), (root, b), (root - 0.02, b))]
        edges = [Part.makeLine(p[i], p[i + 1]) for i in (0, 1, 4, 5)] + [Part.Arc(p[2], p[3], p[4]).toShape(), Part.makeLine(p[6], p[0])]
        out.append(along(Part.Face(Part.Wire(Part.__sortEdges__(edges))), -z, z))
    return out


def hub(teeth):
    n, wide, r0, r1, z0, z1 = BRIDGE
    bridge = box(r0, r1, -wide / 2, wide / 2, z0, z1)
    bridges = [turned(bridge, 360 * k / n) for k in range(n)]
    body = Part.makeCompound(both(HUB)).fuse(bridges + [b.mirror(Vector(), Z) for b in bridges] + teeth)
    return body.cut(cutouts() + [along(square(BORE * IN, BORE_ROUND * IN), -1, 1)]).removeSplitter()


def make(part, cat):
    t = teeth()
    return Part.makeCompound([hub(t), revolved(TIRE).cut(t)])
