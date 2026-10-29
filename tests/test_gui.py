# toolbar, colurs, the parts list, the dock and snapping through link arrays and linked sub-assemblies inside the gui (needs vex-step/), run with: env QT_QPA_PLATFORM=offscreen freecad -M . tests/test_gui.py
import os
import sys
import traceback

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets


def say(msg):
    # the gui eats print
    sys.__stdout__.write(msg + "\n")
    sys.__stdout__.flush()


def snapped(obj, path, face, click, center):
    # fakke click on a hole down path under obj, picked() point and the frame both have to come out right
    on = obj.getSubObject(path, retType=3).multVec(click)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(obj.Document.Name, obj.Name, path + face, on.x, on.y, on.z)
    (link, pt), = snap.picked()
    assert (pt - click).Length < 1e-6, (path, pt, click)
    frame = library.hole_frame(link, pt)
    assert (frame.Placement.Base - center).Length < 1e-6, (path, frame.Placement.Base, center)
    return link


try:
    from freecad.vex_workbench import catalog, library

    Gui.activateWorkbench("VexWorkbench")
    bar = Gui.getMainWindow().findChild(QtWidgets.QToolBar, "VEX")
    tools = [a.text() for a in bar.actions()]
    assert tools == ["VEX parts", "Frame on hole", "Parts list"], tools

    doc = App.newDocument("vexgui")
    _, gen, steps = library.index()
    ch = library.place(doc, gen["1x2x1x5 Steel C-Channel"])
    steel = tuple(library.cat()["colors"]["Steel"])
    got = ch.LinkedObject.Group[0].ViewObject.ShapeColor[:3]
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, steel)), got

    # vex's own colors on a step part, one per face, and the same solid Part.read gives
    motor = steps["Electronics/V5 Smart Motor (276-4840).step"]
    m = library.place(doc, motor)
    doc.recompute()
    assert App.ActiveDocument == doc, App.ActiveDocument.Name
    solid = m.LinkedObject.Group[0]
    colors = solid.ViewObject.DiffuseColor
    assert len(colors) == len(solid.Shape.Faces), (len(colors), len(solid.Shape.Faces))
    # the motor's gold, COLOUR_RGB 0.647 0.518 0 in its step
    assert any(abs(c[0] - 0.647) < 0.01 and abs(c[1] - 0.518) < 0.01 for c in colors), sorted({tuple(round(v, 3) for v in c) for c in colors})
    plain = Part.read(str(catalog.step_path(motor)))
    assert abs(solid.Shape.Volume / plain.Volume - 1) < 1e-6, (solid.Shape.Volume, plain.Volume)
    assert len(library.holes(solid.Shape)) == len(library.holes(plain)), "holes differ"

    Gui.runCommand("Vex_PartsList")
    assert doc.getObject("VexPartsList").get("A5").startswith("Total, 2 parts, 1 without")

    # the dock, a family with pairs
    from freecad.vex_workbench import browser
    Gui.runCommand("Vex_Browser")
    w = browser._dock.widget()
    shoulder = w.tree.findItems("Shoulder Screw", QtCore.Qt.MatchExactly)[0]
    w.tree.setCurrentItem(shoulder)
    w.combos["Length"].setCurrentText("0.5, 0.18")
    w.place()
    assert QtWidgets.QApplication.overrideCursor() is None, "wait cursor stuck"
    got = Gui.Selection.getSelection()[0].Label
    assert got == "0.500, 0.18 Robosource Shoulder Screw (8-32, Steel)", got
    # search, words in any order
    w.search.setText("motor smart")
    hit = w.tree.findItems("Smart Motor", QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive)[0]
    assert not hit.isHidden() and not hit.parent().isHidden(), hit.text(0)
    assert shoulder.isHidden()
    # a variant name finds its family, and picking it starts on that variant
    w.search.setText("1x2x1x25 steel")
    fam = w.tree.findItems("C-Channel", QtCore.Qt.MatchExactly)[0]
    assert not fam.isHidden()
    w.tree.setCurrentItem(fam)
    got = {p: b.currentText() for p, b in w.combos.items()}
    assert got == {"Material": "Steel", "Size": "2", "Holes": "25"}, got
    w.search.setText("")

    # a click on the second element of a link array lands on that element's hole
    from freecad.vex_workbench import snap
    arr = library.place(doc, gen["1x2x1x5 Steel C-Channel"])
    arr.ElementCount = 2
    arr.ElementList[1].Placement = App.Placement(App.Vector(100, 0, 0), App.Rotation())  # PlacementList doesnt move them with ShowElement on
    doc.recompute()
    shape = arr.LinkedObject.Group[0].Shape
    i, f = next((i, f) for i, f in enumerate(shape.Faces) if len(f.Wires) > 1)
    # first hole along x. without element 1's placement the click lands past the end and snaps to the last one
    loop = min((w for w in f.Wires if not w.isSame(f.OuterWire)), key=lambda w: w.BoundBox.Center.x)
    click = loop.Edges[0].valueAt(loop.Edges[0].FirstParameter)  # part's own coords
    # by index, and by the element's own name
    for elem in ("1", arr.ElementList[1].Name):
        snapped(arr, f"{elem}.", f"Face{i + 1}", click, loop.BoundBox.Center)

    # same through a linked sub-assembly, moved 200 over and turned
    side = doc.addObject("App::Part", "Side")
    ch2 = library.place(doc, gen["1x2x1x5 Steel C-Channel"], side)
    ch2.Placement = App.Placement(App.Vector(0, 0, 30), App.Rotation(45, 0, 0))  # inside Side too
    copy = doc.addObject("App::Link", "SideCopy")
    copy.LinkedObject = side
    copy.Placement = App.Placement(App.Vector(0, 200, 0), App.Rotation(0, 0, 90))
    doc.recompute()
    assert snapped(copy, f"{ch2.Name}.", f"Face{i + 1}", click, loop.BoundBox.Center) == ch2
    say("ok")
    failed = False
except Exception:
    say(traceback.format_exc())
    failed = True
for d in list(App.listDocuments()):
    App.closeDocument(d)  # else the save prompt hangs offscreen
if failed:
    os._exit(1)  # closing the window always exits 0
Gui.getMainWindow().close()
