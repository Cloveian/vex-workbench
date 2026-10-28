# Catalog
where every part gets written down

## Identify
the workbench needs one list of every part: the generated families with their numbers, and every step file with its sku and folder

### Relevant constraints/nice to haves:
- Edited by hand, a lot. new robosource part = a few lines, not code
- Comments, cuz half the numbers need a note on where they came from
- Readable by FreeCAD's python with nothing extra installed
- Diffs nicely in git

### What has to be managed/controlled
- Shared numbers (hole grid, wall thickness)
- Families: name and folder templates, what sizes exist, which steps they're checked against
- Step parts: sku, name, file, folder

### Gates

1. comments
2. no extra dependency inside FreeCAD

## Brainstorm

**Gate cuts:**

- JSON: no comments
- YAML: needs pyyaml, and its 'helpful' type guessing (no -> false) would bite a parts list at some point

**Survivors:**

- **A - TOML**
	`tomllib` is in python since 3.11, comments, `[[family]]` tables read nicely, numbers stay numbers
- **B - a python module of dicts**
	no parser at all, but its code, so a typo is a crash and anything could end up in there

## Select

| Criteria                  | **A: TOML** | B: python |
| ------------------------- | :---------: | :-------: |
| Hand editing              |    nice     |    ok     |
| Can only hold data        |     yes     |    no     |
| Other tools can read it   |     yes     |    meh    |


### Decision
A, one file, `freecad/vex_workbench/data/parts.toml`. inches everywhere (vex is all inches, FreeCAD gets mm at the last second).

how its laid out:

- `[grid]` and `[metal]` up top: 0.5 pitch, 0.182 square holes with 0.02 corners, first hole center 0.25 in from the end and 0.296 past the outside of a bend, aluminum 0.062 wall, steel 0.046, 0.032 inside bend radius, count notches 0.0798 deep every 5 holes
- a family can override any of those for itself (the plate's sharp holes, the bar's 0.056 steel), and the metal ones add their shape: `flange`, `between` for the staggered middle row, `diamond` for the plate / bar diamonds, `chamfer` for the tip corners on the cut ends of channels and angles
- `[[family]]` for each generated thing. `name` and `folder` are templates filled from the params (`"1x{width}x1x{holes} {material} C-Channel"`). a param is a list or a `{ from, to, step }` range, every combo is a part. a list of tables is rows, one part each (the washers, the drilled gears). `fixtures` = the vex steps it has to match. `base` = a step it's made out of (the thin nylock is the vex nylock with the plain end shaved down to 11/64)
- after `# --- step parts ---`, one `[[group]]` per folder with `{ sku, name, file }` rows. the 15 pneumatics parts have no sku

`size` is a shaft's width, `length` is a length (the shoulder screws have `[screw length, shoulder length]` pairs), `sizes` is rows, `from` is only ever a range start

---
Back to [design choices](index.md) | [goals](../goals.md)
