# hole frames + Fixed joints, shaft ends, the screw, spacer, align, bend, cut and drill tools, run with: python tests/test_snap.py (needs FreeCAD)
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401
freecad.__path__.insert(0, str(ROOT / "freecad"))
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

from freecad.vex_workbench import shop  # noqa: E402


def fake(refs):
    # joint lookalike outside asm, the solver doesnt see it
    odd = doc.addObject("App::FeaturePython", "Odd")
    odd.addProperty("App::PropertyString", "JointType")
    for prop in ("Reference1", "Reference2"):
        odd.addProperty("App::PropertyXLinkSubHidden", prop)
        setattr(odd, prop, refs)
    return odd


# joints on a face of something else and with nothing picked yet get skipped
box = doc.addObject("Part::Box", "Box")
for refs in ([box, ["Face1", "Vertex1"]], None):
    fake(refs)
# drilling p1 somewhere else keeps the screw's joint on it, the frame comes over to the drilled source. a bare Frame on hole one too
bare = library.hole_frame(p1, App.Vector(3.26, 0.26, 0.046) * IN).Placement
library.rework(p1, [shop.drill(p1, App.Vector(3.5, 0.5, 0.046) * IN, 0.25 * IN, False)])
doc.recompute()
hole = new[0].Reference1[1][0]
assert p1.LinkedObject.VexSteps and p1.LinkedObject.getObject(hole.rstrip(".")) in p1.LinkedObject.Group, hole
assert any(o.TypeId == "App::LocalCoordinateSystem" and o.Placement.isSame(bare, 1e-6) for o in p1.LinkedObject.Group), bare
got = moved([p1, p2, sc, nut])
assert not got and local(nut) == [1.25, 0.25, -0.2391, -0.046], (got, local(nut))
# and on one element of a link array
row = library.place(doc, gen["5x10 Steel Plate"])
row.ElementCount = 3
doc.recompute()
f = library.frame(row, App.Placement(App.Vector(1.25, 0.25, 0.046) * IN, App.Rotation()))
odd = fake([row, [f"1.{f.Name}.", f"1.{f.Name}."]])
library.rework(row, [shop.drill(row, App.Vector(3.5, 0.5, 0.046) * IN, 0.25 * IN, False)])
_, name = odd.Reference1[1][0].rstrip(".").split(".")
assert name != f.Name and row.LinkedObject.getObject(name) in row.LinkedObject.Group, odd.Reference1
# then longer, drilled hole and joint both come along
row.Holes = "15"
library.refit(row)
_, again = odd.Reference1[1][0].rstrip(".").split(".")
assert library.steps(row) and again != name and row.LinkedObject.getObject(again) in row.LinkedObject.Group, odd.Reference1
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
# and through the sub-assembly link
library.rework(p3, [shop.drill(p3, App.Vector(3.5, 0.5, 0) * IN, 0.25 * IN, False)])
doc.recompute()
_, frame = new[1].Reference1[1][0].rstrip(".").split(".")
assert p3.LinkedObject.VexSteps and p3.LinkedObject.getObject(frame) in p3.LinkedObject.Group, new[1].Reference1
got = moved([sc, nut])
assert not got and local(nut) == [1.25, 0.25, -0.2391, -0.046], (got, local(nut))
# a plain size change too, p2 to 15 holes keeps its nut joint. a bare frame stays on the 5x10 source, the 5x15 one is shared
j2 = next(j for j in joints.Group if getattr(j, "JointType", "") == "Revolute" and j.Reference1[0] == p2)
bare = library.hole_frame(p2, App.Vector(3.26, 0.26, 0) * IN).Placement
p2.Holes = "15"
library.refit(p2)  # no observer in here
doc.recompute()
assert not any(o.TypeId == "App::LocalCoordinateSystem" and o.Placement.isSame(bare, 1e-6) for o in p2.LinkedObject.Group), bare
assert p2.LinkedObject.getObject(j2.Reference1[1][0].rstrip(".")) in p2.LinkedObject.Group, j2.Reference1
n2 = j2.Reference2[0]
got = moved([n2])
assert not got and local(n2) == [1.25, 0.25, -0.2391, -0.046], (got, local(n2))

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
# 1/64 and under is touching, so is anything under the 0.016 washer
got = spacers.pick(0.0158 * IN, 0.5)
assert got == [], got
got = [p["name"] for p in spacers.pick(0.016 * IN, 0.5)]
assert got == ["Washer, 0.375 OD, 0.016 (Nylon)"], got
# a shorter spacer keeps its joint at the bottom end, the Top one up to the washer moved. back to 0.875 fixes that one
seat = next(j for j in joints.Group if getattr(j, "JointType", "") == "Revolute" and j.Reference2[0] == put[0])
for length in ("0.5", "0.875"):
    put[0].Length = length
    library.refit(put[0])  # no observer in here
    doc.recompute()
    assert put[0].LinkedObject.getObject(seat.Reference2[1][0].rstrip(".")) in put[0].LinkedObject.Group, (length, seat.Reference2)
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
# hole points. the front two on the 5.5W and its output shaft hole, and a frame on the point bores the same as a click on the face
pts = sorted(library.hole_dots(motor), key=lambda c: c.z)
assert [(round(c.y / IN, 3), round(c.z / IN, 3)) for c in pts] == [(-0.797, -0.376), (-1.58, 0.124), (-1.58, 0.624)], pts
assert screws.bore(motor, library.hole_frame(motor, pts[1])) == (across, deep)
# a gear's shaft hole, both faces
gear = library.place(doc, steps["Motion/Gears/Low Strength/36T Gear (276-2169-002).step"])
doc.recompute()
assert sorted(round(c.z / IN, 3) for c in library.hole_dots(gear)) == [-0.188, 0.188], library.hole_dots(gear)
# the 11W, its front two at z 1.768 and the output socket 0.5 down its recess. none of the loops facing into it, none on the case screw holes with a head 0.05 down
big = library.place(doc, steps["Electronics/V5 Smart Motor (276-4840).step"])
doc.recompute()
pts = library.hole_dots(big)
assert sorted((round(c.x / IN, 3), round(c.z / IN, 3)) for c in pts) == [(-0.5, 1.768), (0, 1.768), (0.5, 1.264)], pts
# both sides of both flanges on a channel, the inside ones are where boxed channel spacers go
ch = library.place(doc, gen["1x2x1x25 Steel C-Channel"])
doc.recompute()
assert len(library.hole_dots(ch)) == len(library.holes(Part.getShape(ch.LinkedObject))) == 248

# align a channel onto the (3.25, 0.25) top hole on p1, 0.25 off and turned 30. a Revolute joint holds the gap, solving moves nothing
from freecad.vex_workbench import align  # noqa: E402

bar = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
doc.recompute()
first = library.hole_dots(bar)[0]


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
s = align.align(where(bar, first), target, 0, asm)
doc.recompute()
mine = [j for j in joints.Group if getattr(j, "VexAlign", False) and j.Reference2[0] == bar]
assert len(mine) == 1, mine
got = moved([p1, p2, bar])
assert not got, got
assert (snap.hole(where(bar, first))[1].Base - snap.hole(target)[1].Base).Length < 1e-9

# slide from there along to (4.75, 1.25). a Slider in place of the Revolute, stops on both holes
for wrong in (target, where(p1, App.Vector(4.75, 1.25, 0) * IN), where(p2, App.Vector(0.25, 0.25, 0.046) * IN)):
    try:
        align.slide(s, wrong)
        raise AssertionError(wrong)
    except ValueError:
        pass
end = where(p1, App.Vector(4.75, 1.25, 0.046) * IN)
k = align.slide(s, end)
doc.recompute()
mine = [j for j in joints.Group if getattr(j, "VexAlign", False) and j.Reference2[0] == bar]
assert mine == [k] and k.JointType == "Slider", mine
got = moved([p1, p2, bar])
assert not got, got
a, b = snap.hole(target)[1].Base, snap.hole(end)[1].Base
up = (b - a).normalize()


def bar_at(nudge):
    # bar pushed nudge mm up the rail and solved, how far up its hole is after
    bar.Placement = App.Placement(bar.Placement.Base + up * nudge, bar.Placement.Rotation)
    assert asm.solve() == 0
    doc.recompute()
    h = snap.hole(where(bar, first))[1].Base - a
    assert h.cross(up).Length < 1e-6, h
    return h.dot(up)


assert abs(bar_at(1 * IN) - 1 * IN) < 1e-6 and abs(bar_at(-0.5 * IN) - 0.5 * IN) < 1e-6
assert k.EnableLengthMin and k.EnableLengthMax and abs(k.LengthMax.Value - 2 * IN) < 1e-9, k.LengthMax
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
up = max(library.hole_dots(sheet), key=lambda c: c.z)
b2 = shop.bend(sheet, up, True, 0, 90)
assert abs(App.Vector(*b2["d"]).z) < 1e-9 and abs(abs(App.Vector(*b2["d"]).y) - 1) < 1e-9, b2["d"]
library.rework(sheet, [b, b2])
s = Part.getShape(sheet.LinkedObject)
assert s.isValid() and len(s.Solids) == 1 and abs(s.Volume / Part.getShape(flat.LinkedObject).Volume - 1) < 0.004, s.Volume
# a joint on a hole on the side that turns goes round with it, and again when that bend gets redone at 45
leg = library.place(doc, gen["5x10 Steel Plate"], asm)
JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), leg)
pin = library.place(doc, gen["2.000 LS Shaft"], asm)
doc.recompute()
f = library.frame(leg, App.Placement(App.Vector(1.25, 0.25, 0.046) * IN, App.Rotation()))
fs = library.hole_frame(pin, App.Vector(0.01, 0.02, 0.1) * IN)
j = snap.revolute(asm, [leg, [f"{f.Name}.", f"{f.Name}."]], [pin, [f"{fs.Name}.", f"{fs.Name}."]])
b = shop.bend(leg, App.Vector(2.25, 0.25, 0.046) * IN, True, 0, 90)
for step in (b, dict(b, angle=45)):
    library.rework(leg, [step])
    g = leg.LinkedObject.getObject(j.Reference1[1][0].rstrip("."))
    assert g in leg.LinkedObject.Group and g.Placement.isSame(metal.turned(step).multiply(f.Placement), 1e-6), (step["angle"], j.Reference1)
    assert asm.solve() == 0
    doc.recompute()
    assert (pin.Placement.Base - leg.Placement.multVec(g.Placement.Base)).Length < 1e-6, (step["angle"], pin.Placement.Base / IN)
# a joint made with freecad's own tool, straight on the bottom face and the corner at 0. bent the corner goes round with its face, drilled the face is a new one in the same spot
sheet = library.place(doc, gen["5x10 Steel Plate"], asm)
doc.recompute()
sol = next(o for o in sheet.LinkedObject.Group if o.TypeId == "Part::Feature")
faces, points = sol.Shape.Faces, [v.Point for v in sol.Shape.Vertexes]  # out here, sol.Shape.Faces inside the key is ~6 s
bottom = min(range(len(faces)), key=lambda i: (-round(faces[i].Area, 3), faces[i].CenterOfGravity.z)) + 1
corner = min(range(len(points)), key=lambda i: points[i].Length) + 1  # rounded corners
at = points[corner - 1]
odd = fake([asm, [f"{sheet.Name}.{sol.Name}.Face{bottom}", f"{sheet.Name}.{sol.Name}.Vertex{corner}"]])
b = shop.bend(sheet, App.Vector(2.25, 0.25, 0.046) * IN, True, 0, 90)
library.rework(sheet, [b])
t = metal.turned(b)
face, v = (asm.getSubObject(s) for s in odd.Reference1[1])
assert (v.Point - t.multVec(at)).Length < 1e-6 and face.distToShape(v)[0] < 1e-6, odd.Reference1
assert (face.normalAt(0, 0) - t.Rotation.multVec(App.Vector(0, 0, -1))).Length < 1e-6, (odd.Reference1, face.normalAt(0, 0))
area = face.Area
library.rework(sheet, [b, shop.drill(sheet, t.multVec(App.Vector(1, 1, 0.046) * IN), 0.25 * IN, False)])
face, v = (asm.getSubObject(s) for s in odd.Reference1[1])
assert (v.Point - t.multVec(at)).Length < 1e-6 and 0 < area - face.Area < 0.25**2 * math.pi / 4 * IN**2 + 1e-6, (odd.Reference1, area - face.Area)
# every kind of step mirrored and done on the mirrored plate is the mirror of it done on the plate. a slanted plane, nothing lines up by luck
from freecad.vex_workbench import duplicate  # noqa: E402

m = duplicate.reflection(App.Vector(1.3, -0.7, 2.1) * IN, App.Vector(1, 2, 0.5))
plain = Part.getShape(flat.LinkedObject)
square = Part.Face(Part.makePolygon([App.Vector(x, y, 0.046) * IN for x, y in ((3.1, 1.1), (3.9, 1.1), (3.9, 1.4), (3.1, 1.4), (3.1, 1.1))]))
for step in (shop.bend(flat, App.Vector(2.25, 0.25, 0.046) * IN, True, 0.25, -60), shop.cut(flat, App.Vector(4.25, 0.25, 0.046) * IN, True, 0),
             shop.slot(flat, App.Vector(0.5, 1, 0.046) * IN, App.Vector(1.5, 1, 0.046) * IN, 0.04 * IN), shop.drill(flat, App.Vector(3.5, 0.25, 0.046) * IN, 0.17 * IN, False),
             {"do": "sketch", "sketch": "Sketch", "face": square.exportBrepToString(), "n": [0, 0, 1], "t": 0.046 * IN}):
    want = metal.work(plain, step).transformed(m)
    got = metal.work(plain.transformed(m), metal.mirrored(step, m))
    far = max(got.distToShape(v)[0] for v in want.Vertexes[::7])
    assert far < 1e-6 and abs(got.Volume - want.Volume) < 1e-6 and "sketch" not in metal.mirrored(step, m), (step["do"], far, got.Volume - want.Volume)
# a channel bends away from its flanges, folding the web into them gets refused
ch = library.place(doc, gen["1x2x1x10 Steel C-Channel"])
doc.recompute()
web = next(c for c in library.hole_dots(ch) if abs(c.z) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
out = metal.fold(Part.getShape(ch.LinkedObject), shop.bend(ch, web, True, 0, 90))
assert len(out.Solids) == 1, out
try:
    metal.fold(Part.getShape(ch.LinkedObject), shop.bend(ch, web, True, 0, -90))
    raise AssertionError("folded a channel into its own flanges")
except ValueError:
    pass
# folding a flange's tip along the length, the line's plane cuts the other flange too and that one stays put
tip = next(c for c in library.hole_dots(ch) if abs(c.z) < 1e-6 and abs(c.y - 0.25 * IN) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
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
    at = next(c for c in library.hole_dots(flush) if abs(c.z - z * IN) < 1e-6 and abs(c.y - 0.25 * IN) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
    s = next(s for s in (shop.cut(flush, at, False, o * IN) for o in (0.25, -0.25)) if abs(s["p"][1] - 0.5 * IN) < 1e-6)
    done.append(s)
    library.rework(flush, done)
web = next(c for c in library.hole_dots(flush) if abs(c.y - 0.546 * IN) < 1e-6 and abs(c.x - 2.25 * IN) < 1e-6)
assert len(metal.fold(Part.getShape(flush.LinkedObject), shop.bend(flush, web, True, 0, -90)).Solids) == 1
# taking the web side off instead would leave the two flanges as two pieces, that gets refused
try:
    metal.cut(Part.getShape(ch.LinkedObject), dict(done[0], side=-done[0]["side"]))
    raise AssertionError("cut a channel into two")
except ValueError as e:
    assert "more than one piece" in str(e), e
# drilling: a click at (2.07, 0.29) snaps 0.25 steps off the first hole to (2, 0.25), between two holes. shift drills it right there
spot = App.Vector(2.07, 0.29, 0.046) * IN
h = shop.drill(plate, spot, 0.17 * IN)
assert (App.Vector(*h["c"]) - App.Vector(2, 0.25, 0.046) * IN).Length < 1e-6 and abs(h["t"] - 0.046 * IN) < 1e-6, h
assert (App.Vector(*shop.drill(plate, spot, 0.17 * IN, False)["c"]) - spot).Length < 1e-6
# right on a hole's center (its dot) it still drills down through the face, not into the hole's wall
assert App.Vector(*shop.drill(plate, App.Vector(2.25, 0.25, 0.046) * IN, 0.25 * IN, False)["n"]).z > 1 - 1e-6
library.rework(plate, [h])
new = [w for w, c, _ in library.holes(Part.getShape(plate.LinkedObject)) if (c - App.Vector(*h["c"])).Length < 1e-6]
assert new and library.screwable(new[0]), new
# a 1/4 one isnt an 8-32 but still gets dots, both sides
wide = shop.drill(plate, App.Vector(3.5, 0.5, 0.046) * IN, 0.25 * IN, False)
library.rework(plate, [h, wide])
dots = [c for c in library.hole_dots(plate) if (c - App.Vector(3.5, 0.5, 0) * IN).Length < 0.05 * IN]
assert len(dots) == 2, dots
# 0.3 doesnt go into the pitch, the grid on both sides still lines up. a drill in front of the first hole doesnt move it
grids = []
for done in ([h, wide], [h, wide, shop.drill(plate, App.Vector(0.07, 0.75, 0.046) * IN, 0.12 * IN, False)]):
    library.rework(plate, done)
    spots = shop.grid_spots(plate, 0.3 * IN)
    grids.append([{(round(p.x, 4), round(p.y, 4)) for p in spots if abs(p.z - z) < 1e-6} for z in (0.046 * IN, 0)])
assert grids[0][0] and grids[0][0] == grids[0][1] == grids[1][0] == grids[1][1], [len(s) for g in grids for s in g]
# an LS gear drilled out to spin on a screw, a click near the middle snaps onto it. straight through, the bore has steps inside that a wall would stop at
gear = library.place(doc, steps["Motion/Gears/Low Strength/12T Gear (276-2169-001).step"])
doc.recompute()
shop.drillable(gear)
d = shop.drill(gear, App.Vector(0.03, -0.02, 0.1875) * IN, 0.18 * IN)
assert App.Vector(*d["c"]).isEqual(App.Vector(0, 0, 0.1875) * IN, 1e-6) and abs(d["t"] - 0.375 * IN) < 1e-6, d
library.rework(gear, [d])
left = Part.getShape(gear.LinkedObject).common(Part.makeCylinder(0.0899 * IN, IN, App.Vector(0, 0, -0.5) * IN))
assert left.Volume < 1e-9, left.Volume
dots = [c for c in library.hole_dots(gear) if c.x**2 + c.y**2 < 1e-9]
assert len(dots) == 2 and gear.Label == "12T Gear", (dots, gear.Label)
try:
    shop.drillable(sc)
    raise AssertionError("drilled a screw")
except ValueError:
    pass

# a bend centered on its line sits half the flat it eats back from where one next to the line does, and a 0 radius (vice and hammer) still folds
flat = library.place(doc, gen["5x10 Steel Plate"])
doc.recompute()
shape = Part.getShape(flat.LinkedObject)
at = App.Vector(2.25, 0.25, 0.046) * IN
next_to, centered, sharp = (metal.fold(shape, shop.bend(flat, at, True, 0, 90, r, c)) for r, c in ((None, False), (None, True), (0, False)))
s = shop.bend(flat, at, True, 0, 90)
w = (s["r"] + s["k"] * s["t"]) * math.pi / 2
a, b = next_to.optimalBoundingBox(), centered.optimalBoundingBox()
assert sorted(round(abs(d) / w, 6) for d in (a.XMin - b.XMin, a.XMax - b.XMax)) == [0, 0.5], (a, b, w)
assert all(len(x.Solids) == 1 and x.isValid() for x in (next_to, centered, sharp))
assert "centered" not in s and shop.bend(flat, at, True, 0, 90, centered=True)["centered"]

# slots: one between two holes is just a slit. edge dots on the grid, three cuts in off the edge drop a 1x1 notch out
kerf = 0.04 * IN
s = shop.slot(flat, App.Vector(1.25, 0.25, 0.046) * IN, App.Vector(1.75, 0.25, 0.046) * IN, kerf)
out = metal.slot(shape, s)
assert len(out.Solids) == 1 and shape.Volume - out.Volume > 1 and "keep" not in s and s["out"] == [False, False], s
# whole and half inches have a count notch, its dot is down at the tip
edges = shop.edge_spots(flat, 0.25 * IN)
assert not [p for p in edges if 0.1 * IN < p.y < 2.4 * IN and 0.1 * IN < p.x < 4.9 * IN], len(edges)
start = [min((p for p in edges if abs(p.x - x * IN) < 1e-6 and p.z > 0.04 * IN), key=lambda p: p.y) for x in (2, 3)]
assert all(0 < p.y < 0.1 * IN for p in start), start
done = [shop.slot(flat, p, App.Vector(p.x, 1 * IN, 0.046 * IN), kerf) for p in start]
assert all(d["out"] == [True, False] for d in done), done
library.rework(flat, done)
done.append(shop.slot(flat, App.Vector(2, 1, 0.046) * IN, App.Vector(3, 1, 0.046) * IN, kerf))
library.rework(flat, done)
out = Part.getShape(flat.LinkedObject)
assert len(out.Solids) == 1 and not out.isInside(App.Vector(2.5, 0.1, 0.02) * IN, 1e-6, True) and out.isInside(App.Vector(2.5, 1.1, 0.02) * IN, 1e-6, True)
# edge to edge is cut to length, the long side stays, or the short one
s = shop.slot(flat, App.Vector(3.75, 0, 0.046) * IN, App.Vector(3.75, 2.5, 0.046) * IN, kerf)
assert abs(metal.slot(out, s).BoundBox.XMax - 3.75 * IN + kerf / 2) < 1e-6, metal.slot(out, s).BoundBox
shop.keeping(out, s, -1)
assert abs(metal.slot(out, s).BoundBox.XMin - 3.75 * IN - kerf / 2) < 1e-6, metal.slot(out, s).BoundBox
# a sketched ring cuts out a disc, the island in the middle goes too
ring = library.place(doc, gen["5x10 Steel Plate"])
doc.recompute()
sk = shop.sketch_on(ring, App.Vector(2.25, 1.25, 0.046) * IN)
for r in (0.4, 0.6):
    sk.addGeometry(Part.Circle(App.Vector(), App.Vector(0, 0, 1), r * IN))
doc.recompute()
assert shop.recut(sk) and "keep" in library.steps(ring)[0], library.steps(ring)
out = Part.getShape(ring.LinkedObject)
assert len(out.Solids) == 1 and not out.isInside(App.Vector(2.55, 1.25, 0.02) * IN, 1e-6, True) and out.isInside(App.Vector(2.25, 2.1, 0.02) * IN, 1e-6, True)
# nothing closed left drops it
sk.delGeometries([0, 1])
doc.recompute()
assert not shop.recut(sk) and library.steps(ring) == []

# a 1x2x1 c-channel inside a steel U-channel: the U's flange inside dots sit out in the 0.025 gap, outside ones stay on the metal
u = library.place(doc, gen["2x2x2x10 Steel U-Channel"])
ch = library.place(doc, gen["1x2x1x10 Steel C-Channel"])
ch.Placement = App.Placement(App.Vector(0, 5, 3) * IN, App.Rotation())
doc.recompute()
side = (29 / 25.4 - 2 * 0.046 - 1) / 2
zs = sorted({round(c.z / IN, 4) for c in library.hole_dots(u) if c.x < 0.3 * IN and abs(c.y / IN - 0.204) < 1e-3})
assert zs == [0, round(0.046 + side, 4), round(29 / 25.4 - 0.046 - side, 4), round(29 / 25.4, 4)], zs
inner = App.Vector(0.25, 0.204, 0.046) * IN
assert abs(library.hole_frame(u, inner).Placement.Base.z / IN - 0.046 - side) < 1e-9
# lined up on that hole the c-channel sits square in the middle, the same gap both sides
align.align((ch, App.Vector(0.26, 0.26, 0) * IN, ch.Placement, (ch, "")), (u, inner, u.Placement, (u, "")), 0)
doc.recompute()
b = ch.Shape.optimalBoundingBox()
assert abs(b.ZMin / IN - 0.046 - side) < 1e-6 and abs((29 / 25.4 - 0.046) - b.ZMax / IN - side) < 1e-6, (b.ZMin / IN, b.ZMax / IN)
# a screw ending on that frame out in the gap still finds its hole, deep is the gap and the flange
across, deep = screws.bore(u, library.hole_frame(u, inner))
assert abs(across / IN - 0.182) < 1e-3 and abs(deep / IN - 0.046 - side) < 1e-4, (across / IN, deep / IN)

# duplicate brings the joints with both ends on copied parts. mirrored or turned the copies already sit where those joints say, a solve moves nothing
q1 = library.place(doc, gen["5x10 Steel Plate"], asm)
q2 = library.place(doc, gen["5x10 Steel Plate"], asm)
q1.Placement = App.Placement(App.Vector(20, 0, 0) * IN, App.Rotation(10, 0, 0))
q2.Placement = q1.Placement.multiply(App.Placement(App.Vector(-IN, 0, -0.046 * IN), App.Rotation()))
bar2 = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
for q in (q1, q2):
    JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), q)
doc.recompute()
qs, qn, _ = screws.fasten(doc, where(q1, App.Vector(1.27, 0.24, 0.046) * IN), where(q2, App.Vector(2.26, 0.26, 0) * IN), "star-screw", nylock, asm)
jb = align.align(where(bar2, library.hole_dots(bar2)[0]), where(q1, App.Vector(3.25, 0.25, 0.046) * IN), 0.25 * IN, asm)["joint"]
jb.Offset2 = snap.offset(0.25 * IN, 30)
assert asm.solve() == 0
doc.recompute()
for how in ({"mirror": duplicate.reflection(App.Vector(17, 0, 0) * IN, App.Vector(1, 0.3, 0))}, {"turn": App.Placement(App.Vector(0, 30, 0), App.Rotation(App.Vector(0, 0, 1), 70))}):
    before = set(doc.Objects)
    aligned = sum(getattr(j, "VexAlign", False) for j in joints.Group)
    assert duplicate.duplicate([q1, q2, qs, qn, bar2], **how)[2:] == (3, 0), how
    new = [o for o in doc.Objects if o not in before and duplicate.vex(o)]
    for q in new[:2]:
        JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), q)
    got = moved(new + [qs, qn, bar2])
    assert not got and sum(getattr(j, "VexAlign", False) for j in joints.Group) == aligned + 1, (list(how), got)
# a motor only nearly mirrors, its joints come along where theres a hole for them, and the copies sit where those joints say
q3 = library.place(doc, gen["5x10 Steel Plate"], asm)
q3.Placement = App.Placement(App.Vector(30, 0, 0) * IN, App.Rotation())
mo = library.place(doc, steps["Electronics/V5 Smart Motor (276-4840).step"], asm)
JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), q3)
doc.recompute()
dot = next(c for c in library.hole_dots(mo) if abs(c.x + 0.5 * IN) < 1e-6)
align.align(where(mo, dot), where(q3, App.Vector(1.25, 0.25, 0.046) * IN), 0, asm)
doc.recompute()
ms, *_ = screws.fasten(doc, where(q3, App.Vector(1.26, 0.26, 0) * IN), where(mo, dot), "star-screw", None, asm)
before = set(doc.Objects)
# the Align one onto the motor's hole and the screw's in the plate (into a thread its just the one)
assert duplicate.duplicate([q3, mo, ms], mirror=duplicate.reflection(App.Vector(28, 0, 0) * IN, App.Vector(1, 0, 0))) == ([], [mo.Label], 2, 0)
new = [o for o in doc.Objects if o not in before and duplicate.vex(o)]
JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), new[0])  # just the plate, the motor hangs off its Align
got = moved(new)
assert not got, got
# a bar on a plate that stays put, mirrored across the plate's middle, gets jointed to the plate's hole on the other side. turned too
q4 = library.place(doc, gen["5x10 Steel Plate"], asm)
q4.Placement = App.Placement(App.Vector(40, 0, 0) * IN, App.Rotation())
b4 = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), q4)
doc.recompute()
align.align(where(b4, library.hole_dots(b4)[0]), where(q4, App.Vector(1.25, 0.25, 0.046) * IN), 0.125 * IN, asm)
doc.recompute()
for how, hole in (({"mirror": duplicate.reflection(App.Vector(42.5, 0, 0) * IN, App.Vector(1, 0, 0))}, (3.75, 0.25)),
                  ({"turn": App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 180), App.Vector(42.5, 1.25, 0) * IN)}, (3.75, 2.25))):
    before = set(doc.Objects)
    assert duplicate.duplicate([b4], **how) == ([], [], 1, 0), how
    cp = next(o for o in doc.Objects if o not in before and duplicate.vex(o))
    k = joints.Group[-1]
    on = q4.LinkedObject.getObject(k.Reference1[1][0].rstrip("."))
    assert k.Reference1[0] == q4 and k.Reference2[0] == cp and (on.Placement.Base - App.Vector(*hole, 0.046) * IN).Length < 1e-6, (list(how), on.Placement.Base / IN)
    got = moved([cp])
    assert not got, (list(how), got)
# vex's 25 hole chassis rail has its holes 0.002 off the middle, mirrored across the middle a channel on the end hole still gets the far end one, and a solve only nudges it
rail = library.place(doc, steps["Structure/Steel/2x1x25 Steel Chassis Rail (275-1145).step"], asm)
rail.Placement = App.Placement(App.Vector(0, 20, 0) * IN, App.Rotation())
b5 = library.place(doc, gen["1x2x1x5 Steel C-Channel"], asm)
JointObject.GroundedJoint(joints.newObject("App::FeaturePython", "Ground"), rail)
doc.recompute()
align.align(where(b5, library.hole_dots(b5)[0]), where(rail, App.Vector(2.028, 0.046, -2.098) * IN), 0, asm)
doc.recompute()
b = Part.getShape(rail.LinkedObject).BoundBox
before = set(doc.Objects)
assert duplicate.duplicate([b5], mirror=duplicate.reflection(App.Vector(b.Center.x, 0, 0), App.Vector(1, 0, 0))) == ([], [], 1, 0)
cp = next(o for o in doc.Objects if o not in before and duplicate.vex(o))
k = joints.Group[-1]
on = rail.LinkedObject.getObject(k.Reference1[1][0].rstrip("."))
assert k.Reference1[0] == rail and (on.Placement.Base - App.Vector(-9.972, 0.046, -2.098) * IN).Length < 0.001 * IN, on.Placement.Base / IN
was = cp.Placement
assert asm.solve() == 0
assert (cp.Placement.Base - was.Base).Length < 0.01 * IN, (cp.Placement.Base - was.Base) / IN
# a whole assembly copied, its joints go in the copy's own joint group
import UtilsAssembly  # noqa: E402

side =doc.addObject("Assembly::AssemblyObject", "Side2")
side.Type = "Assembly"
side.newObject("Assembly::JointGroup", "Joints")
r1, r2 = (library.place(doc, gen["5x10 Steel Plate"], side) for _ in range(2))
r2.Placement = App.Placement(App.Vector(-IN, 0, -0.046 * IN), App.Rotation())
doc.recompute()


def on(r, pt):
    return r, pt, r.Placement, (side, r.Name + ".")


screws.fasten(doc, on(r1, App.Vector(1.27, 0.24, 0.046) * IN), on(r2, App.Vector(2.26, 0.26, 0) * IN), "star-screw", nylock, side)
before = set(doc.Objects)
assert duplicate.duplicate([side], turn=App.Placement(App.Vector(0, 0, 3 * IN), App.Rotation()))[2:] == (2, 0)
twin = next(o for o in doc.Objects if o not in before and o.TypeId == "Assembly::AssemblyObject")
mine = [j for j in UtilsAssembly.getJointGroup(twin).Group if hasattr(j, "Reference1")]
assert len(mine) == 2 and all(j.Reference1[0] in twin.Group and j.Reference2[0] in twin.Group for j in mine), mine

App.closeDocument(doc.Name)
print(f"ok, holes {apart:.1e} mm apart, shaft {off:.1e} off the hole axis, screws pick the 0.29, 0.375 and 1.25")
