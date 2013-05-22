# -*- coding: utf-8 -*-

from compat import (unicode, bytes, OrderedMultiDict,
                    urlparse, urlunparse, urlencode)

from url import URL

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


class Request(object):
    def __init__(self, method=None, url=None, headers=None,
                 version=None, client=None, **kw):
        self.method = method or DEFAULT_METHOD
        self.url = url
        self.headers = OrderedMultiDict(headers or {})
        self.version = version or DEFAULT_VERSION
        self.client = client

    def encode(self, validate=True):  # TODO: serialize?
        pass

    @classmethod
    def from_string(cls, source):
        raise NotImplementedError('http parser does not support '
                                  'parsing requests (for now)')

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
        if url is None or isinstance(url, URL):
            self._url = url  # TODO
        else:
            self._url = URL(url)
