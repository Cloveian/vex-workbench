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
| `freecad/vex_workbench/library.py` | parts in a document: hidden source per variant, placed copies are `App::Link`s. hole finding too (`holes`, `hole_at`, `screw_holes` kept on the source, `cached` per source). a size change or shop step moves frames and joints on holes that stayed put onto the new source (`carry`) and deletes the old worked one once nothing links it (`prune`) |
| `freecad/vex_workbench/browser.py` | the VEX parts dock                                                    |
| `freecad/vex_workbench/snap.py`    | Frame on hole command, clicked spot -> `library.hole_frame`. plus the joint bits and the click panel (orange hole points, green picked ones) the screw, spacer, align and shop tools build on |
| `freecad/vex_workbench/screws.py`  | Screw command, two hole clicks -> shortest screw + nut (or into a thread), jointed in an assembly |
| `freecad/vex_workbench/spacers.py` | Spacers command, fills a gap between two holes with spacers + washers |
| `freecad/vex_workbench/align.py`   | Align command, hole on one part onto a hole on another, faces together, then turned or gapped, Revolute joint in an assembly |
| `freecad/vex_workbench/shop.py`    | Bend, Cut and Drill commands, kept on the link as VexSteps in order. the geometry is `metal.work` (fold, cut, drill) |
| `freecad/vex_workbench/ui.py`      | undo step, wait cursor and error box around building parts, number boxes for the panels, and the toolbar buttons that open them |
| `freecad/vex_workbench/partslist.py` | Parts list command, links counted by name into a spreadsheet         |
| `freecad/vex_workbench/data/parts.toml` | the [catalog](../design-choices/catalog.md)                      |
| `freecad/vex_workbench/resources/icons/` | the workbench and command icons                                 |
| `freecad/vex_workbench/steps/` | the 209 vex steps that ship, gzipped. `catalog.step_file` unzips one into a temp file to read |
| `package.xml`                      | addon manager metadata                                                |
| `tests/`                           | `python tests/test_catalog.py` and so on, `test_gui.py` runs inside freecad (`env QT_QPA_PLATFORM=offscreen freecad -M . tests/test_gui.py`) |
| `tools/fetch_vex_cad.py`           | pulls every V5 step off vexrobotics.com, `uv run` it                  |
| `tools/sort_vex_step.py`           | sorts the downloads into the fusion library folders, `--apply` moves them |
| `tools/ship_steps.py`              | zips the shipped set out of `vex-step/` into the package, drops ones that stopped shipping |
| `tools/render_shots.py`            | the README images, rendered with no window into `downloads/`          |
| `vex-step/`                        | all 289 steps, gitignored. the tests' fixtures and anything that doesnt ship |
| `LICENSE`                          | LGPL-2.1-or-later, the workbench only. vex's steps are theirs                  |
| `downloads/`                       | raw downloads + `manifest.csv`, gitignored                            |
| `docs/`                            | this                                                                  |

the fetch script drives my real firefox (selenium + geckodriver) with my cookies copied into a temp profile, cuz vex is behind cloudflare and anything headless gets a 403. it clicks through the cad results pages and skips anything already in `vex-step/` (by name or sku)

## Testing

- anything that doesnt need FreeCAD (the catalog reader) is plain python, asserts top to bottom, no pytest. the test imports `catalog` straight from its folder, cuz the system `freecad` package loads FreeCAD on import and then it isnt FreeCAD free anymore
- geometry tests import `freecad` on purpose, that puts FreeCAD on the path so plain `python` runs them. generated parts get checked against their fixture steps (volume, bounding box and hole centers, in inches)

---
Back to [code](index.md)
