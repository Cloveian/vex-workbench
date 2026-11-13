# flex wheels. 1.625 and 2 in: a disc with a hex bore and windows between straight spokes. 3 and 4 in: a versahub bore and bolt circle, windows and slots off fusion's outline
import Part
from FreeCAD import Vector

from .metal import IN
from .slide import section
from .stock import hexagon

FAMILIES = ("flex-wheel", "big-flex-wheel")
Z = Vector(0, 0, 1)

# in, one side of a window on +y and the slot over a bolt hole, like slide.half takes. 1 and 3.5 mm rounds
WINDOWS = {
    3: [(0, 0.7677), ((0.1683, 0.7491), (0, 0)), ((0.2149, 0.7773), (0.1769, 0.7875)), (0.2590, 0.9419), ((0.2626, 0.9949), (0.1259, 0.9776)), (0.2445, 1.1381), ((0.1210, 1.2580), (0.1078, 1.1208)), ((0, 1.2638), (0, 0))],
    4: [(0, 0.7677), ((0.1683, 0.7491), (0, 0)), ((0.2149, 0.7773), (0.1769, 0.7875)), (0.2978, 1.0866), ((0.3024, 1.1162), (0.1647, 1.1222)), (0.3222, 1.5698), ((0.2005, 1.7127), (0.1845, 1.5759)), ((0, 1.7244), (0, 0))],
}
SLOTS = {
    3: [(0, 1.1024), ((0.0753, 1.0998), (0, 0)), ((0.1945, 1.1539), (0.0848, 1.2373)), (0.2190, 1.1861), ((0.1936, 1.2489), (0.1876, 1.2100)), ((0, 1.2638), (0, 0))],
    4: [(0, 1.1417), ((0.0225, 1.1415), (0, 0)), ((0.1474, 1.2157), (0.0252, 1.2793)), (0.3021, 1.5128), ((0.1955, 1.7133), (0.1799, 1.5764)), ((0, 1.7244), (0, 0))],
}


def big(p):
    # mm, straight through. windows on 60s, a bolt hole and the slot over it halway between
    circle = lambda r, y=0: Part.Face(Part.Wire(Part.makeCircle(r * IN, Vector(0, y, 0) * IN)))
    window, slot = (section(t[p["od"]]).rotated(Vector(), Vector(1, 0, 0), -90) for t in (WINDOWS, SLOTS))  # off x-z
    hole = circle(p["hole"] / 2, p["bolts"] / 2)
    cuts = [circle(p["bore"] / 2)]
    for k in range(6):
        cuts += [window.rotated(Vector(), Z, 60 * k)] + [s.rotated(Vector(), Z, 60 * k + 30) for s in (slot, hole)]
    w = p["width"] * IN
    return circle(p["od"] / 2).cut(cuts).extrude(Vector(0, 0, w)).translated(Vector(0, 0, -w / 2))


def make(part, cat):
    if part["family"] == "big-flex-wheel":
        return big(part["params"])
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
