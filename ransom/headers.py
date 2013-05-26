# -*- coding: utf-8 -*-

ALL, REQUEST, RESPONSE, CAP_MAP = None, None, None, None


def http_header_case(text):
    try:
        return CAP_MAP[text.lower()]
    except KeyError:
        # Exceptions: ETag, TE, WWW-Authenticate, Content-MD5
        return '-'.join([p.capitalize() for p in text.split('-')])


def _init_headers():
    # called (and del'd) at the very bottom
    global ALL, REQUEST, RESPONSE, CAP_MAP
    ALL = GENERAL + REQUEST_ONLY + RESPONSE_ONLY + ENTITY
    REQUEST = GENERAL + REQUEST_ONLY + ENTITY
    RESPONSE = GENERAL + RESPONSE_ONLY + ENTITY
    CAP_MAP = dict([(h.lower(), h) for h in ALL])
    return


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
