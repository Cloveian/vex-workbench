# snap to hole: click holes on VEX parts, get a frame on each exact center for Assembly joints. plus the joints and two-click panel screws and spacers use
import FreeCAD as App
import FreeCADGui as Gui
from FreeCAD import Vector
from PySide import QtCore, QtWidgets

from . import library, ui

Z = Vector(0, 0, 1)
OFF_AXIS = 0.01  # mm


def spot(root, sub, pt):
    # (link, point in its own coords, link placement in the world, (root, path down to the link)) for one click, None off VEX parts
    objs = root.getSubObjectList(sub)  # root first, then one per name in sub
    k = max((i for i, o in enumerate(objs) if hasattr(o, "VexFamily") or hasattr(o, "VexStep")), default=None)
    if k is None:
        return None
    names = sub.split(".")
    # a link array element sits under the link, its placement counts too. a number in the path, or a LinkElement with ShowElement on
    element = names[k].isdigit() or (k + 1 < len(objs) and objs[k + 1].isDerivedFrom("App::LinkElement"))
    n = k + 1 if element else k
    # placement of the link through the whole path, assembly and all. App::Link has no getGlobalPlacement in 1.1
    path = "".join(name + "." for name in names[:n])
    plc = root.getSubObject(path, retType=3) if n else root.Placement
    return objs[k], plc.inverse().multVec(pt), plc, (root, path)


def picked():
    out = []
    for sel in Gui.Selection.getSelectionEx("", 0):
        for sub, pt in zip(sel.SubElementNames, sel.PickedPoints):
            s = spot(sel.Object, sub, pt)
            if s:
                out.append(s)
    return out


def hole(s):
    # the clicked hole's frame, and where it is in the world
    link, pt, plc, _ = s
    f = library.hole_frame(link, pt)
    return f, plc.multiply(f.Placement)


def line(a, b):
    # (how far b is out along a.z, b.z dot a.z) for two frames in the world, None when b is off that axis
    z = a.Rotation.multVec(Z)
    d = b.Base - a.Base
    if d.cross(z).Length > OFF_AXIS:
        return None
    return d.dot(z), b.Rotation.multVec(Z).dot(z)


def on(obj, f):
    # joint refrence to frame f on obj
    return [obj, [f.Name + ".", f.Name + "."]]


def ref(asm, s, f):
    # joint reference to frame f on the clicked part, None for one outside asm
    import UtilsAssembly
    root, path = s[3]
    comp, sub = UtilsAssembly.getComponentReference(asm, root, path + f.Name + ".")
    return comp and [comp, [sub, sub]]


def inside(parent):
    # world -> parent placement, and parent again if its an assembly to joint in
    local = parent.getGlobalPlacement().inverse() if parent else App.Placement()
    return local, parent if parent and parent.isDerivedFrom("Assembly::AssemblyObject") else None


def fixed(asm, r1, r2):
    import JointObject
    import UtilsAssembly
    if r1 is None:
        return
    j = UtilsAssembly.getJointGroup(asm).newObject("App::FeaturePython", "Joint")
    JointObject.Joint(j, JointObject.JointTypes.index("Fixed"))
    if j.ViewObject:
        JointObject.ViewProviderJoint(j.ViewObject)
    j.Proxy.setJointConnectors(j, [r1, r2])


class Clicks:
    # task panel, click a hole then another and act() gets both spots, what it hands back goes on the status line. PROMPTS for before the first and second click
    def __init__(self, title, rows):
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle(title)
        lay = QtWidgets.QFormLayout(self.form)
        for label, w in rows:
            lay.addRow(label, w)
        self.status = QtWidgets.QLabel()
        lay.addRow(self.status)
        self.first = None
        self.ask()
        Gui.Selection.addObserver(self)

    def ask(self, said=""):
        self.status.setText(said + self.PROMPTS[self.first is not None])

    def addSelection(self, doc, obj, sub, pnt):
        s = spot(App.getDocument(doc).getObject(obj), sub, Vector(*pnt))
        if s is None:
            return
        if self.first is None:
            self.first = s
        else:
            a, self.first = self.first, None
            # not inside the selection callback, it changes the doc
            QtCore.QTimer.singleShot(0, lambda: self.done(a, s))
        self.ask()

    def done(self, a, b):
        said = self.act(a, b)
        if said:
            self.ask(said + "\n")
        Gui.Selection.clearSelection()

    def getStandardButtons(self):
        return QtWidgets.QDialogButtonBox.Close

    def reject(self):
        Gui.Selection.removeObserver(self)
        Gui.Control.closeDialog()
        return True


class HoleFrame:
    def GetResources(self):
        return {"Pixmap": "vex-hole.svg", "MenuText": "Frame on hole",
                "ToolTip": "Frame on the exact center of each clicked hole, or on the end of a shaft, to joint to"}

    def Activated(self):
        spots = picked()
        if not spots:
            QtWidgets.QMessageBox.information(Gui.getMainWindow(), "VEX", "Click a hole on a VEX part first")
            return
        if ui.run("VEX hole frame", lambda: [library.hole_frame(link, pt) for link, pt, *_ in spots]) is None:
            return
        App.ActiveDocument.recompute()
        Gui.Selection.clearSelection()

    def IsActive(self):
        return App.ActiveDocument is not None
