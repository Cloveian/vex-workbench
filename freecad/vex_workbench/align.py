# align tool. click a hole on the part to move, then one on the part it goes against, faces land flat on each other
import math

import FreeCAD as App
import FreeCADGui as Gui
from FreeCAD import Placement, Rotation, Vector
from PySide import QtCore, QtWidgets

from . import snap, ui
from .metal import IN

FLIP = Rotation(Vector(1, 0, 0), 180)  # z against z, face to face
X, Y = Vector(1, 0, 0), Vector(0, 1, 0)


def landed(at, gap, spin):
    # world placement of the moved hole frame, faces together on at, gap mm apart and spin deg around the hole
    return at.multiply(Placement(Vector(0, 0, gap), FLIP)).multiply(Placement(Vector(), Rotation(Vector(0, 0, 1), spin)))


def put(link, frame, parent, at, gap, spin):
    # link placed so frame (link coords) lands on at
    link.Placement = parent.inverse().multiply(landed(at, gap, spin)).multiply(frame.inverse())


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
    return {"moved": obj, "frame": frame, "parent": parent, "at": at, "spin": spin, "joint": joint, "target": target}


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
    return ours(snap.revolute(asm, r1, r2, gap, spin))


def ours(j):
    if j:
        j.addProperty("App::PropertyBool", "VexAlign", "VEX")
        j.VexAlign = True
    return j


def slide(s, end):
    # s from align(), its Revolute swapped for a Slider from the hole it went on to end, stopping at both
    j = s["joint"]
    if not j or j not in s["moved"].Document.Objects:
        raise ValueError("no align joint to turn into a slider, line it up again with an assembly active")
    at = s["at"]
    b = snap.hole(end)[1]
    along = b.Base - at.Base
    z = at.Rotation.multVec(snap.Z)
    if end[3] != s["target"][3] or along.Length < snap.OFF_AXIS or abs(along.dot(z)) > snap.OFF_AXIS:
        raise ValueError(f"click another hole on the same face of {s['target'][0].Label}")
    rail = Placement(at.Base, Rotation(z, along.cross(z), along, "ZXY"))  # z down the rail, x out of the face
    moved = landed(at, snap.gap(j), snap.spin(j))
    asm = j.Proxy.getAssembly(j)
    refs = [[r[0], list(r[1])] for r in (j.Reference1, j.Reference2)]
    asm.Document.removeObject(j.Name)
    k = ours(snap.joint(asm, "Slider", *refs, at.inverse().multiply(rail), moved.inverse().multiply(rail)))
    k.EnableLengthMin = k.EnableLengthMax = True
    k.LengthMin, k.LengthMax = 0, along.Length
    s["joint"] = k
    return k


class Panel(snap.Clicks):
    PROMPTS = ("click a hole on the part to move", "now the hole it goes against")
    END = "now another hole on that face, it slides between the two"

    def __init__(self):
        self.rail = None  # align() state waiting on the slide's end click
        p = App.ParamGet(ui.PARAMS)
        self.angle = ui.number(-360, 360, " deg", p.GetFloat("AlignAngle", 90))
        back, ahead = QtWidgets.QPushButton("Rotate -"), QtWidgets.QPushButton("Rotate +")
        back.clicked.connect(lambda: self.turn(-1))
        ahead.clicked.connect(lambda: self.turn(1))
        turns = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(turns)
        row.setContentsMargins(0, 0, 0, 0)
        for w in (self.angle, back, ahead):
            row.addWidget(w)
        self.gap = ui.number(-36, 36, " in", step=0.125, decimals=3)  # under 0 pushes it in, a shaft end through a hole. a 35 long channel is 17.5
        self.gap.setKeyboardTracking(False)  # one move per typed gap
        self.gap.valueChanged.connect(lambda: self.turn(0))
        self.whole = QtWidgets.QCheckBox("Move its whole group")
        self.whole.setChecked(p.GetBool("AlignWhole", False))
        self.slides = QtWidgets.QCheckBox("Slide along to another hole")
        self.slides.setToolTip("In an assembly, a third click on the same face makes it a slider between the two holes. Drag it to see it move")
        self.slides.setChecked(p.GetBool("AlignSlide", False))
        self.slides.toggled.connect(self.unslide)
        self.last = None  # the last one aligned, what the buttons and the gap move
        super().__init__("VEX align", [("Turn", turns), ("Gap", self.gap), (self.whole,), (self.slides,)])

    def unslide(self, on):
        App.ParamGet(ui.PARAMS).SetBool("AlignSlide", on)
        if not on and self.rail:
            self.rail = None
            self.light([])
            self.ask()

    def ask(self, said=""):
        if self.rail:
            self.status.setText(said + self.END)
        else:
            super().ask(said)

    def take(self, s):
        if not self.rail:
            return super().take(s)
        self.light([s])
        QtCore.QTimer.singleShot(0, lambda: self.slid(s))

    def slid(self, end):
        s, self.rail = self.rail, None
        got = ui.run("Slide VEX part", lambda: slide(s, end))
        Gui.Selection.clearSelection()
        self.light([])
        if got is None:
            self.rail = s  # wrong hole, try again
            self.ask()
            return
        self.last = None  # the buttons would turn it off the rail
        s["moved"].Document.recompute()
        self.ask(f"{s['moved'].Label} slides along {s['target'][0].Label} now\n")

    def act(self, mover, target):
        whole = self.whole.isChecked()
        App.ParamGet(ui.PARAMS).SetBool("AlignWhole", whole)
        active = ui.active()
        got = ui.run("Align VEX part", lambda: align(mover, target, self.gap.value() * IN, active, whole, self.angle.value()))
        if got is None:
            return None
        self.last = got
        got["moved"].Document.recompute()
        if self.slides.isChecked() and got["joint"]:
            self.rail = got
        elif self.slides.isChecked():
            return f"{got['moved'].Label} lined up on {target[0].Label}, but sliding needs an active assembly"
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


ALIGN = ui.Command(Panel, "vex-align.svg", "Align",
                   "Click a hole on the part to move, then the hole it goes against. Faces land flat on each other, then turn it or set a gap")
