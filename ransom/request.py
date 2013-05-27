# -*- coding: utf-8 -*-

from http_parser import HttpParser

from compat import (unicode, bytes, OrderedMultiDict,
                    urlparse, urlunparse, urlencode)

from url import URL, parse_hostinfo
from headers import HTTPHeaderField, header2attr_name


"""
- method: methodcaller->upper, default GET
- http version: float() -> str
- path
- host
- user_agent
- accept
  - mime
  - charset
  - language

URL: scheme, netloc (host), path, params, query (, fragment?)
URL+: username, password, hostname, port

NB Blank headers are not sent
# TODO: incremental parsing/creation of Request
"""

DEFAULT_METHOD = 'GET'
DEFAULT_VERSION = (1, 1)
DEFAULT_SCHEME = 'http'
DEFAULT_PORT = 80

# headers, url, cookies
# ['accept-language', 'accept-encoding', 'accept', 'user-agent', 'accept-charset', 'connection', 'cookie'


class Request(object):
    accept_language = HTTPHeaderField('accept_language')
    accept_encoding = HTTPHeaderField('accept_encoding')
    connection = HTTPHeaderField('connection')

    def __init__(self, method=None, url=None, headers=None,
                 version=None, client=None, **kw):
        self.client = client
        self.method = method or DEFAULT_METHOD
        self.url = url
        if headers:
            headers = dict([(k.lower(), v) for k, v in headers.iteritems()])
        else:
            headers = {}
        headers = OrderedMultiDict(headers)
        self.known_headers = OrderedMultiDict()
        self.extra_headers = headers
        host_header = headers.pop('host', '')
        f, h, p = parse_hostinfo(host_header)
        if not self.url.host:
            # Request-line URL overrides Host header
            self.url.family, self.url.host, self.url.port = f, h, p
        if not self.url.scheme:
            self.url.scheme = DEFAULT_SCHEME
        self.version = version or DEFAULT_VERSION

        fields = self.get_fields()
        for name in headers:
            attr_name = header2attr_name(name)
            if attr_name in fields:
                self.known_headers[attr_name] = headers.pop(name)

    def encode(self, validate=True):
        # TODO: field values are latin-1 or mime-encoded, but
        # are field names latin-1 or ASCII only?
        ret = [self.request_line]
        ret.append('Host: ' + self.url.http_request_host)
        for n, f in self.get_fields().items():
            v = getattr(self, f.attr_name)
            if v:
                ret.append(f.http_name + ': ' + v)
        for h, v in self.extra_headers.iteritems():
            if v:
                ret.append(h + ': ' + v)
        ret.extend(['', ''])
        return '\r\n'.join(ret).encode('latin-1')

    @classmethod
    def from_string(cls, source):
        hp = HttpParser()
        hp.execute(source, len(source))
        hp.execute('', 0)
        return cls(hp._method, hp._url, hp._headers, hp._version)

    @classmethod
    def get_fields(cls):
        return dict([(n, f) for n, f in cls.__dict__.items()
                     if isinstance(f, HTTPHeaderField)])

    @property
    def request_line(self):
        return ' '.join([self.method,
                         self.url.http_request_uri,
                         'HTTP/%d.%d' % self.version])

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, method=None):
        if method is None:
            method = DEFAULT_METHOD
        try:
            self._method = method.upper()
        except (AttributeError, TypeError):
            raise ValueError('http method expected string')

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        if isinstance(url, URL):
            self._url = url  # TODO
        else:
            self._url = URL(url or '')
