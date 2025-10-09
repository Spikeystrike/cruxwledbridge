import json
import requests
import numpy as np
import config
def generate_grid(lu, ru, rb, lb, r, c):
    grid = {}  # Dictionary zur Speicherung der Punkte, Schlüssel ist die ID
    # Interpolate die Positionen für alle Reihen (von links oben nach links unten und rechts oben nach rechts unten)
    for i in range(r):
        # Division durch Null vermeiden, wenn es nur eine Reihe gibt
        t = i / (r - 1) if r > 1 else 0.0
        left_point = ((1 - t) * np.array(lu) + t * np.array(lb)).astype(int)  # Position entlang der linken Seite
        right_point = ((1 - t) * np.array(ru) + t * np.array(rb)).astype(int)  # Position entlang der rechten Seite

        # Reihe von unten gezählt (0-basiert)
        row_from_bottom = r - 1 - i

        # Interpolate die Punkte innerhalb der aktuellen Reihe (von links nach rechts)
        for j in range(c):
            # Division durch Null vermeiden, wenn es nur eine Spalte gibt
            s = j / (c - 1) if c > 1 else 0.0
            point = ((1 - s) * left_point + s * right_point).astype(int)  # Position entlang der aktuellen Zeile

            # Berechne die ID in "Schlangenlinien"-Form von unten
            if (row_from_bottom % 2) == 1:  # Ungerade Reihen von unten (1, 3, ...): von links nach rechts
                led_id = (row_from_bottom * c) + j
            else:  # Gerade Reihen von unten (0, 2, ...): von rechts nach links
                led_id = (row_from_bottom * c) + (c - 1 - j)
            
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
    c1 = []
    c2 = []
    c3 = []
    for i in range(0, 400):
        if i < 100:
            if i not in led:
                if mode == "bright":
                    c1.append(i)
                    c1.append("333333")
            else:
                c1.append(i)
                c1.append(led[i])
        elif i < 250:
            if i not in led:
                if mode == "bright":
                    c2.append(i-100)
                    c2.append("333333")
            else:
                c2.append(i-100)
                c2.append(led[i])
        else:
            if i not in led:
                if mode == "bright":
                    c3.append(i-250)
                    c3.append("333333")
            else:
                c3.append(i-250)
                c3.append(led[i])
    
    
    
 
    req = '{"on":false,"bri":255}'
    r1 = requests.post("http://10.42.250.20/json/state", data=req)
    r2 = requests.post("http://10.42.250.21/json/state", data=req)
    r3 = requests.post("http://10.42.250.22/json/state", data=req)
    # Prepare the base request for each controller based on the mode
    base_req = {"on": True, "bri": 255, "seg": {"i": []}}

    # Send commands to each controller
    if len(c1) > 0:
        req1 = base_req.copy()
        req1["seg"]["i"] = c1
        requests.post("http://10.42.250.20/json/state", json=req1)
    if len(c2) > 0:
        req2 = base_req.copy()
        req2["seg"]["i"] = c2
        requests.post("http://10.42.250.21/json/state", json=req2)
    if len(c3) > 0:
        req3 = base_req.copy()
        req3["seg"]["i"] = c3
        requests.post("http://10.42.250.22/json/state", json=req3)
    return led


def lightUpHoldId(holdid, color):
    req = '{"on":false,"bri":255}'
    r1 = requests.post("http://10.42.250.20/json/state", data=req)
    r2 = requests.post("http://10.42.250.21/json/state", data=req)
    r3 = requests.post("http://10.42.250.22/json/state", data=req)
    if holdid < 100:
        hold=[holdid, color]
        req = '{"on":true,"bri":255,"seg":{"i":'+json.dumps(hold)+'}}'
        r = requests.post("http://10.42.250.20/json/state", data=req)
    elif holdid < 250:
        hold=[holdid-100, color]
        req = '{"on":true,"bri":255,"seg":{"i":'+json.dumps(hold)+'}}'
        r = requests.post("http://10.42.250.21/json/state", data=req)
    else:
        hold=[holdid-250, color]
        req = '{"on":true,"bri":255,"seg":{"i":'+json.dumps(hold)+'}}'
        r = requests.post("http://10.42.250.22/json/state", data=req)

    return r