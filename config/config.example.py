# Copy this file to config.py and set your Crux app token locally.
token = ""

# WLED controllers and their inclusive ranges in the bridge's global LED IDs.
# The controller receives zero-based local LED IDs through WLED's JSON API.
wled_controllers = [
    {
        "ip": "192.0.2.10",
        "start": 0,
        "end": 399,
    },
]

# Color codes in HEX without # that will be used for the LEDS
colors = {
    "hand": "0000FF",
    "hand_l": "ffee00",
    "hand_r": "99ff00",
    "foot": "00ff00",
    "foot_l": "00ff9d",
    "foot_r": "00fbff",
    "start": "FF0000",
    "finish": "FF0000",
    "zone": "a64d79",
}

# Crux holds are stored in app.db as <wall_id>_<hold_id>. This mapping is the
# next step: logical grid LED ID -> physical LED IDs. Lists allow multiple LEDs
# per hold. For a 20x20 wall with exactly one physical LED per hold, use 1:1 IDs.
hole2LEDS = {led_id: [led_id] for led_id in range(400)}
