# bend tool. click a hole the bend line goes through, it folds there, then the boxes change that bend
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from PySide import QtWidgets

from . import library, metal, snap, ui
from .metal import IN, X


def wall(link, center, n):
    # thicknes at a hole, from its loop on the other face
    deep = [(center - c).dot(n) for _, c, m in library.cached(link.LinkedObject, library.holes)
            if m.dot(n) < -0.99 and (center - c).cross(n).Length < 1e-3 and (center - c).dot(n) > 1e-6]
    if not deep:
        raise ValueError(f"can't tell how thick {link.Label} is there, click a hole that goes all the way through")
    return min(deep)


def line(center, n, across, off, before):
    # point and direction of the bend line, through the hole across the length or along it, off mm to the side
    # the length is the part's x, but on a leg an earlier bend stood square to x, its that bend's face normal
    for length in [X] + [Vector(*b["n"]) for b in reversed(before)]:
        along = length - n * n.dot(length)
        if along.Length > 1e-6:
            break
    else:
        raise ValueError("that's an end face, pick a hole on a side")
    along.normalize()
    d = n.cross(along) if across else along
    return center + n.cross(d) * off, d


def first(link, pt, across, off, angle):
    # a new bend through the hole nearest pt. the smaller side turns
    center, n = library.hole_at(link, pt)
    p, d = line(center, n, across, off, library.bends(link))
    cat = library.cat()["metal"]
    b = {"p": list(p), "d": list(d), "n": list(n), "angle": angle, "r": cat["bend"] * IN, "t": wall(link, center, n), "k": cat["k"],
         "center": list(center)}
    shape = Part.getShape(link.LinkedObject)
    past = shape.common(metal.half(p, n.cross(d), n, 0)).Volume
    b["side"] = 1 if past < shape.Volume / 2 else -1
    return b


class Panel(snap.Clicks):
    ONE = "click a hole the bend goes through"

    def __init__(self):
        p = App.ParamGet(ui.PARAMS)
        self.across = QtWidgets.QComboBox()
        self.across.addItems(["Across", "Along"])
        self.across.setCurrentText(p.GetString("BendLine", "Across"))
        self.off = ui.number(-12, 12, " in", step=0.25, decimals=3)
        self.angle = ui.number(-180, 180, " deg", p.GetFloat("BendAngle", 90))
        flip = QtWidgets.QPushButton("Other side turns")
        for box in (self.off, self.angle):
            box.setKeyboardTracking(False)  # one rebuild per typed number
            box.valueChanged.connect(lambda: self.redo())
        self.across.currentTextChanged.connect(lambda: self.redo())
        flip.clicked.connect(lambda: self.redo(-1))
        self.last = None  # (link, bend count) of the last one bent, what the boxes and the button change
        super().__init__("VEX bend", [("Line", self.across), ("Off the hole", self.off), ("Angle", self.angle), (flip,)])

    def one(self):
        return True

    def act(self, spot, _):
        link = spot[0]
        p = App.ParamGet(ui.PARAMS)
        p.SetString("BendLine", self.across.currentText())
        p.SetFloat("BendAngle", self.angle.value())

        def go():
            if library.part_of(link).get("family") not in metal.PROFILES:
                raise ValueError(f"{link.Label} isn't VEX metal, only metal bends")
            b = first(link, spot[1], self.across.currentText() == "Across", self.off.value() * IN, self.angle.value())
            library.rebend(link, library.bends(link) + [b])
            return b
        b = ui.run("Bend VEX part", go)
        if b is None:
            return None
        self.last = link, len(library.bends(link))
        link.Document.recompute()
        return f"bent {link.Label}, the boxes and the button change that bend"

    def redo(self, side=1):
        # the last bend again with whats in the boxes now, same hole. side -1 for the button
        link, count = self.last or (None, 0)
        # deleted, or that bend undone since
        if link is None or link not in self.doc.Objects or len(library.bends(link)) != count:
            self.last = None
            return
        done = library.bends(link)
        b = done[-1]
        p, d = line(Vector(*b["center"]), Vector(*b["n"]), self.across.currentText() == "Across", self.off.value() * IN, done[:-1])
        b.update(p=list(p), d=list(d), angle=self.angle.value(), side=b["side"] * side)
        ui.run("Bend VEX part", lambda: library.rebend(link, done))
        link.Document.recompute()


class Bend:
    def GetResources(self):
        return {"Pixmap": "vex-bend.svg", "MenuText": "Bend",
                "ToolTip": "Click a hole the bend goes through. It folds there by the angle, then change the line, angle or which side turns"}

    def Activated(self):
        Gui.Control.showDialog(Panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()
