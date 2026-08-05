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

# Wall Creation assigns these logical hole IDs according to the selected cable
# direction. Map each logical hole to the physical LED IDs on the cable here.
# The default is one-to-one for 400 holes. You can skip physical IDs or assign
# several LEDs to one hole, e.g. {0: [0], 1: [2, 3]} leaves LED 1 unused.
hole2LEDS = {hole_id: [hole_id] for hole_id in range(400)}
