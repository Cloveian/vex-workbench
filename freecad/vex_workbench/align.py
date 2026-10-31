# align tool. click a hole on the part to move, then one on the part it goes against, faces land flat on each other
import math

import FreeCAD as App
import FreeCADGui as Gui
from FreeCAD import Placement, Rotation, Vector
from PySide import QtWidgets

from . import snap, ui
from .metal import IN

FLIP = Rotation(Vector(1, 0, 0), 180)  # z against z, face to face
X, Y = Vector(1, 0, 0), Vector(0, 1, 0)


def put(link, frame, parent, at, gap, spin):
    # link placed so frame (link coords) sits on world frame at, faces together, gap mm apart and spin deg around the hole
    want = at.multiply(Placement(Vector(0, 0, gap), FLIP)).multiply(Placement(Vector(), Rotation(Vector(0, 0, 1), spin)))
    link.Placement = parent.inverse().multiply(want).multiply(frame.inverse())


def moving(mover, active, whole):
    # what moves and its world placement. the clicked link (an array moves whole), or with whole the top group its in under active
    root, path = mover[3]
    names = path.split(".")[:-1]
    objs = root.getSubObjectList(path)  # root first, then one per name
    k = max(i for i, o in enumerate(objs) if o == mover[0])
    if whole:
        k = objs.index(active) + 1 if active in objs else 0
    if not hasattr(objs[k], "Placement"):
        raise ValueError(f"{objs[k].Label} is a plain group, it has no placement to move. put it in a Part instead")
    return objs[k], snap.placement(root, "".join(n + "." for n in names[:k]))


def spun(hole, at, step):
    # the spin put() needs to keep the hole x as near as it is now, to the nearest step deg. x after the flip is cos*ax - sin*ay
    x = hole.Rotation.multVec(X)
    ax, ay = at.Rotation.multVec(X), at.Rotation.multVec(Y)
    spin = math.degrees(math.atan2(-x.dot(ay), x.dot(ax)))
    return round(spin / step) * step if step else spin


def align(mover, target, gap, active=None, whole=False, step=0):
    # mover, target = snap.spot()s, active = the active part or assembly. state for turning it after, and a Revolute joint if its an assembly
    obj, world = moving(mover, active, whole)
    asm = snap.inside(active)[1]
    if obj in target[3][0].getSubObjectList(target[3][1]):
        raise ValueError(f"{target[0].Label} would move along with it, click a hole on something else to line it up on")
    fm, hole = snap.hole(mover)
    ft, at = snap.hole(target)
    frame = world.inverse().multiply(hole)  # in obj coords
    # world placement of whatever obj sits in, its own placement taken back off the end
    parent = world.multiply(obj.Placement.inverse())
    spin = spun(hole, at, step)
    put(obj, frame, parent, at, gap, spin)
    joint = asm and rejoint(asm, snap.ref(asm, target, ft), snap.ref(asm, mover, fm), gap, spin)
    return {"moved": obj, "frame": frame, "parent": parent, "at": at, "spin": spin, "joint": joint}


def turn(s, gap):
    # s from align() put at its spin and gap. the joint's presolve undoes a plain move
    j = s["joint"]
    if j and j in s["moved"].Document.Objects:
        j.Offset2 = snap.offset(gap, s["spin"])
    else:
        put(s["moved"], s["frame"], s["parent"], s["at"], gap, s["spin"])


def rejoint(asm, r1, r2, gap, spin):
    # one align joint per moving piece, an older one would drag it back
    import UtilsAssembly
    if r2:
        for j in UtilsAssembly.getJointGroup(asm).Group:
            if getattr(j, "VexAlign", False) and j.Reference2 and j.Reference2[0] == r2[0]:
                asm.Document.removeObject(j.Name)
    j = snap.revolute(asm, r1, r2, gap, spin)
    if j:
        j.addProperty("App::PropertyBool", "VexAlign", "VEX")
        j.VexAlign = True
    return j


class Panel(snap.Clicks):
    PROMPTS = ("click a hole on the part to move", "now the hole it goes against")

    def __init__(self):
        p = App.ParamGet(ui.PARAMS)
        self.angle = QtWidgets.QDoubleSpinBox()
        self.angle.setRange(-360, 360)
        self.angle.setSuffix(" deg")
        self.angle.setValue(p.GetFloat("AlignAngle", 90))
        back, ahead = QtWidgets.QPushButton("Rotate -"), QtWidgets.QPushButton("Rotate +")
        back.clicked.connect(lambda: self.turn(-1))
        ahead.clicked.connect(lambda: self.turn(1))
        turns = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(turns)
        row.setContentsMargins(0, 0, 0, 0)
        for w in (self.angle, back, ahead):
            row.addWidget(w)
        self.gap = QtWidgets.QDoubleSpinBox()
        self.gap.setRange(-12, 12)  # under 0 pushes it in, a shaft end through a hole
        self.gap.setDecimals(3)
        self.gap.setSingleStep(0.125)
        self.gap.setSuffix(" in")
        self.gap.setKeyboardTracking(False)  # one move per typed gap
        self.gap.valueChanged.connect(lambda: self.turn(0))
        self.whole = QtWidgets.QCheckBox("Move its whole group")
        self.whole.setChecked(p.GetBool("AlignWhole", False))
        self.last = None  # the last one aligned, what the buttons and the gap move
        super().__init__("VEX align", [("Turn", turns), ("Gap", self.gap), (self.whole,)])

    def act(self, mover, target):
        import UtilsAssembly
        whole = self.whole.isChecked()
        App.ParamGet(ui.PARAMS).SetBool("AlignWhole", whole)
        active = UtilsAssembly.activePartOrAssembly()
        got = ui.run("Align VEX part", lambda: align(mover, target, self.gap.value() * IN, active, whole, self.angle.value()))
        if got is None:
            return None
        self.last = got
        got["moved"].Document.recompute()
        return f"{got['moved'].Label} lined up on {target[0].Label}, the buttons and gap move it"

    def turn(self, way):
        # way -1 / 1 for the buttons, 0 when the gap changed
        s = self.last
        # deleted or undone since
        if not s or s["moved"] not in self.doc.Objects:
            self.last = None
            return
        if way:
            App.ParamGet(ui.PARAMS).SetFloat("AlignAngle", self.angle.value())
        if s["joint"] and s["joint"] in self.doc.Objects:
            # turned or gapped in the joint panel since. a gap from there wins over the box on a button
            s["spin"] = snap.spin(s["joint"])
            if way:
                self.gap.blockSignals(True)
                self.gap.setValue(snap.gap(s["joint"]) / IN)
                self.gap.blockSignals(False)
        s["spin"] -= way * self.angle.value()  # + is counterclockwise looking at the face it went against, same as the joint's rotation box
        gap = self.gap.value() * IN
        ui.run("Turn VEX part", lambda: turn(s, gap))
        s["moved"].Document.recompute()


class Align:
    def GetResources(self):
        return {"Pixmap": "vex-align.svg", "MenuText": "Align",
                "ToolTip": "Click a hole on the part to move, then the hole it goes against. Faces land flat on each other, then turn it or set a gap"}

    def Activated(self):
        Gui.Control.showDialog(Panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()
