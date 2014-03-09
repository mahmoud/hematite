# -*- coding: utf-8 -*-

import string

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


def header2attr_name(text):
    return '_'.join(text.split('-')).lower()


def attr2header_name(text):
    return http_header_case(text.replace('_', '-'))


# TODO: native type? encode()?

class HTTPHeaderField(object):
    def __init__(self, name, load=None, dump=None, encode=None,
                 read_only=False, doc=None):
        self.attr_name = header2attr_name(name)
        self.http_name = attr2header_name(name)
        self.load = load
        self.dump = dump
        self.read_only = bool(read_only)
        self.doc = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        val = obj.headers.get(self.http_name, None)
        if self.load and not isinstance(val, self.native_type):
            # TODO
            val = self.load(val)
        return val

    def __set__(self, obj, value):
        if self.read_only:
            raise AttributeError("read-only field '%s'" % self.attr_name)
        obj.headers[self.http_name] = value

    def __delete__(self, obj):
        raise AttributeError("can't delete field '%s'" % self.attr_name)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s("%s", read_only=%r)' % (cn, self.attr_name, self.read_only)

    def encode(self, value, encoding='latin-1'):
        # TODO: hmm
        return self.http_name + ': ' + value.encode(encoding)


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

HOP_BY_HOP = ['Connection',
              'Keep-Alive',
              'Proxy-Authenticate',
              'TE',
              'Trailers',
              'Transfer-Encoding',
              'Upgrade']


_init_headers()
del _init_headers


_TOKEN_CHARS = frozenset("!#$%&'*+-.^_`|~" + string.letters + string.digits)


def quote_header_value(value, allow_token=True):
    value = str(value)
    if allow_token:
        if set(value).issubset(_TOKEN_CHARS):
            return value
    return '"%s"' % value.replace('\\', '\\\\').replace('"', '\\"')


def unquote_header_value(value, is_filename=False):
    if value and value[0] == value[-1] == '"':
        value = value[1:-1]
        if not is_filename or value[:2] != '\\\\':
            return value.replace('\\\\', '\\').replace('\\"', '"')
    return value


# Accept-style headers

import re



_accept_re = re.compile(r'('
                        r'(?P<media_type>[^,;]+)'
                        r'(;\s*q='
                        r'(?P<quality>[^,;]+))?),?')


def parse_accept_header(text):
    ret = []
    for match in _accept_re.finditer(text):
        try:
            quality = max(min(float(match.group('quality') or 1.0), 1), 0)
        except:
            quality = 0.0
        media_type = match.group('media_type')
        ret.append((media_type, quality))
    return ret


def _main():
    _accept_tests = ['audio/*; q=0.2, audio/basic',
                 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8']
    for t in _accept_tests:
        print
        print parse_accept_header(t)


if __name__ == '__main__':
    _main()
