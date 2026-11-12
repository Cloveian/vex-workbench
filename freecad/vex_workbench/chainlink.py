# chain links, side plates joggled out so the next link's peg goes through this one's outer tab
import Part
from FreeCAD import Vector

from .metal import IN, X

FAMILIES = ("chain-link",)


def side(p):
    # +x plate seen from above: inner tab round pin 0, outer tab round the next pin, step between with its two outside corners rounded
    a, m, o, h = p["inner"], p["joggle"], p["outer"], p["height"] / 2
    s0, s1 = p["step"]
    far = 2 * p["pitch"]
    pts = [(a, -far), (m, -far), (m, s0), (o, s0), (o, far), (m, far), (m, s1), (a, s1)]
    s = Part.Face(Part.makePolygon([Vector(x, y, -h) for x, y in pts + pts[:1]])).extrude(Vector(0, 0, 2 * h))
    corners = [Vector(o, s0, 0), Vector(a, s1, 0)]
    edges = [e for e in s.Edges if e.BoundBox.ZLength > h and any(Vector(e.Vertexes[0].X, e.Vertexes[0].Y, 0).distanceToPoint(c) < 1e-9 for c in corners)]
    return s.makeFillet(p["corner"], edges)


def make(part, cat):
    p = {**part["params"], "pitch": cat["chain"][part["params"]["chain"]]["pitch"]}
    a, m, o, h, pitch = p["inner"], p["joggle"], p["outer"], p["height"] / 2, p["pitch"]
    # side view, round both ends
    end = Part.Face(Part.Wire(Part.makeCircle(h, Vector(-o, 0, 0), X))).extrude(Vector(2 * o, 0, 0))
    other = end.copy()
    other.translate(Vector(0, pitch, 0))
    outline = end.fuse([other, Part.makeBox(2 * o, pitch, 2 * h, Vector(-o, 0, -h))])
    plate = side(p)
    s = plate.fuse(plate.mirror(Vector(), X)).common(outline)
    pegs = [Part.makeCylinder(p["peg"] / 2, o - m, Vector(k * m, 0, 0), k * X) for k in (1, -1)]
    holes = [Part.makeCylinder(p["hole"] / 2, o - m, Vector(k * m, pitch, 0), k * X) for k in (1, -1)]
    s = s.fuse([Part.makeCylinder(p["barrel"] / 2, 2 * a, Vector(-a, 0, 0), X)] + pegs).cut(holes).removeSplitter()
    s.scale(IN)
    return s
