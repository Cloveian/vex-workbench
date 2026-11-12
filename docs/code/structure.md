# Structure

## Layout

| path                               | what                                                                  |
| ---------------------------------- | --------------------------------------------------------------------- |
| `freecad/vex_workbench/`           | the workbench itself (new style addon, FreeCAD finds it by this path) |
| `freecad/vex_workbench/init_gui.py` | registers the workbench, gui only                                    |
| `freecad/vex_workbench/catalog.py` | `parts.toml` -> every part, no FreeCAD needed                         |
| `freecad/vex_workbench/metal.py`   | channels, angles, plate, bar, HS lockbars as Part shapes, and the bends, cuts and drilled holes on them |
| `freecad/vex_workbench/stock.py`   | shafts, standoffs, spacers, washers, plain and flange nuts: a section with lathe ends and a bore |
| `freecad/vex_workbench/derived.py` | parts cut out of a vex step: screws at any length, the thin nylock, the 3/8 HS spacer, other materials |
| `freecad/vex_workbench/chain.py` | Chain command and its math: tangent lines and arcs round the sprockets (a negative radius wraps the other way, for an idler), pins a straight pitch apart along that by bisection, a link frame on each, all one link array. which way an idler wraps comes off the click order, a corner turning back against the loop |
| `freecad/vex_workbench/chainlink.py` | chain links, the 6P one off the fusion library's in round mm numbers. side plates joggled so the next link's peg goes in this one's outer tab |
| `freecad/vex_workbench/flexwheel.py` | the 1.625 and 2 in flex wheels: disc, 3/8 hex bore, windows between straight spokes. all round mm off fusion's |
| `freecad/vex_workbench/rail.py` | linear slide rail: the bent section with its walls leaning in, metal grid holes down the base, 45 deg chamfers off the wall tops at the ends |
| `freecad/vex_workbench/slide.py` | slide trucks: fusion's section as a point table pushed along y, pockets up between the ribs and bosses, both ends chamfered round. drafts and the 0.3 mm rib fillets left off |
| `freecad/vex_workbench/versahex.py` | VersaHex adapters, a turned 1/2 hex and a flange round a 1/4 square bore (the 0.5 one has two slots under its flange). the chamfers are ruled lofts off the section and its offset |
| `freecad/vex_workbench/library.py` | parts in a document: hidden source per variant, placed copies are `App::Link`s. steps read once into freecad's cache folder as brep (`remembered`). hole finding too (`holes`, `hole_at`, `hole_dots` kept on the source, `cached` per source). a size change or shop step moves frames and joints on holes that stayed put or turned with a bend onto the new source (`carry`, the bends from `metal.turned`), and joints straight on a face / edge / corner to whatever of it is left (`element`) and deletes the old worked one once nothing links it (`prune`) |
| `freecad/vex_workbench/browser.py` | the VEX parts dock                                                    |
| `freecad/vex_workbench/snap.py`    | Frame on hole command, clicked spot -> `library.hole_frame`. plus the joint bits and the click panel (orange hole points, yellow under the mouse, green picked ones) the screw, spacer, align, joint, chain and shop tools build on. screen spots for every dot are one numpy matmul |
| `freecad/vex_workbench/screws.py`  | Screw command, two hole clicks -> shortest screw + nut (or into a thread), jointed in an assembly |
| `freecad/vex_workbench/spacers.py` | Spacers command, fills a gap between two holes with spacers + washers |
| `freecad/vex_workbench/align.py`   | Align command, hole on one part onto a hole on another, faces together, then turned, gapped or flipped over onto the hole's other face. no joints |
| `freecad/vex_workbench/joints.py`  | Joint command, two hole clicks (three for a slide) -> a Revolute, Fixed or Slider set off where the parts already are |
| `freecad/vex_workbench/inserts.py` | shaft inserts in HS bores, their own link with Placement = the gear's x `VexSeat` as an expression. the gear knows it by name in `VexInsert`, a link back would be a dependency loop |
| `freecad/vex_workbench/duplicate.py` | Duplicate command, copies of links and groups mirrored or turned. a mirror is world reflection x placement x the part's own middle-plane reflection, so its a turn |
| `freecad/vex_workbench/shop.py`    | Bend, Cut and Drill commands, kept on the link as VexSteps in order. the geometry is `metal.work` (fold, cut, slot, sketch, drill). a cut sketch stays in the doc attached to its link, `shop.Sketches` redoes its step when sketch edit closes |
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
| `tools/read_f3d.py`                | `.f3d` -> step, for measuring the fusion library's parts. a modeled thread still doesnt sew |
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
