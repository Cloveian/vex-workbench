# Log

## 2026-10-27 - how its gonna work

- went through how i want it to work and wrote it all down as [design choices](../design-choices/index.md): FreeCAD 1.1 only with the built in Assembly, generate what we can and ship steps for the rest, every part an `App::Part` with copies as `App::Link`s, nominal sizes, frames on exact hole centers with zero clearance, joints center, step parts get their holes found on import, the browser has common families at the root
- frames get made on click, not on every hole. a 1x5x1x35 channel would be 490 frames, ~3,400 objects, for *one* channel. thats my default, not settled
- robosource washer numbers went in, steel small 0.354 OD / 0.169 bore / 0.031 and large 0.438 / 0.188 / 0.042, nylon 0.375 / 0.173 at 0.016, 0.032 and 0.062. the washer family is rows now, and vex's own two washers dont match any of them so theyre just step parts
- shoulder screws are torx, shoulder is 0.176 (a 0.182 hole leaves 0.006, so its a pivot pin), and the pairs are `[screw length, shoulder length]` under a `length` key. `size` only means shaft width now
- added the github remote

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
