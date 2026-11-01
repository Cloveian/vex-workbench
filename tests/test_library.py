# placing parts in a document, run with: python tests/test_library.py (needs FreeCAD + vex-step/)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401  puts FreeCAD on the path, and finds freecad/vex_workbench in ROOT
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
pl.Holes = "5"
doc.recompute()
assert [s["do"] for s in library.steps(pl)] == ["fold"] and pl.Label == "5x5 Steel Plate", (library.steps(pl), pl.Label)
assert abs(Part.getShape(pl.LinkedObject).BoundBox.XMax - 2.5 * IN) < 0.01
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
doc.recompute()
assert Part.getShape(w).Volume > 0

# weights and the parts list. the washer is a step part, no weight
from freecad.vex_workbench import partslist  # noqa: E402

grams = a.LinkedObject.VexMass.getValueAs("g").Value
assert abs(grams - Part.getShape(a.LinkedObject).Volume * 7.85 / 1000) < 1e-6, grams
assert not hasattr(w.LinkedObject, "VexMass")
counts = partslist.count(doc)
assert [n for n, _ in counts.values()] == [1, 1, 1, 1] and counts[w.Label][1] is None, counts
sheet = partslist.fill(doc)
assert sheet.get("A7").startswith("Total, 4 parts, 1 without"), sheet.get("A7")

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

App.closeDocument(doc.Name)
print("ok")
