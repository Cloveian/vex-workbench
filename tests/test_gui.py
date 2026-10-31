# toolbar, colurs, the parts list, the dock, the screw and align tools and snapping through link arrays and linked sub-assemblies inside the gui (needs vex-step/), run with: env QT_QPA_PLATFORM=offscreen freecad -M . tests/test_gui.py
import math
import os
import sys
import time
import traceback
import zipfile

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
    (link, pt, *_), = snap.picked()
    assert (pt - click).Length < 1e-6, (path, pt, click)
    frame = library.hole_frame(link, pt)
    assert (frame.Placement.Base - center).Length < 1e-6, (path, frame.Placement.Base, center)
    return link


try:
    from freecad.vex_workbench import catalog, library
    from freecad.vex_workbench.metal import IN

    Gui.activateWorkbench("VexWorkbench")
    bar = Gui.getMainWindow().findChild(QtWidgets.QToolBar, "VEX")
    tools = [a.text() for a in bar.actions()]
    assert tools == ["VEX parts", "Frame on hole", "Align", "Screw", "Spacers", "Parts list"], tools

    doc = App.newDocument("vexgui")
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
    assert tops == {(0.96, 0.0, 0.01)} and rest == {steel}, (tops, rest)
    got = plain.LinkedObject.Group[0].ViewObject.ShapeColor[:3]
    assert all(abs(a - b) < 1e-6 for a, b in zip(got, steel)), got
    # a spacer's seam lines are nylon colored so they dont show, its end circles keep their lines
    sp = library.place(doc, gen["0.375 OD Spacer, 0.250 (Nylon)"])
    s, vo = sp.LinkedObject.Group[0].Shape, sp.LinkedObject.Group[0].ViewObject
    seam = {e.hashCode() for f in s.Faces for e in f.Edges if e.isSeam(f)}
    nylon = tuple(library.cat()["colors"]["Nylon"])
    got = {(e.hashCode() in seam, tuple(round(v, 2) for v in c[:3])) for e, c in zip(s.Edges, vo.LineColorArray)}
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
    from freecad.vex_workbench import screws
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
    panel.nut.setCurrentText("Nylock Nut")
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
        return next(f"Vertex{k + 1}" for k, v in enumerate(panel.marks.Shape.Vertexes) if (v.Point - at).Length < 1e-6)

    before = set(doc.Objects)
    first = App.Vector(3.25, 0.25, 0.046) * IN
    Gui.Selection.addSelection(doc.Name, panel.marks.Name, mark(first))
    # the picked one stays green, and goes once the screw is in
    assert [(v.Point - first).Length < 1e-6 for v in panel.lit.Shape.Vertexes] == [True], panel.lit.Shape.Vertexes
    # saving with the panel open leaves the points out of the file, and puts them back
    n = len(panel.marks.Shape.Vertexes)
    saved = os.path.join(os.path.dirname(__file__), "_points.FCStd")
    try:
        doc.saveAs(saved)
        assert len(panel.marks.Shape.Vertexes) == n and len(panel.lit.Shape.Vertexes) == 1
        # openDocument would just hand back doc, its open on that file now
        with zipfile.ZipFile(saved) as z:
            xml = z.read("Document.xml").decode()
        assert "VexHoles" not in xml and "VexPicked" not in xml and 'name="VexPart"' in xml
    finally:
        os.remove(saved)
    # a failed save gets them back too
    ro = os.path.join(os.path.dirname(__file__), "_readonly")
    os.makedirs(ro, exist_ok=True)
    os.chmod(ro, 0o500)
    try:
        doc.saveAs(os.path.join(ro, "x.FCStd"))
    except OSError:
        pass
    finally:
        os.chmod(ro, 0o700)
        os.rmdir(ro)
    QtWidgets.QApplication.processEvents()
    assert panel.marks and len(panel.marks.Shape.Vertexes) == n and len(panel.lit.Shape.Vertexes) == 1
    Gui.Selection.addSelection(doc.Name, panel.marks.Name, mark(App.Vector(3.25, 0.25, -0.046) * IN))
    QtWidgets.QApplication.processEvents()
    got = sorted(library.part_of(o)["name"] for o in set(doc.Objects) - before if o.TypeId == "App::Link")
    assert got == ["0.290 Torx (Star) Screw (8-32, Steel)", "Nylock Nut"], (got, panel.status.text())
    assert not panel.lit.Shape.Vertexes

    # parts placed or deleted with it open get their points sorted out
    def settle():
        end = time.time() + 5
        while panel.later.isActive() and time.time() < end:
            QtWidgets.QApplication.processEvents()

    extra = library.place(doc, gen["5x10 Steel Plate"])
    extra.Placement.Base = App.Vector(10, 0, 0) * IN
    settle()
    assert len(panel.marks.Shape.Vertexes) == n + len(library.screw_holes(extra)), len(panel.marks.Shape.Vertexes)
    assert any((v.Point - App.Vector(10.25, 0.25, 0.046) * IN).Length < 1e-6 for v in panel.marks.Shape.Vertexes)
    doc.removeObject(extra.Name)
    settle()
    assert len(panel.marks.Shape.Vertexes) == n
    # and hiding one element of an array
    arr.setElementVisible("0", False)
    assert panel.later.isActive()
    settle()
    assert len(panel.marks.Shape.Vertexes) == n - len(library.screw_holes(arr)), len(panel.marks.Shape.Vertexes)
    arr.setElementVisible("0", True)
    settle()
    dots = [panel.marks.Name, panel.lit.Name]
    panel.reject()
    assert not any(doc.getObject(n) for n in dots)
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
    Gui.Selection.addSelection(doc.Name, panel.marks.Name, mark(p2.Placement.multVec(below)))
    Gui.Selection.addSelection(doc.Name, panel.marks.Name, mark(up))
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
    hole = library.screw_holes(arr)[0]

    def elem():
        return (arr, hole, arr.getSubObject("1.", retType=3), (arr, "1."))

    align.align(elem(), (p1, up, p1.Placement, (p1, "")), 0)
    doc.recompute()
    at, got = snap.hole((p1, up, p1.Placement, (p1, "")))[1], snap.hole(elem())[1]
    assert (got.Base - at.Base).Length < 1e-9 and abs(got.Rotation.multVec(App.Vector(0, 0, 1)).z + 1) < 1e-9, (got, at)
    p2.Placement = App.Placement(App.Vector(0, 0, -0.046 * IN), App.Rotation())
    doc.recompute()
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
    # align panel with the assembly active, Rotate + has to get through the joint's presolve
    import JointObject
    import UtilsAssembly
    JointObject.GroundedJoint(UtilsAssembly.getJointGroup(asm).newObject("App::FeaturePython", "Ground"), p1)
    swing = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
    doc.recompute()
    Gui.ActiveDocument.ActiveView.setActiveObject("part", asm)
    panel = align.Panel()
    Gui.Control.showDialog(panel)
    panel.angle.setValue(90)
    panel.gap.setValue(0)
    hole = library.screw_holes(swing)[0]
    panel.act((swing, hole, asm.getSubObject(swing.Name + ".", retType=3), (asm, swing.Name + ".")),
              (p1, App.Vector(3.25, 1.25, 0.046) * IN, p1.Placement, (asm, p1.Name + ".")))
    yaw = swing.Placement.Rotation.toEuler()[0]
    panel.turn(1)
    assert abs((swing.Placement.Rotation.toEuler()[0] - yaw) % 360 - 90) < 1e-6, (yaw, swing.Placement)
    # turned another 45 and gapped 0.125 in the joint panel, the next Rotate + goes on from there and keeps the gap
    j = panel.last["joint"]
    j.Offset2 = App.Placement(App.Vector(0, 0, 0.125 * IN), App.Rotation(j.Offset2.Rotation.toEuler()[0] + 45, 0, 0))
    doc.recompute()
    panel.turn(1)
    assert abs((swing.Placement.Rotation.toEuler()[0] - yaw) % 360 - 225) < 1e-6, (yaw, swing.Placement)
    assert abs(panel.gap.value() - 0.125) < 1e-9 and abs(j.Offset2.Base.z - 0.125 * IN) < 1e-9, (panel.gap.value(), j.Offset2)
    panel.reject()
    say("ok")
    failed = False
except Exception:
    say(traceback.format_exc())
    failed = True
# closing the window always exits 0, and hangs offscreen once an assembly joint has solved, plain one too
os._exit(1 if failed else 0)
