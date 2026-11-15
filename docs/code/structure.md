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
| `freecad/vex_workbench/chainlink.py` | chain links, 6P and 3P off the fusion library's in round mm numbers (3P's step edges lean, its side view waists in and its peg tips are beveled). side plates joggled so the next link's peg goes in this one's outer tab |
| `freecad/vex_workbench/flexwheel.py` | flex wheels. 1.625 and 2 in: disc, 3/8 hex bore, windows between straight spokes, all round mm off fusion's. 3 and 4 in: 28 mm versahub bore, bolt circle, and fusion's window and slot outlines as point tables |
| `freecad/vex_workbench/rail.py` | linear slide rail: the bent section with its walls leaning in, metal grid holes down the base, 45 deg chamfers off the wall tops at the ends |
| `freecad/vex_workbench/slide.py` | slide trucks: fusion's section as a point table pushed along y (`section` is the big flex wheels' and versahub's too), pockets cut between the ribs and bosses (the outer one's cross ribs and bosses go back in as the solid section). drafts and the 0.3 mm rib fillets left off |
| `freecad/vex_workbench/ratchet.py` | the ratchet gear: 25 sawtooth teeth, both pockets revolved off an (r, y) profile with their draft and floor rounds, bosses and the hub fused back, built round z and turned onto y like fusion's. and the winch pawl: its section halfway up one drafted half pushed through, the window pocketed from both faces, the arm end beveled off both |
| `freecad/vex_workbench/versahex.py` | VersaHex adapters, a turned 1/2 hex and a flange round a 1/4 square bore (the 0.5 one has two slots under its flange). the chamfers are ruled lofts off the section and its offset |
| `freecad/vex_workbench/sprocket.py` | 3P sprockets, 10T, 15T, 24T, 40T and 48T: one tooth gap per size as a point table off fusion's, turned round, on a 2 mm plate with 45 deg tip chamfers, a hub and the 1/8 square bore. the bigger ones thinner web and swirl windows are their own tables, the 40T and 48T ring rib and 4 bosses too (front on the 40T, back on the 48T) |
| `freecad/vex_workbench/omni.py` | the 2.75 legacy omni: a hub (two sides of a ring with 7 hollow roller cradles each, the back one turned over on x, a middle disc, a barrel and 6 grooved swirl spokes off circle pairs) and 14 rollers, rubber, core and pin each, all one compound. the pockets through the middle are the rubber's barrel 1 mm bigger round each roller. dots off the hub only |
| `freecad/vex_workbench/roundwheel.py` | the 4" legacy round wheel: a revolved hub with fusion's window, groove and gap outlines cut 6 times (fitted to arcs off its slices, drafts left off), 30 teeth and 15 bridges in the channel under them, and the tire revolved round them with the teeth cut out. hub and tire, one compound |
| `freecad/vex_workbench/versahub.py` | the plastic versahubs: a flange with 3 tabs (the notches between them are point tables), ribs over channels on the flange, a hub on top. v1 has blind holes, pockets and the 1/2 hex, v2 a round bore with a bayonet recess and two sets of pockets, plus its steel hex insert. drafts and rounds left off |
| `freecad/vex_workbench/library.py` | parts in a document: hidden source per variant, placed copies are `App::Link`s. steps read once into freecad's cache folder as brep (`remembered`). hole finding too (`holes`, `hole_at`, `hole_dots` kept on the source, `cached` per source). a size change or shop step moves frames and joints on holes that stayed put or turned with a bend onto the new source (`carry`, the bends from `metal.turned`), and joints straight on a face / edge / corner to whatever of it is left (`element`) and deletes the old worked one once nothing links it (`prune`) |
| `freecad/vex_workbench/browser.py` | the VEX parts dock                                                    |
| `freecad/vex_workbench/snap.py`    | Frame on hole command, clicked spot -> `library.hole_frame`. plus the joint bits and the click panel (orange hole points, yellow under the mouse, green picked ones) the screw, spacer, align, joint, chain and shop tools build on. screen spots for every dot are one numpy matmul |
| `freecad/vex_workbench/screws.py`  | Screw command, two hole clicks -> shortest screw + nut (or into a thread), jointed in an assembly |
| `freecad/vex_workbench/spacers.py` | Spacers command, fills a gap between two holes with spacers + washers |
| `freecad/vex_workbench/align.py`   | Align command, hole on one part onto a hole on another, faces together, then turned, gapped or flipped over 180 on the hole so it goes in. no joints |
| `freecad/vex_workbench/joints.py`  | Joint command, two hole clicks (three for a slide) -> lined up with `align.align` unless Line up is off, then a Revolute, Fixed or Slider set off where the parts are |
| `freecad/vex_workbench/inserts.py` | shaft inserts in HS bores, their own link with Placement = the gear's x `VexSeat` as an expression. the gear knows it by name in `VexInsert`, a link back would be a dependency loop. which parts take one is `inserts = true` on their menu row, or on the family for generated ones |
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
| `tools/read_f3d.py`                | `.f3d` -> step, for measuring the fusion library's parts. faces on round surfaces that ShapeFix breaks (a seam run through a hole) get built again with u = 0 turned to a gap between vertices, on copies of the edges. edges that are just a point (no curve, or a line both ends on one spot) get left out of their loop, and a cone out to its apex round one circle comes off `makeCone`. a modeled thread still doesnt sew |
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
