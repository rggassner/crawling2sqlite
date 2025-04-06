#!venv/bin/python3
import re
from config import *
import sqlite3
from urllib.parse import urlsplit
from fake_useragent import UserAgent
from seleniumwire import webdriver
from seleniumwire.utils import decode
import time
import os
from urllib.parse import unquote,urljoin,urlparse
from bs4 import BeautifulSoup
from functions import *
from pathlib import PurePosixPath
import bs4.builder
#import opennsfw2 as n2
from PIL import Image, UnidentifiedImageError
import hashlib
import numpy as np
import signal
import pymysql
from io import BytesIO
import argparse


url_functions = []
content_type_functions = []

##used to generate wordlist
soup_tag_blocklist = [
    "[document]",
    "noscript",
    "header",
    "html",
    "meta",
    "head",
    "input",
    "script",
    "style",
]

class DatabaseConnection:
    def __init__(self, DATABASE="sqlite"):
        self.DATABASE = DATABASE
        self.con = None
        self.cur = None
        if DATABASE == "sqlite":
            self.con = sqlite3.connect(SQLITE_FILE)
            self.con.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
            self.cur = self.con.cursor()
        elif DATABASE == "mariadb":
            self.con = pymysql.connect(
                host=MARIADB_HOST,
                user=MARIADB_USER,
                password=MARIADB_PASSWORD,
                database=MARIADB_DATABASE,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cur = self.con.cursor()
        else:
            raise ValueError("Unsupported database.")
    
    def commit(self):
        if self.con:
            self.con.commit()
    
    def close(self):
        if self.con:
            self.con.close()

def db_create_database(initial_url, db):
    print("Creating database.")
    try:
        host = urlsplit(initial_url)[1]
    except ValueError:
        return False

    create_urls_table = '''
    CREATE TABLE IF NOT EXISTS urls (
        url VARCHAR(2083) NOT NULL,
        visited BOOLEAN,
        isopendir BOOLEAN,
        isnsfw FLOAT,
        content_type TEXT,
        source TEXT,
        words MEDIUMTEXT,
        host TEXT,
        parent_host TEXT,
        resolution INTEGER,
        UNIQUE (url)
    )'''

    create_emails_table = '''
    CREATE TABLE IF NOT EXISTS emails (
        url VARCHAR(2083) NOT NULL,
        email TEXT,
        UNIQUE (url, email)
    )'''

    db.cur.execute(create_urls_table)
    db.cur.execute(create_emails_table)

    insert_query = """
    INSERT INTO urls (url, visited, isopendir, isnsfw, content_type, source, words, host)
    VALUES (%s, 0, 0, 0, '', 'href', '', %s)
    """
    
    if db.DATABASE == "sqlite":
        db.cur.execute(insert_query.replace("%s", "?"), (initial_url, host))
    else:
        db.cur.execute(insert_query, (initial_url, host))
    
    db.commit()
    return True

## Verify if host is in a blocklist.
def is_host_block_listed(url):
    for regex in host_regex_block_list:
        if re.search(regex, url, flags=re.I | re.U):
            return True
    return False

## Verify if url is in a blocklist.
def is_url_block_listed(url):
    for regex in url_regex_block_list:
        if re.search(regex, url, flags=re.I | re.U):
            return True
    return False

## Verify if url is in a allowlist.
def is_host_allow_listed(url):
    for regex in host_regex_allow_list:
        if re.search(regex, url, flags=re.I | re.U):
            return True
    return False

def remove_jsessionid_with_semicolon(url):
    pattern = r';jsessionid=[^&?]*'
    cleaned_url = re.sub(pattern, '', url)
    return cleaned_url

def db_insert_if_new_url(url='', visited='', source='', content_type="", words="", isnsfw='', resolution='', parent_host='', db=None):
    try:
        host = urlsplit(url)[1]
    except ValueError:
        return False

    url = remove_jsessionid_with_semicolon(url)

    query = "INSERT OR IGNORE INTO urls (url, visited, content_type, source, words, host, isnsfw, resolution, parent_host) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)" \
        if db.DATABASE == "sqlite" else "INSERT IGNORE INTO urls (url, visited, content_type, source, words, host, isnsfw, resolution, parent_host) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"

    db.cur.execute(query, (url, visited, content_type, source, words, host, isnsfw, resolution, parent_host))
    db.commit()

    return True

def db_count_url(url, db):
    try:
        query = "SELECT count(url) FROM urls WHERE url = ?" if db.DATABASE == "sqlite" else "SELECT count(url) FROM urls WHERE url = %s"
        db.cur.execute(query, (url,))
        count_url = db.cur.fetchone()
        db.commit()
        return count_url['count(url)']
    except (sqlite3.OperationalError, pymysql.MySQLError) as e:
        print("Error:", e)
        return 0

def db_insert_email(url='', email='', db=None):
    try:
        query = "INSERT OR IGNORE INTO emails (url, email) VALUES (?, ?)" if db.DATABASE == "sqlite" else "INSERT IGNORE INTO emails (url, email) VALUES (%s, %s)"
        db.cur.execute(query, (url, email))
        db.commit()
        return True
    except (sqlite3.OperationalError, pymysql.MySQLError) as e:
        print("Error:", e)
        return False

def db_update_url_isopendir(url, db):
    try:
        query = "UPDATE urls SET isopendir = ? WHERE url = ?" if db.DATABASE == "sqlite" else "UPDATE urls SET isopendir = %s WHERE url = %s"
        db.cur.execute(query, ('1', url))
        db.commit()
        return True
    except (sqlite3.OperationalError, pymysql.MySQLError) as e:
        print("Error:", e)
        return False

def db_update_url_isnsfw(url, isnsfw, db):
    try:
        query = "UPDATE urls SET isnsfw = ? WHERE url = ?" if db.DATABASE == "sqlite" else "UPDATE urls SET isnsfw = %s WHERE url = %s"
        db.cur.execute(query, (isnsfw, url))
        db.commit()
        return True
    except (sqlite3.OperationalError, pymysql.MySQLError) as e:
        print("Error:", e)
        return False

def db_update_url(url='', content_type='', visited='', words='', source='', db=None):
    try:
        query = "UPDATE urls SET visited = ?, content_type = ?, words = ?, source = ? WHERE url = ?" if db.DATABASE == "sqlite" else "UPDATE urls SET visited = %s, content_type = %s, words = %s, source = %s WHERE url = %s"
        db.cur.execute(query, (visited, content_type, words, source, url))
        db.commit()

        if url.endswith('/'):
            url = url[:-1]
            db.cur.execute(query, (visited, content_type, words, source, url))
            db.commit()

        return True
    except (sqlite3.OperationalError, pymysql.MySQLError) as e:
        print("Error:", e)
        return False

def get_random_unvisited_domains(db):
    try:
        query = """
        SELECT url, host FROM (
            SELECT url, host, ROW_NUMBER() OVER (PARTITION BY host ORDER BY RANDOM()) AS row_num
            FROM urls WHERE visited = 0 AND source != 'access'
        ) WHERE row_num = 1 ORDER BY RANDOM();
        """ if db.DATABASE == "sqlite" else """
        SELECT url, host FROM (
            SELECT url, host, ROW_NUMBER() OVER (PARTITION BY host ORDER BY RAND()) AS row_num
            FROM urls WHERE visited = 0 AND source != 'access'
        ) AS subquery WHERE row_num = 1 ORDER BY RAND();
        """
        
        db.cur.execute(query)
        random_url = db.cur.fetchall()
        return random_url
    except (sqlite3.OperationalError, pymysql.MySQLError) as e:
        if "no such table" in str(e) or "Table" in str(e):
            print("Database tables missing. Creating now...")
            db_create_database(INITIAL_URL,db=db)
        else:
            print("Error:", e)
    return []


def sanitize_url(url):
    url = url.strip()
    url = url.rstrip()      
    url = re.sub(r'^“(.*)"', r"\1", url)
    url = re.sub(r"^”(.*)”$", r"\1", url)
    url = re.sub(r"^“(.*)“$", r"\1", url)
    url = re.sub(r'^"(.*)"$', r"\1", url)
    url = re.sub(r"^“(.*)”$", r"\1", url)
    url = re.sub(r"^‘(.*)’$", r"\1", url)
    url = re.sub(r'^"(.*)\'$', r"\1", url)
    url = re.sub(r"^\'(.*)\'$", r"\1", url)
    url = re.sub(r'^”(.*)″$', r"\1", url)        
    url = re.sub(r"^(.+)#.*$", r"\1", url)
    url = re.sub("^www.", "http://www.", url)
    if re.search(r"^http:[^/][^/]", url):
        url = re.sub("^http:", "http://", url)
    if re.search(r"^http:/[^/]", url):
        url = re.sub("^http:/", "http://", url)
    if re.search(r"^https:[^/][^/]", url):
        url = re.sub("^https:", "https://", url)
    if re.search(r"^https:/[^/]", url):
        url = re.sub("^https:/", "https://", url)
    url = re.sub("^ps://", "https://", url)          
    url = re.sub("^ttps://", "https://", url)    
    url = re.sub("^[a-zA-Z.“(´]https://", "https://", url)  
    url = re.sub("^[a-zA-Z.“(´]http://", "http://", url)  
    url = re.sub("^https[a-zA-Z.“(´]://", "https://", url)  
    url = re.sub("^http[.“(´]://", "http://", url) 
    url = re.sub("^htto://", "http://", url)  
    url = re.sub("^https: / /", "https://", url)  
    url = re.sub("^://", "https://", url)      
    url = re.sub("^htt://", "http://", url)    
    url = re.sub("^Mh ttp://", "http://", url) 
    url = re.sub("^htpps://", "https://", url) 
    url = re.sub("^httpp://", "https://", url)     
    url = re.sub("^http:s//", "https://", url)
    url = re.sub("^hthttps://", "https://", url)
    url = re.sub("^httsp://", "https://", url)
    url = re.sub("^htts://", "https://", url)    
    url = re.sub("^htp://http//", "http://", url)
    url = re.sub("^htp://", "http://", url)
    url = re.sub("^htttps://", "https://", url)
    url = re.sub("^https:https://", "https://", url)
    url = re.sub("^hhttp://", "http://", url)
    url = re.sub("^http:/http://", "http://", url)
    url = re.sub("^https https://", "https://", url)
    url = re.sub("^httpshttps://", "https://", url)
    url = re.sub("^https://https://", "https://", url)
    url = re.sub('^"https://', "https://", url)
    url = re.sub("^http:www", "http://www", url)
    url = re.sub("^httpd://", "https://", url)
    url = re.sub("^htps://", "https://", url)    
    url = re.sub("^https: //", "https://", url)
    url = re.sub("^http2://", "https://", url)
    url = re.sub("^https : //", "https://", url)
    url = re.sub("^htttp://", "http://", url)
    url = re.sub("^ttp://", "http://", url)
    url = re.sub("^https%3A//", "https://", url)
    url = re.sub("^%20https://", "https://", url)
    url = re.sub("^%20http://", "http://", url)
    url = re.sub("^%22mailto:", "mailto:", url)
    url = re.sub("^httpqs://", "https://www.", url)
    return url

def get_words(soup, content_url):
    output = ""
    text = soup.find_all(string=True)
    for t in text:
        if t.parent.name not in soup_tag_blocklist:
            output += "{} ".format(t)
    return " ".join(list(set(output.split())))

def get_directory_tree(url):
    #Host will have scheme, hostname and port
    host='://'.join(urlsplit(url)[:2])
    dtree=[]
    for iter in range(1,len(PurePosixPath(unquote(urlparse(url).path)).parts[0:])):
        dtree.append(str(host+'/'+'/'.join(PurePosixPath(unquote(urlparse(url).path)).parts[1:-iter])))
    return dtree

def is_open_directory(content, content_url):
    host=urlsplit(content_url)[1]
    pattern=r'<title>Index of /|<h1>Index of /|\[To Parent Directory\]</A>|<title>'+re.escape(host)+' - /</title>|_sort=\'name\';SortDirsAndFilesName();'
    if re.findall(pattern,content):
        print('### Is open directory -{}-'.format(content_url))
        db_update_url_isopendir(content_url, db)
        return True

def function_for_url(regexp_list):
    def get_url_function(f):
        for regexp in regexp_list:
            url_functions.append((re.compile(regexp, flags=re.I | re.U), f))
        return f
    return get_url_function

## url unsafe {}|\^~[]`
## regex no need to escape '!', '"', '%', "'", ',', '/', ':', ';', '<', '=', '>', '@', and "`"
@function_for_url(
    [
        r"^(\/|\.\.\/|\.\/)",
        r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´ç�í¦ã]+$",
        r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´ç]*[\?\/][0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬:\"¶ç´™*]+$",
    ]
)
def relative_url(args):
    out_url = urljoin(args['parent_url'], args['url'])
    parent_host=urlsplit(args['parent_url'])[1]
    db_insert_if_new_url(url=out_url, visited=0, source="href",parent_host=parent_host,db=args['db'])
    return True


@function_for_url(
    [
        r"(\{|\[|\||\}|\]|\~|\^|\\)",
    ]
)
def unsafe_character_url(args):
    return True


@function_for_url(url_all_others_regex)
def do_nothing_url(args):
    # Do nothing with these regex. They are kept here only as a guideline if you
    # want to write your own functions for them
    return True


@function_for_url([r"^https*://", r"^ftp://"])
def full_url(args):
    parent_host=urlsplit(args['parent_url'])[1]
    db_insert_if_new_url(url=args['url'], visited='0', source="href",parent_host=parent_host,db=args['db'])
    return True


@function_for_url(
    [
        r"^(mailto:|maillto:|maito:|mail:|malito:|mailton:|\"mailto:|emailto:|maltio:|mainto:|E\-mail:|mailtfo:|mailtp:|mailtop:|mailo:|mail to:|Email para:|email :|email:|E-mail: |mail-to:|maitlo:|mail.to:)"
    ]
)
def email_url(args):
    address_search = re.search(
        r"^(mailto:|maillto:|maito:|mail:|malito:|mailton:|\"mailto:|emailto:|maltio:|mainto:|E\-mail:|mailtfo:|mailtp:|mailtop:|mailo:|mail to:|Email para:|email :|email:|E-mail: |mail-to:|maitlo:|mail.to:)(.*)",
        args['url'],
        flags=re.I | re.U,
    )
    if address_search:
        address = address_search.group(2)
        if re.search(
            r"^([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+$",
            address,
        ):
            db_insert_email(url=args['parent_url'], email=address,db=args['db'])
            return True
        else:
            return False
    else:
        return False


def get_links(soup, content_url,db):
    #If you want to grep some patterns, use the code below.
    #pattern=r'"file":{".*?":"(.*?)"}'
    #for script in soup.find_all('script',type="text/javascript"):
    #    if re.search(pattern,str(script)):
    #        print(re.search(pattern,str(script))[1])
    tags = soup("a")
    for tag in tags:
        url = tag.get("href", None)

        if type(url) != str:
            continue
        else:
            url = sanitize_url(url)
        found = False
        host=urlsplit(url)[1]
        #the below block ensures that if link takes to a internal directory of the server, it will use the original host
        if host == '':
            host=urlsplit(content_url)[1]
        if not is_host_block_listed(host) and is_host_allow_listed(host) and not is_url_block_listed(url):
            for regex, function in url_functions:
                m = regex.search(url)
                if m:
                    found = True
                    function({'url':url,'parent_url': content_url,'db':db})
                    continue
            if not found:
                out_url = urljoin(content_url, url)
                print("Unexpected URL -{}- Reference URL -{}-".format(url, content_url))
                print("Unexpected URL. Would this work? -{}-".format(out_url))   
                parent_host=urlsplit(content_url)[1]
                if BE_GREEDY:
                    db_insert_if_new_url(url=out_url,visited=0,source="href",content_type='',words='',parent_host=parent_host,db=db)
    return True

def function_for_content_type(regexp_list):
    def get_content_type_function(f):
        for regexp in regexp_list:
            content_type_functions.append((re.compile(regexp, flags=re.I | re.U), f))
        return f
    return get_content_type_function


def insert_directory_tree(content_url,db):
    parent_host=urlsplit(content_url)[1]
    for url in get_directory_tree(content_url):
        url = sanitize_url(url)
        db_insert_if_new_url(url=url, visited='0',source="dirtree",parent_host=parent_host,db=db)

@function_for_content_type(content_type_html_regex)
def content_type_download(args):
    try:
        soup = BeautifulSoup(args['content'], "html.parser")
    except UnboundLocalError as e:
        print(e)
        return False
    except bs4.builder.ParserRejectedMarkup as e:
        print(e)
        return False
    get_links(soup, args['url'],args['db'])
    if EXTRACT_WORDS:
        words = get_words(soup, args['url'])
    else:
        words = ''
    db_insert_if_new_url(url=args['url'],visited=args['visited'],source=args['source'],content_type=args['content_type'],parent_host=args['parent_host'],db=args['db'])
    db_update_url(url=args['url'],content_type=args['content_type'],visited=args['visited'],words=words,source=args['source'],db=args['db'])
    is_open_directory(str(soup), args['url'])
    return True

@function_for_content_type(content_type_image_regex)
def content_type_images(args):
    try:
        img = Image.open(BytesIO(args['content']))
        width, height = img.size
        nsfw_probability=0
        if img.mode == "CMYK":
            img = img.convert("RGB")
        filename = hashlib.sha512(img.tobytes()).hexdigest() + ".png"
    except UnidentifiedImageError as e:
        #SVG using cairo in the future
        db_update_url(url=args['url'], content_type=args['content_type'], visited='1',source='access',db=args['db'])
        return False
    except Image.DecompressionBombError as e:
        db_update_url(url=args['url'], content_type=args['content_type'], visited='1',source='access',db=args['db'])
        return False
    except OSError:
        db_update_url(url=args['url'], content_type=args['content_type'], visited='1',source='access',db=args['db'])
        return False
    if SAVE_ALL_IMAGES:
        img.save(IMAGES_FOLDER+'/' + filename, "PNG")
    if CATEGORIZE_NSFW:
        image = n2.preprocess_image(img, n2.Preprocessing.YAHOO)
        inputs = np.expand_dims(image, axis=0) 
        predictions = model.predict(inputs)
        sfw_probability, nsfw_probability = predictions[0]
        db_update_url_isnsfw(args['url'], nsfw_probability, db)
        if nsfw_probability>NSFW_MIN_PROBABILITY:
            print('porn {} {}'.format(nsfw_probability,args['url']))
            if SAVE_NSFW:
                img.save(NSFW_FOLDER +'/'+ filename, "PNG")
        else:
            if SAVE_SFW:
                img.save(SFW_FOLDER +'/' +filename, "PNG")
    db_insert_if_new_url(url=args['url'],visited='1',content_type=args['content_type'],source=args['source'],isnsfw=float(nsfw_probability),resolution=width*height,parent_host=args['parent_host'],db=args['db'])
    db_update_url(url=args['url'], content_type=args['content_type'], visited='1',source='access',db=args['db'])
    return True

@function_for_content_type([r"^audio/midi$"])
def content_type_midis(args):
    if not DOWNLOAD_MIDIS:
        db_update_url(url=args['url'], content_type=args['content_type'], visited='1',source='access',db=args['db'])
        return True
    filename=os.path.basename(urlparse(args['url']).path)
    f = open(MIDIS_FOLDER+'/'+filename, "wb")
    f.write(args['content'])
    f.close()
    db_update_url(url=args['url'], content_type=args['content_type'], visited='1',source='access',db=args['db'])
    return True

@function_for_content_type(content_type_pdf)
def content_type_pdfs(args):
    db_update_url(url=args['url'], content_type=args['content_type'], visited='1',source='access',db=args['db'])
    if not DOWNLOAD_PDFS:
        return True
    filename=os.path.basename(urlparse(args['url']).path)
    f = open(PDFS_FOLDER+'/'+filename, "wb")
    f.write(args['content'])
    f.close()
    return True

@function_for_content_type(content_type_all_others_regex)
def content_type_ignore(args):
    # We update as visited.
    if db_count_url(args['url'],args['db']) == 0:
        db_insert_if_new_url(url=args['url'],visited='1',content_type=args['content_type'],source=args['source'],parent_host=args['parent_host'],db=args['db'])
    else:
        db_update_url(url=args['url'],visited='1',content_type=args['content_type'],words=args['words'],source=args['source'],db=args['db'])
    return True

def sanitize_content_type(content_type):
    content_type = content_type.strip()
    content_type = content_type.rstrip()      
    content_type = re.sub(r'^"(.*)"$', r"\1", content_type)
    content_type = re.sub(r'^content-type: (.*)"$', r"\1", content_type)
    content_type = re.sub(r'^content-type:(.*)"$', r"\1", content_type)  
    content_type = re.sub(r'^(.*?);.*$', r"\1",content_type)
    return content_type

def get_page(url,driver,db):
    driver = read_web(url,driver)
    parent_host=urlsplit(url)[1]
    if driver:
        for request in driver.requests:
            if request.response and request.response.headers['Content-Type']:
                url=request.url
                host=urlsplit(url)[1]
                content=decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
                content_type=request.response.headers['Content-Type']
                content_type=sanitize_content_type(content_type)
                if not is_host_block_listed(host) and is_host_allow_listed(host) and not is_url_block_listed(url):
                    if HUNT_OPEN_DIRECTORIES:
                        insert_directory_tree(url,db)
                    found=False
                    for regex, function in content_type_functions:
                        m = regex.search(content_type)
                        if m:
                            found = True
                            function({'url':url,'visited':'1', 'content_type':content_type, 'content':content,'source':'access','words':'','parent_host':parent_host,'db':db})
                            continue
                    if not found:
                        print("UNKNOWN type -{}- -{}-".format(url, content_type))

def break_after(seconds=60):
    def timeout_handler(signum, frame):  # Custom signal handler
        raise TimeoutException
    def function(function):
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                res = function(*args, **kwargs)
                signal.alarm(0)  # Clear alarm
                return res
            except TimeoutException:
                print(
                    "Oops, timeout: {} {} {} {} sec reached.".format(
                        seconds, function.__name__, args, kwargs
                    )
                )
            return
        return wrapper
    return function

## This "break_after" is a decorator, not intended for timeouts,
## but for links that take too long downloading, like streamings
## or large files.
@break_after(MAX_DOWNLOAD_TIME)
def read_web(url,driver):
    try:
        if url.startswith('http://'):
            url=HTTPS_EMBED+url
        driver.get(url)
        return driver
    except Exception as e:
        print(e)
        return False

class TimeoutException(Exception):  # Custom exception class
    pass

def initialize_driver():
    user_agent = UserAgent().random
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={user_agent}')
    prefs = {"download.default_directory": DIRECT_LINK_DOWNLOAD_FOLDER,}
    options.add_experimental_option("prefs", prefs)
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    #options.add_argument('--disable-webgl')
    #options.add_argument('--disable-webrtc')
    #options.add_argument('--disable-geolocation')
    #options.add_argument('--disable-gpu')
    #options.add_argument('--disable-infobars')
    #options.add_argument('--disable-popup-blocking')
    #options.add_argument('--blink-settings=imagesEnabled=false')
    #options.add_argument('--disable-extensions')
    #options.add_argument('--disable-javascript')
    #options.add_argument('--disable-dev-shm-usage')
    #options.add_argument('--proxy-server=http://your-proxy-server:port')
    #options.add_argument('--proxy-server=http://'+PROXY_HOST+':'PROXY_PORT)
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(SELENIUM_WIDTH, SELENIUM_HEIGHT)
    return driver


def crawler(db):
    for iteration in range(ITERATIONS):
        if CATEGORIZE_NSFW:
            model = n2.make_open_nsfw_model()
        driver = initialize_driver()
        random_urls = get_random_unvisited_domains(db=db)
        for target_url in random_urls:
            if (
                not is_host_block_listed(target_url['host']) and
                is_host_allow_listed(target_url['host']) and
                not is_url_block_listed(target_url['url'])
            ):
                try:
                    print(target_url['url'])
                    del driver.requests
                    get_page(target_url['url'], driver,db)
                    if HUNT_OPEN_DIRECTORIES:
                        insert_directory_tree(target_url['url'],db)
                except UnicodeEncodeError:
                    pass
        driver.quit()


def main():
    parser = argparse.ArgumentParser(description="URL scanner and inserter.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["insert", "run"],
        default="run",
        help="Choose 'insert' to insert a URL or 'run' to execute the crawler"
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="The URL to insert (used with 'insert' command)"
    )

    args = parser.parse_args()
    db = DatabaseConnection(DATABASE=DATABASE)

    if args.command == "insert":
        if not args.url:
            print("Error: Please provide a URL to insert.")
        else:
            db_insert_if_new_url(url=args.url, visited=0, source='', content_type="", words="", isnsfw='', resolution='', parent_host='', db=db)
    else:
        crawler(db)

    db.close()

if __name__ == "__main__":
    main()

