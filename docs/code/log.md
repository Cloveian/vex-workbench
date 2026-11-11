# Log

## 2026-11-11 - more parts

- 3/8" HS spacer. vex has no step for it, so its their 1/2" with 1/8" cut out of the middle. theyre molded with draft both ways off a parting line in the middle (0.3937 across there, ~0.0088"/in a side smaller going out), so the two halves meet on the same section and it just looks molded. 0.02158 in3, 1.7% under halfway between the 1/4 and the 1/2, which is 0.007 g. the four real ones are fixtures now too, which is how the 1/16" (actually 1.6 mm, 0.063) turned out to be getting a 0.0005" sliver cut out of it. not anymore
- aluminum 2x2 angle and 5x plate, off the fusion library's f3ds. same shape as the steel ones: at 0.063 the plate is exact and the angle is -0.06%, theyre 0.062 like the c-channels. fusion's have a lil 0.1" tab sticking out one end (0.705 wide on the angle, two 0.32 ones on the plate) that vex's steel steps dont, *no* idea why, mine dont either. also fusion's "25 - 2x2 Angle" is the 35 hole one
- read_f3d skips shells that are one flat face. fusion's metal files have a surface body on every face of the part and those were stopping it
- 6P chain links, generated. every number on fusion's link is a round mm (3.25, 4.45, 5.65, 4.4 tall, a 3.2 barrel, 2 mm peg into a 2.1 hole) and mine xors against it at 0.000000%. *Yippee.* the 3P link is toroids and splines all over its snap pin, thats a whole other night

## 2026-11-10 - the redo

My whole system corrpted and i had to restore from a snapshot from the 9th, so everything after it was *gone*. tonight was doing it all again off my list, measured and worked out again from the steps and the fusion files, not copied from anything. it went faster the second time at least, and some of it came out better _:(´□`」 ∠):_

- hover: the dot a click would take goes yellow under the mouse. every dot's screen spot is one numpy matmul off the view volume's matrix now, 0.04 ms for 543, projectToScreen one at a time was ~6 ms (that ones from before the restore, didnt time it again). checked against coin's own to 0.01 px
- the mouse callback on the click panel was called `clicked()`, which is what FreeCAD calls on a task panel with its *buttons*, so Close threw into the report view on every panel. its `pressed()` now
- place: a new part lands 1" off the +x side of whats drawn (coin's box of the whole scene, taken before it goes in), bottoms level, one undo step. **Then align** opens Align after
- shaft inserts: an Insert box (None / Round / Square) on the wheels, gears and sprockets with a 1/4 square HS bore. ~~29~~ 28 of them, measured this time: every one has exactly one square loop 0.25 to 0.339 across on each face, and the 12T HS pinion is a 1/8 bore so it doesnt count. the insert is 0.395 square flange 0.05 thick, then a 0.248 body 0.15 long, a 0.16 round hole (plastic) or 1/8 square (metal). its own link, Placement = `gear.Placement * VexSeat` as an expression, and a Fixed joint when its in an assembly. the gear first had a PropertyLink back to it, which made a dependency loop with the expression, so Duplicate's `tops()` saw the gear inside itself and copied nothing. its the insert's name in a string now. ABS 1.06 and powdered metal 6.8 (a guess) give 0.19 g and 1.35 g, flagged ~
- joint tool: Spin, Fixed or Slide, the slide math that sat commented out in align.py lives in `joints.py` now. offsets off where the parts already are, a solve moves nothing (tested for all three)
- step dots cached on disk next to the brep. the rays were 11.0 s on the 4" antistatic traction wheel, 8.7 on the 84T HS v2, 9.5 on the 40T 6P sprocket, every new document. now once

still lost, not redone yet: the chain tool and its 6P and 3P links, the 3P sprockets, every fusion-measured family (flex wheels, VersaHex and the VersaHub, legacy omnis and traction, the turned parts, the linear slide, ratchet and pawl), the 3/8 HS spacer, aluminum 2x2 angle and 5x plate. thats the next few nights i guess

## 2026-11-08 - align just moves, 0.2.0

- placing a U-channel after two c-channels put one next to *each* of them. double clicking a placed part in the tree makes its hidden source the active part, and `activePartOrAssembly()` hands that back, so the U-channel went in the source and every copy showed it. place, align, screw, spacers and duplicate all ask `ui.active()` now, which skips sources
- option boxes got cut to a word or two ("Auto finish", "Pick screw", "Whole group", "Show grid"), the rest went in tooltips
- Align doesnt make joints anymore, and Slide is gone with it. joints are for a joint tool, the slider math is kept commented out for that. screws, nuts and spacers still get their Revolutes
- Align > Flip turns the part over onto the same hole's other face, for an insert into a gear. which face is a ray down through the metal just past the hole's edge, first face out. the farthest loop on the axis would have been a channel's *other* flange
- Screw > To the nylon: on a nylock the screw only has to reach the top of the hex flats, 0.139 up on vex's (0.193 tall), so two 0.046 plates take a 0.25 instead of the 0.29. the length already went by the nut picked, so a thin nylock or a hex nut was getting a shorter screw already
- the 3.25" antistatic wheel stall didnt reproduce headless: 7.0 s the first time for the traction one (5.3 s of that reading its 14 MB step), 1.5 s from the brep cache after, the omni 1.0 / 0.4. drawing isnt in those numbers, so its still open. the old copy in my Mod folder predates the cache tho
- a repro script called `wheel.py` hung freecad before it ran a line, cuz `wheel` is a pip package and something at startup imported mine. renamed it and it was fine ლ(¯ロ¯"ლ)

## 2026-11-07 - fusion colors, bends round holes, the last families, al channels

- step parts get read once and kept as a brep in freecad's cache folder, keyed on the file and a `BREPS_VERSION`. the 1" star drive coupler goes 26.7 s -> 0.012 s, and brep keeps the face order so vex's face colors still line up. headless doesnt use it and the gui test points it at a temp folder, so the tests never touch the real cache
- colors off the fusion library's appearances for every step it has a match for and vex left grey, ~45 of them plus the 10 repainted wheels (steps with vex's own colors keep those, so the HS v2 gears stay grey). its acetal gears and sprockets are all "VEX Red Acetal" 255,30,30, which i did not expect. the wheels lost their photo colors too. first go let a folder color beat a row's material and the steel 12T Metal Gear came out red, the checker caught it
- the metal vex doesnt make is gone: U and 1x1 aluminum only, bar steel only, and a family `skip` for the steel 3x c-channel. 795 -> 600 generated. asking for a skipped one says so, and on a placed one the box goes back
- bends go on a band at a time wherever the strip's section changes, so a hole inside the bend wraps round it open. first version only looked at edge vertices and a round hole's far side isnt one, so a drilled hole came out half filled, half a rectangular slot. a 0.08 hole 0.02 short of the line: 0.17 of it stayed open on the old sweep, all of it now
- nylon and nylock flange nuts and the 3 / 5 / 7 hole HS lockbars, measured off fusion's f3ds. a lockbar is just the 1x bar with a sharp 1/4 square middle hole, volume to 4 decimals. every family has a generator now, the wing nut is the only one left (skipped later, vex doesnt have one)
- aluminum c-channel is its own shape: 0.55 flanges, flange holes 0.3 off the web, 0.078 tip chamfers, 0.070 marks with round bottoms. every hole on all 5 al fixtures lines up. the 3x is its own again (0.546, 0.063 wall, 0.05 chamfers, sharp 0.06 marks), it was 0.23% light till slicing both every few hundredths along a mark showed the chamfers and marks off. its reliefs sit off center too but at -0.17% thats in with the other c-channels
- the al numbers are written once now: a row's tables merge into the family's (`catalog.merged`, and `fits` so `picks` still finds the 3x's Size, it threw on placing one at first), and the cut 1x1s say `cut_from` the 3x and only keep their web
- the old pneumatics hex nut, ~~a #6-32 off ASME #6 (5/16, 7/64) cuz i couldnt find a model~~ fusion's "Hex Nut (Piston, 6-40, Steel)", the cylinder rod nut, 0.31 x 0.11 and 0.2% over its volume. it sat in Hardware/Nuts, not the 8-32 folder i was looking in. fusion's "Hex Nut (8-32, Steel)" turned out to be vex's 275-1028, same volume, so the 8-32 ones were never off

## 2026-11-06 - a review pass

Went through every module with a bug review before any of this gets pushed. most of what came back was edge casses or "what if the catalog had a typo", the real ones:

- a screw ending on a U-channel's inside flange threw IndexError. that frame sits out in the 0.025 gap so a c-channel inside meets it, and `bore()` wanted it dead on the hole loop. it matches the loop on the frame's axis now and adds the gap to the depth
- a drilled LS gear changing size through its menu box never pruned its old worked source, and a drill that didnt fit the new gear left it half switched. `restep` goes through `refit` now like a size change does
- duplicating a part out of a folder inside an assembly put the copy in the assembly, not the folder (`getParentGroup()` is None straight in a Part, so the folder goes first now). and the panel counted the selection, not what got copied
- drill's Show the grid only drew on metal, so the grid it snaps an LS gear to was invisible
- cut kept its "last cut" across a mode change, so Keep the other side could flip a cut from the other mode
- the grid dots and the hole dots cached by source name only, an undo or a linked file can hand out the same name again. both key off `source_key()` now, same as the shape cache
- parts list didnt count through a plain link to a link (an App::Link has no Group), and a copy with no weight could blank out one that had one

And a few small ones: a gap under the 0.016 washer said "more than 8 spacers", `hole_dots` could get its saved property stuck empty, a removed menu id would KeyError on every change. all 791 parts with a generator build a valid single solid (the 635 metal ones take 570 s). spacers between two U-channel inside flanges started from the gap frames and floated 0.025 off each side (and a screw's spacer off one ovirshot into the next part), they start on the metal now with the first joint held back to it. screw heads and nuts on one floated the same way, plus a 0.016 washer in the air under the head and a 0.375 screw where a 0.290 does. `library.off_metal()` says how far a frame sits off, and screws, nuts and spacers all go from the metal. left for later: a bend fills in a hole that sits within ~2 mm (w, 2.08 on steel) past the line without crossing it. volumes at a few Off the hole values didnt settle it (the section changes with the small holes too), reading `fold()` did: the bend is only the section on the line swept round, and `rest` starts at w. its in known limits in the README now

## 2026-11-06 - colors and weights

- the 2" omni wasnt a photo job after all. the appearance asset in the f3d (`.protein`, a zip of autodesk binaries) is cut into 136 byte pages with an 8 byte header each, and with those stripped "VEX Wheel Plastic" is 29/255 grey and "Roller Rubber" 166/255, exact 8 bit steps, and the swatch thumbnails next to them agree. black hub and a new "Roller Grey". tried a `--colors` tool for every f3d but theres no property tags in there, picking the color out by "looks like n/255" got 4 of 6 right, so no tool
- vex left ~half its steps with no `COLOUR_RGB` at all, every nut, every LS shaft, the retainers. those skip ImportGui now (faster too) and get their material's color like generated parts do, acetal has none so the gears look the same
- 15 wheel and bogie rows got vex's listed weight. checked each against the step volume first, all 1.0 to 2.9 g/cm3 except the 2" omni (90 g) and the V2 2" mecanum (127 g), which come out 5.5, so not those
- wheel painting took 130 s for the 10 repainted wheels. it was computing `Volume` on every piece twice just to see which rollers are the same, on those splines thats ~10 s a go for the 2.75 omni. counting faces / edges / vertexes gives the exact same colors on all 10, 7.8 s total. a review pointed out same counts isnt same shape (3 different size bushings would all go rim), so total edge length is in the key too, 0.05 s more
- the slider limits: in 1.1.4 ondsel only switches a limit on inside a drag step, so a plain solve can never respect them. not my bug, and still cant drag from python

## 2026-11-06 - drilled gears and a fusion reader

- joints made with freecad's own tool straight on a face, edge or corner of a plate died on any rework: the worked source gets a new solid (`Solid001`) with every face renumbered, so `Vex.Solid.Face431` pointed at nothing. `carry` looks them up again by where they are now, through the same `ways()` the frames use. a face counts if any of it is left (most overlap wins), edges and corners have to be right there. first go did a boolean against every plane in the face's box, which on a plate is ~400 hole walls, 3.6 s for one drill. only faces actually on the old face's surface get the boolean now, ~0.4 s
- "drilled gears" were never a part, you just take a drill to an LS gear so it spins on a screw. so the made up family went and Drill takes LS gears now. it goes straight through the whole gear, the bore has a step inside at 0.125 that the wall finder stopped at, leaving a 0.06 skin at the bottom. a drilled gear keeps the color most of it was
- nylon and aluminum hex nuts really are the steel shape (robosource, ASME 11/32 x 1/8)
- `tools/read_f3d.py` reads the fusion library's .f3d files: ACIS binary SAB inside a zip, cm. planes, cones, spheres, tori, lemon tori (omni rollers, occ's toroid wont do those so its a circle swept round), spline surfaces and intcurves off the b-spline acis stores inline, tolerant edges. the hex nut matches vex's own to 5 decimals, the 36T to 0.01% on volume, the 2" omni solid for solid to 6. the mecanum has a modeled thread on one screw that winds ~10 times past a seam and doesnt sew, and assemblies come out as loose parts since the placements live in fusion's own BulkStream. *bleh*
- the fusion files dont have face colors in the brep, theyre in an autodesk asset blob pointed at by body GUIDs, so the 2" omni colors are still a photo job. and the library has no license, so the reader is for measuring, nothing it makes ships

## 2026-11-05 - joints that follow along

- the 11W output finally gets a dot. its socket is a 1/4 square turned 45, so its box is 0.35 across and it was "too big" for a shaft hole the whole time. goes by 2 \* the center's distance to the loop now (across the flats), dot sits where the square starts 0.5" down the recess
- slide limits: read FreeCAD 1.1's AssemblyObject.cpp. the limits go into every solve (min `=>`, max `=<`, rail is marker I and the mover J, so 0 to rail length is the right way round), the static solve just doesnt hold them, 3.5" up a 2" rail. drag isnt in the python api, so a hand drag is still the only test
- joints follow bends. a bend's turned side moves by one rigid placement (`metal.turned`), so a frame either stayed or went round with it. `ways()` tries every combo of the bends since the old and new steps split, undo the old ones then redo the new, first one that lands on a hole wins. a 90 redone at 45 lands right, and a real Revolute'd shaft follows after a solve
- mirroring worked metal with no middle plane left (a bend plus one off center hole) mirrors the steps on the plain part's plane: points and directions through the matrix, `side` flips cuz n x d does. checked every step kind against a slanted mirror, which caught `transformGeometry` turning the sketch face into bsplines a mm3 off. `transformShape` does reflections exact
- a flaky wheel paint test turned out real: 9000 faces on an omni, `hashCode()` only goes to 2^31, so on ~2% of loads two faces share one and a hub face goes rim colored. `findSubShape` numbers them now
- Duplicate brings joints along when both ends are on copied parts. a mirrored frame is own \* frame \* a flip of its own y so its still right handed, offsets get the same flip on both sides (gap stays, spin goes negative), angle limits swap and negate. a whole copied assembly gets its own joint group
- the mirror check went from "one of 3 axis planes, exact vertices" to the best of those plus planes through each axis off level vertices (vex's torx lobes), neighbor cells so a point on a cell edge isnt a miss, and for 20 or fewer leftovers each has to land on an edge (stray split vertices do, a drilled hole's dont). had a boolean there first, 38 s on a 36T v2 gear, *bleh*
- found doing that: the "handed" fallback was a reflection through the part's own Z, which on a motor is the shaft. so a mirrored motor came out pointing its shaft the wrong way the whole time lol. now the plane it comes closest to mirroring on, keeps the shaft. near-mirrors (motors, v2 HS gears with a handful of odd bits) bring a joint only if its mirrored frame lands on a hole
- joints to a part that wasnt copied come too: its frame goes through the mirror in that part's own coords (W^-1 M W \* frame \* the y flip) or the turn, and if theres a hole there the copy gets jointed to it. so a drive side mirrored across a symmetric chassis comes out bolted to the other side. ones with nowhere to go get counted and the panel says "couldn't come along, Align it again"
- the undo test caught a stray frame: a joint whose far end failed still made its frame on the copy end, and thats a shared source so every channel that size grew a Hole. frames only get made once both ends have somewhere to go now

## 2026-11-04 - weights, slides, wheels, mirrors

- step parts weigh something now. 20 off vex's listed masses (motors 155 g, brain 285 g, the pneumatic cylinders), the rest volume \* density off a material per folder (`[step_material]`) and a ~ in the parts list. vex's product pages 403 anything that isnt a person, playwright included, so the numbers came out of search snippets and the materials off pages saved by hand. the battery is 0.62 lb off the store, the KB says 350 g which is just the controller's number copy pasted
- Align > Slide along to another hole: a third click down the rail and the Revolute becimes a Slider, frames turned so z runs hole to hole, length limits on both holes. a plain `asm.solve()` ignores the limits completely (bar went 6" up a 2" rail), so whether a real drag stops on them is still a ?
- wheels repainted off the photos in vex's library article, most of their steps had no color and a couple were cad green and red. rim = solids there are 3+ of or out past half the radius, hub the rest. the 2" mecanum also has 2 loose shells of 4000 specks of faces that the solids didnt cover. rendered offscreen with `LIBGL_ALWAYS_SOFTWARE=1` and they look right
- FreeCAD material cards on everything with a material (Steel-Generic, Aluminum-6061-T6, PA6, POM, PTFE), set before the colors and they dont touch them
- Duplicate: mirror or turn a copy. a mirror is world reflection \* placement \* the part's own middle-plane reflection, two reflections = a turn, so a channel lands exactly on its mirror image and is still a channel. the own plane comes off the vertices. mecanums swap to the other hand, the V2s exactly, vex's V1 left and right models arent even mirrors of each other so those are close-ish. motors just get named
- a link forwards getattr to what it links, so `hasattr(link, "VexName")` is true on every copy. bit a test, *bleh*

## 2026-11-02 to 11-04 - the list from actually using it

- hole dots are their own ovirlay, drawn over solids, with my own picking: anything within about 14 px of a dot gets it, the one facing you wins. freecad selects on the mouse release, which my callback never sees, so every dot click also picked the edge under it. any selection right after a dot press gets thrown out now. hidpi and a spreadsheet tab in front of the 3d view sorted too
- round holes get dots (shaft holes on gears, wheels, sprockets, the 5.5W output, bigger round holes in metal, drilled ones). screw_holes stopped being true, so its hole_dots
- U-channel inner dots sit out in the gap, so a c-channel aligned in there lands centered. half the tests were quietly testing my addon manager install and not the repo
- parts.toml takes "5/16" and "29 mm". aluminum is 0.062 in some places and 0.063 in others, and past_bend could come off the thickness, both left for later
- drill grid any size, with a dot on every grid spot if you want. the front and back faces had different grids so a hole from the back didnt match one from the front
- bends get an inside radius box (down to 0, vice and hammer) and can sit next to the line or centered on it
- screw a row: pick holes on the head side, one click across does them all with auto finish on
- cut: two points for a kerf wide cut that stops anywhere (slots, notches), the count notches tried to eat the edge dots. and Sketch it, a live sketch on the face that cuts out whats closed in it, edit it and the cut redoes, delete it and the metal comes back. only one task dialog at a time, so the cut panel closes itself first
- place menus for wheels, gears and sprockets (`[[menu]]`), only combos that exist, and a placed one keeps the boxes and swaps in place. a box reset the boxes under it which changed the part again, BUSY stops it chasing its tail

## 2026-11-01 - cutting, drilling, presentable

- Cut works on the same lines as Bend: through a hole, across or along, slid over. metal.cut() is fold() without the fold, the same split (only whats cut off the clicked wall goes, a far flange the plane slices stays). sawn edge, no notches. slide 0.25 from a flange's hole row onto the web and the flange comes off flush, do both flanges and the web finally folds toward where they were
- Drill: click a spot, a round hole goes through the wall, snapped to the 0.25 grid off the nearest hole on that face (Shift for exact). the wall thickness comes off that hole too, cuz on a plate the grid spots are already little square holes and a ray there just goes straight through
- the bends list became a steps list (VexSteps, fold / cut / drill in order) and bend.py became shop.py with all three panels on one base. metal.py already had a cut variable in make(), renamed it before it bit me like bend() did
- the side that goes or turns gets picked off just the clicked wall's pieces, the whole half space counted the far flange too and cut the web off instead of the flange. and it gets picked again when you slide the line after clicking, plus a cut that would leave two pieces says no
- a step that couldnt be done blew up inside the document observer with nobody to catch it, now the new source gets made first so it errors in the panel like it should. that also put up a modal error box in the gui test, which offscreen just sits there forever, fun
- README rewritten for someone landing on it cold, quick start, the tools grouped, known limits. spots for screenshots in docs/img/shots.txt, those need the real window
- making a worked part shorter keeps the steps that still fit and drops the rest with a warning, it used to get stuck half changed. and the old worked source gets deleted after, both there and on every redo of a step
- parts list: total is what the copies really weigh, each is the plain one off the shelf. i thought a cut copy only ever weighs less so the heaviest would do, then measured a bend. it adds 0.04 g on a plate, cuz k = 0.44 puts the neutral line inside of the middle of the wall so the bend has a bit more metal than the flat it eats
- joints come over to the new source when a part gets bent, cut or drilled, for holes that are still in the same spot. the joint refs are just names of LCSs in the source, so a new source = every joint on that part pointing at nothing. ones on a hole a bend moved still break, that ones a decision (folow the hole? delete the joint?). it runs on every size change too, any part, and a standoff or spacer keeps the joint on the end that didnt move. its Seat points in while the end's normal points out, so the axis matches either way round
- offscreen freecad cant draw its 3d view, but `saveImage` still renders with `LIBGL_ALWAYS_SOFTWARE=1`, hole dots and all. so README images can come out of a script, just no panels in them
- looked stuff up for the roadmap: hs spacer bore is 0.252 on vex's steps, robosource's shoulder screw length includes the shoulder (screw() had it right), vex's cad library has none of al bar / steel U / steel 1x1 / steel 3x, and vex's terms dont say if the steps can be shared
- a bare Frame on hole comes along too now, but only onto a worked source just that copy uses. on a plain one it would turn up on every plate that size, placed later or not
- refit wiped all the steps when even the plain part couldnt be made, then errored anyway. now it just errors. and a fresh clone with no vex-step/ gets told to go read the README instead of a path
- freecad's own joint tool on a face or edge still breaks on any of this, faces get renumbered. only frames carry
- the steps ship now. not all 912 MB of them (the clawbot alone is 119 MB, over github's 100 MB a file), just the bases and the V5 robot parts, gzipped: 209 files, 131 MB, the biggest a 6.7 MB omni wheel. they get unzipped into a temp file to read and it goes again right after. the browser hides the 80 that dont ship unless vex-step/ is there. a fresh clone in downloads/ placed a screw and a motor (13 colors and all) with no vex-step/ anywhere
- LGPL-2.1-or-later like freecad, and the README says how to install it through the addon manager or by cloning into Mod, with the renders as its pictures

## 2026-10-31 - bending

- Bend tool. click a hole, it folds on a line through it, across or along the part and slid over by any amount, any angle, inside radius 0.032. metal.fold() cuts the part at the line, sweeps the cross section there round an axis r off the inside face, and turns the rest round the same axis after moving it back by the flat the bend eats, w = (r + k*t) * angle (~0.08" for a 90). a hole the line goes through leaves a gap in the cross section, so it stays open round the bend for free
- a 90 up across a 5x10 plate lands within 1e-6 mm of the hand worked numbers (leg at 2.25 - r, top at t + r + 2.25 - w), volume within 0.07%. channels bend flanges and all, those come out heavy cuz the flanges get swept round too, the same extra every bend so +3.3% on a 1x2x1x35 and +11% on a 1x2x1x10. which is fine since real metal wont do that without cutting them anyway
- bends live on the one placed copy (VexBends), its source is the straight part + the bends in order. it keeps the straight VexName so the parts list counts what you buy, and Holes changes redo the bends. the length direction for a second bend on a leg bent square to x comes from the earlier bend's face normal
- metal.py already had a bend() for the corners between legs, mine overwrote it and everything with a flange broke. its fold() now
- folding a channel's web toward its own flanges put the flanges past the bend axis, the sweep turned inside out and the fuse handed back nothing or a sliver, still isValid. that gets refussed now, plus a backstop for anything that isnt one solid at 0.8 - 1.5x the volume. so across a channel or an angle it bends one way, away from its other walls, a plate either way
- the cut plane goes on forever, so folding one flange tip along the channel sliced the far flange too and swung it round with it. only pieces cut off the clicked wall turn now (a face on the line within 0.3" of the hole), the rest stay put
- the hole cache keys on VexBends too: a bent source keeps the straight VexName, and FreeCAD gives an undone object's name to the next one made
- 1x1 angles cut out of a 1x3x1 channel, along the middle hole's edge (0.659 web) or between the holes (0.5). two between-holes halves + the middle strip and its holes come out to the channel's volume exactly, which is a nice check with no step to compare to. the fusion only 2-wide / 5-wide ones with no numbers are gone, 868 -> 798 generated
- the sawn edge check first looked for a "web" param, which the U-channel has too, so it lost its notches on one leg. only +0.1% volume, under the 0.2% the metal test lets through, a part by part volume compare caught it
- screw tool: Pick the screw myself, one click puts the picked screw in that hole. shoulder screws only go in that way, the shoulder length is too much of a judgement call to pick for you

## 2026-10-31 - align

- screws, nuts and spacers sit on Revolute joints now, not Fixed, so they can spin. snap.revolute() puts any gap in Offset2, cuz thats what the joint panel's offset box edits (Offset1 just showed as 0 there)
- Align tool. hole on the part to move, then the hole it goes against, faces land flat. it keeps the turn the part already had, rounded to the angle box (atan2 of the old x against the target's x and y, after the face to face flip), then Rotate -/+ and a gap box. gap under 0 pushes it in, so a shaft end goes through a hole
- a link array moves whole from any element's hole, and "Move its whole group" moves the top Part under the active assembly instead, all the same math: frame = world(thing that moves)^-1 * the hole's world frame
- Revolute is one of the joints FreeCAD presolves: when its made, and every time Offset1/2 change, matchJCS snaps the part so the frames match exactly, turn and all. so Rotate in an assembly did nothing, it got snapped right back. the turn lives in the joint now, Offset2 = (0, 0, gap) turned by -spin, which also makes it show in the joint panel's rotation box. the panel reads it back off the joint before turning, in case it got turned there by hand
- aligning something again swaps out its old align joint (tagged VexAlign), the old one just dragged it back on the next solve
- nuts lost the "#8-32" and "(8-32, Steel)", hex screws are out of the screw tool, shoulder screws next once i know how the shoulder should fit

## 2026-10-30 - dots

- screws go into threads with no nut (standoffs, motors), and a spacer tool for boxed channel, both earlier that day
- the screw and spacer panels put orange dots on every screw hole, both sides of the metal, and a green one stays on what you picked. FreeCAD's own select highlight on a point was gone the second the mouse left it. dots refresh 100 ms after anything moves, gets placed or deleted, and stay out of the file on save (a save that fails too, no finish signal for that)
- screw holes = 8-32 round or ~0.182 square, open to the outside (a ray out of it), one per hole and side, and not when most of 5 rays down it stop in under 1/4 (the 11W case screws have heads 0.05 in). worked out once and kept on the source. 11W and 5.5W both get just their 2 front holes. the 11W takes ~3.4 s the first time, its 4773 faces
- screw placing 4.1 -> 0.4 s on 5x25 plates. f.OuterWire gets worked out again on *every* call, and holes() asked for it once per wire, so 250 holes on a face was 250 of them. 0.8 s -> 0.09 for holes() alone, plus hole loops and face boxes cached per source
- RootObjects leaves out a sub-assembly once something links to it, and RootObjectsIgnoreLinks does too once a link array's elements do. the parts list and the dots share library.roots() now, the old parts list filter. link array elements say Visibility False in the gui, the array's isElementVisible() is what counts
- star screw heads get vex's color code, 0.290 yellow to 2.500 brown, sampled off the pack picture. seam lines on round stuff get drawn in the face color instead of going Shaded, Shaded lost the spacer ends too and you couldnt tell where one stopped

## 2026-10-29 - screws

- screw tool. click the head side hole, then the nut side, shortest screw thats all the way through the nut + the nut. star or hex and which nut are in the panel, kept in prefs. vex's step nuts get stood up with derived.upright() same as mine. inside an assembly both get a Fixed joint to their hole, their frames sit right on the hole frames so solving moves nothing
- offscreen freecad hangs on close once any assembly joint has solved, a plain one with none of my code too, so the gui test os._exit()s. idk if a real window does it
- metal legs are flat faces now, holes as inner wires (no boolean), only edge stuff gets a 2D cut, then bends fused on. 1x5x1x35 3.05 -> 2.09 s, 3x3x35 angle 3.77 -> 2.17, 5x35 plate 1.24 -> 0.17, bar 0.53 -> 0.09. same volume to 6 decimels and same faces as before. the rest is the relief cuts in the bends and the fuse, so ~1 s isnt happening without something smarter

## 2026-10-28 - the metal is done

- aluminum 2x2 angles and aluminum plates arent a thing, so theyre gone. 869 generated now
- U-channel generator. 1.017 deep, 1.1417 tall (thats 29.0 mm, so 0.0157 more than 1.0 inside and a 2x c-channel slides in), 0.063 wall, two rows + the staggered one on all three sides. holes start 0.313 past the outside of a bend, which is 0.25 off the *inside*, same as the steel channel's 0.296 = 0.25 + 0.046. the web is a hair off center cuz of it. all 177 holes land on vex's
- bend reliefs are in. through the bend the walls are radial, on the legs they're a triangle straight through. unrolled its one diamond, except vex drew every file *dih*frently:

	| step | half width mid bend | k |
	|---|---|---|
	| 2x steel c | 0.0846 (stretched) | 0.135 |
	| 5x steel c | 0.0898 | 0.135 |
	| 2x2 steel angle | 0.0934 (stretched) | 0.41 |
	| 3x3 steel angle | 0.0898 | 0.41 |
	| al U | 0.0898 | 0.44 |
	| al 1x1 angle | 0.0934 (stretched) | 0.41 |

	so mine is the populer one, 45 deg, 0.0898, k = 0.44 (inventor's default, and the U on the nose). built as a ruled loft of radial rectangles every 15 deg, the chord error is ~0.00003. angles went from +0.26 to +0.78% to within 0.03%, the U +0.01%, the 2x steel channel +0.13% (its the stretched one). test tolerance 1% -> 0.2%

- the plain `BoundBox` is ~0.011 loose around the loft faces, the test uses `optimalBoundingBox()` now. had me thinking the reliefs made the parts *bigger* for a sec lol
- the bar's notch bottoms are r0.005, only the bottoms, the mouths and end chamfers are sharp and so are the plate's. the bar is face for face with vex now (48 r0.005s, 100 r0.02s, 254 planes)
- the reliefs cost time, a 1x5x1x35 channel is 3.1 s to build now (was 2.1), the 3x3x35 angle 3.6 (was 3.1)
- the 1x1 variants (2-wide, thick 5-wide, thin 5-wide) are only in the fusion library as f3d, and all i could get out of those is a 256 px thumbnail. so still no numbers

later, the small stuff

- `stock.py`, shafts, standoffs, spacers, washers and the extra-low nut. they're all one section pushed along z (a square with its corners turned and/or rounded, a hex, a circle), cut by a turned blank, minus a bore. every turned end vex drew is one arc in the radius / length profile, so `end = { x, z, r }` covers all of them: the LS shaft only clips its corners, the pitch shaft gets a bullet nose, the standoff a tiny round, and the HS shaft is an r5 mm sphere 4 mm in (a 3-4-5 triangle, metric under the hood lol). standoffs past 1" are blind, 0.5 deep each end. everything matched vex first run, LS shafts and spacers exact, standoffs and pitch shafts within 0.02%
- the "HS shafts run long" from the 26th was the loose bounding box again. the 2, 3 and 4" are actually 1 mm *short*, the 24" is right. mine are nominal
- `end` has to be a table, a list in the toml is an axis and it made 3 variants out of one shaft. caught it before it went in
- `derived.py`, parts cut out of a vex step. screws are vex's 1/2 screw stood up, head + a stub of shank and its tip kept, the tip moved out to length, my shank between. all 23 hex and star screws match vex dead on, so the torx recess never had to be drawn by hand. shoulder screws are the same with the 0.176 shoulder under the head, the thin nylock is vex's nylock shaved on the plain side (the toroids on the nylon end are still there, checked). every one comes out with the face that touches the part at z = 0, for the fastener tool later
- getting there: the bounding box (yes again) put the cuts in the wrong place, and the first cylinder on the star screw is a torx lobe, off the axis, so the shank came out crooked. the biggest cylinder is always on the axis
- frame on hole picks by distance to the loop now, not its center. clicking right on a motor screw hole's edge went to a vent 11 times in 58 by center, 0 by loop
- colors per material, `VexMass` from volume x density (a steel 1x2x1x10 is 48 g), and a Parts list button that fills a spreadsheet. step parts keep vex's own colors, but only through `ImportGui` with the gui up, `Import.insert` greys every face. so the motor is gold again
- `tests/test_gui.py` runs inside freecad offscreen. it hung at the end on the save prompt for the unsaved doc till the docs got closed first
- frame on hole on a shaft puts the frame on the axis at the end you clicked, they have no loop to find. a 2" LS shaft fixed to a channel hole sits 2e-16 mm off the hole axis, so dead center
- shoulder screw lengths showed up as python lists in the dock (`[0.29, 0.09]`), and `od` / `n` came out as Od / N. now "0.29, 0.09", OD and Holes
- HS spacers are a family of vex's own four steps. the catalog had a 3/8 off the fusion folders, but vex has no step for it so its gone, 868 now
- wait cursor while a part builds, a 35 long channel is a few seconds of frozen freecad otherwise
- a README for github
- found out how Assembly picks which way a Fixed joint faces: its presolve matches the two frames "matched or flipped", whichever is closer to how the parts sit when you make it, and the solver keeps that. so two channels can come out inside each other instead of face to face, the Reverse button fixes it. centers are exact either way. wrote it up in [using it](../using.md) with the rest of how to use the thing
- parts list walks the tree now, a sub-assembly linked twice counts 3 times with its original, and a link array counts every element. link array elements look top level too, which double counted an array of sub-assemblies till a second look caught it
- clicks on a link array element were getting turned into part coords with the array's placement, not the element's, so every element snapped like it was element 0. my first test for it passed anyway: setting `PlacementList` after `ElementCount` doesnt move anything with ShowElement on (each `LinkElement` has its own Placement), and the hole it picked was the last one, which is also where a click off the end falls back to. ugh. `picked()` takes the element's placement now, by index or by the element's name, and the test moves element 1 for real and picks the first hole
- the gui test checks the point `picked()` hands back now, not just where the frame lands, cuz a wrong point can still fall onto the right hole. through a linked sub-assembly (moved, turned, with the part moved inside it too) it comes out exact
- the dock search takes words in any order, and a family shows when any of its variants matches, so "1x2x1x25 steel" finds C-Channel and picking it starts on Steel / 2 / 25. `library.picks()` is the params -> labels half, `place()` uses it too
- why a 35 long channel takes 3 s: 2.95 of 3.12 is the one boolean cut, 1.83 of it just the 245 holes. cutting the holes leg by leg is no faster (2.01 vs 1.83). cutting the holes in 2D on a leg face and then extrudeing is 3.4x faster (0.39 vs 1.34 s for the web), so building the legs flat with their holes and fusing on the bends could get it to ~1 s. not worth tearing up the generator for tonight, its once per variant

## 2026-10-27 - how its gonna work

- went through how i want it to work and wrote it all down as [design choices](../design-choices/index.md): FreeCAD 1.1 only with the built in Assembly, generate what i can and ship steps for the rest, every part an `App::Part` with copies as `App::Link`s, nominal sizes, frames on exact hole centers with zero clearance, joints center, step parts get their holes found on import, the browser has common families at the root
- frames get made on click, not on every hole. a 1x5x1x35 channel would be 490 frames, ~3,400 objects, for *one* channel
- robosource washer numbers went in, steel small 0.354 OD / 0.169 bore / 0.031 and large 0.438 / 0.188 / 0.042, nylon 0.375 / 0.173 at 0.016, 0.032 and 0.062. the washer family is rows now, and vex's own two washers dont match any of them so theyre just step parts
- shoulder screws are torx, shoulder is 0.176 (a 0.182 hole leaves 0.006, so its a pivot pin), and the pairs are `[screw length, shoulder length]` under a `length` key. `size` only means shaft width now
- added the github remote

later, the actual workbench

- it shows up in FreeCAD 1.1 now, `freecad -M .` and theres a VEX workbench with an empty toolbar. package.xml, init_gui.py, an icon of a bit of c-channel
- `catalog.py` reads the toml into 939 generated parts + 289 steps in 29 ms, no FreeCAD. the drilled gears were two lists that had to line up, as an every-combo param that was 16 gears, rows now. family level `from` is `base` now so `from` only means a range start
- metal generator (`metal.py`). the section is built from its outside corners with real bends, holes cut per leg in one boolean, ~1 s for a 35 long channel. turns out vex's steps *do* have bends, i was wrong yesterday: **0.032 inside radius** on steel and al. also found
	- the holes on channels / angles / bar have 0.02 corners, the plates are sharp
	- every first hole past a bend is 0.296 from the outside of it, web holes are centered
	- the 2x c-channel and the 2x2 / 3x3 angles have a staggered row down the middle (that 104 = 35\*2 + 34 from yesterday), the 3x and 5x channels dont
	- plates have 0.127 diamonds on every grid point, the edge ones are the notches. the bar has the notches too but smaller (0.0798 deep), and its 0.056 thick
	- notches every 5 holes on the free edges *and* through the bends, little count marks. not in yet
- vs vex: plates 0.00%, bar -0.01%, angles and the 2x channel have every hole right and are +0.5 to +1.1% heavy till the count marks are in. the al channel steps are a different shape (0.55 tall, flange holes 0.3, ~~the 5x ones flare to 2.545~~ plain BoundBox lying, its 2.5) so theyre just reported. and vex's 5x steel channels have the web holes 0.24 from one side, mine are centered
- count marks are in on the free edges, and the tip chamfers on the cut ends (0.064 on the steel channel, 0.09 on the angles). angles are +0.26 to +0.78% now, the 2x steel channel +0.84%. whats left is the bend reliefs at the count marks, a 0.0898 x 0.0798 diamond wrapped round the inside of the bend, so helicoid sides. *bleh*
- parts can go in a document now. a VEX parts dock (families up top, greyed out till they have a generator, the fusion folders under, a search box), pick the options, Place. each variant gets one hidden `App::Part` source under "VEX parts", every placed one is a plain `App::Link` to it with the params as properties (Holes, Material, Size...). change one and a document observer points just that link at the other variant. had to be a plain `App::Link`, not `App::LinkPython`, the assembly code checks `TypeId == "App::Link"` exactly
- snap to hole works. click holes on placed parts, hit Frame on hole, and an LCS goes on each exact center, z out of the face, x along the length. the hole is the nearest inner loop on a flat face to where you clicked (anything up to 0.5" across), so round 8-32 holes on step parts *should* work too. the smart motor has 206 loops under 0.5" tho, most of them tiny detail, so a near miss could grab a vent or a logo. tried 4 of its screw holes: 0.02" off lands right every time, at 0.05" one of the 4 loses to a nieghbor loop. needs a size filter or something. the frame lives in the source, so every copy of that part has it. two channels on a Fixed joint frame to frame come out **0.0 mm** apart (`tests/test_snap.py`, headless, the Assembly module is fine without a gui) *Yippee.*

## 2026-10-26 - every V5 step, and the catalog

- `tools/fetch_vex_cad.py` pulls every V5 step off vexrobotics.com. headless got a cloudflare 403, so it drives my real firefox through selenium with my cookies in a temp profile (the real profile is 1.6 GB and locked while firefox is open). the search page is algolia with 5 searches on it, each with its own pages, so the next button is the one whose only page key is the cad one. counting cards from all 5 was 137 a page lol
- `tools/sort_vex_step.py` moves them into the fusion library folders, a regex table in order. "Drive Shaft Bar Lock" was landing in LS Shafts till the lock bar rule went first. 4 folders the fusion library doesnt have: Electronics/Legacy (Cortex), Kits, Tank Tread, the 2" mecanum V2s
- 289 steps total with the 13 packs i grabbed by hand
- catalog in `parts.toml`, 23 generated families + 90 step groups. measured off the real solids in FreeCAD, not guessed:
	- holes 0.182 square, 0.5 pitch, first center 0.25 from the end
	- wall: aluminum 0.062 (angle 0.063), steel 0.046. same outside, steel just thinner
	- no bend radius in vex's steps at all, the corners are sharp. todo, *bleh*
	- nylock 0.196 tall with the nylon on top, the thin one shaves 0.024 off the plain end to get 11/64
	- pitch shaft = n * 0.5 - 0.070, all 7 of them
	- HS shafts run long, 2.039 and 24.079, HS spacer isnt round (0.425 across)
	- steel washer 0.032, teflon 0.042, backwards from what the fusion library says
- the two 2x2x2x20 U-channel files are the same solid

---
Back to [code](index.md)
