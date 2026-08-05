def return_wall_lighting_html(path_prefix=""):
    html= """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <title>Wand-Beleuchtungsmodus</title>
        <style>
            body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; margin-top: 50px; background-color: #f4f4f9; }
            h1 { color: #333; }
            button { padding: 12px 25px; font-size: 16px; margin: 10px; cursor: pointer; border-radius: 5px; border: none; color: white; transition: background-color 0.3s; }
            #btn-dark { background-color: #555; }
            #btn-dark:hover { background-color: #333; }
            #btn-bright { background-color: #007BFF; }
            #btn-bright:hover { background-color: #0056b3; }
            #status { margin-top: 20px; font-weight: bold; font-size: 1.1em; }
        </style>
    </head>
    <body>
        <h1>Wand-Beleuchtungsmodus</h1>
        <p>Wähle den Beleuchtungsmodus für die Kletterwand.</p>
        <div>
            <button id="btn-dark" onclick="setMode('dark')">Dunkel – nur Boulder</button>
            <button id="btn-bright" onclick="setMode('bright')">Hell – freie LEDs gedimmt</button>
        </div>
        <div id="status"></div>

        <script>
            async function setMode(mode) {
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = 'Wird umgeschaltet...';
                try {
                    const response = await fetch('__PATH_PREFIX__/wall_lighting_mode', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ mode: mode }),
                    });
                    const result = await response.json();
                    if (response.ok) {
                        statusDiv.textContent = `Erfolgreich! ${result.message}`;
                        statusDiv.style.color = 'green';
                    } else {
                        throw new Error(result.message || 'Ein Fehler ist aufgetreten.');
                    }
                } catch (error) {
                    statusDiv.textContent = `Fehler: ${error.message}`;
                    statusDiv.style.color = 'red';
                }
            }
        </script>
    </body>
    </html>
    """
    return html.replace("__PATH_PREFIX__", path_prefix)
