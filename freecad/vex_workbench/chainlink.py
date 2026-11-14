# chain links, side plates joggled out so the next link's peg goes through this one's outer tab
import math

import Part
from FreeCAD import Vector

from .metal import IN, X

FAMILIES = ("chain-link",)


def side(p):
    # +x plate seen from above: inner tab round pin 0, outer tab round the next pin, step between with its two outside corners rounded
    a, (m0, m1), o, h = p["inner"], p["joggle"], p["outer"], p["height"] / 2
    s0, s1 = p["step"]  # y at the joggle
    k = math.tan(math.radians(p.get("slant", 0)))  # 3P's step edges lean out
    far = 2 * p["pitch"]
    pts = [(a, -far), (m0, -far), (m0, s0), (o, s0 + k * (o - m0)), (o, far), (m1, far), (m1, s1), (a, s1 - k * (m1 - a))]
    s = Part.Face(Part.makePolygon([Vector(x, y, -h) for x, y in pts + pts[:1]])).extrude(Vector(0, 0, 2 * h))
    corners = [Vector(*pts[3], 0), Vector(*pts[7], 0)]
    edges = [e for e in s.Edges if e.BoundBox.ZLength > h and any(Vector(e.Vertexes[0].X, e.Vertexes[0].Y, 0).distanceToPoint(c) < 1e-9 for c in corners)]
    return s.makeFillet(p["corner"], edges)


def outline(p):
    # side view, round both ends. 3P's pinches in between them to waist on two arcs tagent to the ends
    h, o, pitch = p["height"] / 2, p["outer"], p["pitch"]
    ends = [Part.makeCylinder(h, 2 * o, Vector(-o, y, 0), X) for y in (0, pitch)]
    if "waist" not in p:
        return ends[0].fuse([ends[1], Part.makeBox(2 * o, pitch, 2 * h, Vector(-o, 0, -h))])
    w = p["waist"] / 2
    r = (w * w + (pitch / 2) ** 2 - h * h) / (2 * (h - w))  # its center pitch / 2 along and r + w out, r + h from both pins
    ty, tz = pitch / 2 * h / (r + h), (r + w) * h / (r + h)  # where it touches the ends
    middle = Part.Face(Part.makePolygon([Vector(-o, y, z) for y, z in ((ty, tz), (pitch - ty, tz), (pitch - ty, -tz), (ty, -tz), (ty, tz))])).extrude(2 * o * X)
    return middle.cut([Part.makeCylinder(r, 2 * o, Vector(-o, pitch / 2, z), X) for z in (r + w, -r - w)]).fuse(ends)


def make(part, cat):
    p = {**part["params"], "pitch": cat["chain"][part["params"]["chain"]]["pitch"]}
    a, (m0, m1), o, pitch = p["inner"], p["joggle"], p["outer"], p["pitch"]
    plate = side(p)
    s = plate.fuse(plate.mirror(Vector(), X)).common(outline(p))
    peg = Part.makeCylinder(p["peg"] / 2, o - m0, Vector(m0, 0, 0), X)
    if "bevel" in p:
        # 3P's tip is that much shorter on the side away from the next pin, a lead in
        r = p["peg"] / 2
        peg = peg.cut(Part.Face(Part.makePolygon([Vector(o, r, -r), Vector(o - p["bevel"], -r, -r), Vector(o, -r, -r), Vector(o, r, -r)])).extrude(Vector(0, 0, 2 * r)))
    pegs = [peg, peg.mirror(Vector(), X)]
    holes = [Part.makeCylinder(p["hole"] / 2, o - m1, Vector(k * m1, pitch, 0), k * X) for k in (1, -1)]
    s = s.fuse([Part.makeCylinder(p["barrel"] / 2, 2 * a, Vector(-a, 0, 0), X)] + pegs).cut(holes).removeSplitter()
    s.scale(IN)
    return s
