# Part sources
where the solids come from

## Identify
every V5 part needs a solid, and the solid has to be *exact*. there's three places they could come from

### Relevant constraints/nice to haves:
- Exact: real planes and cylinders, the hole grid right to the thou
- Every size: channels get cut to any length, screws come in 13 lengths, and vex only has steps for some of them
- Shippable: whatever goes in the addon has to be allowed to go in the addon
- Robosource parts too (thin nylocks, shoulder screws, 7/8 standoffs, the washers), they have no cad at all

### What has to be managed/controlled
- Metal, shafts, hardware: all just numbers
- Molded and complicated stuff: motors, wheels, gears, electronics, legacy parts
- Keeping the numbers honest

### Gates

1. exact geometry
2. allowed to ship (or can be made on the users machine)

## Brainstorm

**What's out there:**

- **vex's step files**: 289 of them pulled off vexrobotics.com (`tools/fetch_vex_cad.py`, plus 13 packs by hand), sorted into the fusion library's folders (`tools/sort_vex_step.py`). exported out of solidworks, real planes and cylinders, measured really clean in FreeCAD
- **the fusion library (VEX-CAD)**: more parts and more sizes, but its `.f3d` solids are autodesk ShapeManager binary, the only maybe-reader is the InventorLoader addon (untested). and the repo has no license, so none of it ships
- **generated**: made from the catalog numbers at insert time

**Gate cuts:**

- the fusion library as a source: fails 2. still fine to *look at* for sizes and names

**Survivors:**

- **A - all steps**
	exact, zero code, but only the sizes vex exported. no 1x17 channel, no robosource anything
- **B - all generated**
	every size, but a motor or a wheel from numbers is a whole cad project each
- **C - generate what we can, steps for the rest**
	numbers for the simple stuff, steps for the complicated stuff, and the steps that overlap a generated family become its test fixtures

## Select

| Criteria                     | A: steps | B: generated | **C: both** |
| ---------------------------- | :------: | :----------: | :---------: |
| Every size                   |    no    |     yes      |     yes     |
| Motors, wheels, electronics  |   yes    |  *so* much   |     yes     |
| Robosource parts             |    no    |     yes      |     yes     |
| Something to check against   |   n/a    |     no       |     yes     |


### Decision
C, generate what we can, ship the steps for the rest. 23 generated families in the catalog so far, all 289 steps stay listed as step parts, and the generated ones get checked against the matching steps.

todo before release: check vex's terms on redistributeing their steps. if it's a no, the workbench runs the fetch script on first launch instead

---
Back to [design choices](index.md) | [goals](../goals.md)
