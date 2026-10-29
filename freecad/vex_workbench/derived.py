# parts made out of a vex step: screws at any length, shoulder screws, the thin nylock, other materials and colors
import functools

import Part
from FreeCAD import Placement, Rotation, Vector

from . import catalog
from .metal import IN

BIG = 10.0  # in, past anything
FLIP = Rotation(Vector(1, 0, 0), 180)


@functools.cache
def read(path):
    s = Part.read(path)
    s.scale(1 / IN)
    return s


def base(p, cat):
    step = next(s for s in catalog.step_parts(cat) if s["file"].rsplit(".", 1)[0] == p["base"])
    return read(str(catalog.step_path(step))).copy()


def slab(z0, z1):
    return Part.makeBox(2 * BIG, 2 * BIG, z1 - z0, Vector(-BIG, -BIG, z0))


def upright(s):
    # axis on z, big end (head, plain nut face) at z = 0, the rest up +z. the biggest round face is always on the axis, the torx lobes arent
    c = max((f.Surface for f in s.Faces if f.Surface.TypeId == "Part::GeomCylinder"), key=lambda c: c.Radius)
    s.translate(-c.Center)
    s.Placement = Placement(Vector(), Rotation(c.Axis, Vector(0, 0, 1))).multiply(s.Placement)
    b = s.optimalBoundingBox()  # plain BoundBox spills past the domed heads
    s.translate(Vector(0, 0, -b.ZMin))
    h = b.ZLength
    if s.common(slab(0, 0.02)).Volume < s.common(slab(h - 0.02, h)).Volume:
        s.Placement = Placement(Vector(0, 0, h), FLIP).multiply(s.Placement)
    return s, h


def screw(s, p):
    # base screw head + a stub of shank, its tip moved out to length, our shank between. under the head at z = 0, shank down -z
    s, h = upright(s)
    head, stub, tip = p["head"], 0.05, 0.1
    length, under = p["length"] if "shoulder" in p else (p["length"], 0)
    r = next(f.Surface.Radius for f in s.Faces if f.Surface.TypeId == "Part::GeomCylinder" and f.BoundBox.ZMin > head - 1e-6)
    top = s.common(slab(-1, head + stub))
    end = s.common(slab(h - tip, h + 1))
    end.translate(Vector(0, 0, length - (h - head)))
    out = [Part.makeCylinder(r, length - stub - tip, Vector(0, 0, head + stub)), end]
    if under:
        out.append(Part.makeCylinder(p["shoulder"] / 2, under, Vector(0, 0, head)))
    s = top.fuse(out).removeSplitter()
    s.Placement = Placement(Vector(0, 0, head), FLIP).multiply(s.Placement)
    return s


def thin(s, p):
    # shaved off the plain end, nylon side untoched. plain face at z = 0
    s, h = upright(s)
    s = s.common(slab(h - p["height"], h + 1))
    s.translate(Vector(0, 0, p["height"] - h))
    return s


FAMILIES = {
    "hex-screw": screw,
    "star-screw": screw,
    "shoulder-screw": screw,
    "thin-nylock": thin,
    "hex-nut": lambda s, p: upright(s)[0],  # same shape, other material
    "license-plate": lambda s, p: s,
}


def make(part, cat):
    s = FAMILIES[part["family"]](base(part["params"], cat), part["params"])
    s.scale(IN)
    return s
