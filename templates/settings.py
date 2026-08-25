from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Settings",
        "page.heading": "Settings",
        "page.description": "Configure general bridge behavior.",
        "energy.heading": "Energy saving",
        "energy.description": "Turn the illuminated route off automatically after the selected number of minutes.",
        "energy.label": "Route timeout in minutes",
        "energy.hint": "Use 0 to leave the route on until another route is selected.",
        "energy.save": "Save setting",
        "status.saving": "Saving...",
        "status.saved": "Saved: route turns off after {minutes} minutes.",
        "status.always_on": "Saved: illuminated routes stay on.",
        "status.error": "Could not save setting: {message}",
        "status.generic_error": "An error occurred.",
    },
    "de": {
        "page.title": "Einstellungen",
        "page.heading": "Einstellungen",
        "page.description": "Konfiguriere das allgemeine Verhalten der Bridge.",
        "energy.heading": "Energiesparmodus",
        "energy.description": "Schalte die beleuchtete Route nach der gewählten Anzahl Minuten automatisch aus.",
        "energy.label": "Route nach Minuten ausschalten",
        "energy.hint": "Mit 0 bleibt die Route an, bis eine andere Route ausgewählt wird.",
        "energy.save": "Einstellung speichern",
        "status.saving": "Wird gespeichert...",
        "status.saved": "Gespeichert: Die Route wird nach {minutes} Minuten ausgeschaltet.",
        "status.always_on": "Gespeichert: Beleuchtete Routen bleiben an.",
        "status.error": "Einstellung konnte nicht gespeichert werden: {message}",
        "status.generic_error": "Ein Fehler ist aufgetreten.",
    },
}


def return_settings_html(path_prefix="", route_timeout_minutes=0):
    language_switch = language_switch_html(TRANSLATIONS)
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title data-i18n="page.title">Settings</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: sans-serif; margin: 0; padding: 48px 20px; background: #f4f4f9; color: #222; }
            main { max-width: 620px; margin: 0 auto; }
            .intro { color: #555; }
            .card { margin-top: 28px; padding: 24px; border-radius: 10px; background: white; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
            .card h2 { margin-top: 0; }
            label { display: block; margin: 20px 0 7px; font-weight: bold; }
            input { width: 100%; padding: 10px 12px; border: 1px solid #aaa; border-radius: 5px; font-size: 16px; }
            .hint { color: #555; line-height: 1.45; }
            button { padding: 11px 16px; border: 0; border-radius: 5px; background: #007bff; color: white; font-size: 16px; cursor: pointer; }
            button:hover { background: #0056b3; }
            #status { min-height: 1.4em; margin-top: 14px; font-weight: bold; }
        </style>
    </head>
    <body>
        <main>
            <h1 data-i18n="page.heading">Settings</h1>
            <p class="intro" data-i18n="page.description">Configure general bridge behavior.</p>
            <section class="card">
                <h2 data-i18n="energy.heading">Energy saving</h2>
                <p data-i18n="energy.description">Turn the illuminated route off automatically after the selected number of minutes.</p>
                <form id="energy-saving-form">
                    <label for="route-timeout-minutes" data-i18n="energy.label">Route timeout in minutes</label>
                    <input id="route-timeout-minutes" name="route_timeout_minutes" type="number" min="0" step="1" value="__ROUTE_TIMEOUT_MINUTES__" required>
                    <p class="hint" data-i18n="energy.hint">Use 0 to leave the route on until another route is selected.</p>
                    <button type="submit" data-i18n="energy.save">Save setting</button>
                </form>
                <div id="status" role="status" aria-live="polite"></div>
            </section>
        </main>
        __LANGUAGE_SWITCH__
        <script>
            const form = document.getElementById('energy-saving-form');
            const timeoutInput = document.getElementById('route-timeout-minutes');
            const statusDiv = document.getElementById('status');
            const statusState = { kind: 'idle' };

            function renderStatus() {
                const t = window.cruxI18n.t;
                if (statusState.kind === 'saving') {
                    statusDiv.textContent = t('status.saving');
                } else if (statusState.kind === 'saved') {
                    statusDiv.textContent = statusState.minutes === 0
                        ? t('status.always_on')
                        : t('status.saved', { minutes: statusState.minutes });
                } else if (statusState.kind === 'error') {
                    statusDiv.textContent = t('status.error', { message: statusState.message });
                }
            }

            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                statusState.kind = 'saving';
                statusDiv.style.color = '';
                renderStatus();
                try {
                    const response = await fetch('__PATH_PREFIX__/route_timeout', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ route_timeout_minutes: Number(timeoutInput.value) }),
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.message || result.detail || window.cruxI18n.t('status.generic_error'));
                    statusState.kind = 'saved';
                    statusState.minutes = result.route_timeout_minutes;
                    statusDiv.style.color = 'green';
                } catch (error) {
                    statusState.kind = 'error';
                    statusState.message = error.message;
                    statusDiv.style.color = 'red';
                }
                renderStatus();
            });

            window.addEventListener('crux-language-change', renderStatus);
        </script>
    </body>
    </html>
    """
    return html.replace("__PATH_PREFIX__", path_prefix).replace(
        "__ROUTE_TIMEOUT_MINUTES__",
        str(route_timeout_minutes),
    ).replace("__LANGUAGE_SWITCH__", language_switch)
