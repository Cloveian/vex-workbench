# vex parts in a document. one hidden source per variant, every placed copy is a plain App::Link to it
import functools

import Part

from . import catalog, metal

GROUP = "VexParts"


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
    vals = [v for v in choice.values() if not isinstance(v, bool)]
    return ", ".join(f"{v:g}" if isinstance(v, float) else str(v) for v in vals)


def options(family):
    # the link properties and browser combos. rows all go under "Size"
    out = []
    for key, choices in catalog.axes(family):
        if len(choices) > 1:
            rows = any(set(c) != {key} for c in choices)
            out.append(("Size" if rows else key.title(), choices))
    return out


def shape(part):
    if "file" in part:
        path = catalog.STEP_DIR / part["folder"] / part["file"]
        if not path.is_file():
            raise ValueError(f"no step file at {path}")
        return Part.read(str(path))
    if part["family"] in metal.PROFILES:
        return metal.make(part, cat())
    raise ValueError(f"no generator for {part['family']} yet")


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
    s = shape(part)  # first, or no generator leaves an empty source behind
    src = doc.addObject("App::Part", "VexPart")
    src.Label = f"{name} source"  # the placed copies get the plain name
    src.addProperty("App::PropertyString", "VexName", "VEX")
    src.VexName = name
    solid = doc.addObject("Part::Feature", "Solid")
    solid.Shape = s
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


class Observer:
    # a VEX param changed on a placed copy -> point it at that variant
    def slotChangedObject(self, obj, prop):
        doc = obj.Document
        # undo / redo puts LinkedObject back itself, retargetting made a second source
        if doc.Restoring or doc.Transacting or not hasattr(obj, "VexFamily"):
            return
        if prop != "VexFamily" and obj.getGroupOfProperty(prop) == "VEX":
            retarget(obj)
