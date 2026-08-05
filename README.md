# CRUX App to WLED Bridge
This small python script is a quick and dirty Crux App to WLED Bridge. The workflow is following:

## Setup Container 
To get the bridge running, i recommend to use a proxy for authenticating all urls but https://<bridge>/viewed. 
you can build the container by building the docker file. i would recommend to mount the configuration and database directories:
here a example docker-compose setup (without authenticaiton):
```yaml
services:
  bwall:
    build: ./code
    container_name: cruxwledbridge
    restart: unless-stopped
    user: 1018:100
    expose:
      - "80"
    environment:
      VIRTUAL_HOST: ${VIRTUAL_HOST:?Set VIRTUAL_HOST in .env}
      VIRTUAL_PORT: "80"
      VIRTUAL_PATH: /cruxwledbridge/
      VIRTUAL_DEST: /
      APP_PATH_PREFIX: /cruxwledbridge
    volumes:
      - /share/Docker-Appdata/cruxwledbridge/db:/code/db
      - /share/Docker-Appdata/cruxwledbridge/config:/code/config
    networks:
      - proxy-tier

networks:
  proxy-tier:
    external: true
    name: ${PROXY_NETWORK:-nextcloud_proxy-tier}
```
The SQLite database is stored at `/code/db/app.db`. The configuration file must be available as `/code/config/config.py` (for the example above: `/share/Docker-Appdata/cruxwledbridge/config/config.py`). Copy `config/config.example.py` to that location and adjust it before starting the container. Make sure the mounted host directories are readable or writable as required by the configured container user (`1018:100`).

Set the public hostname in a local `.env` file before starting the stack, for example `VIRTUAL_HOST=bridge.example.com`. The file is ignored by Git. The example uses the existing Nextcloud `nginx-proxy` and exposes the bridge at `https://<VIRTUAL_HOST>/cruxwledbridge/`. It does not publish another host port. `PROXY_NETWORK` must be the Docker network used by the Nextcloud proxy; it defaults to `nextcloud_proxy-tier`. You can find the actual name with `docker network ls` and override it, for example with `PROXY_NETWORK=myproject_proxy-tier docker compose up -d --build`.

The proxy image must support nginx-proxy's `VIRTUAL_PATH` and `VIRTUAL_DEST` settings. The existing Nextcloud service already manages the certificate for this hostname, so the bridge does not request a second certificate.

After that you can start the container and access it under `https://<VIRTUAL_HOST>/cruxwledbridge/`.

## Setup Bridge
1) Create a Gym in the CRUX App and create a wall. 
2) Get your API key from the CRUX App and insert it into `config/config.py` (there is a `config/config.example.py` as an example)
3) Configure `wled_controllers` and `hole2LEDS` in `config/config.py`. `wled_controllers` maps each WLED controller to an inclusive range of global LED IDs. The example uses the documentation-only address `192.0.2.10` for IDs `0-399`; replace it with the address of your WLED controller. The bridge translates these IDs to zero-based controller-local IDs and sends colors through WLED's `/json/state` API. Crux holds are stored in the database as `<wall_id>_<hold_id>`; `hole2LEDS` maps the resulting logical grid LED ID to one or more physical LED IDs. The example uses a one-to-one mapping for a 20x20 wall with one LED per hold.
2) open `https://<bridge>/cruxwledbridge/listwalls?gym=<gymslug>` and select the wall you want to map
3) Input your grid size, then select whether the grid is standard or alternating. In alternating mode, `C` is the total number of possible horizontal positions and must be even. For example, with `C=22`, the first row uses positions 1, 3, ..., 21 and the next row positions 2, 4, ..., 22, resulting in 11 mapped LEDs per row. Tap the grid corners in the order top left, top right, bottom right, bottom left and press send.
4) configure a webhook for the user.viewed action --> `https://<bridge>/cruxwledbridge/viewed`
5) When you press on a climb, it should light up the right holes on the wall. Hold mappings are stored as `<wall_id>_<hold_id>`, so the webhook payload must include `payload.wall_id`.
6) enjoy climbing!

## Hardware used
I use following hardware on the wall:
- LED Strips: WS2811 DC5V/12V 12mm Vollfarb-LED-Pixel-Lichterkette (https://de.aliexpress.com/item/1005009421177129.html?spm=a2g0o.order_list.order_list_main.25.6c195c5f9ulSae&gatewayAdapt=glo2deu)
- LED Controllers: GLEDOPTO ESP32 WELD LED Controller (https://de.aliexpress.com/item/1005009615006206.html?spm=a2g0o.order_list.order_list_main.20.6c195c5f9ulSae&gatewayAdapt=glo2deu)
- Appropriate 5v power supplies
- Under every hold i 3d printed a transparent pla washer to spread the LED Light. I also used a mirrorfilm on the backside of the hole to bounce off light. 
- I drilled 2x 12mm holes next to the screw-hole, with a 2.5cm spacing in between - very similar to the kilter layout. 

if you have any more questions you can reach me in the CRUX App Discord.

## Multiple WLED controllers

Add one entry per controller. Ranges must not overlap:

```python
wled_controllers = [
    {"ip": "192.0.2.10", "start": 0, "end": 399},
]
```

## Setup-Picture
Thats how it looks like after beeing finished:
![Boulderwall Setup](example.jpg)
