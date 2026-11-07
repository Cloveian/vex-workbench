# usage: python -I tools/read_f3d.py <in.f3d> <out.step>
#   pulls the acis breps (binary sab, the .smbs in the zip) out of a fusion .f3d and writes them as one step in mm
#   surfaces: plane, cone, sphere, torus (lemon/apple too), splines off their stored b-spline. curves: lines, circles/ellipses, intcurves the same way
#   tolerant edges/coedges/vertices and voids are fine
#   splines with no stored b-spline and anything else stop with an error

import math
import struct
import sys
import zipfile
from collections import Counter

import freecad  # noqa: F401
import FreeCAD as App
import Part

SURFACES = ("plane-surface", "cone-surface", "sphere-surface", "torus-surface", "spline-surface")
CURVES = ("straight-curve", "ellipse-curve", "intcurve-curve")
IN = 25.4


# assemblies have one .smb per component, each lands at its own origin (placements arent read)
def read_smb(path):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith(".smb")]
        if not names:
            sys.exit(f"{path}: no .smb breps in there")
        return [(n.rsplit("/", 1)[-1], z.read(n)) for n in names]


def read_value(b, pos):
    t = b[pos]
    pos += 1
    if t == 0x04 or t == 0x0c or t == 0x15:  # int, pointer, enum
        return t, struct.unpack_from("<i", b, pos)[0], pos + 4
    if t == 0x06 or t == 0x17:
        return t, struct.unpack_from("<d", b, pos)[0], pos + 8
    if t == 0x07 or t == 0x0d or t == 0x0e:
        n = b[pos]
        return t, b[pos + 1:pos + 1 + n].decode("latin1"), pos + 1 + n
    if t == 0x08:
        n = struct.unpack_from("<H", b, pos)[0]
        return t, b[pos + 2:pos + 2 + n].decode("latin1"), pos + 2 + n
    if t == 0x09 or t == 0x12:
        n = struct.unpack_from("<I", b, pos)[0]
        return t, b[pos + 4:pos + 4 + n].decode("latin1"), pos + 4 + n
    if t == 0x0a or t == 0x0b:
        return t, t == 0x0a, pos
    if t == 0x0f or t == 0x10:
        return t, "{" if t == 0x0f else "}", pos
    if t == 0x11:
        return t, None, pos
    if t == 0x13 or t == 0x14:  # position, direction
        return t, struct.unpack_from("<3d", b, pos), pos + 24
    if t == 0x16:
        return t, struct.unpack_from("<2d", b, pos), pos + 16
    sys.exit(f"unknown sab tag 0x{t:02x} at byte {pos - 1}")


# 0x0e is a name piece that keeps going ("cone" "surface" -> cone-surface), 0x0d ends the name
def read_record(b, pos):
    name, out = [], []
    while True:
        t, v, pos = read_value(b, pos)
        if t == 0x11:
            return "-".join(name), out[1:], pos
        if (t == 0x0d or t == 0x0e) and not out:
            name.append(v)
            if t == 0x0d:
                out.append(None)  # marks the name done
        else:
            out.append(v)  # subtype names inside {} blobs (intcurve etc) too, just data


def read_sab(b):
    if b[:15] not in (b"ASM BinaryFile4", b"ACIS BinaryFile"):
        sys.exit(f"not a binary sab, starts with {b[:15]!r}")
    # 4 ints (version, records, bodies, flags), then product, acis version, date, mm per unit, resabs, resnor
    pos = 31
    head = []
    while len(head) < 6:
        if b[pos] != 0x06 and b[pos] != 0x07:
            sys.exit(f"odd sab header, tag 0x{b[pos]:02x} at byte {pos}")
        _, v, pos = read_value(b, pos)
        head.append(v)
    # record index = position in the file, asmheader is 0. last thing is End-of-ASM-data with no 0x11
    recs, subs = [], []
    while pos < len(b) and not b.startswith(b"\x0e\x03End\x0e\x02of", pos):
        name, fields, pos = read_record(b, pos)
        recs.append((name, resolve_refs(fields, subs)))
    return head[3], recs


# {} subtypes get numbered in file order as they open, "{ ref n }" later on means a copy of number n
# swaps the refs for the real thing so nothing after this has to care
def resolve_refs(f, subs):
    out, open_ = [], []
    k = 0
    while k < len(f):
        if f[k] == "{" and f[k + 1] == "ref":
            out += subs[f[k + 2]]
            k += 4
            continue
        out.append(f[k])
        if f[k] == "{":
            open_.append((len(subs), len(out) - 1))
            subs.append(None)
        elif f[k] == "}":
            n, start = open_.pop()
            subs[n] = out[start:]
        k += 1
    return out


# topology + geometry records go attrib, id, $-1, then their own stuff. this skips the first 3
# tolerant ones (tedge-edge etc) are the plain record with their tolerance stuff tacked on the end
def data(recs, i, want=None):
    name, f = recs[i]
    if want and name != want and not name.endswith("-" + want):
        sys.exit(f"record {i} is {name}, wanted {want}")
    return f[3:]


def vec(t, s=1.0):
    return App.Vector(t[0] * s, t[1] * s, t[2] * s)


# bounded ranges are "T lo T hi", unbounded just "F F", so the stuff after them moves around
def skip_range(d, k):
    for _ in range(2):
        k += 2 if d[k] is True else 1
    return k


# returns the occ surface and whether its normal points the other way from acis's
def make_surface(recs, i, mm):
    name = recs[i][0]
    d = data(recs, i)
    if name == "plane-surface":
        return Part.Plane(vec(d[0], mm), vec(d[1])), False
    if name == "cone-surface":
        if abs(d[3] - 1) > 1e-9:
            sys.exit(f"record {i}: elliptic cone (ratio {d[3]}), not handled")
        k = skip_range(d, 4)
        sin, cos = d[k], d[k + 1]
        r = vec(d[2], mm).Length
        if abs(sin) < 1e-12:
            s = Part.Cylinder()
        elif abs(cos) < 1e-12:
            sys.exit(f"record {i}: cone with a 90 deg half angle, thats a plane")
        else:
            # radius grows sin/cos per unit along the axis, either sign. cos < 0 just means normals point in
            s = Part.Cone()
            s.SemiAngle = math.atan(sin / cos)
        s.Center = vec(d[0], mm)
        s.Axis = vec(d[1])
        s.Radius = r
        return s, cos < 0
    if name == "sphere-surface":
        s = Part.Sphere()
        s.Center = vec(d[0], mm)
        s.Radius = abs(d[1]) * mm
        return s, d[1] < 0
    if name == "torus-surface":
        if d[2] <= 0 or abs(d[3]) >= d[2]:
            # lemon (major < 0, the omni rollers) or apple, occ's toroid wont take either. tube circle swept round the axis instead, same param and normal
            c, n, x = vec(d[0], mm), vec(d[1]).normalize(), vec(d[4]).normalize()
            circ = Part.Circle(c + x * (d[2] * mm), x.cross(n), abs(d[3]) * mm)
            circ.XAxis = x
            return Part.SurfaceOfRevolution(circ, c, n), d[3] < 0
        s = Part.Toroid()
        s.Center = vec(d[0], mm)
        s.Axis = vec(d[1])
        # occ wants major > minor after every set, and it starts at 5 / 1
        if d[2] * mm > s.MinorRadius:
            s.MajorRadius = d[2] * mm
            s.MinorRadius = abs(d[3]) * mm
        else:
            s.MinorRadius = abs(d[3]) * mm
            s.MajorRadius = d[2] * mm
        return s, d[3] < 0
    if name == "spline-surface":
        return make_spline_surface(recs, i, mm), d[0]
    sys.exit(f"record {i}: {name} surface not handled")


# the stored bs3 is the first nubs/nurbs one level into the subtype, deeper ones are the curves it was made from (cyl_spl_sur etc)
# layout: degree u v, "both" etc if nurbs, closure u v, singularity u v, n knots u v, (knot, mult) for u then v, poles with u running fastest, fit tol
def make_spline_surface(recs, si, mm):
    d = data(recs, si)
    depth, k = 0, None
    for j, t in enumerate(d):
        if t == "{":
            depth += 1
        elif t == "}":
            depth -= 1
        elif depth == 1 and t in ("nubs", "nurbs", "nullbs"):
            k = j
            break
    if k is None or d[k] == "nullbs":
        sys.exit(f"record {si}: {d[2]} spline surface without a stored b-spline, not handled")
    du, dv = d[k + 1], d[k + 2]
    per = 4 if d[k] == "nurbs" else 3
    j = k + (8 if per == 4 else 7)
    nu, nv = d[j], d[j + 1]
    j += 2
    ku, mu = knot_list(d, j, nu)
    j += 2 * nu
    kv, mv = knot_list(d, j, nv)
    j += 2 * nv
    npu, npv = sum(mu) - du - 1, sum(mv) - dv - 1
    end = j + per * npu * npv
    if end >= len(d) or not isinstance(d[end], float) or not all(isinstance(x, float) for x in d[j:end]):
        sys.exit(f"record {si}: couldnt line up the {d[2]} b-spline surface data")
    raw = d[j:end]
    at = [[per * (v * npu + u) for v in range(npv)] for u in range(npu)]
    poles = [[vec(raw[p:p + 3], mm) for p in row] for row in at]
    w = [[raw[p + 3] for p in row] for row in at] if per == 4 else None
    s = Part.BSplineSurface()
    s.buildFromPolesMultsKnots(poles, mu, mv, ku, kv, False, False, du, dv, w)
    return s


def point(recs, vi, mm):
    return vec(data(recs, data(recs, vi, "vertex")[2], "point")[0], mm)


# acis edges always run start vertex -> end vertex, sense says if thats against the curve
def make_edge(recs, ei, mm):
    d = data(recs, ei, "edge")
    a, b = point(recs, d[0], mm), point(recs, d[2], mm)
    ci, rev = d[5], d[6]
    name = recs[ci][0]
    c = data(recs, ci)
    if name == "straight-curve":
        return Part.LineSegment(a, b).toShape()
    if name == "ellipse-curve":
        center, normal, major = vec(c[0], mm), vec(c[1]), vec(c[2], mm)
        if abs(c[3] - 1) < 1e-9:
            g = Part.Circle(center, normal, major.Length)
            g.XAxis = major
        else:
            if c[3] > 1:
                sys.exit(f"record {ci}: ellipse with ratio {c[3]} > 1, not handled")
            minor = normal.cross(major).normalize() * (major.Length * c[3])
            g = Part.Ellipse(center + major, center + minor, center)
        # same param as acis now (x axis = major), but project the vertices anyway
        u0, u1 = g.parameter(a), g.parameter(b)
        if rev:
            u0, u1 = u1, u0
        if d[0] == d[2]:
            u1 = u0 + 2 * math.pi
        elif u1 <= u0 + 1e-12:
            u1 += 2 * math.pi
        e = g.toShape(u0, u1)
        return e.reversed() if rev else e
    if name == "intcurve-curve":
        # intcurve has its own sense (c[0]) on top of the edge's
        return spline_edge(make_spline(recs, ci, mm), a, b, rev != c[0], d[0] == d[2], (d[1], d[3]))
    sys.exit(f"record {ci}: {name} edge curve not handled")


# n (knot, mult) pairs from f[j]
def knot_list(f, j, n):
    knots, mults = f[j:j + 2 * n:2], list(f[j + 1:j + 2 * n:2])
    mults[0] += 1  # acis leaves one off each clamped end
    mults[-1] += 1
    return knots, mults


# the stored bs3 is the first nubs/nurbs in the subtype, pcurves come after it
# layout: degree, closure (0 open 2 periodic), n knots, n * (knot, mult), poles (x y z, + w for nurbs), fit tol
def make_spline(recs, ci, mm):
    f = data(recs, ci)
    k = next((j for j, t in enumerate(f) if t in ("nubs", "nurbs", "nullbs")), None)
    if k is None or f[k] == "nullbs":
        sys.exit(f"record {ci}: intcurve without a stored b-spline ({f[2]}), not handled")
    deg, n = f[k + 1], f[k + 3]
    knots, mults = knot_list(f, k + 4, n)
    per = 4 if f[k] == "nurbs" else 3
    start = k + 4 + 2 * n
    end = start + per * (sum(mults) - deg - 1)
    if end >= len(f) or not isinstance(f[end], float):
        sys.exit(f"record {ci}: couldnt line up the b-spline data")
    raw = f[start:end]
    poles = [vec(raw[j:j + 3], mm) for j in range(0, len(raw), per)]
    g = Part.BSplineCurve()
    g.buildFromPolesMultsKnots(poles, mults, knots, False, deg, raw[3::4] if per == 4 else None)
    return g


# projecting a tolerant vertex 0.01 mm off a 0.02 mm curve can land anywere on it, so the edge's stored param wins if its closer
def closest_param(g, p, s):
    u = g.parameter(p)
    if g.FirstParameter <= s <= g.LastParameter and g.value(s).distanceToPoint(p) < g.value(u).distanceToPoint(p):
        return s
    return u


# trims g to run a -> b (backwards along it if flip), wrapping over the seam if its closed
# ends get pinned onto the vertices, the fit is only good to ~1e-3 mm and wires want them exact
# t is the edge's param range, the bs3 runs the other way (-t) if flip
def spline_edge(g, a, b, flip, closed_edge, t):
    if flip:
        a, b = b, a
        t = (-t[1], -t[0])
    lo, hi = g.FirstParameter, g.LastParameter
    tol = 1e-9 * (hi - lo)
    u0, u1 = closest_param(g, a, t[0]), closest_param(g, b, t[1])
    if g.isClosed():
        if u0 > hi - tol:
            u0 = lo
        if u1 < lo + tol:
            u1 = hi
    if closed_edge:
        u1 = u0
    if u1 > u0 + tol:
        c = g.copy()
        c.segment(u0, u1)
    else:
        if not g.isClosed():
            sys.exit("intcurve edge runs backwards on an open spline")
        pieces = []
        for p0, p1 in ((u0, hi), (lo, u1)):
            if p1 > p0 + tol:
                pieces.append(g.copy())
                pieces[-1].segment(p0, p1)
        if not pieces:
            sys.exit("intcurve edge with no length to it")
        c = pieces[0]
        for p in pieces[1:]:
            if not c.join(p):
                sys.exit("intcurve edge across the seam didnt join back up")
    c.setPole(1, a)
    c.setPole(c.NbPoles, b)
    e = c.toShape()
    return e.reversed() if flip else e


# acis vertices can sit a bit off the curve ends (2e-4 mm seen on arcs, tolerant ones more), 2x cuz the next edge can be off the other way
# Part.Wire just quietly leaves out an edge that doesnt reach, even at 1.1e-7 off
def fit_ends(recs, ei, e, mm):
    d = data(recs, ei, "edge")
    ends = [v.Point for v in e.Vertexes]
    gap = max(min((p - q).Length for q in ends) for p in (point(recs, d[0], mm), point(recs, d[2], mm)))
    if gap > 1e-8:
        e.fixTolerance(2 * gap + 1e-7, Part.Vertex)
    return e


def loop_wire(recs, li, edges, mm):
    first = data(recs, li, "loop")[1]
    out, ci, seen = [], first, set()
    while True:
        if ci in seen:
            sys.exit(f"loop {li}: coedges go round without getting back to the first one")
        seen.add(ci)
        d = data(recs, ci, "coedge")
        ei = d[3]
        if ei not in edges:
            edges[ei] = fit_ends(recs, ei, make_edge(recs, ei, mm), mm)
        out.append(edges[ei].reversed() if d[4] else edges[ei])
        ci = d[0]
        if ci == first or ci == -1:
            break
    w = Part.Wire(out)
    if len(w.Edges) != len(out):
        sys.exit(f"loop {li}: wire came out with {len(w.Edges)} of {len(out)} edges")
    return w


def make_face(recs, fi, edges, mm):
    d = data(recs, fi, "face")
    surf, flip = make_surface(recs, d[4], mm)
    # loops go ccw around the acis face normal (= surface normal, flipped if the face is reversed)
    # if occ's surface normal disagrees, build on it with the wires backwards and flip the face after
    agree = d[5] == flip
    fix = Part.ShapeFix.Face(surf, 1e-7, True)
    li = d[1]
    while li != -1:
        w = loop_wire(recs, li, edges, mm)
        fix.add(w if agree else w.reversed())
        li = data(recs, li, "loop")[0]
    fix.perform()
    f = fix.face()
    return f if agree else f.reversed()


def build(recs, mm):
    bad = Counter(n for n, _ in recs if n.endswith(("-surface", "-curve")) and n not in SURFACES + CURVES)
    if bad:
        sys.exit("geometry not handled yet: " + ", ".join(f"{n} x{c}" for n, c in bad.most_common()))
    solids, edges = [], {}
    for bi, (name, _) in enumerate(recs):
        if name != "body":
            continue
        d = data(recs, bi)
        if d[2] != -1:
            t = recs[d[2]][1][2:]
            if t[:4] != [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)] or t[4] != 1:
                sys.exit(f"body {bi} has a non identity transform {t[:5]}, not handled")
        lump = d[0]
        while lump != -1:
            # a lump is one connected solid, any shells after the first are voids (faces already point into them)
            shells, shell = [], data(recs, lump, "lump")[1]
            while shell != -1:
                s = data(recs, shell, "shell")
                if s[1] != -1:
                    sys.exit(f"shell {shell} has subshells, not handled")
                faces, fids, fi = [], [], s[2]
                while fi != -1:
                    faces.append(make_face(recs, fi, edges, mm))
                    fids.append(fi)
                    fi = data(recs, fi, "face")[0]
                sh = Part.Shell(faces)
                sh.sewShape()
                if sh.ShapeType != "Shell":
                    # seen on a modeled thread (cylinder face with a hole winding past the seam ~10 times) and 0.2 mm ball corners with tolerant vertices off by about the face size
                    broken = [f"{i} ({recs[data(recs, i)[4]][0]})" for i, f in zip(fids, faces) if not f.isValid()]
                    sys.exit(f"shell {shell} didnt sew into one shell, got {sh.ShapeType}"
                             + (". faces that came out invalid: " + ", ".join(broken) if broken else ""))
                if not sh.isValid():
                    # tiny faces (0.002 mm2 slivers on the omni rollers) can have pcurves crossing in uv once theyre in the shell
                    # shapefix at 1e-4 grows the tolerances over it, ~4e-5 mm
                    sh.fix(1e-4, 1e-7, 1e-3)
                if not sh.isClosed():
                    print(f"body {bi}: shell {shell} isnt closed", file=sys.stderr)
                shells.append(sh)
                shell = s[0]
            if not shells:
                sys.exit(f"body {bi}: lump {lump} has no shells")
            so = Part.Solid(shells[0] if len(shells) == 1 else Part.Compound(shells))
            if not so.isValid():
                print(f"body {bi}: lump {lump} isnt a valid solid", file=sys.stderr)
            solids.append(so)
            lump = data(recs, lump, "lump")[0]
    return solids


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python -I tools/read_f3d.py <in.f3d> <out.step>")
    solids = []
    for name, b in read_smb(sys.argv[1]):
        try:
            mm, recs = read_sab(b)
            solids += build(recs, mm)
        except SystemExit as e:
            sys.exit(f"{name}: {e}")
    if not solids:
        sys.exit("no solids in there")
    shape = solids[0] if len(solids) == 1 else Part.Compound(solids)
    shape.exportStep(sys.argv[2])
    bb = shape.optimalBoundingBox()  # plain BoundBox goes off the torus poles, way too big
    print(f"{len(shape.Solids)} solid(s), {len(shape.Faces)} faces, valid {shape.isValid()}")
    print(f"volume {shape.Volume / IN ** 3:.6f} in3")
    print(f"bbox {bb.XLength / IN:.4f} x {bb.YLength / IN:.4f} x {bb.ZLength / IN:.4f} in")
