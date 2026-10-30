# hole frames + Fixed joints, shaft ends, and the screw tool (plain, inside face, linked sub-assembly), run with: python tests/test_snap.py (needs FreeCAD)
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401
import FreeCAD as App  # noqa: E402
import JointObject  # noqa: E402  Assembly workbench, works headless
import Part  # noqa: E402

from freecad.vex_workbench import library  # noqa: E402

IN = 25.4
doc = App.newDocument("snaptest")
asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
asm.Type = "Assembly"
joints = asm.newObject("Assembly::JointGroup", "Joints")
_, gen, _ = library.index()
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
nylock = screws.nuts()["#8-32 Nylock Nut"]
had = len(joints.Group)
sc, nut = screws.fasten(doc, head, tail, "star-screw", nylock, asm)
assert sc.Label == "0.290 Torx (Star) Screw (8-32, Steel)", sc.Label
# a Fixed joint each, and solving moves nothing
new = joints.Group[had:]
assert [(j.JointType, j.Reference1[0], j.Reference2[0]) for j in new] == [("Fixed", p1, sc), ("Fixed", p2, nut)], new


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
sc, _ = screws.fasten(doc, head, tail, "hex-screw", nylock)
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
sc, nut = screws.fasten(doc, head, inner, "star-screw", nylock, asm)
new = joints.Group[had:]
assert [j.Reference1[0] for j in new] == [p1, sub] and new[1].Reference1[1][0].startswith(p3.Name + "."), [j.Reference1 for j in new]
got = moved([sc, nut])
assert not got, got
assert local(nut) == [1.25, 0.25, -0.2391, -0.046], local(nut)

App.closeDocument(doc.Name)
print(f"ok, holes {apart:.1e} mm apart, shaft {off:.1e} off the hole axis, screws pick the 0.29 and 0.375")
