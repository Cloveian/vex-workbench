# usage: python tools/ship_steps.py
#   gzips the steps that ship from vex-step/ into freecad/vex_workbench/steps/, and drops ones that stopped shipping

import gzip
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "freecad" / "vex_workbench"))
import catalog  # noqa: E402  straight from its folder, the freecad package would load FreeCAD

# not a v5 robot part
SKIP = ("Kits", "Field Elements", "Electronics/Legacy (Cortex)")
SKIP_FILES = ("V5 Controller (276-4820).step",)


def ships(step, bases, fixtures):
    stem = step["file"].rsplit(".", 1)[0]
    if stem in bases:
        return True
    # the fixtures are generated parts, those only matter to the tests
    return stem not in fixtures and not step["folder"].startswith(SKIP) and step["file"] not in SKIP_FILES


cat = catalog.load()
bases = {v["params"]["base"] for v in catalog.generated(cat) if "base" in v["params"]}
fixtures = {fx for fam in cat["family"] for fx in fam.get("fixtures", [])}
keep = set()
for step in catalog.step_parts(cat):
    if not ships(step, bases, fixtures):
        continue
    out, step_file = catalog.shipped(step), catalog.step_path(step)
    keep.add(out)
    if out.is_file() and out.stat().st_mtime >= step_file.stat().st_mtime:
        continue  # zipped since the download last changed
    out.parent.mkdir(parents=True, exist_ok=True)
    # mtime 0 so the same step zips to the same bytes, git sees no change
    with open(step_file, "rb") as src, gzip.GzipFile(out, "wb", 9, mtime=0) as dst:
        shutil.copyfileobj(src, dst)
for old in catalog.SHIPPED.rglob("*.gz"):
    if old not in keep:
        old.unlink()
for d in sorted(catalog.SHIPPED.rglob("*"), reverse=True):  # deepest first
    if d.is_dir() and not any(d.iterdir()):
        d.rmdir()
total = sum(p.stat().st_size for p in keep)
print(f"{len(keep)} steps, {total / 1e6:.0f} MB in {catalog.SHIPPED.relative_to(ROOT)}")
