# chain loop, pins and link frames, run with: python tests/test_chain.py (needs FreeCAD)
import cmath
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401
freecad.__path__.insert(0, str(ROOT / "freecad"))
from FreeCAD import Placement, Rotation, Vector  # noqa: E402

from freecad.vex_workbench import catalog, chain  # noqa: E402

P = catalog.load()["chain"]["6P"]


def joined(segs):
    # every segment starts where the last one ended
    ends = [chain.at(g, chain.length(g)) for g in segs]
    starts = [chain.at(g, 0) for g in segs]
    return max(abs(e - s) for e, s in zip(ends, starts[1:] + starts[:1]))


def links(pts):
    return [abs(b - a) for a, b in zip(pts, pts[1:])]


# 4 teeth on the pitch circle are a square
r = chain.pitch_radius(4, P)
assert abs(r - P / math.sqrt(2)) < 1e-12, r

# two 24T 4in apart, 16 pitches: each half wrap is 12 chords, so 24 + 2 * 16 pins, no slack
r = chain.pitch_radius(24, P)
segs = chain.loop([(0j, r), (4 + 0j, r)])
assert joined(segs) < 1e-12
pins, gap = chain.pins(segs, P)
assert len(pins) == 56 and abs(gap - P) < 1e-6, (len(pins), gap)
assert max(abs(d - P) for d in links(pins)) < 1e-6

# 12T onto a 36T, the loop is the textbook open belt length
r1, r2, D = chain.pitch_radius(12, P), chain.pitch_radius(36, P), 5.3
segs = chain.loop([(0j, r1), (D + 0j, r2)])
phi = math.asin((r2 - r1) / D)
belt = 2 * math.sqrt(D * D - (r2 - r1) ** 2) + r1 * (math.pi - 2 * phi) + r2 * (math.pi + 2 * phi)
got = sum(chain.length(g) for g in segs)
assert joined(segs) < 1e-12 and abs(got - belt) < 1e-12, (got, belt)
pins, gap = chain.pins(segs, P)
assert len(pins) == 68 and abs(gap - 0.0232026) < 1e-6 and max(abs(d - P) for d in links(pins)) < 1e-6, (len(pins), gap)  # 67 links 0.023 short of closing
# on a wheel the pins are on its pitch circle, lines are tangent there
on = [p for p in pins if abs(abs(p) - r1) < 1e-6 or abs(abs(p - D) - r2) < 1e-6]
assert len(on) > 12, len(on)

# an idler pushing in from outside, chain goes round it the other way (r < 0)
segs = chain.loop([(0j, r2), (6 + 0j, r1), (3 + 1.2j, -r1)])
assert joined(segs) < 1e-9
pins, gap = chain.pins(segs, P)
assert max(abs(d - P) for d in links(pins)) < 1e-6 and 0 < gap <= P + 1e-6

# link frames in a tipped plane, each link's next pin lands on the next link, x along the sprocket axis
plane = Placement(Vector(1, 2, 3), Rotation(Vector(1, 1, 0), 40))
f = chain.frames(plane, pins)
z = plane.Rotation.multVec(Vector(0, 0, 1))
for i, (a, b) in enumerate(zip(f, f[1:])):
    assert (a.multVec(Vector(0, P, 0)) - b.Base).Length < 1e-6, i
    assert (a.Rotation.multVec(Vector(1, 0, 0)) - z).Length < 1e-9, i
assert (f[0].Base - plane.multVec(Vector(pins[0].real, pins[0].imag, 0))).Length < 1e-12

# from_middle is the same loop, starting halfway down the first run
segs = chain.loop([(0j, r1), (D + 0j, r2)])
mid = chain.from_middle(segs)
assert joined(mid) < 1e-12 and abs(sum(map(chain.length, mid)) - belt) < 1e-12
assert abs(chain.at(mid[0], 0) - (chain.at(segs[1], 0) + chain.at(segs[1], chain.length(segs[1]))) / 2) < 1e-12

# 12 teeth with their middles at 0.1 rad + k * 30 deg, tips 0.05 either side. gaps are at 0.1 + 15 deg, a pin at 0.3 rad wants it turned 0.3 - that
r = chain.pitch_radius(12, P)
step = 2 * math.pi / 12
tips = [Vector(1.1 * r * math.cos(a), 1.1 * r * math.sin(a), 0) for k in range(12) for a in (0.1 + k * step - 0.05, 0.1 + k * step + 0.05)]
turn = chain.phase(Placement(), 0j, {"tips": tips, "teeth": 12, "r": r}, [r * cmath.exp(0.3j)])
assert abs(math.radians(turn) - (0.3 - 0.1 - step / 2)) < 1e-9, turn

for bad in ([(0j, r2)], [(0j, r2), (0.5 + 0j, -r2)], [(0j, r1), (0j, r1)]):
    try:
        chain.loop(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)

print("ok")
