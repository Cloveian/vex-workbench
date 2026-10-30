# Structure

## Layout

| path                               | what                                                                  |
| ---------------------------------- | --------------------------------------------------------------------- |
| `freecad/vex_workbench/`           | the workbench itself (new style addon, FreeCAD finds it by this path) |
| `freecad/vex_workbench/init_gui.py` | registers the workbench, gui only                                    |
| `freecad/vex_workbench/catalog.py` | `parts.toml` -> every part, no FreeCAD needed                         |
| `freecad/vex_workbench/metal.py`   | channels, angles, plate, bar as Part shapes                           |
| `freecad/vex_workbench/stock.py`   | shafts, standoffs, spacers, washers: a section with lathe ends and a bore |
| `freecad/vex_workbench/derived.py` | parts cut out of a vex step: screws at any length, the thin nylock, other materials |
| `freecad/vex_workbench/library.py` | parts in a document: hidden source per variant, placed copies are `App::Link`s |
| `freecad/vex_workbench/browser.py` | the VEX parts dock                                                    |
| `freecad/vex_workbench/snap.py`    | Frame on hole command, clicked spot -> `library.hole_frame`. plus the Fixed joint bits and the two-click panel screws and spacers build on |
| `freecad/vex_workbench/screws.py`  | Screw command, two hole clicks -> shortest screw + nut (or into a thread), jointed in an assembly |
| `freecad/vex_workbench/spacers.py` | Spacers command, fills a gap between two holes with spacers + washers |
| `freecad/vex_workbench/ui.py`      | undo step, wait cursor and error box around building parts |
| `freecad/vex_workbench/partslist.py` | Parts list command, links counted by name into a spreadsheet         |
| `freecad/vex_workbench/data/parts.toml` | the [catalog](../design-choices/catalog.md)                      |
| `freecad/vex_workbench/resources/icons/` | the workbench and command icons                                 |
| `package.xml`                      | addon manager metadata                                                |
| `tests/`                           | `python tests/test_catalog.py` and so on, `test_gui.py` runs inside freecad (`env QT_QPA_PLATFORM=offscreen freecad -M . tests/test_gui.py`) |
| `tools/fetch_vex_cad.py`           | pulls every V5 step off vexrobotics.com, `uv run` it                  |
| `tools/sort_vex_step.py`           | sorts the downloads into the fusion library folders, `--apply` moves them |
| `vex-step/`                        | the 289 steps, gitignored                                             |
| `downloads/`                       | raw downloads + `manifest.csv`, gitignored                            |
| `docs/`                            | this                                                                  |

the fetch script drives my real firefox (selenium + geckodriver) with my cookies copied into a temp profile, cuz vex is behind cloudflare and anything headless gets a 403. it clicks through the cad results pages and skips anything already in `vex-step/` (by name or sku)

## Testing

- anything that doesnt need FreeCAD (the catalog reader) is plain python, asserts top to bottom, no pytest. the test imports `catalog` straight from its folder, cuz the system `freecad` package loads FreeCAD on import and then it isnt FreeCAD free anymore
- geometry tests import `freecad` on purpose, that puts FreeCAD on the path so plain `python` runs them. generated parts get checked against their fixture steps (volume, bounding box and hole centers, in inches)

---
Back to [code](index.md)
