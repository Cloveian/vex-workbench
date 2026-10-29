# Roadmap

in build order, each one is something i can open and poke at

- [x] Catalog, every step + the generated families (`parts.toml`)
- [x] Design docs
- [x] **Workbench skeleton**: `package.xml`, `init_gui.py`, icon. done when `freecad -M .` shows a VEX workbench in 1.1
- [x] **Catalog reader**: `parts.toml` -> the actual list of parts, every family expanded. plain python, no FreeCAD. done when the test checks counts, unique names and that every fixture file exists
- [x] **Metal generator**: channels, U-channel, angles, plate and bar are all one cross section stretched to length with square holes on every flat face, so one generator. editable `holes` / `material`. done when it matches the steel steps exactly (aluminum ones flare, looser check)
- [x] **Part browser + insert** - common families at the root, fusion folders under. step parts imported once and linked after
- [x] **Snap to hole**. click a hole, frame at its exact center. two channels jointed hole to hole should be 0 apart
- [x] **The other generators**: shafts, standoffs, spacers, washers, nuts (thin nylock = vex nylock shaved to 11/64), torx button screws, shoulder screws. each checked against its step where there is one
- [ ] **Hole finding on step parts**, the 0.182 square and 8-32 round holes, so motors and gears snap too
- [ ] Extras like colors per material, weight, a parts list

## Later
- [ ] Screw and nut tool. pick two lined up holes, it works out the stack and the screw
- [ ] Bending metal

## Still need numbers for
- [x] bend radius
- [ ] 1x1 angle variants (Regular 2-Wide, Thick 5-Wide, Thin 5-Wide). only fusion has them, as f3d
- [ ] is aluminum c-channel really the steel shape? vex's al steps arent
- [ ] which metal comes in which material (al bar? steel U-channel? steel 1x1? steel 3x c-channel?)
- [ ] flange nuts (nylon, nylock), wing nut
- [ ] HS spacer bore clearance
- [ ] which spacer OD / length combos actually exist
- [ ] drilled gear hole pattern
- [ ] HS lockbar
- [ ] are the nylon / aluminum hex nuts just the steel shape
- [ ] shoulder screw thread = length - shoulder?

---
Back to [goals](goals.md) | [main index](index.md)
