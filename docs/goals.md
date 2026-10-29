# VEX Workbench

The working design doc. The [front page](index.md) has the why.

## Goals & constraints
listed roughly from hardest constraints down to less necessary stuff:

### Must haves
- **Exact dimensions, not 'close enough'** (#1 priority). a joint between two holes lands *exactly* on the hole centers, no slop baked in
- Runs in FreeCAD 1.1, the built in Assembly workbench does the joints
- Every V5 part i'd actually use, generated or from vex's step files
- Generated parts can be changed after they're placed (25 holes -> 20 and it rebuilds)

### Must haves in order to be better than protobot / the fusion library
- Parts easy to find, the common ones right at the top
- Snapping to a hole is one click
- Same part placed 40 times is one model, not 40

### Nice to haves
- A screw and nut tool, so fastening two things is really easy
- Bending metal
- Colors per material, weight, a parts list

### Nice to have, but slightly far-fetched (harder to achieve)
- Cutting metal the way i actually cut it (half holes, cut corners, cut through a hole)


## Design Choices

- [Platform](design-choices/platform.md) - FreeCAD 1.1 + its built in Assembly workbench, python addon
- [Part sources](design-choices/part-sources.md) - generate what we can, ship vex steps for the rest
- [Catalog](design-choices/catalog.md) - one TOML file, families + step groups
- [Parts](design-choices/parts.md) - App::Part per part, editable, copies are links
- [Snap points](design-choices/snap-points.md) - frames at exact hole centers, zero clearance
- [Part browser](design-choices/browser.md) - common families at the root, fusion folders under

## Building it
- [Using it](using.md) - how to put a robot together with it, as it is now
- [Code](code/index.md) - layout, testing, dated log
- [Roadmap](roadmap.md) - build steps in order
