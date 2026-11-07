# metal generator vs vex's steps, run with: python tests/test_metal.py (needs FreeCAD + vex-step/)
import itertools
import math
import re
import sys
import time
from pathlib import Path

import freecad  # noqa: F401  puts FreeCAD on the path
import Part
from FreeCAD import Rotation, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "freecad" / "vex_workbench"))

import catalog  # noqa: E402
import metal  # noqa: E402
from metal import IN  # noqa: E402

cat = catalog.load()
gen = {p["name"]: p for p in catalog.generated(cat)}
steps = {Path(p["file"]).stem: p for p in catalog.step_parts(cat)}

# vex's file is off, ours is the nominal one
OFF = {
    "1x5x1x25 Steel C-Channel (275-1138)": "web holes 0.24 from one side",
    "1x5x1x35 Steel C-Channel (275-1139)": "web holes 0.24 from one side",
}


def points(shape):
    # hole centers on flat faces, inches from the bbox corner
    b = shape.optimalBoundingBox()  # plain BoundBox is ~0.011 loose round the relief faces
    out = []
    for f in shape.Faces:
        if f.Surface.TypeId != "Part::GeomPlane":
            continue
        for w in f.Wires:
            if not w.isSame(f.OuterWire):
                c = w.BoundBox.Center
                out.append(((c.x - b.XMin) / IN, (c.y - b.YMin) / IN, (c.z - b.ZMin) / IN))
    return out, (b.XLength / IN, b.YLength / IN, b.ZLength / IN)


def key(pts):
    return {tuple(round(v * 200) for v in p) for p in pts}


def best(ours, theirs):
    # same holes under some axis swap / flip, fewest left over
    (a, asize), (b, bsize) = ours, theirs
    want = key(b)
    top = None
    for perm in itertools.permutations(range(3)):
        size = [asize[i] for i in perm]
        if any(abs(s - t) > 0.01 for s, t in zip(size, bsize)):
            continue
        for flip in itertools.product((False, True), repeat=3):
            moved = [tuple(size[j] - p[i] if f else p[i] for j, (i, f) in enumerate(zip(perm, flip))) for p in a]
            got = key(moved)
            miss = len(want - got) + len(got - want)
            if top is None or miss < top[0]:
                top = (miss, len(want - got), len(got - want))
    return top


bad = 0
for fam in cat["family"]:
    if fam["id"] not in metal.PROFILES:
        continue
    for fx in fam.get("fixtures", []):
        name = re.sub(r" \([\d-]+\)$", "", re.sub(r" \(6-pack\)", "", fx))
        part = gen.get(name) or gen.get(name + " (Regular)")
        step = steps[fx]
        t0 = time.time()
        ours = metal.make(part, cat)
        ms = (time.time() - t0) * 1000
        theirs = Part.read(str(catalog.step_path(step)))
        po, pt = points(ours), points(theirs)
        size = sorted(round(x, 3) for x in po[1])
        vol = ours.Volume / theirs.Volume - 1
        m = best(po, pt)
        holes = "no orientation fits" if m is None else f"holes off {m[1]} missing / {m[2]} extra"
        # vex's reliefs are all a bit *dih*frent from ours, c-channels most (+0.13% on the 2x steel one). the rest come in under 0.03%, so a lost notch shows
        tol = 0.002 if "C-Channel" in fx else 0.0005
        ok = m is not None and m[0] == 0 and abs(vol) < tol and ours.isValid()
        note = ""
        if not ok and fx in OFF:
            note, ok = f" (known: {OFF[fx]})", True
        if not ok and "Aluminum C-Channel" in fx:
            # al c-channel steps are their own shape (0.55 tall, flange holes 0.3, the 5x flares), ours is the steel layout
            note, ok = " (info, al step)", True
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {fx}: {size} vol {vol * 100:+.2f}% {holes}, {ms:.0f} ms{note}")

# the cut 1x1 angles have no step, theyre half a 1x3x1 c-channel. two between-holes halves + the middle strip and its 10 holes = the channel
g = cat["grid"]
ch, half, edge = (metal.make(gen[n], cat) for n in ("1x3x1x10 Aluminum C-Channel", "1x1x10 Aluminum Angle (Cut 3x, Between Holes)", "1x1x10 Aluminum Angle (Cut 3x, Hole Edge)"))
hole = g["hole"] ** 2 - (4 - math.pi) * g["round"] ** 2
strip = (g["pitch"] * 10 * g["pitch"] - 10 * hole) * cat["metal"]["thickness"]["Aluminum"] * IN**3
off = (2 * half.Volume + strip) / ch.Volume - 1
b = edge.optimalBoundingBox()
ok = abs(off) < 1e-6 and abs(b.ZLength / IN - 0.659) < 1e-6 and half.isValid() and edge.isValid()
bad += not ok
print(f"{'ok ' if ok else 'BAD'} cut 1x1 angles: 2 halves + strip vs the 1x3x1 channel {off * 100:+.5f}%, hole edge one {b.ZLength / IN:.3f} across")

# a bend line 0.03 short of a hole, the hole starts inside the bend and stays open round it
plate = metal.make(gen["5x10 Steel Plate"], cat)
t = cat["metal"]["thickness"]["Steel"] * IN
fold = {"do": "fold", "p": [2.371 * IN, 0.25 * IN, t], "d": [0, 1, 0], "n": [0, 0, 1], "side": 1, "t": t, "angle": 90, "r": 0.032 * IN, "k": 0.44}
p, u, n, w, at, axis, deg = metal.hinge(fold)


def wrapped(q, s):
    # q moved s mm past the line and round the bend
    return Rotation(axis, deg * s / w).multVec(q - u * u.dot(q - p) - at) + at


bent = metal.fold(plate, fold)
mid = Vector(2.25, 0.25, 0.023) * IN  # middle of the wall
s = u.dot(mid - p) - 0.091 * IN  # where the hole starts, past the line
inside = wrapped(mid, (s + w) / 2)  # halfway from there to the end of the bend
ok = 0 < s < w and bent.isValid() and len(bent.Solids) == 1 and not bent.isInside(inside, 1e-6, True)
bad += not ok
print(f"{'ok ' if ok else 'BAD'} bend next to a hole: starts {s:.2f} of {w:.2f} mm into the bend, open there {not bent.isInside(inside, 1e-6, True)}")

# a 1 mm round one drilled 0.5 to 1.5 mm into the same bend, open just past its near side and solid beside its far side
c = Vector(2.371 * IN - 1, 0.5 * IN, t)
drilled = metal.fold(metal.drill(plate, {"do": "drill", "c": list(c), "n": [0, 0, 1], "dia": 1, "t": t}), fold)
mid = c - n * (t / 2)
side = mid + n.cross(u) * 0.4
ok = drilled.isValid() and len(drilled.Solids) == 1 and not drilled.isInside(wrapped(mid, 0.6), 1e-6, True) and drilled.isInside(wrapped(side, 1.4), 1e-6, True)
bad += not ok
print(f"{'ok ' if ok else 'BAD'} bend through a round hole: open at its near side {not drilled.isInside(wrapped(mid, 0.6), 1e-6, True)}, solid beside its far side {drilled.isInside(wrapped(side, 1.4), 1e-6, True)}")

print("all good" if not bad else f"{bad} bad")
sys.exit(1 if bad else 0)
