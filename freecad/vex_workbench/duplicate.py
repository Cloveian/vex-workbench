# duplicate tool. a copy of the picked parts or groups, mirrored across a plane or turned about an axis. parts only ever get turned, so they stay real parts
import itertools
import json
import re

import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Matrix, Placement, Rotation, Vector
from PySide import QtWidgets

from . import align, library, metal, snap, ui
from .metal import IN

AXES = {"X": Vector(1, 0, 0), "Y": Vector(0, 1, 0), "Z": Vector(0, 0, 1)}
SAME = 1e-3  # mm, vertices closer than this are the same one
GROUPS = ("App::Part", "App::DocumentObjectGroup", "Assembly::AssemblyObject")
FLIP_Y = Matrix(1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)  # a flip of a frame's own y, keeps a mirrored frame right handed
LIMITS = ("EnableLengthMin", "EnableLengthMax", "LengthMin", "LengthMax", "Distance", "Distance2", "Angle", "Detach1", "Detach2")  # copied as is, the same in a mirror


def reflection(o, n):
    # across the plane through o with normal n, x - 2((x - o).n)n
    n = Vector(n).normalize()
    d = 2 * o.dot(n)
    return Matrix(1 - 2 * n.x * n.x, -2 * n.x * n.y, -2 * n.x * n.z, d * n.x,
                  -2 * n.y * n.x, 1 - 2 * n.y * n.y, -2 * n.y * n.z, d * n.y,
                  -2 * n.z * n.x, -2 * n.z * n.y, 1 - 2 * n.z * n.z, d * n.z,
                  0, 0, 0, 1)


def own_mirror(shape):
    # (reflection across the plane through its middle it fits best, how many vertices miss). 0 misses is exact, more is a handed part (mecanum, the motors)
    def key(p):
        return round(p.x / SAME), round(p.y / SAME), round(p.z / SAME)

    c = shape.BoundBox.Center
    pts = [v.Point for v in shape.Vertexes]
    have = {key(p) for p in pts}
    near = list(itertools.product((-1, 0, 1), repeat=3))  # a point right on a cell edge rounds either way

    def missing(m, cap):
        # mirrored vertices with no vertex there, up to cap. past the best so far its out anyway
        out = []
        for p in pts:
            k = key(m.multVec(p))
            if not any((k[0] + i, k[1] + j, k[2] + l) in have for i, j, l in near):
                out.append(m.multVec(p))
                if len(out) >= cap:
                    break
        return out

    planes = list(AXES.values())
    # round stuff has its planes at any turn round its axis (vex's torx lobes), bewteen the farthest vertex out and each one level with it
    for a in AXES.values():
        def out(p):
            return (p - c) - a * (p - c).dot(a)
        far = max(pts, key=lambda p: out(p).Length)
        planes += [far - q for q in pts if (far - q).Length > SAME and abs(out(q).Length - out(far).Length) < SAME and abs((q - far).dot(a)) < SAME]
    best, gone = None, pts + [c]
    for n in planes:
        m = reflection(c, n)
        k = missing(m, len(gone))
        if len(k) < len(gone):
            best, gone = m, k
        if not gone:
            break
    # a few left can be where an edge got spilt, on a torx screw where vex's shank stub meets ours. those still land on an edge, a drilled hole's lands on flat metal
    if 0 < len(gone) <= 20:
        edges = Part.Compound(shape.Edges)
        if all(edges.distToShape(Part.Vertex(p))[0] < SAME for p in gone):
            gone = []
    return best, len(gone)


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
    # reflection taking hand a onto hand b, across the plane square to the axle halfway between them. exact on the V2 mecanums, vex's V1 ones dont quite match
    box = a.BoundBox
    size = [box.XLength, box.YLength, box.ZLength]
    return reflection((box.Center + b.BoundBox.Center) * 0.5, list(AXES.values())[size.index(min(size))])


def frame(o):
    # world placement of what ever o sits in
    p = o.getParentGeoFeatureGroup()
    return p.getGlobalPlacement() if p else Placement()


def copied_ref(ref, names, owns):
    # a joint ref onto the copies, None if its not all on copied parts or a neaely mirrored one (a motor) has no hole there
    obj, subs = ref or (None, [""])
    if obj is None or obj.Name not in names:
        return None
    out = []
    for sub in subs:
        owner, name = library.holder(obj, sub)
        cp = names.get(owner.Name)
        if cp is None:
            return None
        path = [names[p].Name if p in names else p for p in sub.split(".")]
        if owns is not None:
            # the mirror of a frame on its own source, own x frame x FLIP_Y, so W' frame' = M W frame FLIP_Y
            lcs = cp.Name in owns and owner.LinkedObject.getObject(name or "")
            if not lcs or lcs.TypeId != "App::LocalCoordinateSystem":
                return None
            own, exact = owns[cp.Name]
            plc = Placement(own.multiply(lcs.Placement.toMatrix()).multiply(FLIP_Y))
            try:
                if not (exact or library.on_hole(cp, plc)):
                    return None
            except ValueError:
                return None  # no holes at all
            path[-2] = library.frame(cp, plc, lcs.Label.rstrip("0123456789") or "Hole").Name
        out.append(".".join(path))
    return [names[obj.Name], out]


def along(doc, names, owns):
    # copies of the joints with both ends on copied parts, how many. owns: copy name -> (its own reflection, exact or not), None for a turn
    n = 0
    for j in [o for o in doc.Objects if hasattr(o, "JointType") and hasattr(o, "Reference1")]:
        refs = [copied_ref(getattr(j, p), names, owns) for p in ("Reference1", "Reference2")]
        if None in refs:
            continue
        offs = [j.Offset1, j.Offset2]
        lo, hi = (j.EnableAngleMin, j.AngleMin), (j.EnableAngleMax, j.AngleMax)
        if owns is not None:
            # same gap, the spin goes the other way
            offs = [Placement(FLIP_Y.multiply(o.toMatrix()).multiply(FLIP_Y)) for o in offs]
            lo, hi = (hi[0], -hi[1]), (lo[0], -lo[1])
        asm = j.Proxy.getAssembly(j)
        k = snap.joint(names.get(asm.Name, asm), j.JointType, *refs, *offs)  # a whole copied assembly gets its own
        for p in LIMITS:
            setattr(k, p, getattr(j, p))
        k.EnableAngleMin, k.AngleMin = lo
        k.EnableAngleMax, k.AngleMax = hi
        if getattr(j, "VexAlign", False):
            align.ours(k)
        n += 1
    return n


def duplicate(objs, mirror=None, turn=None):
    # copies of objs next to them, every vex part mirrored with mirror (a reflection matrix) or turned with turn (a placement)
    # labels back of the handed ones that went to their other hand, the ones with none that only got turned, and how many joints came along
    doc = objs[0].Document
    swapped, handed = [], []
    names, owns = {}, {}  # original name -> its copy, copy name -> (own, exact) (mirror only)
    objs = [o for o in objs if not any(up in objs for up in o.InListRecursive)]  # a part in a picked group comes with it
    for obj in objs:
        if not (vex(obj) or obj.TypeId in GROUPS):
            raise ValueError(f"{obj.Label} isn't a VEX part or a group of them")
        mine = under(obj)
        copies = doc.copyObject(mine, False)
        parent = obj.getParentGeoFeatureGroup() or obj.getParentGroup()
        if parent:
            parent.addObject(copies[0])
        names.update((was.Name, cp) for was, cp in zip(mine, copies))
        for was, cp in zip(mine, copies):
            if not vex(was):
                continue
            world = frame(was).multiply(was.Placement)
            if turn:
                cp.Placement = frame(cp).inverse().multiply(turn.multiply(world))
                continue
            src = was.LinkedObject
            closest, off = library.cached(src, own_mirror)
            own = None if off else closest
            flip = own is None and other_hand(was)
            if flip:
                library.restep(cp, flip)
                swapped.append(was.Label)
                own = hands(Part.getShape(src), Part.getShape(cp.LinkedObject))
            elif own is None and library.steps(was):
                # a bend and an off center hole leave no middle plane, so its the plain part's mirror with the steps mirrored too
                plain, off = library.cached(library.source(doc, library.part_of(was)), own_mirror)
                if not off:
                    own = plain
                    cp.VexSteps = json.dumps([metal.mirrored(s, own) for s in library.steps(was)])
                    library.retarget(cp)
            exact = own is not None
            if not exact:
                handed.append(was.Label)
                own = closest  # the plane it nearly mirrors across, still the same hand
            owns[cp.Name] = own, exact
            # two reflections make a turn, so the part comes out real and in the mirror spot
            cp.Placement = frame(cp).inverse().multiply(Placement(mirror.multiply(world.toMatrix()).multiply(own)))
            if cp.ElementCount:
                cp.PlacementList = [Placement(own.multiply(e.toMatrix()).multiply(own)) for e in was.PlacementList]
    doc.recompute()
    joints = along(doc, names, None if turn else owns)
    doc.recompute()
    return swapped, handed, joints


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
        swapped, handed, joints = got
        said = [f"copied {len(objs)}"]
        if joints:
            said.append(f"{joints} joint{'s' if joints > 1 else ''} came along")
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
