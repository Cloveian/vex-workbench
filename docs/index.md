# VEX Workbench
A FreeCAD workbench for building VEX V5 robots

## Why?
Protobot is 'close enough' cad, and i want *real* cad, where a robot can be designed to exact tolerances and what's on screen is what gets built. the fusion library is the other option but it's fusion, and its files have no license on them.

## How
Meth.
FreeCAD 1.1 already has an assembly workbench with joints built in, so the workbench only has to make the parts and give them good things to snap to

## What
- parts that are just numbers (metal, shafts, screws, nuts, spacers...) get generated from a toml catalog, at whatever size
- everything else (motors, wheels, gears, electronics) is vex's own step files
- snap frames at exact hole centers, then the built in Assembly joints do the rest
- a screw tool, two clicks and there's a screw and nut in (or no nut into a thread), and a spacer tool for the gaps
- an align tool, two clicks and a part is sitting flat on another one hole to hole, then turn it or gap it. later: bending metal

---

[using it](using.md) is how to build something with it. for how it got this way, start at [goals](goals.md), the [design choices](design-choices/index.md) are in the order i made them. the [log](code/log.md) is where i'm at right now
