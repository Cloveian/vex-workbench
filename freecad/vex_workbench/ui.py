# undo step, wait cursor and the error box around anything that builds parts. and the panels number boxes, and toolbar buttons that open them
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from . import library

PARAMS = "User parameter:BaseApp/Preferences/Mod/VexWorkbench"


def run(title, fn):
    # a ValueError out of fn (no generator, no holes, holes off axis) gets undone and shown, None back
    App.setActiveTransaction(title)
    err = None
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)  # a 35 long channel is a few s to build
    try:
        out = fn()
    except ValueError as e:
        err = str(e) or f"{title} didn't work"
    except Exception:
        App.closeActiveTransaction(True)  # a bug. undone, and the traceback still goes to the report view
        raise
    finally:
        QtWidgets.QApplication.restoreOverrideCursor()
    if err is not None:
        App.closeActiveTransaction(True)
        warn(err)
        return None
    App.closeActiveTransaction()
    return out


def warn(msg):
    QtWidgets.QMessageBox.warning(Gui.getMainWindow(), "VEX", msg)


def active():
    # active assembly or part to put new stuff in. double clicking a placed part makes its hidden source the active part, and whatever went in there showed up in every copy
    import UtilsAssembly  # Assembly workbench
    got = UtilsAssembly.activePartOrAssembly()
    parent = got and got.getParentGroup()
    return None if parent and parent.Name == library.GROUP else got


def view(doc):
    # docs 3d view. a spreadsheet or techdraw page in front has no scene
    gd = Gui.getDocument(doc.Name)
    return gd.ActiveView if hasattr(gd.ActiveView, "getSceneGraph") else gd.mdiViewsOfType("Gui::View3DInventor")[0]


def number(lo, hi, suffix, value=0.0, step=1.0, decimals=2):
    box = QtWidgets.QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setSuffix(suffix)
    box.setValue(value)
    return box


class Command:
    # greyed out while another panel is open
    def __init__(self, panel, icon, name, tip):
        self.panel, self.res = panel, {"Pixmap": icon, "MenuText": name, "ToolTip": tip}

    def GetResources(self):
        return self.res

    def Activated(self):
        Gui.Control.showDialog(self.panel())

    def IsActive(self):
        return App.ActiveDocument is not None and not Gui.Control.activeDialog()
