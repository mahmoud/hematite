# -*- coding: utf-8 -*-

import re
import socket

from compat import (unicode, bytes, urlparse, urlunparse,
                    quote, parse_qsl, OrderedMultiDict, BytestringHelper)

"""
TODO:
 - support ';' in addition to '&' for url params
   - http://www.w3.org/TR/REC-html40/appendix/notes.html#h-B.2.2
 - support python compiled without IPv6
 - IRI encoding
 - support empty port (e.g., http://gweb.com:/)
"""

DEFAULT_ENCODING = 'utf-8'

# The unreserved URI characters (per RFC 3986)
_UNRESERVED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789-._~")
_RESERVED_CHARS = frozenset(":/?#[]@!$&'()*+,;=")
_ALLOWED_CHARS = _UNRESERVED_CHARS | _RESERVED_CHARS

# URL parsing regex (per RFC 3986)
_URL_RE = re.compile(r'^((?P<scheme>[^:/?#]+):)?'
                     r'(//(?P<authority>[^/?#]*))?'
                     r'(?P<path>[^?#]*)'
                     r'(\?(?P<query>[^#]*))?'
                     r'(#(?P<fragment>.*))?')

_SCHEME_CHARS = re.escape(''.join(_ALLOWED_CHARS - set(':/?#')))
_AUTH_CHARS = re.escape(''.join(_ALLOWED_CHARS - set(':/?#')))
_PATH_CHARS = re.escape(''.join(_ALLOWED_CHARS - set('?#')))
_QUERY_CHARS = re.escape(''.join(_ALLOWED_CHARS - set('#')))
_FRAG_CHARS = re.escape(''.join(_ALLOWED_CHARS))

_ABS_RE = (r'(?P<path>[' + _PATH_CHARS + ']*)'
           r'(\?(?P<query>[' + _QUERY_CHARS + ']*))?'
           r'(#(?P<fragment>[' + _FRAG_CHARS + '])*)?')

_URL_RE_STRICT = re.compile(r'^(?:(?P<scheme>[' + _SCHEME_CHARS + ']+):)?'
                            r'(//(?P<authority>[' + _AUTH_CHARS + ']*))?'
                            + _ABS_RE)


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


def parse_authority(au_str):  # TODO: namedtuple?
    user, pw, hostinfo = parse_userinfo(au_str)
    family, host, port = parse_hostinfo(hostinfo)
    return user, pw, family, host, port


def parse_hostinfo(au_str):
    """\
    returns:
      family (socket constant or None), host (string), port (int or None)

    >>> parse_hostinfo('googlewebsite.com:443')
    (None, 'googlewebsite.com', 443)
    >>> parse_hostinfo('[::1]:22')
    (10, '::1', 22)
    >>> parse_hostinfo('192.168.1.1:5000')
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


def parse_userinfo(au_str):
    userinfo, _, hostinfo = au_str.partition('@')
    if hostinfo:
        username, _, password = userinfo.partition(':')
    else:
        username, password, hostinfo = None, None, au_str
    return username, password, hostinfo


def parse_url(url_str, encoding=DEFAULT_ENCODING, strict=False):
    if not isinstance(url_str, unicode):
        try:
            url_str = url_str.decode(encoding)
        except AttributeError:
            raise TypeError('parse_url expected str, unicode, or bytes')
    um = (_URL_RE_STRICT if strict else _URL_RE).match(url_str)
    try:
        gs = um.groupdict()
    except AttributeError:
        raise ValueError('could not parse url: %r' % url_str)
    if gs['authority']:
        gs['authority'] = gs['authority'].encode('utf-8').decode('idna')
    else:
        gs['authority'] = ''
    user, pw, family, host, port = parse_authority(gs['authority'])
    gs['username'] = user
    gs['password'] = pw
    gs['family'] = family
    gs['host'] = host
    gs['port'] = port
    return gs


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


class QueryArgDict(OrderedMultiDict):
    # TODO: caching

    @classmethod
    def from_string(cls, query_string):
        pairs = parse_qsl(query_string, keep_blank_values=True)
        return cls(pairs)

    def encode(self, encoding=None):
        # note: uses '%20' instead of '+' for spaces, based partially
        # on observed behavior in chromium.
        encoding = encoding or DEFAULT_ENCODING
        safe = "!$'()*+,/:;?@[]~"  # unsafe = '#&='
        ret_list = []
        for k, v in self.iteritems(multi=True):
            key = quote(unicode(k).encode(encoding), safe=safe)
            val = quote(unicode(v).encode(encoding), safe=safe)
            ret_list.append('='.join((key, val)))
        return '&'.join(ret_list)


# TODO: naming: 'args', 'query_args', or 'query_params'?

class URL(BytestringHelper):
    _attrs = ('scheme', 'username', 'password', 'family',
              'host', 'port', 'path', 'query', 'fragment')

    def __init__(self, url_str=None, encoding=None, strict=False):
        encoding = encoding or DEFAULT_ENCODING
        self.encoding = encoding
        url_dict = {}
        if url_str:
            url_dict = parse_url(url_str, encoding=encoding, strict=strict)

        _d = unicode()
        self.params = _d  # TODO: support path params?
        for attr in self._attrs:
            setattr(self, attr, url_dict.get(attr, _d) or _d)
        self.args = QueryArgDict.from_string(self.query)

    @property
    def authority(self):
        ret = []
        if self.username:
            ret.append(self.username)
            if self.password:
                ret.extend([':', self.password])
            ret.append('@')
        ret.append(self.http_request_host)
        return unicode().join(ret)

    @property
    def http_request_uri(self):  # TODO: name
        return ''.join([self.path, self.query_string])

    @property
    def http_request_host(self):  # TODO: name
        ret = []
        host = self.host.encode('idna')
        if self.family == socket.AF_INET6:
            ret.extend(['[', host, ']'])
        else:
            ret.append(host)
        if self.port:
            ret.extend([':', unicode(self.port)])
        return ''.join(ret)

    @property
    def query_string(self):
        return self.args.encode(self.encoding)

    def __iter__(self):
        s = self
        return iter((s.scheme, s.authority, s.path,
                     s.params, s.query_string, s.fragment))

    def encode(self, encoding=None):
        encoding = encoding or self.encoding
        return urlunparse(self).encode(encoding)  # TODO

    def to_bytes(self):
        return self.encode()

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.encode())


def url2parseresult(url_str):
    from urlparse import ParseResult  # TODO: temporary, for testing
    pd = parse_url(url_str)
    parsed = ParseResult(pd['scheme'], pd['authority'], pd['path'],
                         '', pd['query'], pd['fragment'])
    parsed = parsed._replace(netloc=parsed.netloc.decode('idna'))
    return parsed
