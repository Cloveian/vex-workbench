# snap to hole: click holes on VEX parts, get a frame on each exact center for Assembly joints. plus the joints and two-click panel screws and spacers use
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from PySide import QtCore, QtWidgets

from . import library, ui

Z = Vector(0, 0, 1)
OFF_AXIS = 0.01  # mm
UNMARKED = ("Hardware/Screws", "Hardware/Nuts", "Motion/Spacers")  # what the tools put in
MARK_SIZE = 9  # px
PICK_SIZE = 14  # px, drawn over the orange one
REFRESH = 100  # ms after the last change, the points get worked out again
MOVES = ("Placement", "Visibility", "VisibilityList", "ElementCount", "LinkedObject", "Group")  # changes that move, hide or swap a part's holes. Group for one draged into another sub-assembly


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


def placed(doc):
    # (link, (root, path)) for every shown VEX link, one per link array element
    out = []

    def walk(root, obj, path):
        if hasattr(obj, "VexFamily") or hasattr(obj, "VexStep"):
            n = obj.ElementCount
            elements = [f"{i}." for i in range(n) if obj.isElementVisible(str(i))] if n else [""]
            out.extend((obj, (root, path + e)) for e in elements)
            return
        for sub in obj.getSubObjects():
            child = obj.getSubObject(sub, retType=1)
            # 1 or 0 from a link array, -1 when its up to the child. array elements say Visibility False in the gui either way
            shown = obj.isElementVisible(sub[:-1])
            if child is not None and (shown > 0 or shown < 0 and child.Visibility):
                walk(root, child, path + sub)

    for root in library.roots(doc):
        if root.Visibility:
            walk(root, root, "")
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
        self.picked = []  # world points lit green
        self.doc = App.ActiveDocument
        self.later = QtCore.QTimer()  # one refresh once a burst of changes settles
        self.later.setSingleShot(True)
        self.later.setInterval(REFRESH)
        self.later.timeout.connect(self.refresh)
        self.mark()
        self.draw()
        self.ask()
        Gui.Selection.addObserver(self)
        App.addDocumentObserver(self)

    def orange(self):
        return Part.Compound([Part.Vertex(plc.multVec(c)) for _, c, plc, _ in self.spots])

    def draw(self):
        self.marks = self.dots("VexHoles", MARK_SIZE, (1.0, 0.35, 0.1))
        self.marks.Shape = self.orange()
        # the select highlight on these goes when the mouse leaves
        self.lit = self.dots("VexPicked", PICK_SIZE, (0.1, 0.9, 0.2))
        self.lit.Shape = Part.Compound([Part.Vertex(p) for p in self.picked])
        if self.lit.ViewObject:
            self.lit.ViewObject.Selectable = False  # clicks go through to the orange ones

    def undraw(self):
        for o in (self.marks, self.lit):
            self.doc.removeObject(o.Name)
        self.marks = self.lit = None

    def redraw(self):
        if self.marks is None and self.doc is not None:
            self.draw()

    def refresh(self):
        # parts placed, moved, hidden or deleted with the panel open
        if self.marks is not None and self.doc is not None:
            self.mark()
            self.marks.Shape = self.orange()

    def dots(self, name, size, color):
        o = self.doc.addObject("Part::Feature", name)
        if o.ViewObject:
            o.ViewObject.PointSize = size
            o.ViewObject.PointColor = color
            o.ViewObject.ShowInTree = False
        return o

    def light(self, spots):
        # picked holes in green till the screw or spacers are in
        self.picked = []
        for link, pt, plc, _ in spots:
            try:
                self.picked.append(plc.multVec(library.hole_at(link, pt)[0]))
            except ValueError:
                pass  # part with no holes, act() says so
        self.lit.Shape = Part.Compound([Part.Vertex(p) for p in self.picked])

    def mark(self):
        # a point on every screw hole and stock end, Vertex<i+1> is spots[i]
        self.spots = []
        found = {}  # per source, copies share it
        for link, (root, path) in placed(self.doc):
            src = link.LinkedObject.Name
            if src not in found:
                found[src] = [] if library.part_of(link)["folder"].startswith(UNMARKED) else library.screw_holes(link)
            plc = root.getSubObject(path, retType=3) if path else root.Placement
            self.spots += [(link, c, plc, (root, path)) for c in found[src]]

    def ask(self, said=""):
        self.status.setText(said + self.PROMPTS[self.first is not None])

    def addSelection(self, doc, obj, sub, pnt):
        if obj == self.marks.Name and sub.startswith("Vertex"):
            s = self.spots[int(sub[6:]) - 1]
        else:
            s = spot(App.getDocument(doc).getObject(obj), sub, Vector(*pnt))
        if s is None:
            return
        if self.first is None:
            self.first = s
            self.light([s])
        else:
            a, self.first = self.first, None
            self.light([a, s])
            # not inside the selection callback, it changes the doc
            QtCore.QTimer.singleShot(0, lambda: self.done(a, s))
        self.ask()

    def done(self, a, b):
        said = self.act(a, b)
        if said:
            self.ask(said + "\n")
        Gui.Selection.clearSelection()
        self.light([])

    def getStandardButtons(self):
        return QtWidgets.QDialogButtonBox.Close

    def reject(self):
        self.undraw()
        self.close()
        return True

    def close(self):
        self.later.stop()
        Gui.Selection.removeObserver(self)
        App.removeDocumentObserver(self)
        Gui.Control.closeDialog()

    def slotCreatedObject(self, obj):
        self.soon(obj)

    def slotDeletedObject(self, obj):
        self.soon(obj)

    def slotChangedObject(self, obj, prop):
        if prop in MOVES:
            self.soon(obj)

    def soon(self, obj):
        if obj.Document == self.doc:
            self.later.start()

    # the points arent part of the robot, they stay out of the file
    def slotStartSaveDocument(self, doc, path):
        if doc == self.doc:
            self.undraw()
            # a failed save never sends the finish
            QtCore.QTimer.singleShot(0, self.redraw)

    def slotFinishSaveDocument(self, doc, path):
        if doc == self.doc:
            self.redraw()

    def slotDeletedDocument(self, doc):
        # closed with the panel still open, the points go with it
        if doc == self.doc:
            self.doc = None
            self.close()


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
