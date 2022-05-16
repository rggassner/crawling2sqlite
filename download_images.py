#!/usr/bin/python3
import hashlib
import os
import sqlite3
import re
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from functions import read_web, content_type_image_regex

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

def update_visited(url, visited,content_type,resolution):
    cur = con.cursor()
    cur.execute(
        "update urls set (visited,content_type,resolution) = (?,?,?) where url = ?",
        (visited,content_type, resolution, url),
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
    save=True
    response = read_web(url)
    if not response:
        return False
    try:
        img = Image.open(BytesIO(response[0]))
        width, height = img.size
        if (width * height) < min_image_res:
            save=False
    except UnidentifiedImageError as e:
        #SVG using cairo in the future
        return False
    except Image.DecompressionBombError as e:
        return False
    except OSError:
        return False
    filename = hashlib.sha512(img.tobytes()).hexdigest() + ".png"
    directory = filename[0:dir_chars]
    dirExists = os.path.exists(images_directory + directory)
    if not dirExists and save:
        os.makedirs(images_directory + directory)
    fileExists = os.path.exists(images_directory + directory + "/" + filename)
    if not fileExists and save:
        if img.mode == "CMYK":
            img = img.convert("RGB")
        img.save(images_directory + directory + "/" + filename, "PNG")
    if response[1]:
        return [response[1],width*height]
    else:
        return False

def is_image(content_type):
    for regexp in content_type_image_regex:
        cre = re.compile(regexp, flags=re.I | re.U)
        m = cre.search(content_type)
        if m:
            return True
    return False
    
for image in get_unvisited_img():
    resolution=0
    try:
        save_result=save_image(image)
    except OSError:
        continue
    if save_result:
        content_type,resolution=save_result
        if is_image(content_type):
            update_visited(image, 1, content_type,resolution)
        elif resolution > 0:
            update_visited(image, 1, content_type,resolution)
        else:
            update_visited(image, 0, content_type,resolution)            
    else:
        update_visited(image, 2, 'error',0)
con.close()
