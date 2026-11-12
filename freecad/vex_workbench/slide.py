# linear slide trucks off the fusion library's f3ds. drafts and the 0.3 mm rib fillets left off
import math

import Part
from FreeCAD import Vector

from .metal import IN
from .rail import at

FAMILIES = ("slide-truck",)

# in, fusion's frame: first hole on the origin, top on z = 0, along +y
# half section, x >= 0. a point, or (point, arc center) where an arc gets to it. inner walls squared up off their 1 deg draft
INNER = [(0, 0), (0.2393, 0), ((0.2583, -0.0146), (0.2393, -0.0197)), (0.2847, -0.1132), ((0.2994, -0.1273), (0.3038, -0.1081)), ((0.3141, -0.1414), (0.2951, -0.1465)), (0.3427, -0.2483), ((0.3288, -0.2724), (0.3237, -0.2534)), (0.3096, -0.2775),
         ((0.2950, -0.2966), (0.3147, -0.2966)), (0.2950, -0.3100), ((0.2753, -0.3296), (0.2753, -0.3100)), (0.2309, -0.3296), ((0.2112, -0.3100), (0.2309, -0.3100)), (0.2112, -0.0707), ((0.1980, -0.0591), (0.1980, -0.0709)), (0, -0.0591)]
WALL, PLATE, RIBS, ENDS = 0.2112, -0.0591, -0.2035, -0.2336  # inner wall x, underside of the top, rib bottoms, end wall bottoms
RIB, BOSS, FILLET = 0.0206, 0.1516, 0.0118  # half a rib, boss radius, pocket corners
Y0, Y1, POCKET = -0.2475, 1.7475, (-0.1878, 1.6878)
CHAMFER = 0.016  # round both ends
HOLES = (0, 0.5, 1, 1.5)
HOLE = [(0.0827, 0.01), (0.0827, -0.0657), (0.0728, -0.0828), (0.0728, RIBS - 0.01)]  # 0.165 clearence, 30 deg in to 0.146 for the screw to bite


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


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox((x1 - x0) * IN, (y1 - y0) * IN, (z1 - z0) * IN, Vector(x0, y0, z0) * IN)


def inner():
    body = section(INNER).extrude(Vector(0, (Y1 - Y0) * IN, 0)).translated(Vector(0, Y0 * IN, 0)).fuse(box(-WALL, WALL, Y0, Y1, ENDS, PLATE))
    # pockets up under the top between the ribs and bosses, open below the ribs
    flat = Part.Face(Part.makePolygon([Vector(x, y, 0) * IN for x, y in ((-WALL, POCKET[0]), (WALL, POCKET[0]), (WALL, POCKET[1]), (-WALL, POCKET[1]), (-WALL, POCKET[0]))]))
    ribs = [box(-RIB, RIB, *POCKET, -1, 1)] + [box(-1, 1, y - RIB, y + RIB, -1, 1) for y in HOLES] + [Part.makeCylinder(BOSS * IN, 2 * IN, Vector(0, y, -1) * IN) for y in HOLES]
    cuts = [box(-WALL, WALL, *POCKET, ENDS - 0.01, RIBS)]
    for f in flat.cut(ribs).Faces:
        f = f.makeOffset2D(-FILLET * IN).makeOffset2D(FILLET * IN)
        cuts.append(f.translated(Vector(0, 0, (RIBS - 0.001) * IN)).extrude(Vector(0, 0, (PLATE - RIBS + 0.001) * IN)))
    body = body.cut(cuts)
    hole = Part.Face(Part.makePolygon([at(0, 0.01 * IN)] + [at(x * IN, z * IN) for x, z in HOLE] + [at(0, (RIBS - 0.01) * IN), at(0, 0.01 * IN)])).revolve(Vector(), Vector(0, 0, 1), 360)
    body = body.cut([hole.translated(Vector(0, y * IN, 0)) for y in HOLES]).removeSplitter()
    ends = [e for f in body.Faces if f.BoundBox.YLength < 1e-6 and min(abs(f.BoundBox.YMin - Y0 * IN), abs(f.BoundBox.YMin - Y1 * IN)) < 1e-6 for e in f.Edges]
    return body.makeChamfer(CHAMFER * IN, ends)


def make(part, cat):
    return inner()
