import json
import re
from html import escape
from pathlib import Path

from templates.language import language_switch_html


# Keys are also used by dynamic controls in led_mapping.js.
WORDS = {
    "title": ("Griffe und LEDs", "Grips and LEDs"),
    "grips": ("Griffraster bearbeiten", "Edit grip grids"),
    "leds": ("LED-Raster", "LED grids"),
    "links": ("Zuordnung prüfen", "Review associations"),
    "moon": ("Virtuelles MoonBoard", "Virtual MoonBoard"),
    "intro": ("Grün: Grifflöcher · Gelb: sichtbare LEDs mit physischen Nummern. Die LED-Punkte müssen auf den LED-Bohrungen liegen. Kopierte Griffraster sind nur eine Ausgangsbasis.", "Green: grip holes · Yellow: visible LEDs with physical numbers. Place LED points on the actual LED holes. Copied grip grids are only a starting point."),
    "surfacehelp": ("Gleiche Wandfläche = gleiche Kennung. Zuordnungen dürfen Rastergrenzen überqueren, aber keine Wandkante. Ordne Raster auf unterschiedlichen Wandflächen verschiedenen Kennungen zu.", "Use the same surface ID for grids on the same wall plane. Associations may cross grid boundaries but not wall corners. Give different planes different surface IDs."),
    "gripsurfaces": ("Wandflächen der Griffraster", "Grip grid surfaces"),
    "grid": ("Raster", "Grid"), "name": ("Name", "Name"),
    "row": ("Reihe", "Row"), "col": ("Spalte", "Column"), "extra": ("Zusatzloch", "Extra hole"),
    "surface": ("Wandfläche", "Wall surface"), "rows": ("Reihen", "Rows"),
    "cols": ("Spalten (alle Positionen)", "Columns (all positions)"),
    "alternating": ("Alternierendes Raster", "Alternating grid"),
    "offset": ("Oberste Reihe eingerückt", "Top row offset"),
    "start": ("Kabelstart", "Cable start"), "path": ("Kabelverlauf", "Cable path"),
    "top_left": ("Oben links", "Top left"), "top_right": ("Oben rechts", "Top right"),
    "bottom_left": ("Unten links", "Bottom left"), "bottom_right": ("Unten rechts", "Bottom right"),
    "horizontal": ("Horizontal", "Horizontal"), "vertical": ("Vertikal", "Vertical"),
    "physical": ("Erste physische LED (leer = fortlaufend)", "First physical LED (blank = continue)"),
    "skip": ("Unsichtbare LEDs überspringen (Nummern oder Bereiche, z. B. 12, 18–20)", "Skip hidden LEDs (IDs or ranges, e.g. 12, 18–20)"),
    "skiphelp": ("Übersprungene Nummern bleiben im Kabel vorhanden. Ein abgewählter gelber Punkt entfernt dagegen nur die sichtbare Position; die nachfolgenden Nummern rücken auf. Nummern beginnen bei 0, wie in WLED.", "Skipped IDs still exist on the cable. Disabling a yellow point removes only the visible position; following IDs move forward. IDs start at 0, as in WLED."),
    "add": ("Neues LED-Raster", "New LED grid"), "copy": ("Gewähltes Griffraster kopieren", "Copy selected grip grid"),
    "delete": ("LED-Raster löschen", "Delete LED grid"),
    "deleteconfirm": ("Dieses LED-Raster aus dem Entwurf löschen?", "Delete this LED grid from the draft?"),
    "earlier": ("Im Kabel davor", "Earlier on cable"), "later": ("Im Kabel danach", "Later on cable"),
    "corners": ("Vier LED-Ecken neu anklicken", "Pick four LED corners"),
    "cornerhelp": ("Reihenfolge: links oben, rechts oben, rechts unten, links unten. Danach Zuordnung berechnen.", "Order: top left, top right, bottom right, bottom left. Then calculate associations."),
    "cancel": ("Abbrechen", "Cancel"),
    "shift": ("Versatz in Rasterreihen", "Offset in grid rows"), "shiftbutton": ("LED-Raster verschieben", "Shift LED grid"),
    "addpoint": ("Einzelne LED setzen", "Place individual LED"),
    "end": ("Am Kabelende dieses Rasters", "At the end of this grid's cable"),
    "before": ("Vor Rasterposition", "Before grid position"),
    "remove": ("Entfernen", "Remove"), "extras": ("Einzelne LEDs", "Individual LEDs"),
    "precision": ("Eckpunkte und Suchabstände", "Corners and matching distances"),
    "lateral": ("Seitliche Toleranz (Spaltenabstände)", "Lateral tolerance (column intervals)"),
    "distance": ("Maximalabstand (Abstand senkrecht benachbarter Griffe)", "Maximum distance (vertical grip intervals)"),
    "calculate": ("Zuordnung berechnen", "Calculate associations"),
    "draft": ("Entwurf speichern", "Save draft"), "activate": ("Geprüfte Zuordnung aktivieren", "Activate reviewed associations"),
    "deactivate": ("Bisherige Zuordnung verwenden", "Use legacy mapping"),
    "active": ("Getrennte LED-Zuordnung aktiv. Änderungen bleiben bis zur nächsten Aktivierung ein Entwurf.", "Independent LED mapping active. Edits remain a draft until activated again."),
    "legacy": ("Bisherige Zuordnung aktiv. Dieser Entwurf verändert die Beleuchtung noch nicht.", "Legacy mapping active. This draft does not change the lighting yet."),
    "saved": ("Entwurf gespeichert.", "Draft saved."), "activated": ("Aktiviert. Gilt ab dem nächsten Routenaufruf; MoonBoard-Zuordnungen beim Öffnen neu berechnet.", "Activated. Applies on the next route event; MoonBoard associations recalculate when opened."),
    "dirty": ("Änderungen noch nicht berechnet. Vorschau und Aktivierung sind erst nach der Berechnung verfügbar.", "Changes have not been calculated. Calculate before previewing or activating."),
    "below": ("Unterhalb", "Below"), "above": ("Oberhalb", "Above"), "both": ("Beides", "Both"),
    "automatic": ("Automatisch", "Automatic"), "manual": ("Manuell", "Manual"),
    "missing": ("Fehlt", "Missing"), "ambiguous": ("Mehrdeutig", "Ambiguous"),
    "disabled": ("Ohne LED", "No LED"), "all": ("Alle Griffe", "All grips"),
    "issues": ("Fehlende / mehrdeutige", "Missing / ambiguous"),
    "reviewhelp": ("Griff im Bild oder in der Tabelle wählen. Blau = oberhalb, Orange = unterhalb. Fehlende LEDs werden nicht ersetzt. Nur Ausnahmen müssen manuell zugeordnet werden. Bei Beides hat die untere Beleuchtung Vorrang, wenn sich zwei Griffe eine LED teilen.", "Select a grip in the image or table. Blue = above, orange = below. Missing LEDs have no fallback. Only exceptions need manual assignment. In Both mode, below lighting wins if two grips share an LED."),
    "preview": ("Ausgewählten Griff beleuchten", "Light selected grip"),
    "stop": ("Test beenden / Beleuchtung wiederherstellen", "Stop test / restore lighting"),
    "testled": ("Ausgewählte LED testen", "Test selected LED"),
    "position": ("LED-Position auswählen", "Select LED position"),
    "toggle": ("Position abwählen / aktivieren", "Disable / enable position"),
    "selected": ("Ausgewählter Griff", "Selected grip"),
    "none": ("Keiner", "None"), "unconfigured": ("LEDs außerhalb der Controller-Bereiche", "LEDs outside controller ranges"),
    "invalidnumbers": ("Ungültige LED-Nummern. Ganze Zahlen oder Bereiche verwenden.", "Invalid LED IDs. Use integers or ranges."),
    "unsaved": ("Nicht gespeicherte Änderungen verlassen?", "Leave without saving changes?"),
}


def return_led_mapping_html(data, image_url, path_prefix=""):
    root = Path(__file__).parent
    html = (root / "led_mapping.html").read_text(encoding="utf-8")
    replacements = {
        "__DATA__": json.dumps(data, separators=(",", ":")).replace("</", "<\\/"),
        "__IMAGE__": escape(str(image_url or ""), quote=True),
        "__API__": json.dumps(f"{path_prefix}/ledmapping"),
        "__PREVIEW__": json.dumps(f"{path_prefix}/virtualmapping/preview"),
        "__GRIPS__": f"{path_prefix}/wallcreation?id={data['wallid']}",
        "__MOON__": f"{path_prefix}/virtualmapping?id={data['wallid']}",
        "__LANGUAGE__": language_switch_html({lang: {key: values[i] for key, values in WORDS.items()}
                                               for i, lang in enumerate(("de", "en"))}),
        "__SCRIPT__": (root / "led_mapping.js").read_text(encoding="utf-8"),
    }
    # Insert the script first so its URL/data placeholders are also replaced.
    html = html.replace("__SCRIPT__", replacements.pop("__SCRIPT__"))
    # Substitute once: user-provided names must not become template tokens.
    return re.sub("|".join(re.escape(key) for key in replacements),
                  lambda match: replacements[match.group()], html)
