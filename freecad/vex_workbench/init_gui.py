# vex workbench, gui side
import os

import FreeCAD as App
import FreeCADGui as Gui

from . import library

ICONS = os.path.join(os.path.dirname(__file__), "resources", "icons")


class VexWorkbench(Gui.Workbench):
    MenuText = "VEX"
    ToolTip = "VEX V5 parts with snap frames for Assembly"
    Icon = os.path.join(ICONS, "vex.svg")

    def Initialize(self):
        from . import align, browser, partslist, screws, shop, snap, spacers
        cmds = {"Vex_Browser": browser.ShowBrowser(), "Vex_HoleFrame": snap.HoleFrame(), "Vex_Align": align.Align(), "Vex_Screw": screws.Screw(),
                "Vex_Spacers": spacers.Spacers(), "Vex_Bend": shop.BEND, "Vex_Cut": shop.CUT, "Vex_Drill": shop.DRILL, "Vex_PartsList": partslist.PartsList()}
        for name, cmd in cmds.items():
            Gui.addCommand(name, cmd)
        self.appendToolbar("VEX", list(cmds))
        self.appendMenu("VEX", list(cmds))

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addIconPath(ICONS)
Gui.addWorkbench(VexWorkbench())
# at startup, placed parts in an opened file have to follow their params before the workbench is ever picked
App.addDocumentObserver(library.Observer())
