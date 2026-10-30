# Using it
how to actually build something with it, as it is right now

## Placing parts

Pick the VEX workbench and hit **VEX parts** to open the dock. The families are at the top (greyed out ones dont have a generator yet), vex's own parts are in the folders under them, and the search box filters both. Pick a family, set its options, then **Place** (or just double-click). If theres an active assembly (or part) it goes in there.

- the first time a variant gets placed it has to be built, a 35 long channel takes a few seconds (theres a wait cursor). after that its instant, every copy in that file links to the same source
- a placed part has its options in its properties, under VEX. change Holes or Size or whatever and *just that one* swaps to the other variant, the rest stay put
- vex's step parts keep vex's colors, generated ones get a color per material (the license plates by their color)

## Snapping

Click one or more holes, then **Frame on hole**. Each one gets a frame on its exact center, z out of the face you clicked and x along the length.

- clicking right on the edge of the hole is the sure way. on step parts with a lot of little detail (the motor is covered in vents) a click on the face *near* a hole can still grab a tiny loop next to it
- shafts have no hole, so on a shaft (and standoffs, spacers, washers) the frame goes on the axis at whichever end you clicked closer to
- screws: click the underside of the head, the shank is the hole there, so the frame lands where the head sits. nuts: the bore
- frames live in the part's source, so every copy of that part has them, and clicking the same hole again just gives the same frame back
- link arrays and linked sub-assemblies work too, click the hole on whichever copy you mean and it lands on that one

Then over in the Assembly workbench, joint two frames together (Fixed for bolted stuff). The joint picks whether the two z axes point the same way or opposite from how the parts sit when you make it, so if they come out *inside* each other instead of face to face, hit **Reverse** in the joint panel. either way the centers land exactly on each other.

## Screws

**Screw** opens a panel with the screw (Star or Hex) and the nut to use, it remembers both. click a hole on the head side, then the one on the nut side (the outside faces), and in goes the shortest screw that reaches all the way through the nut, nut and all. it stays open for the next one till you hit Close. with an assembly active they go in it, each with a Fixed joint to its hole.

Pick No nut, or click a threaded hole second (standoffs, and anything under 0.164 across like the motors), and the second click is the face the screw goes *into*. it aims for 3/8 of thread, takes 1/4 if the hole is shallower, and never goes past the bottom. Spacers in gaps fills every gap between the two clicked parts.

**Spacers** does just the filling: click holes on two faces across from each other, fewest spacers + washers within 1/64 under the gap, never over. spacer OD is a setting, 0.375 to start.

While either panel is open every hole gets an orange point on both sides of the metal, plus the ends of shafts and standoffs. on vex's step parts its only 8-32 sized holes a screw can get to from outside, so the motors get their screw holes and not the vents. click a point and its exactly that hole, it goes green till the second click. screws, nuts, spacers and washers dont get points, and the points all go away on Close. clicking a face still works too (nearest hole), and parts placed while the panel is open only get points next time it opens.

## Parts list

**Parts list** counts every placed VEX part by name into a spreadsheet in the document ("VEX parts list"), with the weight of each and the total. vex's step parts and the license plates have no material, so they show a ? and get counted at the bottom. it counts every element of a link array and every copy of a linked sub-assembly too.

## Not there yet

bending, the HS lockbar, drilled gears and the 1x1 angle variants (theres no numbers for those three yet).

---
Back to [main index](index.md)
