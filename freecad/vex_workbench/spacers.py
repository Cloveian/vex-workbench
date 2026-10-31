# spacer tool. click two holes that face each other, the gap gets spacers + washers, like inside a boxed channel
import itertools

import FreeCAD as App
import FreeCADGui as Gui
from FreeCAD import Vector
from PySide import QtWidgets

from . import library, snap, ui
from .metal import IN

SLOP = IN / 64  # mm a stack can come up short
MOST = 8  # pieces in one stack


def length(p):
    return (p["params"]["length"] if p["family"] == "spacer" else p["params"]["thickness"]) * IN


def pick(gap, od):
    # fewest pieces that end up within SLOP under gap, the tightest of those. never over
    if gap <= SLOP:
        return []
    items = [p for p in library.index()[1].values() if p["family"] == "washer" or (p["family"] == "spacer" and p["params"]["od"] == od)]
    for k in range(1, MOST + 1):
        best, most = None, 0
        for combo in itertools.combinations_with_replacement(items, k):
            total = sum(length(p) for p in combo)
            if gap - SLOP <= total <= gap + 1e-6 and total > most:
                best, most = combo, total
        if best:
            # spacers first, washers on the far end
            return sorted(best, key=length, reverse=True)
    raise ValueError(f"a {gap / IN:.3f}\" gap takes more than {MOST} spacers")


def stack(doc, s, parts, parent=None):
    # parts piled up out of the face clicked in s, centered on its hole. Revolute joints down the pile in an assembly
    f, a = snap.hole(s)
    local, asm = snap.inside(parent)
    below = asm and snap.ref(asm, s, f)
    put, z = [], 0
    for p in parts:
        o = library.place(doc, p, parent)
        o.Placement = local.multiply(a).multiply(App.Placement(Vector(0, 0, z), App.Rotation()))
        z += length(p)
        if asm:
            snap.revolute(asm, below, snap.on(o, library.frame(o, App.Placement(), "Seat")))
            below = snap.on(o, library.frame(o, App.Placement(Vector(0, 0, length(p)), App.Rotation()), "Top"))
        put.append(o)
    return put


def fill(doc, one, other, od, parent=None):
    # one, other = snap.spot()s on the two faces
    (_, a), (_, b) = snap.hole(one), snap.hole(other)
    got = snap.line(a, b)
    if got is None or got[1] > -1 + 1e-6 or got[0] <= 0:
        raise ValueError("those holes don't line up, click the two faces that face each other")
    parts = pick(got[0], od)
    if not parts:
        raise ValueError("those faces are touching, nothing to put in there")
    return stack(doc, one, parts, parent)


def ods():
    return [str(od) for od in library.index()[0]["spacer"]["od"]]


def od_box():
    # spacer OD picker, shared with the screw panel
    box = QtWidgets.QComboBox()
    box.addItems(ods())
    box.setCurrentText(App.ParamGet(ui.PARAMS).GetString("SpacerOD", "0.375"))
    return box


def od_from(box):
    App.ParamGet(ui.PARAMS).SetString("SpacerOD", box.currentText())
    return float(box.currentText())


class Panel(snap.Clicks):
    PROMPTS = ("click a hole on one face", "now the hole across from it")

    def __init__(self):
        self.od = od_box()
        super().__init__("VEX spacers", [("Spacer OD", self.od)])

    def act(self, one, other):
        import UtilsAssembly
        od = od_from(self.od)
        doc = one[0].Document
        put = ui.run("Place VEX spacers", lambda: fill(doc, one, other, od, UtilsAssembly.activePartOrAssembly()))
        if not put:
            return None
        doc.recompute()
        return "put in " + ", ".join(o.Label for o in put)


class Spacers:
    def GetResources(self):
        return {"Pixmap": "vex-spacer.svg", "MenuText": "Spacers",
                "ToolTip": "Click holes on two faces across from each other. Fills the gap with spacers and washers, never more than 1/64\" short"}

    def Activated(self):
        Gui.Control.showDialog(Panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()
