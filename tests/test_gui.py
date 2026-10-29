# toolbar, colurs, the parts list and the dock inside the gui, run with: env QT_QPA_PLATFORM=offscreen freecad -M . tests/test_gui.py
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
    w.tree.setCurrentItem(w.tree.findItems("Shoulder Screw", QtCore.Qt.MatchExactly)[0])
    w.combos["Length"].setCurrentText("0.5, 0.18")
    w.place()
    assert QtWidgets.QApplication.overrideCursor() is None, "wait cursor stuck"
    got = Gui.Selection.getSelection()[0].Label
    assert got == "0.500, 0.18 Robosource Shoulder Screw (8-32, Steel)", got
    say("ok")
except Exception:
    say(traceback.format_exc())
for d in list(App.listDocuments()):
    App.closeDocument(d)  # else the save prompt hangs offscreen
Gui.getMainWindow().close()
