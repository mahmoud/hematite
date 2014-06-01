# -*- coding: utf-8 -*-

import ssl
import errno
import socket


class Client(object):

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

        is_ssl = request.url.startswith('https')
        if nonblocking:
            ret.setblocking(0)
        if is_ssl:
            ret = ssl.wrap_socket(ret)

        try:
            conn_res = ret.connect_ex(sockaddr)
        except socket.error as se:
            conn_res = se.args[0]

        if conn_res:
            if conn_res not in (errno.EISCONN, errno.EWOULDBLOCK,
                                errno.EINPROGRESS, errno.EALREADY):
                socket.error('Unknown', conn_res)

        # djb points out that some socket error conditions are only
        # visible with this 'one weird old trick'
        err = ret.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err:
            raise socket.error('Unknown', err)

        return ret


class Operation(object):
    def __init__(self, method):
        self.method = method

    def __call__(self, *a, **kw):
        pass

    def async(self, *a, **kw):
        pass

    def _call(self, args, kwargs):
        pass
