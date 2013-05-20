# -*- coding: utf-8 -*-

import re
import socket
from compat import (unicode, bytes, OrderedDict, StringIO,
                    urlparse, urlunparse, urlencode, quote)

"""
TODO:
 - url param support
 - support ';' in addition to '&' for url params
   - http://www.w3.org/TR/REC-html40/appendix/notes.html#h-B.2.2
"""

DEFAULT_ENCODING = 'utf-8'

# URL parsing regex (per RFC 3986)
_URL_RE = re.compile(r'^((?P<scheme>[^:/?#]+):)?'
                     r'(//(?P<authority>[^/?#]*))?'
                     r'(?P<path>[^?#]*)'
                     r'(\?(?P<query>[^#]*))?'
                     r'(#(?P<fragment>.*))?')


# The unreserved URI characters (per RFC 3986)
_UNRESERVED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789-._~")


# IRI escaped character ranges (per RFC3987)
_ESC_RANGES = [(0xA0, 0xD7FF),
               (0xE000, 0xF8FF),
               (0xF900, 0xFDCF),
               (0xFDF0, 0xFFEF),
               (0xE1000, 0xFFFFD),
               (0xF0000, 0xFFFFD),
               (0x100000, 0x10FFFD)]
_ESC_RANGES.extend([(i, i + 0xFFFD) for i in range(0x10000, 0xE0000, 0x10000)])
_ESC_RANGES.sort(key=lambda x: x[0])


def parse_authority(au_str):
    """\
    returns:
      family (socket constant or None), host (string), port (int or None)

    >>> parse_authority('googlewebsite.com:443')
    (None, 'googlewebsite.com', 443)
    >>> parse_authority('[::1]:22')
    (10, '::1', 22)
    >>> parse_authority('192.168.1.1:5000')
    (2, '192.168.1.1', 5000)

    TODO: check validity of non-IP host before returning?
    TODO: exception types for parse exceptions
    """
    family, host, port = None, '', None
    if not au_str:
        return family, host, port
    if ':' in au_str:  # for port-explicit and IPv6 authorities
        host, _, port_str = au_str.rpartition(':')
        if port_str and ']' not in port_str:
            try:
                port = int(port_str)
            except TypeError:
                raise
        else:
            host, port = au_str, None
        if host and '[' == host[0] and ']' == host[-1]:
            host = host[1:-1]
            try:
                socket.inet_pton(socket.AF_INET6, host)
            except socket.error:
                raise
            else:
                family = socket.AF_INET6
                return family, host, port
    try:
        socket.inet_pton(socket.AF_INET, host)
    except socket.error:
        host = host if (host or port) else au_str
    else:
        family = socket.AF_INET
    return family, host, port


def unquote_unreserved(url):
    """\
    Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.
    """
    parts = url.split('%')
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            c = chr(int(h, 16))
            if c in _UNRESERVED_CHARS:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = '%' + parts[i]
        else:
            parts[i] = '%' + parts[i]
    return ''.join(parts)


def requote(url):
    return quote(unquote_unreserved(url), safe="!#$%&'()*+,/:;=?@[]~")


def parse_url(url_str, encoding=DEFAULT_ENCODING):
    from urlparse import ParseResult  # TODO: tmp
    if not isinstance(url_str, unicode):
        try:
            url_str = url_str.decode(encoding)
        except AttributeError:
            raise TypeError('parse_url expected str, unicode, or bytes')
    um = _URL_RE.match(url_str)
    try:
        gs = um.groupdict()
    except AttributeError:
        raise ValueError('could not parse url')
    parsed = ParseResult(gs['scheme'], gs['authority'], gs['path'],
                         '', gs['query'], gs['fragment'])
    parsed = parsed._replace(netloc=parsed.netloc.decode('idna'))
    return parsed


class URL(object):
    _attrs = ('scheme', 'username', 'password', 'hostname',
              'port', 'path', 'params', 'query', 'fragment')

    def __init__(self, url_str, encoding=None):
        encoding = encoding or DEFAULT_ENCODING
        up = parse_url(url_str, encoding=encoding)
        self.encoding = encoding
        _d = unicode()
        for attr in self._attrs:
            setattr(self, attr, getattr(up, attr) or _d)

    @property
    def netloc(self):
        ret = []
        if self.username:
            ret.append(self.username)
            if self.password:
                ret.extend([':', self.password])
            ret.append('@')
        ret.append(self.hostname)
        port = unicode(self.port)
        if port:
            ret.extend([':', self.port])
        return u''.join(ret)

    @property
    def query_string(self):
        return  # if there are args, join them order

    def __iter__(self):
        s, i = self, iter
        return i((s.scheme, s.netloc, s.path, s.params, s.query, s.fragment))

    def encode(self, encoding=None):
        encoding = encoding or DEFAULT_ENCODING
        # TODO: inherit or duck type
        return urlunparse(self).encode('utf-8')  # TODO
