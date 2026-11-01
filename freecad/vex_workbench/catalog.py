# reads parts.toml into every part, generated and step. no FreeCAD in here
import contextlib
import gzip
import itertools
import os
import shutil
import tempfile
import tomllib
from pathlib import Path

CATALOG = Path(__file__).parent / "data" / "parts.toml"
SHIPPED = Path(__file__).parent / "steps"  # the subset that ships, gzipped by tools/ship_steps.py
STEP_DIR = Path(__file__).parents[2] / "vex-step"  # the whole download, for the test fixtures and anything not shipped

# everything else in a [[family]] is a param
FAMILY_KEYS = ("id", "title", "folder", "name", "fixtures")


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


def step_parts(cat):
    # vex-step/{folder}/{file}, the pneumatics ones have no sku
    return [{**p, "folder": g["folder"]} for g in cat["group"] for p in g["parts"]]


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
