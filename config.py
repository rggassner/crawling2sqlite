#!/usr/bin/python3
USE_PROXY=False
PROXY_HOST='http://127.0.0.1:3128'
MAX_DOWNLOAD_TIME = 600
EXTRACT_WORDS=False
HUNT_OPEN_DIRECTORIES=True
DOWNLOAD_MIDIS=False
MIDIS_FOLDER='midis'
DOWNLOAD_PDFS=False
PDFS_FOLDER='pdfs'
INITIAL_URL = "http://www.uol.com.br"
ITERATIONS = 1000
#be_greedy = True - Save urls to database that might not work, since have not matched any regex.
BE_GREEDY=False
# host_regex_block_list do not crawl these domains. Some urls might be inserted, added from allow lists, but they are never crawled.
host_regex_block_list = [
    "instagram\.com$",
]
#do not crawl urls that match any of these regexes
url_regex_block_list = [
    "/noticias/modules/noticias/modules/noticias/modules/",
    "/images/images/images/images/",
    "/image/image/image/image/",
]
host_regex_allow_list = [r".*"]
