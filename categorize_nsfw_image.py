#!/usr/bin/python3
import hashlib
import os
import sqlite3
import re
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from functions import read_web, content_type_image_regex
import sys
import opennsfw2 as n2
import numpy as np

nsfw_directory = "images/nsfw/"
min_image_res = 64 * 64
save_nsfw=True

model = n2.make_open_nsfw_model()
con = sqlite3.connect("crawler.db", timeout=60)

nsfw_min_probability=.78

def update_visited(url, visited,is_nsfw,content_type,resolution):
    cur = con.cursor()
    cur.execute(
        "update urls set (visited,isnsfw,content_type,resolution) = (?,?,?,?) where url = ?",
        (visited,is_nsfw,content_type, resolution, url),
    )
    con.commit()

def get_unvisited_img():
    cur = con.cursor()
    images = cur.execute(
        'select url from urls where source = "img" and visited = 0 order by random()'
    ).fetchall()
    con.commit()
    return list(zip(*images))[0]

def categorize_image(url):
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
    if img.mode == "CMYK":
        img = img.convert("RGB")
    image = n2.preprocess_image(img, n2.Preprocessing.YAHOO)
    inputs = np.expand_dims(image, axis=0)  # Add batch axis (for single image).
    predictions = model.predict(inputs)
    sfw_probability, nsfw_probability = predictions[0]
    if nsfw_probability>nsfw_min_probability:
        is_nsfw=1
        print('porn {} {} {}'.format(nsfw_probability,filename,url))
        if save_nsfw:
            img.save(nsfw_directory + filename, "PNG")
    if response[1]:
        return [response[1],width*height,float(nsfw_probability)]
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
    is_nsfw=0
    try:
        save_result=categorize_image(image)
    except OSError:
        continue
    if save_result:
        content_type,resolution,is_nsfw=save_result
        if is_image(content_type):
            update_visited(image, 1,is_nsfw, content_type,resolution)
        elif resolution > 0:
            update_visited(image, 1,is_nsfw, content_type,resolution)
        else:
            update_visited(image, 0,is_nsfw, content_type,resolution)            
    else:
        update_visited(image, 2,is_nsfw,'error',0)
con.close()
