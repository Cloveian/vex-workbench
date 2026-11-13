# plastic versahubs, 1/2 hex bore, off the fusion library's f3ds. flange with 3 tabs into a flex wheel's windows, a hub on top. v2 takes a steel hex insert on a bayonet
import math

import Part
from FreeCAD import Vector

from .metal import IN
from .slide import section
from .stock import hexagon

FAMILIES = ("versahub", "versahub-v2", "versahub-insert")
Z = Vector(0, 0, 1)
SIXES = range(0, 360, 60)

# in, flange centered on z = 0. drafts and the 0.3 / 1 mm rounds left off, ~0.2% heavy (v2 ~0.7%)
FLANGE, RIM = 0.0625, 1.0989  # half thick, radius at the middle of its 1 deg draft
HUB, TOP = 0.563, 0.4375
RIB_TOP, CHANNEL_TOP = 0.1875, 0.1284
BOLTS, HOLE = 1.875, 0.1695  # same bolt circle as the 3 and 4 in flex wheels
BLIND, BLIND_AT = 0.0541, 0.375  # radius and the cirlce they sit on, down to the flange top
# v2. the insert's collar goes down the deep pockets and turns 30 into the recess, seated and locked here
BORE = 0.3553  # radius, the insert's tube too
COLLAR, SCALLOP, LOBE_ROUND = 0.4838, 0.1284, 0.0787  # radius, scallops centered on its edge, 2 mm lobe tips
COLLAR_Z = 0.0162, 0.095
DEEP_FLOOR, SHALLOW_FLOOR = COLLAR_Z[0], 0.1737  # deep ones open into the recess
INSERT_HEX, SINK = 0.5012, 0.2998  # across the flats, 45 deg countersink radius at each end

# one side on +y, like slide.half takes. notch between two tabs, rib on the flange over the channel under it, pocket in the hub halfway down its draft
NOTCH = [(0, 0.7677), ((0.1632, 0.7502), (0, 0)), ((0.2096, 0.7784), (0.1716, 0.7886)), (0.2750, 1.0224), ((0.3247, 1.0499), (0.3131, 1.0122)), (0.40, 1.30), (0, 1.30)]
RIB = [(0, 0.7874), ((0.1473, 0.7735), (0, 0)), ((0.2194, 0.8187), (0.1590, 0.8349)), (0.2406, 0.8978), ((0.1923, 0.9753), (0.1802, 0.9140)), ((0, 0.9941), (0, 0))]
CHANNEL = [(0, 0.8465), ((0.1438, 0.8341), (0, 0)), ((0.1662, 0.8484), (0.1472, 0.8535)), (0.1790, 0.8962), ((0.1634, 0.9206), (0.1600, 0.9013)), ((0, 0.9350), (0, 0))]
POCKET = [(0, 0.3789), ((0.0237, 0.3782), (0, 0)), ((0.0403, 0.3820), (0.0256, 0.4076)), (0.1038, 0.4187), ((0.0948, 0.4732), (0.0891, 0.4443)), ((0, 0.4826), (0, 0))]
# v2's, round a lobe and between two. 0.2 mm rounds as chords
DEEP = [(0, 0.4000), ((0.0701, 0.4371), (0, 0.4849)), ((0.0979, 0.4662), (0.1712, 0.3682)), (0.0948, 0.4802), ((0, 0.4879), (0, 0))]
SHALLOW = [(0, 0.3975), ((0.1124, 0.3825), (0, 0)), (0.1223, 0.3918), ((0.1194, 0.4107), (0.2425, 0.4199)), ((0.0432, 0.4880), (0.0358, 0.4045)), ((0, 0.4888), (0, 0))]


def disc(r, z0, z1, x=0, y=0):
    return Part.makeCylinder(r * IN, (z1 - z0) * IN, Vector(x, y, z0) * IN)


def around(pts, z0, z1, degs):
    # off x-z, a copy turned to each angle
    s = section(pts).rotated(Vector(), Vector(1, 0, 0), -90).extrude(Vector(0, 0, (z1 - z0) * IN)).translated(Vector(0, 0, z0 * IN))
    return [s.rotated(Vector(), Z, a) for a in degs]


def hex_bore(flats):
    return hexagon(flats * IN, 30).extrude(Vector(0, 0, 2 * IN)).translated(Vector(0, 0, -IN))


def collar(z0, z1):
    # lobes on the 30s, locked
    circle = lambda r, a=None: Part.Face(Part.Wire(Part.makeCircle(r * IN, Vector() if a is None else Vector(math.cos(a), math.sin(a), 0) * COLLAR * IN)))
    f = circle(COLLAR).cut([circle(SCALLOP, math.radians(a)) for a in SIXES]).Faces[0]
    f = f.makeOffset2D(-LOBE_ROUND * IN).makeOffset2D(LOBE_ROUND * IN)
    return f.extrude(Vector(0, 0, (z1 - z0) * IN)).translated(Vector(0, 0, z0 * IN))


def hub(cuts):
    # both versions. ribs on 0 / 120 / 240, notches halfway between, bolt holes on the 30s
    ribs = (-90, 30, 150)
    body = disc(RIM, -FLANGE, FLANGE).fuse([disc(HUB, 0, TOP)] + around(RIB, 0, RIB_TOP, ribs))
    cuts = cuts + around(NOTCH, -1, 1, (-30, 90, 210)) + around(CHANNEL, -1, CHANNEL_TOP, ribs)
    for a in map(math.radians, SIXES):
        cuts.append(disc(HOLE / 2, -1, 1, BOLTS / 2 * math.cos(a + math.pi / 6), BOLTS / 2 * math.sin(a + math.pi / 6)))
    return body.cut(cuts).removeSplitter()


def v1():
    # pockets on the 30s, blind holes on the 60s
    cuts = around(POCKET, FLANGE, 1, SIXES) + [hex_bore(0.5)]
    for a in map(math.radians, SIXES):
        cuts.append(disc(BLIND, FLANGE, 1, BLIND_AT * math.cos(a), BLIND_AT * math.sin(a)))
    return hub(cuts)


def v2():
    # deep pockets round the lobes on the 60s, shalow ones between
    return hub(around(DEEP, DEEP_FLOOR, 1, [a + 30 for a in SIXES]) + around(SHALLOW, SHALLOW_FLOOR, 1, SIXES) + [disc(BORE, -1, 1), collar(*COLLAR_Z)])


def insert():
    sink = Part.makeCone((SINK - 0.05) * IN, (SINK + 0.05) * IN, 0.1 * IN, Vector(0, 0, TOP - 0.05) * IN)
    cuts = [hex_bore(INSERT_HEX), sink, sink.mirror(Vector(0, 0, (TOP - FLANGE) / 2 * IN), Z)]
    return disc(BORE, -FLANGE, TOP).fuse(collar(*COLLAR_Z)).cut(cuts).removeSplitter()


def make(part, cat):
    return {"versahub": v1, "versahub-v2": v2, "versahub-insert": insert}[part["family"]]()
