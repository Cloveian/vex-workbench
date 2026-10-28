# reads parts.toml into every part, generated and step. no FreeCAD in here
import itertools
import tomllib
from pathlib import Path

CATALOG = Path(__file__).parent / "data" / "parts.toml"

# everything else in a [[family]] is a param
FAMILY_KEYS = ("id", "folder", "name", "fixtures")


def load(path=CATALOG):
    with open(path, "rb") as f:
        return tomllib.load(f)


def span(r):
    # both ends in, ints stay ints
    step = r.get("step", 1)
    n = round((r["to"] - r["from"]) / step)
    return [round(r["from"] + i * step, 6) for i in range(n + 1)]


def axes(family):
    # lists and ranges are one axis each, a list of tables is rows, anything else is a constent
    out = []
    for key, v in family.items():
        if key in FAMILY_KEYS:
            continue
        if isinstance(v, dict) and "to" in v:
            v = span(v)
        if isinstance(v, list):
            out.append([x if isinstance(x, dict) else {key: x} for x in v])
        else:
            out.append([{key: v}])
    return out


def variants(family):
    out = []
    for combo in itertools.product(*axes(family)):
        params = {}
        for c in combo:
            params.update(c)
        out.append({
            "family": family["id"],
            "name": family["name"].format(**params),
            "folder": family["folder"].format(**params),
            "params": params,
        })
    return out


def generated(cat):
    return [v for fam in cat["family"] for v in variants(fam)]


def step_parts(cat):
    # vex-step/{folder}/{file}, the pneumatics ones have no sku
    return [{**p, "folder": g["folder"]} for g in cat["group"] for p in g["parts"]]
