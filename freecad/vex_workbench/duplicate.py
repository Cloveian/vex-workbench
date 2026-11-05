# duplicate tool. a copy of the picked parts or groups, mirrored across a plane or turned about an axis. parts only ever get turned, so they stay real parts
import re

import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Matrix, Placement, Rotation, Vector
from PySide import QtWidgets

from . import library, ui
from .metal import IN

AXES = {"X": Vector(1, 0, 0), "Y": Vector(0, 1, 0), "Z": Vector(0, 0, 1)}
SAME = 1e-3  # mm, vertices closer than this are the same one
GROUPS = ("App::Part", "App::DocumentObjectGroup", "Assembly::AssemblyObject")


def reflection(o, n):
    # across the plane through o with normal n, x - 2((x - o).n)n
    n = Vector(n).normalize()
    d = 2 * o.dot(n)
    return Matrix(1 - 2 * n.x * n.x, -2 * n.x * n.y, -2 * n.x * n.z, d * n.x,
                  -2 * n.y * n.x, 1 - 2 * n.y * n.y, -2 * n.y * n.z, d * n.y,
                  -2 * n.z * n.x, -2 * n.z * n.y, 1 - 2 * n.z * n.z, d * n.z,
                  0, 0, 0, 1)


def own_mirror(shape):
    # a reflection across one of its own middle planes it lands back on itself under, None for a handed part (mecanum, the motors)
    def key(p):
        return round(p.x / SAME), round(p.y / SAME), round(p.z / SAME)

    c = shape.BoundBox.Center
    pts = [v.Point for v in shape.Vertexes]
    have = {key(p) for p in pts}
    for n in AXES.values():
        m = reflection(c, n)
        if all(key(m.multVec(p)) in have for p in pts):
            return m
    return None


def vex(o):
    return o.TypeId == "App::Link" and hasattr(o.LinkedObject, "VexName")


def under(obj):
    # obj and every group and vex link in it, not the sources or an assembly's joints
    out = [obj]
    if obj.TypeId in GROUPS:
        for c in obj.Group:
            if vex(c) or c.TypeId in GROUPS:
                out += under(c)
    return out


def other_hand(link):
    # step key of a Left part's Right one or the other way, None for anything else
    if not hasattr(link, "VexStep"):
        return None
    steps = library.index()[2]
    name = steps[link.VexStep]["name"]
    flip = re.sub("Left|Right", lambda m: "Right" if m[0] == "Left" else "Left", name)
    return next((k for k, p in steps.items() if p["name"] == flip and flip != name), None)


def hands(a, b):
    # reflection taking hand a onto hand b, across the plane square to the axle halfway between them. exact on the V2 mecanums, vex's V1 ones dont quiet match
    box = a.BoundBox
    size = [box.XLength, box.YLength, box.ZLength]
    return reflection((box.Center + b.BoundBox.Center) * 0.5, list(AXES.values())[size.index(min(size))])


def frame(o):
    # world placement of what ever o sits in
    p = o.getParentGeoFeatureGroup()
    return p.getGlobalPlacement() if p else Placement()


def duplicate(objs, mirror=None, turn=None):
    # copies of objs next to them, every vex part mirrored with mirror (a reflection matrix) or turned with turn (a placement)
    # labels back of the handed ones that went to their other hand, and the ones with none that only got turned
    doc = objs[0].Document
    swapped, handed = [], []
    objs = [o for o in objs if not any(up in objs for up in o.InListRecursive)]  # a part in a picked group comes with it
    for obj in objs:
        if not (vex(obj) or obj.TypeId in GROUPS):
            raise ValueError(f"{obj.Label} isn't a VEX part or a group of them")
        mine = under(obj)
        copies = doc.copyObject(mine, False)
        parent = obj.getParentGeoFeatureGroup() or obj.getParentGroup()
        if parent:
            parent.addObject(copies[0])
        for was, cp in zip(mine, copies):
            if not vex(was):
                continue
            world = frame(was).multiply(was.Placement)
            if turn:
                cp.Placement = frame(cp).inverse().multiply(turn.multiply(world))
                continue
            src = was.LinkedObject
            own = library.cached(src, own_mirror)
            flip = own is None and other_hand(was)
            if flip:
                library.restep(cp, flip)
                swapped.append(was.Label)
                own = hands(Part.getShape(src), Part.getShape(cp.LinkedObject))
            elif own is None:
                handed.append(was.Label)
                own = reflection(Part.getShape(src).BoundBox.Center, AXES["Z"])  # turned to where the mirror would be, still the same hand
            # two reflections make a turn, so the part comes out real and in the mirror spot
            cp.Placement = frame(cp).inverse().multiply(Placement(mirror.multiply(world.toMatrix()).multiply(own)))
            if cp.ElementCount:
                cp.PlacementList = [Placement(own.multiply(e.toMatrix()).multiply(own)) for e in was.PlacementList]
    doc.recompute()
    return swapped, handed


class Panel:
    def __init__(self):
        p = App.ParamGet(ui.PARAMS)
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("VEX duplicate")
        lay = QtWidgets.QFormLayout(self.form)
        self.how = QtWidgets.QComboBox()
        self.how.addItems(["Mirror", "Turn"])
        self.how.setCurrentText(p.GetString("DuplicateHow", "Mirror"))
        self.axis = QtWidgets.QComboBox()
        self.axis.addItems(list(AXES))
        self.axis.setCurrentText(p.GetString("DuplicateAxis", "X"))
        self.at = ui.number(-72, 72, " in", 0, 0.5, 3)  # the mirror plane, this far along the axis
        self.angle = ui.number(-360, 360, " deg", 180)
        go = QtWidgets.QPushButton("Duplicate")
        go.clicked.connect(self.go)
        self.status = QtWidgets.QLabel("select the parts or groups to copy, then Duplicate")
        self.status.setWordWrap(True)
        for row in (("Copy", self.how), ("Axis", self.axis), ("Plane at", self.at), ("Turn by", self.angle), (go,), (self.status,)):
            lay.addRow(*row)
        self.how.currentTextChanged.connect(self.mode)
        self.mode(self.how.currentText())

    def mode(self, how):
        self.at.setEnabled(how == "Mirror")
        self.angle.setEnabled(how == "Turn")

    def go(self):
        import UtilsAssembly
        how, axis = self.how.currentText(), self.axis.currentText()
        p = App.ParamGet(ui.PARAMS)
        p.SetString("DuplicateHow", how)
        p.SetString("DuplicateAxis", axis)
        objs = Gui.Selection.getSelection()
        if not objs:
            self.status.setText("select the parts or groups to copy first")
            return
        # plane and axis in the active part or assembly, through its origin
        active = UtilsAssembly.activePartOrAssembly()
        f = active.getGlobalPlacement() if active else Placement()
        n = f.Rotation.multVec(AXES[axis])
        if how == "Mirror":
            got = ui.run("Mirror VEX parts", lambda: duplicate(objs, mirror=reflection(f.multVec(AXES[axis] * self.at.value() * IN), n)))
        else:
            spin = Placement(Vector(), Rotation(AXES[axis], self.angle.value()))
            got = ui.run("Turn VEX parts", lambda: duplicate(objs, turn=f.multiply(spin).multiply(f.inverse())))
        if got is None:
            return
        Gui.Selection.clearSelection()
        swapped, handed = got
        said = [f"copied {len(objs)}"]
        if swapped:
            said.append(f"{', '.join(swapped)} went to the other hand")
        if handed:
            said.append(f"{', '.join(handed)} only turned into place, there's no other hand of {'it' if len(handed) == 1 else 'them'}")
        self.status.setText(". ".join(said))

    def getStandardButtons(self):
        return QtWidgets.QDialogButtonBox.Close

    def reject(self):
        Gui.Control.closeDialog()
        return True


DUPLICATE = ui.Command(Panel, "vex-duplicate.svg", "Duplicate",
                       "Copy the selected parts or groups mirrored across a plane or turned about an axis. Parts get turned, not flipped, so they stay real parts")
