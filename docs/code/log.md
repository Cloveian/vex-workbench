# Log

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

- screw tool. click the head side hole, then the nut side, shortest screw thats all the way through the nut + the nut. star or hex and which nut are in the panel, kept in prefs. vex's step nuts get stood up with derived.upright() same as ours. inside an assembly both get a Fixed joint to their hole, their frames sit right on the hole frames so solving moves nothing
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

	so ours is the populer one, 45 deg, 0.0898, k = 0.44 (inventor's default, and the U on the nose). built as a ruled loft of radial rectangles every 15 deg, the chord error is ~0.00003. angles went from +0.26 to +0.78% to within 0.03%, the U +0.01%, the 2x steel channel +0.13% (its the stretched one). test tolerance 1% -> 0.2%

- the plain `BoundBox` is ~0.011 loose around the loft faces, the test uses `optimalBoundingBox()` now. had me thinking the reliefs made the parts *bigger* for a sec lol
- the bar's notch bottoms are r0.005, only the bottoms, the mouths and end chamfers are sharp and so are the plate's. the bar is face for face with vex now (48 r0.005s, 100 r0.02s, 254 planes)
- the reliefs cost time, a 1x5x1x35 channel is 3.1 s to build now (was 2.1), the 3x3x35 angle 3.6 (was 3.1)
- the 1x1 variants (2-wide, thick 5-wide, thin 5-wide) are only in the fusion library as f3d, and all i could get out of those is a 256 px thumbnail. so still no numbers

later, the small stuff

- `stock.py`, shafts, standoffs, spacers, washers and the extra-low nut. they're all one section pushed along z (a square with its corners turned and/or rounded, a hex, a circle), cut by a turned blank, minus a bore. every turned end vex drew is one arc in the radius / length profile, so `end = { x, z, r }` covers all of them: the LS shaft only clips its corners, the pitch shaft gets a bullet nose, the standoff a tiny round, and the HS shaft is an r5 mm sphere 4 mm in (a 3-4-5 triangle, metric under the hood lol). standoffs past 1" are blind, 0.5 deep each end. everything matched vex first run, LS shafts and spacers exact, standoffs and pitch shafts within 0.02%
- the "HS shafts run long" from the 26th was the loose bounding box again. the 2, 3 and 4" are actually 1 mm *short*, the 24" is right. ours are nominal
- `end` has to be a table, a list in the toml is an axis and it made 3 variants out of one shaft. caught it before it went in
- `derived.py`, parts cut out of a vex step. screws are vex's 1/2 screw stood up, head + a stub of shank and its tip kept, the tip moved out to length, our shank between. all 23 hex and star screws match vex dead on, so the torx recess never had to be drawn by hand. shoulder screws are the same with the 0.176 shoulder under the head, the thin nylock is vex's nylock shaved on the plain side (the toroids on the nylon end are still there, checked). every one comes out with the face that touches the part at z = 0, for the fastener tool later
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

- went through how i want it to work and wrote it all down as [design choices](../design-choices/index.md): FreeCAD 1.1 only with the built in Assembly, generate what we can and ship steps for the rest, every part an `App::Part` with copies as `App::Link`s, nominal sizes, frames on exact hole centers with zero clearance, joints center, step parts get their holes found on import, the browser has common families at the root
- frames get made on click, not on every hole. a 1x5x1x35 channel would be 490 frames, ~3,400 objects, for *one* channel. thats my default, not settled
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
- vs vex: plates 0.00%, bar -0.01%, angles and the 2x channel have every hole right and are +0.5 to +1.1% heavy till the count marks are in. the al channel steps are a different shape (0.55 tall, flange holes 0.3, the 5x ones flare to 2.545) so theyre just reported. and vex's 5x steel channels have the web holes 0.24 from one side, ours are centered
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
