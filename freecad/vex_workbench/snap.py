# snap to hole: click holes on VEX parts, get a frame on each exact center for Assembly joints
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from . import library, ui


def spot(root, sub, pt):
    # (link, point in its own coords, link placement in the world, (root, path down to the link)) for one click, None off VEX parts
    objs = root.getSubObjectList(sub)  # root first, then one per name in sub
    k = max((i for i, o in enumerate(objs) if hasattr(o, "VexFamily") or hasattr(o, "VexStep")), default=None)
    if k is None:
        return None
    names = sub.split(".")
    # a link array element sits under the link, its placement counts too. a number in the path, or a LinkElement with ShowElement on
    element = names[k].isdigit() or (k + 1 < len(objs) and objs[k + 1].isDerivedFrom("App::LinkElement"))
    n = k + 1 if element else k
    # placement of the link through the whole path, assembly and all. App::Link has no getGlobalPlacement in 1.1
    path = "".join(name + "." for name in names[:n])
    plc = root.getSubObject(path, retType=3) if n else root.Placement
    return objs[k], plc.inverse().multVec(pt), plc, (root, path)


def picked():
    out = []
    for sel in Gui.Selection.getSelectionEx("", 0):
        for sub, pt in zip(sel.SubElementNames, sel.PickedPoints):
            s = spot(sel.Object, sub, pt)
            if s:
                out.append(s)
    return out


class HoleFrame:
    def GetResources(self):
        return {"Pixmap": "vex-hole.svg", "MenuText": "Frame on hole",
                "ToolTip": "Frame on the exact center of each clicked hole, or on the end of a shaft, to joint to"}

    def Activated(self):
        spots = picked()
        if not spots:
            QtWidgets.QMessageBox.information(Gui.getMainWindow(), "VEX", "Click a hole on a VEX part first")
            return
        if ui.run("VEX hole frame", lambda: [library.hole_frame(link, pt) for link, pt, *_ in spots]) is None:
            return
        App.ActiveDocument.recompute()
        Gui.Selection.clearSelection()

    def IsActive(self):
        return App.ActiveDocument is not None
