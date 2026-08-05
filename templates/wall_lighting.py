from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Wall lighting mode",
        "page.heading": "Wall lighting mode",
        "page.description": "Choose the lighting mode for the climbing wall.",
        "mode.dark_button": "Dark – boulder only",
        "mode.bright_button": "Bright – dim unused LEDs",
        "mode.dark": "dark",
        "mode.bright": "bright",
        "status.switching": "Switching...",
        "status.success": "Success! Wall lighting mode set to {mode}.",
        "status.error": "Error: {message}",
        "status.generic_error": "An error occurred.",
    },
    "de": {
        "page.title": "Wand-Beleuchtungsmodus",
        "page.heading": "Wand-Beleuchtungsmodus",
        "page.description": "Wähle den Beleuchtungsmodus für die Kletterwand.",
        "mode.dark_button": "Dunkel – nur Boulder",
        "mode.bright_button": "Hell – freie LEDs gedimmt",
        "mode.dark": "dunkel",
        "mode.bright": "hell",
        "status.switching": "Wird umgeschaltet...",
        "status.success": "Erfolgreich! Wand-Beleuchtungsmodus auf {mode} gesetzt.",
        "status.error": "Fehler: {message}",
        "status.generic_error": "Ein Fehler ist aufgetreten.",
    },
}


def return_wall_lighting_html(path_prefix=""):
    language_switch = language_switch_html(TRANSLATIONS)
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title data-i18n="page.title">Wall lighting mode</title>
        <style>
            body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; margin-top: 50px; background-color: #f4f4f9; }
            h1 { color: #333; }
            .mode-button { padding: 12px 25px; font-size: 16px; margin: 10px; cursor: pointer; border-radius: 5px; border: none; color: white; transition: background-color 0.3s; }
            #btn-dark { background-color: #555; }
            #btn-dark:hover { background-color: #333; }
            #btn-bright { background-color: #007BFF; }
            #btn-bright:hover { background-color: #0056b3; }
            #status { margin-top: 20px; font-weight: bold; font-size: 1.1em; }
        </style>
    </head>
    <body>
        <h1 data-i18n="page.heading">Wall lighting mode</h1>
        <p data-i18n="page.description">Choose the lighting mode for the climbing wall.</p>
        <div>
            <button class="mode-button" id="btn-dark" onclick="setMode('dark')" data-i18n="mode.dark_button">Dark – boulder only</button>
            <button class="mode-button" id="btn-bright" onclick="setMode('bright')" data-i18n="mode.bright_button">Bright – dim unused LEDs</button>
        </div>
        <div id="status"></div>

        __LANGUAGE_SWITCH__
        <script>
            const statusState = { kind: 'idle' };

            function renderStatus() {
                const statusDiv = document.getElementById('status');
                const t = window.cruxI18n.t;
                if (statusState.kind === 'switching') {
                    statusDiv.textContent = t('status.switching');
                } else if (statusState.kind === 'success') {
                    statusDiv.textContent = t('status.success', {
                        mode: t(`mode.${statusState.mode}`),
                    });
                } else if (statusState.kind === 'error') {
                    statusDiv.textContent = t('status.error', { message: statusState.message });
                }
            }

            async function setMode(mode) {
                const statusDiv = document.getElementById('status');
                statusState.kind = 'switching';
                renderStatus();
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
                        statusState.kind = 'success';
                        statusState.mode = mode;
                        statusDiv.style.color = 'green';
                    } else {
                        throw new Error(result.message || window.cruxI18n.t('status.generic_error'));
                    }
                } catch (error) {
                    statusState.kind = 'error';
                    statusState.message = error.message;
                    statusDiv.style.color = 'red';
                }
                renderStatus();
            }

            window.addEventListener('crux-language-change', renderStatus);
        </script>
    </body>
    </html>
    """
    return html.replace("__PATH_PREFIX__", path_prefix).replace(
        "__LANGUAGE_SWITCH__",
        language_switch,
    )
