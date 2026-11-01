# parts list: every placed VEX part counted by name, with weights, into a spreadsheet in the document
import FreeCAD as App
import FreeCADGui as Gui

from . import library

SHEET = "VexPartsList"


def weight(src):
    return src.VexMass.getValueAs("g").Value if hasattr(src, "VexMass") else None


def count(doc):
    # name -> [count, g each, g all of them]. grams None without a material, step parts and license plates
    out = {}

    def walk(o, n):
        if o.TypeId == "App::Link":
            n *= max(o.ElementCount, 1)  # link arrays
            src = o.LinkedObject
            if hasattr(src, "VexName"):
                g = weight(src)
                row = out.setdefault(src.VexName, [0, g, None if g is None else 0])
                row[0] += n
                if g is not None:
                    row[1] = max(row[1], g)  # heaviest copy, a worked one with its holes changed has no plain source
                    row[2] += n * g
                return
            o = src  # a linked sub-assembly, its parts n more times
        for child in getattr(o, "Group", []):
            walk(child, n)

    for o in library.roots(doc):
        walk(o, 1)
    # each = off the shelf weight, a bend adds a bit and a cut takes some off
    for src in getattr(doc.getObject(library.GROUP), "Group", []):
        if getattr(src, "VexName", None) in out and not getattr(src, "VexSteps", ""):
            out[src.VexName][1] = weight(src)
    return out


def fill(doc):
    sheet = doc.getObject(SHEET) or doc.addObject("Spreadsheet::Sheet", SHEET)
    sheet.Label = "VEX parts list"
    sheet.clearAll()
    for col, head in zip("ABCD", ("Part", "Count", "Each (g)", "Total (g)")):
        sheet.set(f"{col}1", head)
    grams = parts = unknown = 0
    rows = sorted(count(doc).items())
    for row, (name, (n, each, total)) in enumerate(rows, 2):
        sheet.set(f"A{row}", name)
        sheet.set(f"B{row}", str(n))
        parts += n
        if each is None:
            sheet.set(f"C{row}", "?")
            unknown += n
            continue
        sheet.set(f"C{row}", f"{each:.2f}")
        sheet.set(f"D{row}", f"{total:.2f}")
        grams += total
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
