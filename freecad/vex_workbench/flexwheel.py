# flex wheels, the 1.625 and 2 in ones: a disc with a hex bore and windows between straight spokes
import Part
from FreeCAD import Vector

from .metal import IN
from .stock import hexagon

FAMILIES = ("flex-wheel",)
Z = Vector(0, 0, 1)


def make(part, cat):
    # axis on z, widht centered on z = 0, a spoke along y
    p = part["params"]
    r, w, n = p["od"] / 2, p["width"], p["spokes"]
    out, hub = r - p["rim"], p["hub"][f"{p['od']:g}"]
    low = Vector(0, 0, -2 * w)  # cutters start under it
    ring = Part.makeCylinder(out, 4 * w, low).cut(Part.makeCylinder(hub, 4 * w, low))
    bars = []
    for k in range(n // 2):
        b = Part.makeBox(4 * r, p["spoke"], 8 * w, Vector(-2 * r, -p["spoke"] / 2, -4 * w))
        b.rotate(Vector(), Z, 90 + 360 * k / n)
        bars.append(b)
    windows = [s.makeFillet(p["corner"], [e for e in s.Edges if e.BoundBox.ZLength > w]) for s in ring.cut(bars).Solids]
    bore = hexagon(p["hex"], 30).extrude(Vector(0, 0, 2 * w))
    bore.translate(Vector(0, 0, -w))
    s = Part.makeCylinder(r, w, Vector(0, 0, -w / 2)).cut(windows + [bore]).removeSplitter()
    s.scale(IN)
    return s
