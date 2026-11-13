# vex parts in a document. one hidden source per variant, every placed copy is a plain App::Link to it
import collections
import functools
import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Part
from FreeCAD import Placement, Rotation, Vector

from . import catalog, chainlink, derived, flexwheel, metal, rail, ratchet, slide, stock, versahex, versahub

GROUP = "VexParts"
# family id -> make(part, cat)
GENERATORS = dict.fromkeys(metal.PROFILES, metal.make)
for m in (stock, derived, chainlink, flexwheel, versahex, versahub, rail, slide, ratchet):
    GENERATORS |= dict.fromkeys(m.FAMILIES, m.make)
# mm, outside these it isnt a hole you'd put a screw or shaft through. the 11W motor step has 0.008-0.07 bits inside its screw holes
HOLE_MIN, HOLE_MAX = 0.1 * metal.IN, 0.6 * metal.IN  # a 1/2 hex is 0.577 across its corners
# mm, what a screw goes in. 8-32 round from the 5.5W 0.132 thread up to clearance, square like the metal's 0.182
ROUND = 0.125 * metal.IN, 0.2 * metal.IN
SQUARE = 0.17 * metal.IN, 0.2 * metal.IN
SHAFT = [(0.12 * metal.IN, 0.14 * metal.IN), (0.245 * metal.IN, 0.3 * metal.IN)]  # mm, LS 1/8 and HS 1/4 shaft holes on steps, and the lockbar's dead on 0.25
HEX = [(0.37 * metal.IN, 0.38 * metal.IN), (0.495 * metal.IN, 0.505 * metal.IN)]  # mm across the flats, 3/8 hex bores (the small flex wheels) and 1/2 (versahub)
OUT = 0.001 * metal.IN  # mm, the open-to-outside ray starts this far off the face
MIN_THREAD = 0.25 * metal.IN  # mm, least a screw takes in a thread
SAME_HOLE = 0.25 * metal.IN  # mm, coaxial loops closer than this along the axis are one hole. 11W lead in to counterbore 0.087
ON_AXIS = 0.01  # mm, loop centers this close to a hole's axis are on it
WALL_PROBE = 0.03 * metal.IN  # mm past a hole's edge, into the metal round it. square holes are 0.318 apart
NAMES = {"od": "OD", "n": "Holes"}  # toml key -> link property, where .title() reads wrong
CACHE = {}
BREPS = Path(App.getUserCachePath()) / "VexWorkbench"  # read steps as brep + face colors, gone stale ones just sit there
BREPS_VERSION = 1  # bump when colored() reads a step *dih*frently, old cached ones get skipped
DOTS_VERSION = 1  # same for outermost()
BUSY = set()  # (doc, link) names getting their menu boxes refilled


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


@functools.cache
def menus():
    # id -> [[menu]], just the parts whose step is here, each with its folder/file key
    steps = index()[2]
    named = {p["name"]: k for k, p in steps.items()}
    out = {}
    for m in cat()["menu"]:
        here = [dict(p, key=named[p["part"]]) for p in m["parts"]]
        out[m["id"]] = dict(m, parts=[p for p in here if catalog.has(steps[p["key"]])])
    return out


def label(choice):
    vals = []
    for v in choice.values():
        if isinstance(v, list):
            vals += v  # pairs (the shoulder screws) read flat, "0.29, 0.09"
        elif not isinstance(v, (bool, dict)):  # a dict is a row's own numbers, the 3x c-channel's
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
    if "file" in part and App.GuiUp:
        return remembered(part)
    if "file" in part:
        with catalog.step_file(part) as path:
            return Part.read(str(path)), None
    if part["family"] in GENERATORS:
        return GENERATORS[part["family"]](part, cat()), None
    raise ValueError(f"no generator for {part['family']} yet")


def kept(part):
    # file name in BREPS for a step, without the extension
    read = catalog.stored(part)
    st = read.stat()
    return hashlib.sha1(f"{BREPS_VERSION}|{read}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:16]


def remembered(part):
    # a step read once and kept as a brep, the 1" star drive coupler is 26 s as a step and 0.01 s as a brep. brep keeps the face order so the colors still line up
    name = kept(part)
    brep, colors_file = BREPS / f"{name}.brep", BREPS / f"{name}.json"
    if colors_file.is_file() and brep.is_file():  # json written last, a half written brep never has one
        s = Part.Shape()
        s.read(str(brep))
        colors = json.loads(colors_file.read_text())
        return s, colors and [tuple(c) for c in colors]
    with catalog.step_file(part) as path:
        s, colors = colored(str(path))
    try:
        BREPS.mkdir(parents=True, exist_ok=True)
        s.exportBrep(f"{brep}.part")
        os.replace(f"{brep}.part", brep)
        Path(f"{colors_file}.part").write_text(json.dumps(colors))
        os.replace(f"{colors_file}.part", colors_file)
    except OSError as e:
        App.Console.PrintWarning(f"VEX: couldn't cache {part['file']} ({e}), it reads from the step every time\n")
    return s, colors


def colored(path):
    # vex's own colors only come through ImportGui (Import.insert greys every face), which splits the step into peices
    if b"COLOUR" not in Path(path).read_bytes():  # COLOUR_RGB or a named DRAUGHTING_PRE_DEFINED_COLOUR
        return Part.read(path), None  # no colors at all, source() paints it by material
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


def stood_in(faces, color):
    # vex's stand-in plastic faces get the part's color, a step thats all one color gets it all over (None)
    if len(set(faces)) == 1:
        return None
    stand = cat()["stand_in"].values()
    out = []
    for f in faces:
        vex = any(max(abs(a - b) for a, b in zip(f, c)) < 0.01 for c in stand)  # read back as floats off the step
        out.append(tuple(color) if vex else f)
    return out


def painted(s, paint, faces):
    # face colors for a wheel off its hub and rim, over the step's own faces (or None)
    b = Part.makeCompound(s.Vertexes).BoundBox  # BoundBox on the legacy wheels' splines is an inch off, optimalBoundingBox is 20 s on an omni
    size = [b.XLength, b.YLength, b.ZLength]
    k = size.index(min(size))  # thin way through it = the axle
    axis = Vector(*(float(i == k) for i in range(3)))
    line = Part.makeLine(b.Center - axis * size[k], b.Center + axis * size[k])
    pieces = list(s.Solids)
    # keyed by s.Faces number. hashCode only goes to 2^31, the 9000 faces on an omni share one in ~2% of loads
    inside = {s.findSubShape(f)[1] for x in pieces for f in x.Faces}
    pieces += [sh for sh in s.Shells if s.findSubShape(sh.Faces[0])[1] not in inside]  # the 2" mecanum has 2 loose ones, 4000 specks of faces
    # alike by topology and total edge length, Volume on the 2.75 omni's splines takes ~10 s
    kinds = [(len(x.Faces), len(x.Edges), len(x.Vertexes), round(x.Length, 1)) for x in pieces]
    copies = collections.Counter(kinds)
    rgb = {}
    for x, kind in zip(pieces, kinds):
        # rollers come 3+ alike, a tread is one piece but out past half the raduis. mecanum rollers lean in too far for that
        rim = copies[kind] >= 3 or x.distToShape(line)[0] > max(size) / 4
        c = tuple(cat()["colors"][paint["rim" if rim else "hub"]])
        rgb.update((s.findSubShape(f)[1], c) for f in x.Faces)
    faces = faces or [(0.8, 0.8, 0.8)] * len(s.Faces)
    return [rgb.get(i, old) for i, old in enumerate(faces, 1)]


def group(doc):
    g = doc.getObject(GROUP)
    if g is None:
        g = doc.addObject("App::DocumentObjectGroup", GROUP)
        g.Label = "VEX parts"
    return g


def worked(doc, part, steps):
    # the plain part's shape with steps done to it, mm. off the plain source, building a 35 long channel from scratch is 1.6 s
    s = Part.getShape(source(doc, part))
    for step in steps:
        s = metal.work(s, step)
    return s


def source(doc, part, steps=()):
    # one per variant and set of steps (bends, cuts, drilled holes). a worked one keeps the plain one's VexName, thats what gets bought
    name, key = part["name"], json.dumps(list(steps)) if steps else ""
    for o in group(doc).Group:
        if getattr(o, "VexName", None) == name and getattr(o, "VexSteps", "") == key:
            return o
    if steps:
        s, faces = worked(doc, part, steps), None  # vex's face colors dont survive the steps
        if "file" in part and App.GuiUp:
            # a drilled gear, the color most of it was
            was = next(o for o in source(doc, part).Group if o.TypeId == "Part::Feature").ViewObject.DiffuseColor
            faces = [max(set(was), key=was.count)] * len(s.Faces)
    else:
        s, faces = shape(part)  # first, or no generator leaves an empty source behind
        if part.get("paint") and App.GuiUp:
            faces = painted(s, part["paint"], faces)
        elif faces and part.get("color"):
            faces = stood_in(faces, cat()["colors"][part["color"]])
    src = doc.addObject("App::Part", "VexPart")
    src.Label = f"{name} source" + (", worked" if steps else "")  # the placed copies get the plain name
    src.addProperty("App::PropertyString", "VexName", "VEX")
    src.VexName = name
    if key:
        src.addProperty("App::PropertyString", "VexSteps", "VEX")
        src.VexSteps = key
    solid = doc.addObject("Part::Feature", "Solid")
    solid.Shape = s
    p = part.get("params", {})
    made = p.get("material", part.get("material"))
    if "mass" in part and not steps:
        src.addProperty("App::PropertyMass", "VexMass", "VEX")
        src.VexMass = part["mass"]  # vex's listed one, "155 g"
    elif made in cat()["density"]:
        src.addProperty("App::PropertyMass", "VexMass", "VEX")
        src.VexMass = f"{s.Volume * cat()['density'][made] / 1000} g"  # mm3 * g/cm3
        if "file" in part:
            # one density for a whole step part
            src.addProperty("App::PropertyBool", "VexGuess", "VEX")
            src.VexGuess = True
    if made in cat()["freecad_material"]:
        # before the colors, a material can bring its own look
        import Materials
        solid.ShapeMaterial = Materials.MaterialManager().getMaterial(cat()["freecad_material"][made])
    color_name = p.get("color") or part.get("color") or made  # license plates and flex wheels ("Flex {hardness}") in params, steps get theirs in catalog.step_parts
    color = color_name and cat()["colors"].get(color_name.format(**p))
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
            seams.update((s.findSubShape(e)[1], c) for e in f.Edges if e.isSeam(f))
        if seams:
            vo.LineColorArray = [seams.get(i, vo.LineColor) for i in range(1, len(s.Edges) + 1)]
    src.addObject(solid)
    group(doc).addObject(src)
    src.Visibility = False
    return src


def picks(family, part):
    # {property: label} that lands on part, the inverse of variant()
    mine = part["params"]
    return {prop: next(label(c) for c in choices if catalog.fits(c, mine)) for prop, choices in options(family)}


def place(doc, part, parent=None):
    # parent = the active assembly or part, if theres one
    # plain App::Link, assembly checks TypeId == "App::Link" exactly
    link = parent.newObject("App::Link", "Vex") if parent else doc.addObject("App::Link", "Vex")
    if "file" in part:
        link.addProperty("App::PropertyString", "VexStep", "VEX")
        link.VexStep = f"{part['folder']}/{part['file']}"
        # a wheel from the folders gets the boxes too
        for menu in menus().values():
            mine = [p for p in menu["parts"] if p["key"] == link.VexStep]
            if not mine:
                continue
            boxes(link, menu, mine[0])
            link.addProperty("App::PropertyString", "VexMenu", "VEX")
            link.VexMenu = menu["id"]
            link.setPropertyStatus("VexMenu", "ReadOnly")
            break
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


def boxes(link, menu, part):
    # a menu's axes as properties on a placed copy, each with just the choises that go with the ones above it
    BUSY.add((link.Document.Name, link.Name))  # setting a list jumps it to the first choice, the observer would chase that
    try:
        for axis, choices in catalog.narrowed(menu, part)[0]:
            if not hasattr(link, axis):
                link.addProperty("App::PropertyEnumeration", axis, "VEX")
            setattr(link, axis, choices)
            setattr(link, axis, part[axis])
    finally:
        BUSY.discard((link.Document.Name, link.Name))


def remenu(link):
    # a box changed on a menu part, onto the part the boxes land on now
    menu = menus()[link.VexMenu]
    part = catalog.narrowed(menu, {a: getattr(link, a) for a in menu["axes"]})[1]
    if part["key"] != link.VexStep:
        restep(link, part["key"])  # boxes and all
    else:
        boxes(link, menu, part)


def restep(link, key):
    # a placed step part onto another step, the steps that still fit and its menu boxes along
    link.VexStep = key
    refit(link)
    part = row(link)
    if part:
        boxes(link, menus()[link.VexMenu], part)


def row(link):
    # a placed step part's menu row, None off the menus
    menu = menus().get(getattr(link, "VexMenu", ""))
    return menu and next((p for p in menu["parts"] if p["key"] == link.VexStep), None)


def variant(family, picked):
    # picked = {property: label}, from a link or the browser
    params = {}
    for key, choices in catalog.axes(family):
        if len(choices) == 1:
            params.update(choices[0])
    for prop, choices in options(family):
        labels = [label(c) for c in choices]
        params.update(choices[labels.index(picked[prop])])
    name = family["name"].format(**params)
    if name not in index()[1]:
        raise ValueError(f"VEX doesn't make a {name}")  # a family's skip
    return index()[1][name]


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
    link.LinkedObject = source(link.Document, part, steps(link))
    link.Label = part["name"]


def steps(link):
    # the bends, cuts and drilled holes on one placed copy, metal.work() dicts in order
    return json.loads(getattr(link, "VexSteps", "") or "[]")


def rework(link, done):
    # just this copy gets its own worked source, the plain one stays for the rest
    # made first, a step that cant be done raises before anything changes. the observer would hit it with nobody to catch it
    source(link.Document, part_of(link), done)
    if not hasattr(link, "VexSteps"):
        link.addProperty("App::PropertyString", "VexSteps", "VEX")
        link.setPropertyStatus("VexSteps", "Hidden")
    was = link.LinkedObject
    link.VexSteps = json.dumps(done)
    retarget(link)
    carry(link, was)
    prune(was)


def holder(obj, sub):
    # (the link the frame in joint sub is on, the frame's name) off its root obj. "Link.2.Hole001." is element 2 of an array, "Face1" has no trailing dot
    path = sub.split(".")[:-1]
    owner = path[:-1]
    if owner and owner[-1].isdigit():
        owner.pop()
    return (obj.Document.getObject(owner[-1]) if owner else obj), (path[-1] if path else None)


def on_hole(link, plc, near=1e-4):
    # center of the hole plc (link coords) sits on, within near mm, or None. either way along the axis, a standoff's Seat points in off an end whose normal points out
    center, n = hole_spot(link, plc.Base)
    if (center - plc.Base).Length < near and abs(n.dot(plc.Rotation.multVec(Vector(0, 0, 1)))) > 1 - 1e-6:
        return center
    return None


def on_surface(surface, f):
    # going by a corner and a middle point of f's parameters, a sphere has no vertexes
    u0, u1, v0, v1 = f.ParameterRange
    for p in (f.valueAt(u0, v0), f.valueAt((u0 + u1) / 2, (v0 + v1) / 2)):
        if (surface.value(*surface.parameter(p)) - p).Length > 1e-4:
            return False
    return True


def element(shape, old, way):
    # name of the face / edge / vertex in shape that old is after way, None if its gone
    # a face counts if any of it is still there (a drilled one is a *dih*frent face but the same spot), the most of it wins
    old = old.copy()
    old.transformShape(way.toMatrix())
    kind = old.ShapeType
    if kind == "Vertex":
        hits = [(1, i) for i, v in enumerate(shape.Vertexes, 1) if (v.Point - old.Point).Length < 1e-4]
    elif kind == "Edge":
        # length first, a degenerate edge has no Curve
        hits = [(1, i) for i, e in enumerate(shape.Edges, 1) if abs(e.Length - old.Length) < 1e-4 and (e.CenterOfMass - old.CenterOfMass).Length < 1e-4 and type(e.Curve) is type(old.Curve)]
    else:
        near = [(i, f) for i, f in enumerate(shape.Faces, 1) if type(f.Surface) is type(old.Surface) and f.BoundBox.intersect(old.BoundBox) and on_surface(old.Surface, f)]
        hits = [(f.common(old).Area, i) for i, f in near]  # the boolean only on ones already on the same surface, a plate has ~400 hole walls in the box
    most, i = max(hits, default=(0, 0))
    return f"{kind}{i}" if most > 1e-4 else None  # mm2 for a face


def ways(old, new):
    # where a frame on a copy worked by old steps could be with new ones. each bend since they differ turns it or doesnt, cuts and drills leave it
    k = 0
    while k < min(len(old), len(new)) and old[k] == new[k]:
        k += 1
    undo = [metal.turned(s).inverse() for s in reversed(old[k:]) if s["do"] == "fold"]
    redo = [metal.turned(s) for s in new[k:] if s["do"] == "fold"]
    out = [Placement()]
    for t in undo + redo:
        out += [t.multiply(o) for o in out]
    return out


def carry(link, was):
    # frames on the old source onto the new one, for holes still there or turned with a bend, and joints on this copy with them, ones straight on a face, edge or corner too. on a hole a cut took off they stay broken
    if was is None or was == link.LinkedObject:
        return
    lcs = {o.Name: o for o in was.Group if o.TypeId == "App::LocalCoordinateSystem"}
    solid, new = (next(o for o in s.Group if o.TypeId == "Part::Feature") for s in (was, link.LinkedObject))
    refs = []  # (joint, prop, obj, subs, frame name) through this copy
    direct = []  # (joint, prop, obj, subs, the elements) straight on faces / edges / vertexes of the solid, freecad's own joint tool
    for j in [o for o in link.Document.Objects if hasattr(o, "JointType")]:
        for prop in ("Reference1", "Reference2"):
            obj, subs = getattr(j, prop) or (None, [""])  # None when unset
            if obj is None or not subs:
                continue
            owner, name = holder(obj, subs[0])
            if owner == link and name in lcs:
                refs.append((j, prop, obj, subs, name))
            elif owner == link and name == solid.Name:
                try:
                    olds = [solid.Shape.getElement(s.rsplit(".", 1)[1]) for s in subs]
                except (IndexError, ValueError):
                    continue  # already broken
                if all(o.ShapeType in ("Face", "Edge", "Vertex") for o in olds):
                    direct.append((j, prop, obj, subs, olds))
    tries = ways(steps(was), steps(link))
    for j, prop, obj, subs, olds in direct:
        for way in tries:
            found = [element(new.Shape, o, way) for o in olds]
            if None not in found:
                path = [s.rsplit(".", 1)[0].removesuffix(solid.Name) for s in subs]  # "Vex.Solid" -> "Vex.", or "" with the link as root
                setattr(j, prop, [obj, [f"{p}{new.Name}.{e}" for p, e in zip(path, found)]])
                break
    # bare ones only onto a worked source just this copy uses, on a plain one theyd show up on every copy of that size
    src = link.LinkedObject
    private = bool(getattr(src, "VexSteps", "")) and [o for o in src.InList if o.isDerivedFrom("App::Link")] == [link]
    wanted = {r[4] for r in refs}
    moved = {}  # old frame name -> its copy in the new source
    for old in lcs.values():
        if not (private or old.Name in wanted):
            continue
        for way in tries:
            plc = way.multiply(old.Placement)
            try:
                hit = on_hole(link, plc)
            except ValueError:
                return  # no holes left at all
            if hit is not None:
                moved[old.Name] = frame(link, plc, old.Label.rstrip("0123456789") or "Hole")
                break
    for j, prop, obj, subs, name in refs:
        if name in moved:
            setattr(j, prop, [obj, [".".join(moved[name].Name if p == name else p for p in s.split(".")) for s in subs]])


def prune(src):
    # a worked source nothing links anymore goes, every redo of a step or size change would leave one
    if getattr(src, "VexSteps", "") and not [o for o in src.InList if o.isDerivedFrom("App::Link")]:
        for o in src.Group:
            src.Document.removeObject(o.Name)
        src.Document.removeObject(src.Name)


def source_key(src):
    # a source never changes, a reused object name comes with another VexName or VexSteps
    return src.Document.Uid, src.Name, src.VexName, getattr(src, "VexSteps", "")


def cached(src, what):
    # what(shape) for a source, worked out once
    key = (*source_key(src), what)
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


def dottable(w, step):
    # screw holes, and round ones any size on generated metal (drilled, bigger holes) plus the lockbar's shaft one and the hex bores. on vex's steps the 1/8 and 1/4 shaft holes, keyed or rouned corners, no slots or lightening holes
    if screwable(w):
        return True
    curves = [e.Curve.TypeId for e in w.Edges]
    if not step and all(c == "Part::GeomCircle" for c in curves):
        return True
    b = w.BoundBox
    narrow, wide = sorted([b.XLength, b.YLength, b.ZLength])[1:]
    flats = 2 * w.distToShape(Part.Vertex(b.Center))[0]  # the 11W socket is a 1/4 square turned 45, 0.35 across its box
    if not step:
        hexed = len(curves) == 6 and all(c == "Part::GeomLine" for c in curves) and any(lo <= flats <= hi for lo, hi in HEX)
        return hexed or SHAFT[1][0] <= flats <= SHAFT[1][1]  # not the LS size, a plate diamond is 0.127 across its flats
    shaft = any(lo <= wide <= hi or lo <= flats <= hi for lo, hi in SHAFT)
    return shaft and narrow > 0.95 * wide and all(c in ("Part::GeomLine", "Part::GeomCircle") for c in curves)


def hole_dots(link):
    # centers of dottable holes open to the outside, link coords. shafts and standoffs by their ends
    src = link.LinkedObject
    if getattr(link, "VexFamily", None) in stock.FAMILIES:
        return [c for c, _ in ends(Part.getShape(src))]
    # kept on the source, the 11W's rays take a while
    if not hasattr(src, "VexHoleDots"):
        step = hasattr(link, "VexStep")
        # before the property, one that throws would leave it empty for good
        if step and App.GuiUp and not getattr(src, "VexSteps", ""):
            dots = step_dots(part_of(link), Part.getShape(src))
        else:
            dots = outermost(Part.getShape(src), step)
        src.addProperty("App::PropertyVectorList", "VexHoleDots", "VEX")
        src.setPropertyStatus("VexHoleDots", "Hidden")
        src.VexHoleDots = dots
    gap = u_gap(link)
    return [into_gap(c, gap) for c in src.VexHoleDots]


def step_dots(part, shape):
    # a plain step's dots, kept next to its brep. 11 s of rays on the 4" antistatic wheel, evry time. not anymore
    path = BREPS / f"{kept(part)}.dots{DOTS_VERSION}.json"
    if path.is_file():
        return [Vector(*c) for c in json.loads(path.read_text())]
    dots = outermost(shape, True)
    try:
        BREPS.mkdir(parents=True, exist_ok=True)
        Path(f"{path}.part").write_text(json.dumps([tuple(c) for c in dots]))
        os.replace(f"{path}.part", path)
    except OSError:
        pass  # works it out again next time
    return dots


def outermost(shape, rays):
    # one per hole and side. rays=True drops loops facing into the part, the 11W step has those. generated metal is all through holes
    far = shape.BoundBox.DiagonalLength
    faces = boxed(shape) if rays else []
    kept = {}  # axis and side -> centers
    for w, c, n in sorted(holes(shape), key=lambda h: -h[1].dot(h[2])):
        if not dottable(w, rays) or rays and hits(faces, c + n * OUT, n, far):
            continue
        if rays and screwable(w):
            # most of the rays down it stopping short means somethings in it, the 11W's case screw heads are 0.05 down. a shaft socket is meant to be short
            half = across(w) / 2
            short = [t for t in down(faces, c - n * OUT, n, half / 2, far) if t is not None and t < MIN_THREAD]
            if len(short) >= 3:
                continue
        key = tuple(round(v, 2) for v in (*n, *(c - n * c.dot(n))))
        # the 5.5W has its thread at the face and a wider loop 0.042 under it. a channel's other flange is its own hole
        if all(o.dot(n) - c.dot(n) > SAME_HOLE for o in kept.get(key, [])):
            kept.setdefault(key, []).append(c)
    return [c for cs in kept.values() for c in cs]


def u_gap(link):
    # a U-channel's flange insides as (z, mm out into the channel). its 29 mm leaves a gap round the 2x c-channel it goes over, 0.008 a side
    part = part_of(link)
    if part.get("family") != "u-channel":
        return []
    c = cat()
    p, t = part["params"], metal.thickness(part["params"], c)
    off = (p["web"] - 2 * t - 2 * c["grid"]["pitch"]) / 2 * metal.IN
    return [(t * metal.IN, off), ((p["web"] - t) * metal.IN, -off)]


def into_gap(c, gap):
    # c moved off a U-channel flange inside by u_gap(), so a c-channel's outer dots inside it meet these
    for z, off in gap:
        if abs(c.z - z) < 1e-6:
            return Vector(c.x, c.y, c.z + off)
    return c


def hole_spot(link, point):
    # hole_at, but where the frame and dot go. same thing except on a U-channel's flange insides
    center, n = hole_at(link, point)
    return into_gap(center, u_gap(link)), n


def off_metal(link, point):
    # mm the hole_spot frame sits out off the metal, 0 but on a U-channel's flange insides
    center = hole_at(link, point)[0]
    return (into_gap(center, u_gap(link)) - center).Length


def hole_frame(link, point):
    # LCS on the hole from hole_spot, z out of the face, x along the length if it can
    # it goes in the source so every copy has it
    center, n = hole_spot(link, point)
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


def far_side(link, point):
    # the hole nearest point where it comes out the other side of the wall its in, link coords. None for a blind one
    center, n = hole_at(link, point)
    src = link.LinkedObject
    shape = Part.getShape(src)
    if getattr(link, "VexFamily", None) in stock.FAMILIES:
        return next(c for c, m in ends(shape) if m.dot(n) < 0)
    found = cached(src, holes)
    w = next(h[0] for h in found if (h[1] - center).Length < 1e-6)
    # down through the metal just past the hole's edge, the first face out is the wall's other side. the farthest loop on the axis would be a channel's other flange
    x, y = square_to(n)
    faces, far = boxed(shape), shape.BoundBox.DiagonalLength
    for side in (x, -x, y, -y):
        wall = hits(faces, center + side * (across(w) / 2 + WALL_PROBE) - n * OUT, -n, far)
        if wall:
            break
    else:
        return None
    back = [c for _, c, m in found if m.dot(n) < -1 + 1e-6 and (c - center).cross(n).Length < ON_AXIS]
    best = min(back, key=lambda c: abs((center - c).dot(n) - wall[0]), default=None)
    return best if best is not None and abs((center - best).dot(n) - wall[0]) < SAME_HOLE else None


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
    # placed copies: a VEX param or menu box changing points it at that variant, one going takes its insert
    def slotChangedObject(self, obj, prop):
        doc = obj.Document
        # undo / redo puts LinkedObject back itself, retargetting made a second source
        if doc.Restoring or doc.Transacting:
            return
        menu = hasattr(obj, "VexMenu") and menus().get(obj.VexMenu)
        from . import inserts  # it imports this
        if menu and prop in menu["axes"] and (doc.Name, obj.Name) not in BUSY:
            remenu(obj)
            inserts.boxes(obj, getattr(obj, "Insert", inserts.NONE))  # the bore moved, or its gone
        elif prop in ("Insert", "InsertFlip") and hasattr(obj, "VexInsert") and (doc.Name, obj.Name) not in BUSY:
            inserts.update(obj)
        if not hasattr(obj, "VexFamily"):
            return
        if prop == "VexSteps":
            retarget(obj)  # rework() / refit() already checked them
        elif prop != "VexFamily" and obj.getGroupOfProperty(prop) == "VEX":
            try:
                refit(obj)
            except ValueError as e:
                App.Console.PrintWarning(f"VEX: {e}, {obj.Label} stays what it was\n")
                was = index()[1].get(getattr(obj.LinkedObject, "VexName", None))
                if was:
                    setattr(obj, prop, picks(index()[0][obj.VexFamily], was)[prop])

    def slotDeletedObject(self, obj):
        # a part going takes its insert with it, undo brings both back
        doc = obj.Document
        if doc.Restoring or doc.Transacting or not getattr(obj, "VexInsert", ""):
            return
        from . import inserts
        ins = inserts.insert(obj)
        if ins:
            inserts.take_out(ins)


def refit(link):
    # after a size change the steps that still fit, up to the first that doesnt (a cut past the new end)
    done, was, part = steps(link), link.LinkedObject, part_of(link)
    for k in range(len(done), -1, -1):
        try:
            source(link.Document, part, done[:k])
            break
        except ValueError:
            if k == 0:
                raise  # the plain part cant be made, nothing to do with the steps. they stay
    if k < len(done):
        App.Console.PrintWarning(f"VEX: {len(done) - k} of the bends, cuts or drilled holes on {link.Label} didn't fit the new size, dropped them\n")
        link.VexSteps = json.dumps(done[:k])
    retarget(link)
    carry(link, was)
    prune(was)
