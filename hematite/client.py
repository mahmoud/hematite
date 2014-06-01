# -*- coding: utf-8 -*-

import ssl
import errno
import socket
from io import BlockingIOError

from hematite.async import join as async_join
from hematite.request import Request, RawRequest
from hematite.raw.parser import ResponseReader
from hematite.raw.drivers import SSLSocketDriver


DEFAULT_TIMEOUT = 5.0
CLIENT_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE',
                  'TRACE', 'OPTIONS', 'PATCH']  # CONNECT intentionally omitted


class ClientOperation(object):
    def __init__(self, client, method):
        self.client = client
        self.method = method

    def __call__(self, url, body=None):
        req = Request(self.method, url, body=body)
        self.client.populate_headers(req)
        return self.client.request(request=req)

    def async(self, url, body=None):
        req = Request(self.method, url, body=body)
        self.client.populate_headers(req)
        return self.client.request(request=req, async=True)


class UnboundClientOperation(object):
    def __init__(self, method):
        self.method = method

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return ClientOperation(client=obj, method=self.method)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(method=%r)' % (cn, self.method)


class Client(object):

    for client_method in CLIENT_METHODS:
        locals()[client_method.lower()] = UnboundClientOperation(client_method)
    del client_method

    def __init__(self, profile=None):
        self.profile = profile

    def populate_headers(self, request):
        if self.profile:
            self.profile.populate_headers(request)

    def get_addrinfo(self, request):
        # TODO: call from/merge with get_socket? would lose timing info
        # TODO: should one still run getaddrinfo even when a request has an IP
        # minor wtf: socket.getaddrinfo port can be a service name like 'http'
        ret = None
        url = request.host_url  # a URL object
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

        is_ssl = request.host_url.scheme.startswith('https')
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

    def request(self,
                request,
                async=False,
                autoload_body=True,
                timeout=DEFAULT_TIMEOUT):
        # TODO: kwargs for raise_exc, follow_redirects
        kw = dict(client=self, request=request, autoload_body=autoload_body)
        client_resp = ClientResponse(**kw)
        if async:
            return client_resp
        async_join([client_resp], timeout=timeout)
        return client_resp


class _OldState(object):
    # TODO: ssl_connect?

    (NotStarted, LookupHost, Connect, SendRequestHeaders, SendRequestBody,
     ReceiveResponseHeaders, ReceiveResponseBody, Complete) = range(8)

    # Alternate schemes:
    #
    # Past tense:
    # NotStarted, Started, HostResolved, Connected, RequestEnvelopeSent,
    # RequestSent, ResponseStarted, ResponseEnvelopeComplete, ResponseComplete
    #
    # Gerunds:
    # None, ResolvingHost, Connecting, SendingRequestEnvelope,
    # SendingRequestContent, Waiting, ReceivingResponse,
    # ReceivingResponseContent, Complete


class _State(object):
    # TODO: Securing/Handshaking
    # TODO: WaitingForContinue  # 100 Continue that is
    (NotStarted, ResolvingHost, Connecting, Sending, Receiving,
     Complete) = range(6)

"""RawRequest conversion paradigms:

if not isinstance(req, RawRequest):
    rreq = req.to_raw_request()

if isinstance(req, Request):
    rreq = RawRequest.from_request(req)

Which is more conducive to extensibility?

TODO: in order to enable sending a straight RawRequest, might need an
explicit URL field.
"""


class ClientResponse(object):
    # TODO: are we going to need want_read/want_write for SSL?

    def __init__(self, client, request=None, **kwargs):
        self.client = client
        self.request = request

        if request is None:
            self.raw_request = None  # TODO
        elif isinstance(request, RawRequest):
            self.raw_request = request
        elif isinstance(request, Request):
            self.raw_request = request.to_raw_request()
        else:
            raise TypeError('expected request to be a Request or RawRequest')

        self.state = _State.NotStarted
        self.socket = None
        self.driver = None
        self.timings = {}
        # TODO: need to set error and Complete state on errors
        self.error = None

        self.raw_response = None

        self.autoload_body = kwargs.pop('autoload_body', True)
        self.nonblocking = kwargs.pop('nonblocking', False)
        self.timeout = kwargs.pop('timeout', None)

        # TODO: request body/total bytes uploaded counters
        # TODO: response body/total bytes downloaded counters
        # (for calculating progress)

    def get_data(self):
        if not self._resp_body:
            return None
        return self._resp_body.get_data()

    def fileno(self):
        if self.socket:
            return self.socket.fileno()
        return None  # or raise an exception?

    @property
    def semantic_state(self):
        return ('TBI', 'TBI details')

    @property
    def is_complete(self):
        return self.state == _State.Complete

    @property
    def want_write(self):
        driver = self.driver
        if not driver:
            return True  # to resolve hosts and connect
        return driver.want_write

    @property
    def want_read(self):
        driver = self.driver
        if not driver:
            return False
        if driver.want_read:
            if not self.autoload_body and driver.inbound_headers_completed:
                return False
            return True
        return False

    def do_write(self):
        if self.raw_request is None:
            raise ValueError('request not set')
        state, request = self.state, self.raw_request

        # TODO: BlockingIOErrors for DNS/connect?
        # TODO: SSLErrors on connect? (SSL is currently inside the driver)
        try:
            if state is _State.NotStarted:
                self.state += 1
            elif state is _State.ResolvingHost:
                self.addrinfo = self.client.get_addrinfo(request)
                self.state += 1
            elif state is _State.Connecting:
                self.socket = self.client.get_socket(request,
                                                     self.addrinfo,
                                                     self.nonblocking)
                writer = self.raw_request.get_writer()
                self.driver = SSLSocketDriver(self.socket,
                                              reader=ResponseReader(),
                                              writer=writer)
                self.state += 1
            elif state is _State.Sending:
                if self.driver.write():
                    self.state += 1
            else:
                raise RuntimeError('not in a writable state: %r' % state)
        except BlockingIOError:
            return False
        return self.want_write

    def do_read(self):
        state = self.state
        try:
            if state is _State.Receiving:
                self.raw_response = self.driver.reader.raw_response
                res = self.driver.read()
                if res:
                    self.state += 1
            else:
                raise RuntimeError('not in a readable state: %r' % state)
        except BlockingIOError:
            return False
        return self.want_read
        # TODO: return socket
        # TODO: how to resolve socket returns with as-yet-unfetched body
        # (terminology: lazily-fetched?)
        # TODO: compression support goes where? how about charset decoding?
        # TODO: callback on read complete (to release socket)
