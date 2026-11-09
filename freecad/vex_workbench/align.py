# align tool. click a hole on the part to move, then one on the part it goes against, faces land flat on each other
import math

import FreeCAD as App
from FreeCAD import Placement, Rotation, Vector
from PySide import QtWidgets

from . import library, snap, ui
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
    # mover, target = snap.spot()s, active = the active part or assembly. state for turning it after. just a move, joints are the joint tool's
    obj, world = moving(mover, active, whole)
    if obj in target[3][0].getSubObjectList(target[3][1]):
        raise ValueError(f"{target[0].Label} would move along with it, click a hole on something else to line it up on")
    hole = snap.hole(mover)[1]
    at = snap.hole(target)[1]
    frame = world.inverse().multiply(hole)  # in obj coords
    # world placement of whatever obj sits in, its own placement taken back off the end
    parent = world.multiply(obj.Placement.inverse())
    spin = spun(hole, at, step)
    put(obj, frame, parent, at, gap, spin)
    return {"moved": obj, "frame": frame, "parent": parent, "at": at, "spin": spin, "mover": mover, "target": target, "active": active, "whole": whole}


def turn(s, gap):
    # s from align() put at its spin and gap
    put(s["moved"], s["frame"], s["parent"], s["at"], gap, s["spin"])


def flip(s, gap, step):
    # s from align() done again off the same hole on the part's other face, so its turned over with that face on the target. inserts mostly
    link, pt, _, (root, path) = s["mover"]
    back = library.far_side(link, pt)
    if back is None:
        raise ValueError(f"{link.Label} has nothing on the other side of that hole to flip onto")
    # where the link is now, the click's placement is from before the move
    return align((link, back, snap.placement(root, path), (root, path)), s["target"], gap, s["active"], s["whole"], step)


# Slide, replaced by nothing yet. kept for the joint tool, its frames and limits check out, a plain solve just ignores the limits (ondsel)
# def slide(s, end):
#     # s from align(), its Revolute swapped for a Slider from the hole it went on to end, stopping at both
#     j = s["joint"]
#     if not j or j not in s["moved"].Document.Objects:
#         raise ValueError("no align joint to turn into a slider, line it up again with an assembly active")
#     at = s["at"]
#     b = snap.hole(end)[1]
#     along = b.Base - at.Base
#     z = at.Rotation.multVec(snap.Z)
#     if end[3] != s["target"][3] or along.Length < snap.OFF_AXIS or abs(along.dot(z)) > snap.OFF_AXIS:
#         raise ValueError(f"click another hole on the same face of {s['target'][0].Label}")
#     rail = Placement(at.Base, Rotation(z, along.cross(z), along, "ZXY"))  # z down the rail, x out of the face
#     moved = landed(at, snap.gap(j), snap.spin(j))
#     asm = j.Proxy.getAssembly(j)
#     refs = [[r[0], list(r[1])] for r in (j.Reference1, j.Reference2)]
#     asm.Document.removeObject(j.Name)
#     k = ours(snap.joint(asm, "Slider", *refs, at.inverse().multiply(rail), moved.inverse().multiply(rail)))
#     k.EnableLengthMin = k.EnableLengthMax = True
#     k.LengthMin, k.LengthMax = 0, along.Length
#     s["joint"] = k
#     return k


class Panel(snap.Clicks):
    PROMPTS = ("click a hole on the part to move", "now the hole it goes against")

    def __init__(self):
        p = App.ParamGet(ui.PARAMS)
        self.angle = ui.number(-360, 360, " deg", p.GetFloat("AlignAngle", 90))
        back, ahead = QtWidgets.QPushButton("Rotate -"), QtWidgets.QPushButton("Rotate +")
        back.clicked.connect(lambda: self.turn(-1))
        ahead.clicked.connect(lambda: self.turn(1))
        over = QtWidgets.QPushButton("Flip")
        over.setToolTip("Turns it over on the hole, so the other side of it goes against the face. For inserts")
        over.clicked.connect(self.flip)
        turns = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(turns)
        row.setContentsMargins(0, 0, 0, 0)
        for w in (self.angle, back, ahead, over):
            row.addWidget(w)
        self.gap = ui.number(-36, 36, " in", step=0.125, decimals=3)  # under 0 pushes it in, a shaft end through a hole. a 35 long channel is 17.5
        self.gap.setKeyboardTracking(False)  # one move per typed gap
        self.gap.valueChanged.connect(lambda: self.turn(0))
        self.whole = QtWidgets.QCheckBox("Whole group")
        self.whole.setToolTip("Moves the part or sub-assembly it's in, the top one under the active assembly")
        self.whole.setChecked(p.GetBool("AlignWhole", False))
        self.last = None  # the last one aligned, what the buttons and the gap move
        super().__init__("VEX align", [("Turn", turns), ("Gap", self.gap), (self.whole,)])

    def act(self, mover, target):
        whole = self.whole.isChecked()
        App.ParamGet(ui.PARAMS).SetBool("AlignWhole", whole)
        got = ui.run("Align VEX part", lambda: align(mover, target, self.gap.value() * IN, ui.active(), whole, self.angle.value()))
        if got is None:
            return None
        self.last = got
        got["moved"].Document.recompute()
        return f"{got['moved'].Label} lined up on {target[0].Label}, the buttons and gap move it"

    def still(self):
        # the last one alegned, None once its deleted or undone
        if self.last and self.last["moved"] not in self.doc.Objects:
            self.last = None
        return self.last

    def flip(self):
        s = self.still()
        if not s:
            return
        got = ui.run("Flip VEX part", lambda: flip(s, self.gap.value() * IN, self.angle.value()))
        if got:
            self.last = got
            got["moved"].Document.recompute()

    def turn(self, way):
        # way -1 / 1 for the buttons, 0 when the gap changed
        s = self.still()
        if not s:
            return
        if way:
            App.ParamGet(ui.PARAMS).SetFloat("AlignAngle", self.angle.value())
        s["spin"] -= way * self.angle.value()  # + is counterclockwise looking at the face it went against
        gap = self.gap.value() * IN
        ui.run("Turn VEX part", lambda: turn(s, gap))
        s["moved"].Document.recompute()


ALIGN = ui.Command(Panel, "vex-align.svg", "Align",
                   "Click a hole on the part to move, then the hole it goes against. Faces land flat on each other, then turn it or set a gap")
