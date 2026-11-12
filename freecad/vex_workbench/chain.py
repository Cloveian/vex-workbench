# chain tool. click round the sprocket bores, links go on a pitch apart along the tangent lines and arcs round them. 2d in the sprockets plane, points are complex numbers
import cmath
import math

import FreeCAD as App
import Part
from FreeCAD import Placement, Rotation, Vector
from PySide import QtCore, QtWidgets

from . import catalog, library, snap, ui
from .metal import IN

TOL = 1e-9
OFF_PLANE = 0.02 * IN  # mm, teeth middles this far apart along the axis still take one chain


def pitch_radius(teeth, pitch):
    # pins sit on this circle, a chord of pitch per tooth
    return pitch / (2 * math.sin(math.pi / teeth))


def tangent(c1, r1, c2, r2):
    # line leaving wheel 1 and arriving at wheel 2. r signde, + = center on the left of travel (chain goes round it ccw)
    d = c2 - c1
    L = abs(d)
    if abs(r2 - r1) >= L:
        raise ValueError("those sprockets overlap, the chain can't get between them")
    c = (r2 - r1) / L
    u = d / L
    n = u * complex(c, math.sqrt(1 - c * c))  # left of travel, n.d = r2 - r1
    return c1 - r1 * n, c2 - r2 * n


def loop(wheels):
    # wheels = [(center, r signed)] in the order the chain goes round. segments, each ("line", a, b) or ("arc", center, r, start angle, sweep signed)
    if len(wheels) < 2:
        raise ValueError("a chain needs two sprockets at least")
    lines = [tangent(*wheels[i], *wheels[(i + 1) % len(wheels)]) for i in range(len(wheels))]
    out = []
    for i, (c, r) in enumerate(wheels):
        come, go = lines[i - 1][1], lines[i][0]
        a0, a1 = cmath.phase(come - c), cmath.phase(go - c)
        sweep = math.copysign((a1 - a0) * math.copysign(1, r) % (2 * math.pi), r)
        out.append(("arc", c, abs(r), a0, sweep))
        out.append(("line", go, lines[i][1]))
    return out


def length(seg):
    return abs(seg[2] - seg[1]) if seg[0] == "line" else seg[2] * abs(seg[4])


def at(seg, s):
    if seg[0] == "line":
        a, b = seg[1], seg[2]
        return a + (b - a) * (s / abs(b - a))
    _, c, r, a0, sweep = seg
    return c + cmath.rect(r, a0 + math.copysign(s / r, sweep))


def walk(segs, s):
    # point s along the whole loop, wraps
    s %= sum(length(g) for g in segs)
    for g in segs:
        if s <= length(g):
            return at(g, s)
        s -= length(g)
    return at(segs[-1], length(segs[-1]))


def pins(segs, pitch):
    # pins a straight pitch apart from the start of the loop, and the gap the last link has back to the first. pitch = a perfect fit, under it = slack
    total = sum(length(g) for g in segs)
    s, out = 0.0, [walk(segs, 0)]
    while True:
        # chord is pitch somewhere past pitch of path (a line) and before pi/2 of it (an arc as tight as it gets)
        lo, hi = s + pitch, min(s + pitch * math.pi / 2, total)
        if lo >= total or abs(walk(segs, hi) - out[-1]) < pitch - TOL:
            break  # back round to the start before a hole link fits
        while hi - lo > TOL:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if abs(walk(segs, mid) - out[-1]) < pitch else (lo, mid)
        s = (lo + hi) / 2
        out.append(walk(segs, s))
    if len(out) > 1 and abs(out[-1] - out[0]) < 1e-6:
        out.pop()  # landed back on the first one
    return out, abs(out[0] - out[-1])


def frames(plane, pts):
    # a link on each pin, pin axis on x like chainlink makes them, +y to the next pin. plane = the sprockets plane, its z on their axis
    out = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        d = (b - a) / abs(b - a)
        x, y = Vector(0, 0, 1), Vector(d.real, d.imag, 0)
        out.append(plane.multiply(Placement(Vector(a.real, a.imag, 0), Rotation(x, y, x.cross(y), "XYZ"))))
    return out


def sprocket(s):
    # a clicked sprocket in world mm. at = teeth middle on the axis, tips = vertexes out past the pitch circle
    link, pt, plc, _ = s
    row = library.row(link)
    if not row or "Teeth" not in row:
        raise ValueError(f"{link.Label} isn't a sprocket")
    pitch = library.cat()["chain"][row["Chain"]]["pitch"] * IN
    teeth = int(row["Teeth"])
    r = pitch_radius(teeth, pitch)
    c, n = library.hole_at(link, pt)
    # teeth middle = middle of everything out past the tooth roots, along the axis. ~120 ms on the 32T 6P, 7612 vertexes
    out, tips = [], []
    for v in Part.getShape(link.LinkedObject).Vertexes:
        d = v.Point - c
        along = d.dot(n)
        far = (d - n * along).Length
        if far > r + pitch:
            raise ValueError(f"that's not the middle of {link.Label}, click its bore")
        if far > r - pitch / 2:
            out.append(along)
        if far > r:
            tips.append(plc.multVec(v.Point))
    if not out:
        raise ValueError(f"no teeth round that hole on {link.Label}")
    mid = c + n * ((min(out) + max(out)) / 2)
    return {"at": plc.multVec(mid), "axis": plc.Rotation.multVec(n), "teeth": teeth, "r": r, "chain": row["Chain"], "pitch": pitch,
            "tips": tips, "link": link, "plc": plc}


def lay(sprockets):
    # sprockets in the order the chain goes round -> the plane, (center, signed r) in it
    if len({w["chain"] for w in sprockets}) > 1:
        raise ValueError("those sprockets take different chain")
    z = sprockets[0]["axis"]
    plane = Placement(sprockets[0]["at"], Rotation(Vector(0, 0, 1), z))
    into = plane.inverse()
    flat = []
    for w in sprockets:
        q = into.multVec(w["at"])
        if w["axis"].cross(z).Length > 1e-3:
            raise ValueError("those sprockets aren't on parallel shafts")
        if abs(q.z) > OFF_PLANE:
            raise ValueError(f"those sprockets are {abs(q.z) / IN:.3f} in out of line")
        flat.append(complex(q.x, q.y))
    # a corner turning the way the whole loop does gets wrapped round the outisde, one turning back (an idler pushing in) on its inside
    k = len(flat)
    area = sum((flat[i].conjugate() * flat[(i + 1) % k]).imag for i in range(k))
    way = 1 if area >= 0 else -1
    out = []
    for i, w in enumerate(sprockets):
        turn = ((flat[i] - flat[i - 1]).conjugate() * (flat[(i + 1) % k] - flat[i])).imag
        out.append((flat[i], w["r"] * way * (1 if turn * way >= 0 else -1)))
    return plane, out


def from_middle(segs):
    # same loop starting halfway down the first run, where the odd last link goes
    _, a, b = segs[1]
    m = (a + b) / 2
    return [("line", m, b)] + segs[2:] + [segs[0], ("line", a, m)]


def phase(plane, center, w, pts):
    # deg to turn a sprocket so a tooth gap sits on its pins. e^(i teeth a) over the tips averages out to the tooth middles, the gaps are half a tooth on
    into = plane.inverse()
    acc = 0j
    for t in w["tips"]:
        q = into.multVec(t)
        z = complex(q.x, q.y) - center
        acc += (z / abs(z)) ** w["teeth"]
    gap = cmath.phase(acc) / w["teeth"] + math.pi / w["teeth"]
    on = next((p for p in pts if abs(abs(p - center) - w["r"]) < 1e-6 * IN), None)
    if on is None:
        return 0.0  # chain only touches it, nothing to sit in
    step = 2 * math.pi / w["teeth"]
    return math.degrees((cmath.phase(on - center) - gap + step / 2) % step - step / 2)


def put_on(doc, parent, sprockets, turn=True):
    # a link array round the sprockets, and what to say about the fit. turn = each sprocket turned on its shaft to sit in the chain
    plane, flat = lay(sprockets)
    kind, pitch = sprockets[0]["chain"], sprockets[0]["pitch"]
    pts, gap = pins(from_middle(loop(flat)), pitch)
    c = library.cat()["chain"][kind]
    _, gen, steps = library.index()
    part = gen.get(c["link"]) or next((p for p in steps.values() if p["name"] == c["link"] and catalog.has(p)), None)
    if part is None:
        raise ValueError(f"there's no {c['link']} to put on")
    own = Placement()  # the link's own coords -> chain frame
    if "pins" in c:
        x, y = Vector(*c["pins"]), Vector(*c["along"])
        own = Placement(Vector(*c["middle"]) * IN, Rotation(x, y, x.cross(y), "XYZ")).inverse()
    if turn:
        axis = plane.Rotation.multVec(Vector(0, 0, 1))
        for w, (center, _) in zip(sprockets, flat):
            spin = Placement(Vector(), Rotation(axis, phase(plane, center, w, pts)), w["at"])
            held = w["plc"].multiply(w["link"].Placement.inverse())  # whatever its in, world
            w["link"].Placement = held.inverse().multiply(spin).multiply(w["plc"])
    local = snap.inside(parent)[0]
    link = library.place(doc, part, parent)
    n = len(pts)
    link.ShowElement = False  # one row in the tree
    link.ElementCount = n
    link.PlacementList = [local.multiply(f).multiply(own) for f in frames(plane, pts)]
    if abs(gap - pitch) < 0.001 * IN:
        return link, f"{n} links, a perfect fit"
    return link, f"{n} links with {(pitch - gap) / IN:.3f} in slack, {n - 1} is {gap / IN:.3f} short"


class Panel(snap.Clicks):
    PROMPTS = ("click the bore of a sprocket", "now the next one round, or the first again to close the loop")

    def __init__(self):
        self.bores = []
        self.turn = QtWidgets.QCheckBox("Turn sprockets")
        self.turn.setToolTip("Turn each sprocket on its shaft so a tooth gap sits under every link on it")
        self.turn.setChecked(App.ParamGet(ui.PARAMS).GetBool("ChainTurn", True))
        self.turn.toggled.connect(lambda on: App.ParamGet(ui.PARAMS).SetBool("ChainTurn", on))
        super().__init__("VEX chain", [(self.turn,)])

    def ask(self, said=""):
        n = len(self.bores)
        self.status.setText(said + self.PROMPTS[n > 0] + (f" ({n} so far)" if n > 1 else ""))

    def take(self, s):
        parts = [b[0] for b in self.bores]
        if s[0] in parts[1:]:
            self.ask(f"{s[0].Label} is in already\n")
            return
        if parts and s[0] == parts[0]:
            if len(self.bores) < 2:
                self.ask("a chain needs two sprockets at least\n")
                return
            bores, self.bores = self.bores, []
            QtCore.QTimer.singleShot(0, lambda: self.done(bores, None))
            return
        self.bores.append(s)
        self.light(self.bores)
        self.ask()

    def act(self, spots, _):
        parent = ui.active()
        turn = self.turn.isChecked()
        got = ui.run("VEX chain", lambda: put_on(self.doc, parent, [sprocket(s) for s in spots], turn))
        if got is None:
            return None
        self.doc.recompute()
        return got[1]


CHAIN = ui.Command(Panel, "vex-chain.svg", "Chain", "Click the bore of each sprocket in the order the chain goes round, then the first again. Chain links all the way round")
