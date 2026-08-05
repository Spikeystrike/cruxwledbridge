import requests
import numpy as np
from config import config


def wall_hold_key(wall_id, hold_id):
    """Return the database key for a hold on a specific wall."""
    return f"{wall_id}_{hold_id}"


def _wled_controllers():
    controllers = getattr(config, "wled_controllers", None)
    if not controllers:
        raise ValueError("config.wled_controllers must contain at least one controller")

    normalized = []
    for controller in controllers:
        ip = controller["ip"].strip().rstrip("/")
        start = int(controller["start"])
        end = int(controller["end"])
        if start < 0 or end < start:
            raise ValueError(f"Invalid WLED LED range: {start}-{end}")

        if not ip.startswith(("http://", "https://")):
            ip = f"http://{ip}"
        normalized.append({
            "url": f"{ip}/json/state",
            "start": start,
            "end": end,
        })

    controllers_by_start = sorted(normalized, key=lambda item: item["start"])
    for previous, current in zip(controllers_by_start, controllers_by_start[1:]):
        if current["start"] <= previous["end"]:
            raise ValueError("WLED LED ranges must not overlap")

    return normalized


def _turn_off(controller):
    return requests.post(
        controller["url"],
        json={"on": False, "bri": 255},
    )


def generate_grid(lu, ru, rb, lb, r, c, alternating=False):
    if r < 1 or c < 1:
        raise ValueError("Grid rows and columns must be positive")
    if alternating and (c < 2 or c % 2 != 0):
        raise ValueError("Alternating grids require an even number of columns")

    grid = {}  # Dictionary zur Speicherung der Punkte, Schlüssel ist die ID
    # Interpolate die Positionen für alle Reihen (von links oben nach links unten und rechts oben nach rechts unten)
    for i in range(r):
        # Division durch Null vermeiden, wenn es nur eine Reihe gibt
        t = i / (r - 1) if r > 1 else 0.0
        left_point = (1 - t) * np.array(lu) + t * np.array(lb)  # Position entlang der linken Seite
        right_point = (1 - t) * np.array(ru) + t * np.array(rb)  # Position entlang der rechten Seite

        # Reihe von unten gezählt (0-basiert)
        row_from_bottom = r - 1 - i

        # Im alternierenden Raster verwendet die oberste Reihe die Spalten
        # 0, 2, 4, ... und die nächste Reihe 1, 3, 5, ... . Bei z. B. 22
        # möglichen Spalten bleiben so genau 11 Punkte pro Reihe übrig.
        column_indices = range(i % 2, c, 2) if alternating else range(c)
        active_columns = len(column_indices)

        # Interpolate die Punkte innerhalb der aktuellen Reihe (von links nach rechts)
        for active_column, j in enumerate(column_indices):
            # Division durch Null vermeiden, wenn es nur eine Spalte gibt
            s = j / (c - 1) if c > 1 else 0.0
            point = np.rint((1 - s) * left_point + s * right_point).astype(int)  # Position entlang der aktuellen Zeile

            # Berechne die ID in "Schlangenlinien"-Form von unten
            if (row_from_bottom % 2) == 1:  # Ungerade Reihen von unten (1, 3, ...): von links nach rechts
                led_id = (row_from_bottom * active_columns) + active_column
            else:  # Gerade Reihen von unten (0, 2, ...): von rechts nach links
                led_id = (
                    row_from_bottom * active_columns
                    + (active_columns - 1 - active_column)
                )
            
            grid[led_id] = (point[0].item(), point[1].item())
    return grid


def ledCalculation(lr, ll, ur, ul, c, r, holds, grid):
    holds2led = {}
    for hold in holds:
        # calculate center
        mask_points = np.array(hold["mask"])
        center = np.mean(mask_points, axis=0).astype(int)  # Compute the center (x, y)
        
        # Find the nearest grid point
        nearest_grid_id = min(grid, key=lambda gid: np.linalg.norm(np.array(grid[gid]) - center))

        # Map the hold ID to the nearest grid ID
        holds2led[hold["id"]] = nearest_grid_id
    return holds2led


def sendLightToBoulderwall(holds, mode="dark"):
    colors = config.colors
    hole2LEDS = config.hole2LEDS
    led = {}
    for hold in holds:
        for hled in hole2LEDS[hold]:
            led[hled] =  colors[holds[hold]]

    controllers = _wled_controllers()
    for controller in controllers:
        _turn_off(controller)

        pixels = []
        for global_led_id in range(controller["start"], controller["end"] + 1):
            color = led.get(global_led_id)
            if color is None and mode == "bright":
                color = "333333"
            if color is not None:
                pixels.extend([global_led_id - controller["start"], color])

        if pixels:
            requests.post(
                controller["url"],
                json={"on": True, "bri": 255, "seg": {"i": pixels}},
            )
    return led


def lightUpHoldId(holdid, color):
    controllers = _wled_controllers()
    for controller in controllers:
        _turn_off(controller)

    for controller in controllers:
        if controller["start"] <= holdid <= controller["end"]:
            local_led_id = holdid - controller["start"]
            return requests.post(
                controller["url"],
                json={
                    "on": True,
                    "bri": 255,
                    "seg": {"i": [local_led_id, color]},
                },
            )

    raise ValueError(f"LED ID {holdid} is not assigned to a WLED controller")
