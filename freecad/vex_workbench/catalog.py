# reads parts.toml into every part, generated and step. no FreeCAD in here
import contextlib
import gzip
import itertools
import os
import re
import shutil
import tempfile
import tomllib
from fractions import Fraction
from pathlib import Path

CATALOG = Path(__file__).parent / "data" / "parts.toml"
SHIPPED = Path(__file__).parent / "steps"  # the subset that ships, gzipped by tools/ship_steps.py
STEP_DIR = Path(__file__).parents[2] / "vex-step"  # the whole download, for the test fixtures and anything not shipped

# everything else in a [[family]] is a param
FAMILY_KEYS = ("id", "title", "folder", "name", "fixtures")


def load(path=CATALOG):
    with open(path, "rb") as f:
        return exact(tomllib.load(f))


def exact(v):
    # "5/16" and "29 mm" in the toml -> inches
    if isinstance(v, dict):
        return {k: exact(x) for k, x in v.items()}
    if isinstance(v, list):
        return [exact(x) for x in v]
    if isinstance(v, str):
        if re.fullmatch(r"\d+/\d+", v):
            return float(Fraction(v))
        mm = re.fullmatch(r"(\d+(?:\.\d+)?) ?mm", v)
        if mm:
            return float(mm[1]) / 25.4
    return v


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
            out.append((key, [x if isinstance(x, dict) else {key: x} for x in v]))
        else:
            out.append((key, [{key: v}]))
    return out


def variants(family):
    out = []
    for combo in itertools.product(*(c for _, c in axes(family))):
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


def inside(folder, *tops):
    # folder is one of tops or under it. "Kits Extra" isnt in "Kits"
    return any(folder == t or folder.startswith(t + "/") for t in tops)


def by_folder(table, folder):
    # value of the longest folder in table thats this one or above it
    fits = [f for f in table if inside(folder, f)]
    return table[max(fits, key=len)] if fits else None


def step_parts(cat):
    # vex-step/{folder}/{file}, the pneumatics ones have no sku. a material or paint on the row beats the folders
    out = []
    for g in cat["group"]:
        f = g["folder"]
        defaults = {"material": by_folder(cat["step_material"], f), "paint": by_folder(cat["step_paint"], f)}
        out += [{**defaults, **p, "folder": f} for p in g["parts"]]
    return out


def narrowed(menu, picked):
    # each axis's choices from the parts matching the picks above it, a pick that isnt in them goes to the first
    rows, left = [], menu["parts"]
    for axis in menu["axes"]:
        choices = list(dict.fromkeys(p[axis] for p in left))
        now = picked.get(axis) if picked.get(axis) in choices else choices[0]
        rows.append((axis, choices))
        left = [p for p in left if p[axis] == now]
    return rows, left[0]


def shipped(step):
    return SHIPPED / step["folder"] / (step["file"] + ".gz")


def has(step):
    return shipped(step).is_file() or (STEP_DIR / step["folder"] / step["file"]).is_file()


def step_path(step):
    # the downloaded one
    path = STEP_DIR / step["folder"] / step["file"]
    if not STEP_DIR.is_dir():
        raise ValueError(f"{step['file']} doesn't ship with the workbench and VEX's STEP files aren't downloaded, the README says how to get them into {STEP_DIR}")
    if not path.is_file():
        raise ValueError(f"no step file at {path}")
    return path


@contextlib.contextmanager
def step_file(step):
    # a plain step to read, the shipped one unzipped into a temp file till the with ends
    gz = shipped(step)
    if not gz.is_file():
        yield step_path(step)
        return
    fd, tmp = tempfile.mkstemp(suffix=".step")
    try:
        with os.fdopen(fd, "wb") as out, gzip.open(gz) as src:
            shutil.copyfileobj(src, out)
        yield Path(tmp)
    finally:
        os.remove(tmp)
