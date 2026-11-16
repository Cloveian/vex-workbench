# renders hero / clawbot / chain / align / bend pngs into downloads/ off the offscreen gui, software gl. no panels in them
# env QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 freecad -M . tools/render_shots.py
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "downloads")
sys.path.insert(0, ROOT)
from freecad.vex_workbench import align, chain, library, screws, shop, snap  # noqa: E402
from freecad.vex_workbench.metal import IN  # noqa: E402

V, P, R = App.Vector, App.Placement, App.Rotation
WIDTH, BORDER = 2400, 40  # px out, github shows them ~900 wide, 2x+ for hidpi
SS = 3  # drawn this many times bigger then shrunk, software gl has no antialiasing and 1:1 came out crunchy


def render(name, d, w, h, zup=False):
    # w x h is the shape, drawn SS times that. fitAll leaves a wide margin, trimmed back to BORDER
    v = Gui.ActiveDocument.ActiveView
    v.setAnimationEnabled(False)  # or a camra turn is still going when it saves
    if zup:  # setViewDirection picks its own up, a robot wants z
        z = -V(*d).normalize()
        x = V(0, 0, 1).cross(z).normalize()
        y = z.cross(x)
        v.setCameraOrientation(R(App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1)).Q)
    else:
        v.setViewDirection(d)
    Gui.updateGui()
    v.fitAll()
    Gui.updateGui()
    path = os.path.join(OUT, name)
    v.saveImage(path, w * SS, h * SS, "White")
    subprocess.run(["magick", path, "-trim", "+repage", "-filter", "Lanczos", "-resize", f"{WIDTH - 2 * BORDER}x",
                    "-bordercolor", "white", "-border", str(BORDER), path], check=True)


def spot(link, x, y, z):
    # a click on link at (x, y, z) inches, its own coords
    return (link, V(x, y, z) * IN, link.Placement, (link, ""))


def put(doc, src, rot, x, y, z):
    # turned by rot, box center on (x, y, z) inches
    link = library.place(doc, src)
    link.Placement = P(V(), rot)
    doc.recompute()
    link.Placement = P(V(x, y, z) * IN - link.Shape.BoundBox.Center, rot)
    return link


def hero(gen, steps):
    # two channels web down on a plate, screwed through, a 5.5W on the outer flange, screw panel up for the dots
    doc = App.newDocument("hero")
    plate = library.place(doc, gen["5x15 Steel Plate"])
    nylock = screws.nuts()["Nylock Nut"]
    for y in (0, 1.5):
        ch = library.place(doc, gen["1x2x1x15 Steel C-Channel"])
        ch.Placement = P(V(0, y, 0.592) * IN, R(V(1, 0, 0), -90))  # web down, flanges up
        doc.recompute()
        for x in (0.75, 3.75, 6.75):
            screws.fasten(doc, spot(ch, x + 0.01, 0.5, 0.26), spot(plate, x + 0.01, y + 0.26, 0), "star-screw", nylock)
    motor = library.place(doc, steps["Electronics/V5 Smart Motor (5.5W) (276-4842).step"])
    motor.Placement = P(V(), R(V(0, 1, 0), 90))  # front holes along x
    doc.recompute()
    align.align(spot(motor, 0.01, -1.578, 0.124), spot(ch, 3.76, 0.26, 1.0), 0, step=90)
    doc.recompute()
    for x, z in ((3.76, 0.124), (4.26, 0.624)):  # inside the flange into its tapped holes
        screws.fasten(doc, spot(ch, x, 0.26, 0.954), spot(motor, 0.01, -1.578, z), "star-screw", None)
    doc.recompute()
    Gui.Control.showDialog(screws.Panel())
    Gui.updateGui()
    render("hero.png", (-1, -1.3, -1.4), 1600, 930)
    Gui.Control.closeDialog()
    App.closeDocument(doc.Name)


def clawbot(gen, steps):
    # a clawbot-ish one off the kit's layout, no claw. x forward, y left, nothing actually screwed together
    doc = App.newDocument("clawbot")
    X, Y, Z = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
    side = R(X, -90)  # wheels and motors, axle along y
    down = R(Z, 90) * R(X, -90)  # across, web down
    wheel = steps["Motion/Wheels/Traction Wheels/4 Inch/Legacy/4 Wheel (276-1497) .step"]
    motor = steps["Electronics/V5 Smart Motor (276-4840).step"]
    rail = gen["1x2x1x25 Aluminum C-Channel"]
    for s in (1, -1):
        flip = R(Z, 0 if s > 0 else 180)  # open side in
        put(doc, rail, flip, 0, s * 4.725, 0.5)
        for x in (4.5, -4.5):
            put(doc, wheel, flip * side, x, s * 5.55, 0.5)
        put(doc, motor, flip * side, -4.5, s * 2.98, 0.5)  # output out through the rail
        put(doc, gen["1x2x1x15 Aluminum C-Channel"], flip * R(Y, -90), -1, s * 4.725, 4.75)  # tower
        put(doc, steps["Motion/Gears/Low Strength/84T Gear (276-2169-004).step"], R(X, -90 * s), -1, s * 5.25, 6.75)
        put(doc, steps["Motion/Gears/Low Strength/12T Gear (276-2169-001).step"], R(X, -90 * s), -1, s * 5.2, 4.75)
        put(doc, motor, flip * side, -1, s * 2.98, 4.75)
        put(doc, rail, flip * R(Y, -20 * s), 4.64, s * 5.775, 8.8)  # arm, 20 deg up off the 84T
    put(doc, gen["5x20 Aluminum Plate"], R(Z, 90), -3, 0, 1.03)
    for x in (5.75, -5.75):
        put(doc, gen["1x2x1x20 Aluminum C-Channel"], down, x, 0, 1.275)
    put(doc, gen["1x2x1x23 Aluminum C-Channel"], down, 10.4, 0, 11.1)
    put(doc, steps["Electronics/V5 Robot Brain (276-4810).step"], R(Z, 90), -3, 0, 1.68)
    put(doc, steps["Electronics/V5 Robot Battery (276-4811).step"], R(Z, 90), 2.5, 0, 0.5)
    doc.recompute()
    render("clawbot.png", (-1, 1.5, -0.8), 1600, 1000, zup=True)
    App.closeDocument(doc.Name)


def chained(steps):
    # 6P round a 32T and two 16Ts, the middle one pushing the top run out
    doc = App.newDocument("chain")
    sprockets = []
    for t, sku, x, y in ((32, "276-8330", 0, 0), (16, "276-8328", 7, 0.5), (16, "276-8328", 4, 1.6)):
        s = library.place(doc, steps[f"Motion/Sprockets/6P/{t}T/{t}T Sprocket, 6P ({sku}).step"])
        s.Placement.Base = V(x, y, 0) * IN
        sprockets.append(s)
    doc.recompute()
    clicks = []
    for s in sprockets:
        bore = min(library.hole_dots(s), key=lambda d: V(d.x, d.y, 0).Length)
        clicks.append(chain.sprocket((s, bore, s.Placement, (s, ""))))
    chain.put_on(doc, None, clicks)  # 82 links
    doc.recompute()
    render("chain.png", (-0.6, 0.9, -1), 1600, 800, zup=True)
    App.closeDocument(doc.Name)


def lined_up(gen):
    doc = App.newDocument("align")
    base = library.place(doc, gen["5x10 Steel Plate"])
    wall = library.place(doc, gen["1x2x1x10 Steel C-Channel"])
    wall.Placement = P(V(1, 4, 2) * IN, R(V(1, 1, 0), 40))  # anywhere, align moves it
    doc.recompute()
    align.align(spot(wall, 0.26, 0.26, 0), spot(base, 0.76, 1.26, 0.046), 0)
    doc.recompute()
    render("align.png", (-1, -1.3, -1.1), 1600, 930)  # no panel, its dots show through from the far faces and look like noise
    App.closeDocument(doc.Name)


def bent(gen):
    doc = App.newDocument("bend")
    plate = library.place(doc, gen["5x15 Steel Plate"])
    doc.recompute()
    library.rework(plate, [shop.bend(plate, V(5.25, 0.25, 0.046) * IN, True, 0, -90)])
    doc.recompute()
    render("bend.png", (-1, -1.3, -1.1), 1600, 930)
    App.closeDocument(doc.Name)


breps = tempfile.mkdtemp(prefix="vex-breps")  # not my real step cache
try:
    os.makedirs(OUT, exist_ok=True)
    snap.MARK_SIZE *= SS  # px dots, shrunk with the rest
    snap.PICK_SIZE *= SS
    library.BREPS = Path(breps)
    App.addDocumentObserver(library.Observer())
    _, gen, steps = library.index()
    hero(gen, steps)
    clawbot(gen, steps)
    chained(steps)
    lined_up(gen)
    bent(gen)
    sys.__stdout__.write(f"hero.png, clawbot.png, chain.png, align.png and bend.png in {OUT}\n")
    failed = False
except BaseException:  # Ctrl-C and sys.exit too, or the os._exit below never runs
    traceback.print_exc(file=sys.__stdout__)
    failed = True
shutil.rmtree(breps, ignore_errors=True)
sys.__stdout__.flush()
os._exit(1 if failed else 0)  # the gui wont quit on its own
