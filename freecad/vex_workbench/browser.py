# VEX parts dock. families up top, the fusion folders under, options for the picked family
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from . import catalog, library, ui

KIND = QtCore.Qt.UserRole  # ("family", id) or ("step", folder/file) on each item
_dock = None


class Browser(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.family = None
        self.combos = {}
        self.words = []

        self.search = QtWidgets.QLineEdit(placeholderText="search")
        self.tree = QtWidgets.QTreeWidget(headerHidden=True)
        self.form = QtWidgets.QFormLayout()
        self.button = QtWidgets.QPushButton("Place", enabled=False)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.tree, 1)
        lay.addLayout(self.form)
        lay.addWidget(self.button)

        self.fill()
        self.search.textChanged.connect(self.filter)
        self.tree.currentItemChanged.connect(self.picked)
        self.tree.itemDoubleClicked.connect(lambda *_: self.place())
        self.button.clicked.connect(self.place)

    def fill(self):
        families, _, steps = library.index()
        for fam in families.values():
            it = QtWidgets.QTreeWidgetItem(self.tree, [fam["title"]])
            it.setData(0, KIND, ("family", fam["id"]))
            if fam["id"] not in library.GENERATORS:
                it.setDisabled(True)
                it.setToolTip(0, "no generator yet")
        folders = {}
        for key, p in steps.items():
            if not catalog.has(p):
                continue  # not shipped and not downloaded
            parent = self.tree
            path = ""
            for bit in p["folder"].split("/"):
                path += "/" + bit
                if path not in folders:
                    folders[path] = QtWidgets.QTreeWidgetItem(parent, [bit])
                parent = folders[path]
            QtWidgets.QTreeWidgetItem(parent, [p["name"]]).setData(0, KIND, ("step", key))

    def filter(self, text):
        # an item shows if it or anything under it has every word, any order. a family shows if one of its variants does
        words = self.words = text.lower().split()

        def walk(it):
            kind = it.data(0, KIND)
            family = kind and kind[0] == "family"
            hit = all(w in it.text(0).lower() for w in words) or (family and self.first(kind[1]) is not None)
            kids = [walk(it.child(i)) for i in range(it.childCount())]
            it.setHidden(not (hit or any(kids)))
            if words and any(kids):
                it.setExpanded(True)
            return hit or any(kids)
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))

    def picked(self, it, _old=None):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.combos, self.family = {}, None
        kind = it.data(0, KIND) if it else None
        self.button.setEnabled(bool(kind))
        if not kind or kind[0] != "family":
            return
        self.family = library.index()[0][kind[1]]
        for prop, choices in library.options(self.family):
            box = QtWidgets.QComboBox()
            box.addItems([library.label(c) for c in choices])
            self.form.addRow(prop, box)
            self.combos[prop] = box
        # searched "1x2x1x25 steel", start on that one
        part = self.first(kind[1]) if self.words else None
        if part:
            for prop, lb in library.picks(self.family, part).items():
                self.combos[prop].setCurrentText(lb)

    def first(self, family):
        # first variant of a family with every serached word in its name
        for p in library.index()[1].values():
            if p["family"] == family and all(w in p["name"].lower() for w in self.words):
                return p
        return None

    def place(self):
        it = self.tree.currentItem()
        kind = it.data(0, KIND) if it else None
        if not kind:
            return
        if kind[0] == "step":
            part = library.index()[2][kind[1]]
        else:
            part = library.variant(self.family, {p: b.currentText() for p, b in self.combos.items()})
        doc = App.ActiveDocument or App.newDocument()
        import UtilsAssembly  # Assembly workbench
        link = ui.run("Place VEX part", lambda: library.place(doc, part, UtilsAssembly.activePartOrAssembly()))
        if link is None:
            return
        doc.recompute()
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(link)


class ShowBrowser:
    def GetResources(self):
        return {"Pixmap": "vex.svg", "MenuText": "VEX parts", "ToolTip": "Browse and place VEX parts"}

    def Activated(self):
        global _dock
        if _dock is None:
            _dock = QtWidgets.QDockWidget("VEX parts", Gui.getMainWindow())
            _dock.setObjectName("VexParts")
            _dock.setWidget(Browser())
            Gui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea, _dock)
        _dock.show()
        _dock.raise_()

    def IsActive(self):
        return True
