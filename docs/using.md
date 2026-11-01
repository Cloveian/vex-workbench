# Using it
how to actually build something with it, as it is right now

## Placing parts

Pick the VEX workbench and hit **VEX parts** to open the dock. The families are at the top (greyed out ones dont have a generator yet), vex's own parts are in the folders under them, and the search box filters both. Pick a family, set its options, then **Place** (or just double-click). If theres an active assembly (or part) it goes in there.

- the first time a variant gets placed it has to be built, a 35 long channel takes a few seconds (theres a wait cursor). after that its instant, every copy in that file links to the same source
- a placed part has its options in its properties, under VEX. change Holes or Size or whatever and *just that one* swaps to the other variant, the rest stay put
- vex's step parts keep vex's colors, generated ones get a color per material (the license plates by their color). star screws get the head color vex's color coded pack has for that length, 0.290 yellow up to 2.500 brown (no 0.25 in the pack, so thats plain steel). the seam line down round generated stuff (screws, standoffs, spacers, washers, extra low nuts, HS and pitch shafts) is drawn in the part's own color so it doesnt show, the ends keep their lines so you can see where one spacer stops and the next starts

## Snapping

Click one or more holes, then **Frame on hole**. Each one gets a frame on its exact center, z out of the face you clicked and x along the length.

- clicking right on the edge of the hole is the sure way. on step parts with a lot of little detail (the motor is covered in vents) a click on the face *near* a hole can still grab a tiny loop next to it
- shafts have no hole, so on a shaft (and standoffs, spacers, washers) the frame goes on the axis at whichever end you clicked closer to
- screws: click the underside of the head, the shank is the hole there, so the frame lands where the head sits. nuts: the bore
- frames live in the part's source, so every copy of that part has them, and clicking the same hole again just gives the same frame back
- link arrays and linked sub-assemblies work too, click the hole on whichever copy you mean and it lands on that one

Then over in the Assembly workbench, joint two frames together (Fixed for bolted stuff). The joint picks whether the two z axes point the same way or opposite from how the parts sit when you make it, so if they come out *inside* each other instead of face to face, hit **Reverse** in the joint panel. either way the centers land exactly on each other.

## Hole dots

All the clicking tools (Align, Screw, Spacers, Bend, Cut, Drill) put an orange dot on every hole while their panel is open, on both sides of the metal, plus the ends of shafts and standoffs. on vex's step parts its only 8-32 sized holes a screw can get to from outside, so the motors get their screw holes and not the vents. click a dot and its exactly that hole, a bigger green dot stays on it till the tool's done (face clicks get one on the hole they picked too). screws, nuts, spacers and washers dont get dots, and the dots all go away on Close. clicking a face still works too (nearest hole, except on Drill, where the click is the spot it drills). parts placed, moved or deleted while a panel is open get their dots sorted out a moment after.

## Align

**Align** does what Snapping does in two clicks, without any frames: click a hole on the part you want to move, then the hole on the part it goes against, and it jumps over so the holes line up and the faces sit flat on each other. it keeps the way the part was already turned, rounded to the angle box, so a fresh part comes out square to the other one. **Rotate -** / **Rotate +** turn the last one around the hole by the angle in the box (90 to start, anything works, + is counterclockwise looking at the face it went against), and **Gap** holds it that far off the other face (under 0 pushes it in, like a shaft end going through a hole), both work after its moved. with an assembly active it gets a Revolute joint between the two holes, so it can still spin, and the gap and turn show up as the joint's offset and rotation. lining the same thing up somewhere else swaps that joint for the new one, the old one would just drag it back. click a hole on one element of a link array and the whole array moves so that element's hole lands. tick **Move its whole group** and it moves the Part (or sub-assembly) the clicked part is in instead, the top one under the active assembly, so a whole drive side goes over in one go and everything in it stays where it was in it.

## Screws

**Screw** opens a panel with the screw (Star or Shoulder) and the nut to use, it remembers both. click a hole on the head side, then the one on the nut side (the outside faces), and in goes the shortest screw that reaches all the way through the nut, nut and all. it stays open for the next one till you hit Close. with an assembly active they go in it, each with a Revolute joint to its hole, so it can spin on it.

Pick No nut, or click a threaded hole second (standoffs, and anything under 0.164 across like the motors), and the second click is the face the screw goes *into*. it aims for 3/8 of thread, takes 1/4 if the hole is shallower, and never goes past the bottom. Spacers in gaps fills every gap between the two clicked parts.

Tick **Pick the screw myself** and pick one from the list next to it, then its one click: the hole it goes in, head on that face, no nut and no spacers. Shoulder screws only go in this way, the shoulder length is your call.

**Spacers** does just the filling: click holes on two faces across from each other, fewest spacers + washers within 1/64 under the gap, never over. spacer OD is a setting, 0.375 to start.

## Bending, cutting, drilling

**Bend** folds any VEX metal part on a line through a hole: click the hole (same dots), and it bends there by the **Angle** (90 to start, + folds toward the face you clicked, - away from it). **Line** picks across the length or along it, **Off the hole** slides the line over (0.25 puts it between two rows), and **Other side turns** swaps which side moves, the shorter one moves to start. all of those redo the last bend till you click the next hole. inside radius 0.032 like vex's own bends, so a 90 eats about 0.08" of flat.

Only that one copy bends, the rest stay straight, and it still counts as the straight part in the parts list (thats what you buy). change Holes on it and it keeps its bends (a cut or hole past a shorter new end gets dropped, with a warning in the report view). channels bend too, flanges and all, which real metal wont do without cutting them first, so thats on you :P. only away from the flanges tho, folding the web into its own flanges gets refused (angles the same with their other leg)

**Cut** works on the same kind of line (Line, Off the hole), the smaller side goes and **Keep the other side** swaps it. across through a hole is cut to length, along a flange cuts just that flange (the far one stays). slide the line 0.25 over from a flange's hole row (one way or the other, whichever lands on the web) and the whole flange comes off flush, do both and the web can fold toward where the flanges were. sawn edge, no notches or chamfers. a cut that would leave it in two pieces gets refused.

**Drill** puts a round hole through the wall where you click, **Size** across (0.17 to start, 8-32 clearance). it snaps to the 0.25 grid off the nearest hole on that face, hold Shift to drill right where you clicked. a drilled 8-32 hole gets a dot like any other. on a plate the grid spots between holes already have little square holes, so drilling one of those just opens it up.

bends, cuts and drilled holes all go on that copy in the order you did them, and it still counts as the plain part. joints on its holes dont carry over any of them, so do the shop work before screwing things on.

## Parts list

**Parts list** counts every placed VEX part by name into a spreadsheet in the document ("VEX parts list"), with the weight of each and the total. vex's step parts and the license plates have no material, so they show a ? and get counted at the bottom. it counts every element of a link array and every copy of a linked sub-assembly too.

## Not there yet

the HS lockbar and drilled gears (theres no numbers for them yet).

---
Back to [main index](index.md)
