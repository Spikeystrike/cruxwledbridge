import json
from html import escape

from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Climbing wall – select points",
        "page.heading": "Climbing wall – select points",
        "tabs.add": "Add grid",
        "tabs.grid": "Grid {number}",
        "tabs.range": "LED {start}–{end}",
        "tabs.unconfigured": "not configured",
        "tabs.delete": "Delete grid",
        "tabs.delete_confirm": "Delete this grid? The change is applied when the mapping is saved.",
        "form.rows": "Rows:",
        "form.rows_placeholder": "Number of rows",
        "form.columns": "Columns:",
        "form.columns_placeholder": "Number of columns",
        "form.alternating": "Alternating grid",
        "form.top_row": "Top row:",
        "form.not_offset": "Not offset",
        "form.offset": "Offset",
        "form.led_zero": "LED start:",
        "form.cable_path": "Cable path:",
        "form.top_left": "Top left",
        "form.top_right": "Top right",
        "form.bottom_left": "Bottom left",
        "form.bottom_right": "Bottom right",
        "form.horizontal": "Horizontal (row by row)",
        "form.vertical": "Vertical (column by column)",
        "help.alternating": "For an alternating grid, Columns is the number of all possible horizontal positions. It can be even or odd; the positions used alternate from row to row.",
        "help.numbering": "The first grid starts at LED 0. Every following grid continues after the previous tab; drag the tabs to change that order.",
        "help.corners": "Click the 4 corner points in this order:",
        "help.corner_order": "Top left, top right, bottom right, bottom left",
        "help.selection": "After calculating, click grid points to disable or reactivate them. Then click",
        "help.save_selection": "Save all grids",
        "image.alt": "Climbing wall",
        "button.send": "Save all grids",
        "button.save": "Save all grids",
        "button.reset": "Reset grid",
        "status.points": "Points: {count} / 4",
        "status.grid": "Grid: {active} active, {excluded} disabled{suffix}",
        "status.unsaved": " – not saved yet",
        "grid.excluded_title": "Position is disabled. Click to activate it.",
        "grid.hold_title": "Hold ID: {holdId}\nLED ID: {ledId}",
        "grid.led_title": "LED ID: {ledId}. Click to disable.",
        "alert.alternating_columns": "Columns must be at least 2 for an alternating grid.",
        "alert.active_position": "At least one grid position must remain active.",
        "alert.incomplete_grid": "Please configure all four corners and valid dimensions for grid {number}.",
        "alert.saved": "Saved successfully.",
        "alert.send_error": "An error occurred while sending: {message}",
    },
    "de": {
        "page.title": "Kletterwand – Punkte auswählen",
        "page.heading": "Kletterwand – Punkte auswählen",
        "tabs.add": "Raster hinzufügen",
        "tabs.grid": "Raster {number}",
        "tabs.range": "LED {start}–{end}",
        "tabs.unconfigured": "nicht eingerichtet",
        "tabs.delete": "Raster löschen",
        "tabs.delete_confirm": "Dieses Raster löschen? Die Änderung wird beim Speichern der Zuordnung übernommen.",
        "form.rows": "Reihen:",
        "form.rows_placeholder": "Anzahl der Reihen",
        "form.columns": "Spalten:",
        "form.columns_placeholder": "Anzahl der Spalten",
        "form.alternating": "Alternierendes Raster",
        "form.top_row": "Oberste Reihe:",
        "form.not_offset": "Nicht eingerückt",
        "form.offset": "Eingerückt",
        "form.led_zero": "LED-Start:",
        "form.cable_path": "Kabelverlauf:",
        "form.top_left": "Oben links",
        "form.top_right": "Oben rechts",
        "form.bottom_left": "Unten links",
        "form.bottom_right": "Unten rechts",
        "form.horizontal": "Horizontal (zeilenweise)",
        "form.vertical": "Vertikal (spaltenweise)",
        "help.alternating": "Beim alternierenden Raster ist Spalten die Anzahl aller möglichen horizontalen Positionen. Die Zahl darf gerade oder ungerade sein; die verwendeten Positionen wechseln von Reihe zu Reihe.",
        "help.numbering": "Das erste Raster beginnt bei LED 0. Jedes weitere Raster setzt nach dem vorherigen Tab fort; ziehe die Tabs, um die Reihenfolge zu ändern.",
        "help.corners": "Bitte klicke die 4 Eckpunkte in dieser Reihenfolge an:",
        "help.corner_order": "Links oben, rechts oben, rechts unten, links unten",
        "help.selection": "Nach dem Berechnen kannst du Rasterpunkte anklicken, um sie abzuwählen oder wieder zu aktivieren. Klicke danach auf",
        "help.save_selection": "Alle Raster speichern",
        "image.alt": "Kletterwand",
        "button.send": "Alle Raster speichern",
        "button.save": "Alle Raster speichern",
        "button.reset": "Raster zurücksetzen",
        "status.points": "Punkte: {count} / 4",
        "status.grid": "Raster: {active} aktiv, {excluded} abgewählt{suffix}",
        "status.unsaved": " – noch nicht gespeichert",
        "grid.excluded_title": "Position ist abgewählt. Anklicken zum Aktivieren.",
        "grid.hold_title": "Griff-ID: {holdId}\nLED-ID: {ledId}",
        "grid.led_title": "LED-ID: {ledId}. Anklicken zum Abwählen.",
        "alert.alternating_columns": "Für ein alternierendes Raster müssen mindestens 2 Spalten angegeben werden.",
        "alert.active_position": "Mindestens eine Rasterposition muss aktiv bleiben.",
        "alert.incomplete_grid": "Bitte richte für Raster {number} alle vier Ecken und gültige Abmessungen ein.",
        "alert.saved": "Erfolgreich gespeichert.",
        "alert.send_error": "Beim Senden ist ein Fehler aufgetreten: {message}",
    },
}


def returnwallhtml(wall, path_prefix="", saved_creation=None):
    replacements = {
        "__SAVED_CREATION__": json.dumps(saved_creation or {}, separators=(",", ":")),
        "__WALL_IMAGE_WIDTH__": json.dumps(wall.get("image_width")),
        "__WALL_IMAGE_HEIGHT__": json.dumps(wall.get("image_height")),
        "__WALL_ID__": str(wall["id"]),
        "__PATH_PREFIX__": path_prefix,
        "__IMAGE_URL__": escape(str(wall["image_url"]), quote=True),
        "__LANGUAGE_SWITCH__": language_switch_html(TRANSLATIONS),
    }
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title data-i18n="page.title">Climbing wall – select points</title>
    <style>
        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; background: #f0f0f0; margin: 20px; }
        h1 { color: #333; }
        #grid-tabs { display: flex; align-items: stretch; gap: 8px; width: min(100%, 900px); overflow-x: auto; padding: 4px 2px 10px; }
        .grid-tab { display: flex; flex: 0 0 auto; align-items: stretch; border: 1px solid #aaa; border-radius: 7px; background: #ddd; overflow: hidden; }
        .grid-tab.dragging { opacity: 0.45; }
        .grid-tab.active { border-color: #2879c7; background: #fff; box-shadow: 0 0 0 2px rgba(40, 121, 199, 0.2); }
        .grid-tab-select, .grid-tab-delete, #add-grid-btn { border: 0; cursor: pointer; background: transparent; }
        .grid-tab-select { padding: 8px 10px; text-align: left; }
        .grid-tab-title, .grid-tab-range { display: block; white-space: nowrap; }
        .grid-tab-range { margin-top: 2px; color: #555; font-size: 0.78em; }
        .grid-tab-delete { padding: 0 9px; color: #8b2020; font-size: 1.2em; border-left: 1px solid #bbb; }
        #add-grid-btn { flex: 0 0 auto; padding: 8px 12px; border: 1px dashed #777; border-radius: 7px; background: #f8f8f8; font-weight: 600; }
        .form-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
        .form-row + .form-row { padding-top: 10px; border-top: 1px solid #ccc; }
        #image-container { position: relative; cursor: crosshair; user-select: none; max-width: 100%; }
        #climbing-image { display: block; max-width: 100%; height: auto; }
        .point { position: absolute; width: 12px; height: 12px; background: rgba(255, 0, 0, 0.8); border: 2px solid white; border-radius: 50%; transform: translate(-50%, -50%); pointer-events: none; }
        #action-buttons { display: flex; align-items: center; gap: 10px; margin-top: 20px; }
        #submit-btn, #reset-btn { display: none; padding: 12px 25px; font-size: 1.2em; cursor: pointer; color: white; border: none; border-radius: 5px; }
        #submit-btn { background: #4CAF50; } #submit-btn:hover { background: #45a049; }
        #reset-btn { background: #777; } #reset-btn:hover { background: #666; }
        #status { margin-top: 15px; font-size: 1.1em; color: #555; }
        .grid-point { position: absolute; width: 8px; height: 8px; background: rgba(0, 255, 0, 0.7); border: 1px solid white; border-radius: 50%; transform: translate(-50%, -50%); cursor: pointer; color: white; font-size: 8px; text-align: center; line-height: 8px; }
        .hold-point { background: rgba(255, 165, 0, 0.9); width: auto; height: 16px; min-width: 16px; padding: 0 4px; border-radius: 8px; line-height: 16px; }
        .grid-point.excluded-point { width: 12px; height: 12px; padding: 0; background: rgba(90, 90, 90, 0.35); border: 2px solid rgba(255, 255, 255, 0.9); line-height: 12px; opacity: 0.8; }
    </style>
</head>
<body>
    <h1 data-i18n="page.heading">Climbing wall – select points</h1>
    <div id="grid-tabs" role="tablist" aria-label="Grids"></div>
    <div>
        <div class="form-row">
            <label for="rows" data-i18n="form.rows">Rows:</label>
            <input type="number" id="rows" placeholder="Number of rows" data-i18n-placeholder="form.rows_placeholder" min="1">
            <label for="columns" data-i18n="form.columns">Columns:</label>
            <input type="number" id="columns" placeholder="Number of columns" data-i18n-placeholder="form.columns_placeholder" min="1">
        </div>
        <div class="form-row">
            <label for="alternating"><input type="checkbox" id="alternating"><span data-i18n="form.alternating">Alternating grid</span></label>
            <label for="alternating-start" data-i18n="form.top_row">Top row:</label>
            <select id="alternating-start" disabled>
                <option value="0" data-i18n="form.not_offset">Not offset</option>
                <option value="1" data-i18n="form.offset">Offset</option>
            </select>
        </div>
        <div class="form-row">
            <label for="led-start-corner" data-i18n="form.led_zero">LED start:</label>
            <select id="led-start-corner">
                <option value="top_left" data-i18n="form.top_left">Top left</option>
                <option value="top_right" data-i18n="form.top_right">Top right</option>
                <option value="bottom_left" data-i18n="form.bottom_left" selected>Bottom left</option>
                <option value="bottom_right" data-i18n="form.bottom_right">Bottom right</option>
            </select>
            <label for="led-direction" data-i18n="form.cable_path">Cable path:</label>
            <select id="led-direction">
                <option value="horizontal" data-i18n="form.horizontal">Horizontal (row by row)</option>
                <option value="vertical" data-i18n="form.vertical" selected>Vertical (column by column)</option>
            </select>
        </div>
    </div>
    <p data-i18n="help.alternating">For an alternating grid, Columns is the number of all possible horizontal positions.</p>
    <p data-i18n="help.numbering">The first grid starts at LED 0. Every following grid continues after the previous tab; drag the tabs to change that order.</p>
    <p><span data-i18n="help.corners">Click the 4 corner points in this order:</span> <b data-i18n="help.corner_order">Top left, top right, bottom right, bottom left</b>.</p>
    <p><span data-i18n="help.selection">After calculating, click grid points to disable or reactivate them. Then click</span> <b data-i18n="help.save_selection">Save all grids</b>.</p>
    <div id="image-container"><img id="climbing-image" src="__IMAGE_URL__" alt="Climbing wall" data-i18n-alt="image.alt"></div>
    <div id="status">Points: 0 / 4</div>
    <div id="action-buttons">
        <button id="reset-btn" type="button" data-i18n="button.reset">Reset grid</button>
        <button id="submit-btn" type="button" data-i18n="button.send">Save all grids</button>
    </div>
    __LANGUAGE_SWITCH__
    <script>
        const imageContainer = document.getElementById('image-container');
        const climbingImage = document.getElementById('climbing-image');
        const submitBtn = document.getElementById('submit-btn');
        const resetBtn = document.getElementById('reset-btn');
        const statusDiv = document.getElementById('status');
        const tabsContainer = document.getElementById('grid-tabs');
        const alternatingCheckbox = document.getElementById('alternating');
        const alternatingStart = document.getElementById('alternating-start');
        const rows = document.getElementById('rows');
        const columns = document.getElementById('columns');
        const ledStartCornerSelect = document.getElementById('led-start-corner');
        const ledDirectionSelect = document.getElementById('led-direction');
        const savedCreation = __SAVED_CREATION__;
        const wallImageWidth = __WALL_IMAGE_WIDTH__;
        const wallImageHeight = __WALL_IMAGE_HEIGHT__;
        let renderedHolds2led = savedCreation.holds2led || {};
        let activeGridIndex = 0;
        let activeGridLoaded = false;
        let savedCreationInitialized = false;
        let points = [];
        let renderedPositions = null;
        let positionLedIds = {};
        let excludedPositionIds = new Set();
        let selectionDirty = false;
        let lastGridSettings = null;

        function t(key, replacements = {}) { return window.cruxI18n.t(key, replacements); }
        function createEmptyGrid() {
            return { id: `grid-${Date.now()}-${Math.random().toString(16).slice(2)}`, points: [], positions: null, position_led_ids: {}, excluded_position_ids: [], r: null, c: null, alternating: false, alternating_start_column: 0, led_start_corner: 'bottom_left', led_direction: 'vertical', selection_dirty: false, last_grid_settings: null };
        }
        function normalizeGrid(grid, index) {
            return { ...createEmptyGrid(), ...grid, id: grid.id || `grid-${index + 1}`, points: grid.points || [], positions: grid.positions || null, position_led_ids: grid.position_led_ids || {}, excluded_position_ids: grid.excluded_position_ids || [] };
        }
        const savedGrids = Array.isArray(savedCreation.grids) && savedCreation.grids.length ? savedCreation.grids : [savedCreation];
        let grids = savedGrids.map(normalizeGrid);

        function coordinateWidth() { return wallImageWidth || climbingImage.naturalWidth; }
        function coordinateHeight() { return wallImageHeight || climbingImage.naturalHeight; }
        function imageToDisplay(point) {
            const rect = climbingImage.getBoundingClientRect();
            return { x: point.x * rect.width / coordinateWidth(), y: point.y * rect.height / coordinateHeight() };
        }
        function displayToImage(x, y) {
            const rect = climbingImage.getBoundingClientRect();
            return { x: Math.round(x * coordinateWidth() / rect.width), y: Math.round(y * coordinateHeight() / rect.height) };
        }
        function normalizeSavedCreationCoordinates() {
            const sourceWidth = savedCreation.coordinate_space === 'wall_image' ? (savedCreation.coordinate_width || wallImageWidth) : (savedCreation.coordinate_width || climbingImage.naturalWidth);
            const sourceHeight = savedCreation.coordinate_space === 'wall_image' ? (savedCreation.coordinate_height || wallImageHeight) : (savedCreation.coordinate_height || climbingImage.naturalHeight);
            const targetWidth = coordinateWidth();
            const targetHeight = coordinateHeight();
            if (!sourceWidth || !sourceHeight || !targetWidth || !targetHeight) return;
            const scaleX = targetWidth / sourceWidth;
            const scaleY = targetHeight / sourceHeight;
            grids.forEach((grid) => {
                grid.points = grid.points.map((point) => ({ x: Math.round(point.x * scaleX), y: Math.round(point.y * scaleY) }));
                if (grid.positions) grid.positions = Object.fromEntries(Object.entries(grid.positions).map(([id, point]) => [id, [Math.round(point[0] * scaleX), Math.round(point[1] * scaleY)]]));
            });
            savedCreation.coordinate_space = 'wall_image';
            savedCreation.coordinate_width = targetWidth;
            savedCreation.coordinate_height = targetHeight;
        }

        function numericValue(input) { const value = parseInt(input.value); return Number.isNaN(value) ? null : value; }
        function gridSettingsFor(grid) {
            return JSON.stringify({ points: grid.points, r: grid.r, c: grid.c, alternating: Boolean(grid.alternating), alternatingStartColumn: Number(grid.alternating_start_column || 0), ledStartCorner: grid.led_start_corner || 'bottom_left', ledDirection: grid.led_direction || 'vertical' });
        }
        function captureActiveGrid() {
            if (!activeGridLoaded) return;
            const grid = grids[activeGridIndex];
            grid.points = points.map((point) => ({ ...point }));
            grid.positions = renderedPositions;
            grid.position_led_ids = positionLedIds;
            grid.excluded_position_ids = Array.from(excludedPositionIds);
            grid.r = numericValue(rows);
            grid.c = numericValue(columns);
            grid.alternating = alternatingCheckbox.checked;
            grid.alternating_start_column = numericValue(alternatingStart) ?? 0;
            grid.led_start_corner = ledStartCornerSelect.value;
            grid.led_direction = ledDirectionSelect.value;
            grid.selection_dirty = selectionDirty;
            grid.last_grid_settings = lastGridSettings;
        }
        function renumberGrids() {
            let offset = 0;
            grids.forEach((grid) => {
                if (!grid.positions) { grid.position_led_ids = {}; delete grid.led_start; delete grid.led_end; return; }
                const excluded = new Set((grid.excluded_position_ids || []).map(Number));
                const activeIds = Object.keys(grid.positions).map(Number).filter((id) => !excluded.has(id)).sort((a, b) => a - b);
                grid.position_led_ids = Object.fromEntries(activeIds.map((id, localId) => [id, offset + localId]));
                grid.led_start = offset;
                grid.led_end = offset + activeIds.length - 1;
                offset += activeIds.length;
            });
        }
        function rangeLabel(grid) {
            if (!grid.positions || grid.led_end < grid.led_start) return t('tabs.unconfigured');
            return t('tabs.range', { start: grid.led_start, end: grid.led_end });
        }
        function moveGrid(fromIndex, toIndex) {
            if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
            captureActiveGrid();
            const activeId = grids[activeGridIndex].id;
            const [moved] = grids.splice(fromIndex, 1);
            grids.splice(toIndex, 0, moved);
            activeGridIndex = grids.findIndex((grid) => grid.id === activeId);
            renumberGrids();
            activeGridLoaded = false;
            loadGrid(activeGridIndex);
        }
        function renderTabs() {
            tabsContainer.replaceChildren();
            grids.forEach((grid, index) => {
                const tab = document.createElement('div');
                tab.className = `grid-tab${index === activeGridIndex ? ' active' : ''}`;
                tab.draggable = true;
                tab.addEventListener('dragstart', (event) => { tab.classList.add('dragging'); event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('text/plain', String(index)); });
                tab.addEventListener('dragend', () => tab.classList.remove('dragging'));
                tab.addEventListener('dragover', (event) => event.preventDefault());
                tab.addEventListener('drop', (event) => { event.preventDefault(); moveGrid(Number(event.dataTransfer.getData('text/plain')), index); });
                const select = document.createElement('button');
                select.type = 'button';
                select.className = 'grid-tab-select';
                select.setAttribute('role', 'tab');
                select.setAttribute('aria-selected', index === activeGridIndex ? 'true' : 'false');
                select.innerHTML = `<span class="grid-tab-title">${t('tabs.grid', { number: index + 1 })}</span><span class="grid-tab-range">${rangeLabel(grid)}</span>`;
                select.addEventListener('click', () => loadGrid(index));
                select.addEventListener('keydown', (event) => {
                    if (event.altKey && event.key === 'ArrowLeft' && index > 0) moveGrid(index, index - 1);
                    if (event.altKey && event.key === 'ArrowRight' && index < grids.length - 1) moveGrid(index, index + 1);
                });
                tab.appendChild(select);
                if (grids.length > 1) {
                    const remove = document.createElement('button');
                    remove.type = 'button'; remove.className = 'grid-tab-delete'; remove.textContent = '×';
                    remove.title = t('tabs.delete'); remove.setAttribute('aria-label', t('tabs.delete'));
                    remove.addEventListener('click', () => {
                        if (!window.confirm(t('tabs.delete_confirm'))) return;
                        captureActiveGrid();
                        const activeId = grids[activeGridIndex].id;
                        grids.splice(index, 1);
                        const fallbackIndex = Math.min(index, grids.length - 1);
                        activeGridIndex = grids.findIndex((item) => item.id === activeId);
                        if (activeGridIndex < 0) activeGridIndex = fallbackIndex;
                        renumberGrids(); activeGridLoaded = false; loadGrid(activeGridIndex);
                    });
                    tab.appendChild(remove);
                }
                tabsContainer.appendChild(tab);
            });
            const add = document.createElement('button');
            add.type = 'button'; add.id = 'add-grid-btn'; add.textContent = `+ ${t('tabs.add')}`;
            add.addEventListener('click', () => { captureActiveGrid(); grids.push(createEmptyGrid()); renumberGrids(); activeGridLoaded = false; loadGrid(grids.length - 1); });
            tabsContainer.appendChild(add);
        }
        function loadGrid(index) {
            captureActiveGrid();
            activeGridIndex = index;
            const grid = grids[index];
            points = (grid.points || []).map((point) => ({ ...point }));
            renderedPositions = grid.positions || null;
            positionLedIds = grid.position_led_ids || {};
            excludedPositionIds = new Set((grid.excluded_position_ids || []).map(Number));
            selectionDirty = Boolean(grid.selection_dirty);
            rows.value = grid.r ?? ''; columns.value = grid.c ?? '';
            alternatingCheckbox.checked = Boolean(grid.alternating);
            alternatingStart.value = grid.alternating_start_column ?? 0;
            alternatingStart.disabled = !alternatingCheckbox.checked;
            ledStartCornerSelect.value = grid.led_start_corner || 'bottom_left';
            ledDirectionSelect.value = grid.led_direction || 'vertical';
            lastGridSettings = grid.last_grid_settings;
            if (!lastGridSettings && points.length === 4 && renderedPositions) lastGridSettings = gridSettingsFor(grid);
            activeGridLoaded = true;
            renderTabs(); updateSubmitButtonLabel(); updateUI(); renderGrid(); updateGridStatus();
        }
        function updateSubmitButtonLabel() { submitBtn.textContent = t('button.save'); }
        function renderGrid() {
            document.querySelectorAll('.grid-point').forEach((point) => point.remove());
            if (!renderedPositions) return;
            const led2holds = {};
            for (const holdId in renderedHolds2led) { const ledId = renderedHolds2led[holdId]; if (!led2holds[ledId]) led2holds[ledId] = holdId; }
            for (const positionIdText in renderedPositions) {
                const [x, y] = renderedPositions[positionIdText];
                const displayPoint = imageToDisplay({ x, y });
                const positionId = Number(positionIdText);
                const ledId = positionLedIds[positionIdText];
                const element = document.createElement('div');
                const excluded = excludedPositionIds.has(positionId);
                const classes = ['grid-point'];
                element.style.left = `${displayPoint.x}px`; element.style.top = `${displayPoint.y}px`; element.dataset.positionId = positionIdText;
                if (excluded) { classes.push('excluded-point'); element.title = t('grid.excluded_title'); }
                else if (led2holds[ledId]) { classes.push('hold-point'); element.title = t('grid.hold_title', { holdId: led2holds[ledId], ledId }); element.textContent = led2holds[ledId].substring(0, 4); }
                else element.title = t('grid.led_title', { ledId });
                element.className = classes.join(' ');
                element.addEventListener('click', (event) => {
                    event.stopPropagation();
                    if (excludedPositionIds.has(positionId)) excludedPositionIds.delete(positionId); else excludedPositionIds.add(positionId);
                    selectionDirty = true; captureActiveGrid(); renumberGrids(); positionLedIds = grids[activeGridIndex].position_led_ids;
                    renderTabs(); renderGrid(); updateGridStatus();
                });
                imageContainer.appendChild(element);
            }
        }
        function updateGridStatus() {
            if (!renderedPositions) return;
            const total = Object.keys(renderedPositions).length;
            statusDiv.textContent = t('status.grid', { active: total - excludedPositionIds.size, excluded: excludedPositionIds.size, suffix: selectionDirty ? t('status.unsaved') : '' });
        }
        function updateUI() {
            document.querySelectorAll('.point').forEach((point) => point.remove());
            points.forEach((point) => { const displayPoint = imageToDisplay(point); const element = document.createElement('div'); element.className = 'point'; element.style.left = `${displayPoint.x}px`; element.style.top = `${displayPoint.y}px`; imageContainer.appendChild(element); });
            statusDiv.textContent = t('status.points', { count: points.length });
            submitBtn.style.display = points.length === 4 ? 'block' : 'none';
            resetBtn.style.display = (points.length > 0 || renderedPositions) ? 'block' : 'none';
        }

        alternatingCheckbox.addEventListener('change', () => { alternatingStart.disabled = !alternatingCheckbox.checked; });
        resetBtn.addEventListener('click', () => {
            points = []; renderedPositions = null; positionLedIds = {}; excludedPositionIds.clear(); selectionDirty = true; lastGridSettings = null;
            captureActiveGrid(); renumberGrids(); renderTabs(); updateUI(); renderGrid();
        });
        imageContainer.addEventListener('click', (event) => {
            if (points.length >= 4) return;
            const rect = climbingImage.getBoundingClientRect();
            points.push(displayToImage(event.clientX - rect.left, event.clientY - rect.top)); selectionDirty = true; updateUI();
        });
        imageContainer.addEventListener('contextmenu', (event) => { event.preventDefault(); if (points.length > 0) { points.pop(); selectionDirty = true; updateUI(); } });
        function redraw() { updateUI(); renderGrid(); updateGridStatus(); }
        window.addEventListener('resize', redraw);
        if ('ResizeObserver' in window) new ResizeObserver(() => { if (savedCreationInitialized) redraw(); }).observe(climbingImage);
        window.addEventListener('crux-language-change', () => { renderTabs(); updateSubmitButtonLabel(); redraw(); });

        submitBtn.addEventListener('click', async () => {
            captureActiveGrid();
            for (let index = 0; index < grids.length; index += 1) {
                const grid = grids[index];
                if (grid.points.length !== 4 || !Number.isInteger(grid.r) || grid.r < 1 || !Number.isInteger(grid.c) || grid.c < 1) { alert(t('alert.incomplete_grid', { number: index + 1 })); return; }
                if (grid.alternating && grid.c < 2) { alert(t('alert.alternating_columns')); return; }
                const settings = gridSettingsFor(grid);
                if (grid.last_grid_settings && settings !== grid.last_grid_settings) grid.excluded_position_ids = [];
                if (grid.positions && grid.excluded_position_ids.length === Object.keys(grid.positions).length) { alert(t('alert.active_position')); return; }
            }
            const activeId = grids[activeGridIndex].id;
            const payload = {
                wallid: __WALL_ID__,
                grids: grids.map((grid) => ({
                    id: grid.id,
                    p1x: grid.points[0].x, p1y: grid.points[0].y, p2x: grid.points[1].x, p2y: grid.points[1].y,
                    p3x: grid.points[2].x, p3y: grid.points[2].y, p4x: grid.points[3].x, p4y: grid.points[3].y,
                    r: grid.r, c: grid.c, alternating: Boolean(grid.alternating), alternating_start_column: Number(grid.alternating_start_column || 0),
                    led_start_corner: grid.led_start_corner, led_direction: grid.led_direction, excluded_position_ids: grid.excluded_position_ids,
                })),
            };
            try {
                const response = await fetch('__PATH_PREFIX__/defineholds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const result = await response.json();
                if (!response.ok) throw new Error(result.detail || result.message || `HTTP ${response.status}`);
                renderedHolds2led = result.holds2led || {};
                grids = (result.grids || []).map((grid, index) => { const normalized = normalizeGrid(grid, index); normalized.last_grid_settings = gridSettingsFor(normalized); normalized.selection_dirty = false; return normalized; });
                renumberGrids();
                activeGridIndex = Math.max(0, grids.findIndex((grid) => grid.id === activeId));
                activeGridLoaded = false; loadGrid(activeGridIndex); alert(t('alert.saved'));
            } catch (error) {
                console.error('Could not save wall mapping:', error);
                alert(t('alert.send_error', { message: error.message }));
            }
        });
        function initializeSavedCreation() {
            normalizeSavedCreationCoordinates(); renumberGrids(); activeGridLoaded = false; loadGrid(0); savedCreationInitialized = true;
        }
        if (climbingImage.complete && climbingImage.naturalWidth) initializeSavedCreation();
        else climbingImage.addEventListener('load', initializeSavedCreation, { once: true });
    </script>
</body>
</html>
"""
    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, value)
    return html_content
