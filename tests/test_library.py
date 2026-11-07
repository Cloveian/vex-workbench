# placing parts in a document, run with: python tests/test_library.py (needs FreeCAD)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401  puts FreeCAD on the path, and finds freecad/vex_workbench in ROOT
freecad.__path__.insert(0, str(ROOT / "freecad"))  # this checkout ahead of an addon manager install of it
import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

from freecad.vex_workbench import library  # noqa: E402
from freecad.vex_workbench.metal import IN  # noqa: E402

App.addDocumentObserver(library.Observer())
doc = App.newDocument("vextest")
_, gen, steps = library.index()


def length(obj):
    b = Part.getShape(obj).BoundBox
    return round(max(b.XLength, b.YLength, b.ZLength) / IN, 4)


a = library.place(doc, gen["1x2x1x5 Steel C-Channel"])
doc.recompute()
assert a.Label.startswith("1x2x1x5 Steel C-Channel"), a.Label
assert (a.Holes, a.Material, a.Size) == ("5", "Steel", "2"), (a.Holes, a.Material, a.Size)
assert length(a) == 2.5, length(a)

# same variant shares the source
b = library.place(doc, gen["1x2x1x5 Steel C-Channel"])
assert b.LinkedObject == a.LinkedObject

# editing one copy moves just that one
b.Holes = "10"
doc.recompute()
assert length(b) == 5.0 and length(a) == 2.5, (length(a), length(b))
assert b.LinkedObject != a.LinkedObject
assert len(doc.getObject(library.GROUP).Group) == 2

# rows go by label
b.Size = "5"
doc.recompute()
assert b.Label.startswith("1x5x1x10 Steel C-Channel"), b.Label

# a cut down 1x1 is a variant like any other
c = library.place(doc, gen["1x1x5 Steel Angle (Regular)"])
c.Variant = "Cut 3x, Between Holes"
assert c.Label.startswith("1x1x5 Steel Angle (Cut 3x, Between Holes)"), c.Label
# no generator (the HS lockbar), nothing gets left behind
n = len(doc.Objects)
try:
    library.source(doc, next(p for p in gen.values() if p["family"] == "hs-lockbar"))
    raise AssertionError("made a lockbar")
except ValueError:
    pass
assert len(doc.Objects) == n, (len(doc.Objects), n)

# shortening a bent and cut plate keeps the bend at 1.25 and drops the cut at 3.75 thats past the new end
from freecad.vex_workbench import shop  # noqa: E402

pl = library.place(doc, gen["5x10 Steel Plate"])
doc.recompute()
library.rework(pl, [shop.bend(pl, App.Vector(1.25, 0.25, 0.046) * IN, True, 0, 90), shop.cut(pl, App.Vector(3.75, 0.25, 0.046) * IN, True, 0)])
doc.UndoMode = 1
doc.openTransaction("holes")
long = pl.LinkedObject
pl.Holes = "5"
doc.commitTransaction()
doc.recompute()
assert [s["do"] for s in library.steps(pl)] == ["fold"] and pl.Label == "5x5 Steel Plate", (library.steps(pl), pl.Label)
assert abs(Part.getShape(pl.LinkedObject).BoundBox.XMax - 2.5 * IN) < 0.01
worked = [o for o in doc.getObject(library.GROUP).Group if getattr(o, "VexSteps", "")]
assert worked == [pl.LinkedObject], [o.Label for o in worked]  # the 5x10 one got cleaned up
doc.undo()
doc.recompute()
assert len(library.steps(pl)) == 2 and pl.LinkedObject == long and Part.getShape(long).isValid(), (library.steps(pl), pl.LinkedObject)
doc.redo()
doc.recompute()
doc.UndoMode = 0


# when even the plain part cant be made the error comes out and the fold stays
def refuse(*_):
    raise ValueError("cant")


real, library.source = library.source, refuse
try:
    library.refit(pl)
    raise AssertionError("refit went through")
except ValueError as e:
    assert str(e) == "cant", e
finally:
    library.source = real
assert [s["do"] for s in library.steps(pl)] == ["fold"], library.steps(pl)
doc.removeObject(pl.Name)  # the parts list count further down doesnt want it

# undo / redo dont make another source
doc.UndoMode = 1
doc.openTransaction("holes")
a.Holes = "15"
doc.commitTransaction()
n = len(doc.Objects)
doc.undo()
doc.redo()
doc.recompute()
assert len(doc.Objects) == n and a.Label.startswith("1x2x1x15 Steel C-Channel"), (len(doc.Objects), n, a.Label)

# pairs and the renamed keys read right, and switching by them works
s = library.place(doc, gen["0.290, 0.09 Robosource Shoulder Screw (8-32, Steel)"])
s.Length = "1, 0.12"
doc.recompute()
assert s.Label == "1.000, 0.12 Robosource Shoulder Screw (8-32, Steel)", s.Label
sp = library.place(doc, gen["0.5 OD Spacer, 0.250 (Nylon)"])
assert (sp.OD, sp.Length) == ("0.5", "0.25"), (sp.OD, sp.Length)
for o in (s, sp):
    doc.removeObject(o.Name)

# step part
w = library.place(doc, steps["Motion/Spacers/Washers/Steel/Steel Washer (275-1024).step"])
radio = library.place(doc, steps["Electronics/V5 Robot Radio (276-4831).step"])
collar = library.place(doc, steps["Motion/Collars/Rubber Shaft Collar (228-3510).step"])
doc.recompute()
assert Part.getShape(w).Volume > 0

# wheels repainted: omni rollers light grey on a black hub (the 2" a darker grey), a traction tread grey
colors = library.cat()["colors"]
for f, hub, rim in [("Omni Wheels/2.75 Inch/Antistatic/2.75 (220mm Travel) Omni-Directional Anti-Static Wheel (276-8106).step", "Black", "Light Grey"),
                    ("Traction Wheels/2.75 Inch/Antistatic/2.75 (220mm Travel) Anti-Static Wheel (276-8098).step", "Black", "Grey"),
                    ("Omni Wheels/2 Inch/2” Omni-Directional Wheel (276-9044).step", "Black", "Roller Grey")]:
    wheel = steps["Motion/Wheels/" + f]
    s, _ = library.shape(wheel)
    paint = library.painted(s, wheel["paint"], None)
    big = max(s.Solids, key=lambda x: x.Volume)
    biggest = hub if "Omni" in f else rim  # the omni hub outweighs a roller, a traction tread outweighs its hub
    assert {paint[s.findSubShape(x)[1] - 1] for x in big.Faces} == {tuple(colors[biggest])}, f
    assert set(paint) == {tuple(colors[hub]), tuple(colors[rim])}, f

# weights and the parts list. step parts get vex's listed mass, a guess off the folder's material, or nothing
from freecad.vex_workbench import partslist  # noqa: E402

grams = a.LinkedObject.VexMass.getValueAs("g").Value
assert abs(grams - Part.getShape(a.LinkedObject).Volume * 7.85 / 1000) < 1e-6, grams
assert not hasattr(a.LinkedObject, "VexGuess")
washer = w.LinkedObject
assert washer.VexGuess and abs(washer.VexMass.getValueAs("g").Value - Part.getShape(washer).Volume * 7.85 / 1000) < 1e-6
assert radio.LinkedObject.VexMass.getValueAs("g").Value == 25 and not hasattr(radio.LinkedObject, "VexGuess")
assert not hasattr(collar.LinkedObject, "VexMass")
# and FreeCAD's own material card, the one off its density table name
assert [o.LinkedObject.Group[0].ShapeMaterial.Name for o in (a, w)] == ["Steel-Generic", "Steel-Generic"]
assert collar.LinkedObject.Group[0].ShapeMaterial.Name == "Default"
counts = partslist.count(doc)
assert [row[0] for row in counts.values()] == [1] * 6 and counts[collar.Label][1] is None, counts
sheet = partslist.fill(doc)
assert sheet.get("A9") == "Total, 6 parts, 1 without a weight, 1 guessed (~)", sheet.get("A9")
washer_row = next(r for r in range(2, 8) if sheet.get(f"A{r}") == w.Label)
assert sheet.get(f"C{washer_row}").startswith("~"), sheet.get(f"C{washer_row}")

# a sub-assembly linked once and as an array of 2 counts 4 times with its original, a link array counts every element
sub = doc.addObject("App::Part", "Side")
library.place(doc, gen["1x2x1x20 Aluminum C-Channel"], sub)
doc.addObject("App::Link", "SideCopy").LinkedObject = sub
row = doc.addObject("App::Link", "SideRow")
row.LinkedObject = sub
row.ElementCount = 2
arr = library.place(doc, gen["1.000 Standoff (8-32, Aluminum)"])
arr.ElementCount = 3
doc.recompute()
counts = partslist.count(doc)
assert counts["1x2x1x20 Aluminum C-Channel"][0] == 4 and counts["1.000 Standoff (8-32, Aluminum)"][0] == 3, counts
# a plain link to that array is 2 more, one to nothing is none
doc.addObject("App::Link", "RowCopy").LinkedObject = row
doc.addObject("App::Link", "Nothing")
doc.recompute()
got = partslist.count(doc)["1x2x1x20 Aluminum C-Channel"][0]
assert got == 6, got
doc.removeObject("Nothing")

# a plate bent and one cut in half. each stays the plain one (the bend adds a bit), the total is what both really weigh
p1, p2 = (library.place(doc, gen["5x10 Steel Plate"]) for _ in range(2))
doc.recompute()
plain = p1.LinkedObject.VexMass.getValueAs("g").Value
library.rework(p1, [shop.bend(p1, App.Vector(2.25, 0.25, 0.046) * IN, True, 0, 90)])
library.rework(p2, [shop.cut(p2, App.Vector(2.5, 0.25, 0.046) * IN, True, 0)])
doc.recompute()
bent, half = (o.LinkedObject.VexMass.getValueAs("g").Value for o in (p1, p2))
n, each, total, _ = partslist.count(doc)["5x10 Steel Plate"]
assert n == 2 and each == plain and abs(total - bent - half) < 1e-6 and half < plain < bent, (n, each, total, plain, bent, half)

# duplicate: mirrored across x = 1 in, each copy is exactly where the reflection of the original is, and still a real part
from freecad.vex_workbench import duplicate  # noqa: E402


def corners(link):
    # world vertices, rounded to a micron. through the parent, getShape alone stops at the link's own placement
    up = link.getParentGeoFeatureGroup()
    s = Part.getShape(up, link.Name + ".") if up else Part.getShape(link)
    return sorted((round(v.X, 3), round(v.Y, 3), round(v.Z, 3)) for v in s.Vertexes)


side = doc.addObject("App::Part", "Side")
ch = library.place(doc, gen["1x2x1x7 Steel C-Channel"], side)
ch.Placement = App.Placement(App.Vector(3, 1, 2) * IN, App.Rotation(30, 20, 10))
pl = library.place(doc, gen["5x10 Steel Plate"], side)
pl.Placement = App.Placement(App.Vector(-2, 0, 1) * IN, App.Rotation(0, 90, 0))
side.Placement = App.Placement(App.Vector(0, 4, 0) * IN, App.Rotation(15, 0, 0))
doc.recompute()
before = set(doc.Objects)
m = duplicate.reflection(App.Vector(IN, 0, 0), App.Vector(1, 0, 0))
assert duplicate.duplicate([side], mirror=m) == ([], [], 0, 0)
new = [o for o in doc.Objects if o not in before]
assert not any(o.TypeId == "App::Part" and hasattr(o, "VexName") for o in new), "copied a source"
copy = next(o for o in new if o.TypeId == "App::Part")
assert copy.getParentGroup() is None and len([o for o in copy.Group if duplicate.vex(o)]) == 2
for was, cp in zip((ch, pl), [o for o in copy.Group if duplicate.vex(o)]):
    want = sorted(tuple(round(x, 3) for x in m.multVec(App.Vector(*p))) for p in corners(was))
    assert cp.LinkedObject == was.LinkedObject and corners(cp) == want, was.Label
# turned 90 about z, the copy moves whole
before = set(doc.Objects)
turn = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 90))
duplicate.duplicate([ch], turn=turn)
cp = next(o for o in doc.Objects if o not in before and duplicate.vex(o))
want = sorted(tuple(round(x, 3) for x in turn.multVec(App.Vector(*p))) for p in corners(ch))
assert corners(cp) == want and cp.getParentGeoFeatureGroup() == side
# a V2 mecanum's copy is the other hand, right where its mirror image is. a motor has no other hand, its only turned
mec = library.place(doc, next(p for p in steps.values() if p["name"] == "2” Mecanum Wheels V2 (Left)"))
mec.Placement = App.Placement(App.Vector(4, 2, 1) * IN, App.Rotation(40, 0, 70))
motor = library.place(doc, steps["Electronics/V5 Smart Motor (276-4840).step"])
doc.recompute()
before = set(doc.Objects)
assert duplicate.duplicate([mec, motor], mirror=m) == ([mec.Label], [motor.Label], 0, 0)
cp = next(o for o in doc.Objects if o not in before and duplicate.vex(o) and "Mecanum" in o.Label)
assert cp.Label == "2” Mecanum Wheels V2 (Right)" and cp.Kind == "V2, Right", (cp.Label, cp.Kind)
have = [App.Vector(*p) for p in corners(cp)]
off = max(min((m.multVec(App.Vector(*p)) - q).Length for q in have) for p in corners(mec))
assert off < 0.01, off  # mm
# bent with an off center hole theres no middle plane left, so its copy gets mirrored steps. hole and outline where the mirror puts them
odd = library.place(doc, gen["5x10 Steel Plate"])
odd.Placement = App.Placement(App.Vector(-3, 2, 0) * IN, App.Rotation(20, 10, 0))
doc.recompute()
b = shop.bend(odd, App.Vector(2.25, 0.25, 0.046) * IN, True, 0, 90)
library.rework(odd, [b, shop.drill(odd, App.Vector(3.5, 0.25, 0.046) * IN, 0.17 * IN, False)])
assert duplicate.own_mirror(Part.getShape(odd.LinkedObject))[1] > 0
before = set(doc.Objects)
assert duplicate.duplicate([odd], mirror=m) == ([], [], 0, 0)
cp = next(o for o in doc.Objects if o not in before and duplicate.vex(o))
got = [cp.Placement.multVec(c) for c in library.hole_dots(cp)]
off = max(min((m.multVec(odd.Placement.multVec(c)) - q).Length for q in got) for c in library.hole_dots(odd))
assert len(got) == len(library.hole_dots(odd)) and off < 1e-6, off
want, have = App.BoundBox(), App.BoundBox()
for p in corners(odd):
    want.add(m.multVec(App.Vector(*p)))
for p in corners(cp):
    have.add(App.Vector(*p))
assert (want.Center - have.Center).Length < 0.01 and abs(want.DiagonalLength - have.DiagonalLength) < 0.01, (want, have)
assert abs(Part.getShape(cp).Volume - Part.getShape(odd).Volume) < 1e-6 and cp.LinkedObject != odd.LinkedObject
# a copy of one in a folder inside a part stays in that folder, turned in the part's coords
side = doc.addObject("App::Part", "Side")
side.Placement = App.Placement(App.Vector(10, 0, 0), App.Rotation(0, 0, 30))
folder = side.newObject("App::DocumentObjectGroup", "Left")
pl = library.place(doc, gen["5x10 Steel Plate"], folder)
before = set(doc.Objects)
duplicate.duplicate([pl], turn=App.Placement(App.Vector(0, 0, 3 * IN), App.Rotation()))
cp = next(o for o in doc.Objects if o not in before and duplicate.vex(o))
up = duplicate.frame(cp).multiply(cp.Placement).Base - duplicate.frame(pl).multiply(pl.Placement).Base
assert cp.getParentGroup() == folder and cp.getParentGeoFeatureGroup() == side and (up - App.Vector(0, 0, 3 * IN)).Length < 1e-6, (cp.getParentGroup(), up)

App.closeDocument(doc.Name)
print("ok")
