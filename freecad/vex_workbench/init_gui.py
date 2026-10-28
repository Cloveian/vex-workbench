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
        from . import browser
        Gui.addCommand("Vex_Browser", browser.ShowBrowser())
        self.appendToolbar("VEX", ["Vex_Browser"])
        self.appendMenu("VEX", ["Vex_Browser"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addIconPath(ICONS)
Gui.addWorkbench(VexWorkbench())
# at startup, placed parts in an opened file have to follow their params before the workbench is ever picked
App.addDocumentObserver(library.Observer())
