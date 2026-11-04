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
- [x] **Hole finding on step parts**, the 0.182 square and 8-32 round holes, so motors and gears snap too
	works on click already, any inner loop up to 0.5" on a flat face picked by distance to the loop (58 of 58 on the motor's screw hole edges). the tool panels put dots on just the screw holes (8-32 round or ~0.182 square, open to the outside, one per hole and side), worked out the first time a part needs them and kept on its source. 11W and 5.5W get their 2 front ones (the 11W's case screw holes have heads in them 0.05 down, so no). a face click near a vent can still grab the vent
- [x] Extras like colors per material, weight, a parts list

## Later
- [x] Screw and nut tool. pick two lined up holes, it works out the stack and the screw
	two clicks gives the screw + nut now, jointed to the holes in an assembly. or into a thread with no nut, and spacers in the gaps
- [x] Align tool. hole on the part to move, then the hole it goes against
	faces land flat, keeps its turn to the nearest step, Rotate / Gap after. moves a link array whole, or the group its in. Revolute joint in an assembly, swapped out if its aligned again
- [x] Bending metal, cutting, drilling
	click a hole, it folds on a line through it (across or along, slid over by any amount), any angle, inside radius 0.032 to start. the cross section at the line swept round, holes the line goes through stay open. cut on the same lines (to length, or a flange off flush), drill a round hole anywhere snapped to a grid (0.25 to start). all per copy, kept on the link in order and redone if its Holes change

## From actually using it
- [x] dots drawn on top of solids, and a bigger area to click them
- [x] dots on round holes too: shaft holes (gears, wheels, sprockets, bearings, motor output), bigger round holes in metal, drilled ones. the 11W's output doesnt get one yet, its opening isnt a plain round or square loop
- [x] U-channel inner dots in a hair, to match where a c-channel's outer ones sit. out in the gap, 0.025 a side on steel
- [x] dots on every click-to-do tool, and a "show more" grid with a size box (drill needs it most). all six tools had dots already, drill gets Grid + Show the grid
- [x] screw tool takes several holes on one face, then the ones across. with "auto finish" on, one click across does them all, off and its a click across for each
- [x] cut tool. click two points for a line, doesnt have to go all the way across (slots, notches), more pairs for more cuts. plus a sketch-it button for anything fancier
	two points is in (Cut > Two points), kerf wide, edge dots to run off at, loose bits go. Sketch it starts a live sketch on the face, closing it cuts out whats closed in it
- [x] bend: centered on the line or next to it, and an inside radius box (vice and hammer bends are way tighter than 0.032)
- [x] place menu for wheels, gears and anything else with a pile of variants, same as the c-channel one (family, then type / size / whatever), only combos that exist
	Wheels, Gears and Sprockets, a `[[menu]]` in `parts.toml` each. a placed one gets the boxes as properties too and swaps in place
- [ ] simple joint tool: spin on a hole, slide along a line, and drag a part to see it move
- [ ] duplicate a sub-assembly, mirrorred across a plane or turned about an axis. parts get turned, not mirrored, so they stay real parts
- [ ] real colors and materials on every vex part
- [ ] weight for the step parts too, vex's listed mass where there is one, an estimate where there isnt

## Still need numbers for
- [x] bend radius
- [x] 1x1 angle variants: the official one, plus a 3x c-channel cut down the middle, along the middle hole's edge or between holes. ~~Regular 2-Wide, Thick 5-Wide, Thin 5-Wide, only fusion has them, as f3d~~ (made, Cut 3x Hole Edge and Cut 3x Between Holes)
- [ ] is aluminum c-channel really the steel shape? vex's al steps arent: 0.55 tall flanges, flange holes at 0.3, the 5x flares, 100 to 245 hole loops that dont line up with ours (volume only -0.2 to -1.7%). needs calipers on a real one to know if its vex's cad or the metal
- [x] which metal comes in which material (al bar? steel U-channel? steel 1x1? steel 3x c-channel?). none of the four, going by vex's cad: the zips off the aluminum kits and v5 structure pages (in downloads/) have al 1x1 angle, al U, al 3x c-channel and steel bar, and the 5x plates only in steel. the aluminum kits blurb still says "C-Channel, Plates, and Bars" tho and its own zip has neither. the catalog still makes all of them in both, dropping them is a call to make
- [ ] flange nuts (nylon, nylock), wing nut
- [x] HS spacer bore clearance: 0.252 across the flats on vex's steps, 0.002 over the shaft
- [x] which spacer OD / length combos actually exist: whatever robosource sells is fine
- [ ] drilled gear hole pattern
- [ ] HS lockbar
- [ ] are the nylon / aluminum hex nuts just the steel shape
- [x] shoulder screw thread = length - shoulder? yes, robosource: "Overall length of 0.375" includes shoulder and threads". thats how screw() already does it

---
Back to [goals](goals.md) | [main index](index.md)
