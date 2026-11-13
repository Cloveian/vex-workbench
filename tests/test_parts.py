# everything generated thats not metal (shafts, standoffs, spacers, screws, nuts, chain links, flex wheels, versahex adapters, both versahubs and the v2's insert, 3P sprockets, linear rails, slide trucks, the ratchet gear and winch pawl) vs vex's steps or fusion's numbers, run with: python tests/test_parts.py (needs FreeCAD + vex-step/)
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import freecad  # noqa: E402,F401
freecad.__path__.insert(0, str(ROOT / "freecad"))
import Part  # noqa: E402
from FreeCAD import Vector  # noqa: E402

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

# flex wheels vs the fusion library's f3ds, every hardness the same shape. the 3 and 4 have each arc in two halves, 130 faces on fusion's
for name, in3, box, faces in (("2 Flex Wheel (45A)", 0.871523, [0.5, 2.0, 2.0], 57), ("1.625 Flex Wheel (30A)", 0.691809, [0.5, 1.625, 1.625], 57),
                              ("3 Flex Wheel (45A)", 4.179138, [1.0, 3.0, 3.0], 154), ("4 Flex Wheel (45A)", 6.518047, [1.0, 4.0, 4.0], 154)):
    part = next(p for p in gen if p["name"] == name)
    wheel = library.GENERATORS[part["family"]](part, cat)
    got = size(wheel)
    vol = wheel.Volume / IN**3 / in3 - 1
    ok = got == box and abs(vol) < 0.0005 and wheel.isValid() and len(wheel.Faces) == faces
    bad += not ok
    print(f"{'ok ' if ok else 'BAD'} {name}: {got} vol {vol * 100:+.3f}%, {len(wheel.Faces)} faces")

# versahex adapters vs the fusion library's f3ds
for name, mm3, box in (("Plastic VersaHex Adapter (0.25 Long)", 823.714, [0.2987, 0.625, 0.625]), ("Plastic VersaHex Adapter (0.125 Long)", 531.840, [0.1806, 0.625, 0.625]),
                       ("0.5 VersaHex Adapter (0.25 Long)", 1075.012, [0.3433, 0.7, 0.7])):
    part = next(p for p in gen if p["name"] == name)
    adapter = library.GENERATORS[part["family"]](part, cat)
    got = size(adapter)
    vol = adapter.Volume / mm3 - 1
    ok = got == box and abs(vol) < 0.0005 and adapter.isValid()
    bad += not ok
    print(f"{'ok ' if ok else 'BAD'} {name}: {got} vol {vol * 100:+.3f}%")

# linear rail vs fusion's 35 hole one, up to 8.75 in, short of their tab. 8891.95 mm3 there, 42.027 mm2 across
rail = library.GENERATORS["linear-rail"](next(p for p in gen if p["name"] == "35 Hole Linear Rail"), cat)
got = size(rail)
vol = rail.common(Part.makeBox(100, 8.75 * IN, 100, Vector(-50, 0, -10))).Volume / 8891.95 - 1
ok = got == [0.3464, 0.8206, 17.5] and abs(vol) < 0.0005 and rail.isValid()
bad += not ok
print(f"{'ok ' if ok else 'BAD'} 35 hole linear rail: {got} vol {vol * 100:+.3f}% on the first half")

# slide trucks, the versahubs and the 3P sprockets vs fusion's. no drafts or small rounds so not exact, xor ~1.4% on the inner truck, ~0.75% on the v1 hub
for name, in3, box in (("Slide Truck Inner", 0.208715, [0.3296, 0.6867, 1.995]), ("Slide Truck Outer", 0.325974, [0.5603, 0.9994, 1.9874]),
                       ("0.5 Hex Bore Plastic VersaHub", 0.613912, [0.5, 2.1505, 2.1978]), ("0.5 Hex Bore Plastic VersaHub v2", 0.509168, [0.5, 2.1505, 2.1978]),
                       ("10T Sprocket, 3P", 0.029305, [0.4921, 0.5245, 0.5265]), ("15T Sprocket, 3P", 0.052881, [0.4921, 0.7572, 0.7586])):
    part = next(p for p in gen if p["name"] == name)
    s = library.GENERATORS[part["family"]](part, cat)
    got = size(s)
    vol = s.Volume / IN**3 / in3 - 1
    ok = got == box and abs(vol) < 0.01 and s.isValid()
    bad += not ok
    print(f"{'ok ' if ok else 'BAD'} {name}: {got} vol {vol * 100:+.2f}%")

# ratchet gear, winch pawl and the versahub v2's insert vs fusion's. the pawl's 1 deg draft is left off, so a hair under its box
for name, in3, box in (("Ratchet Gear", 0.251706, [0.32, 1.7148, 1.7169]), ("Winch Pawl", 0.054859, [0.39, 0.62, 0.6581]), ("VersaHub v2 Hex Insert", 0.101087, [0.5, 0.8917, 0.9676])):
    part = next(p for p in gen if p["name"] == name)
    s = library.GENERATORS[part["family"]](part, cat)
    got = size(s)
    vol = s.Volume / IN**3 / in3 - 1
    ok = got == box and abs(vol) < 0.002 and s.isValid()
    bad += not ok
    print(f"{'ok ' if ok else 'BAD'} {name}: {got} vol {vol * 100:+.3f}%")

print("all good" if not bad else f"{bad} bad")
sys.exit(1 if bad else 0)
