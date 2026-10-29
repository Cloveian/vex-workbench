# snap to hole: click holes on VEX parts, get a frame on each exact center for Assembly joints
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from . import library


def picked():
    # (link, point in its own coords) per clicked spot on a VEX part
    out = []
    for sel in Gui.Selection.getSelectionEx("", 0):
        for sub, pt in zip(sel.SubElementNames, sel.PickedPoints):
            objs = sel.Object.getSubObjectList(sub)  # root first, then one per name in sub
            k = max((i for i, o in enumerate(objs) if hasattr(o, "VexFamily") or hasattr(o, "VexStep")), default=None)
            if k is None:
                continue
            # placement of the link through the whole path, assembly and all. App::Link has no getGlobalPlacement in 1.1
            plc = sel.Object.getSubObject(".".join(sub.split(".")[:k]) + ".", retType=3) if k else sel.Object.Placement
            out.append((objs[k], plc.inverse().multVec(pt)))
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
        App.setActiveTransaction("VEX hole frame")
        try:
            for link, pt in spots:
                library.hole_frame(link, pt)
        except ValueError as e:
            App.closeActiveTransaction(True)
            QtWidgets.QMessageBox.warning(Gui.getMainWindow(), "VEX", str(e))
            return
        App.closeActiveTransaction()
        App.ActiveDocument.recompute()
        Gui.Selection.clearSelection()

    def IsActive(self):
        return App.ActiveDocument is not None
