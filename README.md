# VEX Workbench

A FreeCAD 1.1 workbench for building VEX V5 robots in real CAD, with exact parts instead of 'close enough' ones.

It makes the parts and puts frames on hole centers, and FreeCAD's built-in Assembly workbench does the joints. Two channels jointed hole to hole land exactly on top of each other.

## What's in it

- **VEX parts dock** with a search box. The common families sit at the top, and everything else is in folders laid out like the Fusion 360 library. Pick the options, hit Place.
- **Generated parts**, built from the numbers in [`parts.toml`](freecad/vex_workbench/data/parts.toml) and checked against VEX's own files:
  - C-channel, U-channel, angles, plates and bars, every length up to 35 holes, with the bends, notches and bend reliefs
  - LS, HS and pitch shafts, standoffs, spacers and washers
  - hex and star (Torx) screws from 0.25 to 2.5 in long, Robosource shoulder screws, the thin nylock, and nuts in other materials
- **VEX's own STEP files** for everything else (motors, wheels, gears, electronics), with their colors.
- **Frame on hole**: click a hole (or the end of a shaft), and a frame goes on its exact center to joint to.
- **Editable placed parts**: change Holes or Size on a placed part and only that one changes. The same part placed 40 times is one model and 40 links.
- **Screw**: click a hole on the head side, then one on the nut side, and it puts in the shortest screw that makes it through the nut, plus the nut.
- **Colors and weights** per material, and a **Parts list** button that counts everything into a spreadsheet.

Still to come: washers and spacers in the screw tool, and bending metal.

## Running it

You need FreeCAD 1.1. From the repo:

```
freecad -M .
```

then pick the VEX workbench.

Most generated parts work right away. VEX's STEP files aren't in the repo, so the step parts (and the screws, the thin nylock, the other-material nuts, HS spacers and license plates, which all start from one of VEX's files) need them downloaded first:

```
uv run tools/fetch_vex_cad.py
python tools/sort_vex_step.py --apply
```

The first one drives Firefox through VEX's CAD search with your Firefox cookies and downloads every V5 file into `downloads/vex-v5/`. If a bot check comes up, do it in the Firefox window and it carries on. The second sorts them into `vex-step/`, and needs `gh` (the GitHub CLI) to read the Fusion 360 library's folders.

## Tests

```
python tests/test_catalog.py
python tests/test_metal.py
python tests/test_parts.py
python tests/test_library.py
python tests/test_snap.py
env QT_QPA_PLATFORM=offscreen freecad -M . tests/test_gui.py
```

Run them one at a time, with a python that can `import freecad` (the system one, if FreeCAD came from your package manager). All of them except `test_catalog.py` need FreeCAD, and all but `test_catalog.py` and `test_snap.py` need `vex-step/`.

## Docs

[How to use it](docs/using.md) covers placing parts, snapping and joints. The design notes, roadmap and dev log are in [`docs/`](docs/index.md), as an mkdocs site (`mkdocs serve`, with mkdocs-material).
