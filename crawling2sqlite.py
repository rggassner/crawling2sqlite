#!/usr/bin/python3
import re
import sqlite3
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from functions import read_web, content_type_image_regex

initial_url = "https://www.uol.com.br"

#Every iteration one random url for every unique domain in the database is crawled.
iterations = 100

#be_greedy = True - Save urls to database that might not work, since have not matched any regex.
be_greedy=False

# host_regex_block_list do not crawl these domains. Some urls might be inserted, added from allow lists, but they are never crawled.
host_regex_block_list = [
    "wikipedia\.org$",
    "wikimedia\.org$",
    "twitter\.com$",
    "facebook\.com$",
    "tumblr\.com$",
    "pinterest\.com$",
    "reddit\.com$",
    "instagram\.com$",
]

#do not crawl urls that match any of these regexes
url_regex_block_list = [
    "/noticias/modules/noticias/modules/noticias/modules/",
    "/images/images/images/images/",    
    "/image/image/image/image/",        
]


host_regex_allow_list = [r"\.br$"]
# host_regex_allow_list = [r".*"]
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
    try:
        host = urlsplit(initial_url)[1]
    except ValueError as e:
        return false
    con = sqlite3.connect("crawler.db")
    cur = con.cursor()
    cur.execute(
        """CREATE TABLE urls (url text, visited boolean, content_type text, source text, words text, host text, resolution integer, UNIQUE (url))"""
    )
    cur.execute("""CREATE TABLE emails (url text, email text, UNIQUE (url,email))""")
    cur.execute(
        "INSERT INTO urls (url,visited,content_type,source,words,host) VALUES (?,0,'','href','',?)",
        (initial_url, host),
    )
    con.commit()
    con.close()


# Verify if host is in a blocklist.
def is_host_block_listed(url):
    for regex in host_regex_block_list:
        if re.search(regex, url, flags=re.I | re.U):
            return True
    return False

# Verify if url is in a blocklist.
def is_url_block_listed(url):
    for regex in url_regex_block_list:
        if re.search(regex, url, flags=re.I | re.U):
            print('####### URL is block listed {}'.format(url))
            return True
    return False

# Verify if url is in a allowlist.
def is_host_allow_listed(url):
    for regex in host_regex_allow_list:
        if re.search(regex, url, flags=re.I | re.U):
            return True
    return False

def remove_jsessionid_with_semicolon(url):
    pattern = r';jsessionid=[^&?]*'
    cleaned_url = re.sub(pattern, '', url)
    return cleaned_url

def insert_if_new_url(url, visited, source, content_type="", words=""):
    try:
        host = urlsplit(url)[1]
    except ValueError as e:
        return False
    url=remove_jsessionid_with_semicolon(url)
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


def update_url(url, content_type,visited="", words="",source='href'):
    cur = con.cursor()
    if visited != "":
        cur.execute(
            "update urls set (visited,content_type,words,source) = (?,?,?,?) where url = ?",
            (visited, content_type, words, source, url),
        )
    else:
        cur.execute(
            "update urls set (content_type,words,source) = (?,?,?) where url = ?",
            (content_type, words, source, url),
        )    
    con.commit()

#Fast and uses low memory, but hosts
#with inumerous urls will have higher chances to be
#selected, biasing the result.
#def get_random_unvisited_domains():
#    for i in range(3):
#        try:
#            cur = con.cursor()
#            random_url = cur.execute(
#                "SELECT url,host FROM urls WHERE rowid > ( ABS(RANDOM()) % (SELECT max(rowid) FROM urls)) and visited=0 LIMIT 1"
#            ).fetchall()
#            break
#        except sqlite3.OperationalError:
#            create_database(initial_url)
#    return random_url

#Uses more resources, but will spread the connections 
#evenly through the hosts. Expect the number of hosts to increase rapidly
def get_random_unvisited_domains():
    for i in range(3):
        try:
            cur = con.cursor()
            random_url = cur.execute(
                "select url,host from (SELECT url,host FROM urls where visited=0 order by RANDOM()) group by host order by RANDOM()"
            ).fetchall()
            break
        except sqlite3.OperationalError:
            create_database(initial_url)
    return random_url

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
    url = re.sub("^www\.", "http://www.", url)
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
    url = re.sub("^[a-zA-Z\.“\(´]https://", "https://", url)  
    url = re.sub("^[a-zA-Z\.“\(´]http://", "http://", url)  
    url = re.sub("^https[a-zA-Z\.“\(´]://", "https://", url)  
    url = re.sub("^http[\.“\(´]://", "http://", url) 
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
        r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´ç�í¦ã]+$",
        r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´ç]*[\?\/][0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬:\"¶ç´™*]+$",
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
        r"^itms:",         
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
        r"^(tel:|tellto:|te:|callto:|TT:|tell:|telto:|phone:|calto:|call:|telnr:|tek:|sip:|to:|SAC:|facetime-audio:|telefone:|telegram:|tel\+:|tal:|tele:|tels:|cal:|tel\.:)",
        r"^(javascript:|javacscript:|javacript:|javascripy:|javscript:|javascript\.|javascirpt:|javascript;|javascriot:|javascritp:|havascript:|javescript:|javascrip:|javascrpit:|js:|javascripr:|javastript:|javascipt:|javsacript:|javasript:|javascrit:|javascriptt:|ja vascript:|javascrtipt:|jasvascript:|javascropt:|jvascript:|javasctipt:|avascript:|javacsript:)",
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
        r"^(mailto:|maillto:|maito:|mail:|malito:|mailton:|\"mailto:|emailto:|maltio:|mainto:|E\-mail:|mailtfo:|mailtp:|mailtop:|mailo:|mail to:|Email para:|email :|email:|E-mail: |mail-to:|maitlo:|mail.to:)"
    ]
)
def email_url(args):
    address_search = re.search(
        r"^(mailto:|maillto:|maito:|mail:|malito:|mailton:|\"mailto:|emailto:|maltio:|mainto:|E\-mail:|mailtfo:|mailtp:|mailtop:|mailo:|mail to:|Email para:|email :|email:|E-mail: |mail-to:|maitlo:|mail.to:)(.*)",
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
        for regex, function in url_functions:
            m = regex.search(url)
            if m:
                found = True
                function([url, content_url])
                continue
        if not found:
            out_url = urljoin(content_url, url)
            print("Unexpected URL -{}- Reference URL -{}-".format(url, content_url))
            print("Unexpected URL. Would this work? -{}-".format(out_url))   
            if be_greedy:
                insert_if_new_url(out_url, 0, "href")                        
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
     r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬íÇâã€®]+$",
     r"^[0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬´à]*[\?\/][0-9\-\./\?=_\&\s%@<>\(\);\+!,\w\$\'–’—”“ä°§£Ã¬:\"¶´]+$",        
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
        r"^about:",
        r"^file:",
        r"^blob:",
        r"^chrome\-extension:",                
    ]
)
def do_nothing_img(args):
    # Do nothing with these matches. They are kept here only as a guideline if you
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
            out_url = urljoin(content_url,url)
            print("Unexpected Image -{}- Reference URL -{}-".format(url, content_url))
            print("Unexpected Image. Would this work? -{}-".format(out_url))
            if be_greedy:
                insert_if_new_url(out_url, 0, "img")
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
    try:
        soup = BeautifulSoup(args[3], "html.parser")
    except UnboundLocalError as e:
        return False
    get_links(soup, args[0])
    get_images(soup, args[0])
    words = get_words(soup, args[0])
    update_url(args[0], args[2],visited=args[1], words=words)
    return True


@function_for_content_type(content_type_image_regex)
def content_type_images(args):
    # Since we have an external downloader, update as not visited, and mark as a img source
    ##do not pass visited
    update_url(args[0], args[2], source='img')
    return True

@function_for_content_type([r"^audio/midi$"])
def content_type_midis(args):
    #download midi
    args[3]
    filename=os.path.basename(urlparse(args[0]).path)
    f = open('midis/'+filename, "wb")
    f.write(args[3])
    f.close()
    update_url(args[0], args[2], visited=args[1])
    return True

@function_for_content_type(
    [
        r"^\*/\*$",
        r"^adobe/pdf$",        
        r"^application/\*$",        
        r"^application/pdf$",
        r"^application/xml$",
        r"^application/rar$",
        r"^application/zip$",
        r"^application/avi$",
        r"^application/doc$",
        r"^application/xls$",        
        r"^application/rtf$",
        r"^application/ogg$",
        r"^application/mp3$",        
        r"^application/csv$",
        r"^application/wmv$",    
        r"^application/epub$",                        
        r"^application/xlsx$",                
        r"^application/docx$",        
        r"^application/text$",        
        r"^application/json$",
        r"^application/mobi$",
        r"^application/gzip$",
        r"^application/save$",
        r"^application/null$",
        r"^application/zlib$",        
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
        r"^application/x\-xar$",                
        r"^application/unknown$",
        r"^application/x\-gzip$",
        r"^application/msexcel$",
        r"^application/ld\+json$",
        r"^application/rdf\+xml$",
        r"^application/download$",
        r"^application/xml\-dtd$",
        r"^application/rss\+xml$", 
        r"^application/ms\-excel$",        
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
        r"^application/pkcs7\-mime$",                         
        r"^application/x\-xpinstall$",
        r"^application/x\-troff\-man$",                
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
        r"^application/privatetempstorage$",        
        r"^application/x\-httpd\-ea\-php54$",                
        r"^application/x\-httpd\-ea\-php71$",        
        r"^application/vnd\.apple\.mpegurl$",
        r"^application/vnd\.ms\-powerpoint$",
        r"^application/x\-gtar\-compressed$",
        r"^application/x\-shockwave\-flash$",
        r"^application/x\-apple\-diskimage$",
        r"^application/x\-java\-jnlp\-file$", 
        r"^application/x\-mobipocket\-ebook$",
        r"^application/vnd\.ms\-officetheme$",        
        r"^application/x\-ms\-dos\-executable$",                
        r"^application/x\-pkcs7\-certificates$",
        r"^application/x\-research\-info\-systems$",
        r"^application/vnd\.ms\-word\.document\.12$",                
        r"^application/vnd\.google\-earth\.kml\+xml$",        
        r"^application/vnd\.ms\-excel\.openxmlformat$",                 
        r"^application/vnd\.android\.package\-archive$",
        r"^application/vnd\.oasis\.opendocument\.text$",        
        r"^application/x\-zip\-compressedcontent\-length:",  
        r"^application/vnd\.oasis\.opendocument\.spreadsheet$",
        r"^application/vnd\.spring\-boot\.actuator\.v3\+json$",                
        r"^application/vnd\.oasis\.opendocument\.presentation$",
        r"^application/vnd\.ms\-excel\.sheet\.macroenabled\.12$",  
        r"^application/vnd\.openxmlformats\-officedocument\.spre$",                
        r"^application/vnd\.adobe\.air\-application\-installer\-package\+zip$",                
        r"^application/vnd\.openxmlformats\-officedocument\.spreadsheetml\.sheet$",
        r"^application/vnd\.openxmlformats\-officedocument\.presentationml\.slideshow",                  
        r"^application/vnd\.openxmlformats\-officedocument\.wordprocessingml\.document$",
        r"^application/vnd\.openxmlformats\-officedocument\.wordprocessingml\.template$",                
        r"^application/vnd\.openxmlformats\-officedocument\.presentationml\.presentation$",
        r"^audio/ogg$",
        r"^audio/mp3$",                
        r"^audio/mp4$",        
        r"^audio/wav$",        
        r"^audio/mpeg$",
        r"^audio/opus$", 
        r"^audio/x\-rpm$",
        r"^audio/x\-wav$",
        r"^audio/unknown$", 
        r"^audio/x\-scpls$",                 
        r"^audio/x\-ms\-wma$",
        r"^audio/x\-mpegurl$",         
        r"^audio/x\-pn\-realaudio$",         
        r"^binary/octet\-stream$",
        r"^model/usd$",
        r"^multipart/x\-zip$",        
        r"^multipart/form\-data$",
        r"^multipart/x\-mixed\-replace$",
        r"^octet/stream$",        
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
        r"^text/x\-vcard$",                
        r"^text/calendar$",
        r"^text/directory$",
        r"^text/x\-bibtex$",
        r"^text/javascript$",
        r"^text/x\-vcalendar$",        
        r"^text/x\-comma\-separated\-values$",
        r"^text/html, charset=iso\-8859\-1$",        
        r"^video/mp4$",
        r"^video/ogg$",
        r"^video/f4v$", 
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
    update_url(args[0], args[2], visited=args[1])
    return True

def sanitize_content_type(content_type):
    content_type = content_type.strip()
    content_type = content_type.rstrip()      
    content_type = re.sub(r'^"(.*)"$', r"\1", content_type)
    content_type = re.sub(r'^content-type: (.*)"$', r"\1", content_type)
    content_type = re.sub(r'^content-type:(.*)"$', r"\1", content_type)  
    return content_type

def get_page(url):
    response = read_web(url)
    if response:
        content = response[0]
        content_type = response[1]
        content_type=sanitize_content_type(content_type)
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
        update_url(url, "", visited=2)


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

con = sqlite3.connect("crawler.db", timeout=60)

for iteration in range(iterations):
    random_urls = get_random_unvisited_domains()
    for target_url in random_urls:
        if not is_host_block_listed(target_url[1]) and is_host_allow_listed(target_url[1]) and not is_url_block_listed(target_url[0]):
            try:
                get_page(target_url[0])
            except UnicodeEncodeError:
                pass
    #print("End of iteration {}".format(iteration))
    #stats()
con.close()
