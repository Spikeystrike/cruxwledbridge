def returnwallhtml(wall, path_prefix=""):
    html_content = f"""
        
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Kletterwand - Punkte auswählen</title>
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
                #submit-btn {{
                    display: none;
                    margin-top: 20px;
                    padding: 12px 25px;
                    font-size: 1.2em;
                    cursor: pointer;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    transition: background-color 0.3s;
                }}
                #submit-btn:hover {{
                    background-color: #45a049;
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
            <h1>Kletterwand - Punkte auswählen</h1>
             <div>
                <label for="rows">R: </label>
                <input type="number" id="rows" name="rows" placeholder="Anzahl der Reihen" min="1">
                <label for="columns">C: </label>
                <input type="number" id="columns" name="columns" placeholder="Anzahl der Spalten" min="1">
                <label for="alternating">
                    <input type="checkbox" id="alternating" name="alternating">
                    Alternierendes Raster
                </label>
                <label for="alternating-start">Oberste Reihe:</label>
                <select id="alternating-start" name="alternating-start" disabled>
                    <option value="0">Nicht eingerückt</option>
                    <option value="1">Eingerückt</option>
                </select>
                <label for="led-start-corner">LED 0:</label>
                <select id="led-start-corner" name="led-start-corner">
                    <option value="top_left">Oben links</option>
                    <option value="top_right">Oben rechts</option>
                    <option value="bottom_left" selected>Unten links</option>
                    <option value="bottom_right">Unten rechts</option>
                </select>
                <label for="led-direction">Kabelverlauf:</label>
                <select id="led-direction" name="led-direction">
                    <option value="horizontal">Horizontal (zeilenweise)</option>
                    <option value="vertical" selected>Vertikal (spaltenweise)</option>
                </select>
            </div>
            <p>Beim alternierenden Raster ist C die Anzahl aller möglichen Spalten. C darf gerade oder ungerade sein; die verwendeten Spalten wechseln von Reihe zu Reihe.</p>
            <p>Die LED-Nummerierung beginnt bei LED 0 in der gewählten Ecke und folgt dem Kabel schlangenförmig horizontal oder vertikal.</p>
            <p>Bitte klicke die 4 Eckpunkte in der Reihenfolge an: <b>Links-Oben, Rechts-Oben, Rechts-Unten, Links-Unten</b>.</p>
            <p>Nach dem Berechnen kannst du Rasterpunkte anklicken, um sie abzuwählen oder wieder zu aktivieren. Klicke danach auf <b>Auswahl speichern</b>.</p>

            <div id="image-container">
                <img id="climbing-image" src="{wall['image_url']}" alt="Kletterwand">
            </div>

            <div id="status">Punkte: 0 / 4</div>
            <button id="submit-btn">Koordinaten Senden</button>

            <script>
                // JavaScript bleibt unverändert wie in test.html
                const imageContainer = document.getElementById('image-container');
                const climbingImage = document.getElementById('climbing-image');
                const submitBtn = document.getElementById('submit-btn');
                const statusDiv = document.getElementById('status');
                const alternatingCheckbox = document.getElementById('alternating');
                const alternatingStart = document.getElementById('alternating-start');
                let points = [];
                let renderedPositions = null;
                let positionLedIds = {{}};
                let renderedHolds2led = {{}};
                let excludedPositionIds = new Set();
                let selectionDirty = false;
                let lastGridSettings = null;

                alternatingCheckbox.addEventListener('change', () => {{
                    alternatingStart.disabled = !alternatingCheckbox.checked;
                }});

                function imageToDisplay(point) {{
                    const rect = climbingImage.getBoundingClientRect();
                    return {{
                        x: point.x * rect.width / climbingImage.naturalWidth,
                        y: point.y * rect.height / climbingImage.naturalHeight,
                    }};
                }}

                function displayToImage(x, y) {{
                    const rect = climbingImage.getBoundingClientRect();
                    return {{
                        x: Math.round(x * climbingImage.naturalWidth / rect.width),
                        y: Math.round(y * climbingImage.naturalHeight / rect.height),
                    }};
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
                            gridPointElement.title = 'Position ist abgewählt. Anklicken zum Aktivieren.';
                        }} else if (led2holds[ledId]) {{
                            classes.push('hold-point');
                            gridPointElement.title = `Hold-ID: ${{led2holds[ledId]}}\nLED-ID: ${{ledId}}`;
                            gridPointElement.textContent = led2holds[ledId].substring(0, 4);
                        }} else {{
                            gridPointElement.title = `LED-ID: ${{ledId}}. Anklicken zum Abwählen.`;
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
                            submitBtn.textContent = 'Auswahl speichern';
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
                    const suffix = selectionDirty ? ' – noch nicht gespeichert' : '';
                    statusDiv.textContent = `Raster: ${{active}} aktiv, ${{excludedPositionIds.size}} abgewählt${{suffix}}`;
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
                    statusDiv.textContent = `Punkte: ${{points.length}} / 4`;
                    if (points.length === 4) {{
                        submitBtn.style.display = 'block';
                    }} else {{
                        submitBtn.style.display = 'none';
                    }}
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

                imageContainer.addEventListener('contextmenu', (event) => {{
                    event.preventDefault();
                    if (points.length > 0) {{
                        points.pop();
                        updateUI();
                    }}
                }});

                submitBtn.addEventListener('click', async () => {{
                    if (points.length !== 4) {{
                        alert('Bitte wählen Sie genau 4 Punkte aus.');
                        return;
                    }}

                    const r = parseInt(rows.value);
                    const c = parseInt(columns.value);
                    const alternating = document.getElementById('alternating').checked;
                    const alternatingStartColumn = parseInt(alternatingStart.value);
                    const ledStartCorner = document.getElementById('led-start-corner').value;
                    const ledDirection = document.getElementById('led-direction').value;

                    if (isNaN(r) || isNaN(c)) {{
                        alert('Bitte geben Sie gültige Werte für R und C ein.');
                        return;
                    }}

                    if (alternating && c < 2) {{
                        alert('Für ein alternierendes Raster muss C mindestens 2 sein.');
                        return;
                    }}

                    const gridSettings = JSON.stringify({{
                        points: points,
                        r: r,
                        c: c,
                        alternating: alternating,
                        alternatingStartColumn: alternatingStartColumn,
                        ledStartCorner: ledStartCorner,
                        ledDirection: ledDirection,
                    }});
                    if (lastGridSettings !== null && gridSettings !== lastGridSettings) {{
                        excludedPositionIds.clear();
                    }}

                    if (renderedPositions && excludedPositionIds.size === Object.keys(renderedPositions).length) {{
                        alert('Mindestens eine Rasterposition muss aktiv bleiben.');
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
                            submitBtn.textContent = 'Auswahl speichern';
                            renderGrid();
                            updateGridStatus();
                        }}

                        alert(`Server-Antwort: ${{result.message}}`);
                    }} catch (error) {{
                        console.error('Fehler beim Senden:', error);
                        alert(`Ein Fehler ist beim Senden aufgetreten: ${{error.message}}`);
                    }}
                }});
            </script>
        </body>
        </html>
        """
    return html_content
