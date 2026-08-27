from fastapi.exceptions import RequestValidationError
import asyncio
import uvicorn
import logging
import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from html import escape
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Request, logger
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Union
import json
from utils import (
    CELEBRATION_EFFECTS,
    generate_grid,
    generate_grid_position_layout,
    ledCalculation,
    lightUpHoldId,
    playCelebrationEffect,
    positions_near_holds,
    sendLightToBoulderwall,
    wall_hold_key,
)
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON
import requests
from templates.wall_lighting import return_wall_lighting_html
from templates.wallselector import returnwallhtml
from templates.language import language_switch_html
from templates.overview import return_overview_html
from templates.settings import return_settings_html
from config_loader import config
Base = declarative_base()
# SQLAlchemy Model for Wall
class Hold2ledDB(Base):
    __tablename__ = "holds"
    
    holdid = Column(String, primary_key=True, index=True)
    ledid = Column(Integer, nullable=False)
class WallDB(Base):
    __tablename__ = "walls"

    id = Column(Integer, primary_key=True, index=True)
    angle_adjustable = Column(Boolean, default=False)
    created_at = Column(String, nullable=False)
    name = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    image_height = Column(Integer, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_url = Column(String, nullable=True)
    maximum_angle = Column(Integer, nullable=True)
    minimum_angle = Column(Integer, nullable=True)
    holds = Column(JSON, nullable=True)  # Store "holds" as JSON
    hold2led = Column(JSON, nullable=True)  # Store hold2led mapping as JSON

class WallCreationDB(Base):
    __tablename__ = "wall_creation_settings"

    wallid = Column(Integer, ForeignKey("walls.id"), primary_key=True, index=True)
    settings = Column(JSON, nullable=False)


class AppSettingDB(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)

# SQLite engine and session setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////code/db/app.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
token = config.token
auth_header =  {"Authorization":  token}
# Create all tables
Base.metadata.create_all(bind=engine)


def normalize_path_prefix(value: str) -> str:
    value = value.strip()
    if not value or value == "/":
        return ""
    return f"/{value.strip('/')}"


APP_PATH_PREFIX = normalize_path_prefix(os.getenv("APP_PATH_PREFIX", ""))


def disable_uvicorn_access_logging():
    # Uvicorn/FastAPI CLI can configure logging after this module is imported.
    # Disable its context-free access line again during application startup.
    logging.getLogger("uvicorn.access").disabled = True


@asynccontextmanager
async def lifespan(_app: FastAPI):
    disable_uvicorn_access_logging()
    yield


app = FastAPI(root_path=APP_PATH_PREFIX, lifespan=lifespan)

HOLD_LIGHTING_DIRECTIONS = {"below", "above", "both"}


def load_app_setting(key, default=None):
    """Load one JSON-compatible setting from the shared settings store."""
    db = SessionLocal()
    try:
        setting = db.query(AppSettingDB).filter(AppSettingDB.key == key).first()
        return setting.value if setting else default
    finally:
        db.close()


def persist_app_settings(settings):
    """Persist any number of current or future settings in one transaction."""
    db = SessionLocal()
    try:
        for key, value in settings.items():
            setting = db.query(AppSettingDB).filter(
                AppSettingDB.key == key
            ).first()
            if setting:
                setting.value = value
            else:
                db.add(AppSettingDB(key=key, value=value))
        db.commit()
    finally:
        db.close()


def _load_percent_setting(key, default):
    value = load_app_setting(key, default)
    if isinstance(value, bool):
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if 10 <= value <= 100 else default


def load_wall_lighting_mode():
    mode = load_app_setting("wall_lighting_mode", "dark")
    return mode if mode in {"dark", "bright"} else "dark"


def load_hold_lighting_direction():
    direction = load_app_setting("hold_lighting_direction", "below")
    return direction if direction in HOLD_LIGHTING_DIRECTIONS else "below"


def load_celebration_effect():
    default_effect = getattr(config, "celebration_effect", "rainbow")
    if default_effect not in {"off", *CELEBRATION_EFFECTS}:
        default_effect = "rainbow"

    effect = load_app_setting("celebration_effect", default_effect)
    return effect if effect in {"off", *CELEBRATION_EFFECTS} else default_effect


def persist_celebration_effect(effect):
    persist_app_settings({"celebration_effect": effect})


def load_route_timeout_minutes():
    value = load_app_setting("route_timeout_minutes", 0)
    if isinstance(value, bool):
        return 0
    try:
        value = int(value)
        return value if value >= 0 else 0
    except (TypeError, ValueError):
        return 0


def persist_route_timeout_minutes(minutes):
    persist_app_settings({"route_timeout_minutes": int(minutes)})


def _above_led_mapping(saved_settings):
    """Map each logical hold LED to the LED directly above it."""
    if not isinstance(saved_settings, dict):
        return {}

    saved_grids = saved_settings.get("grids")
    if not isinstance(saved_grids, list) or not saved_grids:
        saved_grids = [saved_settings]

    above_leds = {}
    for saved_grid in saved_grids:
        if not isinstance(saved_grid, dict):
            continue
        raw_position_led_ids = saved_grid.get("position_led_ids", {})
        if not isinstance(raw_position_led_ids, dict):
            continue
        try:
            layout = generate_grid_position_layout(
                int(saved_grid["r"]),
                int(saved_grid["c"]),
                alternating=bool(saved_grid.get("alternating", False)),
                alternating_start_column=int(
                    saved_grid.get("alternating_start_column", 0)
                ),
                led_start_corner=saved_grid.get(
                    "led_start_corner",
                    "bottom_left",
                ),
                led_direction=saved_grid.get("led_direction", "vertical"),
            )
            position_led_ids = {
                int(position_id): int(led_id)
                for position_id, led_id
                in raw_position_led_ids.items()
            }
        except (KeyError, TypeError, ValueError):
            continue

        raw_positions = saved_grid.get("positions", {})
        if not isinstance(raw_positions, dict):
            raw_positions = {}
        positions = {}
        for position_id, coordinates in raw_positions.items():
            try:
                x, y = coordinates
                positions[int(position_id)] = (float(x), float(y))
            except (TypeError, ValueError):
                continue

        active_positions = set(position_led_ids).intersection(layout)
        for position_id in active_positions:
            led_id = position_led_ids[position_id]
            row, column = layout[position_id]
            candidates = [
                candidate_id
                for candidate_id in active_positions
                if layout[candidate_id][0] == row - 1
            ]
            if not candidates:
                # No LED exists above the highest active hold. Its own LED is
                # below the hold and is therefore the required fallback.
                above_leds[led_id] = (led_id, True)
                continue

            source_coordinates = positions.get(position_id)

            def candidate_distance(candidate_id):
                candidate_coordinates = positions.get(candidate_id)
                candidate_column = layout[candidate_id][1]
                if source_coordinates and candidate_coordinates:
                    x_distance = source_coordinates[0] - candidate_coordinates[0]
                    y_distance = source_coordinates[1] - candidate_coordinates[1]
                    image_distance = x_distance ** 2 + y_distance ** 2
                else:
                    image_distance = abs(column - candidate_column)
                return image_distance, abs(column - candidate_column), candidate_id

            target_position_id = min(candidates, key=candidate_distance)
            above_leds[led_id] = (
                position_led_ids[target_position_id],
                False,
            )

    return above_leds


def apply_hold_lighting_direction(holds, saved_settings, direction):
    """Move or duplicate route colors to the LEDs above their holds."""
    holds = dict(holds)
    if direction == "below" or not holds:
        return holds
    if direction not in HOLD_LIGHTING_DIRECTIONS:
        return holds

    above_leds = _above_led_mapping(saved_settings)
    shifted_holds = {}
    fallback_holds = {}
    for led_id, hold_type in sorted(holds.items()):
        target_led_id, uses_below_fallback = above_leds.get(
            led_id,
            (led_id, True),
        )
        target = fallback_holds if uses_below_fallback else shifted_holds
        target[target_led_id] = hold_type

    # A highest hold's required below-light fallback wins if a lower hold also
    # tries to use that LED from above.
    shifted_holds.update(fallback_holds)
    if direction == "above":
        return shifted_holds

    # In both-sides mode the LED assigned directly to a hold keeps that hold's
    # own color when two adjacent route holds share the same physical light.
    shifted_holds.update(holds)
    return shifted_holds


wall_lighting_mode = load_wall_lighting_mode()
bright_wall_brightness_percent = _load_percent_setting(
    "bright_wall_brightness_percent",
    20,
)
boulder_brightness_percent = _load_percent_setting(
    "boulder_brightness_percent",
    100,
)
hold_lighting_direction = load_hold_lighting_direction()
celebration_effect = load_celebration_effect()
route_timeout_minutes = load_route_timeout_minutes()
current_wall_holds = {}
_pending_viewed_holds = None
_route_lighting_active = False
celebration_duration_seconds = float(
    getattr(config, "celebration_duration_seconds", 3.0)
)
_lighting_state_lock = asyncio.Lock()
_celebration_generation = 0
_celebration_active = False
_celebration_tasks = set()
_route_timeout_generation = 0
_route_timeout_task = None
_route_timeout_sleep_task = None


def _cancel_route_timeout():
    global _route_timeout_generation, _route_timeout_task
    _route_timeout_generation += 1
    if (
        _route_timeout_task is not None
        and _route_timeout_task is _route_timeout_sleep_task
        and not _route_timeout_task.done()
    ):
        _route_timeout_task.cancel()
    _route_timeout_task = None


def _clear_route_timeout_task(task):
    global _route_timeout_task, _route_timeout_sleep_task
    if _route_timeout_task is task:
        _route_timeout_task = None
    if _route_timeout_sleep_task is task:
        _route_timeout_sleep_task = None


async def _run_route_timeout(delay_seconds, generation):
    global _route_lighting_active, _route_timeout_sleep_task
    task = asyncio.current_task()
    try:
        _route_timeout_sleep_task = task
        await asyncio.sleep(delay_seconds)
        if _route_timeout_sleep_task is task:
            _route_timeout_sleep_task = None
        async with _lighting_state_lock:
            if generation != _route_timeout_generation:
                return
            _route_lighting_active = False
            await asyncio.to_thread(
                sendLightToBoulderwall,
                {},
                "dark",
                bright_wall_brightness_percent,
                boulder_brightness_percent,
            )
    except asyncio.CancelledError:
        return
    finally:
        if _route_timeout_sleep_task is task:
            _route_timeout_sleep_task = None


def schedule_route_timeout():
    global _route_timeout_generation, _route_timeout_task
    _cancel_route_timeout()
    if route_timeout_minutes == 0:
        return False

    generation = _route_timeout_generation
    task = asyncio.create_task(
        _run_route_timeout(route_timeout_minutes * 60, generation)
    )
    _route_timeout_task = task
    task.add_done_callback(_clear_route_timeout_task)
    return True


async def _restore_current_wall():
    global current_wall_holds, _pending_viewed_holds, _route_lighting_active
    if _pending_viewed_holds is not None:
        current_wall_holds = _pending_viewed_holds
        _pending_viewed_holds = None
        _route_lighting_active = True
    if _route_lighting_active:
        await asyncio.to_thread(
            sendLightToBoulderwall,
            dict(current_wall_holds),
            wall_lighting_mode,
            bright_wall_brightness_percent,
            boulder_brightness_percent,
        )
        schedule_route_timeout()
    else:
        await asyncio.to_thread(
            sendLightToBoulderwall,
            {},
            "dark",
            bright_wall_brightness_percent,
            boulder_brightness_percent,
        )


async def _run_celebration(effect, generation):
    global _celebration_active
    try:
        async with _lighting_state_lock:
            if generation != _celebration_generation:
                return
            await asyncio.to_thread(playCelebrationEffect, effect)
        await asyncio.sleep(celebration_duration_seconds)
    except Exception:
        logging.getLogger("cruxwledbridge").exception(
            "Could not run celebration effect %s", effect
        )
    finally:
        async with _lighting_state_lock:
            if generation == _celebration_generation:
                try:
                    await _restore_current_wall()
                finally:
                    # A new celebration can be scheduled while the restore is
                    # waiting on WLED I/O. Do not let this older task mark the
                    # newer celebration inactive.
                    if generation == _celebration_generation:
                        _celebration_active = False


def schedule_celebration():
    global _celebration_active, _celebration_generation
    if celebration_effect == "off":
        return False

    _celebration_generation += 1
    _cancel_route_timeout()
    generation = _celebration_generation
    _celebration_active = True
    task = asyncio.create_task(_run_celebration(celebration_effect, generation))
    _celebration_tasks.add(task)
    task.add_done_callback(_celebration_tasks.discard)
    return True

WALL_LIST_TRANSLATIONS = {
    "en": {
        "page.title": "Wall selector",
        "page.heading": "Wall selector",
    },
    "de": {
        "page.title": "Wandauswahl",
        "page.heading": "Wandauswahl",
    },
}


def configure_access_logger():
    access_logger = logging.getLogger("cruxwledbridge.access")
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False

    if not any(
        getattr(handler, "cruxwledbridge_access_handler", False)
        for handler in access_logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.cruxwledbridge_access_handler = True
        handler.setFormatter(
            logging.Formatter(
                "INFO: %(asctime)s %(message)s",
                datefmt="%Y%m%d-%H%M%S",
            )
        )
        access_logger.addHandler(handler)

    # The application emits the access log itself so it can add climb details.
    # Disable Uvicorn's otherwise identical, but context-free, access line.
    disable_uvicorn_access_logging()
    return access_logger


access_logger = configure_access_logger()


def format_access_log(request: Request, status_code: int) -> str:
    client = request.client
    if client:
        host = client.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        client_address = f"{host}:{client.port}"
    else:
        client_address = "-"

    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"

    climb = getattr(request.state, "viewed_climb", None)
    if climb is None:
        sent_climb = getattr(request.state, "sent_climb", None)
        if sent_climb:
            climb = {
                "id": sent_climb["climb_id"],
                "name": sent_climb["climb_name"],
                "wall_id": sent_climb.get("wall_id"),
            }
    climb_details = ""
    if climb:
        climb_name = json.dumps(str(climb["name"]), ensure_ascii=False)
        climb_details = (
            f" climb_id={climb['id']}"
            f" climb_name={climb_name}"
        )
        if climb.get("wall_id") is not None:
            climb_details += f" wall_id={climb['wall_id']}"

    try:
        reason = HTTPStatus(status_code).phrase
    except ValueError:
        reason = ""

    return (
        f'{client_address} - "{request.method} {path} '
        f'HTTP/{request.scope.get("http_version", "1.1")}"'
        f"{climb_details} {status_code} {reason}"
    ).rstrip()


@app.middleware("http")
async def log_access(request: Request, call_next):
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        access_logger.info(format_access_log(request, status_code))

def register_exception(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):

        exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
        # or logger.error(f'{exc}')
        logger.error(request, exc_str)
        content = {'status_code': 10422, 'message': exc_str, 'data': None}
        return JSONResponse(content=content)

register_exception(app)

class WallLightingMode(BaseModel):
    mode: str
    brightness: Optional[int] = Field(default=None, ge=10, le=100)


class CelebrationEffectSelection(BaseModel):
    effect: str


class WallLightingSettings(BaseModel):
    mode: str
    bright_brightness_percent: int = Field(ge=10, le=100)
    boulder_brightness_percent: int = Field(ge=10, le=100)
    celebration_effect: str
    hold_lighting_direction: Optional[str] = None


class EnergySavingSettings(BaseModel):
    route_timeout_minutes: int = Field(ge=0)

class Hold(BaseModel):
    id: str
    hold_type: str
    mask: List[List[float]]  # Punkte in der Maske als Listen von [x, y]

class User(BaseModel):
    id: int
    created_at: str
    name: str
    profile_image_url: HttpUrl

class H2l(BaseModel):
    hold: str
    led: int

class Wall(BaseModel):
    id: int
    angle_adjustable: bool
    created_at: str
    holds: List[Hold]
    image_height: Optional[int]
    image_url: Optional[str]
    image_width: Optional[int]
    maximum_angle: Optional[int]
    minimum_angle: Optional[int]
    name: str
    updated_at: str
    hold2led: List[H2l]

class Send(BaseModel):
    id: int
    created_at: str
    repeat: bool
    send_date: str
    user: User
class GridTranslation(BaseModel):
    id: Optional[str] = None
    p1x: int
    p1y: int 
    p2x: int 
    p2y: int
    p3x: int
    p3y: int
    p4x: int
    p4y: int
    r: int 
    c: int
    alternating: bool = False
    alternating_start_column: int = 0
    led_start_corner: str = "bottom_left"
    led_direction: str = "vertical"
    excluded_position_ids: List[int] = Field(default_factory=list)
    auto_exclude_empty: bool = True
    apply_auto_exclusions: bool = False


class WallTranslation(GridTranslation):
    wallid: int


class MultiGridWallTranslation(BaseModel):
    wallid: int
    grids: List[GridTranslation]


class Climb(BaseModel):
    id: int
    wall_id: int
    angle: Optional[int]
    color: Optional[str]
    created_at: Optional[str]
    description: Optional[str]
    foot_rules: Optional[str]
    grade: Optional[str]
    gym_name: Optional[str]
    gym_slug: Optional[str]
    holds: List[Hold]
    image_height: Optional[int]
    image_url: HttpUrl
    image_width: int
    name: str
    number_of_comments: int
    number_of_sends: int
    sends: Optional[List[Send]]
    setter_id: int
    setter_name: str
    unedited_image_url: HttpUrl
    unset_at: Optional[str]
    updated_at: str
class PayL(BaseModel):
    payload: Climb


class SentClimb(BaseModel):
    id: int
    name: str
    wall_id: Optional[int] = None


class ClimbSend(BaseModel):
    id: int
    climb: SentClimb


class SentPayL(BaseModel):
    payload: ClimbSend
    
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=return_overview_html(APP_PATH_PREFIX))


@app.post("/viewed")
async def viewed(payload: PayL, request: Request):
    global current_wall_holds, _pending_viewed_holds, _route_lighting_active
    # Verarbeite den JSON-Payload
    climb = payload.payload
    request.state.viewed_climb = {
        "id": climb.id,
        "name": climb.name,
        "wall_id": climb.wall_id,
    }
    try:
        holds = {}
        db = SessionLocal()
        for hold in climb.holds:
            hold_key = wall_hold_key(climb.wall_id, hold.id)
            hit = db.query(Hold2ledDB).filter(Hold2ledDB.holdid == hold_key).first()
            if hit:
                holds[hit.ledid] = hold.hold_type
        saved_creation = db.query(WallCreationDB).filter(
            WallCreationDB.wallid == climb.wall_id
        ).first()
        holds = apply_hold_lighting_direction(
            holds,
            saved_creation.settings if saved_creation else None,
            hold_lighting_direction,
        )
        async with _lighting_state_lock:
            if _celebration_active:
                # Keep the running celebration untouched. If several viewed
                # events arrive, the most recent one is what should be shown
                # once the celebration has finished.
                _pending_viewed_holds = dict(holds)
                _route_lighting_active = True
                _cancel_route_timeout()
            else:
                current_wall_holds = dict(holds)
                _pending_viewed_holds = None
                await asyncio.to_thread(
                    sendLightToBoulderwall,
                    holds,
                    wall_lighting_mode,
                    bright_wall_brightness_percent,
                    boulder_brightness_percent,
                )
                _route_lighting_active = True
                schedule_route_timeout()
        db.close()
    except Exception as e:
        print("ERROR")
       
    return {
        "message": "Payload received successfully",
        "name": climb.name,  # Beispiel: Zugriff auf eines der Felder
        "image_url": climb.image_url,  # Zugriff auf andere Felder
    }


@app.post("/sent")
async def sent(payload: SentPayL, request: Request):
    send = payload.payload
    request.state.sent_climb = {
        "send_id": send.id,
        "climb_id": send.climb.id,
        "climb_name": send.climb.name,
        "wall_id": send.climb.wall_id,
    }
    started = schedule_celebration()
    return {
        "message": "Celebration started" if started else "Celebration disabled",
        "effect": celebration_effect,
    }

@app.post("/wall_lighting_mode")
async def set_wall_lighting_mode(payload: WallLightingMode):
    global wall_lighting_mode, bright_wall_brightness_percent
    if payload.mode in ["dark", "bright"]:
        settings = {"wall_lighting_mode": payload.mode}
        if payload.brightness is not None:
            settings["bright_wall_brightness_percent"] = payload.brightness
        persist_app_settings(settings)
        wall_lighting_mode = payload.mode
        if payload.brightness is not None:
            bright_wall_brightness_percent = payload.brightness
        return {
            "message": f"Wall lighting mode set to {payload.mode}",
            "brightness": bright_wall_brightness_percent,
        }
    else:
        return JSONResponse(status_code=400, content={"message": "Invalid mode. Use 'dark' or 'bright'."})


@app.post("/wall_lighting_settings")
async def set_wall_lighting_settings(payload: WallLightingSettings):
    global wall_lighting_mode, bright_wall_brightness_percent
    global boulder_brightness_percent, celebration_effect, hold_lighting_direction
    global _celebration_active, _celebration_generation

    if payload.mode not in {"dark", "bright"}:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid mode. Use 'dark' or 'bright'."},
        )
    if payload.celebration_effect not in {"off", *CELEBRATION_EFFECTS}:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid celebration effect."},
        )
    new_hold_lighting_direction = (
        payload.hold_lighting_direction or hold_lighting_direction
    )
    if new_hold_lighting_direction not in HOLD_LIGHTING_DIRECTIONS:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid hold lighting direction."},
        )

    persist_app_settings({
        "wall_lighting_mode": payload.mode,
        "bright_wall_brightness_percent": payload.bright_brightness_percent,
        "boulder_brightness_percent": payload.boulder_brightness_percent,
        "celebration_effect": payload.celebration_effect,
        "hold_lighting_direction": new_hold_lighting_direction,
    })
    wall_lighting_mode = payload.mode
    bright_wall_brightness_percent = payload.bright_brightness_percent
    boulder_brightness_percent = payload.boulder_brightness_percent
    celebration_effect = payload.celebration_effect
    hold_lighting_direction = new_hold_lighting_direction

    if celebration_effect == "off" and _celebration_active:
        _celebration_generation += 1
        async with _lighting_state_lock:
            await _restore_current_wall()
            _celebration_active = False

    return {
        "message": "Wall lighting settings updated",
        "mode": wall_lighting_mode,
        "bright_brightness_percent": bright_wall_brightness_percent,
        "boulder_brightness_percent": boulder_brightness_percent,
        "celebration_effect": celebration_effect,
        "hold_lighting_direction": hold_lighting_direction,
    }


@app.post("/celebration_effect")
async def set_celebration_effect(payload: CelebrationEffectSelection):
    global celebration_effect, _celebration_active, _celebration_generation
    allowed_effects = {"off", *CELEBRATION_EFFECTS}
    if payload.effect not in allowed_effects:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid celebration effect."},
        )

    celebration_effect = payload.effect
    persist_celebration_effect(payload.effect)

    if payload.effect == "off" and _celebration_active:
        _celebration_generation += 1
        async with _lighting_state_lock:
            await _restore_current_wall()
            _celebration_active = False

    return {"message": "Celebration effect updated", "effect": payload.effect}

@app.get("/wall_lighting", response_class=HTMLResponse)
async def get_wall_lighting():
    html_content = return_wall_lighting_html(
        APP_PATH_PREFIX,
        celebration_effect,
        bright_wall_brightness_percent,
        wall_lighting_mode,
        boulder_brightness_percent,
        hold_lighting_direction,
    )
    return HTMLResponse(content=html_content)


@app.post("/route_timeout")
async def set_route_timeout(payload: EnergySavingSettings):
    global route_timeout_minutes
    route_timeout_minutes = payload.route_timeout_minutes
    persist_route_timeout_minutes(route_timeout_minutes)
    async with _lighting_state_lock:
        if _route_lighting_active and not _celebration_active:
            schedule_route_timeout()
        else:
            _cancel_route_timeout()
    return {
        "message": "Route timeout updated",
        "route_timeout_minutes": route_timeout_minutes,
    }


@app.get("/settings", response_class=HTMLResponse)
async def get_settings():
    return HTMLResponse(content=return_settings_html(
        APP_PATH_PREFIX,
        route_timeout_minutes,
    ))

@app.get("/lightID/{color}/{led_id}")
async def get_light_id(color: str, led_id: int):
    r = lightUpHoldId(led_id, color)
    # Hier können Sie die Logik implementieren, um die Informationen für die angegebene LED-ID abzurufen
    return {"led_id": led_id, "color": color}
@app.get("/listwalls")
async def list_walls(gym: str = ""):
    gym = gym.strip()
    if not gym:
        raise HTTPException(status_code=400, detail="Please send a gym slug")

    try:
        result = requests.get(
            f"https://www.cruxapp.ca/api/v1/gyms/{quote(gym, safe='')}/gym_walls",
            headers=auth_header,
            verify=False,
            timeout=15,
        )
        result.raise_for_status()
        walls = result.json()
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Could not load walls from Crux") from exc

    if not isinstance(walls, list) or not all(isinstance(wall, dict) for wall in walls):
        raise HTTPException(status_code=502, detail="Unexpected gym walls response from Crux")

    wall_cards = []
    for wall in walls:
        if "id" not in wall or "name" not in wall:
            raise HTTPException(status_code=502, detail="Incomplete wall data from Crux")
        wall_id = quote(str(wall["id"]), safe="")
        wall_name = escape(str(wall["name"]))
        image_url = escape(str(wall.get("image_url") or ""), quote=True)
        wall_cards.append(
            f'<div style="margin-bottom:20px;"><h2>{wall_name}</h2>'
            f'<a href="{APP_PATH_PREFIX}/wallcreation?id={wall_id}"><img src="{image_url}" '
            f'alt="{wall_name}" style="max-width:300px;"></a></div>'
        )
    language_switch = language_switch_html(WALL_LIST_TRANSLATIONS)
    favorite_gym_slug = escape(gym, quote=True)
    html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title data-i18n="page.title">Wall selector</title>
            <style>
                body {{
                    font-family: sans-serif;
                    margin: 20px;
                    background-color: #f4f4f9;
                    color: #222;
                }}
                img {{
                    max-width: 300px;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <h1 data-i18n="page.heading">Wall selector</h1>
            {''.join(wall_cards)}
            {language_switch}
            <script data-gym-slug="{favorite_gym_slug}">
                (() => {{
                    try {{
                        window.localStorage.setItem(
                            'cruxwledbridge.favoriteGymSlug',
                            document.currentScript.dataset.gymSlug,
                        );
                    }} catch (error) {{
                        // The wall list remains usable when browser storage is unavailable.
                    }}
                }})();
            </script>
        </body>
        </html>
    """
    return HTMLResponse(content=html_content)

@app.get ("/wallcreation")
async def wall_creation(id: str = ""):
    id = id.strip()
    if id:
        result = requests.get("https://www.cruxapp.ca/api/v1/gym_walls/"+id, headers=auth_header, verify=False)
        wall = json.loads(result.text)
        db = SessionLocal()
        existing_wall = db.query(WallDB).filter(WallDB.id == wall['id']).first()
        previous_image_width = existing_wall.image_width if existing_wall else None
        previous_image_height = existing_wall.image_height if existing_wall else None

        if existing_wall:
            # Update the existing wall
            existing_wall.angle_adjustable = wall['angle_adjustable']
            existing_wall.created_at = wall['created_at']
            existing_wall.name = wall['name']
            existing_wall.updated_at = wall['updated_at']
            existing_wall.image_height = wall['image_height']
            existing_wall.image_width = wall['image_width']
            existing_wall.image_url = wall['image_url']
            existing_wall.maximum_angle = wall['maximum_angle']
            existing_wall.minimum_angle = wall['minimum_angle']
            existing_wall.holds = [hold for hold in wall['holds']]
        else:
            # Create a new wall if it doesn't exist
            wall_db = WallDB(
                id=wall['id'],
                angle_adjustable=wall['angle_adjustable'],
                created_at=wall['created_at'],
                name=wall['name'],
                updated_at=wall['updated_at'],
                image_height=wall['image_height'],
                image_width=wall['image_width'],
                image_url=wall['image_url'],
                maximum_angle=wall['maximum_angle'],
                minimum_angle=wall['minimum_angle'],
                holds=[hold for hold in wall['holds']]
            )
            db.add(wall_db)

        saved_creation = db.query(WallCreationDB).filter(
            WallCreationDB.wallid == wall['id']
        ).first()
        saved_settings = dict(saved_creation.settings) if saved_creation else None
        if saved_settings and saved_settings.get("coordinate_space") == "wall_image":
            # Older wall-image mappings did not persist their coordinate dimensions.
            # The WallDB values from before the Crux refresh are the best available
            # reference for the image against which those coordinates were saved.
            if not saved_settings.get("coordinate_width") and previous_image_width:
                saved_settings["coordinate_width"] = previous_image_width
            if not saved_settings.get("coordinate_height") and previous_image_height:
                saved_settings["coordinate_height"] = previous_image_height
            saved_creation.settings = saved_settings

        db.commit()  # Save changes to the database
        db.close()
        html_content = returnwallhtml(wall, APP_PATH_PREFIX, saved_settings)
        return HTMLResponse(content=html_content)        
    else:
        raise HTTPException(status_code=400, detail="Please send a wall id")



@app.post("/defineholds")
async def define_holds(payload: Union[WallTranslation, MultiGridWallTranslation]):
    db = SessionLocal()
    existing_wall = db.query(WallDB).filter(WallDB.id == payload.wallid).first()
    if existing_wall is None:
        db.close()
        raise HTTPException(status_code=404, detail="Wall not found")

    multi_grid = isinstance(payload, MultiGridWallTranslation)
    grid_payloads = payload.grids if multi_grid else [payload]
    if not grid_payloads:
        db.close()
        raise HTTPException(status_code=400, detail="At least one grid is required")

    combined_positions = {}
    combined_position_led_ids = {}
    combined_grid = {}
    saved_grids = []
    prepared_grids = []

    for grid_index, grid_payload in enumerate(grid_payloads):
        points = [
            (grid_payload.p1x, grid_payload.p1y),
            (grid_payload.p2x, grid_payload.p2y),
            (grid_payload.p3x, grid_payload.p3y),
            (grid_payload.p4x, grid_payload.p4y),
        ]
        # Point order from the frontend: upper-left, upper-right,
        # lower-right, lower-left.
        ul, ur, lr, ll = points
        try:
            full_grid = generate_grid(
                ul,
                ur,
                lr,
                ll,
                grid_payload.r,
                grid_payload.c,
                alternating=grid_payload.alternating,
                alternating_start_column=grid_payload.alternating_start_column,
                led_start_corner=grid_payload.led_start_corner,
                led_direction=grid_payload.led_direction,
            )
        except ValueError as exc:
            db.close()
            raise HTTPException(
                status_code=400,
                detail=f"Grid {grid_index + 1}: {exc}",
            ) from exc

        excluded_position_ids = set(grid_payload.excluded_position_ids)
        unknown_position_ids = excluded_position_ids.difference(full_grid)
        if unknown_position_ids:
            db.close()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Grid {grid_index + 1}: unknown grid position IDs: "
                    f"{sorted(unknown_position_ids)}"
                ),
            )

        prepared_grids.append((grid_payload, full_grid, excluded_position_ids))
        for position_id, coordinates in full_grid.items():
            combined_positions[(grid_index, position_id)] = coordinates

    occupied_positions = positions_near_holds(
        existing_wall.holds,
        [full_grid for _, full_grid, _ in prepared_grids],
    )
    led_offset = 0

    for grid_index, (grid_payload, full_grid, excluded_position_ids) in enumerate(
        prepared_grids
    ):
        if (
            grid_payload.auto_exclude_empty
            and grid_payload.apply_auto_exclusions
        ):
            excluded_position_ids.update(
                position_id
                for position_id in full_grid
                if (grid_index, position_id) not in occupied_positions
            )

        active_position_ids = [
            position_id
            for position_id in sorted(full_grid)
            if position_id not in excluded_position_ids
        ]
        if not active_position_ids and not grid_payload.apply_auto_exclusions:
            db.close()
            raise HTTPException(
                status_code=400,
                detail=f"Grid {grid_index + 1}: at least one grid position must remain active",
            )

        position_led_ids = {
            position_id: led_offset + local_led_id
            for local_led_id, position_id in enumerate(active_position_ids)
        }
        grid = {
            led_id: full_grid[position_id]
            for position_id, led_id in position_led_ids.items()
        }
        combined_grid.update(grid)
        for position_id in full_grid:
            combined_id = (grid_index, position_id)
            if position_id in position_led_ids:
                combined_position_led_ids[combined_id] = position_led_ids[position_id]

        saved_grids.append({
            "id": grid_payload.id or f"grid-{grid_index + 1}",
            "points": [
                {"x": grid_payload.p1x, "y": grid_payload.p1y},
                {"x": grid_payload.p2x, "y": grid_payload.p2y},
                {"x": grid_payload.p3x, "y": grid_payload.p3y},
                {"x": grid_payload.p4x, "y": grid_payload.p4y},
            ],
            "r": grid_payload.r,
            "c": grid_payload.c,
            "alternating": grid_payload.alternating,
            "alternating_start_column": grid_payload.alternating_start_column,
            "led_start_corner": grid_payload.led_start_corner,
            "led_direction": grid_payload.led_direction,
            "auto_exclude_empty": grid_payload.auto_exclude_empty,
            "excluded_position_ids": sorted(excluded_position_ids),
            "positions": full_grid,
            "position_led_ids": position_led_ids,
            "led_start": led_offset,
            "led_end": led_offset + len(active_position_ids) - 1,
        })
        led_offset += len(active_position_ids)

    holds2led = ledCalculation(
        existing_wall.holds,
        combined_positions,
        combined_position_led_ids,
    )
    db.query(Hold2ledDB).filter(
        Hold2ledDB.holdid.like(f"{payload.wallid}_%")
    ).delete(synchronize_session=False)
    for h in holds2led:
        hold_key = wall_hold_key(payload.wallid, h)
        hold2db = Hold2ledDB(
            holdid=hold_key,
            ledid=holds2led[h]
        )
        db.add(hold2db)

    saved_settings = {
        "coordinate_space": "wall_image",
        "coordinate_width": existing_wall.image_width,
        "coordinate_height": existing_wall.image_height,
        "grids": saved_grids,
        "holds2led": holds2led,
    }
    if not multi_grid:
        # Keep the previous JSON and response shape for existing installations
        # and clients that still submit one flat grid.
        saved_settings = {
            **saved_grids[0],
            "coordinate_space": "wall_image",
            "coordinate_width": existing_wall.image_width,
            "coordinate_height": existing_wall.image_height,
            "holds2led": holds2led,
        }
    saved_creation = db.query(WallCreationDB).filter(
        WallCreationDB.wallid == payload.wallid
    ).first()
    if saved_creation:
        saved_creation.settings = saved_settings
    else:
        db.add(WallCreationDB(wallid=payload.wallid, settings=saved_settings))
    db.commit()
    db.close()

    response = {
        "message":       "Holds 2 LED Saved",
        "grid": combined_grid,
        "grids": saved_grids,
        "holds2led": holds2led,
    }
    if not multi_grid:
        response.update({
            "positions": saved_grids[0]["positions"],
            "position_led_ids": saved_grids[0]["position_led_ids"],
            "excluded_position_ids": saved_grids[0]["excluded_position_ids"],
        })
    return response



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
