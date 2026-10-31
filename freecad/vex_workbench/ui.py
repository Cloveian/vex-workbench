# undo step, wait cursor and the error box around anything that builds parts. and the panels number boxes
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

PARAMS = "User parameter:BaseApp/Preferences/Mod/VexWorkbench"


def run(title, fn):
    # a ValueError out of fn (no generator, no holes, holes off axis) gets undone and shown, None back
    App.setActiveTransaction(title)
    err = None
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)  # a 35 long channel is a few s to build
    try:
        out = fn()
    except ValueError as e:
        err = str(e)
    finally:
        QtWidgets.QApplication.restoreOverrideCursor()
    if err is not None:
        App.closeActiveTransaction(True)
        QtWidgets.QMessageBox.warning(Gui.getMainWindow(), "VEX", err)
        return None
    App.closeActiveTransaction()
    return out


def number(lo, hi, suffix, value=0.0, step=1.0, decimals=2):
    box = QtWidgets.QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setSuffix(suffix)
    box.setValue(value)
    return box
