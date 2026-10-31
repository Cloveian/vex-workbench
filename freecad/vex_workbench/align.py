# align tool. click a hole on the part to move, then one on the part it goes against, faces land flat on each other
import FreeCAD as App
import FreeCADGui as Gui
from FreeCAD import Placement, Rotation, Vector
from PySide import QtWidgets

from . import snap, ui
from .metal import IN

FLIP = Rotation(Vector(1, 0, 0), 180)  # z against z, face to face


def put(link, frame, parent, at, gap, spin):
    # link placed so frame (link coords) sits on world frame at, faces together, gap mm apart and spin deg around the hole
    want = at.multiply(Placement(Vector(0, 0, gap), FLIP)).multiply(Placement(Vector(), Rotation(Vector(0, 0, 1), spin)))
    link.Placement = parent.inverse().multiply(want).multiply(frame.inverse())


def align(mover, target, gap, asm=None):
    # mover, target = snap.spot()s. state for turning it after, and a Revolute joint in asm if theres one
    link = mover[0]
    if link == target[0]:
        raise ValueError("that's the same part twice, click a hole on the part to move then one on another part")
    fm, _ = snap.hole(mover)
    ft, at = snap.hole(target)
    world = mover[2]
    if link.ElementCount:
        # clicked one element, the whole array moves. its world placement is the path without the element
        root, path = mover[3]
        up = "".join(n + "." for n in path.split(".")[:-2])
        world = root.getSubObject(up, retType=3) if up else root.Placement
    frame = world.inverse().multiply(mover[2]).multiply(fm.Placement)  # in the link's coords, through the element if theres one
    # world placement of whatever the link sits in, its own placement taken back off the end
    parent = world.multiply(link.Placement.inverse())
    put(link, frame, parent, at, gap, 0)
    joint = asm and snap.revolute(asm, snap.ref(asm, target, ft), snap.ref(asm, mover, fm), gap)
    return {"link": link, "frame": frame, "parent": parent, "at": at, "spin": 0, "joint": joint}


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
        self.gap.setRange(0, 12)
        self.gap.setDecimals(3)
        self.gap.setSingleStep(0.125)
        self.gap.setSuffix(" in")
        self.gap.setKeyboardTracking(False)  # one move per typed gap
        self.gap.valueChanged.connect(lambda: self.turn(0))
        self.last = None  # the last one aligned, what the buttons and the gap move
        super().__init__("VEX align", [("Turn", turns), ("Gap", self.gap)])

    def act(self, mover, target):
        import UtilsAssembly
        asm = snap.inside(UtilsAssembly.activePartOrAssembly())[1]
        got = ui.run("Align VEX part", lambda: align(mover, target, self.gap.value() * IN, asm))
        if got is None:
            return None
        self.last = got
        got["link"].Document.recompute()
        return f"{got['link'].Label} lined up on {target[0].Label}, the buttons and gap move it"

    def turn(self, way):
        # way -1 / 1 for the buttons, 0 when the gap changed
        s = self.last
        # deleted or undone since
        if not s or s["link"] not in self.doc.Objects:
            self.last = None
            return
        if way:
            App.ParamGet(ui.PARAMS).SetFloat("AlignAngle", self.angle.value())
        s["spin"] += way * self.angle.value()
        gap = self.gap.value() * IN

        def move():
            put(s["link"], s["frame"], s["parent"], s["at"], gap, s["spin"])
            if s["joint"] in self.doc.Objects:
                s["joint"].Offset2 = Placement(Vector(0, 0, gap), Rotation())
        ui.run("Turn VEX part", move)
        s["link"].Document.recompute()


class Align:
    def GetResources(self):
        return {"Pixmap": "vex-align.svg", "MenuText": "Align",
                "ToolTip": "Click a hole on the part to move, then the hole it goes against. Faces land flat on each other, then turn it or set a gap"}

    def Activated(self):
        Gui.Control.showDialog(Panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()
