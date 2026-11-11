# catalog checks, run with: python tests/test_catalog.py
import re
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


# fractions and mm -> inches, other strings left alone
assert catalog.exact(["5/16", "29 mm", "0.5 OD", {"a": "1/4"}]) == [0.3125, 29 / 25.4, "0.5 OD", {"a": 0.25}]
assert next(f for f in cat["family"] if f["id"] == "u-channel")["web"] == 29 / 25.4

# step parts
assert len(steps) == 289, len(steps)
assert sum("sku" not in p for p in steps) == 15
dup = [k for k, n in Counter((p["folder"], p["file"]) for p in steps).items() if n > 1]
assert not dup, dup

# generated names
dup = [k for k, n in Counter(p["name"] for p in gen).items() if n > 1]
assert not dup, dup
names = {p["name"] for p in gen}
for n in ["1x2x1x35 Aluminum C-Channel", "1x5x1x1 Steel C-Channel", "5x Pitch Shaft",
          "Washer, 0.438 OD, 0.042 (Steel)", "2.000, 0.04 Robosource Shoulder Screw (8-32, Steel)", "Thin Nylock Nut", "Nylon Hex Nut"]:
    assert n in names, n

# ranges and rows expand right
assert len(family("c-channel")) == (2 * 3 - 1) * 35  # no steel 3x
assert "1x3x1x35 Steel C-Channel" not in names and "1x3x1x35 Aluminum C-Channel" in names
hs = [p["params"]["length"] for p in family("hs-shaft")]
assert len(hs) == 48 and hs[0] == 0.5 and hs[-1] == 24.0, hs
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

# place menus: every part is one step part, shipped, with a value on every axis and no two the same
names = [p["name"] for p in steps]
for m in cat["menu"]:
    picks = [tuple(p[a] for a in m["axes"]) for p in m["parts"]]
    assert len(set(picks)) == len(picks) and all(set(p) - {"part", "inserts"} == set(m["axes"]) for p in m["parts"]), m["id"]
    for p in m["parts"]:
        assert names.count(p["part"]) == 1 and catalog.shipped(steps[names.index(p["part"])]).is_file(), p["part"]
assert all(names.count(n) == 1 for n in cat["insert"].values()), cat["insert"]
# the boxes only offer what goes with the picks above, a pick that doesnt fit anymore goes to the first
wheels = next(m for m in cat["menu"] if m["id"] == "wheels")
rows, part = catalog.narrowed(wheels, {"Type": "Mecanum", "Size": "2.75", "Kind": "V1, Right"})
assert rows == [("Type", ["Omni", "Traction", "Mecanum"]), ("Size", ["2", "4"]), ("Kind", ["V2, Left", "V2, Right", "V1, Left", "V1, Right"])], rows
assert part["part"] == "2\" Mecanum Wheel- Right", part

assert catalog.inside("Kits/V5", "Field Elements", "Kits") and not catalog.inside("Kits Extra", "Kits")

# step weights: every [step_material] folder has parts under it, every material has a density, listed ones are g or lb
folders = [g["folder"] for g in cat["group"]]
for f, m in cat["step_material"].items():
    assert any(catalog.inside(g, f) for g in folders) and m in cat["density"], (f, m)
for p in steps:
    assert p["material"] is None or p["material"] in cat["density"], p["name"]
    assert re.fullmatch(r"\d+(\.\d+)? (g|lb)", p.get("mass", "0 g")), p["name"]
by_name = {p["name"]: p for p in steps}
assert by_name["Star Drive Shaft Collar"]["material"] == "Steel" and by_name["Rubber Shaft Collar"]["material"] is None
assert set(cat["freecad_material"]) == set(cat["density"]) and all(re.fullmatch(r"[0-9a-f-]{36}", u) for u in cat["freecad_material"].values())
mat = cat["step_material"]
assert catalog.by_folder(mat, "Motion/Sprockets/6P/8T") == "Steel" and catalog.by_folder(mat, "Motion/Sprockets/9P/12T") == "Acetal"
assert catalog.by_folder(mat, "Motion/Wheels") is None

# wheel paint: every [step_paint] folder has parts, its hub and rim are colors
for f, paint in cat["step_paint"].items():
    assert any(catalog.inside(g, f) for g in folders) and set(paint) == {"hub", "rim"}, (f, paint)
    assert all(c in cat["colors"] for c in paint.values()), (f, paint)
assert by_name["4\" Mecanum Wheel"]["paint"] == {"hub": "Old Grey Plastic", "rim": "Roller Grey"}, by_name["4\" Mecanum Wheel"]["paint"]

# step colors: real folders and real colors, the steel gears stay steel, a color on the row wins
for f, c in cat["step_color"].items():
    assert any(catalog.inside(g, f) for g in folders) and c in cat["colors"], (f, c)
got = [by_name[n]["color"] for n in ("36T Gear", "12T High Strength Metal Pinion", "12T Metal Gear", "Flat Bearing", "Large Turntable Bearing", "Turntable Mounting Bracket")]
assert got == ["Red Acetal", "Steel", "Steel", "Bearing Black", "Red Acetal", None], got

print(f"ok, {len(gen)} generated, {len(steps)} step parts")
