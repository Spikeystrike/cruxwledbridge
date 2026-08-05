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
                    pointer-events: none;
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
                    cursor: help;
                    /* Style for the text inside */
                    line-height: 16px;
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
            </div>
            <p>Beim alternierenden Raster muss C gerade sein. Bei C=22 nutzt jede Reihe 11 Punkte; die verwendeten Spalten wechseln von Reihe zu Reihe.</p>
            <p>Bitte klicke die 4 Eckpunkte in der Reihenfolge an: <b>Links-Oben, Rechts-Oben, Rechts-Unten, Links-Unten</b>.</p>

            <div id="image-container">
                <img id="climbing-image" src="{wall['image_url']}" alt="Kletterwand">
            </div>

            <div id="status">Punkte: 0 / 4</div>
            <button id="submit-btn">Koordinaten Senden</button>

            <script>
                // JavaScript bleibt unverändert wie in test.html
                const imageContainer = document.getElementById('image-container');
                const submitBtn = document.getElementById('submit-btn');
                const statusDiv = document.getElementById('status');
                let points = [];

                function updateUI() {{
                    document.querySelectorAll('.point').forEach(p => p.remove());
                    points.forEach(p => {{
                        const pointElement = document.createElement('div');
                        pointElement.className = 'point';
                        pointElement.style.left = `${{p.x}}px`;
                        pointElement.style.top = `${{p.y}}px`;
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
                        const rect = imageContainer.getBoundingClientRect();
                        const x = event.clientX - rect.left;
                        const y = event.clientY - rect.top;
                        points.push({{ x: Math.round(x), y: Math.round(y) }});
                        updateUI();
                    }}
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

                    if (isNaN(r) || isNaN(c)) {{
                        alert('Bitte geben Sie gültige Werte für R und C ein.');
                        return;
                    }}

                    if (alternating && (c < 2 || c % 2 !== 0)) {{
                        alert('Für ein alternierendes Raster muss C eine gerade Zahl sein.');
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
                        
                        // Clear previous grid points if any
                        document.querySelectorAll('.grid-point').forEach(gp => gp.remove());

                        if (result.grid) {{
                            const led2holds = {{}};
                            if (result.holds2led) {{
                                for (const holdId in result.holds2led) {{
                                    const ledId = result.holds2led[holdId];
                                    // Store only the FIRST hold ID found for an LED
                                    if (!led2holds[ledId]) {{
                                        led2holds[ledId] = holdId;
                                    }}
                                }}
                            }}

                            for (const id in result.grid) {{
                                const [x, y] = result.grid[id];
                                const gridPointElement = document.createElement('div');
                                // Use a variable for class names
                                let classes = ['grid-point'];
                                gridPointElement.style.left = `${{x}}px`;
                                gridPointElement.style.top = `${{y}}px`;
                                if (led2holds[id]) {{
                                    classes.push('hold-point');
                                    gridPointElement.title = `Hold-ID: ${{led2holds[id]}}\nLED-ID: ${{id}}`;
                                    // Display the first 4 chars of the hold ID
                                    gridPointElement.textContent = led2holds[id].substring(0, 4);
                                }}
                                gridPointElement.className = classes.join(' ');
                                imageContainer.appendChild(gridPointElement);
                            }}
                        }}

                        alert(`Server-Antwort: ${{result.message}}`);
                    }} catch (error) {{
                        console.error('Fehler beim Senden:', error);
                        alert('Ein Fehler ist beim Senden aufgetreten.');
                    }}
                }});
            </script>
        </body>
        </html>
        """
    return html_content
