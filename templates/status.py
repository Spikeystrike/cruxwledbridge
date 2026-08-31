import json

from templates.language import language_switch_html


TRANSLATIONS = {
    "en": {
        "page.title": "Bridge status",
        "page.heading": "Bridge status",
        "page.description": "Live diagnostics for WLED controllers, CRUX and the database. WLED tests only read device information and do not change the lights.",
        "action.refresh": "Refresh all",
        "action.test": "Test",
        "action.testing": "Testing...",
        "status.loading": "Checking systems...",
        "status.updated": "Last checked: {time}",
        "status.error": "Status could not be loaded: {message}",
        "state.online": "Online",
        "state.offline": "Offline",
        "state.unknown": "Not checked",
        "system.heading": "Bridge services",
        "system.database": "Database",
        "system.crux": "CRUX API",
        "system.lighting": "Lighting state",
        "system.response": "Response: {milliseconds} ms",
        "system.database_counts": "{walls} walls, {mappings} mappings",
        "system.crux_wall": "Live check using wall {wall}",
        "system.mode": "Mode: {mode}; route active: {route}; celebration active: {celebration}",
        "controller.heading": "WLED controllers",
        "controller.number": "Controller",
        "controller.address": "Address",
        "controller.range": "Physical LED range",
        "controller.firmware": "Firmware",
        "controller.leds": "LEDs",
        "controller.response": "Last response",
        "controller.error": "Last error",
        "controller.configured": "configured",
        "controller.reported": "reported",
        "route.heading": "Route diagnostics",
        "route.last_request": "Last route request",
        "route.last_success": "Last fully successful route",
        "route.last_error": "Last route error",
        "route.none": "No data yet",
        "route.entry": "{name} (climb {climb}, wall {wall}) — {status}, {time}",
        "boolean.yes": "yes",
        "boolean.no": "no",
    },
    "de": {
        "page.title": "Bridge-Status",
        "page.heading": "Bridge-Status",
        "page.description": "Live-Diagnose für WLED-Controller, CRUX und Datenbank. WLED-Tests lesen ausschließlich Geräteinformationen und verändern die Beleuchtung nicht.",
        "action.refresh": "Alles aktualisieren",
        "action.test": "Testen",
        "action.testing": "Test läuft ...",
        "status.loading": "Systeme werden geprüft ...",
        "status.updated": "Zuletzt geprüft: {time}",
        "status.error": "Status konnte nicht geladen werden: {message}",
        "state.online": "Online",
        "state.offline": "Offline",
        "state.unknown": "Nicht geprüft",
        "system.heading": "Bridge-Dienste",
        "system.database": "Datenbank",
        "system.crux": "CRUX-API",
        "system.lighting": "Beleuchtungszustand",
        "system.response": "Antwort: {milliseconds} ms",
        "system.database_counts": "{walls} Wände, {mappings} Zuordnungen",
        "system.crux_wall": "Live-Prüfung mit Wand {wall}",
        "system.mode": "Modus: {mode}; Route aktiv: {route}; Jubeleffekt aktiv: {celebration}",
        "controller.heading": "WLED-Controller",
        "controller.number": "Controller",
        "controller.address": "Adresse",
        "controller.range": "Physischer LED-Bereich",
        "controller.firmware": "Firmware",
        "controller.leds": "LEDs",
        "controller.response": "Letzte Antwort",
        "controller.error": "Letzter Fehler",
        "controller.configured": "konfiguriert",
        "controller.reported": "gemeldet",
        "route.heading": "Routendiagnose",
        "route.last_request": "Letzte Routenanforderung",
        "route.last_success": "Letzte vollständig erfolgreiche Route",
        "route.last_error": "Letzter Routenfehler",
        "route.none": "Noch keine Daten",
        "route.entry": "{name} (Climb {climb}, Wand {wall}) — {status}, {time}",
        "boolean.yes": "ja",
        "boolean.no": "nein",
    },
}


def return_status_html(path_prefix=""):
    data_url = json.dumps(f"{path_prefix}/status/data")
    test_url = json.dumps(f"{path_prefix}/status/wled")
    language_switch = language_switch_html(TRANSLATIONS)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title data-i18n="page.title">Bridge status</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ font-family: sans-serif; margin: 0; padding: 32px 18px 80px; background: #f4f4f9; color: #222; }}
            main {{ width: min(1100px, 100%); margin: 0 auto; }}
            h1 {{ margin-bottom: 6px; }}
            .intro {{ margin-top: 0; color: #555; line-height: 1.5; }}
            .toolbar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 14px; margin: 22px 0; }}
            button {{ padding: 9px 14px; border: 0; border-radius: 5px; background: #007bff; color: white; font-size: 15px; cursor: pointer; }}
            button:hover {{ background: #0056b3; }}
            button:disabled {{ opacity: 0.55; cursor: wait; }}
            #load-status {{ font-weight: 600; }}
            .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; }}
            .card, section.panel {{ padding: 18px; border-radius: 9px; background: white; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }}
            .card h3, section.panel h2 {{ margin-top: 0; }}
            .badge {{ display: inline-block; padding: 4px 9px; border-radius: 999px; font-weight: 700; }}
            .badge.online {{ background: #d9f5df; color: #126b25; }}
            .badge.offline {{ background: #ffe0e0; color: #9c1212; }}
            .badge.unknown {{ background: #eee; color: #555; }}
            .detail {{ color: #555; overflow-wrap: anywhere; }}
            section.panel {{ margin-top: 18px; overflow-x: auto; }}
            table {{ width: 100%; border-collapse: collapse; min-width: 850px; }}
            th, td {{ padding: 10px 8px; border-bottom: 1px solid #ddd; text-align: left; vertical-align: top; }}
            th {{ color: #444; }}
            .error {{ max-width: 260px; color: #9c1212; overflow-wrap: anywhere; }}
            .route-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
            .route-item {{ padding: 12px; border-radius: 6px; background: #f6f7fa; }}
            .route-item strong {{ display: block; margin-bottom: 7px; }}
        </style>
    </head>
    <body>
        <main>
            <h1 data-i18n="page.heading">Bridge status</h1>
            <p class="intro" data-i18n="page.description">Live diagnostics for WLED controllers, CRUX and the database. WLED tests only read device information and do not change the lights.</p>
            <div class="toolbar">
                <button id="refresh" type="button" data-i18n="action.refresh">Refresh all</button>
                <span id="load-status" role="status" aria-live="polite"></span>
            </div>

            <section class="panel">
                <h2 data-i18n="system.heading">Bridge services</h2>
                <div id="system-cards" class="cards"></div>
            </section>

            <section class="panel">
                <h2 data-i18n="controller.heading">WLED controllers</h2>
                <table>
                    <thead><tr>
                        <th data-i18n="controller.number">Controller</th>
                        <th data-i18n="controller.address">Address</th>
                        <th data-i18n="controller.range">Physical LED range</th>
                        <th data-i18n="controller.firmware">Firmware</th>
                        <th data-i18n="controller.leds">LEDs</th>
                        <th data-i18n="controller.response">Last response</th>
                        <th data-i18n="controller.error">Last error</th>
                        <th></th>
                    </tr></thead>
                    <tbody id="controller-rows"></tbody>
                </table>
            </section>

            <section class="panel">
                <h2 data-i18n="route.heading">Route diagnostics</h2>
                <div id="route-grid" class="route-grid"></div>
            </section>
        </main>
        {language_switch}
        <script>
            const dataUrl = {data_url};
            const testUrl = {test_url};
            const refreshButton = document.getElementById('refresh');
            const loadStatus = document.getElementById('load-status');
            const systemCards = document.getElementById('system-cards');
            const controllerRows = document.getElementById('controller-rows');
            const routeGrid = document.getElementById('route-grid');
            let currentData = null;

            function t(key, replacements = {{}}) {{ return window.cruxI18n.t(key, replacements); }}
            function localTime(value) {{
                if (!value) return '—';
                const date = new Date(value);
                return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
            }}
            function stateName(value) {{
                if (value === true) return t('state.online');
                if (value === false) return t('state.offline');
                return t('state.unknown');
            }}
            function badge(value) {{
                const span = document.createElement('span');
                span.className = `badge ${{value === true ? 'online' : value === false ? 'offline' : 'unknown'}}`;
                span.textContent = stateName(value);
                return span;
            }}
            function detail(text) {{
                const p = document.createElement('p');
                p.className = 'detail';
                p.textContent = text;
                return p;
            }}
            function serviceCard(title, state, details) {{
                const card = document.createElement('article');
                card.className = 'card';
                const heading = document.createElement('h3');
                heading.textContent = title;
                card.append(heading, badge(state));
                details.filter(Boolean).forEach((item) => card.appendChild(detail(item)));
                return card;
            }}
            function renderSystems() {{
                systemCards.replaceChildren();
                const database = currentData.database || {{}};
                systemCards.appendChild(serviceCard(t('system.database'), database.reachable, [
                    database.response_ms != null ? t('system.response', {{ milliseconds: database.response_ms }}) : '',
                    database.wall_count != null ? t('system.database_counts', {{ walls: database.wall_count, mappings: database.mapping_count }}) : database.error,
                ]));
                const crux = currentData.crux_api || {{}};
                systemCards.appendChild(serviceCard(t('system.crux'), crux.reachable, [
                    crux.response_ms != null ? t('system.response', {{ milliseconds: crux.response_ms }}) : '',
                    crux.wall_id != null ? t('system.crux_wall', {{ wall: crux.wall_id }}) : crux.message,
                    crux.error,
                ]));
                const lighting = currentData.lighting || {{}};
                systemCards.appendChild(serviceCard(t('system.lighting'), true, [
                    t('system.mode', {{
                        mode: lighting.mode || '—',
                        route: t(lighting.route_active ? 'boolean.yes' : 'boolean.no'),
                        celebration: t(lighting.celebration_active ? 'boolean.yes' : 'boolean.no'),
                    }}),
                ]));
            }}
            function renderControllers() {{
                controllerRows.replaceChildren();
                (currentData.wled_controllers || []).forEach((controller) => {{
                    const row = document.createElement('tr');
                    const values = [
                        String(controller.index + 1),
                        controller.address,
                        `${{controller.start}}–${{controller.end}}`,
                        controller.firmware_version || '—',
                        `${{controller.configured_led_count}} ${{t('controller.configured')}} / ${{controller.reported_led_count ?? '—'}} ${{t('controller.reported')}}`,
                        controller.last_response_ms != null ? `${{controller.last_response_ms}} ms / ${{localTime(controller.last_checked_at)}}` : '—',
                    ];
                    values.forEach((value, index) => {{
                        const cell = document.createElement('td');
                        if (index === 0) {{ cell.append(document.createTextNode(`${{value}} `), badge(controller.reachable)); }}
                        else cell.textContent = value;
                        row.appendChild(cell);
                    }});
                    const errorCell = document.createElement('td');
                    errorCell.className = 'error';
                    errorCell.textContent = controller.last_error || '—';
                    row.appendChild(errorCell);
                    const actionCell = document.createElement('td');
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.textContent = t('action.test');
                    button.addEventListener('click', () => testController(controller.index, button));
                    actionCell.appendChild(button);
                    row.appendChild(actionCell);
                    controllerRows.appendChild(row);
                }});
            }}
            function renderRouteItem(labelKey, route) {{
                const item = document.createElement('div');
                item.className = 'route-item';
                const label = document.createElement('strong');
                label.textContent = t(labelKey);
                const value = document.createElement('span');
                value.textContent = route ? t('route.entry', {{
                    name: route.climb_name,
                    climb: route.climb_id,
                    wall: route.wall_id,
                    status: route.status,
                    time: localTime(route.timestamp),
                }}) + (route.error ? ` — ${{route.error}}` : '') : t('route.none');
                item.append(label, value);
                return item;
            }}
            function renderRoutes() {{
                routeGrid.replaceChildren();
                const routes = currentData.route_diagnostics || {{}};
                routeGrid.append(
                    renderRouteItem('route.last_request', routes.last_route_request),
                    renderRouteItem('route.last_success', routes.last_successful_route),
                    renderRouteItem('route.last_error', routes.last_route_error),
                );
            }}
            function render() {{ renderSystems(); renderControllers(); renderRoutes(); }}
            async function loadAll() {{
                refreshButton.disabled = true;
                loadStatus.textContent = t('status.loading');
                try {{
                    const response = await fetch(dataUrl);
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.detail || `HTTP ${{response.status}}`);
                    currentData = data;
                    render();
                    loadStatus.textContent = t('status.updated', {{ time: localTime(data.checked_at) }});
                }} catch (error) {{
                    loadStatus.textContent = t('status.error', {{ message: error.message }});
                }} finally {{
                    refreshButton.disabled = false;
                }}
            }}
            async function testController(index, button) {{
                button.disabled = true;
                button.textContent = t('action.testing');
                try {{
                    const response = await fetch(`${{testUrl}}/${{index}}/test`, {{ method: 'POST' }});
                    const controller = await response.json();
                    if (!response.ok) throw new Error(controller.detail || `HTTP ${{response.status}}`);
                    const position = currentData.wled_controllers.findIndex((item) => item.index === index);
                    if (position >= 0) currentData.wled_controllers[position] = controller;
                    renderControllers();
                }} catch (error) {{
                    loadStatus.textContent = t('status.error', {{ message: error.message }});
                }} finally {{
                    button.disabled = false;
                    button.textContent = t('action.test');
                }}
            }}
            refreshButton.addEventListener('click', loadAll);
            window.addEventListener('crux-language-change', () => {{ if (currentData) render(); }});
            loadAll();
        </script>
    </body>
    </html>
    """
