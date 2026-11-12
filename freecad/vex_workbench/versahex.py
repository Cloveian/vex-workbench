# versahex adapters: a 1/2 hex with turned corners, a round flange on one end, 1/4 square bore through, lathe chamfers. the 0.5 one has two slots under its flange
import math

import Part
from FreeCAD import Vector

from .metal import IN, square
from .stock import section

FAMILIES = ("versahex-adapter", "versahex-adapter-slotted")


def prism(face, z0, z1, bottom=0.0, top=0.0, deg=30):
    # face pushed z0 -> z1, ends chamfered bottom / top across at deg off the end face, negative flares out for a bore. ruled loft, so planes on the flats and cones on the round bits
    slope = math.tan(math.radians(deg))
    rings = [(face.makeOffset2D(-bottom), z0), (face, z0 + abs(bottom) * slope)] if bottom else [(face, z0)]
    rings += [(face, z1 - abs(top) * slope), (face.makeOffset2D(-top), z1)] if top else [(face, z1)]
    wires = []
    for f, z in rings:
        w = f.Faces[0].OuterWire.copy()
        w.translate(Vector(0, 0, z))
        wires.append(w)
    return Part.makeLoft(wires, True, True)


def make(part, cat):
    # centered on z = 0 end to end, flange up +z. worked in mm, makeOffset2D crashes on the 0.02 in chamfer
    params = part["params"]
    p = {k: v * IN for k, v in params.items() if isinstance(v, (int, float)) and k != "deg"}
    c, flange, deg = p["chamfer"], p["flange_t"], params["deg"]
    z1 = (params["hex_long"][f"{params['length']:g}"] * IN + flange) / 2
    disc = Part.Face(Part.Wire(Part.makeCircle(p["flange"] / 2)))
    body = prism(section(p), -z1, z1 - flange, bottom=c, deg=deg).fuse(prism(disc, z1 - flange, z1, top=p.get("flange_top", 0), deg=deg))
    if "slot" in params:
        # out through the rim eather side, floor corners and mouth edges rounded
        w, deep, r = (params["slot"][k] * IN for k in ("width", "deep", "round"))
        floor, under = z1 - flange + deep, z1 - flange
        cuts = []
        for k in (1, -1):
            b = Part.makeBox(w, p["flange"], deep + 1, Vector(-w / 2, p["hex"] / 2 if k > 0 else -p["hex"] / 2 - p["flange"], under - 1))  # from the hex flat out
            cuts.append(b.makeFillet(r, [e for e in b.Edges if e.BoundBox.YLength > 1 and abs(e.BoundBox.ZMin - floor) < 1e-6]))
        body = body.cut(cuts)
        mouth = [e for e in body.Edges if e.BoundBox.XLength < 1e-6 and e.BoundBox.ZLength < 1e-6 and abs(e.BoundBox.ZMin - under) < 1e-6 and abs(abs(e.BoundBox.XMin) - w / 2) < 1e-6]
        body = body.makeFillet(r, mouth)
    return body.cut(prism(square(p["bore"], p["bore_round"]), -z1, z1, bottom=-c, top=-c, deg=deg)).removeSplitter()
