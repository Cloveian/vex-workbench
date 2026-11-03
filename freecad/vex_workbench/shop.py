# shop work on placed metal, bend or cut on a line through a hole, saw a slot, or drill a hole anywhere. kept on that one copy as steps
import math

import FreeCAD as App
import Part
from FreeCAD import Vector
from PySide import QtCore, QtWidgets

from . import library, metal, snap, ui
from .metal import IN, X

GRID = 0.25 * IN  # mm, drill's grid to start, half the hole pitch
KERF = 0.04 * IN  # mm, saw cut to start, my guess at a cutoff wheel
EDGE = 0.1 * IN  # mm, an edge face is the metal's thickness, 0.063 at most


def shifted():
    # Shift held, for right where i clicked
    return bool(QtWidgets.QApplication.queryKeyboardModifiers() & QtCore.Qt.ShiftModifier)


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


def bend(link, pt, across, off, angle, r=None, centered=False):
    # r inside radius in, vex's 0.032 to start. centered puts the middle of the bend on the line
    cat = library.cat()["metal"]
    s = dict(lined(link, pt, across, off, "fold"), angle=angle, r=(cat["bend"] if r is None else r) * IN, k=cat["k"])
    if centered:
        s["centered"] = True  # only when on, older steps stay the same json
    return s


def cut(link, pt, across, off):
    return lined(link, pt, across, off, "cut")


def slot(link, a, b, kerf):
    # a saw cut kerf mm wide from a to b (link coords) through the wall theyre on. doesnt have to go all the way across
    shape = Part.getShape(link.LinkedObject)
    fa, a, t, _ = at_face(link, shape, a)
    fb, b, _, _ = at_face(link, shape, b)
    n = fa.normalAt(0, 0)
    if fb.normalAt(0, 0).dot(n) < 1 - 1e-6 or abs(n.dot(b - a)) > 1e-6:
        raise ValueError("both ends have to be on the same side of the same wall")
    if (b - a).Length < kerf:
        raise ValueError("that cut's shorter than the saw is wide")
    # an end on an outside edge runs off it
    out = [any(e.distToShape(Part.Vertex(p))[0] < 1e-6 for e in free(shape, f)) for f, p in ((fa, a), (fb, b))]
    s = {"do": "slot", "a": list(a), "b": list(b), "n": list(n), "t": t, "kerf": kerf, "out": out}
    keeping(shape, s, 1)
    return s


def keeping(shape, s, side):
    # if the slot cuts bits loose, the biggest stays (side -1 the smalest). kept as a point on it so a Holes change keeps the same one
    s.pop("keep", None)
    pieces = metal.kerf(shape, s).Solids
    if len(pieces) > 1:
        stays = (max if side > 0 else min)(pieces, key=lambda x: x.Volume)
        mid = Part.Vertex((Vector(*s["a"]) + Vector(*s["b"])) * 0.5)
        s["keep"] = list(stays.distToShape(mid)[1][0][0])


def free(shape, face):
    # edges round face that are a sawn or stampped edge of the metal, not a bend or a hole
    n = face.normalAt(0, 0)
    out = []
    for e in face.OuterWire.Edges:
        side = [f for f in shape.ancestorsOfType(e, Part.Face) if not f.isSame(face)]
        if not side or side[0].Surface.TypeId != "Part::GeomPlane" or abs(side[0].normalAt(0, 0).dot(n)) > 1e-6:
            continue
        deep = [n.dot(x.Point) for x in side[0].Vertexes]
        if max(deep) - min(deep) < EDGE:  # wider is the other leg round a 0 radius bend
            out.append(e)
    return out


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


def at_face(link, shape, pt):
    # (face, pt on it, wall there, hole centers on it) for the flat face of shape (source of link) pt is on, link coords
    src = link.LinkedObject
    v = Part.Vertex(pt)
    # the face whose plane its on first. a click on a hole's dot is as far from the hole's own wall as from the face round it
    keyed = [((abs(f.normalAt(0, 0).dot(pt - f.Vertexes[0].Point)) > 1e-6, round(f.distToShape(v)[0], 6)), f)
             for f in shape.Faces if f.Surface.TypeId == "Part::GeomPlane"]
    best = min(k for k, _ in keyed)
    ties = [f for k, f in keyed if k == best]
    # an edge dot is right on the edge face too, the one with holes wins
    face = next((f for f in ties if on_face(src, f.normalAt(0, 0), f.Vertexes[0].Point)), ties[0])
    n = face.normalAt(0, 0)
    c = pt - n * n.dot(pt - face.Vertexes[0].Point)
    near = on_face(src, n, c)
    if near:
        return face, c, wall(link, min(near, key=lambda h: (h - c).Length), n), near  # off a hole, a plate's grid spots are small holes already so a ray there finds nothing
    # no hole on that face, a ray in to the first face it leaves through
    hits = library.hits(library.cached(src, library.boxed), c + n * library.OUT, -n, shape.BoundBox.DiagonalLength)
    if len(hits) < 2:
        raise ValueError("can't find the other side of the wall there")
    return face, c, hits[1] - hits[0], near


def drill(link, pt, dia, grid=GRID):
    # a hole at pt (link coords) through the wall its on. snapped onto that face's lattice(), grid mm, 0 or False for right there
    face, c, t, near = at_face(link, Part.getShape(link.LinkedObject), pt)
    n = face.normalAt(0, 0)
    if near and grid:
        c = gridded(c, grid, *lattice(near, n, library.steps(link)))
    return {"do": "drill", "c": list(c), "n": list(n), "dia": dia, "t": t}


def latticed(link, shape):
    # (face, normal, its lattice()) for every flat face of shape with holes on it
    src = link.LinkedObject
    before = library.steps(link)
    for face in shape.Faces:
        if face.Surface.TypeId != "Part::GeomPlane":
            continue
        n = face.normalAt(0, 0)
        near = on_face(src, n, face.Vertexes[0].Point)
        if near:
            yield face, n, lattice(near, n, before)


def grid_spots(link, grid):
    # every spot drill() would snap to on link, link coords, grid mm. on the metal only, holes and edges left out
    loops = [(w.BoundBox, m) for w, _, m in library.cached(link.LinkedObject, library.holes)]
    out, seen = [], set()
    for face, n, (anchor, e1, e2) in latticed(link, Part.getShape(link.LinkedObject)):
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


def edge_spots(link, grid):
    # where the grid lines cross the outside edges, for a slot to run off at. link coords, grid mm
    shape = Part.getShape(link.LinkedObject)
    out, seen = [], set()
    for face, _, (anchor, e1, e2) in latticed(link, shape):
        for e in free(shape, face):
            if e.Curve.TypeId != "Part::GeomLine":
                continue
            p0 = e.Vertexes[0].Point
            d = e.Vertexes[-1].Point - p0
            for g in (e1, e2):
                if abs(d.dot(g)) < 1e-6:
                    continue  # runs along those grid lines
                at = sorted(((p0 - anchor).dot(g), (p0 + d - anchor).dot(g)))
                for i in range(math.ceil(at[0] / grid - 1e-6), math.floor(at[1] / grid + 1e-6) + 1):
                    p = p0 + d * ((i * grid - (p0 - anchor).dot(g)) / d.dot(g))
                    key = tuple(round(x, 6) for x in p)
                    if key not in seen:
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

    def act(self, spot, other):
        # other: the second click, for a panel thats two clicks right now
        link = spot[0]

        def go():
            if library.part_of(link).get("family") not in metal.PROFILES:
                raise ValueError(f"{link.Label} isn't VEX metal, only metal gets worked")
            library.rework(link, library.steps(link) + [self.step(link, spot[1], other)])
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

    def __init__(self, title, rows, button, other=()):
        p = App.ParamGet(ui.PARAMS)
        self.across = QtWidgets.QComboBox()
        self.across.addItems(["Across", "Along"])
        self.across.setCurrentText(p.GetString("ShopLine", "Across"))
        self.off = ui.number(-12, 12, " in", step=0.25, decimals=3)
        super().__init__(title, [("Line", self.across), ("Off the hole", self.off)] + rows, button, other)

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

    SITS = ["Next to the line", "Centered on it"]

    def __init__(self):
        prefs = App.ParamGet(ui.PARAMS)
        self.angle = ui.number(-180, 180, " deg", prefs.GetFloat("BendAngle", 90))
        # vice and hammer bends are way tighter than vex's
        self.radius = ui.number(0, 0.5, " in", prefs.GetFloat("BendRadius", library.cat()["metal"]["bend"]), step=0.001, decimals=3)
        self.sits = QtWidgets.QComboBox()
        self.sits.addItems(self.SITS)
        self.sits.setCurrentIndex(prefs.GetInt("BendSits", 0))
        rows = [("Angle", self.angle), ("Inside radius", self.radius), ("Bend sits", self.sits)]
        super().__init__("VEX bend", rows, "Other side turns")

    def step(self, link, pt, _):
        prefs = App.ParamGet(ui.PARAMS)
        prefs.SetFloat("BendAngle", self.angle.value())
        prefs.SetFloat("BendRadius", self.radius.value())
        prefs.SetInt("BendSits", self.sits.currentIndex())
        return bend(link, pt, *self.where(), self.angle.value(), self.radius.value(), self.sits.currentIndex() == 1)

    def tweak(self, link, s, before):
        super().tweak(link, s, before)
        s["angle"] = self.angle.value()
        s["r"] = self.radius.value() * IN
        s.pop("centered", None)
        if self.sits.currentIndex() == 1:
            s["centered"] = True


class Gridded:
    # Grid and Show the grid rows for a panel, the grid dots go in through extra(). prefix starts the prefs names
    def grid_rows(self, prefix):
        prefs = App.ParamGet(ui.PARAMS)
        self.prefix = prefix
        self.grid = ui.number(0.05, 1, " in", prefs.GetFloat(prefix + "Grid", GRID / IN), step=0.05, decimals=3)
        self.grid.setKeyboardTracking(False)  # one regrid per typed number
        self.show_grid = QtWidgets.QCheckBox("Show the grid")
        self.show_grid.setChecked(prefs.GetBool(prefix + "ShowGrid", False))
        self.grids = {}  # (finder, source, grid) -> spots, worked sources get new names
        self.grid.valueChanged.connect(self.regrid)
        self.show_grid.toggled.connect(self.regrid)
        return [("Grid", self.grid), (self.show_grid,)]

    def regrid(self, *_):
        prefs = App.ParamGet(ui.PARAMS)
        prefs.SetFloat(self.prefix + "Grid", self.grid.value())
        prefs.SetBool(self.prefix + "ShowGrid", self.show_grid.isChecked())
        self.refresh()

    def found(self, find, link):
        # find(link, grid mm), once per source and grid
        key = (find, link.LinkedObject.Name, self.grid.value())
        if key not in self.grids:
            self.grids[key] = find(link, self.grid.value() * IN)
        return self.grids[key]

    def extra(self, link):
        if not self.show_grid.isChecked() or library.part_of(link).get("family") not in metal.PROFILES:
            return []
        return self.found(grid_spots, link)


class DrillPanel(Gridded, Clicked):
    DID = "drilled"
    ONE = "click where the hole goes, it snaps to the grid. hold Shift for right where you click"

    def __init__(self):
        prefs = App.ParamGet(ui.PARAMS)
        self.size = ui.number(0.05, 1, " in", prefs.GetFloat("DrillSize", 0.17), step=0.005, decimals=3)
        super().__init__("VEX drill", [("Size", self.size)], other=self.grid_rows("Drill"))

    def step(self, link, pt, _):
        App.ParamGet(ui.PARAMS).SetFloat("DrillSize", self.size.value())
        return drill(link, pt, self.size.value() * IN, 0 if shifted() else self.grid.value() * IN)

    def tweak(self, link, s, before):
        s["dia"] = self.size.value() * IN


class CutPanel(Gridded, Lined):
    DID = "cut"
    MODES = ["Line through a hole", "Two points"]
    PROMPTS = ("click where the cut starts, holes, edges and the grid all work", "now where it ends, on the same face")

    def __init__(self):
        prefs = App.ParamGet(ui.PARAMS)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(self.MODES)
        self.mode.setCurrentIndex(prefs.GetInt("CutMode", 0))
        self.kerf = ui.number(0.005, 0.25, " in", prefs.GetFloat("CutKerf", KERF / IN), step=0.005, decimals=3)
        super().__init__("VEX cut", [("Kerf", self.kerf)], "Keep the other side", self.grid_rows("Cut"))
        self.form.layout().insertRow(0, "Cut", self.mode)  # up top, and out of the rows so it doesnt redo
        self.mode.currentIndexChanged.connect(self.modes)
        self.boxes()

    def one(self):
        return self.mode.currentIndex() == 0

    def boxes(self):
        for w in (self.across, self.off):
            w.setEnabled(self.one())
        for w in (self.kerf, self.grid, self.show_grid):
            w.setEnabled(not self.one())

    def modes(self, *_):
        App.ParamGet(ui.PARAMS).SetInt("CutMode", self.mode.currentIndex())
        self.boxes()
        self.first = None
        self.light([])
        self.refresh()
        self.ask()

    def extra(self, link):
        if self.one() or library.part_of(link).get("family") not in metal.PROFILES:
            return []
        return self.found(edge_spots, link) + super().extra(link)

    def snapped(self, link, pt):
        # a face click onto the grid, a dot (edge ones are off it) or Shift right there
        if shifted() or any(dot is link and (c - pt).Length < 1e-6 for dot, c, _, _ in self.spots):
            return pt
        face, c, _, near = at_face(link, Part.getShape(link.LinkedObject), pt)
        return gridded(c, self.grid.value() * IN, *lattice(near, face.normalAt(0, 0), library.steps(link))) if near else c

    def take(self, s):
        # snapped on the click, Shift is per click and act() only runs after the second
        if not self.one():
            try:
                s = (s[0], self.snapped(s[0], s[1]), *s[2:])
            except ValueError as e:
                self.ask(f"{e}\n")
                return
        super().take(s)

    def step(self, link, pt, other):
        if other is None:
            return cut(link, pt, *self.where())
        if other[0] is not link:
            raise ValueError("both ends have to be on the same part")
        App.ParamGet(ui.PARAMS).SetFloat("CutKerf", self.kerf.value())
        return slot(link, pt, other[1], self.kerf.value() * IN)

    def tweak(self, link, s, before):
        if s["do"] != "slot":
            return super().tweak(link, s, before)
        s["kerf"] = self.kerf.value() * IN
        keeping(library.worked(link.Document, library.part_of(link), before), s, self.flipped)


BEND = ui.Command(BendPanel, "vex-bend.svg", "Bend", "Click a hole the bend goes through. It folds there by the angle, then change the line, angle or which side turns")
CUT = ui.Command(CutPanel, "vex-cut.svg", "Cut", "Click a hole the cut goes through, across or along the part. The smaller side goes, or keep that one instead. "
                 "Or set it to two points for a saw cut that stops wherever you want, for slots and notches")
DRILL = ui.Command(DrillPanel, "vex-drill.svg", "Drill", "Click a spot on the metal and a round hole goes through there, snapped to the grid. Hold Shift to skip the snap")
