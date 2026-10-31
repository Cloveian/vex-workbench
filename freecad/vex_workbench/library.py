# vex parts in a document. one hidden source per variant, every placed copy is a plain App::Link to it
import functools
import json

import FreeCAD as App
import Part
from FreeCAD import Placement, Rotation, Vector

from . import catalog, derived, metal, stock

GROUP = "VexParts"
# family id -> make(part, cat)
GENERATORS = dict.fromkeys(metal.PROFILES, metal.make) | dict.fromkeys(stock.FAMILIES, stock.make) | dict.fromkeys(derived.FAMILIES, derived.make)
# mm, outside these it isnt a hole you'd put a screw or shaft through. the 11W motor step has 0.008-0.07 bits inside its screw holes
HOLE_MIN, HOLE_MAX = 0.1 * metal.IN, 0.5 * metal.IN
# mm, what a screw goes in. 8-32 round from the 5.5W 0.132 thread up to clearance, square like the metal's 0.182
ROUND = 0.125 * metal.IN, 0.2 * metal.IN
SQUARE = 0.17 * metal.IN, 0.2 * metal.IN
OUT = 0.001 * metal.IN  # mm, the open-to-outside ray starts this far off the face
MIN_THREAD = 0.25 * metal.IN  # mm, least a screw takes in a thread
SAME_HOLE = 0.25 * metal.IN  # mm, coaxial loops closer than this along the axis are one hole. 11W lead in to counterbore 0.087
NAMES = {"od": "OD", "n": "Holes"}  # toml key -> link property, where .title() reads wrong
CACHE = {}


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


def source(doc, part, bends=()):
    # one per variant and set of bends. a bent one keeps the straight one's VexName, thats what gets bought
    name, key = part["name"], json.dumps(list(bends)) if bends else ""
    for o in group(doc).Group:
        if getattr(o, "VexName", None) == name and getattr(o, "VexBends", "") == key:
            return o
    s, faces = shape(part)  # first, or no generator leaves an empty source behind
    for b in bends:
        s, faces = metal.fold(s, b), None  # vex's face colors dont line up anymore
    src = doc.addObject("App::Part", "VexPart")
    src.Label = f"{name} source" + (", bent" if bends else "")  # the placed copies get the plain name
    src.addProperty("App::PropertyString", "VexName", "VEX")
    src.VexName = name
    if key:
        src.addProperty("App::PropertyString", "VexBends", "VEX")
        src.VexBends = key
    solid = doc.addObject("Part::Feature", "Solid")
    solid.Shape = s
    p = part.get("params", {})
    if p.get("material") in cat()["density"]:
        src.addProperty("App::PropertyMass", "VexMass", "VEX")
        src.VexMass = f"{s.Volume * cat()['density'][p['material']] / 1000} g"  # mm3 * g/cm3
    color = cat()["colors"].get(p.get("color", p.get("material")))
    paint = "heads" in p and p["heads"].get(f"{p['length']:.3f}")
    if paint:
        # color coded star screws, just the head. it sits on z = 0
        faces = [tuple(paint) if f.BoundBox.ZMin > -1e-6 else tuple(color) for f in s.Faces]
    vo = solid.ViewObject  # none headless
    if vo and faces:
        vo.DiffuseColor = faces
    elif vo and color:
        vo.ShapeColor = tuple(color)
    if vo and "file" not in part:
        # the seam line down every full cylender drawn in its face's color so it doesnt show. Shaded would lose the spacer ends too
        seams = {}
        for f, c in zip(s.Faces, faces or [vo.ShapeColor] * len(s.Faces)):
            seams.update((e.hashCode(), c) for e in f.Edges if e.isSeam(f))
        if seams:
            vo.LineColorArray = [seams.get(e.hashCode(), vo.LineColor) for e in s.Edges]
    src.addObject(solid)
    group(doc).addObject(src)
    src.Visibility = False
    return src


def picks(family, part):
    # {property: label} that lands on part, the inverse of variant()
    mine = part["params"].items()
    return {prop: next(label(c) for c in choices if c.items() <= mine) for prop, choices in options(family)}


def place(doc, part, parent=None):
    # parent = the active assembly or part, if theres one
    # plain App::Link, assembly checks TypeId == "App::Link" exactly
    link = parent.newObject("App::Link", "Vex") if parent else doc.addObject("App::Link", "Vex")
    if "file" in part:
        link.addProperty("App::PropertyString", "VexStep", "VEX")
        link.VexStep = f"{part['folder']}/{part['file']}"
    else:
        family = index()[0][part["family"]]
        now = picks(family, part)
        for prop, choices in options(family):
            link.addProperty("App::PropertyEnumeration", prop, "VEX")
            setattr(link, prop, [label(c) for c in choices])
            setattr(link, prop, now[prop])
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


def roots(doc):
    # top of the tree. RootObjects drops a sub-assembly once something links to it, RootObjectsIgnoreLinks too once a link array's elements do
    # the elements look top level, and pass their array's Group through so theyd count twice
    return [o for o in doc.Objects if o.TypeId != "App::LinkElement" and o.getParentGroup() is None and o.getParentGeoFeatureGroup() is None]


def part_of(link):
    # catalog entry a placed copy's VEX props point at
    families, _, steps = index()
    if hasattr(link, "VexStep"):
        return steps[link.VexStep]
    family = families[link.VexFamily]
    return variant(family, {prop: getattr(link, prop) for prop, _ in options(family)})


def retarget(link):
    part = part_of(link)
    link.LinkedObject = source(link.Document, part, bends(link))
    link.Label = part["name"]


def bends(link):
    # the bends on one placed copy, metal.fold() dicts in order
    return json.loads(getattr(link, "VexBends", "") or "[]")


def rebend(link, done):
    # just this copy gets its own bent source, the straight one stays for the rest
    if not hasattr(link, "VexBends"):
        link.addProperty("App::PropertyString", "VexBends", "VEX")
        link.setPropertyStatus("VexBends", "Hidden")
    was = link.LinkedObject
    link.VexBends = json.dumps(done)
    retarget(link)
    # a bent source nothing links anymore, every redo of a bend would leave one
    if was != link.LinkedObject and getattr(was, "VexBends", "") and not [o for o in was.InList if o.isDerivedFrom("App::Link")]:
        for o in was.Group:
            link.Document.removeObject(o.Name)
        link.Document.removeObject(was.Name)


def cached(src, what):
    # what(shape) for a source, worked out once. a source never changes, a reused object name comes with another VexName or VexBends
    key = (src.Document.Uid, src.Name, src.VexName, getattr(src, "VexBends", ""), what)
    if key not in CACHE:
        CACHE[key] = what(Part.getShape(src))
    return CACHE[key]


def holes(shape):
    # (loop, center, outwerd normal) of every inner loop on a flat face. square, round, whatever
    out = []
    for f in shape.Faces:
        if f.Surface.TypeId != "Part::GeomPlane":
            continue
        n = f.normalAt(0, 0)
        outer = f.OuterWire  # once, its worked out again on every call
        for w in f.Wires:
            if not w.isSame(outer) and HOLE_MIN <= across(w) <= HOLE_MAX:
                out.append((w, w.BoundBox.Center, n))
    return out


def across(w):
    # widest a loop is, mm
    b = w.BoundBox
    return max(b.XLength, b.YLength, b.ZLength)


def ends(shape):
    # stock parts run up z from 0 on the axis
    h = shape.optimalBoundingBox().ZMax
    return [(Vector(), Vector(0, 0, -1)), (Vector(0, 0, h), Vector(0, 0, 1))]


def boxed(shape):
    # faces + their bound boxes for hits(), ~35 ms on a 5x25 plate
    return [(f, f.BoundBox) for f in shape.Faces]


def hits(faces, start, d, far):
    # distences along d from start where it crosses one of faces (from boxed), sorted. works on step shells with no solid
    e = Part.makeLine(start, start + d * far)
    eb = e.BoundBox
    out = []
    for f, b in faces:
        if b.intersect(eb):
            out += [(v.Point - start).Length for v in f.section(e).Vertexes]
    out.sort()
    # an edge or seam crossing shows up once per face
    return [t for i, t in enumerate(out) if i == 0 or t - out[i - 1] > 1e-6]


def square_to(n):
    # x and y square to n, x along the length if it can
    x = Vector(1, 0, 0) - n * n.x
    if x.Length < 1e-6:
        x = Vector(0, 1, 0) - n * n.y
    x.normalize()
    return x, n.cross(x)


def down(faces, start, z, r, far):
    # first hit of 5 rays down -z from start, one on the axis and 4 at r off it. None where it opens into nothing
    x, y = square_to(z)
    return [next(iter(hits(faces, start + v * r, -z, far)), None) for v in (Vector(), x, -x, y, -y)]


def screwable(w):
    # 8-32 sized round loop, or a square one. channel corners are rounded, plate ones arent
    sides = [e.Length for e in w.Edges if e.Curve.TypeId == "Part::GeomLine"]
    radii = [e.Curve.Radius for e in w.Edges if e.Curve.TypeId == "Part::GeomCircle"]
    if len(sides) + len(radii) < len(w.Edges) or any(xs and max(xs) - min(xs) > 1e-3 for xs in (sides, radii)):
        return False
    if not sides:
        return ROUND[0] <= 2 * radii[0] <= ROUND[1]
    return len(sides) == 4 and len(radii) in (0, 4) and SQUARE[0] <= sides[0] + 2 * sum(radii[:1]) <= SQUARE[1]


def screw_holes(link):
    # centers of the holes a screw goes in from outside, link coords. shafts and standoffs by their ends
    src = link.LinkedObject
    if getattr(link, "VexFamily", None) in stock.FAMILIES:
        return [c for c, _ in ends(Part.getShape(src))]
    # kept on the source, the 11W's rays take a while
    if not hasattr(src, "VexScrewHoles"):
        src.addProperty("App::PropertyVectorList", "VexScrewHoles", "VEX")
        src.setPropertyStatus("VexScrewHoles", "Hidden")
        src.VexScrewHoles = outermost(Part.getShape(src), hasattr(link, "VexStep"))
    return list(src.VexScrewHoles)


def outermost(shape, rays):
    # one per hole and side. rays=True drops loops facing into the part, the 11W step has those. generated metal is all through holes
    far = shape.BoundBox.DiagonalLength
    faces = boxed(shape) if rays else []
    kept = {}  # axis and side -> centers
    for w, c, n in sorted(holes(shape), key=lambda h: -h[1].dot(h[2])):
        if not screwable(w) or rays and hits(faces, c + n * OUT, n, far):
            continue
        if rays:
            # most of the rays down it stopping short means somethings in it, the 11W's case screw heads are 0.05 down
            half = across(w) / 2
            short = [t for t in down(faces, c - n * OUT, n, half / 2, far) if t is not None and t < MIN_THREAD]
            if len(short) >= 3:
                continue
        key = tuple(round(v, 2) for v in (*n, *(c - n * c.dot(n))))
        # the 5.5W has its thread at the face and a wider loop 0.042 under it. a channel's other flange is its own hole
        if all(o.dot(n) - c.dot(n) > SAME_HOLE for o in kept.get(key, [])):
            kept.setdefault(key, []).append(c)
    return [c for cs in kept.values() for c in cs]


def hole_frame(link, point):
    # LCS on the hole from hole_at, z out of the face, x along the length if it can
    # it goes in the source so every copy has it
    center, n = hole_at(link, point)
    x, y = square_to(n)
    return frame(link, Placement(center, Rotation(x, y, n, "ZXY")))


def hole_at(link, point):
    # (center, outward normal) of the hole nearest point, link coords
    src = link.LinkedObject
    if getattr(link, "VexFamily", None) in stock.FAMILIES:
        # shafts have no loop to find, the end nearer the click
        center, n = min(ends(Part.getShape(src)), key=lambda e: (e[0] - point).Length)
    else:
        found = cached(src, holes)
        if not found:
            raise ValueError(f"no holes on {link.Label}")
        # a hole point is right on a center. coaxal loops a few thou deeper can be nearer than its own edge
        exact = [h for h in found if (h[1] - point).Length < 1e-6]
        # nearest loop, the motor's vents sit closer to a screw hole's edge than its own center does
        v = Part.Vertex(point)
        near = [h for h in found if (h[1] - point).Length < HOLE_MAX] or found
        _, center, n = exact[0] if exact else min(near, key=lambda h: h[0].distToShape(v)[0])
    return center, n


def frame(link, plc, name="Hole"):
    # LCS at plc (link coords) in the source, the one already there if theres one
    src = link.LinkedObject
    for o in src.Group:
        if o.TypeId == "App::LocalCoordinateSystem" and o.Placement.isSame(plc, 1e-6):
            return o
    lcs = link.Document.addObject("App::LocalCoordinateSystem", name)
    lcs.Placement = plc
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
