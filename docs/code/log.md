# Log

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
- snap to hole works. click holes on placed parts, hit Frame on hole, and an LCS goes on each exact center, z out of the face, x along the length. the hole is the nearest inner loop on a flat face to where you clicked (anything up to 0.5" across), so round 8-32 holes on step parts *should* work too, not checked yet. the smart motor has 206 loops under 0.5" tho, most of them tiny detail, so a near miss could grab a vent or a logo. needs a size filter or something. the frame lives in the source, so every copy of that part has it. two channels on a Fixed joint frame to frame come out **0.0 mm** apart (`tests/test_snap.py`, headless, the Assembly module is fine without a gui) *Yippee.*

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
