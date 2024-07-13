from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
import json
import os
import datetime
import sys
import argparse

#=======================================================================================================

#6 characters, from an alphabet of 36 letters (26 latin + 10 numbers)
#lowercase ascii: 97-122
#numbers: 48-57

def int_to_img(num):

    #0->lsd
    #5->msd
    digits = [0, 0, 0, 0, 0, 0]
    res = ""

    for i in range(5, -1, -1):
        digits[i] = num // 36**i
        num %= 36**i

    for d in digits:
        if d <= 9:
            res += str(d)
        elif d <= 35:
            res += chr(d + 87)

    return res[::-1]

#=======================================================================================================

def img_to_int(img_str):

    if len(img_str) != 6:
        raise Exception("Image ID must be 6 characters long")

    res = 0

    for i, char in enumerate(img_str):
        ascii = ord(char)

        if ascii >= 48 and ascii <= 57:
            res += (ascii - 48)*36**(5-i)
        elif ascii >= 97 and ascii <= 122:
            res += (ascii - 87)*36**(5-i)

    return res

#=======================================================================================================

def save_state(state_str, current_image):

    saved_state = None

    if os.path.exists("state.json"):
        with open("state.json", "r", encoding="utf-8") as f:
            saved_state = json.load(f)

        saved_state[state_str] = {"img": current_image}
    else:
        saved_state= {state_str:{"img": current_image}}
    
    with open("state.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(saved_state, indent="\t"))

#=======================================================================================================

def load_state(state_str):

    state = None

    #Images from 000000 to 0zzzzz are invalid
    default_state = {"img": img_to_int("100000")}

    if os.path.exists("state.json"):
        with open("state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
            state = state.get(state_str, default_state)
    else:
        state = default_state

    return state

#=======================================================================================================

def timestamp():
    return f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "

#=======================================================================================================

parser = argparse.ArgumentParser(description='Lightshot scraper', allow_abbrev=False)
parser.add_argument('--state', action=argparse._StoreAction, default="default")
parser.add_argument('--start', action=argparse._StoreAction, default=None)
parser.add_argument('--str', action=argparse.BooleanOptionalAction, default=False)
args = parser.parse_args()

ua = UserAgent(
    browsers=["chrome", "firefox"],
    os=["windows, macos", "linux", "android"],
    fallback = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

state = load_state(args.state)

current_image = None

if args.start is not None:
    current_image = (img_to_int(args.start) if args.str else int(args.start))
else:
    current_image = state["img"]

os.makedirs(f"images/{args.state}", exist_ok=True)
os.makedirs("sessions", exist_ok=True)

sessname = f"Session_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"
sess = open(f"sessions/{sessname}.txt", "w")
sess.write(f"{sessname} [current_image = {current_image}, state = {args.state}]\n==========================================================================================\n")

try:
    while(True):

        user_agent = ua.random

        headers =  {
            "User-Agent": user_agent,
            "authority": "prnt.sc",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US",
            "Cache-Control": "max-age=0",
            "Priority": "u=0, i"
        }

        current_image_name = int_to_img(current_image)

        lightshot_url = "https://prnt.sc/" + int_to_img(current_image)

        r = requests.get(lightshot_url, headers=headers)

        if not r.ok:

            with open("error_state.json", "w", encoding="utf-8") as f:
                    msg = f"Lightshot error occured at image {current_image}.png!"
                    print(msg)
                    sess.write(timestamp() + msg)

                    f.write(json.dumps({
                            "type": "lightshot",
                            "image": current_image,
                            "status": r.status_code,
                            "lightshot_url": lightshot_url,
                            "lightshot_headers": dict(r.headers)
                        },
                        indent="\t"))     
            break
        else:
            soup = BeautifulSoup(r.text, "html.parser")

            img = soup.select_one("#screenshot-image")

            #Check for missing image
            if img is None or img.get("src") == "//st.prntscr.com/2023/07/24/0635/img/0_173a7b_211be8ff.png":

                msg = f"Missing image {current_image_name}.png"
                print(msg)
                sess.write(timestamp() + msg + "\n")

            else:

                #If image is not missing

                imgreq = requests.get(img.get("src"), headers={
                    'Accept': 'image/png',
                    "User-Agent": user_agent,
                    "Referer": "https://imgur.com/"
                    })
                
                if not imgreq.ok:

                    if imgreq.status_code in  [403, 404]:
                        msg = f"Skipping image {current_image_name}.png (ERROR {imgreq.status_code})"
                        print(msg)
                        sess.write(timestamp() + msg + "\n")

                        current_image += 1
                        continue

                    with open("error_state.json", "w", encoding="utf-8") as f:
                        msg = f"Imgur error occured at image {current_image_name}.png!"
                        print(msg)
                        sess.write(timestamp() + msg + "\n")
                        f.write(json.dumps({
                                "type": "imgur",
                                "image": current_image,
                                "status": imgreq.status_code,
                                "lightshot_url": lightshot_url,
                                "imgur_url": img.get("src"),
                                "lightshot_headers": dict(r.headers),
                                "imgur_headers": dict(imgreq.headers)
                            },
                            indent="\t"))
                    break
                else:
                    msg = f"Saving image {current_image_name}.png..."
                    print(msg)
                    sess.write(timestamp() + msg + "\n")
                    with open(f"images/{args.state}/{current_image:010d}_{current_image_name}.png", "wb") as f:
                        f.write(imgreq.content)

        current_image += 1    
        
except KeyboardInterrupt:
    msg = "Crawler stopped. Saving state..."
    print(msg)
    sess.write(timestamp() + msg + "\n")
finally:
    save_state(args.state, current_image - 1 if current_image > 0 else 0)
    sess.close()