# renders hero / align / bend pngs into downloads/ off the offscreen gui, software gl. no panels in them
# env QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 freecad -M . tools/render_shots.py
import os
import subprocess
import sys
import traceback

import FreeCAD as App
import FreeCADGui as Gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "downloads")
sys.path.insert(0, ROOT)
from freecad.vex_workbench import align, library, screws, shop  # noqa: E402
from freecad.vex_workbench.metal import IN  # noqa: E402

V, P, R = App.Vector, App.Placement, App.Rotation


def render(name, d, w, h):
    # fitAll leaves a wide margin, magick trims it back to 40 px and 1200 wide
    v = Gui.ActiveDocument.ActiveView
    v.setViewDirection(d)
    Gui.updateGui()
    v.fitAll()
    Gui.updateGui()
    path = os.path.join(OUT, name)
    v.saveImage(path, w, h, "White")
    subprocess.run(["magick", path, "-trim", "-bordercolor", "white", "-border", "40", "-resize", "1200x", path], check=True)


def spot(link, x, y, z):
    # a click on link at (x, y, z) inches, its own coords
    return (link, V(x, y, z) * IN, link.Placement, (link, ""))


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


def lined_up(gen):
    doc = App.newDocument("align")
    base = library.place(doc, gen["5x10 Steel Plate"])
    wall = library.place(doc, gen["1x2x1x10 Steel C-Channel"])
    wall.Placement = P(V(1, 4, 2) * IN, R(V(1, 1, 0), 40))  # anywhere, align moves it
    doc.recompute()
    align.align(spot(wall, 0.26, 0.26, 0), spot(base, 0.76, 1.26, 0.046), 0)
    doc.recompute()
    Gui.Control.showDialog(align.Panel())
    Gui.updateGui()
    render("align.png", (-1, -1.3, -1.1), 1600, 930)
    Gui.Control.closeDialog()
    App.closeDocument(doc.Name)


def bent(gen):
    doc = App.newDocument("bend")
    plate = library.place(doc, gen["5x15 Steel Plate"])
    doc.recompute()
    library.rework(plate, [shop.bend(plate, V(5.25, 0.25, 0.046) * IN, True, 0, -90)])
    doc.recompute()
    render("bend.png", (-1, -1.3, -1.1), 2400, 1400)
    App.closeDocument(doc.Name)


try:
    os.makedirs(OUT, exist_ok=True)
    App.addDocumentObserver(library.Observer())
    _, gen, steps = library.index()
    hero(gen, steps)
    lined_up(gen)
    bent(gen)
    sys.__stdout__.write(f"hero.png, align.png and bend.png in {OUT}\n")
    failed = False
except Exception:
    traceback.print_exc(file=sys.__stdout__)
    failed = True
sys.__stdout__.flush()
os._exit(1 if failed else 0)  # the gui wont quit on its own
