# -*- coding: utf-8 -*-

import socket

from hematite.socket_io import bio_from_socket
from hematite.request import Request
from hematite.response import Response

DEFAULT_PORTS = {'http': 80,
                 'https': 443}


class Client(object):
    def __init__(self):
        pass

    def request(self, method, url, **kw):
        kw['method'] = method
        kw['url'] = url
        req = Request(**kw)

        hostname = req.hostname
        if not hostname:
            raise ValueError('no hostname found in URL: %r' % url)
        scheme = req._url.scheme
        port = req.port or DEFAULT_PORTS.get(req.scheme)
        if not port:
            raise ValueError('unknown scheme %r and no port found in URL: %r'
                             % (scheme, url))
        conn = socket.create_connection((hostname, port))
        req_bytes = req.to_bytes()
        conn.sendall(req_bytes)
        resp = Response.from_io(bio_from_socket(conn, mode='rb'))
        return resp

    def get(self, url, **kw):
        kw['method'] = 'GET'
        kw['url'] = url
        return self.request(**kw)

    def post(self, url, **kw):
        kw['method'] = 'POST'
        kw['url'] = url
        return self.request(**kw)



class Operation(object):
    def __init__(self, method):
        self.method = method

    def __call__(self, *a, **kw):
        pass

    def async(self, *a, **kw):
        pass

    def _call(self, args, kwargs):
        pass
