# Part browser
how a part gets picked and placed

## Identify
there's 23 families and 289 step parts and growing. finding a 1x2x1x25 steel c-channel shouldn't take a minute

### Relevant constraints/nice to haves:
- The common stuff (channels, screws, nuts, shafts, spacers) gets used constantly
- The fusion library's folders are what i already know my way around
- Generated families need their params picked before placing (holes, length, material)

### What has to be managed/controlled
- Finding a part
- Picking its size
- Placing it

### Gates

1. common parts in one or two clicks

## Brainstorm

**Survivors:**

- **A - a dialog**
	pick family, fill in the numbers, ok. quick for generated parts, useless for 289 step files
- **B - a tree in the fusion folders**
	everything findable, but a channel is 4 folders deep
- **C - both kinda**
	one tree. the common families sit right at the root, the fusion folders below them for everything else. clicking a family opens its options, clicking a step part just places it

## Select

| Criteria             | A: dialog | B: tree | **C: both** |
| -------------------- | :-------: | :-----: | :---------: |
| Common parts quick   |    yes    |   no    |     yes     |
| Step parts findable  |    no     |   yes   |     yes     |


### Decision
C. common families at the root, fusion layout folders for the rest, family -> options -> place.

---
Back to [design choices](index.md) | [goals](../goals.md)
