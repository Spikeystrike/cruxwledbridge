from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Wall lighting mode",
        "page.heading": "Wall lighting mode",
        "page.description": "Choose the lighting mode for the climbing wall.",
        "mode.dark_button": "Dark – boulder only",
        "mode.bright_button": "Bright – dim unused LEDs",
        "mode.brightness": "Bright mode strength: {value}%",
        "mode.dark": "dark",
        "mode.bright": "bright",
        "status.switching": "Switching...",
        "status.success": "Success! Wall lighting mode set to {mode}.",
        "status.error": "Error: {message}",
        "status.generic_error": "An error occurred.",
        "celebration.heading": "Send celebration",
        "celebration.description": "Choose the effect shown on all LEDs for about 3 seconds when the gym reports climb.sent.",
        "celebration.off": "Off",
        "celebration.rainbow": "Moving rainbow",
        "celebration.fireworks": "Fireworks",
        "celebration.color_twinkles": "Color sparkles",
        "celebration.pride": "Rainbow party",
        "celebration.save": "Save effect",
        "celebration.saving": "Saving effect...",
        "celebration.saved": "Celebration effect saved: {effect}.",
        "celebration.error": "Could not save celebration effect: {message}",
    },
    "de": {
        "page.title": "Wand-Beleuchtungsmodus",
        "page.heading": "Wand-Beleuchtungsmodus",
        "page.description": "Wähle den Beleuchtungsmodus für die Kletterwand.",
        "mode.dark_button": "Dunkel – nur Boulder",
        "mode.bright_button": "Hell – freie LEDs gedimmt",
        "mode.brightness": "Stärke im hellen Modus: {value}%",
        "mode.dark": "dunkel",
        "mode.bright": "hell",
        "status.switching": "Wird umgeschaltet...",
        "status.success": "Erfolgreich! Wand-Beleuchtungsmodus auf {mode} gesetzt.",
        "status.error": "Fehler: {message}",
        "status.generic_error": "Ein Fehler ist aufgetreten.",
        "celebration.heading": "Jubeleffekt beim Top",
        "celebration.description": "Wähle den Effekt, der etwa 3 Sekunden lang auf allen LEDs läuft, wenn die Halle climb.sent meldet.",
        "celebration.off": "Aus",
        "celebration.rainbow": "Laufender Regenbogen",
        "celebration.fireworks": "Feuerwerk",
        "celebration.color_twinkles": "Buntes Funkeln",
        "celebration.pride": "Regenbogen-Party",
        "celebration.save": "Effekt speichern",
        "celebration.saving": "Effekt wird gespeichert...",
        "celebration.saved": "Jubeleffekt gespeichert: {effect}.",
        "celebration.error": "Jubeleffekt konnte nicht gespeichert werden: {message}",
    },
}


def return_wall_lighting_html(
    path_prefix="",
    celebration_effect="rainbow",
    bright_brightness_percent=20,
):
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
            .brightness-control { width: min(420px, calc(100vw - 48px)); margin: 12px 0 4px; text-align: center; }
            .brightness-control label { display: block; margin-bottom: 8px; font-weight: bold; }
            .brightness-control input { width: 100%; }
            #status { margin-top: 20px; font-weight: bold; font-size: 1.1em; }
            .celebration { margin-top: 32px; padding-top: 22px; border-top: 1px solid #ccc; text-align: center; max-width: 520px; }
            .celebration h2 { color: #333; margin-bottom: 8px; }
            .celebration select, .celebration button { padding: 10px 14px; font-size: 16px; border-radius: 5px; }
            .celebration button { margin-left: 8px; border: none; color: white; background: #6f42c1; cursor: pointer; }
            .celebration button:hover { background: #59359a; }
            #celebration-status { margin-top: 12px; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1 data-i18n="page.heading">Wall lighting mode</h1>
        <p data-i18n="page.description">Choose the lighting mode for the climbing wall.</p>
        <div>
            <button class="mode-button" id="btn-dark" onclick="setMode('dark')" data-i18n="mode.dark_button">Dark – boulder only</button>
            <button class="mode-button" id="btn-bright" onclick="setMode('bright')" data-i18n="mode.bright_button">Bright – dim unused LEDs</button>
        </div>
        <div class="brightness-control">
            <label for="bright-brightness" id="bright-brightness-label">Bright mode strength: __BRIGHT_BRIGHTNESS__%</label>
            <input id="bright-brightness" type="range" min="10" max="100" step="1" value="__BRIGHT_BRIGHTNESS__">
        </div>
        <div id="status"></div>

        <section class="celebration">
            <h2 data-i18n="celebration.heading">Send celebration</h2>
            <p data-i18n="celebration.description">Choose the effect shown on all LEDs for about 3 seconds when the gym reports climb.sent.</p>
            <div>
                <select id="celebration-effect" aria-label="Send celebration">
                    <option value="off" data-i18n="celebration.off">Off</option>
                    <option value="rainbow" data-i18n="celebration.rainbow">Moving rainbow</option>
                    <option value="fireworks" data-i18n="celebration.fireworks">Fireworks</option>
                    <option value="color_twinkles" data-i18n="celebration.color_twinkles">Color sparkles</option>
                    <option value="pride" data-i18n="celebration.pride">Rainbow party</option>
                </select>
                <button type="button" onclick="setCelebrationEffect()" data-i18n="celebration.save">Save effect</button>
            </div>
            <div id="celebration-status"></div>
        </section>

        __LANGUAGE_SWITCH__
        <script>
            const statusState = { kind: 'idle' };
            const celebrationStatusState = { kind: 'idle' };
            const celebrationSelect = document.getElementById('celebration-effect');
            const brightnessInput = document.getElementById('bright-brightness');
            celebrationSelect.value = '__CELEBRATION_EFFECT__';

            function renderBrightnessLabel() {
                document.getElementById('bright-brightness-label').textContent = window.cruxI18n.t(
                    'mode.brightness',
                    { value: brightnessInput.value },
                );
            }

            brightnessInput.addEventListener('input', renderBrightnessLabel);

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
                        body: JSON.stringify({
                            mode: mode,
                            brightness: Number(brightnessInput.value),
                        }),
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

            function renderCelebrationStatus() {
                const statusDiv = document.getElementById('celebration-status');
                const t = window.cruxI18n.t;
                if (celebrationStatusState.kind === 'saving') {
                    statusDiv.textContent = t('celebration.saving');
                } else if (celebrationStatusState.kind === 'saved') {
                    statusDiv.textContent = t('celebration.saved', {
                        effect: t(`celebration.${celebrationStatusState.effect}`),
                    });
                } else if (celebrationStatusState.kind === 'error') {
                    statusDiv.textContent = t('celebration.error', {
                        message: celebrationStatusState.message,
                    });
                }
            }

            async function setCelebrationEffect() {
                const statusDiv = document.getElementById('celebration-status');
                const effect = celebrationSelect.value;
                celebrationStatusState.kind = 'saving';
                renderCelebrationStatus();
                try {
                    const response = await fetch('__PATH_PREFIX__/celebration_effect', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ effect: effect }),
                    });
                    const result = await response.json();
                    if (!response.ok) {
                        throw new Error(result.message || window.cruxI18n.t('status.generic_error'));
                    }
                    celebrationStatusState.kind = 'saved';
                    celebrationStatusState.effect = result.effect;
                    statusDiv.style.color = 'green';
                } catch (error) {
                    celebrationStatusState.kind = 'error';
                    celebrationStatusState.message = error.message;
                    statusDiv.style.color = 'red';
                }
                renderCelebrationStatus();
            }

            window.addEventListener('crux-language-change', () => {
                renderStatus();
                renderBrightnessLabel();
                renderCelebrationStatus();
            });

            renderBrightnessLabel();
        </script>
    </body>
    </html>
    """
    return html.replace("__PATH_PREFIX__", path_prefix).replace(
        "__CELEBRATION_EFFECT__",
        celebration_effect,
    ).replace(
        "__BRIGHT_BRIGHTNESS__",
        str(bright_brightness_percent),
    ).replace(
        "__LANGUAGE_SWITCH__",
        language_switch,
    )
