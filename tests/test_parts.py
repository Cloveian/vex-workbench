# everything generated thats not metal (shafts, standoffs, spacers, screws, nuts, chain links) vs vex's steps or fusion's numbers, run with: python tests/test_parts.py (needs FreeCAD + vex-step/)
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401
freecad.__path__.insert(0, str(ROOT / "freecad"))
import Part  # noqa: E402

from freecad.vex_workbench import catalog, library, metal  # noqa: E402
from freecad.vex_workbench.metal import IN  # noqa: E402

cat = catalog.load()
gen = catalog.generated(cat)
steps = {Path(p["file"]).stem: p for p in catalog.step_parts(cat)}

# vex's file is off, the generated one is nominal
OFF = {
    "2 High Strength Shaft (276-3440)": "1 mm short, the 24 isnt",
    "3 High Strength Shaft (276-3522)": "1 mm short, the 24 isnt",
    "4 High Strength Shaft (276-3523)": "1 mm short, the 24 isnt",
}


def size(shape):
    b = shape.optimalBoundingBox()
    return sorted(round(v / IN, 4) for v in (b.XLength, b.YLength, b.ZLength))


def nominal(fx):
    # the length in the name, 1_4 = 1/4
    m = re.search(r"(\d+)_(\d+)|(\d+(?:\.\d+)?)", re.sub(r"^#8-32 x | \([\d-]+\)$", "", fx))
    return int(m[1]) / int(m[2]) if m[1] else float(m[3])


bad = 0
for fam in cat["family"]:
    if fam["id"] not in library.GENERATORS or fam["id"] in metal.PROFILES:
        continue
    make = library.GENERATORS[fam["id"]]
    parts = [p for p in gen if p["family"] == fam["id"]]
    for fx in fam.get("fixtures", []):
        step = steps[fx]
        theirs = Part.read(str(catalog.step_path(step)))
        want, n = size(theirs), nominal(fx)
        # spacers come in 3 ODs at each length, take the one that fits
        tries = [make(p, cat) for p in parts if n in (p["params"].get("length"), p["params"].get("n"))]
        ours = min(tries, key=lambda s: sum(abs(a - b) for a, b in zip(size(s), want)))
        got = size(ours)
        vol = ours.Volume / theirs.Volume - 1
        ok = ours.isValid() and max(abs(a - b) for a, b in zip(got, want)) < 0.001 and abs(vol) < 0.005
        note = ""
        if not ok and fx in OFF:
            note, ok = f" (known: {OFF[fx]})", True
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {fx}: {got} vs {want} vol {vol * 100:+.2f}%{note}")
    # every size has to build as one valid solid, ~13 s for all of them. the ones with nothing to check against (wsahers, robosource parts, other materials) get a line each
    for p in parts:
        s = make(p, cat)
        ok = s.isValid() and len(s.Solids) == 1
        bad += not ok
        if not ok or "fixtures" not in fam:
            print(f"{'ok ' if ok else 'BAD'} {p['name']}: builds")

# the 3/8 hs spacer has no step. 0.02158 in3, within 2% of halfway between the 1/4 and 1/2 (0.02195)
hs = {p["params"]["length"]: library.GENERATORS["hs-spacer"](p, cat) for p in gen if p["family"] == "hs-spacer"}
got = size(hs[0.375])
vol = hs[0.375].Volume / ((hs[0.25].Volume + hs[0.5].Volume) / 2) - 1
ok = got[0] == 0.375 and abs(vol) < 0.02
bad += not ok
print(f"{'ok ' if ok else 'BAD'} 3/8 hs spacer: {got} vol {vol * 100:+.2f}% off halfway")

# 6P link vs the fusion library's f3d
link = library.GENERATORS["chain-link"](next(p for p in gen if p["name"] == "Chain Link (6P)"), cat)
got = size(link)
vol = link.Volume / IN**3 / 0.010145 - 1
ok = got == [0.1732, 0.4232, 0.4449] and abs(vol) < 0.0005 and link.isValid()
bad += not ok
print(f"{'ok ' if ok else 'BAD'} 6P chain link: {got} vol {vol * 100:+.3f}%")

print("all good" if not bad else f"{bad} bad")
sys.exit(1 if bad else 0)
