# usage: python tools/sort_vex_step.py [--apply] [src dirs...]
#   moves vex's step files into the fusion library's folder layout under vex-step/. dry run without --apply

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = [ROOT / "downloads" / "vex-v5"]
OUT = ROOT / "vex-step"
FUSION_REPO = "VEX-CAD/VEX-CAD-Fusion-360-Library"

# first match wins, so specific before general. {0} {1} are the regex groups, title-cased (12t -> 12T, steel -> Steel)
RULES = [
    # --- hardware ---
    (r"^#6-32 x", "Hardware/Screws"),
    (r"thumbscrew", "Hardware/Screws/8-32/Nylon"),
    (r"shoulder screw", "Hardware/Screws/8-32/Steel/Shoulder Screws"),
    (r"drive coupler", "Hardware/Standoffs"),
    (r"star drive screw", "Hardware/Screws/8-32/Steel/Torx (Star)"),
    (r"^#8-32 x .*screw", "Hardware/Screws/8-32/Steel/Hex"),
    (r"nylock nut", "Hardware/Nuts/8-32 Nuts/Nylock Nuts"),
    (r"#8-32 hex nut", "Hardware/Nuts/8-32 Nuts/Hex Nuts"),
    (r"keps nut|low profile nut", "Hardware/Nuts/8-32 Nuts"),
    (r"retainer (w_|with) bearing flat|collar retainer", "Motion/Bearings"),
    (r"nut retainer|standoff retainer", "Hardware/Retainers"),
    (r"standoff", "Hardware/Standoffs"),

    # --- motion: shafts n' stuff on them ---
    (r"high strength shaft adapter|shaft inserts", "Motion/Inserts"),
    (r"high strength shaft spacer", "Motion/Spacers/HS Spacers"),
    (r"high strength shaft bearing|bushing kit|bearing flat|flat bearing|bearing blocks|pillow block", "Motion/Bearings"),
    (r"^\d+ high strength shaft", "Motion/HS Shafts"),
    (r"bar lock|^lock bar", "Motion/Lock Bars"),
    (r"capped shaft|pitch shaft|^\d+ shaft|^drive shaft", "Motion/LS Shafts"),
    (r"shaft collar", "Motion/Collars"),
    (r"turntable", "Motion/Turntables"),
    (r"nylon spacer", "Motion/Spacers/0.5 OD"),  # 0.5" OD, measured off the steps
    (r"click-on spacer", "Motion/Spacers/0.375 OD"),
    (r"8mm plastic spacer", "Motion/Spacers/0.313 OD"),  # 0.32" OD
    (r"steel washer", "Motion/Spacers/Washers/Steel"),
    (r"teflon washer", "Motion/Spacers/Washers/Teflon"),

    # gears, sprockets, chain
    (r"gearbox bracket", "Structure/Brackets"),
    (r"bevel gear$|bevel gear \(", "Motion/Gears/Low Strength/Bevel Gears"),
    (r"(\d+t) high strength gear v2", "Motion/Gears/High Strength (v2)/{0}"),
    (r"(\d+t) high strength (gear|metal pinion)", "Motion/Gears/High Strength (v1)/{0}"),
    (r"rack gear|worm gear", "Motion/Gears"),
    (r"^\d+t (metal )?gear", "Motion/Gears/Low Strength"),
    (r"(\d+t) sprocket, 6p", "Motion/Sprockets/6P/{0}"),
    (r"(\d+t) high strength sprocket", "Motion/Sprockets/9P/{0}"),
    (r"high strength (conveyor )?chain", "Motion/Chain Links/9P (High Strength Chain)"),
    (r"conveyor-belt|tank tread|tread links|rubber link", "Motion/Chain Links/Tank Tread"),

    # --- motion: wheels ---
    (r"bogie", "Motion/Wheels"),
    (r"2” mecanum wheels v2 \((left|right)\)", "Motion/Wheels/Mecanum Wheels/2 Inch/V2/{0}"),
    (r"^2 mecanum wheel- (left|right)", "Motion/Wheels/Mecanum Wheels/2 Inch/V1/{0}"),
    (r"^4 mecanum", "Motion/Wheels/Mecanum Wheels/4 Inch"),
    (r"^2” omni", "Motion/Wheels/Omni Wheels/2 Inch"),
    (r"^([\d.]+) \(\d+mm travel\) omni", "Motion/Wheels/Omni Wheels/{0} Inch/Antistatic"),
    (r"^([\d.]+) \(\d+mm travel\) anti-static wheel", "Motion/Wheels/Traction Wheels/{0} Inch/Antistatic"),
    (r"^([\d.]+) wheel", "Motion/Wheels/Traction Wheels/{0} Inch/Legacy"),
    (r"intake rollers", "Motion/Wheels"),

    # rest of motion
    (r"pneumatic|fitting|valve|manifold|pressure|reservoir", "Motion/Pneumatics/New"),
    (r"cam follower|drop off cam|hand crank|lead screw|u-joint|universal joint|differential|shifter shaft|shaft coupler|motor post|clutch|flywheel", "Motion/Advanced"),

    # --- structure ---
    (r"^(30|45|60|90)[ -]degree", "Structure/Gussets/{0} Degrees"),
    (r"gusset", "Structure/Gussets"),
    (r"license plate", "Structure"),
    (r"1x(\d)x1x\d+ (aluminum|steel) c-channel", "Structure/{1}/{0}x C-Channel"),
    (r"u-channel", "Structure/Aluminum/2x U-Channel"),
    (r"1x1x\d+ aluminum angle", "Structure/Aluminum/1x1 Angle (Regular)"),
    (r"(\d)x\1x\d+ (steel|aluminum) angle", "Structure/{1}/{0}x{0} Angle"),
    (r"chassis rail|steel plate|base plate|steel bar", "Structure/Steel"),
    (r"hinge|rubber bumper", "Structure"),

    # --- electronics ---
    (r"mounting flange|screen protector|v5 battery clip", "Electronics/Brain & Battery Accessories"),
    (r"retaining clip", "Electronics/Wires & Cables"),
    (r"bumper switch|limit switch|line tracker|light sensor|potentiometer|accelerometer", "Electronics/Sensors/3-Wire"),
    (r"sensor|3-wire expander", "Electronics/Sensors"),
    (r"^v5 (robot brain|robot battery|robot radio|controller|smart motor)", "Electronics"),
    (r"motor 393|servo|motor controller|power expander|7\.2v|battery (clip|strap|extension)|flashlight", "Electronics/Legacy (Cortex)"),

    # kits + field
    (r"claw kit|clawbot", "Kits"),
    (r"field perimeter", "Field Elements"),
]


def folder_for(stem):
    name = stem.lower()
    for pat, folder in RULES:
        m = re.search(pat, name)
        if m:
            return folder.format(*[(g or "").title() for g in m.groups()])
    return None


def fusion_dirs():
    # to flag the folders i made up
    out = subprocess.run(["gh", "api", f"repos/{FUSION_REPO}/git/trees/main?recursive=1"],
                         capture_output=True, text=True, check=True).stdout
    return {e["path"] for e in json.loads(out)["tree"] if e["type"] == "tree"}


def main():
    apply = "--apply" in sys.argv
    srcs = [Path(a) for a in sys.argv[1:] if a != "--apply"] or SRC
    files = sorted(p for d in srcs if d.is_dir() for p in d.iterdir() if p.suffix.lower() in (".step", ".stp"))

    plan, lost = {}, []
    for p in files:
        folder = folder_for(p.stem)
        if folder:
            plan.setdefault(folder, []).append(p)
        else:
            lost.append(p)

    known = fusion_dirs()
    for folder in sorted(plan):
        tag = "" if folder in known else "   <- not in fusion"
        print(f"{len(plan[folder]):3} {folder}{tag}")
    print(f"\n{len(files)} files, {len(files) - len(lost)} sorted, {len(lost)} no rule")
    for p in lost:
        print(f"  no rule: {p.name}")
    if not apply:
        print("dry run, --apply to move them into", OUT.relative_to(ROOT))
        return 0

    for folder, ps in plan.items():
        d = OUT / folder
        d.mkdir(parents=True, exist_ok=True)
        for p in ps:
            dst = d / p.name
            if not dst.exists():
                p.rename(dst)
            elif dst.samefile(p):
                p.unlink()  # already hardlinked there
            else:
                print(f"  ! {dst.relative_to(OUT)} is already there and dihfrent, left {p} alone")
    for d in srcs:
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    print(f"moved into {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
