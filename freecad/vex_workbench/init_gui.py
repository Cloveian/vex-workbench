# vex workbench, gui side
import os

import FreeCADGui as Gui

ICONS = os.path.join(os.path.dirname(__file__), "resources", "icons")


class VexWorkbench(Gui.Workbench):
    MenuText = "VEX"
    ToolTip = "VEX V5 parts with snap frames for Assembly"
    Icon = os.path.join(ICONS, "vex.svg")

    def Initialize(self):
        # no commands yet
        self.appendToolbar("VEX", [])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addIconPath(ICONS)
Gui.addWorkbench(VexWorkbench())
