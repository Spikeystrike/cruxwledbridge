from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "CRUX WLED Bridge",
        "page.heading": "CRUX WLED Bridge",
        "page.description": "Choose what you want to configure.",
        "wall.heading": "Wall setup",
        "wall.description": "Select a wall from your CRUX gym and map its holds to the physical LEDs.",
        "wall.gym_label": "Gym slug",
        "wall.gym_placeholder": "for example my-climbing-gym",
        "wall.open": "Open wall selection",
        "lighting.heading": "Wall lighting",
        "lighting.description": "Switch between dark and bright wall lighting and configure the celebration shown after a sent climb.",
        "lighting.open": "Open lighting settings",
    },
    "de": {
        "page.title": "CRUX WLED Bridge",
        "page.heading": "CRUX WLED Bridge",
        "page.description": "Wähle aus, was du konfigurieren möchtest.",
        "wall.heading": "Wand einrichten",
        "wall.description": "Wähle eine Wand aus deiner CRUX-Halle und ordne ihre Griffe den physischen LEDs zu.",
        "wall.gym_label": "Gym-Slug",
        "wall.gym_placeholder": "zum Beispiel meine-kletterhalle",
        "wall.open": "Wandauswahl öffnen",
        "lighting.heading": "Wandbeleuchtung",
        "lighting.description": "Wechsle zwischen dunkler und heller Wandbeleuchtung und konfiguriere den Jubeleffekt nach einem Top.",
        "lighting.open": "Beleuchtungseinstellungen öffnen",
    },
}


def return_overview_html(path_prefix=""):
    language_switch = language_switch_html(TRANSLATIONS)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title data-i18n="page.title">CRUX WLED Bridge</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: sans-serif;
                margin: 0;
                padding: 48px 20px;
                background: #f4f4f9;
                color: #222;
            }}
            main {{ max-width: 820px; margin: 0 auto; }}
            h1 {{ margin-bottom: 8px; }}
            .intro {{ margin-top: 0; color: #555; }}
            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-top: 32px;
            }}
            .card {{
                background: white;
                border-radius: 10px;
                padding: 24px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }}
            .card h2 {{ margin-top: 0; }}
            .card p {{ line-height: 1.5; color: #444; }}
            label {{ display: block; font-weight: bold; margin: 20px 0 6px; }}
            input {{
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #bbb;
                border-radius: 5px;
                font-size: 16px;
            }}
            .button {{
                display: inline-block;
                margin-top: 14px;
                padding: 11px 16px;
                border: 0;
                border-radius: 5px;
                background: #007bff;
                color: white;
                text-decoration: none;
                font-size: 16px;
                cursor: pointer;
            }}
            .button:hover {{ background: #0056b3; }}
        </style>
    </head>
    <body>
        <main>
            <h1 data-i18n="page.heading">CRUX WLED Bridge</h1>
            <p class="intro" data-i18n="page.description">Choose what you want to configure.</p>
            <div class="cards">
                <section class="card">
                    <h2 data-i18n="wall.heading">Wall setup</h2>
                    <p data-i18n="wall.description">Select a wall from your CRUX gym and map its holds to the physical LEDs.</p>
                    <form action="{path_prefix}/listwalls" method="get">
                        <label for="gym" data-i18n="wall.gym_label">Gym slug</label>
                        <input id="gym" name="gym" type="text" required
                               placeholder="for example my-climbing-gym"
                               data-i18n-placeholder="wall.gym_placeholder">
                        <button class="button" type="submit" data-i18n="wall.open">Open wall selection</button>
                    </form>
                </section>
                <section class="card">
                    <h2 data-i18n="lighting.heading">Wall lighting</h2>
                    <p data-i18n="lighting.description">Switch between dark and bright wall lighting and configure the celebration shown after a sent climb.</p>
                    <a class="button" href="{path_prefix}/wall_lighting" data-i18n="lighting.open">Open lighting settings</a>
                </section>
            </div>
        </main>
        {language_switch}
    </body>
    </html>
    """
