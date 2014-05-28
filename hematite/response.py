# -*- coding: utf-8 -*-

from io import BlockingIOError

from hematite import serdes
from hematite.fields import RESPONSE_FIELDS
from hematite.constants import CODE_REASONS
from hematite.request import Request

from hematite.raw.drivers import NonblockingSocketClientDriver as NBSCD
from hematite.raw.parser import HTTPVersion
from hematite.raw.datastructures import Headers, Body, ChunkedBody
from hematite.raw import RawResponse, RawRequest

_DEFAULT_VERSION = HTTPVersion(1, 1)


class Response(object):
    # TODO: from_request convenience method?
    def __init__(self, status_code, body=None, **kw):
        self.status_code = int(status_code)
        self.reason = kw.pop('reason', None)
        if self.reason is None:
            self.reason = CODE_REASONS.get(self.status_code, '')
        self._raw_headers = kw.pop('headers', Headers())  # TODO
        self.http_version = kw.pop('http_version', _DEFAULT_VERSION)

        self._body = body
        self._data = None

        self._init_headers()
        # TODO: lots
        return

    # TODO: could use a metaclass for this, could also build it at init
    _header_field_map = dict([(hf.http_name, hf) for hf in RESPONSE_FIELDS])
    locals().update([(hf.attr_name, hf) for hf in RESPONSE_FIELDS])
    _init_headers = serdes._init_headers
    _get_header_dict = serdes._get_headers

    @property
    def is_chunked(self):
        return isinstance(self._body, ChunkedBody)

    def _load_data(self):
        if self.is_chunked:
            chunk_list = []
            while True:
                chunk = self._body.read_chunk()
                if not chunk:
                    break
                chunk_list.append(chunk)
            data = ''.join(chunk_list)
        else:
            data = self._body.read()
        self._data = data

    def get_data(self, as_bytes=True):
        if self._data is None:
            self._load_data()
        if as_bytes:
            return self._data
        try:
            charset = self.content_type.charset
            return self._data.decode(charset)
        except:
            # TODO: what to do here?
            pass
        return self._data

    @classmethod
    def from_raw_response(cls, raw_resp):
        sl = raw_resp.status_line
        kw = {'status_code': sl.status_code,
              'reason': sl.reason,
              'version': sl.version,
              'headers': raw_resp.headers,
              'body': raw_resp.body}
        return cls(**kw)

    def to_raw_response(self):
        headers = self._get_header_dict()
        return RawResponse(status_code=self.status_code,
                           reason=self.reason,
                           http_version=self.http_version,
                           headers=headers,
                           body=self._body)

    @classmethod
    def from_bytes(cls, bytestr):
        raw_resp = RawResponse.from_bytes(bytestr)
        return cls.from_raw_response(raw_resp)

    def to_bytes(self):
        raw_resp = self.to_raw_response()
        return raw_resp.to_bytes()

    @classmethod
    def from_io(cls, io_obj):
        raw_resp = RawResponse.from_io(io_obj)
        return cls.from_raw_response(raw_resp)

    def to_io(self, io_obj):
        raw_resp = self.to_raw_response()
        return raw_resp.to_io(raw_resp)

    def validate(self):
        pass


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

"""
RawRequest conversion paradigms:

if not isinstance(req, RawRequest):
    rreq = req.to_raw_request()

if isinstance(req, Request):
    rreq = RawRequest.from_request(req)

Which is more conducive to extensibility?
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
        return self.state <= _State.Sending

    @property
    def want_read(self):
        if self.state != _State.Receiving:
            return False
        elif not self.autoload_body and self.driver.inbound_headers_completed:
            return False
        else:
            return True
        # TODO: what if body fetching is deferred

    def do_write(self):
        if self.raw_request is None:
            raise ValueError('request not set')
        state, request = self.state, self.request

        # TODO: BlockingIOErrors for DNS/connect?
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
                self.driver = NBSCD(self.socket, self.raw_request)
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


# Thought: It's prudent to raise exceptions with unencoded
# text. Knowing that exception messages will end up in consoles,
# logfiles, and on crazy wires to crazy places, it's safest to raise
# exceptions with ASCII bytestring messages where possible.
