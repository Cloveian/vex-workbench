# chain round sprockets: the loop of tangent lines and arcs, pins a pitch apart along it. 2d in the sprockets plane, points are complex numbers
import cmath
import math

from FreeCAD import Placement, Rotation, Vector

TOL = 1e-9


def pitch_radius(teeth, pitch):
    # pins sit on this circle, a chord of pitch per tooth
    return pitch / (2 * math.sin(math.pi / teeth))


def tangent(c1, r1, c2, r2):
    # line leaving wheel 1 and arriving at wheel 2. r signde, + = center on the left of travel (chain goes round it ccw)
    d = c2 - c1
    L = abs(d)
    if abs(r2 - r1) >= L:
        raise ValueError("those sprockets overlap, the chain cant get between them")
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
