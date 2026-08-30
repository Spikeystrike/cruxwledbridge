from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Wall lighting settings",
        "page.heading": "Wall lighting settings",
        "page.description": "Configure how routes and unused LEDs are illuminated.",
        "mode.heading": "Lighting mode",
        "mode.dark_button": "Dark – boulder only",
        "mode.bright_button": "Bright – dim unused LEDs",
        "mode.background_brightness": "Unused LED brightness: {value}%",
        "mode.boulder_brightness": "Boulder LED brightness: {value}%",
        "mode.above_brightness": "Above-hold LED brightness: {value}%",
        "direction.heading": "Hold illumination direction",
        "direction.description": "Choose whether each hold is illuminated from below, above, or both sides. A standard grid uses the same column one row higher; an alternating grid uses the same column two rows higher. If that exact position is disabled, the hold is illuminated from below instead of using another lateral light. The separate above-hold brightness applies only to Above and below; Above only uses the regular boulder brightness.",
        "direction.below": "Below only",
        "direction.above": "Above only",
        "direction.both": "Above and below",
        "celebration.heading": "Send celebration",
        "celebration.description": "Choose the effect shown on all LEDs for about 3 seconds when the gym reports climb.sent.",
        "celebration.off": "Off",
        "celebration.rainbow": "Moving rainbow",
        "celebration.fireworks": "Fireworks",
        "celebration.color_twinkles": "Color sparkles",
        "celebration.pride": "Rainbow party",
        "save.button": "Save all lighting settings",
        "status.saving": "Saving settings...",
        "status.saved": "All wall lighting settings were saved.",
        "status.error": "Could not save settings: {message}",
        "status.generic_error": "An error occurred.",
    },
    "de": {
        "page.title": "Wandbeleuchtungs-Einstellungen",
        "page.heading": "Wandbeleuchtungs-Einstellungen",
        "page.description": "Lege fest, wie Routen und freie LEDs beleuchtet werden.",
        "mode.heading": "Beleuchtungsmodus",
        "mode.dark_button": "Dunkel – nur Boulder",
        "mode.bright_button": "Hell – freie LEDs gedimmt",
        "mode.background_brightness": "Helligkeit freier LEDs: {value}%",
        "mode.boulder_brightness": "Helligkeit der Boulder-LEDs: {value}%",
        "mode.above_brightness": "Helligkeit der LEDs oberhalb: {value}%",
        "direction.heading": "Beleuchtungsrichtung der Griffe",
        "direction.description": "Lege fest, ob jeder Griff von unten, von oben oder von beiden Seiten beleuchtet wird. Im normalen Raster liegt die obere Position eine Zeile höher in derselben Spalte, im versetzten Raster zwei Zeilen höher. Ist genau diese Position abgewählt, wird der Griff von unten beleuchtet, ohne seitlich auszuweichen. Die separate obere Helligkeit gilt nur für Oben und unten; Nur von oben verwendet die normale Boulder-Helligkeit.",
        "direction.below": "Nur von unten",
        "direction.above": "Nur von oben",
        "direction.both": "Oben und unten",
        "celebration.heading": "Jubeleffekt beim Top",
        "celebration.description": "Wähle den Effekt, der etwa 3 Sekunden lang auf allen LEDs läuft, wenn die Halle climb.sent meldet.",
        "celebration.off": "Aus",
        "celebration.rainbow": "Laufender Regenbogen",
        "celebration.fireworks": "Feuerwerk",
        "celebration.color_twinkles": "Buntes Funkeln",
        "celebration.pride": "Regenbogen-Party",
        "save.button": "Alle Beleuchtungseinstellungen speichern",
        "status.saving": "Einstellungen werden gespeichert...",
        "status.saved": "Alle Wandbeleuchtungs-Einstellungen wurden gespeichert.",
        "status.error": "Einstellungen konnten nicht gespeichert werden: {message}",
        "status.generic_error": "Ein Fehler ist aufgetreten.",
    },
}


def return_wall_lighting_html(
    path_prefix="",
    celebration_effect="rainbow",
    bright_brightness_percent=20,
    wall_lighting_mode="dark",
    boulder_brightness_percent=100,
    hold_lighting_direction="below",
    above_brightness_percent=100,
):
    language_switch = language_switch_html(TRANSLATIONS)
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title data-i18n="page.title">Wall lighting settings</title>
        <style>
            body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; margin: 40px 20px; background-color: #f4f4f9; color: #333; }
            h1, h2 { color: #333; }
            form { width: min(560px, 100%); }
            section { padding: 22px 0; border-top: 1px solid #ccc; }
            section:first-of-type { border-top: 0; }
            .mode-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
            .mode-options input { position: absolute; opacity: 0; pointer-events: none; }
            .mode-options label { padding: 14px; border: 2px solid transparent; border-radius: 7px; color: white; text-align: center; cursor: pointer; }
            label[for="mode-dark"] { background: #555; }
            label[for="mode-bright"] { background: #007bff; }
            .mode-options input:checked + label { border-color: #111; box-shadow: 0 0 0 2px white inset; }
            .direction-options { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
            .direction-options input { position: absolute; opacity: 0; pointer-events: none; }
            .direction-options label { padding: 14px 8px; border: 2px solid transparent; border-radius: 7px; background: #6c757d; color: white; text-align: center; cursor: pointer; }
            .direction-options input:checked + label { border-color: #111; box-shadow: 0 0 0 2px white inset; background: #0069d9; }
            .brightness-control { margin-top: 24px; text-align: center; }
            .brightness-control.is-disabled { opacity: 0.5; }
            .brightness-control label { display: block; margin-bottom: 8px; font-weight: bold; }
            .brightness-control input { width: 100%; }
            .celebration select { box-sizing: border-box; width: 100%; padding: 10px 14px; font-size: 16px; border-radius: 5px; }
            .save-area { padding-top: 24px; border-top: 1px solid #ccc; text-align: center; }
            #save-settings { padding: 13px 22px; border: 0; border-radius: 6px; background: #218838; color: white; font-size: 17px; font-weight: 600; cursor: pointer; }
            #save-settings:hover { background: #176b2b; }
            #save-settings:disabled { opacity: 0.65; cursor: wait; }
            #status { min-height: 1.4em; margin-top: 14px; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1 data-i18n="page.heading">Wall lighting settings</h1>
        <p data-i18n="page.description">Configure how routes and unused LEDs are illuminated.</p>

        <form id="wall-lighting-form">
            <section>
                <h2 data-i18n="mode.heading">Lighting mode</h2>
                <div class="mode-options">
                    <input id="mode-dark" type="radio" name="mode" value="dark" __DARK_CHECKED__>
                    <label for="mode-dark" data-i18n="mode.dark_button">Dark – boulder only</label>
                    <input id="mode-bright" type="radio" name="mode" value="bright" __BRIGHT_CHECKED__>
                    <label for="mode-bright" data-i18n="mode.bright_button">Bright – dim unused LEDs</label>
                </div>
                <div class="brightness-control">
                    <label for="bright-brightness" id="bright-brightness-label">Unused LED brightness: __BRIGHT_BRIGHTNESS__%</label>
                    <input id="bright-brightness" type="range" min="10" max="100" step="1" value="__BRIGHT_BRIGHTNESS__">
                </div>
                <div class="brightness-control">
                    <label for="boulder-brightness" id="boulder-brightness-label">Boulder LED brightness: __BOULDER_BRIGHTNESS__%</label>
                    <input id="boulder-brightness" type="range" min="10" max="100" step="1" value="__BOULDER_BRIGHTNESS__">
                </div>
            </section>

            <section>
                <h2 data-i18n="direction.heading">Hold illumination direction</h2>
                <p data-i18n="direction.description">Choose whether each hold is illuminated from below, above, or both sides. A standard grid uses the same column one row higher; an alternating grid uses the same column two rows higher. If that exact position is disabled, the hold is illuminated from below instead of using another lateral light. The separate above-hold brightness applies only to Above and below; Above only uses the regular boulder brightness.</p>
                <div class="direction-options">
                    <input id="direction-below" type="radio" name="hold_lighting_direction" value="below" __DIRECTION_BELOW_CHECKED__>
                    <label for="direction-below" data-i18n="direction.below">Below only</label>
                    <input id="direction-above" type="radio" name="hold_lighting_direction" value="above" __DIRECTION_ABOVE_CHECKED__>
                    <label for="direction-above" data-i18n="direction.above">Above only</label>
                    <input id="direction-both" type="radio" name="hold_lighting_direction" value="both" __DIRECTION_BOTH_CHECKED__>
                    <label for="direction-both" data-i18n="direction.both">Above and below</label>
                </div>
                <div class="brightness-control" id="above-brightness-control">
                    <label for="above-brightness" id="above-brightness-label">Above-hold LED brightness: __ABOVE_BRIGHTNESS__%</label>
                    <input id="above-brightness" type="range" min="10" max="100" step="1" value="__ABOVE_BRIGHTNESS__">
                </div>
            </section>

            <section class="celebration">
                <h2 data-i18n="celebration.heading">Send celebration</h2>
                <p data-i18n="celebration.description">Choose the effect shown on all LEDs for about 3 seconds when the gym reports climb.sent.</p>
                <select id="celebration-effect" aria-label="Send celebration">
                    <option value="off" data-i18n="celebration.off">Off</option>
                    <option value="rainbow" data-i18n="celebration.rainbow">Moving rainbow</option>
                    <option value="fireworks" data-i18n="celebration.fireworks">Fireworks</option>
                    <option value="color_twinkles" data-i18n="celebration.color_twinkles">Color sparkles</option>
                    <option value="pride" data-i18n="celebration.pride">Rainbow party</option>
                </select>
            </section>

            <div class="save-area">
                <button id="save-settings" type="submit" data-i18n="save.button">Save all lighting settings</button>
                <div id="status" role="status" aria-live="polite"></div>
            </div>
        </form>

        __LANGUAGE_SWITCH__
        <script>
            const form = document.getElementById('wall-lighting-form');
            const saveButton = document.getElementById('save-settings');
            const statusDiv = document.getElementById('status');
            const celebrationSelect = document.getElementById('celebration-effect');
            const brightBrightnessInput = document.getElementById('bright-brightness');
            const boulderBrightnessInput = document.getElementById('boulder-brightness');
            const aboveBrightnessInput = document.getElementById('above-brightness');
            const aboveBrightnessControl = document.getElementById('above-brightness-control');
            const directionInputs = form.querySelectorAll('[name="hold_lighting_direction"]');
            const statusState = { kind: 'idle', message: '' };
            celebrationSelect.value = '__CELEBRATION_EFFECT__';

            function renderBrightnessLabels() {
                document.getElementById('bright-brightness-label').textContent = window.cruxI18n.t(
                    'mode.background_brightness',
                    { value: brightBrightnessInput.value },
                );
                document.getElementById('boulder-brightness-label').textContent = window.cruxI18n.t(
                    'mode.boulder_brightness',
                    { value: boulderBrightnessInput.value },
                );
                document.getElementById('above-brightness-label').textContent = window.cruxI18n.t(
                    'mode.above_brightness',
                    { value: aboveBrightnessInput.value },
                );
            }

            function renderStatus() {
                const t = window.cruxI18n.t;
                if (statusState.kind === 'saving') {
                    statusDiv.textContent = t('status.saving');
                } else if (statusState.kind === 'saved') {
                    statusDiv.textContent = t('status.saved');
                } else if (statusState.kind === 'error') {
                    statusDiv.textContent = t('status.error', { message: statusState.message });
                } else {
                    statusDiv.textContent = '';
                }
            }

            function renderAboveBrightnessAvailability() {
                const enabled = form.elements.hold_lighting_direction.value === 'both';
                aboveBrightnessInput.disabled = !enabled;
                aboveBrightnessControl.classList.toggle('is-disabled', !enabled);
            }

            brightBrightnessInput.addEventListener('input', renderBrightnessLabels);
            boulderBrightnessInput.addEventListener('input', renderBrightnessLabels);
            aboveBrightnessInput.addEventListener('input', renderBrightnessLabels);
            directionInputs.forEach((input) => {
                input.addEventListener('change', renderAboveBrightnessAvailability);
            });

            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                statusState.kind = 'saving';
                saveButton.disabled = true;
                statusDiv.style.color = '#555';
                renderStatus();
                try {
                    const response = await fetch('__PATH_PREFIX__/wall_lighting_settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            mode: form.elements.mode.value,
                            bright_brightness_percent: Number(brightBrightnessInput.value),
                            boulder_brightness_percent: Number(boulderBrightnessInput.value),
                            above_brightness_percent: Number(aboveBrightnessInput.value),
                            hold_lighting_direction: form.elements.hold_lighting_direction.value,
                            celebration_effect: celebrationSelect.value,
                        }),
                    });
                    const result = await response.json();
                    if (!response.ok) {
                        throw new Error(result.message || window.cruxI18n.t('status.generic_error'));
                    }
                    statusState.kind = 'saved';
                    statusDiv.style.color = 'green';
                } catch (error) {
                    statusState.kind = 'error';
                    statusState.message = error.message;
                    statusDiv.style.color = 'red';
                } finally {
                    saveButton.disabled = false;
                    renderStatus();
                }
            });

            window.addEventListener('crux-language-change', () => {
                renderBrightnessLabels();
                renderStatus();
            });

            renderBrightnessLabels();
            renderAboveBrightnessAvailability();
        </script>
    </body>
    </html>
    """
    return (
        html.replace("__PATH_PREFIX__", path_prefix)
        .replace("__CELEBRATION_EFFECT__", celebration_effect)
        .replace("__BRIGHT_BRIGHTNESS__", str(bright_brightness_percent))
        .replace("__BOULDER_BRIGHTNESS__", str(boulder_brightness_percent))
        .replace("__ABOVE_BRIGHTNESS__", str(above_brightness_percent))
        .replace("__DARK_CHECKED__", "checked" if wall_lighting_mode == "dark" else "")
        .replace("__BRIGHT_CHECKED__", "checked" if wall_lighting_mode == "bright" else "")
        .replace("__DIRECTION_BELOW_CHECKED__", "checked" if hold_lighting_direction == "below" else "")
        .replace("__DIRECTION_ABOVE_CHECKED__", "checked" if hold_lighting_direction == "above" else "")
        .replace("__DIRECTION_BOTH_CHECKED__", "checked" if hold_lighting_direction == "both" else "")
        .replace("__LANGUAGE_SWITCH__", language_switch)
    )
