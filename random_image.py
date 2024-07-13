from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
import json
import os
import datetime
import sys
import argparse
import random

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

ua = UserAgent(
    browsers=["chrome", "firefox"],
    os=["windows, macos", "linux", "android"],
    fallback = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

os.makedirs("random", exist_ok=True)

while(True):

    current_image = random.randrange(0, 36**6)

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

        with open("random_error_state.json", "w", encoding="utf-8") as f:
                msg = f"Lightshot error occured at image {current_image}.png!"
                print(msg)

                f.write(json.dumps({
                        "type": "lightshot",
                        "image": current_image,
                        "status": r.status_code,
                        "lightshot_url": lightshot_url,
                        "lightshot_headers": dict(r.headers)
                    },
                    indent="\t"))     
        continue
    else:
        soup = BeautifulSoup(r.text, "html.parser")

        img = soup.select_one("#screenshot-image")

        #Check for missing image
        if img is None or img.get("src") == "//st.prntscr.com/2023/07/24/0635/img/0_173a7b_211be8ff.png":

            msg = f"Missing image {current_image_name}.png"
            print(msg)
            continue

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

                    current_image += 1
                    continue

                with open("random_error_state.json", "w", encoding="utf-8") as f:
                    msg = f"Imgur error occured at image {current_image_name}.png!"
                    print(msg)

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
                continue
            else:
                msg = f"Saving image {current_image_name}.png..."
                print(msg)

                items = os.listdir("random")
                files = [item for item in items if os.path.isfile(os.path.join("random", item))]

                with open(f"random/{len(files):04}_{current_image_name}.png", "wb") as f:
                    f.write(imgreq.content)

                break