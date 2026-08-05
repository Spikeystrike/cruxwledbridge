from fastapi.exceptions import RequestValidationError
import uvicorn
import logging
import os
from html import escape
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Request, logger
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
import json
from utils import (
    generate_grid,
    ledCalculation,
    lightUpHoldId,
    sendLightToBoulderwall,
    wall_hold_key,
)
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON
import requests
from templates.wall_lighting import return_wall_lighting_html
from templates.wallselector import returnwallhtml
from config import config
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
app = FastAPI(root_path=APP_PATH_PREFIX)

wall_lighting_mode = "dark"  # "dark" or "bright"

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
    
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/viewed")
async def viewed(payload: PayL):
    # Verarbeite den JSON-Payload
    try:
        climb = payload.payload
        holds = {}
        db = SessionLocal()
        for hold in climb.holds:
            hold_key = wall_hold_key(climb.wall_id, hold.id)
            hit = db.query(Hold2ledDB).filter(Hold2ledDB.holdid == hold_key).first()
            if hit:
                holds[hit.ledid] = hold.hold_type
        sendLightToBoulderwall(holds, wall_lighting_mode)
        db.close()
    except Exception as e:
        print("ERROR")
       
    return {
        "message": "Payload received successfully",
        "name": climb.name,  # Beispiel: Zugriff auf eines der Felder
        "image_url": climb.image_url,  # Zugriff auf andere Felder
    }

@app.post("/wall_lighting_mode")
async def set_wall_lighting_mode(payload: WallLightingMode):
    global wall_lighting_mode
    if payload.mode in ["dark", "bright"]:
        wall_lighting_mode = payload.mode
        return {"message": f"Wall lighting mode set to {payload.mode}"}
    else:
        return JSONResponse(status_code=400, content={"message": "Invalid mode. Use 'dark' or 'bright'."})

@app.get("/wall_lighting", response_class=HTMLResponse)
async def get_wall_lighting():
    html_content = return_wall_lighting_html(APP_PATH_PREFIX)
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

    html_content = "<h1>Wall Selector</h1>"
    for wall in walls:
        if "id" not in wall or "name" not in wall:
            raise HTTPException(status_code=502, detail="Incomplete wall data from Crux")
        wall_id = quote(str(wall["id"]), safe="")
        wall_name = escape(str(wall["name"]))
        image_url = escape(str(wall.get("image_url") or ""), quote=True)
        html_content += (
            f'<div style="margin-bottom:20px;"><h2>{wall_name}</h2>'
            f'<a href="{APP_PATH_PREFIX}/wallcreation?id={wall_id}"><img src="{image_url}" '
            f'alt="{wall_name}" style="max-width:300px;"></a></div>'
        )
    return HTMLResponse(content=html_content)

@app.get ("/wallcreation")
async def wall_creation(id: str = ""):
    id = id.strip()
    if id:
        result = requests.get("https://www.cruxapp.ca/api/v1/gym_walls/"+id, headers=auth_header, verify=False)
        wall = json.loads(result.text)
        db = SessionLocal()
        existing_wall = db.query(WallDB).filter(WallDB.id == wall['id']).first()

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

        db.commit()  # Save changes to the database
        db.close()
        html_content = returnwallhtml(wall, APP_PATH_PREFIX)
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

    holds2led = ledCalculation(lr, ll, ur, ul, c, r, existing_wall.holds, grid )
    for h in holds2led:
        hold_key = wall_hold_key(payload.wallid, h)
        existing_hold = db.query(Hold2ledDB).filter(Hold2ledDB.holdid == hold_key).first()
        if existing_hold:
            existing_hold.ledid = holds2led[h]


        else:
            hold2db = Hold2ledDB(
                holdid=hold_key,
                ledid=holds2led[h]
            )
            db.add(hold2db)
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
