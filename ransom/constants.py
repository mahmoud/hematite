# -*- coding: utf-8 -*-


CAP_MAP = None
ALL_HEADERS, REQUEST_HEADERS, RESPONSE_HEADERS = None, None, None


def _init_headers():
    # called (and del'd) at the very bottom
    global ALL_HEADERS, REQUEST_HEADERS, RESPONSE_HEADERS, CAP_MAP
    ALL_HEADERS = (GENERAL_HEADERS + REQUEST_ONLY_HEADERS
                   + RESPONSE_ONLY_HEADERS + ENTITY_HEADERS)
    REQUEST_HEADERS = GENERAL_HEADERS + REQUEST_ONLY_HEADERS + ENTITY_HEADERS
    RESPONSE_HEADERS = GENERAL_HEADERS + RESPONSE_ONLY_HEADERS + ENTITY_HEADERS
    CAP_MAP = dict([(h.lower(), h) for h in ALL_HEADERS])
    return


GENERAL_HEADERS = ['Cache-Control',
                   'Connection',
                   'Date',
                   'Pragma',
                   'Trailer',
                   'Transfer-Encoding',
                   'Upgrade',
                   'Via',
                   'Warning']

REQUEST_ONLY_HEADERS = ['Accept',
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

RESPONSE_ONLY_HEADERS = ['Accept-Ranges',
                         'Age',
                         'ETag',
                         'Location',
                         'Proxy-Authenticate',
                         'Retry-After',
                         'Server',
                         'Set-Cookie',  # RFC6265
                         'Vary',
                         'WWW-Authenticate']

ENTITY_HEADERS = ['Allow',
                  'Content-Encoding',
                  'Content-Language',
                  'Content-Length',
                  'Content-Location',
                  'Content-MD5',
                  'Content-Range',
                  'Content-Type',
                  'Expires',
                  'Last-Modified']

HOP_BY_HOP_HEADERS = ['Connection',
                      'Keep-Alive',
                      'Proxy-Authenticate',
                      'TE',
                      'Trailers',
                      'Transfer-Encoding',
                      'Upgrade']


_init_headers()
del _init_headers

from pprint import pprint
pprint(RESPONSE_HEADERS)
