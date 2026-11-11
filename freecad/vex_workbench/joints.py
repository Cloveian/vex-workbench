# joint tool. click a hole on the part that moves, then the one its on, and they get an assembly joint right where they are. back from the dead
import FreeCAD as App
from FreeCAD import Placement, Rotation
from PySide import QtCore, QtWidgets

from . import snap, ui

KINDS = {"Spin": "Revolute", "Fixed": "Fixed", "Slide": "Slider"}


def refs(asm, mover, target):
    # (target ref, mover ref, target hole, mover hole) with the holes in the world
    if asm is None:
        raise ValueError("joints go in an assembly, make one active first")
    fa, a = snap.hole(mover)
    fb, b = snap.hole(target)
    r1, r2 = snap.ref(asm, target, fb), snap.ref(asm, mover, fa)
    if r1 is None or r2 is None:
        raise ValueError(f"{(target if r1 is None else mover)[0].Label} isn't in the active assembly")
    return r1, r2, b, a


def rail(target, end):
    # placement at the target hole with z down the slide to end, its length mm. None and why for an end thats no good
    b = snap.hole(target)[1]
    e = snap.hole(end)[1]
    along = e.Base - b.Base
    z = b.Rotation.multVec(snap.Z)
    if end[3] != target[3] or along.Length < snap.OFF_AXIS or abs(along.dot(z)) > snap.OFF_AXIS:
        return None, f"click another hole on the same face of {target[0].Label}, where it stops"
    return Placement(b.Base, Rotation(z, along.cross(z), along, "ZXY")), along.Length  # x out of the face


def join(asm, kind, mover, target, end=None):
    # offsets off where both holes are now, so the solver has nothing to move
    r1, r2, b, a = refs(asm, mover, target)
    if kind == "Slide":
        on, length = rail(target, end)
        if on is None:
            raise ValueError(length)
        # stops at both ends. a plain solve ignores them, the drag one doesnt (ondsel)
        j = snap.joint(asm, "Slider", r1, r2, b.inverse().multiply(on), a.inverse().multiply(on))
        j.EnableLengthMin = j.EnableLengthMax = True
        j.LengthMin, j.LengthMax = 0, length
        return j
    if kind == "Spin" and snap.line(b, a) is None:
        raise ValueError(f"those holes on {mover[0].Label} and {target[0].Label} aren't lined up, align it first")
    return snap.joint(asm, KINDS[kind], r1, r2, off2=a.inverse().multiply(b))


class Panel(snap.Clicks):
    PROMPTS = ("click a hole on the part that moves", "now the hole it's on")
    END = "now another hole on that face, where the slide stops"

    def __init__(self):
        self.mid = self.end = None  # a slide's second and third clicks
        self.kind = QtWidgets.QComboBox()
        self.kind.addItems(list(KINDS))
        self.kind.setCurrentText(App.ParamGet(ui.PARAMS).GetString("JointKind", "Spin"))
        self.kind.setToolTip("Spin turns on the hole, Slide runs along a row of holes, Fixed holds it")
        self.kind.currentTextChanged.connect(self.restart)
        super().__init__("VEX joint", [("Kind", self.kind)])

    def restart(self, kind):
        App.ParamGet(ui.PARAMS).SetString("JointKind", kind)
        self.first = self.mid = None
        self.light([])
        self.ask()

    def ask(self, said=""):
        if self.mid is not None:
            self.status.setText(said + self.END)
        else:
            super().ask(said)

    def take(self, s):
        if self.kind.currentText() != "Slide" or self.first is None:
            return super().take(s)
        if self.mid is None:
            self.mid = s
            self.light([self.first, s])
            self.ask()
            return
        try:
            on, why = rail(self.mid, s)
        except ValueError as e:
            on, why = None, str(e)  # no holes on it
        if on is None:
            self.ask(why + "\n")  # still waiting on the end
            return
        a, b, self.first, self.mid, self.end = self.first, self.mid, None, None, s
        self.light([a, b, s])
        QtCore.QTimer.singleShot(0, lambda: self.done(a, b))

    def act(self, mover, target):
        kind, end, self.end = self.kind.currentText(), self.end, None
        asm = snap.inside(ui.active())[1]
        j = ui.run("VEX joint", lambda: join(asm, kind, mover, target, end))
        if j is None:
            return None
        j.Document.recompute()
        return f"{kind.lower()} joint {mover[0].Label} on {target[0].Label}"


JOINT = ui.Command(Panel, "vex-joint.svg", "Joint",
                   "Click a hole on the part that moves, then the one it's on. A spin, slide or fixed assembly joint right where they are")
