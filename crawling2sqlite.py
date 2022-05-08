#!/usr/bin/python3
import re
import sqlite3
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from functions import read_web

initial_url = "https://www.uol.com.br"

#Every iteration one random url for every unique domain in the database is crawled.
iterations = 100

#The use of in memory sqlite increases performance but is resource intensive
#and makes impossible to run multiple simultaneous processes, since databases
#would be out of sync.
in_memory_sqlite = True

#Database will be dumped to file every nth visited urls
dump_every = 1000

# block_list do not crawl these domains. Some urls might be inserted, added from allow lists, but they are never crawled.
url_regex_block_list = [
    "wikipedia\.org$",
    "wikimedia\.org$",
    "twitter\.com$",
    "facebook\.com$",
    "tumblr\.com$",
    "pinterest\.com$",
    "reddit\.com$",
    "instagram\.com$",
]
url_regex_allow_list = [r"\.br$"]
# url_regex_allow_list = [r".*"]
url_functions = []
img_functions = []
content_type_functions = []
#used to generate wordlist
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

def create_database(initial_url):
    print("Creating database.")
    host = urlsplit(initial_url)[1]
    con = sqlite3.connect("crawler.db")
    cur = con.cursor()
    cur.execute(
        """CREATE TABLE urls (url text, visited boolean, content_type text, source text, words text, host text, UNIQUE (url))"""
    )
    cur.execute("""CREATE TABLE emails (url text, email text, UNIQUE (url,email))""")
    cur.execute(
        "INSERT INTO urls (url,visited,content_type,source,words,host) VALUES (?,0,'','href','',?)",
        (initial_url, host),
    )
    con.commit()
    con.close()


# Verify if url is in a blocklist.
def is_block_listed(url):
    for regex in url_regex_block_list:
        if re.search(regex, url, flags=re.I | re.U):
            return True
    return False


# Verify if url is in a allowlist.
def is_allow_listed(url):
    for regex in url_regex_allow_list:
        if re.search(regex, url, flags=re.I | re.U):
            return True
    return False


def insert_if_new_url(url, visited, source, content_type="", words=""):
    # try:
    host = urlsplit(url)[1]
    # except Exception as err:
    #    return False
    cur = con.cursor()
    cur.execute(
        "insert or ignore into urls (url,visited,content_type,source,words,host) values (?,?,?,?,?,?)",
        (url, visited, content_type, source, words, host),
    )
    con.commit()
    return True


def insert_email(url, email):
    cur = con.cursor()
    cur.execute("insert or ignore into emails (url,email) values (?,?)", (url, email))
    con.commit()
    return True


def update_url(url, visited, content_type, words=""):
    cur = con.cursor()
    cur.execute(
        "update urls set (visited,content_type,words) = (?,?,?) where url = ?",
        (visited, content_type, words, url),
    )
    con.commit()


def get_random_unvisited_domains():
    for i in range(3):
        try:
            cur = con.cursor()
            random_url = cur.execute(
                "SELECT url, host FROM (select url,host from urls where visited =0 order by random() ) as z GROUP BY z.host order by random() "
            ).fetchall()
            break
        except sqlite3.OperationalError:
            create_database(initial_url)
    return random_url


def sanitize_url(url):
    url = url.strip()
    url = url.rstrip()      
    url = re.sub('^“(.*)"', "\1", url)
    url = re.sub(r"^”(.*)”$", r"\1", url)
    url = re.sub(r"^“(.*)“$", r"\1", url)
    url = re.sub(r'^"(.*)"$', r"\1", url)
    url = re.sub(r"^“(.*)”$", r"\1", url)
    url = re.sub(r"^‘(.*)’$", r"\1", url)
    url = re.sub(r'^"(.*)\'$', r"\1", url)
    url = re.sub(r"^\'(.*)\'$", r"\1", url)
    url = re.sub(r'^”(.*)″$', r"\1", url)        
    url = re.sub(r"^(.+)#.*$", r"\1", url)
    url = re.sub("^www\.", "http://www.", url)
    if re.search(r"^http:[^/][^/]", url):
        url = re.sub("^http:", "http://", url)
    if re.search(r"^http:/[^/]", url):
        url = re.sub("^http:/", "http://", url)
    if re.search(r"^https:[^/][^/]", url):
        url = re.sub("^https:", "https://", url)
    if re.search(r"^https:/[^/]", url):
        url = re.sub("^https:/", "https://", url)
        
    in_url=url
    
    url = re.sub("^[a-zA-Z\.“\(´]https://", "https://", url)  
    url = re.sub("^[a-zA-Z\.“\(´]http://", "http://", url)  
    url = re.sub("^https[a-zA-Z\.“\(´]://", "https://", url)  
    url = re.sub("^http[\.“\(´]://", "http://", url)  
    url = re.sub("^https: / /", "https://", url)  
    url = re.sub("^://", "https://", url)      
    url = re.sub("^htt://", "http://", url)    
    url = re.sub("^Mh ttp://", "http://", url) 
    url = re.sub("^htpps://", "https://", url) 
    url = re.sub("^http:s//", "https://", url)
    url = re.sub("^hthttps://", "https://", url)
    url = re.sub("^httsp://", "https://", url)
    url = re.sub("^htts://", "https://", url)    
    url = re.sub("^htp://http//", "http://", url)
    url = re.sub("^htttps://", "https://", url)
    url = re.sub("^https:https://", "https://", url)
    url = re.sub("^ttps://", "https://", url)
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
    url = re.sub("^%22mailto:", "mailto:", url)
    url = re.sub("^httpqs://", "https://www.", url)
    if in_url != url:
        print("URL SANITIZED:")
        print("IN###-{}-".format(in_url))
        print("OUT##-{}-".format(url))
    return url

def get_words(soup, content_url):
    output = ""
    text = soup.find_all(text=True)
    for t in text:
        if t.parent.name not in soup_tag_blocklist:
            output += "{} ".format(t)
    return " ".join(list(set(output.split())))


###############################################################################
def function_for_url(regexp_list):
    def get_url_function(f):
        for regexp in regexp_list:
            url_functions.append((re.compile(regexp, flags=re.I | re.U), f))
        return f

    return get_url_function


# url unsafe {}|\^~[]`
# regex no need to escape '!', '"', '%', "'", ',', '/', ':', ';', '<', '=', '>', '@', and "`"
@function_for_url(
    [
        r"^(\/|\.\.\/|\.\/)",
        r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´ç�]+$",
        r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´ç]*[\?\/][0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬:\"¶ç´]+$",
    ]
)
def relative_url(args):
    out_url = urljoin(args[1], args[0])
    insert_if_new_url(out_url, 0, "href")
    return True


@function_for_url(
    [
        r"(\{|\[|\||\}|\]|\~|\^|\\)",
    ]
)
def unsafe_character_url(args):
    return True


@function_for_url(
    [
        r"^#",
        r"^$",
        r"^\$",
        r"^tg:",
        r"^fb:",        
        r"^app:",
        r"^apt:",
        r"^geo:",
        r"^sms:",
        r"^ssh:",
        r"^fax:",
        r"^fon:",
        r"^git:",
        r"^svn:",
        r"^wss:",
        r"^mms:",
        r"^aim:",
        r"^rtsp:",        
        r"^file:",
        r"^feed:",
        r"^itpc:",
        r"^news:",
        r"^atom:",
        r"^nntp:",
        r"^sftp:",
        r"^data:",
        r"^apps:",
        r"^xmpp:",
        r"^void:",
        r"^waze:",        
        r"^viber:",
        r"^steam:",
        r"^ircs*:",
        r"^skype:",
        r"^ymsgr:",
        r"^about:",
        r"^movie:",
        r"^rsync:",
        r"^popup:",        
        r"^itmss:",
        r"^chrome:",
        r"^telnet:",
        r"^webcal:",
        r"^magnet:",
        r"^vscode:",
        r"^mumble:",
        r"^unsafe:",        
        r"^podcast:",
        r"^spotify:",
        r"^bitcoin:",
        r"^threema:",
        r"^\.onion$",
        r"^\(none\)$",
        r"^ethereum:",
        r"^litecoin:",
        r"^whatsapp:",
        r"^appstream:",
        r"^worldwind:",
        r"^x\-webdoc:",
        r"^applenewss:",
        r"^itms\-apps:",
        r"^itms\-beta:",
        r"^santanderpf:",        
        r"^bitcoincash:",
        r"^android\-app:",
        r"^ms\-settings:",
        r"^applewebdata:",
        r"^fb\-messenger:",
        r"^moz\-extension:",
        r"^microsoft\-edge:",
        r"^x\-help\-action:",
        r"^digitalassistant:",
        r"^chrome\-extension:",
        r"^ms\-windows\-store:",
        r"^(tel:|tellto:|te:|callto:|TT:|tell:|telto:|phone:|calto:|call:|telnr:|tek:|sip:|to:|SAC:)",
        r"^(javascript:|javacscript:|javacript:|javascripy:|javscript:|javascript\.|javascirpt:|javascript;|javascriot:|javascritp:|havascript:|javescript:|javascrip:|javascrpit:|js:|javascripr:|javastript:|javascipt:|javsacript:|javasript:|javascrit:|javascriptt:|ja vascript:|javascrtipt:|jasvascript:)",
    ]
)
def do_nothing_url(args):
    # Do nothing with these regex. They are kept here only as a guideline if you
    # want to write your own functions for them
    return True


@function_for_url([r"^https*://", r"^ftp://"])
def full_url(args):
    insert_if_new_url(args[0], 0, "href")
    return True


@function_for_url(
    [
        r"^(mailto:|maillto:|maito:|mail:|malito:|mailton:|\"mailto:|emailto:|maltio:|mainto:|E\-mail:|mailtfo:|mailtp:|mailtop:|mailo:|mail to:|Email para:|email :|email:)"
    ]
)
def email_url(args):
    address_search = re.search(
        r"^(mailto:|maillto:|maito:|mail:|malito:|mailton:|\"mailto:|emailto:|maltio:|mainto:|E\-mail:|mailtfo:|mailtp:|mailtop:|mailo:|mail to:|Email para:|email :|email:)(.*)",
        args[0],
        flags=re.I | re.U,
    )
    if address_search:
        address = address_search.group(2)
        if re.search(
            r"^([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+$",
            address,
        ):
            insert_email(args[1], address)
            return True
        else:
            return False
    else:
        return False


def get_links(soup, content_url):
    tags = soup("a")
    for tag in tags:
        url = tag.get("href", None)
        if type(url) != str:
            continue
        else:
            url = sanitize_url(url)
        found = False
        for regex, function in url_functions:
            m = regex.search(url)
            if m:
                found = True
                function([url, content_url])
                continue
        if not found:
            print("Unexpected URL -{}- Reference URL -{}-".format(url, content_url))
    return True

###############################################################################
# iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii
def function_for_img(regexp_list):
    def get_img_function(f):
        for regexp in regexp_list:
            img_functions.append((re.compile(regexp, flags=re.I | re.U), f))
        return f

    return get_img_function


@function_for_img(
    [
     r"^(\/|\.\.\/|\.\/)",
     r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬íÇ]+$",
     r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´]*[\?\/][0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬:\"¶´]+$",        
    ]
)
def relative_img(args):
    out_url = urljoin(args[1], args[0])
    insert_if_new_url(out_url, 0, "img")
    return True


@function_for_img(
    [
        r"(\{|\[|\||\}|\]|\~|\^|\\)",
    ]
)
def unsafe_character_img(args):
    return True


@function_for_img(
    [
        r"^#",
        r"^$",
        r"^data:",
    ]
)
def do_nothing_img(args):
    # Do nothing with these regex. They are kept here only as a guideline if you
    # want to write your own functions for them
    return True


@function_for_img([r"^https*://", r"^ftp://"])
def full_img(args):
    insert_if_new_url(args[0], 0, "img")
    return True


def get_images(soup, content_url):
    tags = soup("img")
    for tag in tags:
        url = tag.get("src", None)
        if type(url) != str:
            continue
        else:
            url = sanitize_url(url)
        found = False
        for regex, function in img_functions:
            m = regex.search(url)
            if m:
                found = True
                function([url, content_url])
                continue
        if not found:
            print("Unexpected Image -{}- Reference URL -{}-".format(url, content_url))
    return True


# iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii
# -----------------------------------------------------------------------------------------------------------------------
def function_for_content_type(regexp_list):
    def get_content_type_function(f):
        for regexp in regexp_list:
            content_type_functions.append((re.compile(regexp, flags=re.I | re.U), f))
        return f

    return get_content_type_function


@function_for_content_type([r"^text/html$"])
def content_type_download(args):
    soup = BeautifulSoup(args[3], "html.parser")
    get_links(soup, args[0])
    get_images(soup, args[0])
    words = get_words(soup, args[0])
    update_url(args[0], args[1], args[2], words=words)
    return True


@function_for_content_type(
    [
        r"^image/\*$",
        r"^image/gif$",
        r"^image/png$",
        r"^image/bmp$",
        r"^image/jpg$",
        r"^image/any$",
        r"^image/apng$",
        r"^image/jpeg$",
        r"^image/tiff$",
        r"^image/webp$",
        r"^image/pjpeg$",
        r"^image/x\-icon$",
        r"^image/svg\+xml$",
        r"^image/x\-ms\-bmp$",        
        r"^image/vnd\.wap\.wbmp$",
        r"^image/vnd\.microsoft\.icon$",
        r"^application/jpg$",        
    ]
)
def content_type_images(args):
    # Since we have an external downloader, update as not visited
    update_url(args[0], 0, args[2])
    return True


@function_for_content_type(
    [
        r"^\*/\*$",
        r"^audio/ogg$",
        r"^audio/mp3$",                
        r"^audio/mp4$",        
        r"^audio/mpeg$",
        r"^audio/opus$",
        r"^application/pdf$",
        r"^application/xml$",
        r"^application/rar$",
        r"^application/zip$",
        r"^application/avi$",
        r"^application/doc$",
        r"^application/xls$",        
        r"^application/rtf$",
        r"^application/ogg$",
        r"^application/csv$",
        r"^application/docx$",        
        r"^application/text$",        
        r"^application/json$",
        r"^application/mobi$",
        r"^application/gzip$",
        r"^application/save$",
        r"^application/null$",        
        r"^application/\.zip$",
        r"^application/\.rar$",
        r"^application/\.pdf$",
        r"^application/x\-xz$",
        r"^application/x\-sh$",
        r"^application/x\-twb$",
        r"^application/x\-tar$",
        r"^application/x\-rar$",
        r"^application/x\-msi$",
        r"^application/msword$",
        r"^application/x\-zip$",
        r"^application/msword$",
        r"^application/unknown$",
        r"^application/x\-gzip$",
        r"^application/msexcel$",
        r"^application/ld\+json$",
        r"^application/rdf\+xml$",
        r"^application/download$",
        r"^application/xml\-dtd$",
        r"^application/rss\+xml$", 
        r"^application/hal\+json$",        
        r"^application/ttml\+xml$",
        r"^application/x\-msword$",
        r"^application/pgp\-keys$",
        r"^application/epub\+zip$",
        r"^application/atom\+xml$",
        r"^application/x\-bibtex$",
        r"^application/pkix\-crl$",        
        r"^application/x\-dosexec$",               
        r"^application/javascript$",
        r"^application/x\-mpegurl$",
        r"^application/postscript$",
        r"^application/xhtml\+xml$",
        r"^application/x\-msexcel$",
        r"^application/x\-tar\-gz$",
        r"^application/pkix\-cert$",
        r"^application/x\-rss\+xml$",
        r"^application/x\-xpinstall$",
        r"^application/java\-archive$",        
        r"^application/x\-javascript$",
        r"^application/x\-msdownload$",
        r"^application/x\-httpd\-php$",
        r"^application/octet\-stream$",
        r"^application/vnd\.ms\-word$",
        r"^application/x\-executable$",                
        r"^application/pgp\-signature$",
        r"^application/vnd\.ms\-excel$",
        r"^application/force\-download$",
        r"^application/x\-msdos\-program$",
        r"^application/x\-iso9660\-image$",
        r"^application/vnd\.ogc\.wms_xml$",
        r"^application/x\-x509\-ca\-cert$",                
        r"^application/x\-ms\-application$",                
        r"^application/x\-zip\-compressed$",
        r"^application/x\-rar\-compressed$",
        r"^application/x\-debian\-package$", 
        r"^application/pdfcontent\-length:",                
        r"^application/vnd\.apple\.mpegurl$",
        r"^application/vnd\.ms\-powerpoint$",
        r"^application/x\-gtar\-compressed$",
        r"^application/x\-shockwave\-flash$",
        r"^application/x\-apple\-diskimage$",
        r"^application/x\-java\-jnlp\-file$", 
        r"^application/x\-mobipocket\-ebook$",
        r"^application/vnd\.ms\-officetheme$",        
        r"^application/x\-pkcs7\-certificates$",
        r"^application/x\-research\-info\-systems$",
        r"^application/vnd\.android\.package\-archive$",
        r"^application/vnd\.oasis\.opendocument\.text$",
        r"^application/vnd\.oasis\.opendocument\.spreadsheet$",
        r"^application/vnd\.spring\-boot\.actuator\.v3\+json$",                
        r"^application/vnd\.oasis\.opendocument\.presentation$",
        r"^application/vnd\.openxmlformats\-officedocument\.spreadsheetml\.sheet$",
        r"^application/vnd\.openxmlformats\-officedocument\.wordprocessingml\.document$",
        r"^application/vnd\.openxmlformats\-officedocument\.presentationml\.presentation$",
        r"^audio/x\-rpm$",
        r"^audio/x\-wav$",
        r"^audio/x\-ms\-wma$",
        r"^binary/octet\-stream$",
        r"^model/usd$",
        r"^multipart/x\-zip$",        
        r"^multipart/form\-data$",
        r"^multipart/x\-mixed\-replace$",
        r"^text/xml$",
        r"^text/css$",
        r"^text/csv$",
        r"^text/rtf$",
        r"^text/x\-sh$",
        r"^text/vcard$",
        r"^text/plain$",
        r"^text/turtle$",
        r"^text/x\-tex$",
        r"^text/x\-chdr$",
        r"^text/calendar$",
        r"^text/directory$",
        r"^text/x\-bibtex$",
        r"^text/javascript$",
        r"^text/x\-comma\-separated\-values$",
        r"^text/html, charset=iso\-8859\-1$",        
        r"^video/mp4$",
        r"^video/ogg$",
        r"^video/webm$",
        r"^video/x\-flv$",        
        r"^video/quicktime$",        
        r"^video/x\-ms\-wmv$",
        r"^video/x\-ms\-asf$",
        r"^video/x\-msvideo$",
        r"^x\-application/octet\-stream$",
    ]
)
def content_type_ignore(args):
    # We update as visited.
    update_url(args[0], args[1], args[2])
    return True


def get_page(url):
    response = read_web(url)
    if response:
        content = response[0]
        content_type = response[1]
        found = False
        for regex, function in content_type_functions:
            m = regex.search(content_type)
            if m:
                found = True
                function([url, 1, content_type, content])
                continue
        if not found:
            print("UNKNOWN type -{}- -{}-".format(url, content_type))
    else:
        # Page request didn't work
        update_url(url, 2, "", "")


# ----------------------------------------------------------------------


def get_url_count():
    cur = con.cursor()
    url_count = cur.execute("select count(url) from urls").fetchone()[0]
    con.commit()
    return url_count


def get_unique_domain_count():
    cur = con.cursor()
    unique_domain_count = cur.execute(
        "select count(distinct host) from urls"
    ).fetchone()[0]
    con.commit()
    return unique_domain_count


def get_image_count():
    cur = con.cursor()
    image_count = cur.execute(
        'select count(host) from urls where source="img"'
    ).fetchone()[0]
    con.commit()
    return image_count


def get_visit_count():
    cur = con.cursor()
    visit_count = cur.execute(
        "select count(url) from urls where visited =1"
    ).fetchone()[0]
    con.commit()
    return visit_count


def get_email_count():
    cur = con.cursor()
    email_count = cur.execute("select count(distinct email) from emails").fetchone()[0]
    con.commit()
    return email_count


def get_content_type_count():
    cur = con.cursor()
    content_type_count = cur.execute(
        "select content_type,count(content_type) as total from urls group by content_type order by total desc limit 10"
    ).fetchall()
    con.commit()
    return content_type_count


def get_domain_count():
    cur = con.cursor()
    domain_count = cur.execute(
        "select host,count(host) as total from urls group by host order by total desc limit 10"
    ).fetchall()
    con.commit()
    return domain_count


def stats():
    url_count = get_url_count()
    unique_domain_count = get_unique_domain_count()
    image_count = get_image_count()
    visit_count = get_visit_count()
    email_count = get_email_count()
    print("Top 10 content_type:")
    for row in get_content_type_count():
        print("{}".format(row))
    print("Top 10 domains:")
    for row in get_domain_count():
        print("{}".format(row))
    print(
        "url_count={} unique_domain_count={} image_count={} visit_count={} email_count={}".format(
            url_count, unique_domain_count, image_count, visit_count, email_count
        )
    )

if in_memory_sqlite:    
    source_con = sqlite3.connect("crawler.db", timeout=60)
    con = sqlite3.connect(':memory:',timeout=60)
    source_con.backup(con)
else:
    con = sqlite3.connect("crawler.db", timeout=60)

processed_count=0
for iteration in range(iterations):
    random_urls = get_random_unvisited_domains()
    for target_url in random_urls:
        if not is_block_listed(target_url[1]) and is_allow_listed(target_url[1]):
            try:
                get_page(target_url[0])
                if processed_count >= dump_every:
                    con.backup(source_con)
                    processed_count=0
                else:
                    processed_count=processed_count+1
            except UnicodeEncodeError:
                pass
    if in_memory_sqlite:
        con.backup(source_con)
    print("End of iteration {}".format(iteration))
    stats()

if in_memory_sqlite:
    source_con.close()
con.close()
