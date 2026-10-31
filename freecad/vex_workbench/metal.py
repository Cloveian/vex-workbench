# channels, angles, plate, bar: flat legs with their holes cut in 2D, bends between, all along x
import math

import Part
from FreeCAD import Matrix, Placement, Rotation, Vector

IN = 25.4
X = Vector(1, 0, 0)
EPS = 0.01  # cutters poke out this far each side


def yz(y, z):
    return Vector(0, y, z)


def frames(pts):
    # leg directions + inward normals (toward the material), every bend turns the same way
    d = [(b - a).normalize() for a, b in zip(pts, pts[1:])]
    turn = 1 if len(d) < 2 or d[0].cross(d[1]).x > 0 else -1
    return d, [X.cross(e) * turn for e in d]


def bend(pts, d, n, j, t, r):
    # slice of the bend at outside corner pts[j], r = inside radius. the legs either side are flat pieces of their own
    ro, q, din, dout = r + t, pts[j], d[j - 1], d[j]
    c, mid = q - din * ro + dout * ro, (din - dout).normalize()
    a, b = q - din * ro, q + dout * ro
    return Part.Face(Part.Wire([
        Part.Arc(a, c + mid * ro, b).toShape(),
        Part.LineSegment(b, b + n[j] * t).toShape(),
        Part.Arc(b + n[j] * t, c + mid * r, a + n[j - 1] * t).toShape(),
        Part.LineSegment(a + n[j - 1] * t, a).toShape()]))


def square(size, r):
    h = size / 2 - r
    f = Part.Face(Part.makePolygon([Vector(-h, -h, 0), Vector(h, -h, 0), Vector(h, h, 0), Vector(-h, h, 0), Vector(-h, -h, 0)]))
    return f.makeOffset2D(r, 0) if r > 0 else f


def diamond(h, r=0):
    # h = half diaganal, how deep it notches an edge. r rounds the two y points, the notch bottoms
    if not r:
        return Part.Face(Part.makePolygon([Vector(h, 0, 0), Vector(0, h, 0), Vector(-h, 0, 0), Vector(0, -h, 0), Vector(h, 0, 0)]))
    a, b = r / 2**0.5, r * (2**0.5 - 1)  # tangant points, and how much the tip pulls in
    tip, edges = Vector(h, 0, 0), []
    for s in (1, -1):
        p, m, q = Vector(s * a, s * (h - a), 0), Vector(0, s * (h - b), 0), Vector(-s * a, s * (h - a), 0)
        edges += [Part.LineSegment(tip * s, p).toShape(), Part.Arc(p, m, q).toShape(), Part.LineSegment(q, tip * -s).toShape()]
    return Part.Face(Part.Wire(edges))


def place(tool, origin, d, n):
    # tool x -> along, y -> across the leg, z -> through it
    # copy first, the fuse after is ~2x slower with the Placement set straight on the tool
    c = tool.copy()
    c.Placement = Placement(Matrix(1, d.x, n.x, origin.x, 0, d.y, n.y, origin.y, 0, d.z, n.z, origin.z, 0, 0, 0, 1)).multiply(tool.Placement)
    return c


def reliefs(pts, d, t, r, xs, half, k):
    # flat pattern diamond (half diagonal `half`) wrapped round every bend at each x
    # -> lofts per bend, and the triangles it leaves on the legs as (leg, 2D cutter)
    ro, rn = r + t, r + k * t
    edge = half - rn * math.pi / 4  # half width where bend meets leg, also how far it runs onto the leg
    reach = (ro + EPS) / math.cos(math.radians(7.5))  # chords cut short of the outside without the 1/cos
    back = Part.Face(Part.makePolygon([Vector(-edge, 0, 0), Vector(edge, 0, 0), Vector(0, -edge, 0), Vector(-edge, 0, 0)]))
    on = back.mirror(Vector(0, 0, 0), Vector(0, 1, 0))
    lofts, tris = [], []
    for j in range(1, len(pts) - 1):
        q, din, dout = pts[j], d[j - 1], d[j]
        c = q - din * ro + dout * ro
        # ruled loft of radial rectangels every 15 deg, at x = 0
        rings = []
        for i in range(7):
            s = i / 6  # 0 = incomming leg, 1 = outgoing
            u = dout * -math.cos(s * math.pi / 2) + din * math.sin(s * math.pi / 2)
            a = half - rn * abs(s - 0.5) * math.pi / 2
            p = [c + u * (r - EPS) - X * a, c + u * reach - X * a, c + u * reach + X * a, c + u * (r - EPS) + X * a]
            rings.append(Part.makePolygon(p + p[:1]))
        loft = Part.makeLoft(rings, True, True)
        lofts.append([loft.translated(X * x) for x in xs])
        for x in xs:
            tris.append((j - 1, back.translated(Vector(x, (q - pts[j - 1]).Length - ro, 0))))
            tris.append((j, on.translated(Vector(x, ro, 0))))
    return lofts, tris


# --- profiles ---
# each gives the outside corners and, per leg, where the holes go across it (from the leg start)
# between = the staggered rows, half a pitch along


def rows(size, p, g):
    # hole rows counted from the outside of a bend
    b = p.get("past_bend", g["past_bend"])
    far = [b + g["pitch"] * i for i in range(size)]
    mid = [b + g["pitch"] * (i + 0.5) for i in range(size - 1)] if p.get("between") else []
    return far, mid


def c_channel(p, g):
    h, w = p["flange"], p["width"] * g["pitch"]
    pts = [yz(0, 0), yz(h, 0), yz(h, w), yz(0, w)]
    web = [g["end"] + g["pitch"] * i for i in range(p["width"])]
    mid = [g["pitch"] * (i + 1) for i in range(p["width"] - 1)] if p.get("between") else []
    flange, _ = rows(1, p, g)
    return pts, [([h - x for x in flange], []), (web, mid), (flange, [])]


def angle(size):
    def profile(p, g):
        if "web" in p:
            # cut out of a 3x c-channel, web runs up to the cut
            h = p["flange"]
            flange, _ = rows(1, p, g)
            return [yz(0, 0), yz(h, 0), yz(h, p["web"])], [([h - x for x in flange], []), ([g["end"]], [])]
        a = size * g["pitch"]
        pts = [yz(0, 0), yz(a, 0), yz(a, a)]
        far, mid = rows(size, p, g)
        return pts, [([a - x for x in far], [a - x for x in mid]), (far, mid)]
    return profile


def u_channel(p, g):
    # web rows from one bend too, so a hair off center
    h = p["flange"]
    pts = [yz(0, 0), yz(h, 0), yz(h, p["web"]), yz(0, p["web"])]
    far, mid = rows(2, p, g)
    return pts, [([h - x for x in far], [h - x for x in mid]), (far, mid), (far, mid)]


def flat(size):
    def profile(p, g):
        pts = [yz(0, 0), yz(size * g["pitch"], 0)]
        return pts, [([g["end"] + g["pitch"] * i for i in range(size)], [])]
    return profile


PROFILES = {
    "c-channel": c_channel,
    "u-channel": u_channel,
    "angle-1x1": angle(1),
    "angle-2x2": angle(2),
    "angle-3x3": angle(3),
    "plate-5x": flat(5),
    "bar-1x": flat(1),
}


def make(part, cat):
    p, g, metal = part["params"], cat["grid"], cat["metal"]
    sawn = p.get("cut", {}).get(p.get("variant"))
    if sawn:
        p = {**p, **sawn}
    elif p.get("variant", "Regular") != "Regular":
        raise ValueError(f"no dims for {p['variant']} angles yet")
    mat = p["material"]
    t = p.get("thickness", {}).get(mat, metal["thickness"][mat])
    pts, legs = PROFILES[part["family"]](p, g)
    d, n = frames(pts)
    length = p["holes"] * g["pitch"]
    r, last = metal["bend"], len(legs) - 1
    lens = [(b - a).Length for a, b in zip(pts, pts[1:])]
    # every leg is cut flat in 2D, x along the length and y across from the leg start, then pushed through t
    # 2.1 s for a 1x5x1x35, mostly the relief cuts in the bends and the fuse
    cuts = [[] for _ in legs]
    hole = square(g["hole"], p.get("round", g["round"]))
    for k, (main, between) in enumerate(legs):
        spots = [(a, g["end"] + g["pitch"] * i) for a in main for i in range(p["holes"])]
        spots += [(a, g["pitch"] * (i + 1)) for a in between for i in range(p["holes"] - 1)]
        cuts[k] += [hole.translated(Vector(x, a, 0)) for a, x in spots]
    if "diamond" in p:
        # every grid point, edges included. the corner chamfers at the ends stay sharp
        h = p["diamond"] / 2**0.5
        sharp, dia = diamond(h), diamond(h, p.get("root", 0))
        width = round(lens[0] / g["pitch"])
        cuts[0] += [(dia if 0 < i < p["holes"] else sharp).translated(Vector(g["pitch"] * i, g["pitch"] * j, 0))
                    for i in range(p["holes"] + 1) for j in range(width + 1)]
    bends = []
    if last:
        # count marks + end chamfers on the free edges of the first and last leg
        notch, cham = diamond(metal["mark"]), diamond(p["chamfer"])
        every = metal["marks"] * g["pitch"]
        xs = [every * i for i in range(1, int(length / every - 1e-6) + 1)]
        # a sawn edge has neither
        for k, a in [(0, 0)] + ([] if sawn else [(last, lens[-1])]):
            cuts[k] += [notch.translated(Vector(x, a, 0)) for x in xs]
            cuts[k] += [cham.translated(Vector(x, a, 0)) for x in (0, length)]
        lofts, tris = reliefs(pts, d, t, r, xs, metal["relief"], metal["k"])
        for k, f in tris:
            cuts[k].append(f)
        for j, mine in enumerate(lofts, 1):
            b = bend(pts, d, n, j, t, r).extrude(X * length)
            bends.append(b.cut(mine) if mine else b)  # 5 long or less has no marks, so no reliefs
    pieces = []
    for k, cut in enumerate(cuts):
        # flat part of the leg only, the bends have the rest
        a0, a1 = (r + t if k else 0), lens[k] - (r + t if k < last else 0)
        f = Part.Face(Part.makePolygon([Vector(0, a0, 0), Vector(length, a0, 0), Vector(length, a1, 0), Vector(0, a1, 0), Vector(0, a0, 0)]))
        # only what crosses an edge needs a boolean, the rest go in as plain inner wires
        inside, edge = [], []
        for c in cut:
            b = c.BoundBox
            (inside if b.XMin > 1e-6 and b.XMax < length - 1e-6 and b.YMin > a0 + 1e-6 and b.YMax < a1 - 1e-6 else edge).append(c)
        if edge:
            f = f.cut(edge).Faces[0]
        f.cutHoles([c.OuterWire.reversed() for c in inside])
        pieces.append(place(f.extrude(Vector(0, 0, t)), pts[k], d[k], n[k]))
    # fuse splits the end faces at every seam, removeSplitter puts them back to one like vex
    solid = pieces[0].fuse(pieces[1:] + bends).removeSplitter() if last else pieces[0]
    solid.scale(IN)
    return solid


# --- bending a made part ---
BIG = 1e4  # mm, a box this big is a half space


def half(at, u, n, lo):
    # everything at least lo mm past at along u
    v = n.cross(u)
    box = Part.makeBox(BIG, BIG, BIG)
    box.Placement = Placement(at + u * lo - v * BIG / 2 - n * BIG / 2, Rotation(u, v, n, "ZXY"))
    return box


def fold(shape, b):
    # shape folded once by a bend dict, mm in its own coords
    if abs(b["angle"]) < 1e-6:
        return shape
    p, d, n = (Vector(*b[key]) for key in ("p", "d", "n"))  # line through p along d, on the face out along n
    u = n.cross(d) * b["side"]  # into the side that turns
    a = math.radians(abs(b["angle"]))
    w = (b["r"] + b["k"] * b["t"]) * a  # flat length the bend eats, on the netural line. r inside radius, t wall
    keep = shape.cut(half(p, u, n, 0))
    turns = shape.common(half(p, u, n, 0))
    rest = turns.common(half(p, u, n, w))
    # cross section on the line, swept round. a hole the line goes through leaves a gap in it, so it stays open round the bend
    section = [f for f in turns.Faces if f.Surface.TypeId == "Part::GeomPlane" and abs(abs(f.normalAt(0, 0).dot(u)) - 1) < 1e-6
               and abs(u.dot(f.CenterOfMass - p)) < 1e-6]
    if not section or not keep.Solids:
        raise ValueError("nothing to bend there, the line has to go across the metal with some on both sides")
    up = 1 if b["angle"] > 0 else -1
    # inside radius off the clicked face folding toward it, off the far face folding away
    at = p + n * b["r"] if up > 0 else p - n * (b["t"] + b["r"])
    # a channel's flanges reach past the axis folding the web toward them, the sweep turns inside out
    reach = [up * n.dot(v.Point - at) for f in section for v in f.Vertexes]
    if max(reach) > 1e-6:
        raise ValueError("that would fold it through itself, a flange or another wall is in the way. try the other way, or cut it off first")
    axis, deg = u.cross(n), math.degrees(a) * up
    pieces = [Part.makeCompound(section).revolve(at, axis, deg)]
    if rest.Solids:
        rest.translate(-u * w)
        rest.rotate(at, axis, deg)
        pieces.append(rest)
    out = keep.fuse(pieces).removeSplitter()
    # anything else that collapes comes back as nothing or a sliver, still isValid
    if len(out.Solids) != 1 or not 0.8 < out.Volume / shape.Volume < 1.5:
        raise ValueError("that bend came out broken, try it a little different")
    return out
