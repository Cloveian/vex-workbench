# shop work on placed metal, bend or cut on a line through a hole or drill one anywhere. kept on that one copy as steps
import FreeCAD as App
import Part
from FreeCAD import Vector
from PySide import QtCore, QtWidgets

from . import library, metal, snap, ui
from .metal import IN, X

GRID = 0.25 * IN  # mm, drill's grid to start, half the hole pitch


def wall(link, center, n):
    # thicknes at a hole, from its loop on the other face
    deep = [(center - c).dot(n) for _, c, m in library.cached(link.LinkedObject, library.holes)
            if m.dot(n) < -0.99 and (center - c).cross(n).Length < 1e-3 and (center - c).dot(n) > 1e-6]
    if not deep:
        raise ValueError(f"can't tell how thick {link.Label} is there, click a hole that goes all the way through")
    return min(deep)


def length(n, before):
    # the part's length on a face out along n. its x, but on a leg an earlier bend stood square to x, its that bend's face normal
    for way in [X] + [Vector(*s["n"]) for s in reversed(before) if s["do"] == "fold"]:
        along = way - n * n.dot(way)
        if along.Length > 1e-6:
            along.normalize()
            return along
    raise ValueError("that's an end face, pick a hole on a side")


def line(center, n, across, off, before):
    # point and direction of a line through the hole, across the length or along it, off mm to the side
    along = length(n, before)
    d = n.cross(along) if across else along
    return center + n.cross(d) * off, d


def lined(link, pt, across, off, do):
    # a step on a line through the hole nearest pt
    center, n = library.hole_at(link, pt)
    p, d = line(center, n, across, off, library.steps(link))
    s = {"do": do, "p": list(p), "d": list(d), "n": list(n), "t": wall(link, center, n), "center": list(center)}
    s["side"] = smaller(Part.getShape(link.LinkedObject), s)
    return s


def smaller(shape, s):
    # the side (+-1) that turns or goes. just whats cut off the clicked wall counts, a far flange the plane slices stays put
    p, u, n = metal.line(dict(s, side=1))
    past = sum(x.Volume for x in metal.split(shape, p, u, n, s["t"])[1])
    return 1 if past < shape.Volume / 2 else -1


def bend(link, pt, across, off, angle):
    cat = library.cat()["metal"]
    return dict(lined(link, pt, across, off, "fold"), angle=angle, r=cat["bend"] * IN, k=cat["k"])


def cut(link, pt, across, off):
    return lined(link, pt, across, off, "cut")


def on_face(src, n, p):
    # hole centers on the plane through p, facing n
    return [h for _, h, m in library.cached(src, library.holes) if m.dot(n) > 1 - 1e-6 and abs(n.dot(h - p)) < 1e-6]


def lattice(near, n, before):
    # the grid on a face goes off its first hole along then across that wasnt drilled, so any grid size is one lattice
    e1 = length(n, before)
    e2 = n.cross(e1)
    up = e2 if next(x for x in e2 if abs(x) > 1e-6) > 0 else -e2  # both sides of a wall pick the same hole
    drilled = [Vector(*s["c"]) for s in before if s["do"] == "drill"]
    plain = [h for h in near if all((h - d).cross(n).Length > 1e-6 for d in drilled)] or near  # in the plane, its loop on the far side counts too
    return min(plain, key=lambda h: (round(h.dot(e1), 6), round(h.dot(up), 6))), e1, e2


def gridded(c, grid, anchor, e1, e2):
    # c onto the nearest grid spot
    return anchor + e1 * round((c - anchor).dot(e1) / grid) * grid + e2 * round((c - anchor).dot(e2) / grid) * grid


def drill(link, pt, dia, grid=GRID):
    # a hole at pt (link coords) through the wall its on. snapped onto that face's lattice(), grid mm, 0 or False for right there
    src = link.LinkedObject
    shape = Part.getShape(src)
    v = Part.Vertex(pt)
    # the face whose plane its on first. a click on a hole's dot is as far from the hole's own wall as from the face round it
    face = min((f for f in shape.Faces if f.Surface.TypeId == "Part::GeomPlane"),
               key=lambda f: (round(abs(f.normalAt(0, 0).dot(pt - f.Vertexes[0].Point)), 6), f.distToShape(v)[0]))
    n = face.normalAt(0, 0)
    c = pt - n * n.dot(pt - face.Vertexes[0].Point)
    near = on_face(src, n, c)
    if near:
        t = wall(link, min(near, key=lambda h: (h - c).Length), n)  # off a hole, a plate's grid spots are small holes already so a ray there finds nothing
        if grid:
            c = gridded(c, grid, *lattice(near, n, library.steps(link)))
    else:
        # no hole on that face, a ray in to the first face it leaves through
        hits = library.hits(library.cached(src, library.boxed), c + n * library.OUT, -n, shape.BoundBox.DiagonalLength)
        if len(hits) < 2:
            raise ValueError("can't find the other side of the wall there")
        t = hits[1] - hits[0]
    return {"do": "drill", "c": list(c), "n": list(n), "dia": dia, "t": t}


def grid_spots(link, grid):
    # every spot drill() would snap to on link, link coords, grid mm. on the metal only, holes and edges left out
    src = link.LinkedObject
    before = library.steps(link)
    loops = [(w.BoundBox, m) for w, _, m in library.cached(src, library.holes)]
    out, seen = [], set()
    for face in Part.getShape(src).Faces:
        if face.Surface.TypeId != "Part::GeomPlane":
            continue
        n = face.normalAt(0, 0)
        near = on_face(src, n, face.Vertexes[0].Point)
        if not near:
            continue
        anchor, e1, e2 = lattice(near, n, before)
        b = face.BoundBox
        corners = [Vector(x, y, z) for x in (b.XMin, b.XMax) for y in (b.YMin, b.YMax) for z in (b.ZMin, b.ZMax)]
        span = [[round((p - anchor).dot(e) / grid) for p in corners] for e in (e1, e2)]
        # the outline on its own, a plate face with all its holes is ~4 ms an isInside
        outline = Part.Face(face.OuterWire)
        edges = [(e.BoundBox, e) for e in face.OuterWire.Edges]
        for bb, _ in edges:
            bb.enlarge(1e-6)
        holes = [App.BoundBox(bb) for bb, m in loops if m.dot(n) > 1 - 1e-6]
        for bb in holes:
            bb.enlarge(1e-6)  # flat along n, a spot on the face can miss it on float noise
        for i in range(min(span[0]), max(span[0]) + 1):
            for j in range(min(span[1]), max(span[1]) + 1):
                p = anchor + e1 * (i * grid) + e2 * (j * grid)
                key = tuple(round(x, 6) for x in p)
                if key in seen or any(bb.isInside(p) for bb in holes):
                    continue
                # isInside counts a spot right on the edge as in, a drill there is half a hole
                if any(bb.isInside(p) and e.distToShape(Part.Vertex(p))[0] < 1e-6 for bb, e in edges):
                    continue
                if outline.isInside(p, 1e-6, True):
                    seen.add(key)
                    out.append(p)
    return out


class Clicked(snap.Clicks):
    # one click makes a step on that copy, then the boxes (and the button, side -1) redo the last one. step() builds it, tweak() puts the boxes in
    UNDO = "Rework VEX part"

    def __init__(self, title, rows, button=None, other=()):
        # other: rows that dont redo the last one, like the drill's grid
        self.last = None  # (link, step count) of the last one done, what the boxes change
        for box in [w for _, w in rows if isinstance(w, QtWidgets.QDoubleSpinBox)]:
            box.setKeyboardTracking(False)  # one rebuild per typed number
            box.valueChanged.connect(lambda: self.redo())
        for box in [w for _, w in rows if isinstance(w, QtWidgets.QComboBox)]:
            box.currentTextChanged.connect(lambda: self.redo())
        if button:
            flip = QtWidgets.QPushButton(button)
            flip.clicked.connect(lambda: self.redo(-1))
            rows = rows + [(flip,)]
        super().__init__(title, rows + list(other))

    def one(self):
        return True

    def act(self, spot, _):
        link = spot[0]

        def go():
            if library.part_of(link).get("family") not in metal.PROFILES:
                raise ValueError(f"{link.Label} isn't VEX metal, only metal gets worked")
            library.rework(link, library.steps(link) + [self.step(link, spot[1])])
            return True
        if not ui.run(self.UNDO, go):
            return None
        self.last = link, len(library.steps(link))
        self.flipped = 1  # the button's -1, on top of whichever side is smaller
        link.Document.recompute()
        return f"{self.DID} {link.Label}, the boxes change that one"

    def redo(self, side=1):
        link, count = self.last or (None, 0)
        # deleted, or that step undone since
        if link is None or link not in self.doc.Objects or len(library.steps(link)) != count:
            self.last = None
            return
        self.flipped *= side
        done = library.steps(link)

        def go():
            self.tweak(link, done[-1], done[:-1])  # in here, a line it cant make shows the error box
            library.rework(link, done)
            return True
        if not ui.run(self.UNDO, go):
            self.flipped *= side  # refused, nothing got flipped
        link.Document.recompute()


class Lined(Clicked):
    # bend and cut, a line through the hole across or along, slid over
    ONE = "click a hole the line goes through"

    def __init__(self, title, rows, button):
        p = App.ParamGet(ui.PARAMS)
        self.across = QtWidgets.QComboBox()
        self.across.addItems(["Across", "Along"])
        self.across.setCurrentText(p.GetString("ShopLine", "Across"))
        self.off = ui.number(-12, 12, " in", step=0.25, decimals=3)
        super().__init__(title, [("Line", self.across), ("Off the hole", self.off)] + rows, button)

    def where(self):
        App.ParamGet(ui.PARAMS).SetString("ShopLine", self.across.currentText())
        return self.across.currentText() == "Across", self.off.value() * IN

    def tweak(self, link, s, before):
        across, off = self.where()
        p, d = line(Vector(*s["center"]), Vector(*s["n"]), across, off, before)
        s.update(p=list(p), d=list(d))
        # a new line can have the other side smaller
        s["side"] = smaller(library.worked(link.Document, library.part_of(link), before), s) * self.flipped


class BendPanel(Lined):
    DID = "bent"

    def __init__(self):
        self.angle = ui.number(-180, 180, " deg", App.ParamGet(ui.PARAMS).GetFloat("BendAngle", 90))
        super().__init__("VEX bend", [("Angle", self.angle)], "Other side turns")

    def step(self, link, pt):
        App.ParamGet(ui.PARAMS).SetFloat("BendAngle", self.angle.value())
        return bend(link, pt, *self.where(), self.angle.value())

    def tweak(self, link, s, before):
        super().tweak(link, s, before)
        s["angle"] = self.angle.value()


class CutPanel(Lined):
    DID = "cut"

    def __init__(self):
        super().__init__("VEX cut", [], "Keep the other side")

    def step(self, link, pt):
        return cut(link, pt, *self.where())


class DrillPanel(Clicked):
    DID = "drilled"
    ONE = "click where the hole goes, it snaps to the grid. hold Shift for right where you click"

    def __init__(self):
        prefs = App.ParamGet(ui.PARAMS)
        self.size = ui.number(0.05, 1, " in", prefs.GetFloat("DrillSize", 0.17), step=0.005, decimals=3)
        self.grid = ui.number(0.05, 1, " in", prefs.GetFloat("DrillGrid", GRID / IN), step=0.05, decimals=3)
        self.grid.setKeyboardTracking(False)  # one regrid per typed number
        self.show_grid = QtWidgets.QCheckBox("Show the grid")
        self.show_grid.setChecked(prefs.GetBool("DrillShowGrid", False))
        self.grids = {}  # (source, grid) -> spots, worked sources get new names
        super().__init__("VEX drill", [("Size", self.size)], other=[("Grid", self.grid), (self.show_grid,)])
        self.grid.valueChanged.connect(self.regrid)
        self.show_grid.toggled.connect(self.regrid)

    def regrid(self, *_):
        prefs = App.ParamGet(ui.PARAMS)
        prefs.SetFloat("DrillGrid", self.grid.value())
        prefs.SetBool("DrillShowGrid", self.show_grid.isChecked())
        self.refresh()

    def extra(self, link):
        if not self.show_grid.isChecked() or library.part_of(link).get("family") not in metal.PROFILES:
            return []
        key = (link.LinkedObject.Name, self.grid.value())
        if key not in self.grids:
            self.grids[key] = grid_spots(link, self.grid.value() * IN)
        return self.grids[key]

    def step(self, link, pt):
        App.ParamGet(ui.PARAMS).SetFloat("DrillSize", self.size.value())
        shift = QtWidgets.QApplication.queryKeyboardModifiers() & QtCore.Qt.ShiftModifier
        return drill(link, pt, self.size.value() * IN, 0 if shift else self.grid.value() * IN)

    def tweak(self, link, s, before):
        s["dia"] = self.size.value() * IN


BEND = ui.Command(BendPanel, "vex-bend.svg", "Bend", "Click a hole the bend goes through. It folds there by the angle, then change the line, angle or which side turns")
CUT = ui.Command(CutPanel, "vex-cut.svg", "Cut", "Click a hole the cut goes through, across or along the part. The smaller side goes, or keep that one instead")
DRILL = ui.Command(DrillPanel, "vex-drill.svg", "Drill", "Click a spot on the metal and a round hole goes through there, snapped to the grid. Hold Shift to skip the snap")
