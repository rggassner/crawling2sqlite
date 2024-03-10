#!/usr/bin/python3
SELENIUM_WIDTH=1920
SELENIUM_HEIGHT=1080
USE_PROXY=False
PROXY_HOST='http://20.206.106.192:8123'
MAX_DOWNLOAD_TIME = 120
EXTRACT_WORDS=False
HUNT_OPEN_DIRECTORIES=True
DOWNLOAD_MIDIS=False
MIDIS_FOLDER='midis'
DOWNLOAD_PDFS=False
PDFS_FOLDER='pdfs'
INITIAL_URL='https://www.uol.com.br'
ITERATIONS=10
NSFW_MIN_PROBABILITY=.78
CATEGORIZE_NSFW=True
SAVE_NSFW=True
NSFW_FOLDER='images/nsfw'
SAVE_SFW=False
SFW_FOLDER='images/sfw'
MIN_NSFW_RES = 224 * 224
SAVE_ALL_IMAGES=False
IMAGES_FOLDER='images'
DIRECT_LINK_DOWNLOAD_FOLDER='/dev/null'

#be_greedy = True - Save urls to database that might not work, since have not matched any regex.
BE_GREEDY=False

# host_regex_block_list do not crawl these domains. 
host_regex_block_list = [
    '\.instagram\.com$',
]

#do not crawl urls that match any of these regexes
url_regex_block_list = [
    '/noticias/modules/noticias/modules/noticias/modules/',
    '/images/images/images/images/',
    '/image/image/image/image/',
]

host_regex_allow_list = [r'.*']
