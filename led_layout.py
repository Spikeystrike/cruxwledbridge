"""Independent grip geometry, physical LED geometry and spatial associations.

All stored coordinates refer to the wall photograph. Matching takes place in
each grip grid's rectified plane, never in cable order or raw screen Y.
"""
import copy
import json
from functools import lru_cache
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from utils import _grid_homography, generate_grid, generate_grid_position_layout


class Point(BaseModel):
    x: float = Field(ge=0, allow_inf_nan=False)
    y: float = Field(ge=0, allow_inf_nan=False)


class ExtraLED(Point):
    id: int = Field(lt=0, strict=True)
    before_position_id: int | None = Field(default=None, ge=0, strict=True)


class LEDGrid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(default="LED grid", max_length=100)
    surface: str = Field(default="1", min_length=1, max_length=100)
    points: list[Point] = Field(min_length=4, max_length=4)
    r: int = Field(ge=1, le=250, strict=True)
    c: int = Field(ge=1, le=250, strict=True)
    alternating: bool = False
    alternating_start_column: Literal[0, 1] = 0
    led_start_corner: Literal["top_left", "top_right", "bottom_left", "bottom_right"] = "bottom_left"
    led_direction: Literal["horizontal", "vertical"] = "vertical"
    physical_start: int | None = Field(default=None, ge=0, strict=True)
    excluded_position_ids: list[int] = Field(default_factory=list, max_length=10000)
    manual_positions: list[ExtraLED] = Field(default_factory=list, max_length=1000)


class Override(BaseModel):
    # null deliberately leaves this side unassigned; absence means automatic.
    below: int | None = Field(default=None, ge=0, strict=True)
    above: int | None = Field(default=None, ge=0, strict=True)


class LEDLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    coordinate_width: float = Field(gt=0, allow_inf_nan=False)
    coordinate_height: float = Field(gt=0, allow_inf_nan=False)
    grids: list[LEDGrid] = Field(default_factory=list, max_length=100)
    skipped_physical_ids: list[Annotated[int, Field(ge=0, strict=True)]] = Field(default_factory=list, max_length=10000)
    grip_surfaces: dict[str, Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=dict)
    overrides: dict[str, Override] = Field(default_factory=dict)
    lateral_tolerance: float = Field(default=0.35, gt=0, le=0.49, allow_inf_nan=False)
    max_distance: float = Field(default=0.9, gt=0, le=2, allow_inf_nan=False)


def saved_grids(settings):
    return settings.get("grids") or [settings]


def grid_identity(grid, index):
    return grid.get("id") or f"grid-{index + 1}"


def grip_positions(settings):
    """Stable references use structural row/column, not cable numbering."""
    grips = []
    for index, grid in enumerate(saved_grids(settings)):
        identity = grid_identity(grid, index)
        layout = generate_grid_position_layout(
            grid["r"], grid["c"], grid.get("alternating", False),
            grid.get("alternating_start_column", 0),
            grid.get("led_start_corner", "bottom_left"),
            grid.get("led_direction", "vertical"),
        )
        positions = {int(key): value for key, value in grid.get("positions", {}).items()}
        for raw_id, logical_id in grid.get("position_led_ids", {}).items():
            position_id = int(raw_id)
            if position_id not in positions:
                continue
            location = f"r{layout[position_id][0]}c{layout[position_id][1]}" if position_id >= 0 else f"manual{position_id}"
            grips.append({
                "key": f"{identity}:{location}", "grid_id": identity,
                "grid_index": index, "position_id": position_id,
                "logical_id": int(logical_id),
                "row": layout[position_id][0] if position_id >= 0 else None,
                "column": layout[position_id][1] if position_id >= 0 else None,
                "x": positions[position_id][0], "y": positions[position_id][1],
            })
    return grips


def seed_layout(settings, hole2leds, width, height):
    """Copy grip geometry as an editable draft; never claim it is calibrated."""
    grids = []
    skipped = set()
    previous = None
    for index, grid in enumerate(saved_grids(settings)):
        physical = []
        for logical in sorted(int(value) for value in grid.get("position_led_ids", {}).values()):
            ids = hole2leds.get(logical, hole2leds.get(str(logical), []))
            if isinstance(ids, int):
                ids = [ids]
            physical.extend(ids)
        # Import known ascending cable gaps. Non-monotonic/multi-LED legacy
        # mappings remain intact until the user explicitly activates a layout.
        physical_start = min(physical) if physical and (previous is None or physical[0] <= previous) else None
        for led in physical:
            if previous is not None and previous < led:
                skipped.update(range(previous + 1, led))
            previous = led
        grids.append({
            "id": grid_identity(grid, index), "name": f"LED {index + 1}",
            "surface": "1", "points": copy.deepcopy(grid["points"]),
            "r": grid["r"], "c": grid["c"],
            "alternating": grid.get("alternating", False),
            "alternating_start_column": grid.get("alternating_start_column", 0),
            "led_start_corner": grid.get("led_start_corner", "bottom_left"),
            "led_direction": grid.get("led_direction", "vertical"),
            "physical_start": physical_start,
            "excluded_position_ids": grid.get("excluded_position_ids", []),
            "manual_positions": copy.deepcopy(grid.get("manual_positions", [])),
        })
    return LEDLayout(
        coordinate_width=settings.get("coordinate_width") or width,
        coordinate_height=settings.get("coordinate_height") or height,
        grids=grids, skipped_physical_ids=sorted(skipped),
    ).model_dump(exclude_unset=True)


def led_positions(layout):
    skipped = set(layout.skipped_physical_ids)
    if any(type(value) is not int or value < 0 for value in skipped):
        raise ValueError("Skipped LED IDs must be non-negative integers")
    points, seen, grid_ids = [], set(), set()
    next_id = 0
    for grid in layout.grids:
        if grid.id in grid_ids:
            raise ValueError("Duplicate LED grid ID")
        grid_ids.add(grid.id)
        if grid.r * grid.c > 10000:
            raise ValueError("An LED grid may contain at most 10000 positions")
        generated = generate_grid(
            *[(p.x, p.y) for p in grid.points], grid.r, grid.c,
            grid.alternating, grid.alternating_start_column,
            grid.led_start_corner, grid.led_direction,
        )
        base_ids = sorted(generated)
        manual_ids = set()
        for extra in grid.manual_positions:
            if extra.id in manual_ids:
                raise ValueError("Duplicate individual LED position ID")
            manual_ids.add(extra.id)
            if extra.before_position_id is not None and extra.before_position_id not in generated:
                raise ValueError("Individual LED insertion position no longer exists")
        order = []
        for anchor in [*base_ids, None]:
            order.extend(p.id for p in grid.manual_positions if p.before_position_id == anchor)
            if anchor is not None:
                order.append(anchor)
        generated.update({p.id: (p.x, p.y) for p in grid.manual_positions})
        excluded = set(grid.excluded_position_ids)
        if excluded.difference(generated):
            raise ValueError("Disabled LED position no longer exists")
        if grid.physical_start is not None:
            next_id = grid.physical_start
        for position_id in order:
            x, y = generated[position_id]
            if not (0 <= x <= layout.coordinate_width and 0 <= y <= layout.coordinate_height):
                raise ValueError("LED positions must be inside the wall image")
            if position_id in excluded:
                points.append({"grid_id": grid.id, "position_id": position_id, "x": x, "y": y,
                               "surface": grid.surface, "physical_id": None})
                continue
            while next_id in skipped:
                next_id += 1
            if next_id in seen:
                raise ValueError(f"Physical LED {next_id} is assigned more than once; check grid starts")
            seen.add(next_id)
            points.append({"grid_id": grid.id, "position_id": position_id, "x": x, "y": y,
                           "surface": grid.surface, "physical_id": next_id})
            next_id += 1
    return points


def calculate_layout(settings, raw_layout):
    layout = LEDLayout.model_validate(raw_layout)
    leds = led_positions(layout)
    grips = grip_positions(settings)
    width = settings.get("coordinate_width") or layout.coordinate_width
    height = settings.get("coordinate_height") or layout.coordinate_height
    sx, sy = width / layout.coordinate_width, height / layout.coordinate_height
    leds = [{**p, "x": p["x"] * sx, "y": p["y"] * sy} for p in leds]
    active = [p for p in leds if p["physical_id"] is not None]
    by_id = {p["physical_id"]: p for p in active}
    known_grids = {grid_identity(g, i) for i, g in enumerate(saved_grids(settings))}
    if set(layout.grip_surfaces).difference(known_grids):
        raise ValueError("A configured grip grid no longer exists; reload the LED editor")
    if set(layout.overrides).difference(p["key"] for p in grips):
        raise ValueError("An overridden grip no longer exists; remove its override")
    transforms = {}
    for index, grid in enumerate(saved_grids(settings)):
        try:
            transforms[index] = np.linalg.inv(_grid_homography(*[(p["x"], p["y"]) for p in grid["points"]]))
        except (np.linalg.LinAlgError, KeyError) as exc:
            raise ValueError("Grip grid corners do not define a valid wall plane") from exc

    def rectify(transform, x, y):
        p = transform @ np.array([x, y, 1.0])
        if abs(p[2]) < 1e-9:
            return None
        return p[:2] / p[2]

    for grip in grips:
        grid = saved_grids(settings)[grip["grid_index"]]
        surface = layout.grip_surfaces.get(grip["grid_id"], "1")
        grip["surface"] = surface
        transform = transforms[grip["grid_index"]]
        source = rectify(transform, grip["x"], grip["y"])
        if source is None:
            raise ValueError("Grip lies outside its wall plane")
        candidates = {"below": [], "above": []}
        row_step = 2 if grid.get("alternating") else 1
        for led in active:
            if led["surface"] != surface:
                continue
            target = rectify(transform, led["x"], led["y"])
            if target is None:
                continue
            dx, dy = (target - source) * [max(1, grid["c"] - 1), max(1, grid["r"] - 1)]
            dy /= row_step
            if abs(dx) > layout.lateral_tolerance or not 0.01 < abs(dy) <= layout.max_distance:
                continue
            candidates["below" if dy > 0 else "above"].append((float(np.hypot(dx, dy)), led["physical_id"]))
        override = layout.overrides.get(grip["key"])
        for side in ("below", "above"):
            choices = sorted(candidates[side])
            manual = override is not None and side in override.model_fields_set
            if manual:
                chosen = getattr(override, side)
                if chosen is not None and (chosen not in by_id or by_id[chosen]["surface"] != surface):
                    raise ValueError(f"Override for {grip['key']} refers to a missing LED or another wall surface")
                status = "manual" if chosen is not None else "disabled"
            elif not choices:
                chosen, status = None, "missing"
            elif len(choices) > 1 and choices[1][0] - choices[0][0] <= 0.08:
                chosen, status = None, "ambiguous"
            else:
                chosen, status = choices[0][1], "automatic"
            grip[side] = chosen
            grip[f"{side}_status"] = status
            grip[f"{side}_candidates"] = [led for _, led in choices[:5]]
    return {"grips": grips, "leds": leds,
            "coordinate_width": width, "coordinate_height": height,
            "summary": {side: {status: sum(p[f"{side}_status"] == status for p in grips)
                               for status in ("automatic", "manual", "missing", "ambiguous", "disabled")}
                        for side in ("below", "above")}}


def active_associations(settings):
    if not isinstance(settings, dict) or not settings.get("led_layout"):
        return None
    # Route events reuse the resolved geometry; any saved change invalidates it.
    return _cached_associations(json.dumps(settings, sort_keys=False))


@lru_cache(maxsize=8)
def _cached_associations(serialized):
    settings = json.loads(serialized)
    return {p["logical_id"]: p for p in calculate_layout(settings, settings["led_layout"])["grips"]}


def physical_route(holds, associations, direction):
    """Resolve colors once; below wins a shared LED in combined mode."""
    result = {}
    sides = ("above", "below") if direction == "both" else (direction,)
    for side in sides:
        for grip_id, value in sorted(holds.items()):
            led = associations.get(grip_id, {}).get(side)
            if led is not None:
                result[led] = (value, "above") if direction == "both" and side == "above" else value
    return result
