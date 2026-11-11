# toolbar, colurs, the parts list, the dock, the screw, align, bend, cut and drill tools and snapping through link arrays and linked sub-assemblies inside the gui (needs vex-step/), run with: env QT_QPA_PLATFORM=offscreen freecad -M . tests/test_gui.py
import math
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part
import Sketcher
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
    (link, pt, *_), = snap.picked()
    assert (pt - click).Length < 1e-6, (path, pt, click)
    frame = library.hole_frame(link, pt)
    assert (frame.Placement.Base - center).Length < 1e-6, (path, frame.Placement.Base, center)
    return link


breps = tempfile.mkdtemp(prefix="vex-breps")  # not my real step cache
try:
    from freecad.vex_workbench import catalog, library
    from freecad.vex_workbench.metal import IN

    library.BREPS = Path(breps)
    Gui.activateWorkbench("VexWorkbench")
    bar = Gui.getMainWindow().findChild(QtWidgets.QToolBar, "VEX")
    tools = [a.text() for a in bar.actions()]
    assert tools == ["VEX parts", "Frame on hole", "Align", "Joint", "Screw", "Spacers", "Bend", "Cut", "Drill", "Duplicate", "Parts list"], tools

    doc = App.newDocument("vexgui")
    # a bug in a tool still raises, and whatever it half built gets undone
    from freecad.vex_workbench import ui
    try:
        ui.run("Broken", lambda: doc.addObject("App::FeaturePython", "Half") and 1 / 0)
        raise AssertionError("ZeroDivisionError got eaten")
    except ZeroDivisionError:
        pass
    assert App.getActiveTransaction() is None and doc.getObject("Half") is None, (App.getActiveTransaction(), doc.Objects)
    _, gen, steps = library.index()
    ch = library.place(doc, gen["1x2x1x5 Steel C-Channel"])
    steel = tuple(library.cat()["colors"]["Steel"])
    got = ch.LinkedObject.Group[0].ViewObject.ShapeColor[:3]
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, steel)), got
    # 1/2 star screw has a red head on a steel shank, the 1/4 has no color in the pack
    red, plain = (library.place(doc, gen[f"{n} Torx (Star) Screw (8-32, Steel)"]) for n in ("0.500", "0.250"))
    sc = red.LinkedObject.Group[0]
    tops, rest = set(), set()
    for c, f in zip(sc.ViewObject.DiffuseColor, sc.Shape.Faces):
        (tops if f.BoundBox.ZMin > -1e-6 else rest).add(tuple(round(v, 2) for v in c[:3]))
    assert tops == {(0.96, 0.0, 0.01)} and rest == {tuple(round(v, 2) for v in steel)}, (tops, rest)
    got = plain.LinkedObject.Group[0].ViewObject.ShapeColor[:3]
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, steel)), got
    # a spacer's seam lines are nylon colored so they dont show, its end circles keep their lines
    sp = library.place(doc, gen["0.375 OD Spacer, 0.250 (Nylon)"])
    s, vo = sp.LinkedObject.Group[0].Shape, sp.LinkedObject.Group[0].ViewObject
    seam = {s.findSubShape(e)[1] for f in s.Faces for e in f.Edges if e.isSeam(f)}
    nylon = tuple(library.cat()["colors"]["Nylon"])
    got = {(i in seam, tuple(round(v, 2) for v in c[:3])) for i, c in enumerate(vo.LineColorArray, 1)}
    want = {(True, nylon), (False, tuple(round(v, 2) for v in vo.LineColor[:3]))}
    assert vo.DisplayMode == "Flat Lines" and seam and got == want, (got, want)
    for o in (red, plain, sp):
        doc.removeObject(o.Name)

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
    # read again its off the cached brep, same faces in the same order with the same colors
    t = time.time()
    again, faces = library.shape(motor)
    t = time.time() - t
    assert len(list(library.BREPS.glob("*.json"))) == 1 and t < 2, (list(library.BREPS.iterdir()), t)
    assert all((a.CenterOfMass - b.CenterOfMass).Length < 1e-9 for a, b in zip(again.Faces, solid.Shape.Faces)), "faces moved"
    assert len(faces) == len(colors) and max(abs(a - b) for f, c in zip(faces, colors) for a, b in zip(f, c)) < 1e-6, "colors moved"
    # no colors in vex's hex nut step, so its steel
    nut = library.place(doc, steps["Hardware/Nuts/8-32 Nuts/Hex Nuts/#8-32 Hex Nut (275-1028).step"])
    got = nut.LinkedObject.Group[0].ViewObject.ShapeColor[:3]
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, steel)), got
    doc.removeObject(nut.Name)
    # or its folders color off the fusion library, acetal has none
    gear = library.place(doc, steps["Motion/Gears/Low Strength/36T Gear (276-2169-002).step"])
    got = gear.LinkedObject.Group[0].ViewObject.ShapeColor[:3]
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, library.cat()["colors"]["Red Acetal"])), got
    doc.removeObject(gear.Name)
    # vex's stand-in red on the HS v2 gears goes fusion red, the 84,88,90 core stays
    hs = next(p for p in steps.values() if p["name"].startswith("36T High Strength Gear v2"))
    gear = library.place(doc, hs)
    shades = {tuple(round(v, 2) for v in c[:3]) for c in gear.LinkedObject.Group[0].ViewObject.DiffuseColor}
    assert shades == {(1.0, 0.12, 0.12), (0.33, 0.35, 0.35)}, shades
    doc.removeObject(gear.Name)
    # a step thats all one grey takes its materal's
    screw = library.place(doc, next(p for p in steps.values() if p["name"] == "#8-32 x 1/2\" Star Drive Screw"))
    got = screw.LinkedObject.Group[0].ViewObject.ShapeColor[:3]
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, steel)), got
    doc.removeObject(screw.Name)

    Gui.runCommand("Vex_PartsList")
    sheet = doc.getObject("VexPartsList")
    assert sheet.get("A5") == "Total, 2 parts" and 155 in (sheet.get("C2"), sheet.get("C3")), (sheet.get("A5"), sheet.get("C2"), sheet.get("C3"))

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
    # a source made the active part by a doubie click, the next one goes at the top
    src = Gui.Selection.getSelection()[0].LinkedObject
    Gui.ActiveDocument.ActiveView.setActiveObject("part", src)
    lo, hi = browser.drawn(doc)
    w.place()
    again = Gui.Selection.getSelection()[0]
    assert again not in src.Group and not again.getParentGeoFeatureGroup(), [o.Label for o in src.Group]
    Gui.ActiveDocument.ActiveView.setActiveObject("part", None)
    # clear of everything already drawn, 1 in off the +x side, bottoms level
    b = again.Shape.BoundBox
    assert abs(b.XMin - hi.x - 25.4) < 0.01 and abs(b.ZMin - lo.z) < 0.01, (b, lo, hi)
    # then align opens on it, like it always did :)
    from freecad.vex_workbench import align
    opened, real = [], align.Panel

    class Seen(real):
        def __init__(self):
            super().__init__()
            opened.append(self)

    align.Panel = Seen
    w.align.setChecked(True)
    try:
        w.place()
    finally:
        align.Panel = real
        w.align.setChecked(False)
    third = Gui.Selection.getSelection()[0]
    assert len(opened) == 1 and Gui.Control.activeDialog(), opened
    opened[0].reject()
    doc.removeObject(third.Name)
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
    # searching again with it still picked moves its boxes too
    w.search.setText("1x2x1x30 steel")
    got = {p: b.currentText() for p, b in w.combos.items()}
    assert w.tree.currentItem() is fam and got == {"Material": "Steel", "Size": "2", "Holes": "30"}, got
    w.search.setText("c-channel")
    got = {p: b.currentText() for p, b in w.combos.items()}
    assert got == {"Material": "Steel", "Size": "2", "Holes": "30"}, got
    # theres no steel 3x, Place says so and puts nothing down
    w.combos["Size"].setCurrentText("3")
    had, said, warning = len(doc.Objects), [], QtWidgets.QMessageBox.warning
    QtWidgets.QMessageBox.warning = lambda *a: said.append(a[2])
    try:
        w.place()
    finally:
        QtWidgets.QMessageBox.warning = warning
    assert said == ["VEX doesn't make a 1x3x1x30 Steel C-Channel"] and len(doc.Objects) == had, (said, len(doc.Objects))
    w.combos["Size"].setCurrentText("2")
    # clearing it closes what it opened
    w.search.setText("")
    assert not hit.parent().isExpanded(), "the search left Electronics open"
    # unless whats picked is in there
    w.search.setText("motor smart")
    w.tree.setCurrentItem(hit)
    w.search.setText("")
    assert hit.parent().isExpanded() and w.tree.currentItem() is hit, "the pick got folded away"
    # a menu, picking Mecanum leaves just its sizes and kinds. a search starts on the part it finds
    wheels = w.tree.findItems("Wheels", QtCore.Qt.MatchExactly)[0]
    w.tree.setCurrentItem(wheels)
    w.combos["Type"].setCurrentText("Mecanum")
    assert [w.combos["Size"].itemText(i) for i in range(w.combos["Size"].count())] == ["2", "4"]
    w.combos["Kind"].setCurrentText("V1, Right")
    w.place()
    got = Gui.Selection.getSelection()[0]
    assert got.Label == "2\" Mecanum Wheel- Right" and got.VexStep.endswith("(217-7400).step"), got.Label
    # repainted over its step colors, fusion's grey rollers on a charcoal hub
    shades = {tuple(round(v, 2) for v in c[:3]) for c in got.LinkedObject.Group[0].ViewObject.DiffuseColor}
    assert shades == {(0.15, 0.16, 0.16), (0.65, 0.65, 0.65)}, shades
    # it has the boxes too, a new Type swaps it in place and the boxes under narrow to match
    assert (got.Type, got.Size, got.Kind) == ("Mecanum", "2", "V1, Right") and got.getEnumerationsOfProperty("Size") == ["2", "4"]
    got.Type = "Omni"
    assert got.Label == "2” Omni-Directional Wheel" and got.getEnumerationsOfProperty("Kind") == ["Standard"], got.Label
    assert got.LinkedObject.VexName == got.Label
    w.search.setText("hs bore 18t")
    sprockets = w.tree.findItems("Sprockets", QtCore.Qt.MatchExactly)[0]
    assert not sprockets.isHidden()
    w.tree.setCurrentItem(sprockets)
    got = {p: b.currentText() for p, b in w.combos.items()}
    assert got == {"Chain": "9P (High Strength)", "Teeth": "18", "Bore": "HS"}, got
    # an HS bore takes an insert, placed with it as its own part
    from freecad.vex_workbench import inserts
    assert w.insert.isEnabled()
    w.insert.setCurrentText("Square")
    w.place()
    got = Gui.Selection.getSelection()[0]
    assert got.Insert == "Square" and library.part_of(inserts.insert(got))["name"] == "Metal Shaft Inserts", got.VexInsert
    w.combos["Bore"].setCurrentText("Standard")
    assert not w.insert.isEnabled() and w.insert.currentText() == "None"
    # a search that hides it lets it go, Place goes grey
    w.search.setText("smart motor")
    assert w.tree.currentItem() is None and not w.button.isEnabled() and not w.combos, (w.tree.currentItem(), w.combos)
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
    # hole points find them all, each array element and the channel in Side, its copy and an array of it. each once
    sides = doc.addObject("App::Link", "SideArray")
    sides.LinkedObject = side
    sides.ElementCount = 2
    doc.recompute()
    got = [(root.Name, path, link) for link, (root, path) in snap.placed(doc)]
    paths = {(r, p): link for r, p, link in got}
    assert len(paths) == len(got), sorted(paths)
    want = {(arr.Name, "0."): arr, (arr.Name, "1."): arr, (side.Name, f"{ch2.Name}."): ch2, (copy.Name, f"{ch2.Name}."): ch2,
            (sides.Name, f"0.{ch2.Name}."): ch2, (sides.Name, f"1.{ch2.Name}."): ch2}
    assert all(paths.get(k) == v for k, v in want.items()), sorted(paths)
    # hidden array elements get none
    sides.setElementVisible("1", False)
    arr.setElementVisible("0", False)
    paths = {(root.Name, path) for link, (root, path) in snap.placed(doc)}
    assert (sides.Name, f"1.{ch2.Name}.") not in paths and (arr.Name, "0.") not in paths and (arr.Name, "1.") in paths, sorted(paths)
    sides.setElementVisible("1", True)
    arr.setElementVisible("0", True)

    # screw tool, two clicks on two stacked plates
    from freecad.vex_workbench import screws, ui
    p1 = library.place(doc, gen["5x10 Steel Plate"])
    p2 = library.place(doc, gen["5x10 Steel Plate"])
    p2.Placement = App.Placement(App.Vector(0, 0, -0.046 * IN), App.Rotation())
    doc.recompute()
    faces = p1.LinkedObject.Group[0].Shape.Faces
    top = next(k for k, f in enumerate(faces) if f.Surface.TypeId == "Part::GeomPlane" and f.normalAt(0, 0).z > 0.5) + 1
    bottom = next(k for k, f in enumerate(faces) if f.Surface.TypeId == "Part::GeomPlane" and f.normalAt(0, 0).z < -0.5) + 1
    panel = screws.Panel()
    Gui.Control.showDialog(panel)
    panel.kind.setCurrentText("Star")
    panel.mine.setChecked(False)  # whatever the last real use left in the prefs
    panel.nut.setCurrentText(screws.NO_NUT)
    assert not panel.nylon.isEnabled(), "To the nylon with no nut"
    panel.nut.setCurrentText("Nylock Nut")
    assert panel.nylon.isEnabled()
    panel.nylon.setChecked(False)
    panel.fill.setChecked(False)
    before = set(doc.Objects)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, p1.Name, f"Face{top}", 1.26 * IN, 0.25 * IN, 0.046 * IN)
    Gui.Selection.addSelection(doc.Name, p2.Name, f"Face{bottom}", 1.25 * IN, 0.26 * IN, -0.046 * IN)
    QtWidgets.QApplication.processEvents()
    got = sorted(o.Label for o in set(doc.Objects) - before if o.TypeId == "App::Link")
    assert got == ["0.290 Torx (Star) Screw (8-32, Steel)", "Nylock Nut"], got
    assert panel.status.text().startswith("put in a 0.290 Torx (Star) Screw"), panel.status.text()
    fasteners = {o.Name for o in set(doc.Objects) - before if o.TypeId == "App::Link"}
    panel.reject()
    # same clicking the hole points, on a fresh hole. none on the screw and nut
    panel = screws.Panel()
    Gui.Control.showDialog(panel)
    assert not fasteners & {s[0].Name for s in panel.spots}

    def mark(at):
        return next(k for k, p in enumerate(panel.points) if (p - at).Length < 1e-6)

    def click(at):
        # what pressed() does once its found the dot under the mouse
        panel.take(panel.spots[mark(at)])

    before = set(doc.Objects)
    first = App.Vector(3.25, 0.25, 0.046) * IN
    click(first)
    # the picked one stays green, and goes once the screw is in. nothing of the dots in the document
    assert [(p - first).Length < 1e-6 for p in panel.picked] == [True] and panel.lit.point.getNum() == 1, panel.picked
    assert set(doc.Objects) == before
    n = len(panel.points)
    assert panel.marks.point.getNum() == n
    click(App.Vector(3.25, 0.25, -0.046) * IN)
    QtWidgets.QApplication.processEvents()
    got = sorted(library.part_of(o)["name"] for o in set(doc.Objects) - before if o.TypeId == "App::Link")
    assert got == ["0.290 Torx (Star) Screw (8-32, Steel)", "Nylock Nut"], (got, panel.status.text())
    assert not panel.picked and panel.lit.point.getNum() == 0
    # a few on one face, again unpicks. auto finish does all of them off one click across
    panel.auto.setChecked(True)
    before = set(doc.Objects)
    for x in (4.25, 4.75, 3.75, 3.75):
        click(App.Vector(x, 0.75, 0.046) * IN)
    assert len(panel.picked) == 2 and panel.status.text().startswith("2 picked"), panel.status.text()
    click(App.Vector(4.75, 0.75, -0.046) * IN)
    QtWidgets.QApplication.processEvents()
    got = sorted(library.part_of(o)["name"] for o in set(doc.Objects) - before if o.TypeId == "App::Link")
    assert got == ["0.290 Torx (Star) Screw (8-32, Steel)"] * 2 + ["Nylock Nut"] * 2, (got, panel.status.text())
    assert panel.status.text().startswith("put in 2 screws") and not panel.picked, panel.status.text()
    # off, a click across for each. one thats not under any of them does nothing
    panel.auto.setChecked(False)
    before = set(doc.Objects)
    for x in (4.25, 4.75):
        click(App.Vector(x, 1.25, 0.046) * IN)
    click(App.Vector(4.75, 1.25, -0.046) * IN)
    QtWidgets.QApplication.processEvents()
    assert "1 still picked" in panel.status.text() and len(panel.picked) == 1, panel.status.text()
    click(App.Vector(3.25, 1.25, -0.046) * IN)
    assert panel.status.text().startswith("none of them"), panel.status.text()
    click(App.Vector(4.25, 1.25, -0.046) * IN)
    QtWidgets.QApplication.processEvents()
    assert len([o for o in set(doc.Objects) - before if o.TypeId == "App::Link"]) == 4 and not panel.picked, panel.status.text()

    # parts placed or deleted with it open get their points sorted out
    def settle():
        end = time.time() + 5
        while panel.later.isActive() and time.time() < end:
            QtWidgets.QApplication.processEvents()

    extra = library.place(doc, gen["5x10 Steel Plate"])
    extra.Placement.Base = App.Vector(10, 0, 0) * IN
    settle()
    assert len(panel.points) == n + len(library.hole_dots(extra)) == panel.marks.point.getNum(), len(panel.points)
    assert any((p - App.Vector(10.25, 0.25, 0.046) * IN).Length < 1e-6 for p in panel.points)
    doc.removeObject(extra.Name)
    settle()
    assert len(panel.points) == n
    # and hiding one element of an array
    arr.setElementVisible("0", False)
    assert panel.later.isActive()
    settle()
    assert len(panel.points) == n - len(library.hole_dots(arr)), len(panel.points)
    arr.setElementVisible("0", True)
    settle()
    # looking staright down, a click on a hole gets its top dot not the one under it, and a miss gets nothing
    view = Gui.ActiveDocument.ActiveView
    view.viewTop()
    view.fitAll()
    region = view.getViewer().getSoRenderManager().getViewportRegion()
    screen = panel.on_screen(region)
    assert len({(round(x), round(y)) for x, y, _ in screen}) > 100, region.getViewportSizePixels().getValue()  # really spread out, not all on one px
    k = mark(App.Vector(3.75, 0.25, 0.046) * IN)
    assert panel.points[snap.nearest(screen, screen[mark(App.Vector(3.75, 0.25, 0) * IN)][:2])] == panel.points[k]
    assert snap.nearest(screen, (-100, -100)) is None
    from pivy import coin

    # the one matmul lands where coin puts them one at a time
    vv = view.getCameraNode().getViewVolume(region.getViewportAspectRatio())
    w, h = region.getViewportSizePixels().getValue()
    for i in (0, k, len(screen) - 1):
        p = panel.points[i]
        s = vv.projectToScreen(coin.SbVec3f(p.x, p.y, p.z)).getValue()
        assert abs(s[0] * w - screen[i][0]) < 0.01 and abs(s[1] * h - screen[i][1]) < 0.01, (s, screen[i])

    # through the viewer like a real event would go
    def send(ev, x, y):
        ev.setPosition(coin.SbVec2s(round(x), round(y)))
        act = coin.SoHandleEventAction(region)
        act.setEvent(ev)
        act.apply(view.getViewer().getSoRenderManager().getSceneGraph())

    # a real press + release 2 px off that dot
    def mouse(state, x, y):
        ev = coin.SoMouseButtonEvent()
        ev.setButton(coin.SoMouseButtonEvent.BUTTON1)
        ev.setState(state)
        send(ev, x, y)

    # isHandled() is no use here, FreeCAD's own selection node marks every press handled
    Gui.Selection.clearSelection()
    mouse(coin.SoButtonEvent.DOWN, screen[k][0] + 2, screen[k][1])
    mouse(coin.SoButtonEvent.UP, screen[k][0] + 2, screen[k][1])  # FreeCAD selects the edge under it here
    QtWidgets.QApplication.processEvents()
    assert [(p - panel.points[k]).Length < 1e-6 for p in panel.picked] == [True] and panel.first, panel.picked
    assert not Gui.Selection.getSelectionEx(), [s.SubElementNames for s in Gui.Selection.getSelectionEx()]  # and that got dropped
    # nowhere near a dot changes nothing
    mouse(coin.SoButtonEvent.DOWN, 1, 1)
    mouse(coin.SoButtonEvent.UP, 1, 1)
    assert len(panel.picked) == 1, panel.picked

    # hovering lights the one a click would take, yellow, and nothing off the dots. second time writing this test. love that
    def move(x, y):
        send(coin.SoLocation2Event(), x, y)

    move(screen[k][0] + 2, screen[k][1])
    assert panel.under == k and panel.hover.point.getNum() == 1, panel.under
    assert (App.Vector(*panel.hover.point[0].getValue()) - panel.points[k]).Length < 1e-3
    move(1, 1)
    assert panel.under is None and panel.hover.point.getNum() == 0
    overlay, root = panel.overlay, view.getSceneGraph()
    panel.reject()
    assert root.findChild(overlay) == -1
    # picked by hand: one click, that screw, no nut. shoulder screws only go in that way
    panel = screws.Panel()
    Gui.Control.showDialog(panel)
    panel.kind.setCurrentText("Star")
    panel.mine.setChecked(True)
    panel.size.setCurrentText("0.500 Torx (Star) Screw (8-32, Steel)")
    assert panel.status.text().startswith(panel.ONE) and not panel.nut.isEnabled()
    for name, at in (("0.500 Torx (Star) Screw (8-32, Steel)", 0.75), ("0.500, 0.18 Robosource Shoulder Screw (8-32, Steel)", 1.75)):
        if "Shoulder" in name:
            panel.kind.setCurrentText("Shoulder")
            assert panel.mine.isChecked() and not panel.mine.isEnabled()
            panel.size.setCurrentText(name)
        before = set(doc.Objects)
        click(App.Vector(at, 0.25, 0.046) * IN)
        QtWidgets.QApplication.processEvents()
        got = [library.part_of(o)["name"] for o in set(doc.Objects) - before if o.TypeId == "App::Link"]
        assert got == [name], (got, panel.status.text())
    # back off shoulder the box goes back to how it was
    panel.kind.setCurrentText("Star")
    panel.mine.setChecked(False)
    panel.kind.setCurrentText("Shoulder")
    # and placing one doesnt save the forced tick over it
    click(App.Vector(2.75, 0.25, 0.046) * IN)
    QtWidgets.QApplication.processEvents()
    assert not App.ParamGet(ui.PARAMS).GetBool("ScrewMine", True)
    panel.kind.setCurrentText("Star")
    assert panel.mine.isEnabled() and not panel.mine.isChecked()
    panel.reject()
    # spacer panel, the plates 0.25 apart now
    from freecad.vex_workbench import spacers
    p2.Placement = App.Placement(App.Vector(0, 0, -0.296 * IN), App.Rotation())
    doc.recompute()
    panel = spacers.Panel()
    Gui.Control.showDialog(panel)
    panel.od.setCurrentText("0.375")
    before = set(doc.Objects)
    Gui.Selection.addSelection(doc.Name, p1.Name, f"Face{bottom}", 2.26 * IN, 0.25 * IN, 0)
    Gui.Selection.addSelection(doc.Name, p2.Name, f"Face{top}", 2.25 * IN, 0.26 * IN, -0.25 * IN)
    QtWidgets.QApplication.processEvents()
    got = [o.Label for o in set(doc.Objects) - before if o.TypeId == "App::Link"]
    assert got == ["0.375 OD Spacer, 0.250 (Nylon)"], (got, panel.status.text())
    panel.reject()
    # align panel, bottom (1.25, 0.25) hole on p2 onto the one on top of p1 by their points, 0.125 off, then turned 45 and regapped
    from freecad.vex_workbench import align
    panel = align.Panel()
    Gui.Control.showDialog(panel)
    panel.gap.setValue(0.125)
    panel.angle.setValue(45)
    below = App.Vector(1.25, 0.25, 0) * IN  # bottom face of p2, its own coords
    up = App.Vector(1.25, 0.25, 0.046) * IN  # top of p1, it sits at 0
    click(p2.Placement.multVec(below))
    click(up)
    QtWidgets.QApplication.processEvents()
    assert panel.last and "lined up" in panel.status.text(), panel.status.text()

    def frames():
        return snap.hole((p1, up, p1.Placement, (p1, "")))[1], snap.hole((p2, below, p2.Placement, (p2, "")))[1]

    at, got = frames()
    assert abs(got.Base.z - at.Base.z - 0.125 * IN) < 1e-9 and (got.Base - at.Base).cross(App.Vector(0, 0, 1)).Length < 1e-9, got.Base
    assert abs(got.Rotation.multVec(App.Vector(0, 0, 1)).z + 1) < 1e-9  # facing back down onto p1
    x0 = got.Rotation.multVec(App.Vector(1, 0, 0))
    panel.turn(1)
    panel.gap.setValue(0.25)
    at, got = frames()
    assert abs(got.Base.z - at.Base.z - 0.25 * IN) < 1e-9, got.Base
    assert abs(got.Rotation.multVec(App.Vector(1, 0, 0)).dot(x0) - math.cos(math.radians(45))) < 1e-9
    panel.reject()
    # a link array moves whole, so the hole on element 1 (100 over in the array) lands
    hole = library.hole_dots(arr)[0]

    def elem():
        return (arr, hole, arr.getSubObject("1.", retType=3), (arr, "1."))

    align.align(elem(), (p1, up, p1.Placement, (p1, "")), 0)
    doc.recompute()
    at, got = snap.hole((p1, up, p1.Placement, (p1, "")))[1], snap.hole(elem())[1]
    assert (got.Base - at.Base).Length < 1e-9 and abs(got.Rotation.multVec(App.Vector(0, 0, 1)).z + 1) < 1e-9, (got, at)
    p2.Placement = App.Placement(App.Vector(0, 0, -0.046 * IN), App.Rotation())
    doc.recompute()
    # bend panel, one click on a dot folds a plate there, the angle box redoes that bend and the button turns the other side
    from freecad.vex_workbench import shop
    sheet = library.place(doc, gen["5x10 Steel Plate"])
    sheet.Placement.Base = App.Vector(0, 300, 0)
    doc.recompute()
    panel = shop.BendPanel()
    Gui.Control.showDialog(panel)
    panel.radius.setValue(0.032)  # whatever the last real use left in the prefs
    panel.sits.setCurrentIndex(0)
    panel.across.setCurrentText("Across")
    panel.off.setValue(0)
    panel.angle.setValue(90)
    click(App.Vector(2.25 * IN, 300 + 0.25 * IN, 0.046 * IN))
    QtWidgets.QApplication.processEvents()
    assert panel.last == (sheet, 1) and len(library.steps(sheet)) == 1, panel.status.text()
    up = Part.getShape(sheet.LinkedObject).BoundBox.ZMax
    panel.angle.setValue(45)
    assert len(library.steps(sheet)) == 1 and Part.getShape(sheet.LinkedObject).BoundBox.ZMax < up - 1
    next(w for w in panel.form.findChildren(QtWidgets.QPushButton) if w.text() == "Other side turns").click()
    assert library.steps(sheet)[0]["side"] == -1 and library.steps(sheet)[0]["angle"] == 45, library.steps(sheet)
    # the redos dont leave old bent sources lying around
    bent = [o for o in library.group(doc).Group if getattr(o, "VexSteps", "")]
    assert bent == [sheet.LinkedObject], [o.Label for o in bent]
    panel.reject()
    # cut panel takes the end off another plate at a dot, the button keeps the other side. then drill a hole in it by a face click
    stock = library.place(doc, gen["5x10 Steel Plate"])
    stock.Placement.Base = App.Vector(0, 400, 0)
    doc.recompute()
    panel = shop.CutPanel()
    Gui.Control.showDialog(panel)
    panel.mode.setCurrentIndex(0)
    panel.across.setCurrentText("Across")
    panel.off.setValue(0)
    click(App.Vector(3.75 * IN, 400 + 0.25 * IN, 0.046 * IN))
    QtWidgets.QApplication.processEvents()
    assert [s["do"] for s in library.steps(stock)] == ["cut"], panel.status.text()
    assert abs(Part.getShape(stock.LinkedObject).BoundBox.XMax - 3.75 * IN) < 0.01
    next(w for w in panel.form.findChildren(QtWidgets.QPushButton) if w.text() == "Keep the other side").click()
    assert abs(Part.getShape(stock.LinkedObject).BoundBox.XMin - 3.75 * IN) < 0.01
    panel.reject()
    panel = shop.DrillPanel()
    Gui.Control.showDialog(panel)
    panel.size.setValue(0.17)
    panel.grid.setValue(0.25)  # whatever the last real use left in the prefs
    panel.show_grid.setChecked(False)
    Gui.Selection.addSelection(doc.Name, stock.Name, f"Face{top}", 4.07 * IN, 400 + 0.29 * IN, 0.046 * IN)
    QtWidgets.QApplication.processEvents()
    got = library.steps(stock)
    assert [s["do"] for s in got] == ["cut", "drill"], panel.status.text()
    assert (App.Vector(*got[1]["c"]) - App.Vector(4, 0.25, 0.046) * IN).Length < 1e-6, got[1]["c"]
    # showing the grid puts a dot between the holes, and a click on it drills right there
    holes_only = len(panel.points)
    panel.show_grid.setChecked(True)
    between = App.Vector(4.5 * IN, 400 + 0.25 * IN, 0.046 * IN)
    assert len(panel.points) > holes_only and any((p - between).Length < 1e-6 for p in panel.points), len(panel.points)
    click(between)
    QtWidgets.QApplication.processEvents()
    got = library.steps(stock)
    assert len(got) == 3 and (App.Vector(*got[2]["c"]) - App.Vector(4.5, 0.25, 0.046) * IN).Length < 1e-6, got[-1]["c"]
    quarter = len(panel.points)
    # none on the ends, the cut one at 3.75 is right on the grid
    b = Part.getShape(stock.LinkedObject).BoundBox
    assert not [p for p in panel.extra(stock) if min(abs(p.x - b.XMin), abs(p.x - b.XMax)) < 1e-6], b
    panel.grid.setValue(0.125)
    assert len(panel.points) > quarter, (len(panel.points), quarter)
    # 0.2 doesnt go into the 0.5 pitch, the dots it does show still drill right there
    panel.grid.setValue(0.2)
    spots = panel.extra(stock)
    moved = [p for p in spots[::10] if (App.Vector(*shop.drill(stock, p, 0.17 * IN, 0.2 * IN)["c"]) - p).Length > 1e-6]
    assert spots and not moved, (len(spots), moved)
    panel.show_grid.setChecked(False)
    panel.grid.setValue(0.25)
    # an LS gear's hub face drills out its bore, the color most of it was all over
    gear = library.place(doc, steps["Motion/Gears/Low Strength/12T Gear (276-2169-001).step"])
    gear.Placement.Base = App.Vector(0, 600, 0)
    doc.recompute()
    was = next(o for o in gear.LinkedObject.Group if o.TypeId == "Part::Feature").ViewObject.DiffuseColor
    hub = App.Vector(0.07 * IN, 600 + 0.07 * IN, 0.1875 * IN)
    k = next(i for i, f in enumerate(Part.getShape(gear).Faces, 1) if f.distToShape(Part.Vertex(hub))[0] < 1e-6)
    Gui.Selection.addSelection(doc.Name, gear.Name, f"Face{k}", hub.x, hub.y, hub.z)
    QtWidgets.QApplication.processEvents()
    got = library.steps(gear)
    assert len(got) == 1 and App.Vector(*got[0]["c"]).isEqual(App.Vector(0, 0, 0.1875) * IN, 1e-6), (got, panel.status.text())
    now = next(o for o in gear.LinkedObject.Group if o.TypeId == "Part::Feature").ViewObject.DiffuseColor
    assert set(now) == {max(set(was), key=was.count)}, (set(now), set(was))
    # the grid it snaps to shows on the gear too
    panel.show_grid.setChecked(True)
    assert panel.extra(gear), "no grid on the gear"
    panel.show_grid.setChecked(False)
    panel.reject()
    # click a flange's hole then slide the line onto the web, the side gets picked again for the new line so the flange goes
    chan = library.place(doc, gen["1x2x1x10 Steel C-Channel"])
    chan.Placement.Base = App.Vector(0, 500, 0)
    doc.recompute()
    plain = Part.getShape(chan.LinkedObject).Volume
    panel = shop.CutPanel()
    Gui.Control.showDialog(panel)
    panel.mode.setCurrentIndex(0)
    panel.across.setCurrentText("Along")
    panel.off.setValue(0)
    click(App.Vector(2.25 * IN, 500 + 0.25 * IN, 0))
    QtWidgets.QApplication.processEvents()
    # Off the hole slides along n x d, whichever way that points the web is +y. a wrong way would pop an error box nobody closes offscreen
    s = library.steps(chan)[0]
    panel.off.setValue(0.25 if App.Vector(*s["n"]).cross(App.Vector(*s["d"])).y > 0 else -0.25)
    s = Part.getShape(chan.LinkedObject)
    assert len(library.steps(chan)) == 1 and len(s.Solids) == 1 and abs(s.Volume / plain - 0.732) < 0.01, (s.Volume / plain, panel.status.text())
    # keeping the other side there is two pieces, refused. the button stays unflipped for the next slide
    said, warning = [], QtWidgets.QMessageBox.warning
    QtWidgets.QMessageBox.warning = lambda *a: said.append(a[2])
    try:
        side = library.steps(chan)[0]["side"]
        next(w for w in panel.form.findChildren(QtWidgets.QPushButton) if w.text() == "Keep the other side").click()
    finally:
        QtWidgets.QMessageBox.warning = warning
    assert said and "more than one piece" in said[0] and library.steps(chan)[0]["side"] == side and panel.flipped == 1, (said, panel.flipped)
    # two points, edge dot to edge dot across a plate is cut to length. the button keeps the short end, the kerf box redoes it
    saw = library.place(doc, gen["5x10 Steel Plate"])
    saw.Placement.Base = App.Vector(0, 600, 0)
    doc.recompute()
    panel.mode.setCurrentIndex(1)
    panel.kerf.setValue(0.04)
    panel.show_grid.setChecked(False)
    assert not panel.across.isEnabled() and panel.status.text().startswith("click where the cut starts")
    click(App.Vector(3.75 * IN, 600, 0.046 * IN))
    click(App.Vector(3.75 * IN, 600 + 2.5 * IN, 0.046 * IN))
    QtWidgets.QApplication.processEvents()
    assert [s["do"] for s in library.steps(saw)] == ["slot"], panel.status.text()
    assert abs(Part.getShape(saw.LinkedObject).BoundBox.XMax - 3.73 * IN) < 1e-6
    next(w for w in panel.form.findChildren(QtWidgets.QPushButton) if w.text() == "Keep the other side").click()
    assert abs(Part.getShape(saw.LinkedObject).BoundBox.XMin - 3.77 * IN) < 1e-6
    panel.kerf.setValue(0.06)
    assert abs(Part.getShape(saw.LinkedObject).BoundBox.XMin - 3.78 * IN) < 1e-6 and len(library.steps(saw)) == 1
    # a face click snaps to the grid on its own click
    assert (panel.snapped(saw, App.Vector(4.07, 0.29, 0.046) * IN) - App.Vector(4, 0.25, 0.046) * IN).Length < 1e-6
    # sketch it, a click on a hole starts a sketch there and closes the panel. closing the sketch cuts its circle out
    pocket = library.place(doc, gen["5x10 Steel Plate"])
    pocket.Placement.Base = App.Vector(0, 700, 0)
    doc.recompute()
    plain = Part.getShape(pocket.LinkedObject).Volume
    panel.mode.setCurrentIndex(2)
    assert panel.status.text().startswith("click the face to sketch on") and not panel.kerf.isEnabled()
    click(App.Vector(2.25 * IN, 700 + 0.75 * IN, 0.046 * IN))
    QtWidgets.QApplication.processEvents()
    QtWidgets.QApplication.processEvents()
    sk = next(o for o in doc.Objects if getattr(o, "VexCut", None) == pocket)
    assert Gui.ActiveDocument.getInEdit() == sk.ViewObject and Gui.Control.activeDialog()
    assert (sk.Placement.Base - App.Vector(2.25 * IN, 700 + 0.75 * IN, 0.046 * IN)).Length < 1e-6, sk.Placement
    circle = sk.addGeometry(Part.Circle(App.Vector(), App.Vector(0, 0, 1), 0.3 * IN))

    def closing():
        Gui.ActiveDocument.resetEdit()
        for _ in range(3):
            QtWidgets.QApplication.processEvents()
    closing()
    lost = plain - Part.getShape(pocket.LinkedObject).Volume
    assert [s["do"] for s in library.steps(pocket)] == ["sketch"] and not sk.Visibility, library.steps(pocket)
    assert 0 < lost < math.pi * (0.3 * IN) ** 2 * 0.046 * IN, lost  # the holes in it were already gone
    # edit it again, same step a size bigger
    Gui.ActiveDocument.setEdit(sk)
    QtWidgets.QApplication.processEvents()
    sk.setDatum(sk.addConstraint(Sketcher.Constraint("Radius", circle, 0.3 * IN)), App.Units.Quantity(0.45 * IN, App.Units.Length))
    closing()
    assert len(library.steps(pocket)) == 1 and plain - Part.getShape(pocket.LinkedObject).Volume > lost * 1.5
    # it follows the copy, and deleteing it puts the metal back
    pocket.Placement.Base = App.Vector(0, 800, 0)
    doc.recompute()
    assert abs(sk.Placement.Base.y - 800 - 0.75 * IN) < 1e-6, sk.Placement
    doc.removeObject(sk.Name)
    QtWidgets.QApplication.processEvents()
    assert library.steps(pocket) == [] and abs(Part.getShape(pocket.LinkedObject).Volume - plain) < 1e-6
    # opened again it comes up in sketch mode, prompt and all
    panel = shop.CutPanel()
    Gui.Control.showDialog(panel)
    assert panel.status.text().startswith("click the face to sketch on"), panel.status.text()
    panel.mode.setCurrentIndex(0)
    panel.reject()
    # same in an assembly gets joints, with their view providers
    asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
    asm.Type = "Assembly"
    for p in (p1, p2):
        asm.addObject(p)
    doc.recompute()
    head = snap.spot(asm, f"{p1.Name}.Face{top}", App.Vector(1.26, 0.25, 0.046) * IN)
    tail = snap.spot(asm, f"{p2.Name}.Face{bottom}", App.Vector(1.25, 0.26, -0.046) * IN)
    sc, nut, _ = screws.fasten(doc, head, tail, "star-screw", screws.nuts()["Nylock Nut"], asm)
    js = [j for j in asm.OutListRecursive if hasattr(j, "JointType")]
    assert sorted(j.Reference2[0].Name for j in js) == sorted([sc.Name, nut.Name]), js
    assert all(j.ViewObject.Proxy for j in js)
    # align panel with the assembly active, just a move, Rotate + and Flip after it
    import JointObject
    import UtilsAssembly
    JointObject.GroundedJoint(UtilsAssembly.getJointGroup(asm).newObject("App::FeaturePython", "Ground"), p1)
    swing = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
    doc.recompute()
    Gui.ActiveDocument.ActiveView.setActiveObject("part", asm)
    joints = len(UtilsAssembly.getJointGroup(asm).Group)
    panel = align.Panel()
    Gui.Control.showDialog(panel)
    panel.angle.setValue(90)
    panel.gap.setValue(0)
    hole = library.hole_dots(swing)[0]
    mover = (swing, hole, asm.getSubObject(swing.Name + ".", retType=3), (asm, swing.Name + "."))
    on = (p1, App.Vector(2.25, 1.25, 0.046) * IN, p1.Placement, (asm, p1.Name + "."))
    panel.act(mover, on)
    yaw = swing.Placement.Rotation.toEuler()[0]
    panel.turn(1)
    assert abs((swing.Placement.Rotation.toEuler()[0] - yaw) % 360 - 90) < 1e-6, (yaw, swing.Placement)
    flip = next(w for w in panel.form.findChildren(QtWidgets.QPushButton) if w.text() == "Flip")
    flip.click()
    flip.click()
    now = (swing, hole, asm.getSubObject(swing.Name + ".", retType=3), (asm, swing.Name + "."))
    assert (snap.hole(now)[1].Base - snap.hole(on)[1].Base).Length < 1e-6, "flipped twice and its not back"
    assert len(UtilsAssembly.getJointGroup(asm).Group) == joints, "align made a joint"
    panel.reject()
    # joint panel, a slide's end on the other face keeps it waiting for a good one
    from freecad.vex_workbench import joints as jt
    panel = jt.Panel()
    Gui.Control.showDialog(panel)
    panel.kind.setCurrentText("Slide")
    panel.take(now)
    panel.take(on)
    panel.take((p1, App.Vector(3.25, 1.25, -0.046) * IN, p1.Placement, (asm, p1.Name + ".")))
    assert panel.mid is not None and panel.status.text().startswith("click another hole on the same face"), panel.status.text()
    panel.take((p1, App.Vector(4.25, 1.25, 0.046) * IN, p1.Placement, (asm, p1.Name + ".")))
    QtWidgets.QApplication.processEvents()
    k = UtilsAssembly.getJointGroup(asm).Group[-1]
    assert k.JointType == "Slider" and panel.mid is None and panel.status.text().startswith("slide joint"), panel.status.text()
    doc.removeObject(k.Name)
    # spin, it stays there for the duplicate checks
    panel.kind.setCurrentText("Spin")
    panel.take(now)
    panel.take(on)
    QtWidgets.QApplication.processEvents()
    assert UtilsAssembly.getJointGroup(asm).Group[-1].JointType == "Revolute", panel.status.text()
    panel.reject()
    # duplicate panel, the swinging channel mirrored across the assembly's YZ plane lands in it with the same source. its plate doesnt reach over there, so its joint stays
    from freecad.vex_workbench import duplicate
    panel = duplicate.Panel()
    Gui.Control.showDialog(panel)
    panel.how.setCurrentText("Mirror")
    panel.axis.setCurrentText("X")
    had = set(doc.Objects)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(swing)
    panel.go()
    cp = [o for o in doc.Objects if o not in had and duplicate.vex(o)]
    assert len(cp) == 1 and cp[0].LinkedObject == swing.LinkedObject and cp[0] in asm.Group, cp
    assert panel.status.text() == "copied 1. 1 joint couldn't come along, joint it again", panel.status.text()
    # no stry frame on the channel's end of that joint, and one undo takes the copy back out
    new = [o for o in doc.Objects if o not in had]
    assert not any(o.TypeId == "App::LocalCoordinateSystem" for o in new), [o.Label for o in new]
    doc.undo()
    assert set(doc.Objects) == had, [o.Label for o in set(doc.Objects) - had]
    # across the plate's middle its joint comes along onto the mirror hole, one undo takes the copy, joint and new frames back out
    panel.at.setValue(2.5)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(swing)
    panel.go()
    assert panel.status.text() == "copied 1. 1 joint came along", panel.status.text()
    k = UtilsAssembly.getJointGroup(asm).Group[-1]
    on = p1.LinkedObject.getObject(k.Reference1[1][0].rstrip("."))
    assert k.JointType == "Revolute" and k.Reference1[0] == p1 and on not in had, (k.JointType, k.Reference1)
    assert (on.Placement.Base - App.Vector(2.75, 1.25, 0.046) * IN).Length < 1e-6, on.Placement.Base / IN
    doc.undo()
    assert set(doc.Objects) == had, [o.Label for o in set(doc.Objects) - had]
    panel.reject()
    say("ok")
    failed = False
except BaseException:  # Ctrl-C and sys.exit too, or the os._exit below never runs
    say(traceback.format_exc())
    failed = True
shutil.rmtree(breps, ignore_errors=True)
# closing the window always exits 0, and hangs offscreen once an assembly joint has solved, plain one too
os._exit(1 if failed else 0)
