import json
from html import escape

from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Virtual MoonBoard mapping",
        "page.heading": "Virtual MoonBoard mapping",
        "page.description": "Calculate a temporary LED list as before, or save named MoonBoard installations for later use.",
        "saved.heading": "Saved MoonBoard installations",
        "saved.description": "Several Mini or Standard MoonBoards can be stored on the same CRUX wall, including more than one installation of the same setup.",
        "saved.select": "Saved mapping:",
        "saved.temporary": "Temporary / new mapping",
        "form.mapping_name": "Installation name:",
        "form.mapping_name_placeholder": "e.g. Mini left",
        "form.board_type": "MoonBoard:",
        "form.board_mini": "Mini MoonBoard",
        "form.board_standard": "Standard MoonBoard",
        "form.setup": "Setup:",
        "form.rows": "Rows:",
        "form.columns": "Columns:",
        "form.alternating": "Alternating grid",
        "form.top_row": "Top row:",
        "form.not_offset": "Not offset",
        "form.offset": "Offset",
        "form.led_zero": "Virtual LED start:",
        "form.cable_path": "Virtual cable path:",
        "form.top_left": "Top left",
        "form.top_right": "Top right",
        "form.bottom_left": "Bottom left",
        "form.bottom_right": "Bottom right",
        "form.horizontal": "Horizontal (row by row)",
        "form.vertical": "Vertical (column by column)",
        "help.corners": "Click four MoonBoard corner points in this order:",
        "help.corner_order": "Top left, top right, bottom right, bottom left",
        "help.mapping": "Calculate remains temporary and produces the same copyable list as before. Save mapping stores the selected board, setup, corners, CRUX hold IDs and physical LEDs in the bridge database.",
        "help.preview": "The preview lights the mapped physical cable LEDs orange. Stop it to restore the previous route or off state.",
        "button.calculate": "Calculate physical LED list",
        "button.new": "New / temporary",
        "button.save": "Save mapping",
        "button.update": "Update mapping",
        "button.delete": "Delete mapping",
        "button.reset": "Reset virtual grid",
        "button.copy": "Copy LED list",
        "button.preview": "Light mapped LEDs",
        "button.restore": "Stop preview and restore lighting",
        "result.heading": "Physical cable LED numbers",
        "result.description": "Comma-separated in the selected virtual cable order:",
        "status.points": "Corner points: {count} / 4",
        "status.calculating": "Calculating nearest physical LEDs...",
        "status.mapped": "Mapped {virtual} virtual positions to {physical} physical LEDs. Repeated physical IDs: {duplicates}.",
        "status.copied": "LED list copied.",
        "status.loaded": "Loaded saved mapping “{name}”.",
        "status.saving": "Saving MoonBoard mapping...",
        "status.saved": "Saved MoonBoard mapping “{name}”.",
        "status.deleting": "Deleting MoonBoard mapping...",
        "status.deleted": "Saved MoonBoard mapping deleted. Temporary mode is active.",
        "status.previewing": "Lighting mapped physical LEDs...",
        "status.preview_active": "Mapped physical LEDs are lit. Successful controllers: {successful}; failed: {failed}.",
        "status.restoring": "Restoring previous wall lighting...",
        "status.restored": "Previous wall lighting restored.",
        "status.preview_error": "LED preview failed: {message}",
        "status.error": "Could not calculate the mapping: {message}",
        "status.save_error": "Could not save the mapping: {message}",
        "status.delete_error": "Could not delete the mapping: {message}",
        "alert.alternating_columns": "Columns must be at least 2 for an alternating grid.",
        "alert.dimensions": "Rows and columns must be positive whole numbers.",
        "alert.name": "Enter a name for this MoonBoard installation.",
        "alert.points": "Select all four MoonBoard corners first.",
        "alert.delete_confirm": "Delete the selected MoonBoard mapping?",
        "image.alt": "Climbing wall",
    },
    "de": {
        "page.title": "Virtuelle MoonBoard-Zuordnung",
        "page.heading": "Virtuelle MoonBoard-Zuordnung",
        "page.description": "Berechne wie bisher eine temporäre LED-Liste oder speichere benannte MoonBoard-Installationen zur späteren Verwendung.",
        "saved.heading": "Gespeicherte MoonBoard-Installationen",
        "saved.description": "An derselben CRUX-Wand können mehrere Mini- oder Standard-MoonBoards gespeichert werden – auch mehrere Installationen desselben Setups.",
        "saved.select": "Gespeicherte Zuordnung:",
        "saved.temporary": "Temporäre / neue Zuordnung",
        "form.mapping_name": "Name der Installation:",
        "form.mapping_name_placeholder": "z. B. Mini links",
        "form.board_type": "MoonBoard:",
        "form.board_mini": "Mini MoonBoard",
        "form.board_standard": "Standard-MoonBoard",
        "form.setup": "Setup:",
        "form.rows": "Reihen:",
        "form.columns": "Spalten:",
        "form.alternating": "Alternierendes Raster",
        "form.top_row": "Oberste Reihe:",
        "form.not_offset": "Nicht eingerückt",
        "form.offset": "Eingerückt",
        "form.led_zero": "Virtueller LED-Start:",
        "form.cable_path": "Virtueller Kabelverlauf:",
        "form.top_left": "Oben links",
        "form.top_right": "Oben rechts",
        "form.bottom_left": "Unten links",
        "form.bottom_right": "Unten rechts",
        "form.horizontal": "Horizontal (zeilenweise)",
        "form.vertical": "Vertikal (spaltenweise)",
        "help.corners": "Klicke vier MoonBoard-Eckpunkte in dieser Reihenfolge an:",
        "help.corner_order": "Links oben, rechts oben, rechts unten, links unten",
        "help.mapping": "„Berechnen“ bleibt temporär und erzeugt dieselbe kopierbare Liste wie bisher. „Zuordnung speichern“ legt Board, Setup, Eckpunkte, CRUX-Griff-IDs und physische LEDs dauerhaft in der Bridge-Datenbank ab.",
        "help.preview": "Die Vorschau lässt die zugeordneten physischen Kabel-LEDs orange leuchten. Beim Beenden wird die vorherige Route beziehungsweise der ausgeschaltete Zustand wiederhergestellt.",
        "button.calculate": "Physische LED-Liste berechnen",
        "button.new": "Neu / temporär",
        "button.save": "Zuordnung speichern",
        "button.update": "Zuordnung aktualisieren",
        "button.delete": "Zuordnung löschen",
        "button.reset": "Virtuelles Raster zurücksetzen",
        "button.copy": "LED-Liste kopieren",
        "button.preview": "Ermittelte LEDs aufleuchten lassen",
        "button.restore": "Vorschau beenden und Beleuchtung wiederherstellen",
        "result.heading": "Physische Kabel-LED-Nummern",
        "result.description": "Kommagetrennt in der gewählten virtuellen Kabelreihenfolge:",
        "status.points": "Eckpunkte: {count} / 4",
        "status.calculating": "Nächstgelegene physische LEDs werden berechnet ...",
        "status.mapped": "{virtual} virtuelle Positionen wurden {physical} physischen LEDs zugeordnet. Wiederholte physische IDs: {duplicates}.",
        "status.copied": "LED-Liste wurde kopiert.",
        "status.loaded": "Gespeicherte Zuordnung „{name}“ wurde geladen.",
        "status.saving": "MoonBoard-Zuordnung wird gespeichert ...",
        "status.saved": "MoonBoard-Zuordnung „{name}“ wurde gespeichert.",
        "status.deleting": "MoonBoard-Zuordnung wird gelöscht ...",
        "status.deleted": "Gespeicherte MoonBoard-Zuordnung wurde gelöscht. Der temporäre Modus ist aktiv.",
        "status.previewing": "Ermittelte physische LEDs werden eingeschaltet ...",
        "status.preview_active": "Die ermittelten physischen LEDs leuchten. Erfolgreiche Controller: {successful}; fehlgeschlagen: {failed}.",
        "status.restoring": "Vorherige Wandbeleuchtung wird wiederhergestellt ...",
        "status.restored": "Vorherige Wandbeleuchtung wurde wiederhergestellt.",
        "status.preview_error": "LED-Vorschau fehlgeschlagen: {message}",
        "status.error": "Die Zuordnung konnte nicht berechnet werden: {message}",
        "status.save_error": "Die Zuordnung konnte nicht gespeichert werden: {message}",
        "status.delete_error": "Die Zuordnung konnte nicht gelöscht werden: {message}",
        "alert.alternating_columns": "Für ein alternierendes Raster müssen mindestens 2 Spalten angegeben werden.",
        "alert.dimensions": "Reihen und Spalten müssen positive ganze Zahlen sein.",
        "alert.name": "Gib einen Namen für diese MoonBoard-Installation ein.",
        "alert.points": "Wähle zuerst alle vier MoonBoard-Eckpunkte aus.",
        "alert.delete_confirm": "Die ausgewählte MoonBoard-Zuordnung löschen?",
        "image.alt": "Kletterwand",
    },
}


def _script_json(value):
    """Serialize JSON without allowing user text to terminate a script tag."""
    return json.dumps(value, separators=(",", ":")).replace("</", "<\\/")


def return_virtual_mapping_html(
    wall,
    path_prefix="",
    saved_mappings=None,
    moonboard_setups=None,
):
    replacements = {
        "__WALL_ID__": json.dumps(wall["id"]),
        "__WALL_NAME__": escape(str(wall.get("name") or "")),
        "__WALL_IMAGE_WIDTH__": json.dumps(wall.get("image_width")),
        "__WALL_IMAGE_HEIGHT__": json.dumps(wall.get("image_height")),
        "__IMAGE_URL__": escape(str(wall.get("image_url") or ""), quote=True),
        "__CALCULATE_URL__": f"{path_prefix}/virtualmapping/calculate",
        "__PREVIEW_URL__": f"{path_prefix}/virtualmapping/preview",
        "__MAPPINGS_URL__": f"{path_prefix}/virtualmapping/mappings",
        "__SAVED_MAPPINGS__": _script_json(saved_mappings or []),
        "__MOONBOARD_SETUPS__": _script_json(moonboard_setups or {}),
        "__LANGUAGE_SWITCH__": language_switch_html(TRANSLATIONS),
    }
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title data-i18n="page.title">Virtual MoonBoard mapping</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: sans-serif; margin: 0; padding: 24px 18px 80px; background: #f4f4f9; color: #222; }
        main { width: min(1100px, 100%); margin: 0 auto; }
        h1 { margin-bottom: 6px; }
        .intro { margin-top: 0; color: #555; line-height: 1.5; }
        .panel, #mapping-form { margin: 22px 0; padding: 18px; border-radius: 9px; background: white; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .panel h2 { margin: 0 0 8px; }
        .panel .intro { margin-bottom: 16px; }
        .form-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; margin-bottom: 12px; }
        .form-row:last-child { margin-bottom: 0; }
        label { font-weight: 600; }
        input[type="number"], input[type="text"], select { min-width: 110px; padding: 8px 10px; font-size: 16px; border: 1px solid #aaa; border-radius: 5px; }
        #saved-mapping-select { min-width: min(390px, 100%); }
        #mapping-name { min-width: min(300px, 100%); }
        input[type="checkbox"] { width: 18px; height: 18px; vertical-align: middle; }
        .help { line-height: 1.5; }
        .help strong { display: block; }
        #image-container { position: relative; width: fit-content; max-width: 100%; cursor: crosshair; user-select: none; }
        #climbing-image { display: block; max-width: 100%; height: auto; }
        .corner-point, .virtual-point, .source-point { position: absolute; transform: translate(-50%, -50%); border-radius: 50%; pointer-events: none; }
        .corner-point { width: 15px; height: 15px; background: #d00000; border: 2px solid white; z-index: 4; }
        .source-point { width: 10px; height: 10px; background: #087fdb; border: 1px solid white; z-index: 2; }
        .virtual-point { display: flex; align-items: center; justify-content: center; min-width: 20px; height: 20px; padding: 0 3px; background: rgba(255, 139, 0, 0.88); border: 1px solid white; color: #111; font-size: 8px; font-weight: 700; z-index: 3; }
        #actions { display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 10px; }
        button { padding: 10px 15px; border: 0; border-radius: 5px; background: #007bff; color: white; font-size: 16px; cursor: pointer; }
        button:hover { background: #0056b3; }
        button:disabled { opacity: 0.55; cursor: not-allowed; }
        #reset-button { background: #666; }
        #reset-button:hover { background: #444; }
        #new-button { background: #666; }
        #new-button:hover { background: #444; }
        #delete-button { background: #a32222; }
        #delete-button:hover { background: #7f1818; }
        #save-button { background: #27823b; }
        #save-button:hover { background: #1c652c; }
        #status { min-height: 1.5em; margin: 8px 0 18px; font-weight: 600; }
        #result { padding: 18px; border-radius: 9px; background: white; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        #result h2 { margin-top: 0; }
        #physical-led-output { width: 100%; min-height: 130px; padding: 12px; resize: vertical; font: 15px/1.45 monospace; border: 1px solid #999; border-radius: 5px; }
        .result-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
        #preview-button { background: #d96d00; }
        #preview-button:hover { background: #ad5700; }
        #preview-button.is-active { background: #a32222; }
        #preview-button.is-active:hover { background: #7f1818; }
    </style>
</head>
<body>
    <main>
        <h1 data-i18n="page.heading">Virtual MoonBoard mapping</h1>
        <p><strong>__WALL_NAME__</strong></p>
        <p class="intro" data-i18n="page.description">Calculate a temporary LED list as before, or save named MoonBoard installations for later use.</p>

        <section class="panel" id="saved-mappings-panel">
            <h2 data-i18n="saved.heading">Saved MoonBoard installations</h2>
            <p class="intro" data-i18n="saved.description">Several Mini or Standard MoonBoards can be stored on the same CRUX wall, including more than one installation of the same setup.</p>
            <div class="form-row">
                <label for="saved-mapping-select" data-i18n="saved.select">Saved mapping:</label>
                <select id="saved-mapping-select"></select>
                <button id="new-button" type="button" data-i18n="button.new">New / temporary</button>
                <button id="delete-button" type="button" disabled data-i18n="button.delete">Delete mapping</button>
            </div>
            <div class="form-row">
                <label for="mapping-name" data-i18n="form.mapping_name">Installation name:</label>
                <input id="mapping-name" type="text" maxlength="100" data-i18n-placeholder="form.mapping_name_placeholder" placeholder="e.g. Mini left">
                <label for="board-type" data-i18n="form.board_type">MoonBoard:</label>
                <select id="board-type">
                    <option value="mini" data-i18n="form.board_mini">Mini MoonBoard</option>
                    <option value="standard" data-i18n="form.board_standard">Standard MoonBoard</option>
                </select>
                <label for="board-setup" data-i18n="form.setup">Setup:</label>
                <select id="board-setup"></select>
            </div>
        </section>

        <form id="mapping-form">
            <div class="form-row">
                <label for="rows" data-i18n="form.rows">Rows:</label>
                <input id="rows" type="number" min="1" step="1" value="12" required>
                <label for="columns" data-i18n="form.columns">Columns:</label>
                <input id="columns" type="number" min="1" step="1" value="11" required>
                <label for="alternating"><input id="alternating" type="checkbox"> <span data-i18n="form.alternating">Alternating grid</span></label>
            </div>
            <div class="form-row">
                <label for="alternating-start" data-i18n="form.top_row">Top row:</label>
                <select id="alternating-start" disabled>
                    <option value="0" data-i18n="form.not_offset">Not offset</option>
                    <option value="1" data-i18n="form.offset">Offset</option>
                </select>
                <label for="led-start-corner" data-i18n="form.led_zero">Virtual LED start:</label>
                <select id="led-start-corner">
                    <option value="top_left" data-i18n="form.top_left">Top left</option>
                    <option value="top_right" data-i18n="form.top_right">Top right</option>
                    <option value="bottom_left" selected data-i18n="form.bottom_left">Bottom left</option>
                    <option value="bottom_right" data-i18n="form.bottom_right">Bottom right</option>
                </select>
                <label for="led-direction" data-i18n="form.cable_path">Virtual cable path:</label>
                <select id="led-direction">
                    <option value="horizontal" data-i18n="form.horizontal">Horizontal (row by row)</option>
                    <option value="vertical" selected data-i18n="form.vertical">Vertical (column by column)</option>
                </select>
            </div>
        </form>

        <p class="help">
            <strong data-i18n="help.corners">Click four MoonBoard corner points in this order:</strong>
            <span data-i18n="help.corner_order">Top left, top right, bottom right, bottom left</span>
        </p>
        <p class="help" data-i18n="help.mapping">Calculate remains temporary and produces the same copyable list as before. Save mapping stores the selected board, setup, corners, CRUX hold IDs and physical LEDs in the bridge database.</p>

        <div id="image-container">
            <img id="climbing-image" src="__IMAGE_URL__" alt="Climbing wall" data-i18n-alt="image.alt">
        </div>

        <div id="actions">
            <button id="reset-button" type="button" data-i18n="button.reset">Reset virtual grid</button>
            <button id="calculate-button" type="button" disabled data-i18n="button.calculate">Calculate physical LED list</button>
            <button id="save-button" type="button" disabled data-i18n="button.save">Save mapping</button>
        </div>
        <div id="status" role="status" aria-live="polite"></div>

        <section id="result" hidden>
            <h2 data-i18n="result.heading">Physical cable LED numbers</h2>
            <p data-i18n="result.description">Comma-separated in the selected virtual cable order:</p>
            <textarea id="physical-led-output" readonly></textarea>
            <p class="help" data-i18n="help.preview">The preview lights the mapped physical cable LEDs orange. Stop it to restore the previous route or off state.</p>
            <div class="result-actions">
                <button id="copy-button" type="button" data-i18n="button.copy">Copy LED list</button>
                <button id="preview-button" type="button" data-i18n="button.preview">Light mapped LEDs</button>
            </div>
        </section>
    </main>
    __LANGUAGE_SWITCH__
    <script>
        const wallId = __WALL_ID__;
        const wallImageWidth = __WALL_IMAGE_WIDTH__;
        const wallImageHeight = __WALL_IMAGE_HEIGHT__;
        const moonboardSetups = __MOONBOARD_SETUPS__;
        const mappingsUrl = '__MAPPINGS_URL__';
        const previewUrl = '__PREVIEW_URL__';
        let savedMappings = __SAVED_MAPPINGS__;

        const form = document.getElementById('mapping-form');
        const savedMappingSelect = document.getElementById('saved-mapping-select');
        const mappingNameInput = document.getElementById('mapping-name');
        const boardTypeSelect = document.getElementById('board-type');
        const boardSetupSelect = document.getElementById('board-setup');
        const rowsInput = document.getElementById('rows');
        const columnsInput = document.getElementById('columns');
        const alternatingInput = document.getElementById('alternating');
        const alternatingStart = document.getElementById('alternating-start');
        const ledStartCorner = document.getElementById('led-start-corner');
        const ledDirection = document.getElementById('led-direction');
        const imageContainer = document.getElementById('image-container');
        const climbingImage = document.getElementById('climbing-image');
        const calculateButton = document.getElementById('calculate-button');
        const resetButton = document.getElementById('reset-button');
        const newButton = document.getElementById('new-button');
        const saveButton = document.getElementById('save-button');
        const deleteButton = document.getElementById('delete-button');
        const resultSection = document.getElementById('result');
        const output = document.getElementById('physical-led-output');
        const copyButton = document.getElementById('copy-button');
        const previewButton = document.getElementById('preview-button');
        const status = document.getElementById('status');

        let selectedMappingId = null;
        let points = [];
        let matches = [];
        let physicalIds = [];
        let previewActive = false;
        let previewRequestPending = false;
        let statusState = { key: 'status.points', replacements: { count: 0 }, error: false };

        function t(key, replacements = {}) { return window.cruxI18n.t(key, replacements); }
        function coordinateWidth() { return wallImageWidth || climbingImage.naturalWidth; }
        function coordinateHeight() { return wallImageHeight || climbingImage.naturalHeight; }
        function imageToDisplay(x, y) {
            const rect = climbingImage.getBoundingClientRect();
            return { x: x * rect.width / coordinateWidth(), y: y * rect.height / coordinateHeight() };
        }
        function displayToImage(x, y) {
            const rect = climbingImage.getBoundingClientRect();
            return { x: Math.round(x * coordinateWidth() / rect.width), y: Math.round(y * coordinateHeight() / rect.height) };
        }
        function setStatus(key, replacements = {}, error = false) {
            statusState = { key, replacements, error };
            renderStatus();
        }
        function renderStatus() {
            status.textContent = t(statusState.key, statusState.replacements);
            status.style.color = statusState.error ? '#b00020' : '#333';
        }
        function renderPreviewButton() {
            previewButton.textContent = t(previewActive ? 'button.restore' : 'button.preview');
            previewButton.classList.toggle('is-active', previewActive);
            previewButton.disabled = previewRequestPending || physicalIds.length === 0;
        }
        function renderPersistenceButtons() {
            saveButton.textContent = t(selectedMappingId ? 'button.update' : 'button.save');
            saveButton.disabled = points.length !== 4;
            deleteButton.disabled = !selectedMappingId;
        }
        function setupLabel(mapping) {
            return moonboardSetups[mapping.board_type]?.[mapping.setup]?.label || mapping.setup;
        }
        function renderSavedMappingSelect() {
            const selected = selectedMappingId || '';
            savedMappingSelect.replaceChildren();
            const temporary = document.createElement('option');
            temporary.value = '';
            temporary.textContent = t('saved.temporary');
            savedMappingSelect.appendChild(temporary);
            [...savedMappings]
                .sort((left, right) => left.name.localeCompare(right.name))
                .forEach((mapping) => {
                    const option = document.createElement('option');
                    option.value = mapping.id;
                    option.textContent = `${mapping.name} — ${setupLabel(mapping)}`;
                    savedMappingSelect.appendChild(option);
                });
            savedMappingSelect.value = selected;
            renderPersistenceButtons();
        }
        function renderBoardSetups(preferredSetup = null, applyDimensions = false) {
            const setups = moonboardSetups[boardTypeSelect.value] || {};
            boardSetupSelect.replaceChildren();
            Object.entries(setups).forEach(([setupId, setup]) => {
                const option = document.createElement('option');
                option.value = setupId;
                option.textContent = setup.label;
                boardSetupSelect.appendChild(option);
            });
            if (preferredSetup && setups[preferredSetup]) {
                boardSetupSelect.value = preferredSetup;
            }
            if (applyDimensions) applySetupDimensions();
        }
        function applySetupDimensions() {
            const setup = moonboardSetups[boardTypeSelect.value]?.[boardSetupSelect.value];
            if (!setup) return;
            rowsInput.value = setup.rows;
            columnsInput.value = setup.columns;
            alternatingInput.checked = false;
            alternatingStart.value = '0';
            alternatingStart.disabled = true;
            void clearResult();
        }
        function removeMappingMarkers() {
            imageContainer.querySelectorAll('.virtual-point, .source-point').forEach((element) => element.remove());
            matches = [];
        }
        async function clearResult() {
            if (previewActive) {
                const restored = await setPreview(false, true);
                if (!restored) return false;
            }
            removeMappingMarkers();
            physicalIds = [];
            output.value = '';
            resultSection.hidden = true;
            renderPreviewButton();
            setStatus('status.points', { count: points.length });
            return true;
        }
        function renderCorners() {
            imageContainer.querySelectorAll('.corner-point').forEach((element) => element.remove());
            points.forEach((point) => {
                const display = imageToDisplay(point.x, point.y);
                const marker = document.createElement('div');
                marker.className = 'corner-point';
                marker.style.left = `${display.x}px`;
                marker.style.top = `${display.y}px`;
                imageContainer.appendChild(marker);
            });
            calculateButton.disabled = points.length !== 4;
            renderPersistenceButtons();
        }
        function renderMatches() {
            imageContainer.querySelectorAll('.virtual-point, .source-point').forEach((element) => element.remove());
            const renderedSources = new Set();
            matches.forEach((match) => {
                const sourceKey = `${match.source_x}:${match.source_y}:${match.physical_led_ids.join('/')}`;
                if (!renderedSources.has(sourceKey)) {
                    renderedSources.add(sourceKey);
                    const sourceDisplay = imageToDisplay(match.source_x, match.source_y);
                    const source = document.createElement('div');
                    source.className = 'source-point';
                    source.style.left = `${sourceDisplay.x}px`;
                    source.style.top = `${sourceDisplay.y}px`;
                    const cruxHolds = (match.crux_hold_ids || []).join(', ') || '—';
                    source.title = `Wall LED ${match.logical_led_id} → ${match.physical_led_ids.join(', ')}; CRUX ${cruxHolds}`;
                    imageContainer.appendChild(source);
                }
                const virtualDisplay = imageToDisplay(match.virtual_x, match.virtual_y);
                const virtual = document.createElement('div');
                virtual.className = 'virtual-point';
                virtual.style.left = `${virtualDisplay.x}px`;
                virtual.style.top = `${virtualDisplay.y}px`;
                virtual.textContent = match.physical_led_ids.join('/');
                const moonboardPosition = match.moonboard_hold_label || `#${match.virtual_position_id}`;
                virtual.title = `${moonboardPosition}: ${match.physical_led_ids.join(', ')} (Wall LED ${match.logical_led_id})`;
                imageContainer.appendChild(virtual);
            });
        }
        function redraw() { renderCorners(); renderMatches(); }
        function integerValue(input) {
            const value = Number(input.value);
            return Number.isInteger(value) ? value : null;
        }
        function buildPayload() {
            return {
                wallid: wallId,
                p1x: points[0].x, p1y: points[0].y,
                p2x: points[1].x, p2y: points[1].y,
                p3x: points[2].x, p3y: points[2].y,
                p4x: points[3].x, p4y: points[3].y,
                r: integerValue(rowsInput),
                c: integerValue(columnsInput),
                alternating: alternatingInput.checked,
                alternating_start_column: Number(alternatingStart.value),
                led_start_corner: ledStartCorner.value,
                led_direction: ledDirection.value,
            };
        }
        function validateGrid() {
            if (points.length !== 4) {
                window.alert(t('alert.points'));
                return false;
            }
            const rows = integerValue(rowsInput);
            const columns = integerValue(columnsInput);
            if (!Number.isInteger(rows) || rows < 1 || !Number.isInteger(columns) || columns < 1) {
                window.alert(t('alert.dimensions'));
                return false;
            }
            if (alternatingInput.checked && columns < 2) {
                window.alert(t('alert.alternating_columns'));
                return false;
            }
            return true;
        }
        function showMappingResult(mapping) {
            matches = mapping.matches || [];
            physicalIds = mapping.physical_led_ids || [];
            output.value = physicalIds.join(', ');
            resultSection.hidden = false;
            renderMatches();
            renderPreviewButton();
        }
        function scaleSavedMapping(mapping) {
            const sourceWidth = mapping.coordinate_width || coordinateWidth();
            const sourceHeight = mapping.coordinate_height || coordinateHeight();
            const scaleX = coordinateWidth() / sourceWidth;
            const scaleY = coordinateHeight() / sourceHeight;
            return {
                points: (mapping.points || []).map((point) => ({
                    x: Math.round(point.x * scaleX),
                    y: Math.round(point.y * scaleY),
                })),
                matches: (mapping.matches || []).map((match) => ({
                    ...match,
                    virtual_x: Math.round(match.virtual_x * scaleX),
                    virtual_y: Math.round(match.virtual_y * scaleY),
                    source_x: Math.round(match.source_x * scaleX),
                    source_y: Math.round(match.source_y * scaleY),
                })),
            };
        }
        async function loadSavedMapping(mapping, statusKey = 'status.loaded') {
            if (!await clearResult()) return;
            selectedMappingId = mapping.id;
            savedMappingSelect.value = mapping.id;
            mappingNameInput.value = mapping.name;
            boardTypeSelect.value = mapping.board_type;
            renderBoardSetups(mapping.setup, false);
            const stored = mapping.mapping || {};
            rowsInput.value = stored.r;
            columnsInput.value = stored.c;
            alternatingInput.checked = Boolean(stored.alternating);
            alternatingStart.value = stored.alternating_start_column || 0;
            alternatingStart.disabled = !alternatingInput.checked;
            ledStartCorner.value = stored.led_start_corner || 'bottom_left';
            ledDirection.value = stored.led_direction || 'vertical';
            const scaled = scaleSavedMapping(stored);
            points = scaled.points;
            showMappingResult({
                matches: scaled.matches,
                physical_led_ids: stored.physical_led_ids || [],
            });
            renderCorners();
            renderSavedMappingSelect();
            setStatus(statusKey, { name: mapping.name });
        }
        async function newTemporaryMapping() {
            if (!await clearResult()) return;
            selectedMappingId = null;
            mappingNameInput.value = '';
            boardTypeSelect.value = 'mini';
            renderBoardSetups('mini_2020', false);
            rowsInput.value = 12;
            columnsInput.value = 11;
            alternatingInput.checked = false;
            alternatingStart.value = '0';
            alternatingStart.disabled = true;
            ledStartCorner.value = 'bottom_left';
            ledDirection.value = 'vertical';
            points = [];
            renderSavedMappingSelect();
            renderCorners();
            setStatus('status.points', { count: 0 });
        }
        async function setPreview(enabled, silent = false) {
            if (previewRequestPending) return false;
            const ids = [...physicalIds];
            previewRequestPending = true;
            renderPreviewButton();
            if (!silent) setStatus(enabled ? 'status.previewing' : 'status.restoring');
            try {
                const response = await fetch(previewUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ physical_led_ids: ids, enabled }),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
                previewActive = enabled;
                if (!silent) {
                    if (enabled) {
                        setStatus('status.preview_active', {
                            successful: data.controllers?.successful ?? 0,
                            failed: data.controllers?.failed ?? 0,
                        });
                    } else {
                        setStatus('status.restored');
                    }
                }
                return true;
            } catch (error) {
                setStatus('status.preview_error', { message: error.message }, true);
                return false;
            } finally {
                previewRequestPending = false;
                renderPreviewButton();
            }
        }

        imageContainer.addEventListener('click', (event) => {
            if (points.length >= 4) return;
            const rect = climbingImage.getBoundingClientRect();
            points.push(displayToImage(event.clientX - rect.left, event.clientY - rect.top));
            void clearResult();
            renderCorners();
        });
        imageContainer.addEventListener('contextmenu', (event) => {
            event.preventDefault();
            if (!points.length) return;
            points.pop();
            void clearResult();
            renderCorners();
        });
        form.addEventListener('change', () => { void clearResult(); });
        form.addEventListener('input', () => { void clearResult(); });
        alternatingInput.addEventListener('change', () => {
            alternatingStart.disabled = !alternatingInput.checked;
        });
        boardTypeSelect.addEventListener('change', () => {
            renderBoardSetups(null, true);
        });
        boardSetupSelect.addEventListener('change', applySetupDimensions);
        savedMappingSelect.addEventListener('change', () => {
            const mapping = savedMappings.find((item) => item.id === savedMappingSelect.value);
            if (mapping) void loadSavedMapping(mapping);
            else void newTemporaryMapping();
        });
        newButton.addEventListener('click', () => { void newTemporaryMapping(); });
        resetButton.addEventListener('click', () => {
            points = [];
            void clearResult();
            renderCorners();
        });
        calculateButton.addEventListener('click', async () => {
            if (!validateGrid()) return;
            if (previewActive && !await setPreview(false, true)) return;
            const payload = buildPayload();
            setStatus('status.calculating');
            calculateButton.disabled = true;
            try {
                const response = await fetch('__CALCULATE_URL__', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
                showMappingResult(data);
                const duplicates = physicalIds.length - new Set(physicalIds).size;
                setStatus('status.mapped', { virtual: matches.length, physical: physicalIds.length, duplicates });
            } catch (error) {
                await clearResult();
                setStatus('status.error', { message: error.message }, true);
            } finally {
                renderCorners();
            }
        });
        saveButton.addEventListener('click', async () => {
            if (!validateGrid()) return;
            const name = mappingNameInput.value.trim();
            if (!name) {
                window.alert(t('alert.name'));
                return;
            }
            if (previewActive && !await setPreview(false, true)) return;
            const payload = {
                ...buildPayload(),
                mapping_id: selectedMappingId,
                name,
                board_type: boardTypeSelect.value,
                setup: boardSetupSelect.value,
            };
            setStatus('status.saving');
            saveButton.disabled = true;
            try {
                const response = await fetch(mappingsUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
                const saved = data.mapping;
                const existingIndex = savedMappings.findIndex((item) => item.id === saved.id);
                if (existingIndex >= 0) savedMappings[existingIndex] = saved;
                else savedMappings.push(saved);
                await loadSavedMapping(saved, 'status.saved');
            } catch (error) {
                setStatus('status.save_error', { message: error.message }, true);
                renderPersistenceButtons();
            }
        });
        deleteButton.addEventListener('click', async () => {
            if (!selectedMappingId || !window.confirm(t('alert.delete_confirm'))) return;
            if (previewActive && !await setPreview(false, true)) return;
            const mappingId = selectedMappingId;
            setStatus('status.deleting');
            deleteButton.disabled = true;
            try {
                const response = await fetch(`${mappingsUrl}/${encodeURIComponent(mappingId)}?wallid=${encodeURIComponent(wallId)}`, {
                    method: 'DELETE',
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
                savedMappings = savedMappings.filter((item) => item.id !== mappingId);
                await newTemporaryMapping();
                setStatus('status.deleted');
            } catch (error) {
                setStatus('status.delete_error', { message: error.message }, true);
                renderPersistenceButtons();
            }
        });
        copyButton.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(output.value);
            } catch (error) {
                output.focus();
                output.select();
                document.execCommand('copy');
            }
            setStatus('status.copied');
        });
        previewButton.addEventListener('click', () => {
            void setPreview(!previewActive);
        });
        window.addEventListener('pagehide', () => {
            if (!previewActive || !navigator.sendBeacon) return;
            const body = new Blob([
                JSON.stringify({ physical_led_ids: physicalIds, enabled: false }),
            ], { type: 'application/json' });
            navigator.sendBeacon(previewUrl, body);
        });
        window.addEventListener('resize', redraw);
        if ('ResizeObserver' in window) new ResizeObserver(redraw).observe(climbingImage);
        window.addEventListener('crux-language-change', () => {
            renderSavedMappingSelect();
            renderStatus();
            renderPreviewButton();
            renderPersistenceButtons();
        });
        renderBoardSetups('mini_2020', true);
        renderSavedMappingSelect();
        if (climbingImage.complete && climbingImage.naturalWidth) redraw();
        else climbingImage.addEventListener('load', redraw, { once: true });
        renderPreviewButton();
        renderPersistenceButtons();
        renderStatus();
    </script>
</body>
</html>
"""
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    return html
