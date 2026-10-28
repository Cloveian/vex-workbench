# Structure

## Layout

| path                               | what                                                                  |
| ---------------------------------- | --------------------------------------------------------------------- |
| `freecad/vex_workbench/`           | the workbench itself (new style addon, FreeCAD finds it by this path) |
| `freecad/vex_workbench/data/parts.toml` | the [catalog](../design-choices/catalog.md)                      |
| `tools/fetch_vex_cad.py`           | pulls every V5 step off vexrobotics.com, `uv run` it                  |
| `tools/sort_vex_step.py`           | sorts the downloads into the fusion library folders, `--apply` moves them |
| `vex-step/`                        | the 289 steps, gitignored                                             |
| `downloads/`                       | raw downloads + `manifest.csv`, gitignored                            |
| `docs/`                            | this                                                                  |

the fetch script drives my real firefox (selenium + geckodriver) with my cookies copied into a temp profile, cuz vex is behind cloudflare and anything headless gets a 403. it clicks through the cad results pages and skips anything already in `vex-step/` (by name or sku)

## Testing

- anything that doesnt need FreeCAD (the catalog reader) is plain python
- geometry runs headless in `freecadcmd`, generated parts checked against their fixture steps (volume and bounding box, in inches)

---
Back to [code](index.md)
