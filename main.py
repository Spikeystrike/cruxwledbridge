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
from typing import List, Optional
import json
from utils import (
    CELEBRATION_EFFECTS,
    generate_grid,
    ledCalculation,
    lightUpHoldId,
    playCelebrationEffect,
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

wall_lighting_mode = "dark"  # "dark" or "bright"
current_wall_holds = {}
_pending_viewed_holds = None
celebration_duration_seconds = float(
    getattr(config, "celebration_duration_seconds", 3.0)
)
_lighting_state_lock = asyncio.Lock()
_celebration_generation = 0
_celebration_active = False
_celebration_tasks = set()


def load_celebration_effect():
    default_effect = getattr(config, "celebration_effect", "rainbow")
    if default_effect not in {"off", *CELEBRATION_EFFECTS}:
        default_effect = "rainbow"

    db = SessionLocal()
    try:
        setting = db.query(AppSettingDB).filter(
            AppSettingDB.key == "celebration_effect"
        ).first()
        if setting and setting.value in {"off", *CELEBRATION_EFFECTS}:
            return setting.value
        return default_effect
    finally:
        db.close()


def persist_celebration_effect(effect):
    db = SessionLocal()
    try:
        setting = db.query(AppSettingDB).filter(
            AppSettingDB.key == "celebration_effect"
        ).first()
        if setting:
            setting.value = effect
        else:
            db.add(AppSettingDB(key="celebration_effect", value=effect))
        db.commit()
    finally:
        db.close()


celebration_effect = load_celebration_effect()


async def _restore_current_wall():
    global current_wall_holds, _pending_viewed_holds
    if _pending_viewed_holds is not None:
        current_wall_holds = _pending_viewed_holds
        _pending_viewed_holds = None
    await asyncio.to_thread(
        sendLightToBoulderwall,
        dict(current_wall_holds),
        wall_lighting_mode,
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


class CelebrationEffectSelection(BaseModel):
    effect: str

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
class WallTranslation(BaseModel):
    wallid: int
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
    global current_wall_holds, _pending_viewed_holds
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
        async with _lighting_state_lock:
            if _celebration_active:
                # Keep the running celebration untouched. If several viewed
                # events arrive, the most recent one is what should be shown
                # once the celebration has finished.
                _pending_viewed_holds = dict(holds)
            else:
                current_wall_holds = dict(holds)
                _pending_viewed_holds = None
                await asyncio.to_thread(
                    sendLightToBoulderwall,
                    holds,
                    wall_lighting_mode,
                )
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
    global wall_lighting_mode
    if payload.mode in ["dark", "bright"]:
        wall_lighting_mode = payload.mode
        return {"message": f"Wall lighting mode set to {payload.mode}"}
    else:
        return JSONResponse(status_code=400, content={"message": "Invalid mode. Use 'dark' or 'bright'."})


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
    html_content = return_wall_lighting_html(APP_PATH_PREFIX, celebration_effect)
    return HTMLResponse(content=html_content)

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
async def define_holds(payload: WallTranslation):
    points = [(payload.p1x, payload.p1y) ,(payload.p2x, payload.p2y),(payload.p3x, payload.p3y),(payload.p4x, payload.p4y)]
    # Die Punkte werden in der Reihenfolge vom Frontend übernommen:
    # 0: links-oben (ul), 1: rechts-oben (ur), 2: rechts-unten (lr), 3: links-unten (ll)
    ul = points[0]
    ur = points[1]
    lr = points[2]
    ll = points[3]

    db = SessionLocal()
    c = payload.c 
    r = payload.r
    existing_wall = db.query(WallDB).filter(WallDB.id == payload.wallid).first()
    if existing_wall is None:
        db.close()
        raise HTTPException(status_code=404, detail="Wall not found")
    try:
        full_grid = generate_grid(
            ul,
            ur,
            lr,
            ll,
            r,
            c,
            alternating=payload.alternating,
            alternating_start_column=payload.alternating_start_column,
            led_start_corner=payload.led_start_corner,
            led_direction=payload.led_direction,
        )  # lu, ru, rb, lb
    except ValueError as exc:
        db.close()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    excluded_position_ids = set(payload.excluded_position_ids)
    unknown_position_ids = excluded_position_ids.difference(full_grid)
    if unknown_position_ids:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Unknown grid position IDs: {sorted(unknown_position_ids)}",
        )

    active_position_ids = [
        position_id
        for position_id in sorted(full_grid)
        if position_id not in excluded_position_ids
    ]
    position_led_ids = {
        position_id: led_id
        for led_id, position_id in enumerate(active_position_ids)
    }
    grid = {
        led_id: full_grid[position_id]
        for position_id, led_id in position_led_ids.items()
    }
    if not grid:
        db.close()
        raise HTTPException(status_code=400, detail="At least one grid position must remain active")

    holds2led = ledCalculation(
        existing_wall.holds,
        full_grid,
        position_led_ids,
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
        "points": [
            {"x": payload.p1x, "y": payload.p1y},
            {"x": payload.p2x, "y": payload.p2y},
            {"x": payload.p3x, "y": payload.p3y},
            {"x": payload.p4x, "y": payload.p4y},
        ],
        "r": r,
        "c": c,
        "alternating": payload.alternating,
        "alternating_start_column": payload.alternating_start_column,
        "led_start_corner": payload.led_start_corner,
        "led_direction": payload.led_direction,
        "coordinate_space": "wall_image",
        "coordinate_width": existing_wall.image_width,
        "coordinate_height": existing_wall.image_height,
        "excluded_position_ids": sorted(excluded_position_ids),
        "positions": full_grid,
        "position_led_ids": position_led_ids,
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

    return {
        "message":       "Holds 2 LED Saved",
        "grid": grid,
        "positions": full_grid,
        "position_led_ids": position_led_ids,
        "excluded_position_ids": sorted(excluded_position_ids),
        "holds2led": holds2led,
    }



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
