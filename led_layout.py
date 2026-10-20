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

from utils import _grid_homography, _grid_cable_order, generate_grid, generate_grid_position_layout

Corner = Literal["top_left", "top_right", "bottom_left", "bottom_right"]
Direction = Literal["horizontal", "vertical"]


class LEDReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grid_id: str = Field(min_length=1, max_length=100)
    position_id: int = Field(strict=True)


class CableGap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: LEDReference
    target: LEDReference
    count: int = Field(ge=1, le=10000, strict=True)


class CableSubgrid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(default="", max_length=100)
    position_ids: list[int] = Field(min_length=1, max_length=10000)
    start_corner: Corner = "bottom_left"
    direction: Direction = "vertical"


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
    # Freeze the point identity separately from the editable cable pattern.
    position_start_corner: Corner | None = None
    position_direction: Direction | None = None
    subgrids: list[CableSubgrid] = Field(default_factory=list, max_length=500)
    physical_start: int | None = Field(default=None, ge=0, strict=True)
    excluded_position_ids: list[int] = Field(default_factory=list, max_length=10000)
    manual_positions: list[ExtraLED] = Field(default_factory=list, max_length=1000)


class Override(BaseModel):
    # null deliberately leaves this side unassigned; absence means automatic.
    below: Annotated[int, Field(ge=0, strict=True)] | LEDReference | None = None
    above: Annotated[int, Field(ge=0, strict=True)] | LEDReference | None = None


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
    # None uses grid patterns. [] is a deliberately started, unfinished path.
    cable_path: list[LEDReference] | None = Field(default=None, max_length=10000)
    cable_start: int = Field(default=0, ge=0, strict=True)
    edge_skips: list[CableGap] = Field(default_factory=list, max_length=10000)


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


def derive_led_grid(settings, identity, mode="copy", offset_rows=0.5):
    grid = next((g for i, g in enumerate(saved_grids(settings)) if grid_identity(g, i) == identity), None)
    if grid is None:
        raise ValueError("Grip grid not found")
    if mode == "alternate" and not grid.get("alternating"):
        raise ValueError("Complementary positions require an alternating grip grid")
    fields = ("r", "c", "points", "alternating", "alternating_start_column", "led_start_corner",
              "led_direction", "excluded_position_ids", "manual_positions")
    result = {key: copy.deepcopy(grid[key]) for key in fields if key in grid}
    result["position_start_corner"] = grid.get("led_start_corner", "bottom_left")
    result["position_direction"] = grid.get("led_direction", "vertical")
    if mode == "alternate":
        result["alternating_start_column"] = 1 - grid.get("alternating_start_column", 0)
        result["excluded_position_ids"] = []
        result["manual_positions"] = []
    if mode == "below":
        transform = _grid_homography(*[(p["x"], p["y"]) for p in grid["points"]])
        inverse = np.linalg.inv(transform)
        for point in [*result["points"], *result.get("manual_positions", [])]:
            uv = inverse @ np.array([point["x"], point["y"], 1.0])
            uv = uv / uv[2]; uv[1] += offset_rows / max(1, grid["r"] - 1)
            xy = transform @ uv
            point["x"], point["y"] = float(xy[0] / xy[2]), float(xy[1] / xy[2])
    return result


def _led_geometry(layout):
    points, grid_ids = [], set()
    for grid in layout.grids:
        if grid.id in grid_ids:
            raise ValueError("Duplicate LED grid ID")
        grid_ids.add(grid.id)
        if grid.r * grid.c > 10000:
            raise ValueError("An LED grid may contain at most 10000 positions")
        generated = generate_grid(
            *[(p.x, p.y) for p in grid.points], grid.r, grid.c,
            grid.alternating, grid.alternating_start_column,
            grid.position_start_corner or grid.led_start_corner,
            grid.position_direction or grid.led_direction,
        )
        structural = generate_grid_position_layout(
            grid.r, grid.c, grid.alternating, grid.alternating_start_column,
            grid.position_start_corner or grid.led_start_corner,
            grid.position_direction or grid.led_direction,
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
        for position_id in order:
            x, y = generated[position_id]
            if not (0 <= x <= layout.coordinate_width and 0 <= y <= layout.coordinate_height):
                raise ValueError("LED positions must be inside the wall image")
            points.append({"grid_id": grid.id, "position_id": position_id, "x": x, "y": y,
                           "surface": grid.surface, "physical_id": None,
                           "enabled": position_id not in excluded,
                           "row": structural.get(position_id, (None, None))[0],
                           "column": structural.get(position_id, (None, None))[1]})
    return points


def _ref(point):
    return (point["grid_id"], point["position_id"])


def _pattern(grid, points, corner, direction):
    regular = {(p["row"], p["column"]): p for p in points if p["row"] is not None}
    result = [_ref(regular[key]) for key in _grid_cable_order(regular, corner, direction)]
    # Additional bores retain their explicit insertion anchor (or append).
    extras = {p["position_id"]: p for p in points if p["row"] is None}
    for extra in grid.manual_positions:
        if extra.id not in extras:
            continue
        anchor = (grid.id, extra.before_position_id)
        at = result.index(anchor) if anchor in result else len(result)
        result.insert(at, (grid.id, extra.id))
    enabled = {_ref(p) for p in points if p["enabled"]}
    return [ref for ref in result if ref in enabled]


def cable_geometry(layout):
    """Resolve stable bores into a physical cable, including visible gap labels."""
    points = _led_geometry(layout)
    by_ref = {_ref(p): p for p in points}
    enabled = {key for key, p in by_ref.items() if p["enabled"]}
    starts, order = {}, []
    pattern_order = []
    for grid in layout.grids:
        group = [p for p in points if p["grid_id"] == grid.id]
        claimed, section_ids, grid_order = set(), set(), []
        for sub in grid.subgrids:
            ids = set(sub.position_ids)
            if sub.id in section_ids or len(ids) != len(sub.position_ids) or ids & claimed:
                raise ValueError("Cable subgrids must have unique IDs and non-overlapping positions")
            if ids.difference(p["position_id"] for p in group):
                raise ValueError("A cable subgrid contains positions that no longer exist")
            claimed.update(ids); section_ids.add(sub.id)
            grid_order.extend(_pattern(grid, [p for p in group if p["position_id"] in ids], sub.start_corner, sub.direction))
        rest = [p for p in group if p["position_id"] not in claimed]
        if not grid.subgrids and grid.position_start_corner is None and grid.position_direction is None:
            grid_order.extend(_ref(p) for p in rest if p["enabled"])  # Exact legacy cable order.
        else:
            grid_order.extend(_pattern(grid, rest, grid.led_start_corner, grid.led_direction))
        if grid_order and grid.physical_start is not None:
            starts[grid_order[0]] = grid.physical_start
        pattern_order.extend(grid_order)
    if layout.cable_path is None:
        order = pattern_order
    else:
        order = [(p.grid_id, p.position_id) for p in layout.cable_path]
        starts = {order[0]: layout.cable_start} if order else {}
        # A free path can cross separate controllers. Preserve explicit starts
        # on first entering another grid; only its first grid uses cable_start.
        entered = {order[0][0]} if order else set()
        grid_starts = {g.id: g.physical_start for g in layout.grids}
        for key in order:
            if key[0] not in entered and grid_starts.get(key[0]) is not None:
                starts[key] = grid_starts[key[0]]
            entered.add(key[0])
        if len(order) != len(set(order)):
            raise ValueError("A visible LED may occur only once in the cable path")
        if set(order).difference(enabled):
            raise ValueError("Cable path refers to a disabled or missing LED position")
    adjacent = set(zip(order, order[1:]))
    gaps = {}
    for gap in layout.edge_skips:
        key = ((gap.source.grid_id, gap.source.position_id), (gap.target.grid_id, gap.target.position_id))
        if key not in adjacent:
            raise ValueError("Skipped LEDs must connect two adjacent LEDs in the current cable path")
        if key in gaps:
            raise ValueError("Duplicate cable gap")
        gaps[key] = gap.count
    skipped = set(layout.skipped_physical_ids)
    seen, edges = set(), []
    next_id, previous, represented = 0, None, set()
    leading = []
    for key in order:
        next_id = starts.get(key, next_id)
        gap_ids = []
        count = gaps.get((previous, key), 0)
        if count:
            gap_ids.extend(range(next_id, next_id + count)); next_id += count
        while next_id in skipped:
            gap_ids.append(next_id); next_id += 1
        if next_id in seen or any(i in seen for i in gap_ids):
            raise ValueError(f"Physical LED {next_id} is assigned more than once; check grid starts")
        seen.update(gap_ids); seen.add(next_id); represented.update(gap_ids)
        by_ref[key]["physical_id"] = next_id
        if previous is not None:
            # Explicit controller starts may jump over absolute skipped IDs.
            before = by_ref[previous]["physical_id"]
            gap_ids = sorted(set(gap_ids) | {i for i in skipped if before < i < next_id})
            represented.update(gap_ids)
            edges.append({"source": {"grid_id": previous[0], "position_id": previous[1]},
                          "target": {"grid_id": key[0], "position_id": key[1]},
                          "skipped_ids": gap_ids, "inserted_count": count})
        else:
            leading = gap_ids
        previous = key; next_id += 1
    return {"leds": points, "cable_order": [{"grid_id": g, "position_id": p} for g, p in order],
            "pattern_order": [{"grid_id": g, "position_id": p} for g, p in pattern_order],
            "cable_edges": edges, "leading_skipped_ids": leading,
            "unplaced_skipped_ids": sorted(skipped - represented),
            "unwired_count": len(enabled.difference(order))}


def led_positions(layout):
    return cable_geometry(layout)["leds"]


def calculate_layout(settings, raw_layout):
    layout = LEDLayout.model_validate(raw_layout)
    cable = cable_geometry(layout)
    leds = cable["leds"]
    grips = grip_positions(settings)
    width = settings.get("coordinate_width") or layout.coordinate_width
    height = settings.get("coordinate_height") or layout.coordinate_height
    sx, sy = width / layout.coordinate_width, height / layout.coordinate_height
    leds = [{**p, "x": p["x"] * sx, "y": p["y"] * sy} for p in leds]
    active = [p for p in leds if p["physical_id"] is not None]
    by_id = {p["physical_id"]: p for p in active}
    by_ref = {_ref(p): p for p in leds}
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
                if isinstance(chosen, LEDReference):
                    led = by_ref.get((chosen.grid_id, chosen.position_id))
                    if led is None or led["surface"] != surface:
                        raise ValueError(f"Override for {grip['key']} refers to a missing LED or another wall surface")
                    chosen = led["physical_id"]
                    status = "manual" if chosen is not None else "missing"
                    grip[side] = chosen
                    grip[f"{side}_status"] = status
                    grip[f"{side}_candidates"] = [led for _, led in choices[:5]]
                    continue
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
    return {**cable, "grips": grips, "leds": leds,
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
