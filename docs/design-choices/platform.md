# Platform
what cad, what does the assembling, how it gets packaged

## Identify
I need a cad that can do real solids to exact dimensions, and something that puts a robot together out of them

### Relevant constraints/nice to haves:
- Free and open, so anyone on a team can use it without a license thing
- Real B-rep solids (planes and cylinders, not meshes), so dimensions are exact and a hole is a hole
- Joints that hold parts together and can move (shafts spin, arms swing)
- Scriptable, the parts get made from numbers

### What has to be managed/controlled
- Making the solids
- Placing them and holding them together
- Getting the workbench installed

### Gates

1. free and open source
2. real B-rep solids
3. scriptable in something i can actually write

## Brainstorm

**Gate cuts:**

- Fusion: not free for everyone, not open, and the vex library for it already exists (and has no license)
- Onshape: cloud only, free plan makes every doc public
- Protobot: not cad, its the 'close enough' thing this is replacing
- Blender: mesh, so no exact holes

**Survivors:**

- **A - FreeCAD + built in Assembly workbench**
	in FreeCAD since 1.0, OndselSolver, joints take an `App::LocalCoordinateSystem` (or a face/edge) as the reference, so snap frames drop straight in. maintained with FreeCAD itself
- **B - FreeCAD + Assembly4**
	addon, LCS + `App::Link` based, works well, but its own thing to install and keep up with
- **C - FreeCAD + A2plus**
	older addon, constraint based (faces and edges, no frames)

## Select

| Criteria                           | A: built in | B: Assembly4 | C: A2plus |
| ---------------------------------- | :---------: | :----------: | :-------: |
| Nothing extra to install           |     yes     |      no      |    no     |
| Takes LCS frames as references     |     yes     |     yes      |    no     |


### Decision
A, FreeCAD + the built in Assembly workbench. **1.1 only** (thats what i run, 1.1.4 here, python 3.14 inside it). Packaged as a new style addon, `freecad/vex_workbench/` with a `package.xml`, so the addon manager can install it and `freecad -M .` loads it straight from the repo.

---
Back to [design choices](index.md) | [goals](../goals.md)
