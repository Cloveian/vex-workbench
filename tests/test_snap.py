# hole frames + Fixed joints, shaft ends, the screw, spacer and align tools, run with: python tests/test_snap.py (needs FreeCAD + vex-step/)
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401
import FreeCAD as App  # noqa: E402
import JointObject  # noqa: E402  Assembly workbench, works headless
import Part  # noqa: E402

from freecad.vex_workbench import library, snap  # noqa: E402
from freecad.vex_workbench.metal import IN  # noqa: E402

doc = App.newDocument("snaptest")
asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
asm.Type = "Assembly"
joints = asm.newObject("Assembly::JointGroup", "Joints")
_, gen, steps = library.index()
a = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
b = library.place(doc, gen["1x5x1x10 Steel C-Channel"], asm)
b.Placement = App.Placement(App.Vector(30, 40, 50), App.Rotation(10, 20, 30))
doc.recompute()

# a: second web hole, a bit off center on the outside. b: a flange hole
fa = library.hole_frame(a, App.Vector(0.8, 0.55, 0.3) * IN)
fb = library.hole_frame(b, App.Vector(3.2, 0.3, 0.0) * IN)
assert (fa.Placement.Base - App.Vector(0.75, 0.546, 0.25) * IN).Length < 1e-6, fa.Placement.Base / IN
assert (fa.Placement.Rotation.multVec(App.Vector(0, 0, 1)) - App.Vector(0, 1, 0)).Length < 1e-9
assert (fb.Placement.Base - App.Vector(3.25, 0.25, 0) * IN).Length < 1e-6, fb.Placement.Base / IN
assert (fb.Placement.Rotation.multVec(App.Vector(0, 0, 1)) - App.Vector(0, 0, -1)).Length < 1e-9

# same spot again is the same frame
assert library.hole_frame(a, App.Vector(0.76, 0.55, 0.26) * IN) == fa

ground = joints.newObject("App::FeaturePython", "Ground")
JointObject.GroundedJoint(ground, a)
j = joints.newObject("App::FeaturePython", "Joint")
JointObject.Joint(j, JointObject.JointTypes.index("Fixed"))
j.Proxy.setJointConnectors(j, [[a, [fa.Name + ".", fa.Name + "."]], [b, [fb.Name + ".", fb.Name + "."]]])
assert asm.solve() == 0
doc.recompute()

pa, pb = a.Placement.multiply(fa.Placement), b.Placement.multiply(fb.Placement)
apart = (pa.Base - pb.Base).Length
assert apart < 1e-9, apart

# a shaft through fa, end frame on its axis
s = library.place(doc, gen["2.000 LS Shaft"], asm)
s.Placement = App.Placement(App.Vector(-20, 10, 5), App.Rotation(30, 0, 40))
doc.recompute()
fs = library.hole_frame(s, App.Vector(0.01, 0.02, 0.1) * IN)
assert fs.Placement.Base.Length < 1e-9, fs.Placement.Base
j = joints.newObject("App::FeaturePython", "Joint")
JointObject.Joint(j, JointObject.JointTypes.index("Fixed"))
j.Proxy.setJointConnectors(j, [[a, [fa.Name + ".", fa.Name + "."]], [s, [fs.Name + ".", fs.Name + "."]]])
assert asm.solve() == 0
doc.recompute()
axis = pa.Rotation.multVec(App.Vector(0, 0, 1))
off = (s.Placement.multVec(App.Vector(0, 0, 25)) - pa.Base).cross(axis).Length
assert off < 1e-9, off
assert (s.Placement.Base - pa.Base).Length < 1e-9, s.Placement.Base

# screw + nylock through two plates, the second one two holes over. 2 * 0.046 + the nylock 0.193 -> the 0.29 star
from freecad.vex_workbench import screws  # noqa: E402

m = App.Placement(App.Vector(5, -7, 11), App.Rotation(20, 30, 40))
p1 = library.place(doc, gen["5x10 Steel Plate"], asm)
p2 = library.place(doc, gen["5x10 Steel Plate"], asm)
p1.Placement = m
p2.Placement = m.multiply(App.Placement(App.Vector(-IN, 0, -0.046 * IN), App.Rotation()))
for p in (p1, p2):
    # the solver leaves alone anything not tied to ground
    JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), p)
doc.recompute()
# clicked inside the assembly, so the root is asm
head = (p1, App.Vector(1.27, 0.24, 0.046) * IN, p1.Placement, (asm, p1.Name + "."))  # top face, the (1.25, 0.25) hole
tail = (p2, App.Vector(2.26, 0.26, 0) * IN, p2.Placement, (asm, p2.Name + "."))  # bottom face, same hole
nylock = screws.nuts()["Nylock Nut"]
had = len(joints.Group)
sc, nut, _ = screws.fasten(doc, head, tail, "star-screw", nylock, asm)
assert sc.Label == "0.290 Torx (Star) Screw (8-32, Steel)", sc.Label
# a Revolute joint each, and solving moves nothing
new = joints.Group[had:]
assert [(j.JointType, j.Reference1[0], j.Reference2[0]) for j in new] == [("Revolute", p1, sc), ("Revolute", p2, nut)], new


def moved(objs):
    # what asm.solve() moved, by label
    was = [o.Placement for o in objs]
    assert asm.solve() == 0
    doc.recompute()
    return [o.Label for o, p in zip(objs, was) if not o.Placement.isSame(p, 1e-9)]


got = moved([p1, p2, sc, nut])
assert not got, got


def local(link):
    # bbox in the plate's own frame, inches
    s = Part.getShape(link).copy()
    s.Placement = m.inverse().multiply(s.Placement)
    b = s.optimalBoundingBox()
    return [round(v / IN, 4) for v in (b.Center.x, b.Center.y, b.ZMin, b.ZMax)]


assert local(nut) == [1.25, 0.25, -0.2391, -0.046], local(nut)
got = local(sc)
assert got[:2] == [1.25, 0.25] and got[2] == round(0.046 - 0.29, 4) and got[3] == round(0.046 + 0.087, 4), got
sc, *_ = screws.fasten(doc, head, tail, "hex-screw", nylock)
assert sc.Label == "0.375 Hex Screw (8-32, Steel)", sc.Label
try:
    screws.fasten(doc, head, (p2, App.Vector(2.26, 0.26, 0.046) * IN, p2.Placement, tail[3]), "star-screw", nylock)  # inside face
    raise AssertionError("inside face went through")
except ValueError:
    pass

# nut side plate inside a linked sub-assembly, its joint goes on the link (the part that moves)
side = doc.addObject("App::Part", "Side")
p3 = library.place(doc, gen["5x10 Steel Plate"], side)
p3.Placement = App.Placement(App.Vector(-IN, 0, -0.046 * IN), App.Rotation())
sub = asm.newObject("App::Link", "SideLink")
sub.LinkedObject = side
sub.Placement = m
JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), sub)
doc.recompute()
inner = (p3, tail[1], sub.Placement.multiply(p3.Placement), (asm, f"{sub.Name}.{p3.Name}."))
had = len(joints.Group)
sc, nut, _ = screws.fasten(doc, head, inner, "star-screw", nylock, asm)
new = joints.Group[had:]
assert [j.Reference1[0] for j in new] == [p1, sub] and new[1].Reference1[1][0].startswith(p3.Name + "."), [j.Reference1 for j in new]
got = moved([sc, nut])
assert not got, got
assert local(nut) == [1.25, 0.25, -0.2391, -0.046], local(nut)

# stright through both flanges of one channel (a), head and nut on the same part. 1.0 + 0.193 -> the 1.25
on_a = (asm, a.Name + ".")
top = (a, App.Vector(0.76, 0.26, 1.0) * IN, a.Placement, on_a)  # top flange outside, the (0.75, 0.25) hole
bot = (a, App.Vector(0.76, 0.24, 0) * IN, a.Placement, on_a)  # bottom flange outside
had = len(joints.Group)
sc, nut, _ = screws.fasten(doc, top, bot, "star-screw", nylock, asm)
assert sc.Label == "1.250 Torx (Star) Screw (8-32, Steel)", sc.Label
assert (sc.Placement.Base - App.Vector(0.75, 0.25, 1.0) * IN).Length < 1e-6, sc.Placement.Base / IN
refs = [(j.Reference1[0], j.Reference2[0]) for j in joints.Group[had:]]
assert refs == [(a, sc), (a, nut)], refs
got = moved([sc, nut])
assert not got, got

# same with the gap between the flanges filled, 1 - 2 * 0.046 = 0.908 -> 7/8 + a 1/32 washer
def stacked(put):
    # label without the 001 of a second copy, z in the asm
    return [(o.Label.rstrip("0123456789"), round(o.Placement.Base.z / IN, 4)) for o in put]


sc, nut, put = screws.fasten(doc, top, bot, "star-screw", nylock, asm, 0.375)
labels = stacked(put)
assert labels == [("0.375 OD Spacer, 0.875 (Nylon)", 0.954), ("Washer, 0.375 OD, 0.032 (Nylon)", 0.079)], labels
got = moved([sc, nut, *put])
assert not got, got

# spacer tool between the inside faces, 0.5 OD, stacked up from the bottom flange
from freecad.vex_workbench import spacers  # noqa: E402

put = spacers.fill(doc, (a, App.Vector(0.76, 0.26, 0.046) * IN, a.Placement, on_a), (a, App.Vector(0.76, 0.24, 0.954) * IN, a.Placement, on_a), 0.5, asm)
labels = stacked(put)
assert labels == [("0.5 OD Spacer, 0.875 (Nylon)", 0.046), ("Washer, 0.375 OD, 0.032 (Nylon)", 0.921)], labels
got = moved(put)
assert not got, got

# no nut, into a standoff under the (1.25, 0.25) hole in p1. the 0.5 is through, a 2 is tapped 0.5 from each end
for size, want in [("0.500", "0.500"), ("2.000", "0.500"), ("0.375", "0.375")]:
    so = library.place(doc, gen[f"{size} Standoff (8-32, Aluminum)"], asm)
    h = float(size) * IN
    so.Placement = m.multiply(App.Placement(App.Vector(1.25 * IN, 0.25 * IN, -h), App.Rotation()))
    doc.recompute()
    into = (so, App.Vector(0.01, 0, h), so.Placement, (asm, so.Name + "."))
    had = len(joints.Group)
    sc, nut, _ = screws.fasten(doc, head, into, "star-screw", nylock, asm)
    # 0.046 of plate, then 3/8 in if the thread is that deep
    assert sc.Label.rstrip("0123456789") == f"{want} Torx (Star) Screw (8-32, Steel)" and nut is None, (size, sc.Label)
    assert [j.Reference2[0] for j in joints.Group[had:]] == [sc]
    doc.removeObject(so.Name)
so = library.place(doc, gen["0.250 Standoff (8-32, Aluminum)"], asm)
so.Placement = m.multiply(App.Placement(App.Vector(1.25 * IN, 0.25 * IN, -0.25 * IN), App.Rotation()))
doc.recompute()
try:
    screws.fasten(doc, head, (so, App.Vector(0.01, 0, 0.25 * IN), so.Placement, (asm, so.Name + ".")), "star-screw", nylock, asm)
    raise AssertionError("got 1/4 into a 1/4 standoff through a plate")
except ValueError:
    pass
# No nut picked, but the p2 hole is plain metal
try:
    screws.fasten(doc, head, (p2, App.Vector(2.26, 0.26, 0.046) * IN, p2.Placement, tail[3]), "star-screw", None)
    raise AssertionError("screwed into plain metal")
except ValueError:
    pass

# the 5.5W motor's front holes are threaded, 3/4 deep
motor = library.place(doc, steps["Electronics/V5 Smart Motor (5.5W) (276-4842).step"])
doc.recompute()
across, deep = screws.bore(motor, library.hole_frame(motor, App.Vector(0.01, -1.578, 0.124) * IN))
assert screws.tapped(motor, across) and abs(deep / IN - 0.75) < 0.01, (across / IN, deep / IN)
# hole points. just the front two on the 5.5W, and a frame on the point bores the same as a click on the face
pts = sorted(library.screw_holes(motor), key=lambda c: c.z)
assert [(round(c.y / IN, 3), round(c.z / IN, 3)) for c in pts] == [(-1.58, 0.124), (-1.58, 0.624)], pts
assert screws.bore(motor, library.hole_frame(motor, pts[0])) == (across, deep)
# 11W just its front two at z 1.768. none of the loops facing into it, none on the case screw holes with a head 0.05 down
big = library.place(doc, steps["Electronics/V5 Smart Motor (276-4840).step"])
doc.recompute()
pts = library.screw_holes(big)
assert sorted((round(c.x / IN, 3), round(c.z / IN, 3)) for c in pts) == [(-0.5, 1.768), (0, 1.768)], pts
# both sides of both flanges on a channel, the inside ones are where boxed channel spacers go
ch = library.place(doc, gen["1x2x1x25 Steel C-Channel"])
doc.recompute()
assert len(library.screw_holes(ch)) == len(library.holes(Part.getShape(ch.LinkedObject))) == 248

# align a channel onto the (3.25, 0.25) top hole on p1, 0.25 off and turned 30. a Revolute joint holds the gap, solving moves nothing
from freecad.vex_workbench import align  # noqa: E402

bar = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
doc.recompute()
first = library.screw_holes(bar)[0]


def where(link, pt, up=""):
    # the spot a click on that hole inside asm gives, up for the groups its in
    path = up + link.Name + "."
    return (link, pt, asm.getSubObject(path, retType=3), (asm, path))


had = len(joints.Group)
target = where(p1, App.Vector(3.25, 0.25, 0.046) * IN)
s = align.align(where(bar, first), target, 0.25 * IN, asm)
align.put(s["moved"], s["frame"], s["parent"], s["at"], 0.25 * IN, 30)
doc.recompute()
(_, at), (_, got) = snap.hole(target), snap.hole(where(bar, first))
z, x = (lambda p: p.Rotation.multVec(App.Vector(0, 0, 1))), (lambda p: p.Rotation.multVec(App.Vector(1, 0, 0)))
d = got.Base - at.Base
assert abs(d.dot(z(at)) - 0.25 * IN) < 1e-9 and d.cross(z(at)).Length < 1e-9, d
assert abs(z(got).dot(z(at)) + 1) < 1e-9 and abs(x(got).dot(x(at)) - math.cos(math.radians(30))) < 1e-9, (z(got), x(got))
new = joints.Group[had:]
assert [j.JointType for j in new] == ["Revolute"] and abs(new[0].Offset2.Base.z - 0.25 * IN) < 1e-9, new
got = moved([p1, p2, bar])
assert not got, got
# it keeps the turn a part already has, to the nearest step: 80 stays 80, or 90 on a 90 or 45 step
h = App.Placement(App.Vector(), align.FLIP.multiply(App.Rotation(App.Vector(0, 0, 1), 80)))
assert [round(align.spun(h, App.Placement(), s), 6) for s in (0, 90, 45)] == [80, 90, 90]
# lined up again somewhere else, its old align joint goes
target = where(p1, App.Vector(2.75, 1.25, 0.046) * IN)
align.align(where(bar, first), target, 0, asm)
doc.recompute()
mine = [j for j in joints.Group if getattr(j, "VexAlign", False) and j.Reference2[0] == bar]
assert len(mine) == 1, mine
got = moved([p1, p2, bar])
assert not got, got
assert (snap.hole(where(bar, first))[1].Base - snap.hole(target)[1].Base).Length < 1e-9
# whole group: a Part in asm with a channel and a plate in it. aligning by the channel moves just the Part, so they keep where they are in it
grp = doc.addObject("App::Part", "Grp")
asm.addObject(grp)
g1 = library.place(doc, gen["1x2x1x5 Steel C-Channel"], grp)
g2 = library.place(doc, gen["5x10 Steel Plate"], grp)
g2.Placement = App.Placement(App.Vector(0, 3 * IN, 0), App.Rotation(0, 0, 90))
doc.recompute()
was = g1.Placement, g2.Placement
inner = where(g1, first, grp.Name + ".")
target = where(p1, App.Vector(4.25, 0.25, 0.046) * IN)
align.align(inner, target, 0, asm, whole=True)
doc.recompute()
(_, at), (_, got) = snap.hole(target), snap.hole(where(g1, first, grp.Name + "."))
assert (got.Base - at.Base).Length < 1e-9 and g1.Placement.isSame(was[0], 1e-9) and g2.Placement.isSame(was[1], 1e-9), got.Base
# and a part in that same group cant be what it lines up on
try:
    align.align(inner, where(g2, App.Vector(0.25, 0.25, 0.046) * IN, grp.Name + "."), 0, asm, True)
    raise AssertionError("lined a group up on itself")
except ValueError:
    pass

App.closeDocument(doc.Name)
print(f"ok, holes {apart:.1e} mm apart, shaft {off:.1e} off the hole axis, screws pick the 0.29, 0.375 and 1.25")
