# linear slide rail: a bent channel with its walls leaning in, square holes down the base, wall tops chamferd off at the ends for the truck
import math

import FreeCAD as App
import Part
from FreeCAD import Vector

from .metal import BIG, IN, square

FAMILIES = ("linear-rail",)


def at(x, z):
    return Vector(x, 0, z)


def arc(c, r, a0, a1):
    # a0 to a1 through their average, rad. pick them so thats the side you want
    p = [at(c[0] + r * math.cos(a), c[1] + r * math.sin(a)) for a in (a0, (a0 + a1) / 2, a1)]
    return Part.Arc(*p).toShape()


def section(p):
    # x across, z up off the base. bend centers at +-half, walls leaning in by lean deg, squared off where the outside reaches height
    half, t, ri, lean, top = p["across"] / 2, p["thickness"], p["bend"], math.radians(p["lean"]), p["height"]
    ro = ri + t
    n = (math.cos(lean), math.sin(lean))  # out of the right wall, where its bend ends
    up = (-math.sin(lean), math.cos(lean))  # up the right wall
    outer = (half + ro * n[0], ro + ro * n[1])
    top_out = (outer[0] + up[0] * (top - outer[1]) / up[1], top)
    top_in = (top_out[0] - t * n[0], top_out[1] - t * n[1])
    inner = (half + ri * n[0], ro + ri * n[1])
    mirror = lambda q: (-q[0], q[1])
    line = lambda a, b: Part.makeLine(at(*a), at(*b))
    c, d = (half, ro), (-half, ro)
    edges = [line((-half, 0), (half, 0)), arc(c, ro, -math.pi / 2, lean), line(outer, top_out), line(top_out, top_in), line(top_in, inner), arc(c, ri, lean, -math.pi / 2),
             line((half, t), (-half, t)), arc(d, ri, 3 * math.pi / 2, math.pi - lean), line(mirror(inner), mirror(top_in)), line(mirror(top_in), mirror(top_out)),
             line(mirror(top_out), mirror(outer)), arc(d, ro, math.pi - lean, 3 * math.pi / 2)]
    return Part.Face(Part.Wire(Part.__sortEdges__(edges))), top_out[0]


def make(part, cat):
    # worked in mm, along +y from 0. holes off the metal's grid
    p = {k: v * IN for k, v in part["params"].items() if isinstance(v, (int, float)) and k not in ("lean", "holes")}
    p["lean"] = part["params"]["lean"]
    g = cat["grid"]
    length = part["params"]["holes"] * g["pitch"] * IN
    face, corner = section(p)
    s = face.extrude(Vector(0, length, 0))
    t = p["thickness"]
    hole = square(g["hole"] * IN, g["round"] * IN).extrude(Vector(0, 0, 3 * t))
    cuts = [hole.translated(Vector(0, (g["end"] + g["pitch"] * i) * IN, -t)) for i in range(part["params"]["holes"])]
    # 45 deg off each wall top at both ends. each cutter leans with its wall, kept to that side or it bites the other wall too
    lean = math.radians(p["lean"])
    for k in (1, -1):
        up = Vector(-k * math.sin(lean), 0, math.cos(lean))
        side = Part.makeBox(BIG, 3 * BIG, BIG, Vector(0 if k > 0 else -BIG, -BIG, -BIG / 2))
        for y0, dy in ((0, 1), (length, -1)):
            m = (up + Vector(0, -dy, 0)).normalize()
            cutter = Part.makeBox(2 * BIG, 2 * BIG, BIG, Vector(-BIG, -BIG, 0))
            cutter.Placement = App.Placement(Vector(k * corner, y0 + dy * p["chamfer"], p["height"]), App.Rotation(Vector(0, 0, 1), m))
            cuts.append(cutter.common(side))
    return s.cut(cuts).removeSplitter()
