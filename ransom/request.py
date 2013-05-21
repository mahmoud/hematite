# -*- coding: utf-8 -*-

from compat import (unicode, bytes, OrderedDict, StringIO,
                    urlparse, urlunparse, urlencode)


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


class BaseRequest(object):
    def __init__(self, client=None):
        self.client = client

    def to_string(self, validate=True):  # TODO: serialize?
        pass

    @classmethod
    def from_string(cls, source):
        raise NotImplementedError('http parser does not support '
                                  'parsing requests (for now)')

    @property
    def method(self):
        return self._method

    @method.setter
    def _set_method(self, method=None):
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
    def _set_url(self, url):
        self._url = url  # TODO
