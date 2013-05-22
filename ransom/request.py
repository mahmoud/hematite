# -*- coding: utf-8 -*-

from compat import (unicode, bytes, OrderedMultiDict,
                    urlparse, urlunparse, urlencode)

from url import URL, parse_hostinfo

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

# TODO: incremental parsing/creation of Request
"""

DEFAULT_METHOD = 'GET'
DEFAULT_VERSION = (1, 1)
DEFAULT_SCHEME = 'http'
DEFAULT_PORT = 80


class Request(object):
    def __init__(self, method=None, url=None, headers=None,
                 version=None, client=None, **kw):
        self.method = method or DEFAULT_METHOD
        self.url = url
        headers = OrderedMultiDict(headers or {})
        self.headers = OrderedMultiDict([(k.lower(), v) for k, v in
                                         headers.iteritems()])

        host_header = self.headers.pop('host', '')
        f, h, p = parse_hostinfo(host_header)
        if not self.url.host:
            # Request-line URL overrides Host header
            self.url.family, self.url.host, self.url.port = f, h, p
        if not self.url.scheme:
            self.url.scheme = DEFAULT_SCHEME

        self.version = version or DEFAULT_VERSION
        self.client = client

    def encode(self, validate=True):
        ret = [self.request_line]
        ret.extend(['Host: ' + self.url.http_request_host, '', ''])
        return '\r\n'.join(ret).encode('latin-1')

    @classmethod
    def from_string(cls, source):
        raise NotImplementedError('http parser does not support '
                                  'parsing requests (for now)')

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
