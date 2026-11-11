# shaft inserts in HS bores. their own part, held in its bore by an expression on Placement. second draft, the first one was fine
import FreeCAD as App

from . import library, snap
from .metal import IN

BORE = 0.24 * IN, 0.36 * IN  # mm across a HS bore loop's box, 0.25 square to the 8T 6P's 0.339
FLANGE = 0.05 * IN  # mm, both inserts, off vex's steps
NONE = "None"


def kinds():
    return [NONE, *library.cat()["insert"]]


def takes(link):
    return bool((library.row(link) or {}).get("inserts"))


def bores(shape):
    # (center, outward normal, along a flat) of the square loop on each face of a HS bore, [] for none
    out = []
    for w, c, n in library.holes(shape):
        flats = [e for e in w.Edges if e.Curve.TypeId == "Part::GeomLine"]
        if len(flats) >= 4 and BORE[0] <= library.across(w) <= BORE[1]:
            out.append((c, n, flats[0].Curve.Direction))
    # the +x / +y / +z face first, InsertFlip takes the other
    return sorted(out, key=lambda b: -(b[1].x + b[1].y + b[1].z)) if len(out) == 2 else []


def seat(bore):
    # insert's own coords onto the bore. its flange is y 0..FLANGE, into the bore up +y, flats along x and z
    c, n, d = bore
    z = d.cross(-n)
    o = c + n * FLANGE
    return App.Placement(App.Matrix(d.x, -n.x, z.x, o.x, d.y, -n.y, z.y, o.y, d.z, -n.z, z.z, o.z, 0, 0, 0, 1))


def step(kind):
    name = library.cat()["insert"][kind]
    return next(p for p in library.index()[2].values() if p["name"] == name)


def boxes(link, kind=NONE):
    # Insert and InsertFlip on a placed part that takes them, and kind put in. one that stopped taking them loses its insert
    if not takes(link):
        if hasattr(link, "Insert"):
            update(link)
        return
    busy = link.Document.Name, link.Name
    library.BUSY.add(busy)
    try:
        if not hasattr(link, "Insert"):
            link.addProperty("App::PropertyEnumeration", "Insert", "VEX")
            link.addProperty("App::PropertyBool", "InsertFlip", "VEX")
            link.addProperty("App::PropertyString", "VexInsert", "VEX")  # its name. a PropertyLink back would be a loop with the insert's expression
            link.setPropertyStatus("VexInsert", "Hidden")
            link.Insert = kinds()
        link.Insert = kind
    finally:
        library.BUSY.discard(busy)
    update(link)


def insert(link):
    # None for none. a copied part still names the one in the part it was copied off of
    ins = link.VexInsert and link.Document.getObject(link.VexInsert)
    return ins if ins and any(expr.startswith(link.Name + ".") for _, expr in ins.ExpressionEngine) else None


def update(link):
    # puts in, moves or takes out the insert to match the boxes, after a box or the part itself changed
    ins = insert(link)
    kind = link.Insert
    found = kind != NONE and takes(link) and library.cached(link.LinkedObject, bores)
    at = found and seat(found[int(link.InsertFlip)])
    if ins is not None and found and library.part_of(ins)["name"] == step(kind)["name"] and ins.VexSeat.isSame(at, 1e-9):
        return
    if ins is not None:
        take_out(ins)
    link.VexInsert = ""
    if found:
        put_in(link, step(kind), at)


def put_in(link, part, at):
    # at = where it sits, link coords
    parent = link.getParentGeoFeatureGroup()
    ins = library.place(link.Document, part, parent)
    ins.addProperty("App::PropertyPlacement", "VexSeat", "VEX")
    ins.setPropertyStatus("VexSeat", "Hidden")
    ins.VexSeat = at
    ins.Placement = link.Placement.multiply(at)  # the expression has it again on the next recompute
    ins.setExpression("Placement", f"{link.Name}.Placement * VexSeat")
    link.VexInsert = ins.Name
    asm = snap.inside(parent)[1]
    if asm:
        # and fixed in for the solver
        snap.joint(asm, "Fixed", snap.on(link, library.frame(link, at, "Bore")), snap.on(ins, library.frame(ins, App.Placement(), "Seat")))


def take_out(ins):
    doc = ins.Document
    for j in [o for o in ins.InList if hasattr(o, "JointType")]:
        doc.removeObject(j.Name)
    doc.removeObject(ins.Name)
