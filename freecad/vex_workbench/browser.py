# VEX parts dock. families and menus up top, the fusion folders under, options for the picked one
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from . import catalog, library, ui

KIND = QtCore.Qt.UserRole  # ("family", id), ("menu", id) or ("step", folder/file) on each item
_dock = None


class Browser(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.family = self.menu = None
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
        for m in library.menus().values():
            it = QtWidgets.QTreeWidgetItem(self.tree, [m["title"]])
            it.setData(0, KIND, ("menu", m["id"]))
            if not m["parts"]:
                it.setDisabled(True)
                it.setToolTip(0, "none of their step files are here")
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
        # an item shows if it or anything under it has every word, any order. a family or menu shows if one of its variants does
        words = self.words = text.lower().split()

        def walk(it):
            kind = it.data(0, KIND)
            boxes = kind and kind[0] != "step"
            hit = all(w in it.text(0).lower() for w in words) or (boxes and self.first(kind) is not None)
            kids = [walk(it.child(i)) for i in range(it.childCount())]
            it.setHidden(not (hit or any(kids)))
            if words and any(kids):
                it.setExpanded(True)
            return hit or any(kids)
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        cur = self.tree.currentItem()
        if cur is not None and cur.isHidden():
            self.tree.setCurrentItem(None)  # its boxes and Place would still drop the part the search hid

    def picked(self, it, _old=None):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.combos, self.family, self.menu = {}, None, None
        kind = it.data(0, KIND) if it else None
        self.button.setEnabled(bool(kind))
        # searched "1x2x1x25 steel", start on that one
        part = self.first(kind) if kind and kind[0] != "step" and self.words else None
        if kind and kind[0] == "menu":
            self.menu = library.menus()[kind[1]]
            for axis in self.menu["axes"]:
                box = QtWidgets.QComboBox()
                box.currentTextChanged.connect(lambda _: self.narrow())
                self.form.addRow(axis, box)
                self.combos[axis] = box
            self.narrow(part)
        if not kind or kind[0] != "family":
            return
        self.family = library.index()[0][kind[1]]
        for prop, choices in library.options(self.family):
            box = QtWidgets.QComboBox()
            box.addItems([library.label(c) for c in choices])
            self.form.addRow(prop, box)
            self.combos[prop] = box
        if part:
            for prop, lb in library.picks(self.family, part).items():
                self.combos[prop].setCurrentText(lb)

    def narrow(self, picked=None):
        # refills the menu boxes, signals off or every clear() narrows again
        rows, part = catalog.narrowed(self.menu, picked or {a: b.currentText() for a, b in self.combos.items()})
        for axis, choices in rows:
            box = self.combos[axis]
            box.blockSignals(True)
            box.clear()
            box.addItems(choices)
            box.setCurrentText(part[axis])
            box.blockSignals(False)
        return part

    def first(self, kind):
        # first variant of a family or part of a menu with every serached word in its name
        if kind[0] == "menu":
            named = [(p, p["part"]) for p in library.menus()[kind[1]]["parts"]]
        else:
            named = [(p, p["name"]) for p in library.index()[1].values() if p["family"] == kind[1]]
        return next((p for p, name in named if all(w in name.lower() for w in self.words)), None)

    def place(self):
        it = self.tree.currentItem()
        kind = it.data(0, KIND) if it else None
        if not kind:
            return
        if kind[0] == "step":
            part = library.index()[2][kind[1]]
        elif kind[0] == "menu":
            part = library.index()[2][self.narrow()["key"]]
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
