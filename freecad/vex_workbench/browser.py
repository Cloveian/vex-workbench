# VEX parts dock. families and menus up top, the fusion folders under, options for the picked one
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets

from . import catalog, inserts, library, ui
from .metal import IN

KIND = QtCore.Qt.UserRole  # ("family", id), ("menu", id) or ("step", folder/file) on each item
CLEAR = IN  # past whats drawn
_dock = None


def drawn(doc):
    # (min, max) round everything shown in the 3d view, None for nothing
    from pivy import coin
    act = coin.SoGetBoundingBoxAction(coin.SbViewportRegion())
    act.apply(ui.view(doc).getSceneGraph())
    b = act.getBoundingBox()
    return None if b.isEmpty() else (App.Vector(*b.getMin().getValue()), App.Vector(*b.getMax().getValue()))


def land(link, parent, box):
    # off the +x side of box, bottoms level. definitely the first time writing this
    if box is None:
        return
    world = parent.getGlobalPlacement() if parent else App.Placement()
    b = Part.getShape(link).transformed(world.toMatrix()).BoundBox
    plc = link.Placement
    plc.Base += world.Rotation.inverted().multVec(App.Vector(box[1].x + CLEAR - b.XMin, 0, box[0].z - b.ZMin))
    link.Placement = plc


class Browser(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.family = self.menu = None
        self.combos = {}
        self.words = []
        self.opened = []  # folders a search expanded, they close again when its cleared

        self.search = QtWidgets.QLineEdit(placeholderText="search")
        self.tree = QtWidgets.QTreeWidget(headerHidden=True)
        self.form = QtWidgets.QFormLayout()
        self.button = QtWidgets.QPushButton("Place", enabled=False)
        self.align = QtWidgets.QCheckBox("Then align")
        self.align.setToolTip("Opens Align once it's placed, to put it on a hole")
        self.align.setChecked(App.ParamGet(ui.PARAMS).GetBool("PlaceAlign", False))
        self.align.toggled.connect(lambda on: App.ParamGet(ui.PARAMS).SetBool("PlaceAlign", on))
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.tree, 1)
        lay.addLayout(self.form)
        lay.addWidget(self.align)
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
            if words and any(kids) and not it.isExpanded():
                it.setExpanded(True)
                self.opened.append(it)
            return hit or any(kids)
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        cur = self.tree.currentItem()
        if not words:
            for it in self.opened:
                it.setExpanded(False)
            self.opened = []
            if cur is not None:
                self.tree.scrollToItem(cur)  # opens the way back down to whats picked
        kind = cur.data(0, KIND) if cur is not None else None
        if cur is not None and cur.isHidden():
            self.tree.setCurrentItem(None)  # its boxes and Place would still drop the part the search hid
        elif kind and kind[0] != "step" and words and not all(w in cur.text(0).lower() for w in words) and self.first(kind):
            # already picked, its boxes go onto what got searched. "channel" is just its own name, those stay
            self.picked(cur)

    def picked(self, it, _old=None):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.combos, self.family, self.menu, self.insert = {}, None, None, None
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
            if any(p.get("inserts") for p in self.menu["parts"]):
                self.insert = QtWidgets.QComboBox()
                self.insert.addItems(inserts.kinds())
                self.insert.setToolTip("Shaft insert in the HS bore, as its own part. Round is VEX's plastic one, Square the metal one")
                self.form.addRow("Insert", self.insert)
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
        if self.insert is not None:
            self.insert.setEnabled(bool(part.get("inserts")))
            if not part.get("inserts"):
                self.insert.setCurrentText(inserts.NONE)
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
            try:
                part = library.variant(self.family, {p: b.currentText() for p, b in self.combos.items()})
            except ValueError as e:
                ui.warn(str(e))
                return
        doc = App.ActiveDocument or App.newDocument()

        def go():
            box, parent = drawn(doc), ui.active()
            link = library.place(doc, part, parent)
            land(link, parent, box)
            inserts.boxes(link, self.insert.currentText() if self.insert and self.insert.isEnabled() else inserts.NONE)
            return link

        link = ui.run("Place VEX part", go)
        if link is None:
            return
        doc.recompute()
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(link)
        if self.align.isChecked() and not Gui.Control.activeDialog():
            from . import align
            Gui.Control.showDialog(align.Panel())


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
