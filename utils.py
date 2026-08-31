import copy
import logging
import threading
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

import requests
import numpy as np
from config_loader import config


CELEBRATION_EFFECTS = {
    "rainbow": {"fx": 9, "sx": 180, "ix": 180},
    "fireworks": {"fx": 42, "sx": 180, "ix": 220},
    "color_twinkles": {"fx": 74, "sx": 170, "ix": 220},
    "pride": {"fx": 63, "sx": 170, "ix": 190},
}

logger = logging.getLogger("cruxwledbridge.wled")
_wled_status_lock = threading.Lock()
_wled_status = {}
_last_wled_operation = None


class LightingResult(dict):
    """Existing LED mapping result plus a non-serialized operation report."""

    def __init__(self, values, operation):
        super().__init__(values)
        self.operation = operation


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wled_request_timeout():
    try:
        timeout = float(getattr(config, "wled_request_timeout_seconds", 2.0))
    except (TypeError, ValueError):
        timeout = 2.0
    return timeout if timeout > 0 else 2.0


def _controller_identity(controller):
    return controller["base_url"]


def _controller_details(controller, index=None):
    details = {
        "index": index,
        "address": controller["base_url"],
        "start": controller["start"],
        "end": controller["end"],
        "configured_led_count": controller["end"] - controller["start"] + 1,
    }
    with _wled_status_lock:
        details.update(copy.deepcopy(
            _wled_status.get(_controller_identity(controller), {})
        ))
    return details


def _record_wled_success(controller, elapsed_ms, info=None):
    checked_at = _utc_now()
    update = {
        "reachable": True,
        "last_checked_at": checked_at,
        "last_success_at": checked_at,
        "last_response_ms": round(elapsed_ms, 1),
        "last_error": None,
    }
    if isinstance(info, dict):
        update["firmware_version"] = info.get("ver")
        update["device_name"] = info.get("name")
        leds = info.get("leds")
        if isinstance(leds, dict):
            update["reported_led_count"] = leds.get("count")
    with _wled_status_lock:
        _wled_status.setdefault(_controller_identity(controller), {}).update(update)


def _record_wled_failure(controller, error, elapsed_ms):
    checked_at = _utc_now()
    update = {
        "reachable": False,
        "last_checked_at": checked_at,
        "last_error_at": checked_at,
        "last_response_ms": round(elapsed_ms, 1),
        "last_error": str(error),
    }
    with _wled_status_lock:
        _wled_status.setdefault(_controller_identity(controller), {}).update(update)


def _request_wled(controller, method, url, *, action, json=None):
    started = time.monotonic()
    try:
        if method == "POST":
            response = requests.post(
                url,
                json=json,
                timeout=_wled_request_timeout(),
            )
        else:
            response = requests.get(url, timeout=_wled_request_timeout())
        response.raise_for_status()
    except (requests.RequestException, ValueError, TypeError) as exc:
        elapsed_ms = (time.monotonic() - started) * 1000
        _record_wled_failure(controller, exc, elapsed_ms)
        logger.warning(
            "WLED %s failed for %s (LEDs %s-%s): %s",
            action,
            controller["base_url"],
            controller["start"],
            controller["end"],
            exc,
        )
        return None

    elapsed_ms = (time.monotonic() - started) * 1000
    _record_wled_success(controller, elapsed_ms)
    return response


def _finish_wled_operation(kind, controller_results):
    global _last_wled_operation
    successful = [result for result in controller_results if result["success"]]
    failed = [result for result in controller_results if not result["success"]]
    if failed and successful:
        status = "partial"
    elif failed:
        status = "failed"
    else:
        status = "ok"
    report = {
        "kind": kind,
        "status": status,
        "finished_at": _utc_now(),
        "successful_controllers": successful,
        "failed_controllers": failed,
    }
    with _wled_status_lock:
        _last_wled_operation = copy.deepcopy(report)
    return report


def get_last_wled_operation():
    with _wled_status_lock:
        return copy.deepcopy(_last_wled_operation)


def get_wled_status_snapshot():
    return [
        _controller_details(controller, index)
        for index, controller in enumerate(_wled_controllers())
    ]


def probe_wled_controller(index):
    controllers = _wled_controllers()
    if index < 0 or index >= len(controllers):
        raise ValueError(f"Unknown WLED controller index: {index}")
    controller = controllers[index]
    started = time.monotonic()
    try:
        response = requests.get(
            f"{controller['base_url']}/json/info",
            timeout=_wled_request_timeout(),
        )
        response.raise_for_status()
        info = response.json()
        if not isinstance(info, dict):
            raise ValueError("WLED returned invalid /json/info data")
    except (requests.RequestException, ValueError, TypeError) as exc:
        elapsed_ms = (time.monotonic() - started) * 1000
        _record_wled_failure(controller, exc, elapsed_ms)
        logger.warning("WLED status check failed for %s: %s", controller["base_url"], exc)
    else:
        elapsed_ms = (time.monotonic() - started) * 1000
        _record_wled_success(controller, elapsed_ms, info)
    return _controller_details(controller, index)


def probe_all_wled_controllers():
    controller_count = len(_wled_controllers())
    with ThreadPoolExecutor(max_workers=controller_count) as executor:
        return list(executor.map(probe_wled_controller, range(controller_count)))


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
            "base_url": ip,
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
    return _request_wled(
        controller,
        "POST",
        controller["url"],
        action="switch-off",
        json={"on": False, "bri": 255},
    )


def _grid_homography(lu, ru, rb, lb):
    """Map a normalized rectangle onto the four selected image points."""
    source_points = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    destination_points = np.asarray((lu, ru, rb, lb), dtype=float)
    if destination_points.shape != (4, 2) or not np.isfinite(destination_points).all():
        raise ValueError("Grid corners must contain four finite x/y coordinates")

    equations = []
    targets = []
    for (s, t), (x, y) in zip(source_points, destination_points):
        equations.append((s, t, 1.0, 0.0, 0.0, 0.0, -s * x, -t * x))
        targets.append(x)
        equations.append((0.0, 0.0, 0.0, s, t, 1.0, -s * y, -t * y))
        targets.append(y)

    coefficients = np.linalg.solve(
        np.asarray(equations, dtype=float),
        np.asarray(targets, dtype=float),
    )
    transform = np.append(coefficients, 1.0).reshape(3, 3)
    if np.linalg.matrix_rank(transform) < 3:
        raise ValueError("Grid corners must define a non-degenerate quadrilateral")
    return transform


def _project_grid_point(transform, s, t):
    projected = transform @ np.asarray((s, t, 1.0), dtype=float)
    if np.isclose(projected[2], 0.0):
        raise ValueError("Grid corners produce a point at infinity")
    point = np.rint(projected[:2] / projected[2]).astype(int)
    return point[0].item(), point[1].item()


def _validate_grid_layout(
    r,
    c,
    alternating,
    alternating_start_column,
    led_start_corner,
    led_direction,
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


def _grid_row_columns(r, c, alternating, alternating_start_column):
    row_columns = []
    for row_from_top in range(r):
        if alternating:
            first_column = (alternating_start_column + row_from_top) % 2
            row_columns.append(list(range(first_column, c, 2)))
        else:
            row_columns.append(list(range(c)))
    return row_columns


def _grid_cable_order(positions, led_start_corner, led_direction):
    positions = set(positions)
    starts_top = led_start_corner.startswith("top_")
    starts_left = led_start_corner.endswith("_left")

    if led_direction == "horizontal":
        stripes = sorted({row for row, _ in positions}, reverse=not starts_top)
        stripe_positions = lambda stripe: [
            (row, column) for row, column in positions if row == stripe
        ]
        first_run_ascending = starts_left
        sort_axis = lambda position: position[1]
    else:
        stripes = sorted({column for _, column in positions}, reverse=not starts_left)
        stripe_positions = lambda stripe: [
            (row, column) for row, column in positions if column == stripe
        ]
        first_run_ascending = starts_top
        sort_axis = lambda position: position[0]

    cable_order = []
    for stripe_index, stripe in enumerate(stripes):
        ascending = first_run_ascending if stripe_index % 2 == 0 else not first_run_ascending
        cable_order.extend(
            sorted(stripe_positions(stripe), key=sort_axis, reverse=not ascending)
        )
    return cable_order


def generate_grid_position_layout(
    r,
    c,
    alternating=False,
    alternating_start_column=0,
    led_start_corner="bottom_left",
    led_direction="vertical",
):
    """Return each cable-order position ID's structural row and column."""
    _validate_grid_layout(
        r,
        c,
        alternating,
        alternating_start_column,
        led_start_corner,
        led_direction,
    )
    row_columns = _grid_row_columns(r, c, alternating, alternating_start_column)
    positions = {
        (row, column)
        for row, columns in enumerate(row_columns)
        for column in columns
    }
    return {
        position_id: position
        for position_id, position in enumerate(
            _grid_cable_order(positions, led_start_corner, led_direction)
        )
    }


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
    _validate_grid_layout(
        r,
        c,
        alternating,
        alternating_start_column,
        led_start_corner,
        led_direction,
    )
    row_columns = _grid_row_columns(r, c, alternating, alternating_start_column)

    try:
        transform = _grid_homography(lu, ru, rb, lb)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Grid corners must define a non-degenerate quadrilateral"
        ) from exc

    positions = {}
    for i in range(r):
        t = i / (r - 1) if r > 1 else 0.0

        # Im alternierenden Raster wechseln die verwendeten Spalten je Reihe.
        # Bei ungeradem C darf sich deshalb die Anzahl aktiver Punkte je Reihe
        # um eins unterscheiden.
        column_indices = row_columns[i]
        for j in column_indices:
            s = j / (c - 1) if c > 1 else 0.0
            positions[(i, j)] = _project_grid_point(transform, s, t)

    # Sort the logical positions in physical cable order. The direction selects
    # whether the cable snakes through rows or columns; the chosen corner fixes
    # both LED 0 and the direction of the first run.
    cable_order = _grid_cable_order(
        positions,
        led_start_corner,
        led_direction,
    )

    grid = {
        led_id: positions[position]
        for led_id, position in enumerate(cable_order)
    }
    return grid


def positions_near_holds(holds, grids, proximity_ratio=0.45):
    """Return grid positions that have a CRUX hold at or near them.

    The tolerance follows the local grid spacing so the heuristic keeps
    working for differently sized and perspective-distorted wall images.
    Each hold is assigned to at most one position across all grids.
    """
    flattened_positions = {
        (grid_index, position_id): np.asarray(coordinates, dtype=float)
        for grid_index, grid in enumerate(grids)
        for position_id, coordinates in grid.items()
    }
    if not flattened_positions:
        return set()

    local_spacings = {}
    for (grid_index, position_id), point in flattened_positions.items():
        neighbour_distances = sorted(
            distance
            for (other_grid_index, other_position_id), other_point
            in flattened_positions.items()
            if other_grid_index == grid_index
            and other_position_id != position_id
            and (distance := np.linalg.norm(other_point - point)) > 0
        )
        local_spacings[(grid_index, position_id)] = (
            float(np.median(neighbour_distances[:4]))
            if neighbour_distances
            else 0.0
        )

    occupied_positions = set()
    for hold in holds or []:
        mask_points = np.asarray(hold.get("mask", []), dtype=float)
        if (
            mask_points.ndim != 2
            or mask_points.shape[0] == 0
            or mask_points.shape[1] != 2
            or not np.isfinite(mask_points).all()
        ):
            continue

        center = np.mean(mask_points, axis=0)
        nearest_position = min(
            flattened_positions,
            key=lambda key: np.linalg.norm(flattened_positions[key] - center),
        )
        distance = np.linalg.norm(flattened_positions[nearest_position] - center)
        hold_radius = max(
            (np.linalg.norm(mask_point - center) for mask_point in mask_points),
            default=0.0,
        )
        tolerance = max(
            local_spacings[nearest_position] * proximity_ratio,
            hold_radius,
        )
        if distance <= tolerance:
            occupied_positions.add(nearest_position)

    return occupied_positions


def map_virtual_grid_to_physical_leds(
    virtual_grid,
    saved_settings,
    hole2leds,
    target_width=None,
    target_height=None,
):
    """Match virtual cable-order positions to physical LEDs across all grids."""
    if not isinstance(saved_settings, dict):
        raise ValueError("A saved wall mapping is required")

    saved_grids = saved_settings.get("grids")
    if not isinstance(saved_grids, list) or not saved_grids:
        saved_grids = [saved_settings]

    source_width = saved_settings.get("coordinate_width") or target_width
    source_height = saved_settings.get("coordinate_height") or target_height
    try:
        scale_x = (
            float(target_width) / float(source_width)
            if target_width and source_width
            else 1.0
        )
        scale_y = (
            float(target_height) / float(source_height)
            if target_height and source_height
            else 1.0
        )
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ValueError("Wall mapping coordinate dimensions are invalid") from exc

    active_positions = []
    for saved_grid in saved_grids:
        if not isinstance(saved_grid, dict):
            continue
        positions = saved_grid.get("positions", {})
        position_led_ids = saved_grid.get("position_led_ids", {})
        if not isinstance(positions, dict) or not isinstance(position_led_ids, dict):
            continue

        for raw_position_id, raw_logical_led_id in position_led_ids.items():
            coordinates = positions.get(raw_position_id)
            if coordinates is None:
                coordinates = positions.get(str(raw_position_id))
            if coordinates is None:
                try:
                    coordinates = positions.get(int(raw_position_id))
                except (TypeError, ValueError):
                    coordinates = None
            try:
                x, y = coordinates
                logical_led_id = int(raw_logical_led_id)
                x = float(x) * scale_x
                y = float(y) * scale_y
            except (TypeError, ValueError):
                continue
            if not np.isfinite((x, y)).all():
                continue
            active_positions.append((logical_led_id, x, y))

    if not active_positions:
        raise ValueError("The saved wall mapping has no active LED positions")
    if not isinstance(virtual_grid, dict) or not virtual_grid:
        raise ValueError("The virtual grid has no positions")

    matches = []
    flattened_physical_led_ids = []
    for virtual_position_id in sorted(virtual_grid):
        try:
            virtual_x, virtual_y = virtual_grid[virtual_position_id]
            virtual_x = float(virtual_x)
            virtual_y = float(virtual_y)
        except (TypeError, ValueError) as exc:
            raise ValueError("The virtual grid contains invalid coordinates") from exc

        logical_led_id, source_x, source_y = min(
            active_positions,
            key=lambda position: (
                (position[1] - virtual_x) ** 2
                + (position[2] - virtual_y) ** 2,
                position[0],
            ),
        )
        physical_led_ids = hole2leds.get(logical_led_id)
        if physical_led_ids is None:
            physical_led_ids = hole2leds.get(str(logical_led_id))
        if isinstance(physical_led_ids, int):
            physical_led_ids = [physical_led_ids]
        if not isinstance(physical_led_ids, (list, tuple)) or not physical_led_ids:
            raise ValueError(
                f"Logical LED {logical_led_id} has no physical hole2LEDS mapping"
            )
        try:
            physical_led_ids = [int(led_id) for led_id in physical_led_ids]
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Logical LED {logical_led_id} has an invalid hole2LEDS mapping"
            ) from exc

        distance = float(np.hypot(source_x - virtual_x, source_y - virtual_y))
        flattened_physical_led_ids.extend(physical_led_ids)
        matches.append({
            "virtual_position_id": int(virtual_position_id),
            "virtual_x": round(virtual_x),
            "virtual_y": round(virtual_y),
            "logical_led_id": logical_led_id,
            "physical_led_ids": physical_led_ids,
            "source_x": round(source_x),
            "source_y": round(source_y),
            "distance": distance,
        })

    return {
        "matches": matches,
        "physical_led_ids": flattened_physical_led_ids,
    }


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


def _scale_hex_color(color, brightness_percent):
    color = color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"Invalid RGB color: {color}")
    try:
        channels = [int(color[index:index + 2], 16) for index in range(0, 6, 2)]
    except ValueError as exc:
        raise ValueError(f"Invalid RGB color: {color}") from exc
    return "".join(
        f"{round(channel * brightness_percent / 100):02X}"
        for channel in channels
    )


def sendPhysicalLeds(physical_led_ids, color="FF8B00"):
    """Illuminate physical cable LEDs directly for a temporary preview."""
    if not isinstance(physical_led_ids, (list, tuple, set)):
        raise ValueError("Physical LED IDs must be a list")
    try:
        normalized_ids = [int(led_id) for led_id in physical_led_ids]
    except (TypeError, ValueError) as exc:
        raise ValueError("Physical LED IDs must be integers") from exc
    if not normalized_ids:
        raise ValueError("At least one physical LED ID is required")
    if any(led_id < 0 for led_id in normalized_ids):
        raise ValueError("Physical LED IDs must not be negative")

    normalized_color = _scale_hex_color(color, 100)
    unique_ids = list(dict.fromkeys(normalized_ids))
    controllers = _wled_controllers()
    unknown_ids = [
        led_id
        for led_id in unique_ids
        if not any(
            controller["start"] <= led_id <= controller["end"]
            for controller in controllers
        )
    ]
    if unknown_ids:
        raise ValueError(
            "Physical LED IDs are not assigned to a WLED controller: "
            f"{unknown_ids}"
        )

    selected_ids = set(unique_ids)
    controller_results = []
    for index, controller in enumerate(controllers):
        if _turn_off(controller) is None:
            result = _controller_details(controller, index)
            result["success"] = False
            controller_results.append(result)
            continue

        pixels = []
        for global_led_id in range(controller["start"], controller["end"] + 1):
            if global_led_id in selected_ids:
                pixels.extend([
                    global_led_id - controller["start"],
                    normalized_color,
                ])
        success = True
        if pixels:
            success = _request_wled(
                controller,
                "POST",
                controller["url"],
                action="virtual-mapping-preview",
                json={
                    "on": True,
                    "bri": 255,
                    "seg": {"fx": 0, "i": pixels},
                },
            ) is not None
        result = _controller_details(controller, index)
        result["success"] = success
        controller_results.append(result)

    operation = _finish_wled_operation("virtual-mapping-preview", controller_results)
    return LightingResult(
        {led_id: normalized_color for led_id in unique_ids},
        operation,
    )


def sendLightToBoulderwall(
    holds,
    mode="dark",
    bright_brightness_percent=20,
    boulder_brightness_percent=100,
    above_brightness_percent=100,
):
    if not 10 <= bright_brightness_percent <= 100:
        raise ValueError("Bright wall brightness must be between 10 and 100 percent")
    if not 10 <= boulder_brightness_percent <= 100:
        raise ValueError("Boulder brightness must be between 10 and 100 percent")
    if not 10 <= above_brightness_percent <= 100:
        raise ValueError("Above-hold brightness must be between 10 and 100 percent")

    colors = config.colors
    hole2LEDS = config.hole2LEDS
    bright_channel = round(255 * bright_brightness_percent / 100)
    bright_background_color = f"{bright_channel:02X}" * 3
    led = {}
    for hole_id, hold_value in holds.items():
        if (
            isinstance(hold_value, (list, tuple))
            and len(hold_value) == 2
            and hold_value[1] == "above"
        ):
            hold_type = hold_value[0]
            brightness_percent = above_brightness_percent
        else:
            hold_type = hold_value
            brightness_percent = boulder_brightness_percent
        for physical_led_id in hole2LEDS[hole_id]:
            led[physical_led_id] = _scale_hex_color(
                colors[hold_type],
                brightness_percent,
            )

    controllers = _wled_controllers()
    controller_results = []
    for index, controller in enumerate(controllers):
        if _turn_off(controller) is None:
            result = _controller_details(controller, index)
            result["success"] = False
            controller_results.append(result)
            continue

        pixels = []
        for global_led_id in range(controller["start"], controller["end"] + 1):
            color = led.get(global_led_id)
            if color is None and mode == "bright":
                color = bright_background_color
            if color is not None:
                pixels.extend([global_led_id - controller["start"], color])

        success = True
        if pixels:
            success = _request_wled(
                controller,
                "POST",
                controller["url"],
                action="route-render",
                # Explicitly return the segment to Solid. A celebration may
                # have left a WLED effect active before this state is restored.
                json={"on": True, "bri": 255, "seg": {"fx": 0, "i": pixels}},
            ) is not None
        result = _controller_details(controller, index)
        result["success"] = success
        controller_results.append(result)
    operation = _finish_wled_operation("route", controller_results)
    return LightingResult(led, operation)


def playCelebrationEffect(effect):
    """Run a native WLED effect over the complete range of every controller."""
    settings = CELEBRATION_EFFECTS.get(effect)
    if settings is None:
        raise ValueError(f"Unknown celebration effect: {effect}")

    controller_results = []
    for index, controller in enumerate(_wled_controllers()):
        led_count = controller["end"] - controller["start"] + 1
        # Boulder rendering uses WLED's individual LED control, which freezes
        # the segment. Turning WLED off explicitly leaves individual LED mode;
        # start the effect only in the following request so the animation is
        # reliably active regardless of the previously rendered boulder state.
        reset_response = _request_wled(
            controller,
            "POST",
            controller["url"],
            action="celebration-reset",
            json={"on": False, "tt": 0},
        )
        if reset_response is None:
            result = _controller_details(controller, index)
            result["success"] = False
            controller_results.append(result)
            continue
        effect_response = _request_wled(
            controller,
            "POST",
            controller["url"],
            action="celebration-start",
            json={
                "on": True,
                "bri": 255,
                "tt": 0,
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
        )
        result = _controller_details(controller, index)
        result["success"] = effect_response is not None
        controller_results.append(result)
    return _finish_wled_operation("celebration", controller_results)


def lightUpHoldId(holdid, color):
    controllers = _wled_controllers()
    for controller in controllers:
        _turn_off(controller)

    for controller in controllers:
        if controller["start"] <= holdid <= controller["end"]:
            local_led_id = holdid - controller["start"]
            return _request_wled(
                controller,
                "POST",
                controller["url"],
                action="single-led",
                json={
                    "on": True,
                    "bri": 255,
                    "seg": {"i": [local_led_id, color]},
                },
            )

    raise ValueError(f"LED ID {holdid} is not assigned to a WLED controller")
