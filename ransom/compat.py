# -*- coding: utf-8 -*-
import sys

is_py2 = sys.version_info[0] == 2
is_py3 = sys.version_info[0] == 3

from collections import OrderedDict  # TODO

if is_py2:
    from urllib import quote, unquote, quote_plus, unquote_plus, urlencode
    from urlparse import urlparse, urlunparse, urljoin, urlsplit, urldefrag
    from urllib2 import parse_http_list
    import cookielib
    from Cookie import Morsel
    from StringIO import StringIO

    unicode, str, bytes, basestring = unicode, str, str, basestring
elif is_py3:
    from urllib.parse import (urlparse, urlunparse, urljoin, urlsplit,
                              urlencode, quote, unquote, quote_plus,
                              unquote_plus, urldefrag)
    from urllib.request import parse_http_list
    from http import cookiejar as cookielib
    from http.cookies import Morsel
    from io import StringIO

    unicode, str, bytes, basestring = str, bytes, bytes, str
else:
    raise NotImplementedError('welcome to the future, I guess. (report this)')