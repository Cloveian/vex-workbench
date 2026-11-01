# hole frames + Fixed joints, shaft ends, the screw, spacer, align, bend, cut and drill tools, run with: python tests/test_snap.py (needs FreeCAD + vex-step/)
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
doc.recompute()
z, x = (lambda p: p.Rotation.multVec(App.Vector(0, 0, 1))), (lambda p: p.Rotation.multVec(App.Vector(1, 0, 0)))


def turned(spin):
    # hole x on the bar at that spin, after the face to face flip
    a = math.radians(spin)
    return x(at) * math.cos(a) - at.Rotation.multVec(App.Vector(0, 1, 0)) * math.sin(a)


# the joint's presolve keeps the turn it came with, then a turn to 30 goes through the joint too
(_, at), (_, got) = snap.hole(target), snap.hole(where(bar, first))
assert (x(got) - turned(s["spin"])).Length < 1e-9, (s["spin"], x(got))
s["spin"] = 30
align.turn(s, 0.25 * IN)
doc.recompute()
(_, at), (_, got) = snap.hole(target), snap.hole(where(bar, first))
d = got.Base - at.Base
assert abs(d.dot(z(at)) - 0.25 * IN) < 1e-9 and d.cross(z(at)).Length < 1e-9, d
assert abs(z(got).dot(z(at)) + 1) < 1e-9 and (x(got) - turned(30)).Length < 1e-9, (z(got), x(got))
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
# a gap under 0 pushes a shaft end down through the hole, its axis on the hole axis
sh = library.place(doc, gen["2.000 LS Shaft"])
doc.recompute()
target = where(p1, App.Vector(3.75, 0.25, 0.046) * IN)
align.align((sh, App.Vector(), sh.Placement, (sh, "")), target, -0.5 * IN)
at = snap.hole(target)[1]
assert (sh.Placement.Base - (at.Base - z(at) * 0.5 * IN)).Length < 1e-9 and abs(z(sh.Placement).dot(z(at)) - 1) < 1e-9, sh.Placement
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
s = align.align(inner, target, 0, asm, whole=True)
doc.recompute()
(_, at), (_, got) = snap.hole(target), snap.hole(where(g1, first, grp.Name + "."))
assert (got.Base - at.Base).Length < 1e-9 and g1.Placement.isSame(was[0], 1e-9) and g2.Placement.isSame(was[1], 1e-9), got.Base
# turned through its joint the whole group swings, still nothing moves inside it
s["spin"] += 90
align.turn(s, 0)
doc.recompute()
(_, at), (_, got) = snap.hole(target), snap.hole(where(g1, first, grp.Name + "."))
assert (got.Base - at.Base).Length < 1e-9 and (x(got) - turned(s["spin"])).Length < 1e-9, x(got)
assert g1.Placement.isSame(was[0], 1e-9) and g2.Placement.isSame(was[1], 1e-9)
# and a part in that same group cant be what it lines up on
try:
    align.align(inner, where(g2, App.Vector(0.25, 0.25, 0.046) * IN, grp.Name + "."), 0, asm, True)
    raise AssertionError("lined a group up on itself")
except ValueError:
    pass

# bending, a plate folded 90 up across its 2.25 hole row. the short side turns, and the bent leg lands where the hand worked numbers say
from freecad.vex_workbench import metal, partslist, shop  # noqa: E402

sheet = library.place(doc, gen["5x10 Steel Plate"])
flat = library.place(doc, gen["5x10 Steel Plate"])
doc.recompute()
plates = partslist.count(doc)["5x10 Steel Plate"][0]
b = shop.bend(sheet, App.Vector(2.25, 0.25, 0.046) * IN, True, 0, 90)
assert b["side"] == 1 and abs(b["t"] - 0.046 * IN) < 1e-9, b
library.rework(sheet, [b])
s = Part.getShape(sheet.LinkedObject)
t, r = 0.046 * IN, 0.032 * IN
w = (r + 0.44 * t) * math.pi / 2  # flat it eats, on the neutral line
bb = s.BoundBox
# inside of the bend r off the top face, so the leg stands at 2.25 - r and goes up 2.25 - w past it
assert abs(bb.ZMax - (t + r + 2.25 * IN - w)) < 1e-6 and abs(bb.XMin - (2.25 * IN - r - t)) < 1e-6, bb
assert s.isValid() and len(s.Solids) == 1 and abs(s.Volume / Part.getShape(flat.LinkedObject).Volume - 1) < 0.002, s.Volume
# just that copy, and it still counts as a 5x10 plate
assert sheet.LinkedObject != flat.LinkedObject and sheet.LinkedObject.VexName == flat.LinkedObject.VexName == "5x10 Steel Plate"
assert partslist.count(doc)["5x10 Steel Plate"][0] == plates
# a second bend on the leg that now stands square to x, its length is the first bend's face normal. across it is still across
up = max(library.screw_holes(sheet), key=lambda c: c.z)
b2 = shop.bend(sheet, up, True, 0, 90)
assert abs(App.Vector(*b2["d"]).z) < 1e-9 and abs(abs(App.Vector(*b2["d"]).y) - 1) < 1e-9, b2["d"]
library.rework(sheet, [b, b2])
s = Part.getShape(sheet.LinkedObject)
assert s.isValid() and len(s.Solids) == 1 and abs(s.Volume / Part.getShape(flat.LinkedObject).Volume - 1) < 0.004, s.Volume
# a channel bends away from its flanges, folding the web into them gets refused
ch = library.place(doc, gen["1x2x1x10 Steel C-Channel"])
doc.recompute()
web = next(c for c in library.screw_holes(ch) if abs(c.z) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
out = metal.fold(Part.getShape(ch.LinkedObject), shop.bend(ch, web, True, 0, 90))
assert len(out.Solids) == 1, out
try:
    metal.fold(Part.getShape(ch.LinkedObject), shop.bend(ch, web, True, 0, -90))
    raise AssertionError("folded a channel into its own flanges")
except ValueError:
    pass
# folding a flange's tip along the length, the line's plane cuts the other flange too and that one stays put
tip = next(c for c in library.screw_holes(ch) if abs(c.z) < 1e-6 and abs(c.y - 0.25 * IN) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
s = Part.getShape(ch.LinkedObject)
out = metal.fold(s, shop.bend(ch, tip, False, 0, 90))
far = [f for f in out.Faces if f.Surface.TypeId == "Part::GeomPlane" and abs(f.normalAt(0, 0).z - 1) < 1e-6 and f.BoundBox.ZMin > 0.9 * IN]
assert len(out.Solids) == 1 and abs(out.Volume / s.Volume - 1) < 0.005 and far and min(f.BoundBox.YMin for f in far) < 1e-6, out.Volume
# cut to length through the 3.75 hole, the short end goes. the other side kept instead starts there
plate = library.place(doc, gen["5x10 Steel Plate"])
doc.recompute()
s = Part.getShape(plate.LinkedObject)
c = shop.cut(plate, App.Vector(3.75, 0.25, 0.046) * IN, True, 0)
assert abs(metal.cut(s, c).BoundBox.XMax - 3.75 * IN) < 1e-6
assert abs(metal.cut(s, dict(c, side=-c["side"])).BoundBox.XMin - 3.75 * IN) < 1e-6
# cutting a flange tip off along the channel leaves the far flange whole
out = metal.cut(Part.getShape(ch.LinkedObject), shop.cut(ch, tip, False, 0))
top = [f for f in out.Faces if f.Surface.TypeId == "Part::GeomPlane" and abs(f.normalAt(0, 0).z - 1) < 1e-6 and f.BoundBox.ZMin > 0.9 * IN]
low = [f for f in out.Faces if f.BoundBox.ZMax < 0.1 * IN]  # whats left of the clicked flange
assert len(out.Solids) == 1 and top and min(f.BoundBox.YMin for f in top) < 1e-6 and min(f.BoundBox.YMin for f in low) > 0.2 * IN, out.BoundBox
# both flanges off flush with the web (the line slid 0.25 over to its inside face), then the web folds the way the flanges were
flush = library.place(doc, gen["1x2x1x10 Steel C-Channel"])
doc.recompute()
done = []
for z in (0, 1):
    at = next(c for c in library.screw_holes(flush) if abs(c.z - z * IN) < 1e-6 and abs(c.y - 0.25 * IN) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
    s = next(s for s in (shop.cut(flush, at, False, o * IN) for o in (0.25, -0.25)) if abs(s["p"][1] - 0.5 * IN) < 1e-6)
    done.append(s)
    library.rework(flush, done)
web = next(c for c in library.screw_holes(flush) if abs(c.y - 0.546 * IN) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
assert len(metal.fold(Part.getShape(flush.LinkedObject), shop.bend(flush, web, True, 0, -90)).Solids) == 1
# taking the web side off instead would leave the two flanges as two pieces, that gets refused
try:
    metal.cut(Part.getShape(ch.LinkedObject), dict(done[0], side=-done[0]["side"]))
    raise AssertionError("cut a channel into two")
except ValueError as e:
    assert "more than one piece" in str(e), e
# drilling: a click at (2.07, 0.29) snaps 0.25 steps off the nearest hole to (2, 0.25), between two holes. shift drills it right there
spot = App.Vector(2.07, 0.29, 0.046) * IN
h = shop.drill(plate, spot, 0.17 * IN)
assert (App.Vector(*h["c"]) - App.Vector(2, 0.25, 0.046) * IN).Length < 1e-6 and abs(h["t"] - 0.046 * IN) < 1e-6, h
assert (App.Vector(*shop.drill(plate, spot, 0.17 * IN, False)["c"]) - spot).Length < 1e-6
library.rework(plate, [h])
new = [w for w, c, _ in library.holes(Part.getShape(plate.LinkedObject)) if (c - App.Vector(*h["c"])).Length < 1e-6]
assert new and library.screwable(new[0]), new

App.closeDocument(doc.Name)
print(f"ok, holes {apart:.1e} mm apart, shaft {off:.1e} off the hole axis, screws pick the 0.29, 0.375 and 1.25")
