# screw tool. click a hole on the head side, then one on the nut side, it puts in the shortest screw that makes it through the nut
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from PySide import QtCore, QtWidgets

from . import derived, library, snap, ui
from .metal import IN

KINDS = {"Star": "star-screw", "Hex": "hex-screw"}
NUT_FOLDER = "Hardware/Nuts/8-32 Nuts"
PARAMS = "User parameter:BaseApp/Preferences/Mod/VexWorkbench"
OFF_AXIS = 0.01  # mm


def nuts():
    _, gen, steps = library.index()
    # vex steps and our generated nuts, both by folder
    return {p["name"]: p for p in [*steps.values(), *gen.values()] if p["folder"].startswith(NUT_FOLDER)}


def shortest(family, need):
    # need in mm
    fits = [p for p in library.index()[1].values() if p["family"] == family and p["params"]["length"] * IN > need - 1e-6]
    if not fits:
        raise ValueError(f"no {library.index()[0][family]['title']} is long enough, it needs {need / IN:.3f}\"")
    return min(fits, key=lambda p: p["params"]["length"])


def hole(s):
    # the clicked hole's frame, and where it is in the world
    link, pt, plc, _ = s
    f = library.hole_frame(link, pt)
    return f, plc.multiply(f.Placement)


def joint(asm, s, f, part, pf):
    # Fixed, hole frame f on the clicked part to pf on the new screw / nut. none for a part outside asm
    import JointObject
    import UtilsAssembly
    root, path = s[3]
    comp, sub = UtilsAssembly.getComponentReference(asm, root, path + f.Name + ".")
    if comp is None:
        return
    j = UtilsAssembly.getJointGroup(asm).newObject("App::FeaturePython", "Joint")
    JointObject.Joint(j, JointObject.JointTypes.index("Fixed"))
    if j.ViewObject:
        JointObject.ViewProviderJoint(j.ViewObject)
    j.Proxy.setJointConnectors(j, [[comp, [sub, sub]], [part, [pf.Name + ".", pf.Name + "."]]])


def seat(src):
    # plain face of the nut at z = 0 and its hieght. vex step nuts come in however they were drawn
    shape = Part.getShape(src)
    s, h = derived.upright(shape.copy(), IN)
    return s.Placement.multiply(shape.Placement.inverse()), h


def fasten(doc, head, tail, family, nut, parent=None):
    # head, tail = snap.spot()s, head side first. screw and nut links back
    (fa, a), (fb, b) = hole(head), hole(tail)
    z = a.Rotation.multVec(Vector(0, 0, 1))
    d = a.Base - b.Base
    gap = d.dot(z)
    # facing each other (gap < 0) = the inside faces got clicked
    if b.Rotation.multVec(Vector(0, 0, 1)).dot(z) > -1 + 1e-6 or d.cross(z).Length > OFF_AXIS or gap <= 0:
        raise ValueError("those holes don't line up, click the outside face on both ends")
    local = parent.getGlobalPlacement().inverse() if parent else App.Placement()
    plc, h = seat(library.source(doc, nut))
    screw = shortest(family, gap + h)  # before anything gets placed
    n = library.place(doc, nut, parent)
    n.Placement = local.multiply(b).multiply(plc)
    s = library.place(doc, screw, parent)
    s.Placement = local.multiply(a)  # under the head on the face, shank down -z
    if parent and parent.isDerivedFrom("Assembly::AssemblyObject"):
        # their frames sit right on the hole frames, the joints dont move anything
        joint(parent, head, fa, s, library.frame(s, App.Placement(), "Seat"))
        joint(parent, tail, fb, n, library.frame(n, plc.inverse(), "Seat"))
    return s, n


class Panel:
    def __init__(self):
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("VEX screw")
        p = App.ParamGet(PARAMS)
        self.kind = QtWidgets.QComboBox()
        self.kind.addItems(list(KINDS))
        self.kind.setCurrentText(p.GetString("Screw", "Star"))
        self.nut = QtWidgets.QComboBox()
        self.nut.addItems(list(nuts()))
        self.nut.setCurrentText(p.GetString("Nut", "#8-32 Nylock Nut"))
        self.status = QtWidgets.QLabel()
        lay = QtWidgets.QFormLayout(self.form)
        lay.addRow("Screw", self.kind)
        lay.addRow("Nut", self.nut)
        lay.addRow(self.status)
        self.first = None
        self.ask()
        Gui.Selection.addObserver(self)

    def ask(self, said=""):
        self.status.setText(said + ("click a hole on the head side" if self.first is None else "now the hole on the nut side"))

    def addSelection(self, doc, obj, sub, pnt):
        s = snap.spot(App.getDocument(doc).getObject(obj), sub, Vector(*pnt))
        if s is None:
            return
        if self.first is None:
            self.first = s
        else:
            head, self.first = self.first, None
            # not inside the selection callback, it changes the doc
            QtCore.QTimer.singleShot(0, lambda: self.place(head, s))
        self.ask()

    def place(self, head, tail):
        p = App.ParamGet(PARAMS)
        p.SetString("Screw", self.kind.currentText())
        p.SetString("Nut", self.nut.currentText())
        doc = head[0].Document
        import UtilsAssembly
        family, nut = KINDS[self.kind.currentText()], nuts()[self.nut.currentText()]
        put = ui.run("Place VEX screw", lambda: fasten(doc, head, tail, family, nut, UtilsAssembly.activePartOrAssembly()))
        if put:
            screw, _ = put
            doc.recompute()
            self.ask(f"put in a {screw.Label}\n")
        Gui.Selection.clearSelection()

    def getStandardButtons(self):
        return QtWidgets.QDialogButtonBox.Close

    def reject(self):
        Gui.Selection.removeObserver(self)
        Gui.Control.closeDialog()
        return True


class Screw:
    def GetResources(self):
        return {"Pixmap": "vex-screw.svg", "MenuText": "Screw",
                "ToolTip": "Click a hole on the head side, then the one on the nut side. Puts in the shortest screw that makes it through the nut"}

    def Activated(self):
        Gui.Control.showDialog(Panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()
