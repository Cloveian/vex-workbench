# catalog checks, run with: python tests/test_catalog.py
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# straight from the folder, the system freecad package drags all of FreeCAD in
sys.path.insert(0, str(ROOT / "freecad" / "vex_workbench"))

import catalog  # noqa: E402

cat = catalog.load()
gen = catalog.generated(cat)
steps = catalog.step_parts(cat)


def family(id):
    return [p for p in gen if p["family"] == id]


# step parts
assert len(steps) == 289, len(steps)
assert sum("sku" not in p for p in steps) == 15
dup = [k for k, n in Counter((p["folder"], p["file"]) for p in steps).items() if n > 1]
assert not dup, dup

# generated names
dup = [k for k, n in Counter(p["name"] for p in gen).items() if n > 1]
assert not dup, dup
names = {p["name"] for p in gen}
for n in ["1x2x1x35 Aluminum C-Channel", "1x5x1x1 Steel C-Channel", "5x Pitch Shaft", "LS 84T Gear (Drilled)",
          "Washer, 0.438 OD, 0.042 (Steel)", "2.000, 0.04 Robosource Shoulder Screw (8-32, Steel)", "Thin Nylock Nut", "Nylon Hex Nut"]:
    assert n in names, n

# ranges and rows expand right
assert len(family("c-channel")) == 2 * 3 * 35
hs = [p["params"]["length"] for p in family("hs-shaft")]
assert len(hs) == 48 and hs[0] == 0.5 and hs[-1] == 24.0, hs
assert len(family("drilled-gear")) == 4
assert len(family("washer")) == 5
assert family("c-channel")[0]["folder"] == "Structure/Aluminum/2x C-Channel"

# fixtures and bases are real step files
stems = {Path(p["file"]).stem for p in steps}
for fam in cat["family"]:
    for f in fam.get("fixtures", []):
        assert f in stems, (fam["id"], f)
for p in gen:
    b = p["params"].get("base")
    assert b is None or b in stems, (p["name"], b)

# and on disk, if theyre here (gitignored)
vs = catalog.STEP_DIR
if vs.is_dir():
    gone = [p["file"] for p in steps if not (vs / p["folder"] / p["file"]).is_file()]
    assert not gone, gone

# a fresh clone without them gets pointed at the README
catalog.STEP_DIR = ROOT / "no-such-folder"
try:
    catalog.step_path(steps[0])
    raise AssertionError("found a step in a folder that isnt there")
except ValueError as e:
    assert "README" in str(e), e
catalog.STEP_DIR = vs

# every base ships, and a shipped one comes out a real step thats gone again after
bases = {v["params"]["base"] for v in gen if "base" in v["params"]}
base_steps = [p for p in steps if Path(p["file"]).stem in bases]
unshipped = [p["file"] for p in base_steps if not catalog.shipped(p).is_file()]
assert len(base_steps) == len(bases) and not unshipped, unshipped
with catalog.step_file(base_steps[0]) as path:
    with open(path, "rb") as f:
        assert f.read(12) == b"ISO-10303-21", path
assert not path.exists(), path

print(f"ok, {len(gen)} generated, {len(steps)} step parts")
