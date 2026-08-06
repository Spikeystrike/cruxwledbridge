import requests
import numpy as np
from config import config


CELEBRATION_EFFECTS = {
    "rainbow": {"fx": 9, "sx": 180, "ix": 180},
    "fireworks": {"fx": 42, "sx": 180, "ix": 220},
    "color_twinkles": {"fx": 74, "sx": 170, "ix": 220},
    "pride": {"fx": 63, "sx": 170, "ix": 190},
}


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


def generate_grid(
    lu,
    ru,
    rb,
    lb,
    r,
    c,
    alternating=False,
    alternating_start_column=0,
    led_start_corner="bottom_left",
    led_direction="vertical",
):
    if r < 1 or c < 1:
        raise ValueError("Grid rows and columns must be positive")
    if alternating and c < 2:
        raise ValueError("Alternating grids require at least two columns")
    if alternating_start_column not in (0, 1):
        raise ValueError("Alternating grid start column must be 0 or 1")
    if led_start_corner not in {"top_left", "top_right", "bottom_left", "bottom_right"}:
        raise ValueError("LED start corner must be top_left, top_right, bottom_left, or bottom_right")
    if led_direction not in {"horizontal", "vertical"}:
        raise ValueError("LED direction must be horizontal or vertical")

    row_columns = []
    for row_from_top in range(r):
        if alternating:
            first_column = (alternating_start_column + row_from_top) % 2
            row_columns.append(list(range(first_column, c, 2)))
        else:
            row_columns.append(list(range(c)))

    positions = {}
    # Interpolate die Positionen für alle Reihen (von links oben nach links unten und rechts oben nach rechts unten)
    for i in range(r):
        # Division durch Null vermeiden, wenn es nur eine Reihe gibt
        t = i / (r - 1) if r > 1 else 0.0
        left_point = (1 - t) * np.array(lu) + t * np.array(lb)  # Position entlang der linken Seite
        right_point = (1 - t) * np.array(ru) + t * np.array(rb)  # Position entlang der rechten Seite

        # Im alternierenden Raster wechseln die verwendeten Spalten je Reihe.
        # Bei ungeradem C darf sich deshalb die Anzahl aktiver Punkte je Reihe
        # um eins unterscheiden.
        column_indices = row_columns[i]
        # Interpolate die Punkte innerhalb der aktuellen Reihe (von links nach rechts)
        for j in column_indices:
            # Division durch Null vermeiden, wenn es nur eine Spalte gibt
            s = j / (c - 1) if c > 1 else 0.0
            point = np.rint((1 - s) * left_point + s * right_point).astype(int)  # Position entlang der aktuellen Zeile

            positions[(i, j)] = (point[0].item(), point[1].item())

    starts_top = led_start_corner.startswith("top_")
    starts_left = led_start_corner.endswith("_left")

    # Sort the logical positions in physical cable order. The direction selects
    # whether the cable snakes through rows or columns; the chosen corner fixes
    # both LED 0 and the direction of the first run.
    if led_direction == "horizontal":
        stripes = sorted({row for row, _ in positions}, reverse=not starts_top)
        stripe_positions = lambda stripe: [(row, column) for row, column in positions if row == stripe]
        first_run_ascending = starts_left
        sort_axis = lambda position: position[1]
    else:
        stripes = sorted({column for _, column in positions}, reverse=not starts_left)
        stripe_positions = lambda stripe: [(row, column) for row, column in positions if column == stripe]
        first_run_ascending = starts_top
        sort_axis = lambda position: position[0]

    cable_order = []
    for stripe_index, stripe in enumerate(stripes):
        ascending = first_run_ascending if stripe_index % 2 == 0 else not first_run_ascending
        cable_order.extend(
            sorted(stripe_positions(stripe), key=sort_axis, reverse=not ascending)
        )

    grid = {
        led_id: positions[position]
        for led_id, position in enumerate(cable_order)
    }
    return grid


def ledCalculation(holds, full_grid, position_led_ids):
    holds2led = {}
    for hold in holds:
        # calculate center
        mask_points = np.array(hold["mask"])
        center = np.mean(mask_points, axis=0).astype(int)  # Compute the center (x, y)

        # Match against every physical grid position first. Otherwise a hold at
        # an excluded position would be moved to the nearest active position.
        nearest_position_id = min(
            full_grid,
            key=lambda position_id: np.linalg.norm(
                np.array(full_grid[position_id]) - center
            ),
        )

        # Excluded positions are intentionally absent from position_led_ids.
        # Active positions map to their contiguous logical hole ID.
        logical_hole_id = position_led_ids.get(nearest_position_id)
        if logical_hole_id is not None:
            holds2led[hold["id"]] = logical_hole_id
    return holds2led


def sendLightToBoulderwall(holds, mode="dark"):
    colors = config.colors
    hole2LEDS = config.hole2LEDS
    led = {}
    for hole_id, hold_type in holds.items():
        for physical_led_id in hole2LEDS[hole_id]:
            led[physical_led_id] = colors[hold_type]

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
                # Explicitly return the segment to Solid. A celebration may
                # have left a WLED effect active before this state is restored.
                json={"on": True, "bri": 255, "seg": {"fx": 0, "i": pixels}},
            )
    return led


def playCelebrationEffect(effect):
    """Run a native WLED effect over the complete range of every controller."""
    settings = CELEBRATION_EFFECTS.get(effect)
    if settings is None:
        raise ValueError(f"Unknown celebration effect: {effect}")

    for controller in _wled_controllers():
        led_count = controller["end"] - controller["start"] + 1
        # Boulder rendering uses WLED's individual LED control, which freezes
        # the segment. Wake the controller first, then explicitly unfreeze the
        # segment before selecting an effect. Keeping these as two requests also
        # makes effect startup reliable when the controller was previously off.
        requests.post(
            controller["url"],
            json={"on": True, "bri": 255, "tt": 0},
            timeout=2,
        )
        requests.post(
            controller["url"],
            json={
                "seg": {
                    "id": 0,
                    "start": 0,
                    "stop": led_count,
                    "on": True,
                    "bri": 255,
                    "frz": False,
                    **settings,
                },
            },
            timeout=2,
        )


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
