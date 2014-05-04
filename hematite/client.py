# -*- coding: utf-8 -*-

import errno
import socket

from hematite.socket_io import iopair_from_socket
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
        reader, writer = iopair_from_socket(conn)
        resp = Response.from_io(reader)
        return resp

    def get(self, url, **kw):
        kw['method'] = 'GET'
        kw['url'] = url
        return self.request(**kw)

    def post(self, url, **kw):
        kw['method'] = 'POST'
        kw['url'] = url
        return self.request(**kw)

    def get_addrinfo(self, request):
        # TODO: call from/merge with get_socket? would lose timing info
        # TODO: should one still run getaddrinfo even when a request has an IP
        # minor wtf: socket.getaddrinfo port can be a service name like 'http'
        ret = None
        url = request._url  # the URL object
        host = url.host
        port = url.port or (443 if url.scheme.lower() == 'https' else 80)

        # here we use the value of url.family to indicate whether host
        # is already an IP or not. the user might have mucked with
        # this, so maybe a better check is in order.
        if url.family is None:
            # assuming TCP ;P
            # big wtf: no kwargs on getaddrinfo
            addrinfos = socket.getaddrinfo(host,
                                           port,
                                           socket.AF_UNSPEC,  # v4/v6
                                           socket.SOCK_STREAM,
                                           socket.IPPROTO_TCP)
            # TODO: configurable behavior on multiple returns?
            # TODO: (cont.) set preference for IPv4/v6

            # NOTE: raises exception on unresolvable hostname, so
            #       addrinfo[0] should never indexerror
            family, socktype, proto, canonname, sockaddr = addrinfos[0]
            ret = (family, socktype) + sockaddr
        elif url.family is socket.AF_INET:
            ret = (url.family, socket.SOCK_STREAM, host, port)
        elif url.family is socket.AF_INET6:
            # TODO: how to handle flowinfo, scopeid here? is None even valid?
            ret = (url.family, socket.SOCK_STREAM, host, port, None, None)
        else:
            raise ValueError('invalid family on url: %r' % url)

        # NOTE: it'd be cool to just return an unconnected socket
        # here, but even unconnected sockets use fds
        return ret

    # TODO: maybe split out addrinfo into relevant fields
    # TODO: make request optional?
    def get_socket(self, request, addrinfo, nonblocking):
        # yikes
        family, socktype, sockaddr = addrinfo[0], addrinfo[1], addrinfo[2:]

        ret = socket.socket(family, socktype)
        if nonblocking:
            ret.setblocking(0)
        try:
            conn_res = ret.connect_ex(sockaddr)
        except socket.error as se:
            conn_res = se.args[0]

        if conn_res:
            if conn_res not in (errno.EISCONN, errno.EWOULDBLOCK,
                                errno.EINPROGRESS, errno.EALREADY):
                socket.error('Unknown', conn_res)

        # TODO: what's this do?
        err = ret.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err:
            raise socket.error('Unknown', err)

        return ret
