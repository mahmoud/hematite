# -*- coding: utf-8 -*-

from io import BlockingIOError

from hematite import serdes
from hematite.fields import RESPONSE_FIELDS
from hematite.constants import CODE_REASONS
#from hematite.socket_io import iopair_from_socket, readline
from hematite.request import Request

from hematite.raw import messages as M
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

    def __init__(self, client, request=None):
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

        self.autoload_body = True
        self.nonblocking = False
        self.timeout = None

        self.raw_response = None
        self._resp_body = None

        # TODO: request body/total bytes uploaded counters
        # TODO: response body/total bytes downloaded counters
        # (for calculating progress)

        # TODO: need to set error and Complete state on errors
        self.error = None

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

                """
                elif state is _State.ReceiveResponseBody:
                if not self._resp_body:
                    headers = self.raw_response.headers
                    self._resp_body = ClientResponseBody(headers,
                                                         self._reader)
                if self.autoload_body:
                    if self._resp_body.read_body():
                        self.state += 1
                else:
                    self.state += 1
                """
            else:
                raise RuntimeError('not in a readable state: %r' % state)
        except BlockingIOError:
            return False
        return self.want_read
        # TODO: return socket
        # TODO: how to resolve socket returns with as-yet-unfetched body
        # (terminology: lazily-fetched?)

    def write_request_headers(self):
        if not self._writer.empty:
            self._writer.write(None)

        next_bit = next(self._writer_iter, M.Empty)
        if next_bit is M.Empty:
            return True
        self._writer.write(next_bit.value)
        return False

    def read_response_headers(self):
        while not self.raw_response.state == M.Complete:
            if type(self.raw_response.state) is type(M.NeedLine):
                # TODO: polish up the messages paradigm
                line = readline(self._reader)
                next_state = M.HaveLine(value=line)
            else:
                raise RuntimeError('Unknown state %r'
                                   % self.raw_response.state)
            self.raw_response.state = self.raw_response.reader.send(next_state)
        return True  # TODO: pretty sure this is fine right?


class ClientResponseBody(object):
    # TODO: may merge somewhere or get a more generic name
    # TODO: compression support goes here? how about charset decoding?
    # TODO: callback on read complete (to release socket)
    def __init__(self, headers, reader):
        self.reader = reader
        self._parts = []
        self._data = None

        is_chunked = Body(headers).chunked  # TODO
        if is_chunked:
            self._body = ChunkEncodedBody(headers)
            self.read_body = self._read_response_body_chunk
        else:
            self._body = IdentityEncodedBody(headers)
            self.read_body = self._read_response_body_ident

    @property
    def is_loaded(self):
        return self._data is not None

    def get_data(self):
        if not self._data:
            self.read_body()
            if len(self._parts) == 1:
                self._data = self._parts[0]
            else:
                self._data = ''.join(self._parts)
        return self._data

    def _read_response_body_chunk(self):
        data = None
        body = self._body
        reader = self.reader
        while not body.complete:
            if body.state.type == M.NeedLine.type:
                line = readline(reader)
                next_state = M.HaveLine(value=line)
            elif body.state.type == M.NeedData.type:
                data = reader.read(body.state.amount)
                if data is None:
                    raise BlockingIOError(None, None)
                next_state = M.HaveData(value=data)
            elif body.state.type == M.NeedPeek.type:
                peeked = reader.peek(body.state.amount)
                if not peeked:
                    raise BlockingIOError(None, None)
                next_state = M.HavePeek(amount=peeked)
            elif body.state.type == M.HaveData.type:
                self._parts.append(body.state.value)
                next_state = M.Empty
            else:
                raise RuntimeError('Unknown state {0}'.format(body.state))
            body.state = body.reader.send(next_state)

        assert body.complete, 'Unknown state {0}'.format(body.state)
        return body.complete

    def _read_response_body_ident(self, amt=None):
        body = self._body
        reader = self.reader
        while not body.complete:
            if body.state.type == M.NeedData.type:
                data = reader.read(body.state.amount)
                if data is None:
                    raise BlockingIOError(None, None)
                self._parts.append(data)
                next_state = M.HaveData(value=data)
            else:
                raise RuntimeError('Unknown state {0}'.format(body.state))
            body.state = body.reader.send(next_state)

        assert body.complete, 'Unknown state {0}'.format(body.state)
        return body.complete




# Thought: It's prudent to raise exceptions with unencoded
# text. Knowing that exception messages will end up in consoles,
# logfiles, and on crazy wires to crazy places, it's safest to raise
# exceptions with ASCII bytestring messages where possible.
