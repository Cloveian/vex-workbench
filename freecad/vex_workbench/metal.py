# channels, angles, plate, bar: one bent section stretched along x, holes cut through each flat leg
import math

import Part
from FreeCAD import Matrix, Placement, Vector

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


def section(pts, d, n, t, r):
    # pts = outside corners, r = inside bend radius
    ro, edges = r + t, []

    def line(a, b):
        edges.append(Part.LineSegment(a, b).toShape())

    def arc(a, m, b):
        edges.append(Part.Arc(a, m, b).toShape())

    cur = pts[0]
    for k in range(1, len(pts) - 1):
        q, din, dout = pts[k], d[k - 1], d[k]
        c, mid = q - din * ro + dout * ro, (din - dout).normalize()
        line(cur, q - din * ro)
        arc(q - din * ro, c + mid * ro, q + dout * ro)
        cur = q + dout * ro
    line(cur, pts[-1])
    cur = pts[-1] + n[-1] * t
    line(pts[-1], cur)
    for k in range(len(pts) - 2, 0, -1):
        q, din, dout = pts[k], d[k - 1], d[k]
        c, mid = q - din * ro + dout * ro, (din - dout).normalize()
        line(cur, q + dout * ro + n[k] * t)
        arc(q + dout * ro + n[k] * t, c + mid * r, q - din * ro + n[k - 1] * t)
        cur = q - din * ro + n[k - 1] * t
    line(cur, pts[0] + n[0] * t)
    line(pts[0] + n[0] * t, pts[0])
    return Part.Face(Part.Wire(edges))


def prism(face, t):
    # face in xy, pushed through t along z
    return face.extrude(Vector(0, 0, t + 2 * EPS)).translated(Vector(0, 0, -EPS))


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
    c = tool.copy()
    # on top of tool.Placement, translated() keeps its shift there
    c.Placement = Placement(Matrix(1, d.x, n.x, origin.x, 0, d.y, n.y, origin.y, 0, d.z, n.z, origin.z, 0, 0, 0, 1)).multiply(tool.Placement)
    return c


def reliefs(pts, d, n, t, r, xs, half, k):
    # flat pattern diamond (half diagonal `half`) wrapped round every bend at each x
    ro, rn = r + t, r + k * t
    edge = half - rn * math.pi / 4  # half width where bend meets leg, also how far it runs onto the leg
    reach = (ro + EPS) / math.cos(math.radians(7.5))  # chords cut short of the outside without the 1/cos
    tri = Part.Face(Part.makePolygon([Vector(-edge, 0, 0), Vector(edge, 0, 0), Vector(0, -edge, 0), Vector(-edge, 0, 0)]))
    back, on = prism(tri, t), prism(tri.mirror(Vector(0, 0, 0), Vector(0, 1, 0)), t)
    out = []
    for j in range(1, len(pts) - 1):
        q, din, dout = pts[j], d[j - 1], d[j]
        c = q - din * ro + dout * ro
        for x in xs:
            # ruled loft of radial rectangles every 15 deg
            rings = []
            for i in range(7):
                s = i / 6  # 0 = incoming leg, 1 = outgoing
                u = dout * -math.cos(s * math.pi / 2) + din * math.sin(s * math.pi / 2)
                a = half - rn * abs(s - 0.5) * math.pi / 2
                p = [c + u * (r - EPS) + X * (x - a), c + u * reach + X * (x - a), c + u * reach + X * (x + a), c + u * (r - EPS) + X * (x + a)]
                rings.append(Part.makePolygon(p + p[:1]))
            out.append(Part.makeLoft(rings, True, True))
            out.append(place(back, q - din * ro + X * x, din, n[j - 1]))
            out.append(place(on, q + dout * ro + X * x, dout, n[j]))
    return out


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
    if p.get("variant", "Regular") != "Regular":
        raise ValueError(f"no dims for {p['variant']} angles yet")
    mat = p["material"]
    t = p.get("thickness", {}).get(mat, metal["thickness"][mat])
    pts, legs = PROFILES[part["family"]](p, g)
    d, n = frames(pts)
    length = p["holes"] * g["pitch"]
    solid = section(pts, d, n, t, metal["bend"]).extrude(X * length)

    hole = prism(square(g["hole"], p.get("round", g["round"])), t)
    cutters = []
    for k, (main, between) in enumerate(legs):
        spots = [(a, g["end"] + g["pitch"] * i) for a in main for i in range(p["holes"])]
        spots += [(a, g["pitch"] * (i + 1)) for a in between for i in range(p["holes"] - 1)]
        cutters += [place(hole, pts[k] + d[k] * a + X * x, d[k], n[k]) for a, x in spots]
    if "diamond" in p:
        # every grid point, edges included. the corner chamfers at the ends stay sharp
        h = p["diamond"] / 2**0.5
        sharp, dia = prism(diamond(h), t), prism(diamond(h, p.get("root", 0)), t)
        width = round((pts[1] - pts[0]).Length / g["pitch"])
        cutters += [place(dia if 0 < i < p["holes"] else sharp, pts[0] + d[0] * (g["pitch"] * j) + X * (g["pitch"] * i), d[0], n[0])
                    for i in range(p["holes"] + 1) for j in range(width + 1)]
    if len(pts) > 2:
        # count marks + end chamfers on the free edges of the first and last leg
        notch, cham = prism(diamond(metal["mark"]), t), prism(diamond(p["chamfer"]), t)
        every = metal["marks"] * g["pitch"]
        xs = [every * i for i in range(1, int(length / every - 1e-6) + 1)]
        for tip, k in [(pts[0], 0), (pts[-1], -1)]:
            cutters += [place(notch, tip + X * x, d[k], n[k]) for x in xs]
            cutters += [place(cham, tip + X * x, d[k], n[k]) for x in (0, length)]
        cutters += reliefs(pts, d, n, t, metal["bend"], xs, metal["relief"], metal["k"])
    solid = solid.cut(cutters)
    solid.scale(IN)
    return solid
