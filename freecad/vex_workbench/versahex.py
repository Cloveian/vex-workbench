# plastic versahex adapters: a 1/2 hex with turned corners, a round flange on one end, 1/4 square bore through, 30 deg lathe chamfers
import math

import Part
from FreeCAD import Vector

from .metal import IN
from .stock import hexagon

FAMILIES = ("versahex-adapter",)
SLOPE = math.tan(math.radians(30))  # chamfer depth per width, 30 deg off the end face


def turned(flats, turn):
    # hex with its flats on y, corners turned down to a circle turn across
    return hexagon(flats).common(Part.Face(Part.Wire(Part.makeCircle(turn / 2)))).Faces[0]


def rounded(side, r):
    a = side / 2
    f = Part.Face(Part.makePolygon([Vector(-a, -a, 0), Vector(a, -a, 0), Vector(a, a, 0), Vector(-a, a, 0), Vector(-a, -a, 0)]))
    return f.makeOffset2D(-r).makeOffset2D(r)


def prism(face, z0, z1, bottom=0.0, top=0.0):
    # face pushed z0 -> z1, ends chamfered bottom / top across, negative flares out for a bore. ruled loft, so planes on the flats and cones on the round bits
    rings = [(face.makeOffset2D(-bottom), z0), (face, z0 + abs(bottom) * SLOPE)] if bottom else [(face, z0)]
    rings += [(face, z1 - abs(top) * SLOPE), (face.makeOffset2D(-top), z1)] if top else [(face, z1)]
    wires = []
    for f, z in rings:
        w = f.Faces[0].OuterWire.copy()
        w.translate(Vector(0, 0, z))
        wires.append(w)
    return Part.makeLoft(wires, True, True)


def make(part, cat):
    # centered on z = 0 end to end, flange up +z. worked in mm, makeOffset2D crashes on the 0.02 in chamfer
    p = {k: v * IN for k, v in part["params"].items() if isinstance(v, (int, float))}
    c, flange = p["chamfer"], p["flange_t"]
    z1 = (part["params"]["hex_long"][f"{part['params']['length']:g}"] * IN + flange) / 2
    body = prism(turned(p["hex"], p["turn"]), -z1, z1 - flange, bottom=c).fuse(prism(Part.Face(Part.Wire(Part.makeCircle(p["flange"] / 2))), z1 - flange, z1, top=c))
    return body.cut(prism(rounded(p["bore"], p["bore_round"]), -z1, z1, bottom=-c, top=-c)).removeSplitter()
