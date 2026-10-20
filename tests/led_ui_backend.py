"""Line-based calculation adapter for the UI test, with no HTTP or hardware."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_led_layout import settings_fixture, layout_fixture
from led_layout import calculate_layout, derive_led_grid
settings = settings_fixture()
saved = layout_fixture()
for line in sys.stdin:
    try:
        request = json.loads(line)
        if request.get('mode'):
            result = {'grid': derive_led_grid(settings, request['grid_id'], request['mode'], request['offset_rows']),
                      'coordinate_width': 500, 'coordinate_height': 500}
        elif request.get('refresh'):
            result = {'grip_grids': settings['grids'], 'coordinate_width': 500, 'coordinate_height': 500, 'layout': saved}
        elif request.get('action') == 'deactivate':
            result = {'active': False}
        else:
            result = {**calculate_layout(settings, request['layout']), 'active': request['action'] == 'activate', 'unconfigured_led_ids': []}
            if request['action'] in ('activate', 'draft'):
                saved = request['layout']
        print(json.dumps({'ok': True, 'data': result}), flush=True)
    except Exception as exc:
        print(json.dumps({'ok': False, 'data': {'detail': str(exc)}}), flush=True)
