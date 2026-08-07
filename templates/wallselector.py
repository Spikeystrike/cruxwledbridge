import json

from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Climbing wall – select points",
        "page.heading": "Climbing wall – select points",
        "form.rows": "Rows:",
        "form.rows_placeholder": "Number of rows",
        "form.columns": "Columns:",
        "form.columns_placeholder": "Number of columns",
        "form.alternating": "Alternating grid",
        "form.top_row": "Top row:",
        "form.not_offset": "Not offset",
        "form.offset": "Offset",
        "form.cable_path": "Cable path:",
        "form.top_left": "Top left",
        "form.top_right": "Top right",
        "form.bottom_left": "Bottom left",
        "form.bottom_right": "Bottom right",
        "form.horizontal": "Horizontal (row by row)",
        "form.vertical": "Vertical (column by column)",
        "help.alternating": "For an alternating grid, Columns is the number of all possible horizontal positions. It can be even or odd; the positions used alternate from row to row.",
        "help.numbering": "LED numbering starts with LED 0 in the selected corner and follows the cable in a horizontal or vertical snake pattern.",
        "help.corners": "Click the 4 corner points in this order:",
        "help.corner_order": "Top left, top right, bottom right, bottom left",
        "help.selection": "After calculating, click grid points to disable or reactivate them. Then click",
        "help.save_selection": "Save selection",
        "image.alt": "Climbing wall",
        "button.send": "Send coordinates",
        "button.save": "Save selection",
        "button.reset": "Reset",
        "status.points": "Points: {count} / 4",
        "status.grid": "Grid: {active} active, {excluded} disabled{suffix}",
        "status.unsaved": " – not saved yet",
        "grid.excluded_title": "Position is disabled. Click to activate it.",
        "grid.hold_title": "Hold ID: {holdId}\nLED ID: {ledId}",
        "grid.led_title": "LED ID: {ledId}. Click to disable.",
        "alert.four_points": "Please select exactly 4 points.",
        "alert.valid_grid": "Please enter valid values for Rows and Columns.",
        "alert.alternating_columns": "Columns must be at least 2 for an alternating grid.",
        "alert.active_position": "At least one grid position must remain active.",
        "alert.saved": "Saved successfully.",
        "alert.send_error": "An error occurred while sending: {message}",
    },
    "de": {
        "page.title": "Kletterwand – Punkte auswählen",
        "page.heading": "Kletterwand – Punkte auswählen",
        "form.rows": "Reihen:",
        "form.rows_placeholder": "Anzahl der Reihen",
        "form.columns": "Spalten:",
        "form.columns_placeholder": "Anzahl der Spalten",
        "form.alternating": "Alternierendes Raster",
        "form.top_row": "Oberste Reihe:",
        "form.not_offset": "Nicht eingerückt",
        "form.offset": "Eingerückt",
        "form.cable_path": "Kabelverlauf:",
        "form.top_left": "Oben links",
        "form.top_right": "Oben rechts",
        "form.bottom_left": "Unten links",
        "form.bottom_right": "Unten rechts",
        "form.horizontal": "Horizontal (zeilenweise)",
        "form.vertical": "Vertikal (spaltenweise)",
        "help.alternating": "Beim alternierenden Raster ist Spalten die Anzahl aller möglichen horizontalen Positionen. Die Zahl darf gerade oder ungerade sein; die verwendeten Positionen wechseln von Reihe zu Reihe.",
        "help.numbering": "Die LED-Nummerierung beginnt bei LED 0 in der gewählten Ecke und folgt dem Kabel schlangenförmig horizontal oder vertikal.",
        "help.corners": "Bitte klicke die 4 Eckpunkte in dieser Reihenfolge an:",
        "help.corner_order": "Links oben, rechts oben, rechts unten, links unten",
        "help.selection": "Nach dem Berechnen kannst du Rasterpunkte anklicken, um sie abzuwählen oder wieder zu aktivieren. Klicke danach auf",
        "help.save_selection": "Auswahl speichern",
        "image.alt": "Kletterwand",
        "button.send": "Koordinaten senden",
        "button.save": "Auswahl speichern",
        "button.reset": "Zurücksetzen",
        "status.points": "Punkte: {count} / 4",
        "status.grid": "Raster: {active} aktiv, {excluded} abgewählt{suffix}",
        "status.unsaved": " – noch nicht gespeichert",
        "grid.excluded_title": "Position ist abgewählt. Anklicken zum Aktivieren.",
        "grid.hold_title": "Griff-ID: {holdId}\nLED-ID: {ledId}",
        "grid.led_title": "LED-ID: {ledId}. Anklicken zum Abwählen.",
        "alert.four_points": "Bitte wähle genau 4 Punkte aus.",
        "alert.valid_grid": "Bitte gib gültige Werte für Reihen und Spalten ein.",
        "alert.alternating_columns": "Für ein alternierendes Raster müssen mindestens 2 Spalten angegeben werden.",
        "alert.active_position": "Mindestens eine Rasterposition muss aktiv bleiben.",
        "alert.saved": "Erfolgreich gespeichert.",
        "alert.send_error": "Beim Senden ist ein Fehler aufgetreten: {message}",
    },
}


def returnwallhtml(wall, path_prefix="", saved_creation=None):
    saved_creation_json = json.dumps(saved_creation or {}, separators=(",", ":"))
    wall_image_width_json = json.dumps(wall.get("image_width"))
    wall_image_height_json = json.dumps(wall.get("image_height"))
    language_switch = language_switch_html(TRANSLATIONS)
    html_content = f"""
        
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title data-i18n="page.title">Climbing wall – select points</title>
            <style>
                /* Gleiche CSS wie in test.html */
                body {{
                    font-family: sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background-color: #f0f0f0;
                    margin: 20px;
                }}
                h1 {{
                    color: #333;
                }}
                .form-row {{
                    display: flex;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 8px;
                    margin-bottom: 10px;
                }}
                .form-row + .form-row {{
                    padding-top: 10px;
                    border-top: 1px solid #ccc;
                }}
                #image-container {{
                    position: relative;
                    cursor: crosshair;
                    -webkit-user-drag: none;
                    user-select: none;
                    -moz-user-select: none;
                    -webkit-user-select: none;
                    -ms-user-select: none;
                    max-width: 100%;
                }}
                /* Restlicher CSS-Code für Punkte und Buttons */
                #climbing-image {{
                    display: block;
                    max-width: 100%;
                    height: auto;
                }}
                .point {{
                    position: absolute;
                    width: 12px;
                    height: 12px;
                    background-color: rgba(255, 0, 0, 0.8);
                    border: 2px solid white;
                    border-radius: 50%;
                    transform: translate(-50%, -50%);
                    pointer-events: none;
                }}
                #action-buttons {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-top: 20px;
                }}
                #submit-btn, #reset-btn {{
                    display: none;
                    padding: 12px 25px;
                    font-size: 1.2em;
                    cursor: pointer;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    transition: background-color 0.3s;
                }}
                #submit-btn {{
                    background-color: #4CAF50;
                }}
                #submit-btn:hover {{
                    background-color: #45a049;
                }}
                #reset-btn {{
                    background-color: #777;
                }}
                #reset-btn:hover {{
                    background-color: #666;
                }}
                #status {{
                    margin-top: 15px;
                    font-size: 1.1em;
                    color: #555;
                }}
                .grid-point {{
                    position: absolute;
                    width: 8px;
                    height: 8px;
                    background-color: rgba(0, 255, 0, 0.7); /* Green for grid points */
                    border: 1px solid white;
                    border-radius: 50%;
                    transform: translate(-50%, -50%);
                    cursor: pointer;
                    color: white; font-size: 8px; text-align: center; line-height: 8px;
                }}
                .hold-point {{
                    background-color: rgba(255, 165, 0, 0.9); /* Orange for mapped holds */
                    /* Make the point larger to fit text */
                    width: auto;
                    height: 16px;
                    min-width: 16px;
                    padding: 0 4px;
                    border-radius: 8px;
                    /* Style for the text inside */
                    line-height: 16px;
                }}
                .grid-point.excluded-point {{
                    width: 12px;
                    height: 12px;
                    padding: 0;
                    background-color: rgba(90, 90, 90, 0.35);
                    border: 2px solid rgba(255, 255, 255, 0.9);
                    line-height: 12px;
                    opacity: 0.8;
                }}
            </style>
        </head>
        <body>
            <h1 data-i18n="page.heading">Climbing wall – select points</h1>
             <div>
                <div class="form-row">
                    <label for="rows" data-i18n="form.rows">Rows:</label>
                    <input type="number" id="rows" name="rows" placeholder="Number of rows" data-i18n-placeholder="form.rows_placeholder" min="1">
                    <label for="columns" data-i18n="form.columns">Columns:</label>
                    <input type="number" id="columns" name="columns" placeholder="Number of columns" data-i18n-placeholder="form.columns_placeholder" min="1">
                </div>
                <div class="form-row">
                    <label for="alternating">
                        <input type="checkbox" id="alternating" name="alternating">
                        <span data-i18n="form.alternating">Alternating grid</span>
                    </label>
                </div>
                <div class="form-row">
                    <label for="alternating-start" data-i18n="form.top_row">Top row:</label>
                    <select id="alternating-start" name="alternating-start" disabled>
                        <option value="0" data-i18n="form.not_offset">Not offset</option>
                        <option value="1" data-i18n="form.offset">Offset</option>
                    </select>
                </div>
                <div class="form-row">
                    <label for="led-start-corner">LED 0:</label>
                    <select id="led-start-corner" name="led-start-corner">
                        <option value="top_left" data-i18n="form.top_left">Top left</option>
                        <option value="top_right" data-i18n="form.top_right">Top right</option>
                        <option value="bottom_left" data-i18n="form.bottom_left" selected>Bottom left</option>
                        <option value="bottom_right" data-i18n="form.bottom_right">Bottom right</option>
                    </select>
                    <label for="led-direction" data-i18n="form.cable_path">Cable path:</label>
                    <select id="led-direction" name="led-direction">
                        <option value="horizontal" data-i18n="form.horizontal">Horizontal (row by row)</option>
                        <option value="vertical" data-i18n="form.vertical" selected>Vertical (column by column)</option>
                    </select>
                </div>
            </div>
            <p data-i18n="help.alternating">For an alternating grid, Columns is the number of all possible horizontal positions. It can be even or odd; the positions used alternate from row to row.</p>
            <p data-i18n="help.numbering">LED numbering starts with LED 0 in the selected corner and follows the cable in a horizontal or vertical snake pattern.</p>
            <p><span data-i18n="help.corners">Click the 4 corner points in this order:</span> <b data-i18n="help.corner_order">Top left, top right, bottom right, bottom left</b>.</p>
            <p><span data-i18n="help.selection">After calculating, click grid points to disable or reactivate them. Then click</span> <b data-i18n="help.save_selection">Save selection</b>.</p>

            <div id="image-container">
                <img id="climbing-image" src="{wall['image_url']}" alt="Climbing wall" data-i18n-alt="image.alt">
            </div>

            <div id="status">Points: 0 / 4</div>
            <div id="action-buttons">
                <button id="reset-btn" type="button" data-i18n="button.reset">Reset</button>
                <button id="submit-btn" data-i18n="button.send">Send coordinates</button>
            </div>

            {language_switch}

            <script>
                // JavaScript bleibt unverändert wie in test.html
                const imageContainer = document.getElementById('image-container');
                const climbingImage = document.getElementById('climbing-image');
                const submitBtn = document.getElementById('submit-btn');
                const resetBtn = document.getElementById('reset-btn');
                const statusDiv = document.getElementById('status');
                const alternatingCheckbox = document.getElementById('alternating');
                const alternatingStart = document.getElementById('alternating-start');
                const rows = document.getElementById('rows');
                const columns = document.getElementById('columns');
                const ledStartCornerSelect = document.getElementById('led-start-corner');
                const ledDirectionSelect = document.getElementById('led-direction');
                const savedCreation = {saved_creation_json};
                const wallImageWidth = {wall_image_width_json};
                const wallImageHeight = {wall_image_height_json};
                let points = savedCreation.points || [];
                let renderedPositions = savedCreation.positions || null;
                let positionLedIds = savedCreation.position_led_ids || {{}};
                let renderedHolds2led = savedCreation.holds2led || {{}};
                let excludedPositionIds = new Set(savedCreation.excluded_position_ids || []);
                let selectionDirty = false;
                let lastGridSettings = null;
                let savedCreationInitialized = false;

                function t(key, replacements = {{}}) {{
                    return window.cruxI18n.t(key, replacements);
                }}

                function updateSubmitButtonLabel() {{
                    submitBtn.textContent = t(
                        renderedPositions ? 'button.save' : 'button.send'
                    );
                }}

                alternatingCheckbox.addEventListener('change', () => {{
                    alternatingStart.disabled = !alternatingCheckbox.checked;
                }});

                function coordinateWidth() {{
                    return wallImageWidth || climbingImage.naturalWidth;
                }}

                function coordinateHeight() {{
                    return wallImageHeight || climbingImage.naturalHeight;
                }}

                function imageToDisplay(point) {{
                    const rect = climbingImage.getBoundingClientRect();
                    return {{
                        x: point.x * rect.width / coordinateWidth(),
                        y: point.y * rect.height / coordinateHeight(),
                    }};
                }}

                function displayToImage(x, y) {{
                    const rect = climbingImage.getBoundingClientRect();
                    return {{
                        x: Math.round(x * coordinateWidth() / rect.width),
                        y: Math.round(y * coordinateHeight() / rect.height),
                    }};
                }}

                function normalizeSavedCreationCoordinates() {{
                    const sourceWidth = savedCreation.coordinate_space === 'wall_image'
                        ? (savedCreation.coordinate_width || wallImageWidth)
                        : (savedCreation.coordinate_width || climbingImage.naturalWidth);
                    const sourceHeight = savedCreation.coordinate_space === 'wall_image'
                        ? (savedCreation.coordinate_height || wallImageHeight)
                        : (savedCreation.coordinate_height || climbingImage.naturalHeight);
                    const targetWidth = coordinateWidth();
                    const targetHeight = coordinateHeight();
                    if (!sourceWidth || !sourceHeight || !targetWidth || !targetHeight) return;

                    const scaleX = targetWidth / sourceWidth;
                    const scaleY = targetHeight / sourceHeight;
                    points = points.map(point => ({{
                        x: Math.round(point.x * scaleX),
                        y: Math.round(point.y * scaleY),
                    }}));
                    if (renderedPositions) {{
                        renderedPositions = Object.fromEntries(
                            Object.entries(renderedPositions).map(([positionId, point]) => [
                                positionId,
                                [
                                    Math.round(point[0] * scaleX),
                                    Math.round(point[1] * scaleY),
                                ],
                            ])
                        );
                    }}
                    savedCreation.coordinate_space = 'wall_image';
                    savedCreation.coordinate_width = targetWidth;
                    savedCreation.coordinate_height = targetHeight;
                }}

                function renderGrid() {{
                    document.querySelectorAll('.grid-point').forEach(gp => gp.remove());
                    if (!renderedPositions) return;

                    const led2holds = {{}};
                    for (const holdId in renderedHolds2led) {{
                        const ledId = renderedHolds2led[holdId];
                        if (!led2holds[ledId]) led2holds[ledId] = holdId;
                    }}

                    for (const positionIdText in renderedPositions) {{
                        const [x, y] = renderedPositions[positionIdText];
                        const displayPoint = imageToDisplay({{ x, y }});
                        const positionId = Number(positionIdText);
                        const ledId = positionLedIds[positionIdText];
                        const gridPointElement = document.createElement('div');
                        const excluded = excludedPositionIds.has(positionId);
                        const classes = ['grid-point'];
                        gridPointElement.style.left = `${{displayPoint.x}}px`;
                        gridPointElement.style.top = `${{displayPoint.y}}px`;
                        gridPointElement.dataset.positionId = positionIdText;

                        if (excluded) {{
                            classes.push('excluded-point');
                            gridPointElement.title = t('grid.excluded_title');
                        }} else if (led2holds[ledId]) {{
                            classes.push('hold-point');
                            gridPointElement.title = t('grid.hold_title', {{
                                holdId: led2holds[ledId],
                                ledId: ledId,
                            }});
                            gridPointElement.textContent = led2holds[ledId].substring(0, 4);
                        }} else {{
                            gridPointElement.title = t('grid.led_title', {{ ledId: ledId }});
                        }}

                        gridPointElement.className = classes.join(' ');
                        gridPointElement.addEventListener('click', (event) => {{
                            event.stopPropagation();
                            if (excludedPositionIds.has(positionId)) {{
                                excludedPositionIds.delete(positionId);
                            }} else {{
                                excludedPositionIds.add(positionId);
                            }}
                            selectionDirty = true;
                            updateSubmitButtonLabel();
                            renderGrid();
                            updateGridStatus();
                        }});
                        imageContainer.appendChild(gridPointElement);
                    }}
                }}

                function updateGridStatus() {{
                    if (!renderedPositions) return;
                    const total = Object.keys(renderedPositions).length;
                    const active = total - excludedPositionIds.size;
                    const suffix = selectionDirty ? t('status.unsaved') : '';
                    statusDiv.textContent = t('status.grid', {{
                        active: active,
                        excluded: excludedPositionIds.size,
                        suffix: suffix,
                    }});
                }}

                function updateUI() {{
                    document.querySelectorAll('.point').forEach(p => p.remove());
                    points.forEach(p => {{
                        const displayPoint = imageToDisplay(p);
                        const pointElement = document.createElement('div');
                        pointElement.className = 'point';
                        pointElement.style.left = `${{displayPoint.x}}px`;
                        pointElement.style.top = `${{displayPoint.y}}px`;
                        imageContainer.appendChild(pointElement);
                    }});
                    statusDiv.textContent = t('status.points', {{ count: points.length }});
                    if (points.length === 4) {{
                        submitBtn.style.display = 'block';
                    }} else {{
                        submitBtn.style.display = 'none';
                    }}
                    resetBtn.style.display = (points.length > 0 || renderedPositions) ? 'block' : 'none';
                }}

                resetBtn.addEventListener('click', () => {{
                    points = [];
                    renderedPositions = null;
                    positionLedIds = {{}};
                    renderedHolds2led = {{}};
                    excludedPositionIds.clear();
                    selectionDirty = false;
                    lastGridSettings = null;
                    updateSubmitButtonLabel();
                    updateUI();
                    renderGrid();
                }});

                function currentGridSettings() {{
                    return JSON.stringify({{
                        points: points,
                        r: parseInt(rows.value),
                        c: parseInt(columns.value),
                        alternating: alternatingCheckbox.checked,
                        alternatingStartColumn: parseInt(alternatingStart.value),
                        ledStartCorner: ledStartCornerSelect.value,
                        ledDirection: ledDirectionSelect.value,
                    }});
                }}

                function initializeSavedCreation() {{
                    normalizeSavedCreationCoordinates();
                    if (savedCreation.r !== undefined) rows.value = savedCreation.r;
                    if (savedCreation.c !== undefined) columns.value = savedCreation.c;
                    alternatingCheckbox.checked = Boolean(savedCreation.alternating);
                    alternatingStart.value = savedCreation.alternating_start_column ?? 0;
                    alternatingStart.disabled = !alternatingCheckbox.checked;
                    if (savedCreation.led_start_corner) {{
                        ledStartCornerSelect.value = savedCreation.led_start_corner;
                    }}
                    if (savedCreation.led_direction) {{
                        ledDirectionSelect.value = savedCreation.led_direction;
                    }}
                    if (points.length === 4) {{
                        lastGridSettings = currentGridSettings();
                    }}
                    updateSubmitButtonLabel();
                    updateUI();
                    renderGrid();
                    updateGridStatus();
                    savedCreationInitialized = true;
                }}

                imageContainer.addEventListener('click', (event) => {{
                    if (points.length < 4) {{
                        const rect = climbingImage.getBoundingClientRect();
                        const x = event.clientX - rect.left;
                        const y = event.clientY - rect.top;
                        points.push(displayToImage(x, y));
                        updateUI();
                    }}
                }});

                window.addEventListener('resize', () => {{
                    updateUI();
                    renderGrid();
                    updateGridStatus();
                }});

                if ('ResizeObserver' in window) {{
                    new ResizeObserver(() => {{
                        if (!savedCreationInitialized) return;
                        updateUI();
                        renderGrid();
                        updateGridStatus();
                    }}).observe(climbingImage);
                }}

                window.addEventListener('crux-language-change', () => {{
                    updateSubmitButtonLabel();
                    updateUI();
                    renderGrid();
                    updateGridStatus();
                }});

                imageContainer.addEventListener('contextmenu', (event) => {{
                    event.preventDefault();
                    if (points.length > 0) {{
                        points.pop();
                        updateUI();
                    }}
                }});

                submitBtn.addEventListener('click', async () => {{
                    if (points.length !== 4) {{
                        alert(t('alert.four_points'));
                        return;
                    }}

                    const r = parseInt(rows.value);
                    const c = parseInt(columns.value);
                    const alternating = document.getElementById('alternating').checked;
                    const alternatingStartColumn = parseInt(alternatingStart.value);
                    const ledStartCorner = document.getElementById('led-start-corner').value;
                    const ledDirection = document.getElementById('led-direction').value;

                    if (isNaN(r) || isNaN(c)) {{
                        alert(t('alert.valid_grid'));
                        return;
                    }}

                    if (alternating && c < 2) {{
                        alert(t('alert.alternating_columns'));
                        return;
                    }}

                    const gridSettings = currentGridSettings();
                    if (lastGridSettings !== null && gridSettings !== lastGridSettings) {{
                        excludedPositionIds.clear();
                    }}

                    if (renderedPositions && excludedPositionIds.size === Object.keys(renderedPositions).length) {{
                        alert(t('alert.active_position'));
                        return;
                    }}

                    const payload = {{
                        p1x: points[0].x,
                        p1y: points[0].y,
                        p2x: points[1].x,
                        p2y: points[1].y,
                        p3x: points[2].x,
                        p3y: points[2].y,
                        p4x: points[3].x,
                        p4y: points[3].y,
                        r: r,
                        c: c,
                        alternating: alternating,
                        alternating_start_column: alternatingStartColumn,
                        led_start_corner: ledStartCorner,
                        led_direction: ledDirection,
                        excluded_position_ids: Array.from(excludedPositionIds),
                        wallid: { wall['id'] }
                    }};
                    
                    console.log('Sende folgende Daten:', payload);

                    try {{
                        const response = await fetch('{path_prefix}/defineholds', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify(payload),
                        }});
                        const result = await response.json();
                        if (!response.ok) {{
                            throw new Error(result.detail || result.message || `HTTP ${{response.status}}`);
                        }}
                        
                        if (result.positions) {{
                            renderedPositions = result.positions;
                            positionLedIds = result.position_led_ids || {{}};
                            renderedHolds2led = result.holds2led || {{}};
                            excludedPositionIds = new Set(result.excluded_position_ids || []);
                            selectionDirty = false;
                            lastGridSettings = gridSettings;
                            updateSubmitButtonLabel();
                            renderGrid();
                            updateGridStatus();
                        }}

                        alert(t('alert.saved'));
                    }} catch (error) {{
                        console.error('Fehler beim Senden:', error);
                        alert(t('alert.send_error', {{ message: error.message }}));
                    }}
                }});

                if (climbingImage.complete && climbingImage.naturalWidth) {{
                    initializeSavedCreation();
                }} else {{
                    climbingImage.addEventListener('load', initializeSavedCreation, {{ once: true }});
                }}
            </script>
        </body>
        </html>
        """
    return html_content
