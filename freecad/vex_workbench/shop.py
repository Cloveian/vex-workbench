# shop work on placed metal, bend or cut on a line through a hole or drill one anywhere. kept on that one copy as steps
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from PySide import QtCore, QtWidgets

from . import library, metal, snap, ui
from .metal import IN, X

GRID = 0.25 * IN  # mm, drilled holes snap to the half pitch off a hole on that face


def wall(link, center, n):
    # thicknes at a hole, from its loop on the other face
    deep = [(center - c).dot(n) for _, c, m in library.cached(link.LinkedObject, library.holes)
            if m.dot(n) < -0.99 and (center - c).cross(n).Length < 1e-3 and (center - c).dot(n) > 1e-6]
    if not deep:
        raise ValueError(f"can't tell how thick {link.Label} is there, click a hole that goes all the way through")
    return min(deep)


def length(n, before):
    # the part's length on a face out along n. its x, but on a leg an earlier bend stood square to x, its that bend's face normal
    for way in [X] + [Vector(*s["n"]) for s in reversed(before) if s["do"] == "fold"]:
        along = way - n * n.dot(way)
        if along.Length > 1e-6:
            along.normalize()
            return along
    raise ValueError("that's an end face, pick a hole on a side")


def line(center, n, across, off, before):
    # point and direction of a line through the hole, across the length or along it, off mm to the side
    along = length(n, before)
    d = n.cross(along) if across else along
    return center + n.cross(d) * off, d


def lined(link, pt, across, off, do):
    # a step on a line through the hole nearest pt. the smaller side is the one that turns or goes
    center, n = library.hole_at(link, pt)
    p, d = line(center, n, across, off, library.steps(link))
    t = wall(link, center, n)
    shape = Part.getShape(link.LinkedObject)
    # just whats cut off the clicked wall counts, a far flange the plane slices through stays put either way
    past = sum(x.Volume for x in metal.split(shape, p, n.cross(d), n, t)[1])
    return {"do": do, "p": list(p), "d": list(d), "n": list(n), "t": t, "center": list(center),
            "side": 1 if past < shape.Volume / 2 else -1}


def bend(link, pt, across, off, angle):
    cat = library.cat()["metal"]
    return dict(lined(link, pt, across, off, "fold"), angle=angle, r=cat["bend"] * IN, k=cat["k"])


def cut(link, pt, across, off):
    return lined(link, pt, across, off, "cut")


def drill(link, pt, dia, snapped=True):
    # a hole at pt (link coords) through the wall its on. snapped onto the grid off the nearest hole on that face
    src = link.LinkedObject
    shape = Part.getShape(src)
    v = Part.Vertex(pt)
    face = min((f for f in shape.Faces if f.Surface.TypeId == "Part::GeomPlane"), key=lambda f: f.distToShape(v)[0])
    n = face.normalAt(0, 0)
    c = pt - n * n.dot(pt - face.Vertexes[0].Point)
    near = [h for _, h, m in library.cached(src, library.holes) if m.dot(n) > 1 - 1e-6 and abs(n.dot(h - c)) < 1e-6]
    if near:
        h = min(near, key=lambda h: (h - c).Length)
        t = wall(link, h, n)  # off a hole, a plate's grid spots are small holes already so a ray there finds nothing
        if snapped:
            e1 = length(n, library.steps(link))
            e2 = n.cross(e1)
            c = h + e1 * round((c - h).dot(e1) / GRID) * GRID + e2 * round((c - h).dot(e2) / GRID) * GRID
    else:
        # no hole on that face, a ray in to the first face it leaves through
        hits = library.hits(library.cached(src, library.boxed), c + n * library.OUT, -n, shape.BoundBox.DiagonalLength)
        if len(hits) < 2:
            raise ValueError("can't find the other side of the wall there")
        t = hits[1] - hits[0]
    return {"do": "drill", "c": list(c), "n": list(n), "dia": dia, "t": t}


class Clicked(snap.Clicks):
    # one click makes a step on that copy, then the boxes (and the button, side -1) redo the last one. step() builds it, tweak() puts the boxes in
    UNDO = "Rework VEX part"

    def __init__(self, title, rows, button=None):
        self.last = None  # (link, step count) of the last one done, what the boxes change
        for box in [w for _, w in rows if isinstance(w, QtWidgets.QDoubleSpinBox)]:
            box.setKeyboardTracking(False)  # one rebuild per typed number
            box.valueChanged.connect(lambda: self.redo())
        for box in [w for _, w in rows if isinstance(w, QtWidgets.QComboBox)]:
            box.currentTextChanged.connect(lambda: self.redo())
        if button:
            flip = QtWidgets.QPushButton(button)
            flip.clicked.connect(lambda: self.redo(-1))
            rows = rows + [(flip,)]
        super().__init__(title, rows)

    def one(self):
        return True

    def act(self, spot, _):
        link = spot[0]

        def go():
            if library.part_of(link).get("family") not in metal.PROFILES:
                raise ValueError(f"{link.Label} isn't VEX metal, only metal gets worked")
            library.rework(link, library.steps(link) + [self.step(link, spot[1])])
            return True
        if not ui.run(self.UNDO, go):
            return None
        self.last = link, len(library.steps(link))
        link.Document.recompute()
        return f"{self.DID} {link.Label}, the boxes change that one"

    def redo(self, side=1):
        link, count = self.last or (None, 0)
        # deleted, or that step undone since
        if link is None or link not in self.doc.Objects or len(library.steps(link)) != count:
            self.last = None
            return
        done = library.steps(link)
        self.tweak(done[-1], done[:-1], side)
        ui.run(self.UNDO, lambda: library.rework(link, done))
        link.Document.recompute()


class Lined(Clicked):
    # bend and cut, a line through the hole across or along, slid over
    ONE = "click a hole the line goes through"

    def __init__(self, title, rows, button):
        p = App.ParamGet(ui.PARAMS)
        self.across = QtWidgets.QComboBox()
        self.across.addItems(["Across", "Along"])
        self.across.setCurrentText(p.GetString("ShopLine", "Across"))
        self.off = ui.number(-12, 12, " in", step=0.25, decimals=3)
        super().__init__(title, [("Line", self.across), ("Off the hole", self.off)] + rows, button)

    def where(self):
        App.ParamGet(ui.PARAMS).SetString("ShopLine", self.across.currentText())
        return self.across.currentText() == "Across", self.off.value() * IN

    def tweak(self, s, before, side):
        across, off = self.where()
        p, d = line(Vector(*s["center"]), Vector(*s["n"]), across, off, before)
        s.update(p=list(p), d=list(d), side=s["side"] * side)


class BendPanel(Lined):
    DID = "bent"

    def __init__(self):
        self.angle = ui.number(-180, 180, " deg", App.ParamGet(ui.PARAMS).GetFloat("BendAngle", 90))
        super().__init__("VEX bend", [("Angle", self.angle)], "Other side turns")

    def step(self, link, pt):
        App.ParamGet(ui.PARAMS).SetFloat("BendAngle", self.angle.value())
        return bend(link, pt, *self.where(), self.angle.value())

    def tweak(self, s, before, side):
        super().tweak(s, before, side)
        s["angle"] = self.angle.value()


class CutPanel(Lined):
    DID = "cut"

    def __init__(self):
        super().__init__("VEX cut", [], "Keep the other side")

    def step(self, link, pt):
        return cut(link, pt, *self.where())


class DrillPanel(Clicked):
    DID = "drilled"
    ONE = "click where the hole goes, it snaps to the 0.25 grid. hold Shift for right where you click"

    def __init__(self):
        self.size = ui.number(0.05, 1, " in", App.ParamGet(ui.PARAMS).GetFloat("DrillSize", 0.17), step=0.005, decimals=3)
        super().__init__("VEX drill", [("Size", self.size)])

    def step(self, link, pt):
        App.ParamGet(ui.PARAMS).SetFloat("DrillSize", self.size.value())
        shift = QtWidgets.QApplication.queryKeyboardModifiers() & QtCore.Qt.ShiftModifier
        return drill(link, pt, self.size.value() * IN, not shift)

    def tweak(self, s, before, side):
        s["dia"] = self.size.value() * IN


class Command:
    # the three toolbar buttons, one per panel
    def __init__(self, panel, icon, name, tip):
        self.panel, self.res = panel, {"Pixmap": icon, "MenuText": name, "ToolTip": tip}

    def GetResources(self):
        return self.res

    def Activated(self):
        Gui.Control.showDialog(self.panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()


BEND = Command(BendPanel, "vex-bend.svg", "Bend", "Click a hole the bend goes through. It folds there by the angle, then change the line, angle or which side turns")
CUT = Command(CutPanel, "vex-cut.svg", "Cut", "Click a hole the cut goes through, across or along the part. The smaller side goes, or keep that one instead")
DRILL = Command(DrillPanel, "vex-drill.svg", "Drill", "Click a spot on the metal and a round hole goes through there, snapped to the 0.25 grid. Hold Shift to skip the snap")
