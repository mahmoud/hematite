# -*- coding: utf-8 -*-

import re
import socket

from compat import (unicode, bytes, urlunparse, quote,
                    parse_qsl, OrderedMultiDict, BytestringHelper)

"""
 - url.params (semicolon separated) http://www.w3.org/TR/REC-html40/appendix/notes.html#h-B.2.2
 - support python compiled without IPv6
 - IRI encoding
 - support empty port (e.g., http://gweb.com:/)
"""

DEFAULT_ENCODING = 'utf-8'

# The unreserved URI characters (per RFC 3986)
_UNRESERVED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789-._~")
# chars reserved some (but not all places)
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


def _make_quote_map(allowed_chars):
    ret = {}
    for i, c in zip(range(256), str(bytearray(range(256)))):
        ret[c] = c if c in allowed_chars else '%{0:02X}'.format(i)
    return ret


_PATH_QUOTE_MAP = _make_quote_map(_ALLOWED_CHARS - set('?#'))
_QUERY_ELEMENT_QUOTE_MAP = _make_quote_map(_ALLOWED_CHARS - set('#&='))


def quote_path(text):
    try:
        bytestr = text.encode('utf-8')
    except UnicodeDecodeError:
        pass
    except:
        raise ValueError('expected text or UTF-8 encoded bytes, not %r' % text)
    return ''.join([_PATH_QUOTE_MAP[b] for b in bytestr])


def quote_query_element(text):
    try:
        bytestr = text.encode('utf-8')
    except UnicodeDecodeError:
        pass
    except:
        raise ValueError('expected text or UTF-8 encoded bytes, not %r' % text)
    return ''.join([_QUERY_ELEMENT_QUOTE_MAP[b] for b in bytestr])


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
            except ValueError:
                raise ValueError('invalid authority in URL %r expected int'
                                 ' for port, not %r)' % (au_str, port_str))
        else:
            host, port = au_str, None
        if host and '[' == host[0] and ']' == host[-1]:
            host = host[1:-1]
            try:
                socket.inet_pton(socket.AF_INET6, host)
            except socket.error:
                raise ValueError('invalid IPv6 host: %r' % host)
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
            raise TypeError('parse_url expected str, unicode, or bytes, not %r'
                            % url_str)
    um = (_URL_RE_STRICT if strict else _URL_RE).match(url_str)
    try:
        gs = um.groupdict()
    except AttributeError:
        raise ValueError('could not parse url: %r' % url_str)
    if gs['authority']:
        try:
            gs['authority'] = gs['authority'].decode('idna')
        except:
            pass
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
    # TODO: self.update_extend_from_string()?

    @classmethod
    def from_string(cls, query_string):
        pairs = parse_qsl(query_string, keep_blank_values=True)
        return cls(pairs)

    def encode(self):
        # note: uses '%20' instead of '+' for spaces, based partially
        # on observed behavior in chromium.
        ret_list = []
        for k, v in self.iteritems(multi=True):
            key = quote_query_element(unicode(k))
            val = quote_query_element(unicode(v))
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
    def is_absolute(self):
        return bool(self.scheme)  # RFC2396 3.1

    @property
    def http_request_url(self):  # TODO: name
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
        return self.args.encode()

    def __iter__(self):
        s = self
        return iter((s.scheme, s.get_authority(idna=True), s.path,
                     s.params, s.query_string, s.fragment))

    def encode(self, encoding=None):
        encoding = encoding or self.encoding
        return self.to_text().encode(encoding)

    # TODO: normalize?

    def get_authority(self, idna=True):
        parts = []
        _add = parts.append
        if self.username:
            _add(self.username)
            if self.password:
                _add(':')
                _add(self.password)
            _add('@')
        if self.host:
            if self.family == socket.AF_INET6:
                _add('[')
                _add(self.host)
                _add(']')
            elif idna:
                _add(self.host.encode('idna'))
            else:
                _add(self.host)
            if self.port:
                _add(':')
                _add(unicode(self.port))
        return u''.join(parts)

    def to_text(self, idna=True):
        scheme, path, params = self.scheme, self.path, self.params
        authority = self.get_authority(idna=idna)
        query_string, fragment = self.query_string, self.fragment

        parts = []
        _add = parts.append
        if scheme:
            _add(scheme)
            _add(':')
        if authority:
            _add('//')
            _add(authority)
        elif (scheme and path[:2] != '//'):
            _add('//')
        if path:
            if path[:1] != '/':
                _add('/')
            _add(quote_path(path))
        if params:
            _add(';')
            _add(params)
        if query_string:
            _add('?')
            _add(query_string)
        if fragment:
            _add('#')
            _add(fragment)
        return u''.join(parts)

    def to_bytes(self):
        return self.encode()

    @classmethod
    def from_bytes(cls, bytestr):
        return cls(bytestr)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.to_text())


def _urlunparse(data):
    """Put a parsed URL back together again.  This may result in a
    slightly different, but equivalent URL, if the URL that was parsed
    originally had redundant delimiters, e.g. a ? with an empty query
    (the draft states that these are equivalent)."""
    scheme, netloc, url, params, query, fragment = data
    if params:
        url = "%s;%s" % (url, params)
    return urlunsplit((scheme, netloc, url, query, fragment))

def _urlunsplit(data):
    """Combine the elements of a tuple as returned by urlsplit() into a
    complete URL as a string. The data argument can be any five-item iterable.
    This may result in a slightly different, but equivalent URL, if the URL that
    was parsed originally had unnecessary delimiters (for example, a ? with an
    empty query; the RFC states that these are equivalent)."""
    scheme, netloc, url, query, fragment = data
    if netloc or (scheme and scheme in uses_netloc and url[:2] != '//'):
        if url and url[:1] != '/': url = '/' + url
        url = '//' + (netloc or '') + url
    if scheme:
        url = scheme + ':' + url
    if query:
        url = url + '?' + query
    if fragment:
        url = url + '#' + fragment
    return url
