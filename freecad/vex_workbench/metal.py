# channels, angles, plate, bar: one bent section stretched along x, holes cut through each flat leg
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


def diamond(h):
    # h = half diaganal, how deep it notches an edge
    return Part.Face(Part.makePolygon([Vector(h, 0, 0), Vector(0, h, 0), Vector(-h, 0, 0), Vector(0, -h, 0), Vector(h, 0, 0)]))


def place(tool, origin, d, n):
    # tool x -> along, y -> across the leg, z -> through it
    c = tool.copy()
    # on top of tool.Placement, translated() keeps its shift there
    c.Placement = Placement(Matrix(1, d.x, n.x, origin.x, 0, d.y, n.y, origin.y, 0, d.z, n.z, origin.z, 0, 0, 0, 1)).multiply(tool.Placement)
    return c


# --- profiles ---
# each gives the outside corners and, per leg, where the holes go across it (from the leg start)
# between = the staggered rows, half a pitch along


def c_channel(p, g):
    h, w = p["flange"], p["width"] * g["pitch"]
    pts = [yz(0, 0), yz(h, 0), yz(h, w), yz(0, w)]
    web = [g["end"] + g["pitch"] * i for i in range(p["width"])]
    mid = [g["pitch"] * (i + 1) for i in range(p["width"] - 1)] if p.get("between") else []
    return pts, [([h - g["past_bend"]], []), (web, mid), ([g["past_bend"]], [])]


def angle(size):
    def profile(p, g):
        a = size * g["pitch"]
        pts = [yz(0, 0), yz(a, 0), yz(a, a)]
        far = [g["past_bend"] + g["pitch"] * i for i in range(size)]
        mid = [g["past_bend"] + g["pitch"] * (i + 0.5) for i in range(size - 1)] if p.get("between") else []
        return pts, [([a - x for x in far], [a - x for x in mid]), (far, mid)]
    return profile


def flat(size):
    def profile(p, g):
        pts = [yz(0, 0), yz(size * g["pitch"], 0)]
        return pts, [([g["end"] + g["pitch"] * i for i in range(size)], [])]
    return profile


PROFILES = {
    "c-channel": c_channel,
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
        # every grid point, edges included
        dia = prism(diamond(p["diamond"] / 2**0.5), t)
        width = round((pts[1] - pts[0]).Length / g["pitch"])
        cutters += [place(dia, pts[0] + d[0] * (g["pitch"] * j) + X * (g["pitch"] * i), d[0], n[0])
                    for i in range(p["holes"] + 1) for j in range(width + 1)]
    if len(pts) > 2:
        # count marks + end chamfers on the free edges of the first and last leg
        notch, cham = prism(diamond(metal["mark"]), t), prism(diamond(p["chamfer"]), t)
        every = metal["marks"] * g["pitch"]
        xs = [every * i for i in range(1, int(length / every - 1e-6) + 1)]
        for tip, k in [(pts[0], 0), (pts[-1], -1)]:
            cutters += [place(notch, tip + X * x, d[k], n[k]) for x in xs]
            cutters += [place(cham, tip + X * x, d[k], n[k]) for x in (0, length)]
    # todo bend reliefs at the count marks. flat pattern diamond on the inside surface, 0.0898 across the bend x 0.0798 along, wraped round the bend (helicoid sides)
    solid = solid.cut(cutters)
    solid.scale(IN)
    return solid
