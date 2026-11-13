# plastic versahub, 1/2 hex bore, off the fusion library's f3d. flange with 3 tabs into a flex wheel's windows, a hub on top with blind holes and pockets
import math

import Part
from FreeCAD import Vector

from .metal import IN
from .slide import section
from .stock import hexagon

FAMILIES = ("versahub",)
Z = Vector(0, 0, 1)

# in, flange centered on z = 0. drafts and the 0.3 / 1 mm rounds left off, ~0.2% heavy
FLANGE, RIM = 0.0625, 1.0989  # half thick, radius at the middle of its 1 deg draft
HUB, TOP = 0.563, 0.4375
RIB_TOP, CHANNEL_TOP = 0.1875, 0.1284
BOLTS, HOLE = 1.875, 0.1695  # same bolt circle as the 3 and 4 in flex wheels
BLIND, BLIND_AT = 0.0541, 0.375  # radius and the cirlce they sit on, down to the flange top

# one side on +y, like slide.half takes. notch between two tabs, rib on the flange over the channel under it, pocket in the hub halfway down its draft
NOTCH = [(0, 0.7677), ((0.1632, 0.7502), (0, 0)), ((0.2096, 0.7784), (0.1716, 0.7886)), (0.2750, 1.0224), ((0.3247, 1.0499), (0.3131, 1.0122)), (0.40, 1.30), (0, 1.30)]
RIB = [(0, 0.7874), ((0.1473, 0.7735), (0, 0)), ((0.2194, 0.8187), (0.1590, 0.8349)), (0.2406, 0.8978), ((0.1923, 0.9753), (0.1802, 0.9140)), ((0, 0.9941), (0, 0))]
CHANNEL = [(0, 0.8465), ((0.1438, 0.8341), (0, 0)), ((0.1662, 0.8484), (0.1472, 0.8535)), (0.1790, 0.8962), ((0.1634, 0.9206), (0.1600, 0.9013)), ((0, 0.9350), (0, 0))]
POCKET = [(0, 0.3789), ((0.0237, 0.3782), (0, 0)), ((0.0403, 0.3820), (0.0256, 0.4076)), (0.1038, 0.4187), ((0.0948, 0.4732), (0.0891, 0.4443)), ((0, 0.4826), (0, 0))]


def disc(r, z0, z1, x=0, y=0):
    return Part.makeCylinder(r * IN, (z1 - z0) * IN, Vector(x, y, z0) * IN)


def around(pts, z0, z1, degs):
    # off x-z, a copy turned to each angle
    s = section(pts).rotated(Vector(), Vector(1, 0, 0), -90).extrude(Vector(0, 0, (z1 - z0) * IN)).translated(Vector(0, 0, z0 * IN))
    return [s.rotated(Vector(), Z, a) for a in degs]


def make(part, cat):
    # ribs on 0 / 120 / 240, notches halfway between, bolt holes and pockets on the 30s
    ribs, notches, sixes = (-90, 30, 150), (-30, 90, 210), range(0, 360, 60)
    body = disc(RIM, -FLANGE, FLANGE).fuse([disc(HUB, 0, TOP)] + around(RIB, 0, RIB_TOP, ribs))
    cuts = around(NOTCH, -1, 1, notches) + around(CHANNEL, -1, CHANNEL_TOP, ribs) + around(POCKET, FLANGE, 1, sixes)
    for a in map(math.radians, sixes):
        cuts.append(disc(BLIND, FLANGE, 1, BLIND_AT * math.cos(a), BLIND_AT * math.sin(a)))
        cuts.append(disc(HOLE / 2, -1, 1, BOLTS / 2 * math.cos(a + math.pi / 6), BOLTS / 2 * math.sin(a + math.pi / 6)))
    cuts.append(hexagon(0.5 * IN, 30).extrude(Vector(0, 0, 2 * IN)).translated(Vector(0, 0, -IN)))
    return body.cut(cuts).removeSplitter()
