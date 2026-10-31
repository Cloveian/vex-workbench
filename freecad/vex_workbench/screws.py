# screw tool. click a hole on the head side, then one on the nut side, it puts in the shortest screw that makes it through the nut or into a thread
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from PySide import QtWidgets

from . import derived, library, snap, spacers, stock, ui
from .metal import IN

KINDS = {"Star": "star-screw", "Shoulder": "shoulder-screw"}
BY_HAND = ("shoulder-screw",)  # no auto pick, the shoulder length is my call
NUT_FOLDER = "Hardware/Nuts/8-32 Nuts"
NO_NUT = "No nut"
TAPPED = 0.164 * IN  # mm, 8-32 major. a screw doesnt go through anything smaller so its a thread. 5.5W motor 0.136, 11W 0.1596 lead in
THREAD = 0.375 * IN, library.MIN_THREAD  # mm in the thread, what it aims for and the least it takes
LEAD = 0.01 * IN  # mm, probes start this far in past the face
X = Vector(1, 0, 0)


def nuts():
    _, gen, steps = library.index()
    # vex steps and our generated nuts, both by folder
    return {p["name"]: p for p in [*steps.values(), *gen.values()] if p["folder"].startswith(NUT_FOLDER)}


def sizes(family):
    return sorted((p for p in library.index()[1].values() if p["family"] == family), key=lambda p: p["params"]["length"])


def shortest(family, need):
    # need in mm
    fits = [p for p in sizes(family) if p["params"]["length"] * IN > need - 1e-6]
    if not fits:
        raise ValueError(f"no {library.index()[0][family]['title']} is long enough, it needs {need / IN:.3f}\"")
    return fits[0]


def into(family, gap, deep):
    # gap through the clicked parts, then deep of thread (None = no bottom). shortest that gets 3/8 in, else the longest that gets 1/4
    room = gap + deep if deep is not None else float("inf")
    fit = [p for p in sizes(family) if gap + THREAD[1] - 1e-6 < p["params"]["length"] * IN < room + 1e-6]
    if not fit:
        said = f", it's {deep / IN:.3f}\" deep" if deep is not None else ""
        raise ValueError(f"no {library.index()[0][family]['title']} gets 1/4\" into that hole{said}")
    good = [p for p in fit if p["params"]["length"] * IN > gap + THREAD[0] - 1e-6]
    return good[0] if good else fit[-1]


def bore(link, f):
    # (across, deep) for the hole under frame f, mm. deep is None if it opens into nothing
    src = link.LinkedObject
    far = Part.getShape(src).BoundBox.DiagonalLength
    faces = library.cached(src, library.boxed)
    r = f.Placement.Rotation
    x, z = r.multVec(X), r.multVec(snap.Z)
    start = f.Placement.Base - z * LEAD
    # the loop it was found on, a ray across catches the thread bts in the 11W step. stock parts have none, theyre clean
    loops = [w for w, c, _ in library.cached(src, library.holes) if (c - f.Placement.Base).Length < 1e-6]
    half = library.across(loops[0]) / 2 if loops else library.hits(faces, start, x, far)[0]
    # 5 rays down the hole, theyre all stopped by a bottom. the 11W step has bits of thread in there that stop some
    ends = library.down(faces, start, z, half / 2, far)
    if None not in ends:
        return 2 * half, max(ends) + LEAD
    # through, how long the wall around it is
    wall = library.hits(faces, start + x * half * 1.3, -z, far)
    return 2 * half, wall[0] + LEAD if wall else None


def tapped(link, across):
    fam = getattr(link, "VexFamily", None)
    # a shaft end is small but no thread
    return fam == "standoff" or (fam not in stock.FAMILIES and across < TAPPED)


def gaps(head, tail, a, gap, across):
    # empty stretches between the clicked parts down the screw from a, (spot on the face it starts from, length) each
    z, x = a.Rotation.multVec(snap.Z), a.Rotation.multVec(X)
    # in the metal next to the hole, the axis only ever sees the hole
    start = a.Base + z * LEAD + x * across * 0.65
    same = head[0] is tail[0] and head[2].isSame(tail[2], 1e-9)
    runs = []
    for s in [head] if same else [head, tail]:
        # ray into the part's coords, a moved copy of a plate is ~0.15 s
        back = s[2].inverse()
        faces = library.cached(s[0].LinkedObject, library.boxed)
        ts = [t - LEAD for t in library.hits(faces, back.multVec(start), back.Rotation.multVec(-z), gap + 2 * LEAD)]
        # in, out, in, out... the last one runs into the thread
        runs += [(ts[i], ts[i + 1] if i + 1 < len(ts) else gap, s) for i in range(0, len(ts), 2)]
    out, end, last = [], 0, head
    for t0, t1, s in sorted(runs, key=lambda r: r[0]):
        if t0 - end > spacers.SLOP:
            link, _, plc, path = last
            out.append(((link, plc.inverse().multVec(a.Base - z * end), plc, path), t0 - end))
        if t1 > end:
            end, last = t1, s
    return out


def seat(src):
    # plain face of the nut at z = 0 and its hieght. vex step nuts come in however they were drawn
    shape = Part.getShape(src)
    s, h = derived.upright(shape.copy(), IN)
    return s.Placement.multiply(shape.Placement.inverse()), h


def fasten(doc, head, tail, family, nut, parent=None, od=None):
    # head, tail = snap.spot()s, head side first. nut None = into a thread, od = spacers that size in the gaps
    # screw, nut (None into a thread), spacers back
    (fa, a), (fb, b) = snap.hole(head), snap.hole(tail)
    across, deep = bore(tail[0], fb)
    threaded = nut is None or tapped(tail[0], across)
    got = snap.line(a, b)
    gap = -got[0] if got else 0
    # the nut side faces away from the head, a thread faces back at it
    if got is None or abs(got[1] - (1 if threaded else -1)) > 1e-6 or gap < (-1e-6 if threaded else 1e-6):
        last = "the face the screw goes into" if threaded else "the outside face on the nut side"
        raise ValueError(f"those holes don't line up, click the outside face on the head side then {last}")
    # all picked before anything gets placed
    if threaded:
        screw = into(family, gap, deep)
    else:
        plc, h = seat(library.source(doc, nut))
        screw = shortest(family, gap + h)
    fills = []
    if od:
        fills = [(s, spacers.pick(t, od)) for s, t in gaps(head, tail, a, gap, max(across, bore(head[0], fa)[0]))]
    s = drop(doc, head, screw, parent)
    local, asm = snap.inside(parent)
    n = None
    if not threaded:
        n = library.place(doc, nut, parent)
        n.Placement = local.multiply(b).multiply(plc)
        if asm:
            snap.revolute(asm, snap.ref(asm, tail, fb), snap.on(n, library.frame(n, plc.inverse(), "Seat")))
    put = [o for at, parts in fills for o in spacers.stack(doc, at, parts, parent)]
    return s, n, put


def drop(doc, head, screw, parent=None):
    # screw (a catalog part) in the clicked hole, under its head on that face, shank down -z
    fa, a = snap.hole(head)
    local, asm = snap.inside(parent)
    s = library.place(doc, screw, parent)
    s.Placement = local.multiply(a)
    # frames right on the hole frames, the joint doesnt move anything
    if asm:
        snap.revolute(asm, snap.ref(asm, head, fa), snap.on(s, library.frame(s, App.Placement(), "Seat")))
    return s


class Panel(snap.Clicks):
    PROMPTS = ("click a hole on the head side", "now the hole on the nut side, or the one it screws into")
    ONE = "click the hole it goes in, the head lands on that face"

    def __init__(self):
        p = App.ParamGet(ui.PARAMS)
        self.kind = QtWidgets.QComboBox()
        self.kind.addItems(list(KINDS))
        self.kind.setCurrentText(p.GetString("Screw", "Star"))
        self.mine = QtWidgets.QCheckBox("Pick the screw myself")
        self.mine.setChecked(p.GetBool("ScrewMine", False))
        self.size = QtWidgets.QComboBox()
        self.nut = QtWidgets.QComboBox()
        self.nut.addItems([*nuts(), NO_NUT])
        saved = p.GetString("Nut")
        self.nut.setCurrentText(saved if self.nut.findText(saved) >= 0 else "Nylock Nut")  # none saved, or one thats been renamed since
        self.fill = QtWidgets.QCheckBox("Spacers in gaps")
        self.fill.setChecked(p.GetBool("Fill", False))
        self.od = spacers.od_box()
        self.kind.currentTextChanged.connect(self.relist)
        self.mine.toggled.connect(self.modes)
        super().__init__("VEX screw", [("Screw", self.kind), (self.mine, self.size), ("Nut", self.nut), (self.fill, self.od)])
        self.relist()
        self.size.setCurrentText(p.GetString("ScrewPick"))

    def relist(self):
        family = KINDS[self.kind.currentText()]
        self.size.clear()
        self.size.addItems([s["name"] for s in sizes(family)])
        hand = family in BY_HAND
        if hand and self.mine.isEnabled():
            self.before = self.mine.isChecked()  # back to that on a kind it can pick again
            self.mine.setChecked(True)
        elif not hand and not self.mine.isEnabled():
            self.mine.setChecked(self.before)
        self.mine.setEnabled(not hand)
        self.modes()

    def modes(self):
        for w in (self.nut, self.fill, self.od):
            w.setEnabled(not self.mine.isChecked())
        self.size.setEnabled(self.mine.isChecked())
        self.ask()

    def one(self):
        return self.mine.isChecked()

    def act(self, head, tail):
        import UtilsAssembly
        p = App.ParamGet(ui.PARAMS)
        p.SetString("Screw", self.kind.currentText())
        p.SetBool("ScrewMine", self.mine.isChecked())
        doc = head[0].Document
        active = UtilsAssembly.activePartOrAssembly()
        if tail is None:
            p.SetString("ScrewPick", self.size.currentText())
            pick = library.index()[1][self.size.currentText()]
            put = ui.run("Place VEX screw", lambda: (drop(doc, head, pick, active), None, []))
        else:
            p.SetString("Nut", self.nut.currentText())
            p.SetBool("Fill", self.fill.isChecked())
            family = KINDS[self.kind.currentText()]
            nut = None if self.nut.currentText() == NO_NUT else nuts()[self.nut.currentText()]
            od = spacers.od_from(self.od) if self.fill.isChecked() else None
            put = ui.run("Place VEX screw", lambda: fasten(doc, head, tail, family, nut, active, od))
        if not put:
            return None
        doc.recompute()
        screw, _, extra = put
        return f"put in a {screw.Label}" + (f" + {len(extra)} spacers and washers" if extra else "")


class Screw:
    def GetResources(self):
        return {"Pixmap": "vex-screw.svg", "MenuText": "Screw",
                "ToolTip": "Click a hole on the head side, then the one on the nut side. Puts in the shortest screw that makes it through the nut, "
                "or gets 3/8\" into a threaded hole (1/4\" if that's all there is). Or pick the screw yourself and place it with one click"}

    def Activated(self):
        Gui.Control.showDialog(Panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()
