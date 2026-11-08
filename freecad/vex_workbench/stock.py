# shafts, standoffs, spacers, washers, the plain nuts: one section pushed along z, ends turned like on a lathe, bore down the middle
import math

import Part
from FreeCAD import Vector

from .metal import EPS, IN, square

FAMILIES = ("ls-shaft", "hs-shaft", "pitch-shaft", "standoff", "extra-low-nut", "flange-nut", "nylock-flange-nut", "piston-nut", "spacer", "washer")
O, Z = Vector(0, 0, 0), Vector(0, 0, 1)


def section(p):
    if "size" in p:
        # square shaft, corners turned down to a circle and / or rounded
        f = square(p["size"], 0)
        if "turn" in p:
            f = f.common(Part.Face(Part.Wire(Part.makeCircle(p["turn"] / 2)))).Faces[0]
        if "round" in p:
            f = f.makeOffset2D(-p["round"]).makeOffset2D(p["round"])
        return f
    if "hex" in p:
        r = p["hex"] / 3**0.5  # across flats -> across corners / 2
        corners = [Vector(r * math.cos(math.pi / 3 * i), r * math.sin(math.pi / 3 * i), 0) for i in range(7)]
        return Part.Face(Part.makePolygon(corners))
    return Part.Face(Part.Wire(Part.makeCircle(p["od"] / 2)))


def blank(h, end):
    # revovled round bar, each end turned along an arc of radius r centered (x out, z in from the end)
    x, z, r = end["x"], end["z"], end["r"]
    a0 = -math.asin(z / r)  # where the arc meets the end face. -90 deg when its tangent to it

    def arc(face, sign):
        def pt(a):
            return Vector(x + r * math.cos(a), 0, face + sign * (z + r * math.sin(a)))
        return Part.Arc(pt(a0), pt(a0 / 2), pt(0)), pt(a0), pt(0)

    lo, lo0, lo1 = arc(0, 1)
    hi, hi0, hi1 = arc(h, -1)
    top = Vector(0, 0, h)
    edges = [Part.LineSegment(O, lo0), lo, Part.LineSegment(lo1, hi1), hi, Part.LineSegment(hi0, top), Part.LineSegment(top, O)]
    face = Part.Face(Part.Wire([e.toShape() for e in edges]))
    return face.revolve(O, Z, 360)


def crown(h, c):
    # nylock dome on the hex top at h, flat out to r then a qaurter round R down onto it
    r, R = c["r"], c["R"]
    pts = [Vector(0, 0, h), Vector(r + R, 0, h), Vector(r, 0, h + R), Vector(0, 0, h + R)]
    a = math.radians(45)
    arc = Part.Arc(pts[1], Vector(r + R * math.cos(a), 0, h + R * math.sin(a)), pts[2])
    edges = [Part.LineSegment(pts[0], pts[1]), arc, Part.LineSegment(pts[2], pts[3]), Part.LineSegment(pts[3], pts[0])]
    return Part.Face(Part.Wire([e.toShape() for e in edges])).revolve(O, Z, 360)


def bores(p, h):
    # through, or blind `tap` deep from each end on long standoffs. `sink` = 45 deg chamfer at the mouth
    r, sink, deep = p["bore"] / 2, p.get("sink", 0), p.get("tap", h)
    if h <= 2 * deep:
        out = [Part.makeCylinder(r, h + 2 * EPS, Vector(0, 0, -EPS))]
    else:
        out = [Part.makeCylinder(r, deep + EPS, Vector(0, 0, -EPS)), Part.makeCylinder(r, deep + EPS, Vector(0, 0, h - deep))]
    if sink:
        out += [Part.makeCone(r + sink + EPS, r, sink + EPS, Vector(0, 0, -EPS)),
                Part.makeCone(r + sink + EPS, r, sink + EPS, Vector(0, 0, h + EPS), -Z)]
    return out


def height(p, g):
    # pitch shafts are n holes minus a bit so they fit between
    if "n" in p:
        return p["n"] * g["pitch"] - p["short"]
    return p.get("length", p.get("thickness", p.get("height")))


def make(part, cat):
    p = part["params"]
    h = height(p, cat["grid"])
    solid = section(p).extrude(Z * h)
    if "end" in p:
        solid = solid.common(blank(h, p["end"]))
    if "collar" in p:
        solid = solid.fuse(Part.makeCylinder(p["collar"] / 2, p["lip"])).removeSplitter()
    if "crown" in p:
        c = p["crown"]
        solid = solid.fuse(crown(h, c)).removeSplitter()
        h += c["R"]
        solid = solid.cut(Part.makeCylinder(c["mouth"] / 2, c["deep"] + EPS, Vector(0, 0, h - c["deep"])))
    if "bore" in p:
        solid = solid.cut(bores(p, h))
    solid.scale(IN)
    return solid
