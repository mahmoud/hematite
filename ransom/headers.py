# -*- coding: utf-8 -*-

from operator import attrgetter

ALL, REQUEST, RESPONSE, CAP_MAP = None, None, None, None


def _init_headers():
    # called (and del'd) at the very bottom
    global ALL, REQUEST, RESPONSE, CAP_MAP
    ALL = GENERAL + REQUEST_ONLY + RESPONSE_ONLY + ENTITY
    REQUEST = GENERAL + REQUEST_ONLY + ENTITY
    RESPONSE = GENERAL + RESPONSE_ONLY + ENTITY
    CAP_MAP = dict([(h.lower(), h) for h in ALL])
    return


def http_header_case(text):
    try:
        return CAP_MAP[text.lower()]
    except KeyError:
        # Exceptions: ETag, TE, WWW-Authenticate, Content-MD5
        return '-'.join([p.capitalize() for p in text.split('-')])


class MessageField(object):
    # TODO

    def __init__(self, name, getter=None, setter=None,
                 read_only=False, doc=None):
        self.name = name
        self.http_name = http_header_case(name)
        self.getter = getter or attrgetter('_' + name)
        self.setter = setter
        self.read_only = bool(read_only)
        self.doc = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.getter(obj)

    def __set__(self, obj, value):
        if self.read_only:
            raise AttributeError("read-only field '%s'" % self.name)
        if self.setter:
            return self.setter(obj, value)
        setattr(obj, '_' + self.name, value)

    def __delete__(self, obj):
        raise AttributeError("can't delete field property '%s'" % self.name)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s("%s", read_only=%r)' % (cn, self.name, self.read_only)


GENERAL = ['Cache-Control',
           'Connection',
           'Date',
           'Pragma',
           'Trailer',
           'Transfer-Encoding',
           'Upgrade',
           'Via',
           'Warning']

REQUEST_ONLY = ['Accept',
                'Accept-Charset',
                'Accept-Encoding',
                'Accept-Language',
                'Authorization',
                'Cookie',  # RFC6265
                'Expect',
                'From',
                'Host',
                'If-Match',
                'If-Modified-Since',
                'If-None-Match',
                'If-Range',
                'If-Unmodified-Since',
                'Max-Forwards',
                'Proxy-Authorization',
                'Range',
                'Referer',
                'TE',
                'User-Agent']

RESPONSE_ONLY = ['Accept-Ranges',
                 'Age',
                 'ETag',
                 'Location',
                 'Proxy-Authenticate',
                 'Retry-After',
                 'Server',
                 'Set-Cookie',  # RFC6265
                 'Vary',
                 'WWW-Authenticate']

ENTITY = ['Allow',
          'Content-Encoding',
          'Content-Language',
          'Content-Length',
          'Content-Location',
          'Content-MD5',
          'Content-Range',
          'Content-Type',
          'Expires',
          'Last-Modified']


_init_headers()
del _init_headers
