#!/usr/bin/python3
import hashlib
import os
import sqlite3
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from functions import read_web

images_directory = "images/"
min_image_res = 300 * 200

# Number of characters from file hash used for directory creation.
# Keep in mind that more than 10k sub-directories or files per directory might be too much.
# 1=16 directories
# 2=256 directories
# 3=4096 directories
# 4=65536 directories
dir_chars = 1

con = sqlite3.connect("crawler.db", timeout=60)


def update_visited(url, visited):
    cur = con.cursor()
    cur.execute(
        "update urls set (visited) = (?) where url = ?",
        (visited, url),
    )
    con.commit()


def get_unvisited_img():
    cur = con.cursor()
    images = cur.execute(
        'select url from urls where source = "img" and visited = 0 order by random()'
    ).fetchall()
    con.commit()
    return list(zip(*images))[0]


def save_image(url):
    response = read_web(url)
    if not response:
        return False
    try:
        img = Image.open(BytesIO(response[0]))
        width, height = img.size
        if (width * height) < min_image_res:
            return False
    except UnidentifiedImageError as e:
        return False
    except Image.DecompressionBombError as e:
        return False
    except OSError:
        return False
    filename = hashlib.sha512(img.tobytes()).hexdigest() + ".png"
    directory = filename[0:dir_chars]
    dirExists = os.path.exists(images_directory + directory)
    if not dirExists:
        os.makedirs(images_directory + directory)
    fileExists = os.path.exists(images_directory + directory + "/" + filename)
    if not fileExists:
        if img.mode == "CMYK":
            img = img.convert("RGB")
        img.save(images_directory + directory + "/" + filename, "PNG")


for image in get_unvisited_img():
    save_image(image)
    update_visited(image, 1)
con.close()
