# parts list: every placed VEX part counted by name, with weights, into a spreadsheet in the document
import FreeCAD as App
import FreeCADGui as Gui

SHEET = "VexPartsList"


def count(doc):
    # name -> [count, g each]. None without a material, step parts and the plates
    out = {}

    def walk(o, n):
        if o.TypeId == "App::Link":
            n *= max(o.ElementCount, 1)  # link arrays
            src = o.LinkedObject
            if hasattr(src, "VexName"):
                each = src.VexMass.getValueAs("g").Value if hasattr(src, "VexMass") else None
                out.setdefault(src.VexName, [0, each])[0] += n
                return
            o = src  # a linked sub-assembly, its parts n more times
        for child in getattr(o, "Group", []):
            walk(child, n)

    # from the top of the tree, RootObjects leaves out a sub-assembly once its linked
    for o in doc.Objects:
        # link array elements look top level too, and pass Group through to what the array links
        if o.TypeId != "App::LinkElement" and o.getParentGroup() is None and o.getParentGeoFeatureGroup() is None:
            walk(o, 1)
    return out


def fill(doc):
    sheet = doc.getObject(SHEET) or doc.addObject("Spreadsheet::Sheet", SHEET)
    sheet.Label = "VEX parts list"
    sheet.clearAll()
    for col, head in zip("ABCD", ("Part", "Count", "Each (g)", "Total (g)")):
        sheet.set(f"{col}1", head)
    grams = parts = unknown = 0
    rows = sorted(count(doc).items())
    for row, (name, (n, each)) in enumerate(rows, 2):
        sheet.set(f"A{row}", name)
        sheet.set(f"B{row}", str(n))
        parts += n
        if each is None:
            sheet.set(f"C{row}", "?")
            unknown += n
            continue
        sheet.set(f"C{row}", f"{each:.2f}")
        sheet.set(f"D{row}", f"{n * each:.2f}")
        grams += n * each
    end = len(rows) + 3
    note = f", {unknown} without a weight" if unknown else ""
    sheet.set(f"A{end}", f"Total, {parts} parts{note}")
    sheet.set(f"D{end}", f"{grams:.1f}")
    sheet.recompute()
    return sheet


class PartsList:
    def GetResources(self):
        return {"Pixmap": "vex-list.svg", "MenuText": "Parts list",
                "ToolTip": "Count every VEX part in the document, with weights, into a spreadsheet"}

    def Activated(self):
        App.setActiveTransaction("VEX parts list")
        sheet = fill(App.ActiveDocument)
        App.closeActiveTransaction()
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(sheet)

    def IsActive(self):
        return App.ActiveDocument is not None
