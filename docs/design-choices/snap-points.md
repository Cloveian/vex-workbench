# Snap points
what a joint attaches to, and how exact it is

## Identify
this is the part that makes it *not* protobot. two holes jointed together have to land on each other exactly, every time

### Relevant constraints/nice to haves:
- Assembly joints take an `App::LocalCoordinateSystem` as the reference, or a face / edge / vertex
- A square hole has no center to click. its edges give edge midpoints, which are 0.091 off center
- Every frame is ~7 objects in the tree (origin point, 3 axes, 3 planes)
- Step parts come in with no frames at all

### What has to be managed/controlled
- Where frames go (hole center, which face, which way is out)
- When they get made
- How big the parts are vs how big vex's files say they are
- Clearance between a hole and what goes through it

### Gates

1. exact hole centers
2. doesnt make FreeCAD crawl on a full robot

## Brainstorm

**Sizes:**

Vex's steps aren't always nominal. the 2, 3 and 4" HS shafts are 1 mm short (the 2" is 1.9606, the 24" isnt), and the aluminum c-channels flare out a bit (1x5x1x35 is 2.545 wide not 2.5). the steel ones are clean. so do parts match the files or the numbers on the product page?

**When frames get made:**

- **A - every hole, up front**
	a 1x5x1x35 c-channel is 245 holes, both faces = 490 frames = ~3,400 objects. 30 channels in a robot is ~100k objects, and FreeCAD gets *so* slow way before that
- **B - on click**
	click a hole (an edge or the face around it), a frame shows up at its exact center pointing out of the face, joint to it. the screw tool makes its own the same way

**Gate cuts:**

- A fails 2

## Select

only B survives, so not much of a table


### Decision
- **Nominal sizes.** parts are the numbers, not vex's file quirks. the steps are fixtures, close enough to check against, not the truth
- **Zero tolerance at the snaps.** frames sit on the exact nominal hole center, nothing baked in, so exact things are easy to build. real clearance (a 0.176 shoulder in a 0.182 hole) stays in the solids, the joint just centers it
- **Joints center** whatever goes through the hole
- **Hole finding on import** for step parts, the 0.182 square holes and 8-32 round ones, so motors and gears snap the same way
- **Frames on click** (B). not settled, thats my default, nobody said yes to it yet

---
Back to [design choices](index.md) | [goals](../goals.md)
