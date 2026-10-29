# vex parts in a document. one hidden source per variant, every placed copy is a plain App::Link to it
import functools

import FreeCAD as App
import Part
from FreeCAD import Placement, Rotation, Vector

from . import catalog, derived, metal, stock

GROUP = "VexParts"
# family id -> make(part, cat)
GENERATORS = dict.fromkeys(metal.PROFILES, metal.make) | dict.fromkeys(stock.FAMILIES, stock.make) | dict.fromkeys(derived.FAMILIES, derived.make)
HOLE_MAX = 0.5 * metal.IN  # mm, anything bigger isnt a hole you'd put a screw or shaft through
NAMES = {"od": "OD", "n": "Holes"}  # toml key -> link property, where .title() reads wrong


@functools.cache
def cat():
    return catalog.load()


@functools.cache
def index():
    c = cat()
    families = {f["id"]: f for f in c["family"]}
    generated = {p["name"]: p for p in catalog.generated(c)}
    steps = {f"{p['folder']}/{p['file']}": p for p in catalog.step_parts(c)}
    return families, generated, steps


def label(choice):
    vals = []
    for v in choice.values():
        if isinstance(v, list):
            vals += v  # pairs (the shoulder screws) read flat, "0.29, 0.09"
        elif not isinstance(v, bool):
            vals.append(v)
    return ", ".join(f"{v:g}" if isinstance(v, float) else str(v) for v in vals)


def options(family):
    # the link properties and browser combos. rows all go under "Size"
    out = []
    for key, choices in catalog.axes(family):
        if len(choices) > 1:
            rows = any(set(c) != {key} for c in choices)
            out.append(("Size" if rows else NAMES.get(key, key.title()), choices))
    return out


def shape(part):
    if "file" in part:
        path = str(catalog.step_path(part))
        return colored(path) if App.GuiUp else (Part.read(path), None)
    if part["family"] in GENERATORS:
        return GENERATORS[part["family"]](part, cat()), None
    raise ValueError(f"no generator for {part['family']} yet")


def colored(path):
    # vex's own colors only come through ImportGui (Import.insert greys every face), which splits the step into peices
    import ImportGui
    active = App.ActiveDocument
    tmp = App.newDocument("VexImport", hidden=True)
    try:
        ImportGui.insert(path, tmp.Name)
        shapes, colors = [], []
        for o in tmp.Objects:
            if o.TypeId == "Part::Feature":
                s = o.Shape.copy()
                s.Placement = o.getGlobalPlacement()
                dc = o.ViewObject.DiffuseColor
                colors += dc if len(dc) == len(s.Faces) else dc[:1] * len(s.Faces)
                shapes.append(s)
        return Part.makeCompound(shapes), colors
    finally:
        App.closeDocument(tmp.Name)
        if active:
            App.setActiveDocument(active.Name)


def group(doc):
    g = doc.getObject(GROUP)
    if g is None:
        g = doc.addObject("App::DocumentObjectGroup", GROUP)
        g.Label = "VEX parts"
    return g


def source(doc, part):
    name = part["name"]
    for o in group(doc).Group:
        if getattr(o, "VexName", None) == name:
            return o
    s, faces = shape(part)  # first, or no generator leaves an empty source behind
    src = doc.addObject("App::Part", "VexPart")
    src.Label = f"{name} source"  # the placed copies get the plain name
    src.addProperty("App::PropertyString", "VexName", "VEX")
    src.VexName = name
    solid = doc.addObject("Part::Feature", "Solid")
    solid.Shape = s
    p = part.get("params", {})
    if p.get("material") in cat()["density"]:
        src.addProperty("App::PropertyMass", "VexMass", "VEX")
        src.VexMass = f"{s.Volume * cat()['density'][p['material']] / 1000} g"  # mm3 * g/cm3
    color = cat()["colors"].get(p.get("color", p.get("material")))
    vo = solid.ViewObject  # none headless
    if vo and faces:
        vo.DiffuseColor = faces
    elif vo and color:
        vo.ShapeColor = tuple(color)
    src.addObject(solid)
    group(doc).addObject(src)
    src.Visibility = False
    return src


def place(doc, part, parent=None):
    # parent = the active assembly or part, if theres one
    # plain App::Link, assembly checks TypeId == "App::Link" exactly
    link = parent.newObject("App::Link", "Vex") if parent else doc.addObject("App::Link", "Vex")
    if "file" in part:
        link.addProperty("App::PropertyString", "VexStep", "VEX")
        link.VexStep = f"{part['folder']}/{part['file']}"
    else:
        family = index()[0][part["family"]]
        for prop, choices in options(family):
            labels = [label(c) for c in choices]
            link.addProperty("App::PropertyEnumeration", prop, "VEX")
            setattr(link, prop, labels)
            now = next(lb for c, lb in zip(choices, labels) if c.items() <= part["params"].items())
            setattr(link, prop, now)
        # last, the observer ignores links without it
        link.addProperty("App::PropertyString", "VexFamily", "VEX")
        link.VexFamily = part["family"]
        link.setPropertyStatus("VexFamily", "ReadOnly")
    retarget(link)
    return link


def variant(family, picked):
    # picked = {property: label}, from a link or the browser
    params = {}
    for key, choices in catalog.axes(family):
        if len(choices) == 1:
            params.update(choices[0])
    for prop, choices in options(family):
        labels = [label(c) for c in choices]
        params.update(choices[labels.index(picked[prop])])
    return index()[1][family["name"].format(**params)]


def retarget(link):
    families, _, steps = index()
    if hasattr(link, "VexStep"):
        part = steps[link.VexStep]
    else:
        family = families[link.VexFamily]
        part = variant(family, {prop: getattr(link, prop) for prop, _ in options(family)})
    link.LinkedObject = source(link.Document, part)
    link.Label = part["name"]


def holes(shape):
    # (loop, center, outwerd normal) of every inner loop on a flat face. square, round, whatever
    out = []
    for f in shape.Faces:
        if f.Surface.TypeId != "Part::GeomPlane":
            continue
        n = f.normalAt(0, 0)
        for w in f.Wires:
            b = w.BoundBox
            if not w.isSame(f.OuterWire) and max(b.XLength, b.YLength, b.ZLength) <= HOLE_MAX:
                out.append((w, b.Center, n))
    return out


def hole_frame(link, point):
    # LCS on the exact center of the hole nearset point (link coords), z out of the face, x along the length if it can
    # it goes in the source so every copy has it
    src = link.LinkedObject
    shape = Part.getShape(src)
    if getattr(link, "VexFamily", None) in stock.FAMILIES:
        # shafts have no loop to find. stock parts run up z from 0 on the axis, so the end nearer the click
        h = shape.optimalBoundingBox().ZMax
        center, n = (Vector(0, 0, h), Vector(0, 0, 1)) if point.z > h / 2 else (Vector(), Vector(0, 0, -1))
    else:
        found = holes(shape)
        if not found:
            raise ValueError(f"no holes on {link.Label}")
        # nearest loop, the motor's vents sit closer to a screw hole's edge than its own center does
        v = Part.Vertex(point)
        near = [h for h in found if (h[1] - point).Length < HOLE_MAX] or found
        _, center, n = min(near, key=lambda h: h[0].distToShape(v)[0])
    for o in src.Group:
        if o.TypeId == "App::LocalCoordinateSystem" and (o.Placement.Base - center).Length < 1e-6 \
                and (o.Placement.Rotation.multVec(Vector(0, 0, 1)) - n).Length < 1e-6:
            return o
    x = Vector(1, 0, 0) - n * n.x
    if x.Length < 1e-6:
        x = Vector(0, 1, 0) - n * n.y
    lcs = link.Document.addObject("App::LocalCoordinateSystem", "Hole")
    lcs.Placement = Placement(center, Rotation(x, n.cross(x), n, "ZXY"))
    src.addObject(lcs)
    return lcs


class Observer:
    # a VEX param changed on a placed copy -> point it at that variant
    def slotChangedObject(self, obj, prop):
        doc = obj.Document
        # undo / redo puts LinkedObject back itself, retargetting made a second source
        if doc.Restoring or doc.Transacting or not hasattr(obj, "VexFamily"):
            return
        if prop != "VexFamily" and obj.getGroupOfProperty(prop) == "VEX":
            retarget(obj)
