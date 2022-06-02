import gzip
import zlib
import signal
import ssl
import urllib.error
import urllib.request
from http.client import IncompleteRead, InvalidURL, BadStatusLine, HTTPException
from io import BytesIO
from socket import timeout
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from django.utils.encoding import force_str

MAX_DOWNLOAD_TIME = 600
user_agent = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0"
)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

content_type_image_regex = [
        r"^img/jpeg$",    
        r"^image/\*$",
        r"^image/gif$",
        r"^image/png$",
        r"^image/bmp$",
        r"^image/svg$",    
        r"^image/jpg$",
        r"^image/any$",
        r"^image/apng$",
        r"^image/avif$",    
        r"^image/jpeg$",
        r"^image/tiff$",
        r"^image/webp$",
        r"^image/pjpeg$",
        r"^image/dicomp$", 
        r"^image/x\-png$",     
        r"^image/\{png\}$", 
        r"^image/x\-icon$",
        r"^image/vnd\.dwg$",    
        r"^image/svg\+xml$",
        r"^image/x\-ms\-bmp$",        
        r"^image/x-photoshop$",         
        r"^image/x\-coreldraw$",        
        r"^image/vnd\.wap\.wbmp$",
        r"^image/vnd\.microsoft\.icon$",
        r"^application/jpg$",        
    ]


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


# This "break_after" is a decorator, not intended for timeouts,
# but for links that take too long downloading, like streamings
# or large files.
@break_after(MAX_DOWNLOAD_TIME)
def read_web(url):
    try:
        req = urllib.request.Request(smart_urlquote(url))
        req.add_header("User-Agent", user_agent)
        response = urllib.request.urlopen(req, context=ctx, timeout=30)
        content = response.read()
        content_type = response.info().get_content_type()
        if response.info().get("Content-Encoding") == "gzip":
            buf = BytesIO(content)
            f = gzip.GzipFile(fileobj=buf)
            outc = f.read()
            return [outc, content_type]
        elif response.info().get("Content-Encoding") == "deflate":
            data = BytesIO(zlib.decompress(content))
            outc = data.read()
            return [outc, content_type]
    except urllib.error.HTTPError as e:
        return False
    except urllib.error.URLError as e:
        return False
    except timeout:
        return False
    except UnicodeError:
        return False
    except ConnectionResetError:
        return False
    except IncompleteRead as e:
        return False
    except InvalidURL as e:
        return False
    except BadStatusLine as e:
        return False
    except ssl.SSLError as e:
        return False
    except gzip.BadGzipFile as e:
        return False
    except zlib.error as e:
        return False
    except HTTPException as e:
        return False
    return [content, content_type]

# encode whitespaces from urls
def smart_urlquote(url):
    # Handle IDN before quoting.
    scheme, netloc, path, query, fragment = urlsplit(url)
    try:
        netloc = netloc.encode("idna").decode("ascii")  # IDN -> ACE
    except UnicodeError:  # invalid domain part
        pass
    else:
        url = urlunsplit((scheme, netloc, path, query, fragment))
    url = unquote(force_str(url))
    # See http://bugs.python.org/issue2637
    url = quote(url, safe=b"!*'();:@&=+$,/?#[]~")
    return force_str(url)


class TimeoutException(Exception):  # Custom exception class
    pass
