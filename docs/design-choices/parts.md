# Parts
what one placed part actually is in the FreeCAD tree

## Identify
a placed part has to be something the Assembly joints can grab, that can be edited after, and that doesnt cost a full copy every time it's used

### Relevant constraints/nice to haves:
- Assembly joints walk the reference down through `App::Part` containers but stop at the first `Part::Feature` (`UtilsAssembly.getObject`), so frames inside a bare solid can't be reached
- Editable: change `holes` from 25 to 20 and it rebuilds right where it is
- A robot has like 200 screws, they can't each be their own solid
- Frames have to move with the part

### What has to be managed/controlled
- The solid
- Its params (holes, length, material...)
- Its snap frames
- Copies

### Gates

1. joints can reach the frames
2. editable after placing

## Brainstorm

**Gate cuts:**

- bare `Part::Feature` solid, frames next to it in a group: joints cant tell which solid a frame belongs to, and they don't move with it
- a plain imported solid with no params: fails 2

**Survivors:**

- **A - copies**
	an `App::Part` holding a parametric solid + its frames, every placement its own copy. simple, edit just that one. 200 screws = 200 solids tho
- **B - links**
	same `App::Part`, but placements are `App::Link`s to one source per variant. one 0.5" screw solid, 200 links to it. editing a placed copy points that link at a *dih*frent variant (made if it doesn't exist yet), so the other 199 stay put

## Select

| Criteria                 | A: copies | **B: links** |
| ------------------------ | :-------: | :----------: |
| Joints reach the frames  |    yes    |     yes      |
| 200 screws               |   heavy   |    light     |
| Parts list               |  count by name | count links |
| Edit one placed part     |   easy    | swap its link |


### Decision
B. each variant is an `App::Part` with the generated solid (a `Part::FeaturePython` with the params as properties) and its frames, and every placement is an `App::Link` to it.

Where the sources live isn't settled. my default is a hidden group inside the same document, so a robot is still one `.FCStd` and nothing breaks when the file moves. a separate library file would share them between robots but then every robot depends on it being there

Color and weight sit on the source too, so every link has them: a color per material (or per color, for the license plates, and vex's own colors on step parts) and `VexMass` = volume \* density. only generated parts with a material get a weight, a motor isnt one block of anything. the parts list counts links by name into a spreadsheet in the document. also my defaults, not settled

---
Back to [design choices](index.md) | [goals](../goals.md)
