# the 2.75 legacy omni off the fusion library's f3d. a hub with 7 roller cradles a side, 14 rollers (rubber on a core on a pin), all one compound
import math

import Part
from FreeCAD import Vector

from .metal import IN, X, square
from .ratchet import along, revolved
from .sprocket import disc

FAMILIES = ("legacy-omni",)
Z = Vector(0, 0, 1)

# in, axis on z. front rollers at 90 - 360k/7 on z +OUT, the back ones half a step round on -OUT
N, AT, OUT = 7, 1.0827, 0.315
FACE, DISC, WEB, PLATE = 0.4429, 0.0295, 0.0492, 0.3839  # z of the outside faces, the middle disc, cradle bottoms past the middle, cradle tops inside
BORE, BORE_ROUND = 0.25, 0.0118  # HS square
# outside of the cradles, (r, z) like slide.half. a crowned rim, the faces lean in 0.01 out past r 0.94
OUTSIDE = [(0, -FACE), (0.9449, -FACE), (1.1796, -0.4332), ((1.2877, -0.3239), (1.1796, -0.3239)), ((1.2877, 0.3239), (-3.268, 0)), ((1.1796, 0.4332), (1.1796, 0.3239)), (0.9449, FACE), (0, FACE), (0, -FACE)]
# inside of the ring the spokes come off, flared out to a chamfer at the face
INSIDE = [(0, DISC), (0.6578, DISC), (0.6886, 0.3993), (0.6921, 0.4075), (0.7246, 0.4395), (0.7329, FACE), (0.7329, 1), (0, 1), (0, DISC)]
# cradles, a wedge between two lines (u across, v out) on one side of its middle. hollow 0.0646 in from them out to r 1.2355, open under the middle
CRADLE = (0.0435, 0.9098), (0.2131, 1.2618)
CAVITY = (0.0104, 0.99), (0.1181, 1.2139), 1.2355
# the pins snap in from the face down a slot to the pin, this far along it and this wide, then a hole round the pin's end
NOTCH, NOTCH_WIDE, PIN_HOLE = 0.4336, 0.099, (0.0413, 0.4766)
# pockets between them, the web runs round a circle this big this far out on the roller's line. holes at the cradle feet off the same circles
SCALLOP, SCALLOP_AT, FOOT = 1.4186, 2.165, 1.4614
# barrel, (r, z): the bore boss and a tube round it with a gap between, spokes across the gap
BOSS = [(0, 0), (0.2474, 0), (0.2423, 0.2881), (0.2396, 0.3718), ((0.2295, 0.3929), (0.2295, 0.3832)), (0, 0.3929), (0, 0)]
TUBE = [(0.2859, 0), (0.341, 0), (0.341, 0.3813), ((0.326, 0.3929), (0.326, 0.3813)), (0.3039, 0.3929), ((0.2921, 0.3813), (0.3039, 0.3813)), (0.2859, 0)]
LUGS = 0.2928, 0.3372, 32, 0.447  # two up off the tube, 32 to 148 deg and across
# 6 spokes, each the piece of a crescent between two circles (center, r) at about this deg, +60k. a groove down the middle out past the tube, the disc's windows between them
SPOKE, SPOKE_TOP = (((-0.3937, 0), 0.5871), ((-0.4724, -0.0669), 0.4557), -105), 0.374
GROOVE = ((-0.3937, 0), 0.5429), ((-0.4724, -0.0669), 0.5004), -100, 0.52
WINDOW = 0.3445, 0.6299
# roller clearance through the middle, the rubber's barrel 1 mm bigger round each roller's axis, cut off this far along it
CLEAR = [(0, -0.4061), (0.2750, -0.4061), ((0.2750, 0.4061), (-1.0807, 0)), (0, 0.4061), (0, -0.4061)]
# rollers, (r off the axis, along it) like ratchet.revolved, half of each. 2 mm pin, a core with two grooves round it, rubber on its middle
PIN, PIN_LONG = 0.0394, 0.4528
CORE = [(0.0413, 0), (0.0413, 0.3445), (0.1532, 0.3445), (0.1753, 0.3306), (0.1811, 0.3166), (0.1811, 0.2756), (0.2008, 0.2478), (0.2008, 0.2165), ((0.1811, 0.1969), (0.1811, 0.2165)), (0.1023, 0.1969), (0.1023, 0.0394), (0.1811, 0.0394), ((0.2008, 0.0197), (0.1811, 0.0197)), (0.2008, 0), (0.0413, 0)]
RUBBER = [(0.1968, 0), (0.1968, 0.2579), (0.1771, 0.2776), (0.1771, 0.3248), (0.2471, 0.3248), ((0.2586, 0.3157), (0.2471, 0.3157)), ((0.2953, 0), (-1.0807, 0)), (0.1968, 0)]


def ring(r0, r1):
    return disc(r1).cut(disc(r0))


def polar(r, deg):
    return r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg))


def turned(shape, deg):
    return shape.rotated(Vector(), Z, deg)


def both(pts):
    # a revolved profile on z >= 0 and its mirror
    f = revolved(pts)
    return [f, f.mirror(Vector(), Z)]


def front():
    return [90 - 360 * k / N for k in range(N)]


def back():
    return [a + 180 / N for a in front()]


def seats():
    return [(a, OUT) for a in front()] + [(a, -OUT) for a in back()]


def wedge(lines, v0, v1):
    # between the two lines (u, v) -> (-u, v) mirrored, from v0 out to v1, pointing up +y
    (u0, w0), (u1, w1) = lines
    u = lambda v: u0 + (v - w0) * (u1 - u0) / (w1 - w0)
    pts = [Vector(-u(v0), v0, 0), Vector(u(v0), v0, 0), Vector(u(v1), v1, 0), Vector(-u(v1), v1, 0)]
    return Part.Face(Part.makePolygon([p * IN for p in pts + pts[:1]]))


def side():
    # the front's ring and cradles, cradles at the back rollers. the back is this turned over on x
    web = along(disc(1.0).cut([disc(SCALLOP, *polar(SCALLOP_AT, a)) for a in front()]), DISC, FACE)
    cradles = [turned(along(wedge(CRADLE, 0.84, 1.45), -WEB, FACE), a - 90) for a in back()]
    return web.fuse(cradles)


def holes():
    # front cradles' cavities and the holes at their feet, through to the back's pockets
    (u0, v0), (u1, v1), r = CAVITY
    cavity = wedge(CAVITY[:2], v0 - u0 * (v1 - v0) / (u1 - u0) + 0.001, 1.4).common(disc(r))
    out = []
    for a in back():
        foot = disc(SCALLOP, *polar(SCALLOP_AT, a)).cut([disc(FOOT, *polar(SCALLOP_AT, a + d)) for d in (-180 / N, 180 / N)])
        foot = foot.common(disc(0.9))
        out += [turned(along(cavity, -1, PLATE), a - 90), along(foot, -1, PLATE)]
    notch = Part.makeBox(2 * NOTCH * IN, NOTCH_WIDE * IN, (1 - OUT) * IN, Vector(-NOTCH, AT - NOTCH_WIDE / 2, OUT) * IN)
    r, long = PIN_HOLE
    pin = Part.makeCylinder(r * IN, 2 * long * IN, Vector(-long, AT, OUT) * IN, X)
    return out + [turned(s, a - 90) for a in front() for s in (notch, pin)]


def lugs():
    r0, r1, a, top = LUGS
    fan = Part.Face(Part.makePolygon([Vector()] + [Vector(*polar(1, d), 0) * IN for d in (a, 90, 180 - a)] + [Vector()]))
    one = along(ring(r0, r1).common(fan), 0.3, top)
    out = [one, turned(one, 180)]
    return out + [s.mirror(Vector(), Z) for s in out]


def crescent(c1, r1, c2, r2, at, r0, r):
    # in circle c1, out of c2, r0 to r from the axis. the circles go round past the next spoke, so just the piece at about at deg
    pieces = disc(r1, *c1).cut(disc(r2, *c2)).common(ring(r0, r)).Faces
    return min(pieces, key=lambda f: abs(math.remainder(math.degrees(math.atan2(f.CenterOfMass.y, f.CenterOfMass.x)) - at, 360)))


def spokes():
    one = crescent(*SPOKE[0], *SPOKE[1], SPOKE[2], 0.2426, 0.69)
    (g1, s1), (g2, s2), at, out = GROOVE
    groove = crescent(g1, s1, g2, s2, at, 0.341, out)
    body = along(one, -SPOKE_TOP, SPOKE_TOP).cut([along(groove, DISC, 1), along(groove, -1, -DISC)])
    return one, [turned(body, 60 * k) for k in range(6)]


def roller():
    # rubber, core and pin round z
    pin = Part.makeCylinder(PIN * IN, 2 * PIN_LONG * IN, Vector(0, 0, -PIN_LONG * IN))
    return [s.fuse(s.mirror(Vector(), Z)).removeSplitter() for s in (revolved(RUBBER), revolved(CORE))] + [pin.makeFillet(PIN / 2 * IN, pin.Edges)]


def placed(s, a, z):
    # off z onto the roller at a deg: round x, out to r AT
    return turned(s.rotated(Vector(), Vector(0, 1, 0), 90).translated(Vector(0, AT, z) * IN), a - 90)


def hub():
    s = side()
    middle = [along(disc(1.4), -DISC, DISC), along(ring(0.66, 1.4), -WEB, WEB)]  # the disc, thicker out under the cradles
    outer = s.fuse([s.rotated(Vector(), X, 180)] + middle).common(revolved(OUTSIDE)).cut(both(INSIDE))
    spoke, arms = spokes()
    body = outer.fuse(both(BOSS) + both(TUBE) + arms + lugs())
    h = holes()
    cuts = h + [x.rotated(Vector(), X, 180) for x in h]
    windows = ring(*WINDOW).cut([turned(spoke, 60 * k) for k in range(6)])
    cuts.append(along(windows, -DISC - 0.01, DISC + 0.01))
    # only through the middle, out past it the cradles' own walls make the pocekts
    through = Part.makeBox(4 * IN, 4 * IN, 2 * (WEB + 0.01) * IN, Vector(-2, -2, -WEB - 0.01) * IN)
    clear = revolved(CLEAR)
    cuts += [placed(clear, a, z).common(through) for a, z in seats()]
    cuts.append(along(square(BORE * IN, BORE_ROUND * IN), -1, 1))
    return body.cut(cuts)


def make(part, cat):
    one = roller()
    rollers = [placed(s, a, z) for a, z in seats() for s in one]
    return Part.makeCompound([hub()] + rollers)
