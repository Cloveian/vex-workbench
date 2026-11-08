# screw tool. click a hole (or a few on one face) on the head side, then across on the nut side, it puts in the shortest screw that makes it through the nut or into a thread. or one picked by hand, one click
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets

from . import catalog, derived, library, snap, spacers, stock, ui
from .metal import IN, X

KINDS = {"Star": "star-screw", "Shoulder": "shoulder-screw"}
BY_HAND = ("shoulder-screw",)  # no auto pick, the shoulder length is my call
NUT_FOLDER = "Hardware/Nuts/8-32 Nuts"
NO_NUT = "No nut"
TAPPED = 0.164 * IN  # mm, 8-32 major. a screw doesnt go through anything smaller so its a thread. 5.5W motor 0.136, 11W 0.1596 lead in
THREAD = 0.375 * IN, library.MIN_THREAD  # mm in the thread, what it aims for and the least it takes
LEAD = 0.01 * IN  # mm, probes start this far in past the face


def nuts():
    _, gen, steps = library.index()
    # vex steps and the generated nuts, both by folder
    return {p["name"]: p for p in [*steps.values(), *gen.values()] if catalog.inside(p["folder"], NUT_FOLDER)}


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
    base = f.Placement.Base
    # the loop it was found on, nearest on the axis. a U-channel's inside flange frame sits out in the gap, so the probes start at the loop and the gap goes on top
    on = min((((base - c).dot(z), w, c) for w, c, _ in library.cached(src, library.holes) if (c - base).cross(z).Length < 1e-6), key=lambda t: abs(t[0]), default=None)
    gap, loop, c = on if on and abs(on[0]) < 0.05 * IN else (0, None, base)
    start = c - z * LEAD
    # across off the loop, a ray catches the thread bits in the 11W step. stock parts have none, theyre clean
    half = library.across(loop) / 2 if loop else library.hits(faces, start, x, far)[0]
    # 5 rays down the hole, theyre all stopped by a bottom. the 11W step has bits of thread in there that stop some
    ends = library.down(faces, start, z, half / 2, far)
    if None not in ends:
        return 2 * half, gap + max(ends) + LEAD
    # through, how long the wall around it is
    wall = library.hits(faces, start + x * half * 1.3, -z, far)
    return 2 * half, gap + wall[0] + LEAD if wall else None


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


def facing(s):
    # world (center, normal) of the hole at spot s
    link, pt, plc, _ = s
    c, n = library.hole_spot(link, pt)
    return plc.multVec(c), plc.Rotation.multVec(n)


def flush(a, b):
    # two facing()s on the same face
    return a[1].dot(b[1]) > 1 - 1e-6 and abs((b[0] - a[0]).dot(a[1])) < snap.OFF_AXIS


def on_axis(a, p):
    # world point p on hole a's axis
    return (p - a[0]).cross(a[1]).Length < snap.OFF_AXIS


def seat(src):
    # plain face of the nut at z = 0 and its hieght. vex step nuts come in however they were drawn
    shape = Part.getShape(src)
    s, h = derived.upright(shape.copy(), IN)
    return s.Placement.multiply(shape.Placement.inverse()), h


def fasten(doc, head, tail, family, nut, parent=None, od=None):
    # head, tail = snap.spot()s, head side first. nut None = into a thread, od = spacers that size in the gaps
    # screw, nut (None into a thread), spacers back
    (fa, a), (fb, b) = snap.hole(head), snap.hole(tail)
    # a U-channel's inside flange frame sits out in the gap, everything from here on goes from the metal
    ba, bb = library.off_metal(*head[:2]), library.off_metal(*tail[:2])
    a, b = a.multiply(snap.offset(-ba, 0)), b.multiply(snap.offset(-bb, 0))
    across, deep = bore(tail[0], fb)
    deep = None if deep is None else deep - bb
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
            snap.revolute(asm, snap.ref(asm, tail, fb), snap.on(n, library.frame(n, plc.inverse(), "Seat")), bb)
    put = [o for at, parts in fills for o in spacers.stack(doc, at, parts, parent)]
    return s, n, put


def drop(doc, head, screw, parent=None):
    # screw (a catalog part) in the clicked hole, under its head on that face, shank down -z
    fa, a = snap.hole(head)
    back = library.off_metal(*head[:2])
    local, asm = snap.inside(parent)
    s = library.place(doc, screw, parent)
    s.Placement = local.multiply(a).multiply(snap.offset(-back, 0))
    # Seat on the screw origin and the joint held back the same, it doesnt move anything
    if asm:
        snap.revolute(asm, snap.ref(asm, head, fa), snap.on(s, library.frame(s, App.Placement(), "Seat")), back)
    return s


class Panel(snap.Clicks):
    PROMPTS = ("click a hole on the head side, or a few on one face",
               "more on that face (again to unpick), or the hole on the nut side / the one it screws into")
    ONE = "click the hole it goes in, the head lands on that face"

    def __init__(self):
        p = App.ParamGet(ui.PARAMS)
        self.heads = []  # (spot, facing()) picked on the head side, waiting for a hole across
        self.auto = QtWidgets.QCheckBox("Auto finish, one click across does them all")
        self.auto.setChecked(p.GetBool("ScrewAuto", True))
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
        super().__init__("VEX screw", [("Screw", self.kind), (self.mine, self.size), ("Nut", self.nut), (self.fill, self.od), (self.auto,)])
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
        for w in (self.nut, self.fill, self.od, self.auto):
            w.setEnabled(not self.mine.isChecked())
        self.size.setEnabled(self.mine.isChecked())
        if self.one():
            self.heads, self.first = [], None
            self.light([])
        self.ask()

    def one(self):
        return self.mine.isChecked()

    def take(self, s):
        if self.one():
            self.light([s])
            QtCore.QTimer.singleShot(0, lambda: self.done([(s, None)]))
            return
        try:
            at = facing(s)
        except ValueError as e:
            self.ask(f"{e}\n")
            return
        if not self.heads or flush(self.heads[0][1], at):
            again = [h for h in self.heads if (h[1][0] - at[0]).Length < snap.OFF_AXIS]
            if again:
                self.heads.remove(again[0])
            else:
                self.heads.append((s, at))
            self.first = self.heads[0][0] if self.heads else None
            self.light([h[0] for h in self.heads])
            self.ask(f"{len(self.heads)} picked\n" if len(self.heads) > 1 else "")
            return
        if self.auto.isChecked():
            # every dot on the face clicked, then the one under each head
            there = [(d, p) for d, p in zip(self.spots, self.points) if abs((p - at[0]).dot(at[1])) < snap.OFF_AXIS]
            pairs = []
            for h, ha in self.heads:
                if on_axis(ha, at[0]):
                    pairs.append((h, s))
                    continue
                under = next((d for d, p in there if on_axis(ha, p) and flush(at, facing(d))), None)
                if under:
                    pairs.append((h, under))
        else:
            pairs = [(h, s) for h, ha in self.heads if on_axis(ha, at[0])][:1]
        if not pairs:
            self.ask("none of them line up with a hole there\n")
            return
        self.light([x for pair in pairs for x in pair])
        QtCore.QTimer.singleShot(0, lambda: self.done(pairs))

    def done(self, pairs):
        said = self.act(pairs)
        if said:
            # the rest wait for a click across
            self.heads = [h for h in self.heads if all(h[0] is not a for a, _ in pairs)]
            self.first = self.heads[0][0] if self.heads else None
            self.ask(said + (f", {len(self.heads)} still picked" if self.heads else "") + "\n")
        Gui.Selection.clearSelection()
        self.light([h[0] for h in self.heads])

    def act(self, pairs):
        # (head, tail) spots, tail None for one picked by hand
        p = App.ParamGet(ui.PARAMS)
        p.SetString("Screw", self.kind.currentText())
        p.SetBool("ScrewMine", self.mine.isChecked() if self.mine.isEnabled() else self.before)  # not the forced one shoulder screws get
        doc = pairs[0][0][0].Document
        active = ui.active()
        if pairs[0][1] is None:
            p.SetString("ScrewPick", self.size.currentText())
            pick = library.index()[1][self.size.currentText()]
            put = ui.run("Place VEX screw", lambda: [(drop(doc, pairs[0][0], pick, active), None, [])])
        else:
            p.SetString("Nut", self.nut.currentText())
            p.SetBool("Fill", self.fill.isChecked())
            p.SetBool("ScrewAuto", self.auto.isChecked())
            family = KINDS[self.kind.currentText()]
            nut = None if self.nut.currentText() == NO_NUT else nuts()[self.nut.currentText()]
            od = spacers.od_from(self.od) if self.fill.isChecked() else None
            put = ui.run("Place VEX screw", lambda: [fasten(doc, h, t, family, nut, active, od) for h, t in pairs])
        if not put:
            return None
        doc.recompute()
        extra = sum(len(x) for _, _, x in put)
        said = f"put in a {put[0][0].Label}" if len(put) == 1 else f"put in {len(put)} screws"
        return said + (f" + {extra} spacers and washers" if extra else "")


SCREW = ui.Command(Panel, "vex-screw.svg", "Screw",
                   "Click a hole on the head side, then the one on the nut side. Puts in the shortest screw that makes it through the nut, "
                   "or gets 3/8\" into a threaded hole (1/4\" if that's all there is). Pick a few holes on one face first and one click across does the lot. Or pick the screw yourself and place it with one click")
