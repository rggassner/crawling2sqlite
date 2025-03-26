#!venv/bin/python3
SELENIUM_WIDTH=1920
SELENIUM_HEIGHT=1080
EMBED_PORT='4443'
USE_PROXY=False
PROXY_HOST='http://10.206.106.192:8123'
MAX_DOWNLOAD_TIME = 120
EXTRACT_WORDS=False
HUNT_OPEN_DIRECTORIES=True
DOWNLOAD_MIDIS=False
MIDIS_FOLDER='midis'
DOWNLOAD_PDFS=False
PDFS_FOLDER='pdfs'
INITIAL_URL='https://www.kernel.org'
ITERATIONS=1
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
HTTPS_EMBED='https://localhost:'+EMBED_PORT+'/embed.html?url='
GROUP_DOMAIN_LEVEL=4

#be_greedy = True - Save urls to database that might not work, since have not matched any regex.
BE_GREEDY=False

# host_regex_block_list do not crawl these domains. 
host_regex_block_list = [
    'localhost:4443$',
    '.instagram.com$',
]

#do not crawl urls that match any of these regexes
url_regex_block_list = [
    '/noticias/modules/noticias/modules/noticias/modules/',
    '/images/images/images/images/',
]

host_regex_allow_list = [r'.*']


