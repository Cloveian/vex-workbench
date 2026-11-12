# linear slide trucks off the fusion library's f3ds. drafts, the 0.3 mm rib fillets and the outer one's end chamfers left off
import math

import Part
from FreeCAD import Vector

from .metal import IN
from .rail import at

FAMILIES = ("slide-truck",)

# in, fusion's frame: first hole on the origin, along +y. the inner one hangs off z = 0, the outer one stands on it
# half sections, x >= 0. a point, or (point, arc center) where an arc gets to it. walls squared up off their 1 deg draft
INNER = [(0, 0), (0.2393, 0), ((0.2583, -0.0146), (0.2393, -0.0197)), (0.2847, -0.1132), ((0.2994, -0.1273), (0.3038, -0.1081)), ((0.3141, -0.1414), (0.2951, -0.1465)), (0.3427, -0.2483), ((0.3288, -0.2724), (0.3237, -0.2534)), (0.3096, -0.2775),
         ((0.2950, -0.2966), (0.3147, -0.2966)), (0.2950, -0.3100), ((0.2753, -0.3296), (0.2753, -0.3100)), (0.2309, -0.3296), ((0.2112, -0.3100), (0.2309, -0.3100)), (0.2112, -0.0707), ((0.1980, -0.0591), (0.1980, -0.0709)), (0, -0.0591)]
WALL, PLATE, RIBS, ENDS = 0.2112, -0.0591, -0.2035, -0.2336  # inner wall x, underside of the top, rib bottoms, end wall bottoms
RIB, BOSS, FILLET = 0.0206, 0.1516, 0.0118  # half a rib, boss radius, pocket corners
Y0, Y1, POCKET = -0.2475, 1.7475, (-0.1878, 1.6878)
CHAMFER = 0.016  # round both ends
HOLES = (0, 0.5, 1, 1.5)
HOLE = [(0.0827, 0.01), (0.0827, -0.0657), (0.0728, -0.0828), (0.0728, RIBS - 0.01)]  # 0.165 clearence, 30 deg in to 0.146 for the screw to bite

# outer, the section at a cross rib. the inner truck's feet go in the round grooves
OUTER = [(0, 0), (0.2417, 0), ((0.2559, 0.0059), (0.2417, 0.0200)), (0.4889, 0.2389), ((0.4946, 0.2524), (0.4749, 0.2528)), (0.4997, 0.5403), ((0.4800, 0.5603), (0.4800, 0.5406)), (0.4019, 0.5603), ((0.3826, 0.5352), (0.4019, 0.5403)), (0.4062, 0.4472),
         ((0.4153, 0.4415), (0.4138, 0.4492)), ((0.4246, 0.4352), (0.4168, 0.4337)), ((0.3217, 0.3051), (0.3165, 0.4150)), ((0.3165, 0.3101), (0.3215, 0.3101)), (0.3165, 0.3150), ((0.3115, 0.3200), (0.3115, 0.3150)), (0.2215, 0.3200),
         ((0.2165, 0.3150), (0.2215, 0.3150)), (0.2165, 0.3074), ((0.2146, 0.3035), (0.2115, 0.3074)), (0.1054, 0.2144), ((0.0930, 0.2100), (0.0930, 0.2297)), (0, 0.2100)]
# pockets from below between the ribs: under the web, and under the grooves out to the 45 deg face
UNDER_WEB = [(0.021, -0.01), (0.021, 0.1509), (0.121, 0.1509), (0.2005, 0.2156), (0.2005, -0.01), (0.021, -0.01)]
UNDER_GROOVE = [(0.244, -0.01), (0.244, 0.2622), ((0.4264, 0.2866), (0.3165, 0.4150)), ((0.4463, 0.2778), (0.4345, 0.2776)), (0.4463, 0.2251), ((0.4670, 0.2170), (0.4581, 0.2251)), (0.3, -0.01), (0.244, -0.01)]
OUTER_RIB, OUTER_Y, BOSS_TOP = 0.0227, (-0.2437, 1.7437), 0.25  # half a cross rib, ends, bosses up past the web
OUTER_HOLE = [(0.0827, -0.01), (0.0827, 0.0394), (0.0728, 0.0564), (0.0728, BOSS_TOP)]


def half(pts):
    out, last = [], None
    for q in pts:
        p, c = (q, None) if isinstance(q[0], (int, float)) else q
        p = (p[0] * IN, p[1] * IN)
        if c and last:
            c = (c[0] * IN, c[1] * IN)
            # through the real ends, fusion's 4 places put them a hair off one radius
            a0, a1 = math.atan2(last[1] - c[1], last[0] - c[0]), math.atan2(p[1] - c[1], p[0] - c[0])
            a, r = a0 + ((a1 - a0 + math.pi) % (2 * math.pi) - math.pi) / 2, math.dist(c, p)  # halfway, the short way round
            out.append(Part.Arc(at(*last), at(c[0] + r * math.cos(a), c[1] + r * math.sin(a)), at(*p)).toShape())
        elif last:
            out.append(Part.makeLine(at(*last), at(*p)))
        last = p
    return out


def section(pts):
    edges = half(pts)
    return Part.Face(Part.Wire(Part.__sortEdges__(edges + [e.mirror(Vector(), Vector(1, 0, 0)) for e in edges])))


def both_sides(pts):
    # outline already closed, on +x
    f = Part.Face(Part.Wire(half(pts)))
    return [f, f.mirror(Vector(), Vector(1, 0, 0))]


def along(face, y0, y1):
    return face.extrude(Vector(0, (y1 - y0) * IN, 0)).translated(Vector(0, y0 * IN, 0))


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox((x1 - x0) * IN, (y1 - y0) * IN, (z1 - z0) * IN, Vector(x0, y0, z0) * IN)


def cross_ribs(rib, z0, z1):
    # and a boss z0 to z1 round every hole
    return [box(-1, 1, y - rib, y + rib, -1, 1) for y in HOLES] + [Part.makeCylinder(BOSS * IN, (z1 - z0) * IN, Vector(0, y, z0) * IN) for y in HOLES]


def holes(profile):
    start, end = at(0, profile[0][1] * IN), at(0, profile[-1][1] * IN)
    hole = Part.Face(Part.makePolygon([start] + [at(x * IN, z * IN) for x, z in profile] + [end, start])).revolve(Vector(), Vector(0, 0, 1), 360)
    return [hole.translated(Vector(0, y * IN, 0)) for y in HOLES]


def inner():
    body = along(section(INNER), Y0, Y1).fuse(box(-WALL, WALL, Y0, Y1, ENDS, PLATE))
    # pockets up under the top between the ribs and bosses, open below the ribs
    flat = Part.Face(Part.makePolygon([Vector(x, y, 0) * IN for x, y in ((-WALL, POCKET[0]), (WALL, POCKET[0]), (WALL, POCKET[1]), (-WALL, POCKET[1]), (-WALL, POCKET[0]))]))
    ribs = [box(-RIB, RIB, *POCKET, -1, 1)] + cross_ribs(RIB, -1, 1)
    cuts = [box(-WALL, WALL, *POCKET, ENDS - 0.01, RIBS)]
    for f in flat.cut(ribs).Faces:
        f = f.makeOffset2D(-FILLET * IN).makeOffset2D(FILLET * IN)
        cuts.append(f.translated(Vector(0, 0, (RIBS - 0.001) * IN)).extrude(Vector(0, 0, (PLATE - RIBS + 0.001) * IN)))
    body = body.cut(cuts)
    body = body.cut(holes(HOLE)).removeSplitter()
    ends = [e for f in body.Faces if f.BoundBox.YLength < 1e-6 and min(abs(f.BoundBox.YMin - Y0 * IN), abs(f.BoundBox.YMin - Y1 * IN)) < 1e-6 for e in f.Edges]
    return body.makeChamfer(CHAMFER * IN, ends)


def outer():
    solid = along(section(OUTER), *OUTER_Y)
    pockets = [along(f, *POCKET) for f in both_sides(UNDER_WEB) + both_sides(UNDER_GROOVE)]
    # cross ribs and bosses back in, solid section wherever they are
    ribs = cross_ribs(OUTER_RIB, -0.01, BOSS_TOP)
    body = solid.cut(pockets).fuse(solid.common(ribs))
    return body.cut(holes(OUTER_HOLE)).removeSplitter()


def make(part, cat):
    return {"Inner": inner, "Outer": outer}[part["params"]["side"]]()
