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
	click a hole, it folds on a line through it (across or along, slid over by any amount), any angle, inside radius 0.032 to start. the cross section at the line swept round, ~~holes the line goes through stay open~~ a band at a time where the section changes, so any hole in the bend wraps round it (square ones exact, round and slanted edges in w / 12 steps). cut on the same lines (to length, or a flange off flush), drill a round hole anywhere snapped to a grid (0.25 to start). all per copy, kept on the link in order and redone if its Holes change

## From actually using it
- [x] dots drawn on top of solids, and a bigger area to click them
- [x] dots on round holes too: shaft holes (gears, wheels, sprockets, bearings, motor output), bigger round holes in metal, drilled ones. the 11W's output too, its socket is a 1/4 square turned 45 so it goes by across the flats, the dot sits where the square starts 0.5" down the recess
- [x] U-channel inner dots in a hair, to match where a c-channel's outer ones sit. out in the gap, ~~0.025 a side on steel~~ 0.008 a side (aluminum only now)
- [x] dots on every click-to-do tool, and a "show more" grid with a size box (drill needs it most). all six tools had dots already, drill gets Grid + Show the grid
- [x] screw tool takes several holes on one face, then the ones across. with "auto finish" on, one click across does them all, off and its a click across for each
- [x] cut tool. click two points for a line, doesnt have to go all the way across (slots, notches), more pairs for more cuts. plus a sketch-it button for anything fancier
	two points is in (Cut > Two points), kerf wide, edge dots to run off at, loose bits go. Sketch it starts a live sketch on the face, closing it cuts out whats closed in it
- [x] bend: centered on the line or next to it, and an inside radius box (vice and hammer bends are way tighter than 0.032)
- [x] place menu for wheels, gears and anything else with a pile of variants, same as the c-channel one (family, then type / size / whatever), only combos that exist
	Wheels, Gears and Sprockets, a `[[menu]]` in `parts.toml` each. a placed one gets the boxes as properties too and swaps in place
- [ ] simple joint tool: spin on a hole, slide along a line, and drag a part to see it move
	spin is Align's Revolute, slide is Align > Slide along to another hole (a Slider, length limits on the two holes). drag is the assembly's own. the limits go in on every solve (rail is marker I, the moving part J, so 0 to the rail length is the right way round) but a plain solve still leaves it 3.5" up a 2" rail. thats ondsel, not us: in 1.1.4 a limit only switches on inside a drag step (`PosICDragLimitNewtonRaphson`, the one place that calls `activate()`), a plain solve or recompute never does. and drag isnt in the python api, so a real drag by hand is the only way to see if it stops on them
- [x] duplicate a sub-assembly, mirrored across a plane or turned about an axis. parts get turned, not mirrored, so they stay real parts
	Duplicate tool. each part goes through world mirror x placement x a mirror across one of its own middle planes (found off its vertices), two reflections = a turn. worked metal with no middle plane left gets its steps mirrored on the plain part's. mecanums swap to the other hand, other handed ones (motors) get turned across the plane they nearly mirror on and named. joints between copied parts come along, and ones to parts that stay put go to the mirrored / turned hole on them if theres one, a mirrored frame is own x frame x a flip of its own y so it stays right handed, offsets conjugated by that flip
- [ ] real colors and materials on every vex part
	wheels repainted ~~off vex's library photos~~ in the fusion library's appearances (hub / rim), FreeCAD material cards on everything with a material, 24T HS gear is steel per the store. steps with no colors in them at all get a `[step_color]` by folder or row off fusion (red acetal gears and sprockets, bearings, 9P chain, sensors), or their material's color like generated parts (every nut, LS shaft, retainer). left: no fusion match for the V2 2" mecanum, tank tread, legacy cortex stuff or the bogies (theyre painted per face), the legacy traction wheels' steps are laid out too odd for the hub / rim split, and wheel materials, the store's wheels page has no material tab
- [x] weight for the step parts too, vex's listed mass where there is one, an estimate where there isnt
	35 listed (electronics, flywheel weight, pneumatics, the wheels, bogies, intake roller, 393), the rest off a material per folder from vex's store pages. listed ones checked against step volume, all 1.0 to 2.9 g/cm3. the 2" omni (90 g) and V2 2" mecanum (127 g) came out 5.5, way too heavy for that much plastic, so theyre left off. inserts, kits, the 4" HS bore wheel (no listing anywhere), the other sensors (pack or piece isnt clear) and the small pneumatic fittings still a ?

## Still need numbers for
- [x] bend radius
- [x] 1x1 angle variants: the official one, plus a 3x c-channel cut down the middle, along the middle hole's edge or between holes. ~~Regular 2-Wide, Thick 5-Wide, Thin 5-Wide, only fusion has them, as f3d~~ (made, Cut 3x Hole Edge and Cut 3x Between Holes)
- [ ] is aluminum c-channel really the steel shape? vex's al steps arent: 0.55 tall flanges, flange holes at 0.3, the 5x flares, 100 to 245 hole loops that dont line up with ours (volume only -0.2 to -1.7%). needs calipers on a real one to know if its vex's cad or the metal
- [x] which metal comes in which material (al bar? steel U-channel? steel 1x1? steel 3x c-channel?). none of the four, going by vex's cad: the zips off the aluminum kits and v5 structure pages (in downloads/) have al 1x1 angle, al U, al 3x c-channel and steel bar, and the 5x plates only in steel. the aluminum kits blurb still says "C-Channel, Plates, and Bars" tho and its own zip has neither. ~~the catalog still makes all of them in both, dropping them is a call to make~~ dropped: U and 1x1 are aluminum only, bar is steel only, and the c-channel family skips steel 3x
- [ ] flange nuts (nylon, nylock), wing nut. nylon one is in, off the fusion library's, 21/64 hex on a flat 0.379 flange. nylock has a domed crown on top, still to do. no wing nut anywhere yet
- [x] HS spacer bore clearance: 0.252 across the flats on vex's steps, 0.002 over the shaft
- [x] which spacer OD / length combos actually exist: whatever robosource sells is fine
- [x] ~~drilled gear hole pattern~~ not a part, an LS gear drilled out by hand. Drill does LS gears now, straight through
- [ ] HS lockbar
- [x] are the nylon / aluminum hex nuts just the steel shape? yes. robosource's nylon one is 11/32 across, 0.130 tall, "the same size as VEX EDR nuts", aluminum 8-32 nuts are ASME 11/32 x 1/8, and the fusion library's three are one shape. thats what the catalog does already
- [x] shoulder screw thread = length - shoulder? yes, robosource: "Overall length of 0.375" includes shoulder and threads". thats how screw() already does it

---
Back to [goals](goals.md) | [main index](index.md)
