# placing parts in a document, run with: python tests/test_library.py (needs FreeCAD + vex-step/)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401  puts FreeCAD on the path, and finds freecad/vex_workbench in ROOT
import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

from freecad.vex_workbench import library  # noqa: E402

IN = 25.4
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

# no generator for that variant, link stays put and nothing gets left behind
c = library.place(doc, gen["1x1x5 Steel Angle (Regular)"])
n = len(doc.Objects)
c.Variant = "Thin 5-Wide"
assert len(doc.Objects) == n and c.Label.startswith("1x1x5 Steel Angle (Regular)"), (len(doc.Objects), n, c.Label)

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

App.closeDocument(doc.Name)
print("ok")
