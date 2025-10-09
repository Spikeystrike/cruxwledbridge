# CRUX App to WLED Bridge
This small python script is a quick and dirty Crux App to WLED Bridge. The workflow is following:

## Setup Container 
To get the bridge running, i recommend to use a proxy for authenticating all urls but https://<bridge>/viewed. 
you can build the container by building the docker file. i would recommend to mount the config.py and app.db:
here a example docker-compose setup (without authenticaiton):
```
services:
  bwall:
    build: ./cruxledbridge
    restart: unless-stopped
    ports:
      - 8080:80
    volumes:
      - ./app.db:/code/app.db
      - ./config.py:/code/app/config.py
```
after that you can startup your container and access it under https://<bridge> 

## Setup Bridge
1) Create a Gym in the CRUX App and create a wall. 
2) Get your API key from the CRUX App and insert it into config.py (there is a config.example.py as an example)
3) Map your LEDs to the hold ids. Your hold IDs are all possible places to place a hold (if you have for example a 13x13 grid, you have 169 holdIDs) - you may have to edit the code for LEDs because it is very individual for my setup. all individual stuff is in utils.py
2) open <bridge>/listwalls?gym=<gymslug> and select the wall you want to map 
3) input your grid size, then tap on the top hole, top left, bottom left, bottom right hole an press send
4) configure a webhook for the user.viewed action --> https://<bridge>/viewed 
5) When you press on a climb, it should light up the right holes on the wall
6) enjoy climbing!

## Hardware used
I use following hardware on the wall:
- LED Strips: WS2811 DC5V/12V 12mm Vollfarb-LED-Pixel-Lichterkette (https://de.aliexpress.com/item/1005009421177129.html?spm=a2g0o.order_list.order_list_main.25.6c195c5f9ulSae&gatewayAdapt=glo2deu)
- LED Controllers: GLEDOPTO ESP32 WELD LED Controller (https://de.aliexpress.com/item/1005009615006206.html?spm=a2g0o.order_list.order_list_main.20.6c195c5f9ulSae&gatewayAdapt=glo2deu)
- Appropriate 5v power supplies
- Under every hold i 3d printed a transparent pla washer to spread the LED Light. I also used a mirrorfilm on the backside of the hole to bounce off light. 
- I drilled 2x 12mm holes next to the screw-hole, with a 2.5cm spacing in between - very similar to the kilter layout. 

if you have any more questions you can reach me in the CRUX App Discord.

## Todos
The WLED API Setup is VERY individual right now, i will refactor it when i have time.

## Setup-Picture
Thats how it looks like after beeing finished:
![Boulderwall Setup](example.jpg)