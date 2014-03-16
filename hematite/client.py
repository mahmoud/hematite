# -*- coding: utf-8 -*-

import socket

from hematite.compat import bio_from_socket
from hematite.request import Request
from hematite.response import Response

DEFAULT_PORTS = {'http': 80,
                 'https': 443}


class Client(object):
    def __init__(self):
        pass

    def get(self, url, **kw):
        kw['method'] = 'GET'
        kw['url'] = url
        req = Request(**kw)

        hostname = req.hostname
        if not hostname:
            raise ValueError('no hostname found in URL: %r' % url)
        scheme = req._url.scheme
        port = req.port or DEFAULT_PORTS.get(req._url.scheme)  # TODO
        if not port:
            raise ValueError('unknown scheme %r and no port found in URL: %r'
                             % (scheme, url))

        conn = socket.create_connection((hostname, port))
        req_bytes = req.to_bytes()
        conn.sendall(req_bytes)
        resp = Response.from_io(bio_from_socket(conn, mode='rb'))

        if resp.is_chunked:
            body = []
            while True:
                chunk = resp._body.read_chunk()
                if not chunk:
                    break
                body.append(chunk)
            body = ''.join(body)
        else:
            body = resp._body.read()
        return resp, body
