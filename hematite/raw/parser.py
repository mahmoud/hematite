import re
from abc import ABCMeta, abstractmethod
from collections import namedtuple

from hematite.compat import BytestringHelper, make_sentinel
from hematite.raw import datastructures
from hematite.raw import core
from hematite.url import URL, _ABS_RE
from hematite.constants import CODE_REASONS
from hematite.raw import messages as M

# TODO: maintain case

_MISSING = make_sentinel()


class HTTPParseException(core.HTTPException):
    """Raised when an error occurs while parsing an HTTP message"""


class InvalidStatusLine(HTTPParseException):
    """Raised when a response begins with an invalid status line.
    (RFC2616 6.1)"""


class InvalidVersion(InvalidStatusLine):
    """Raised when either a request or response provides an invalid HTTP
    version.  (RFC2616 3.1)"""


class InvalidStatusCode(InvalidStatusLine):
    """Raised when a response provides an invalid status code (RFC2616
    6.1.1)"""


class InvalidRequestLine(HTTPParseException):
    """Raised when a request begins with an invalid request line (RFC2616
    5.1)"""


class InvalidMethod(InvalidRequestLine):
    """Raised when a request line contains invalid method (RFC2616
    5.1.1)"""


class InvalidURI(InvalidRequestLine):
    """Raised when a request specifies an invalid URI (RFC2616 5.1.2;
    RFC2616 3.2)"""


class InvalidHeaders(HTTPParseException):
    """Raised when a request or response contains invalid headers (RFC2616
    4.2)"""


class BodyReadException(core.HTTPException):
    """Raised when an error occurs while reading a body"""


class IncompleteBody(BodyReadException):
    """Raised when a Content-Length defined body cannot be completely read."""


class InvalidChunk(BodyReadException):
    """Raised when a parse error occurs while consuming a chunk"""


class HTTPVersion(namedtuple('HTTPVersion', 'major minor'), BytestringHelper):
    """Represents an HTTP version (RFC2616 3.1).

    This is a :class:`~collections.namedtuple`, so versions can be
    naturally compared:

    >>> HTTPVersion(major=1, minor=1) > HTTPVersion(1, 0) > HTTPVersion(0, 9)
    True

    """

    PARSE_VERSION = re.compile('HTTP/'
                               '(?P<http_major_version>\d+)'
                               '\.'
                               '(?P<http_minor_version>\d+)')

    def to_bytes(self):
        return b'HTTP/%d.%d' % self

    @classmethod
    def from_match(cls, match):
        """Create an :class:`HTTPVersion` from a :class:`re.match` object.

        This is intended for use within other parsers.  You probably
        want :meth:`HTTPVersion.from_bytes` instead
        """
        if not match:
            raise InvalidVersion('Missing version string')
        major = match.group('http_major_version')
        minor = match.group('http_minor_version')

        if not (major or minor):
            raise InvalidVersion('Unparseable version', match.string)

        return cls(int(major), int(minor))

    @classmethod
    def from_bytes(cls, string):
        """Create an :class:`HTTPVersion` from a byte string.  Raises an
        :exc:`InvalidVersion` exception on errors.

        >>> HTTPVersion.from_bytes('HTTP/2.0')
        HTTPVersion(major=2, minor=0)
        """
        return cls.from_match(cls.PARSE_VERSION.search(string))


class StatusLine(namedtuple('StatusLine', 'version status_code reason'),
                 BytestringHelper):
    """
    Represents an HTTP Status-Line (RFC2616 6.1).
    """

    PARSE_STATUS_LINE = re.compile(''.join([
        '(?:', HTTPVersion.PARSE_VERSION.pattern, ')?',
        '(?:', core.START_LINE_SEP.pattern, ')?',
        '(?P<status_code>\d{3})?',
        '(?:', core.START_LINE_SEP.pattern,
        # 6.1: No CR or LF is allowed except in the final CRLF
        # sequence.
        '(?P<reason>[^', re.escape(core._TEXT_EXCLUDE), '\r\n]+))?']))

    def to_bytes(self):
        r"""Return a byte string representing this status line.  If
        :attribute:`StatusLine.reason` is `None`, this will attempt to
        provide one from the standard status code to reason mapping:

        >>> StatusLine(HTTPVersion(1, 1), status_code=200,
        ...            reason=None).to_bytes()
        'HTTP/1.1 200 OK\r\n'

        If :attribute:`StatusLine.reason` is otherwise false, the
        reason is completely omitted:

        >>> StatusLine(HTTPVersion(1, 1), status_code=200,
        ...            reason='').to_bytes()
        'HTTP/1.1 200\r\n'
        """
        version, status_code, reason = self
        if reason is None:
            reason = CODE_REASONS.get(status_code)

        if reason:
            reason = ' ' + reason

        return b'%s %d%s\r\n' % (version, status_code, reason)

    @classmethod
    def from_match(cls, match):
        """Create a :class:`StatusLine` from a :class:`re.match` object.

        This is intended for use within other parsers.  You probably
        want :meth:`StatusLine.from_bytes` instead.
        """
        version = HTTPVersion.from_match(match)

        if not match:
            raise InvalidStatusLine('Missing status line')

        raw_status_code = match.group('status_code')
        if not raw_status_code:
            raise InvalidStatusCode('Could not retrieve status code',
                                    match.string)

        status_code = int(match.group('status_code'))

        reason = match.group('reason')
        if not reason:
            reason = CODE_REASONS.get(status_code)

        return cls(version, status_code, reason)

    @classmethod
    def from_bytes(cls, line):
        r"""Create a :class:`StatusLine` from a byte string.  The trailing
        carriage return and newline are *not* matched.

        Raises :exc:`InvalidStatusCode` on missing/unparseable status
        codes and :exc:`InvalidStatusLine` on other errors.  Note that
        a missing reason is allowed!

        >>> StatusLine.from_bytes('HTTP/2.0 200 OK')
        ... # doctest: +NORMALIZE_WHITESPACE
        StatusLine(version=HTTPVersion(major=2, minor=0),
                   status_code=200, reason='OK')
        """
        match = cls.PARSE_STATUS_LINE.match(line)
        if not match:
            raise InvalidStatusLine('Could not parse status line', line)
        return cls.from_match(match)


class RequestLine(namedtuple('RequestLine', 'method url version'),
                  BytestringHelper):
    """
    Represents an HTTP Request-Line (RFC2616 5.1)
    """

    PARSE_REQUEST_LINE = re.compile(''.join([
        '(?P<method>', core.TOKEN.pattern, ')?',
        '(?:', core.START_LINE_SEP.pattern, ')?',
        '(?P<url>' + _ABS_RE + ')?',
        '(?:', core.START_LINE_SEP.pattern, ')?',
        '(?:', HTTPVersion.PARSE_VERSION.pattern, ')?']))

    def to_bytes(self):
        """Return a byte string representing this request line without the
        trailing carriage return and line feed:

        >>> RequestLine(method='GET',
        ...             url=URL(u'/'),
        ...             version=HTTPVersion(1, 1)).to_bytes()
        'GET / HTTP/1.1'
        """
        return b'%s %s %s' % self

    @classmethod
    def from_match(cls, match):
        """Create a :class:`RequestLine` from a :class:`re.match` object.

        This is intended for use within other parsers.  You probably
        want :meth:`RequestLine.from_bytes` instead. """
        if not match:
            raise InvalidRequestLine('Missing status line')

        method = match.group('method')
        if not method:
            raise InvalidMethod('Could not parse method', match.string)

        raw_url = match.group('url')
        if not raw_url:
            raise InvalidURI('Could not parse URI', match.string)

        url = URL(raw_url, strict=True)

        version = HTTPVersion.from_match(match)

        return cls(method, url, version)

    @classmethod
    def from_bytes(cls, line):
        r"""Create a :class:`RequestLine` from a byte string.  The trailing
        carriage return and new line are *not* matched.

        >>> RequestLine.from_bytes('GET /index.html?q=something HTTP/1.0')
        ... # doctest: +NORMALIZE_WHITESPACE
        RequestLine(method='GET', url=URL(u'/index.html?q=something'),
                    version=HTTPVersion(major=1, minor=0))

        If the method is missing, this raises :exc:`InvalidMethod` exception;

        If a URI is missing, it raises an :exc:`InvalidURI` exception;

        If the version is missing, it raises :exc:`InvalidVersion`;

        ...and on any other error this method raises an
        :exc:`InvalidRequestLine`.
        """
        match = cls.PARSE_REQUEST_LINE.match(line)
        if not match:
            raise InvalidRequestLine('Could not parse request line', line)
        return cls.from_match(match)


class _ProtocolElement(object):
    _fields = ('state',)
    state = M.Empty

    @property
    def complete(self):
        return self.state is M.Complete

    def __repr__(self):
        cn = self.__class__.__name__
        fields = self._fields
        fields_and_values = ['{0}={1!r}'.format(field, getattr(self, field))
                             for field in fields]
        return '<{0} {1}>'.format(cn, ', '.join(fields_and_values))


class Reader(_ProtocolElement):
    __metaclass__ = ABCMeta

    def __init__(self, *args, **kwargs):
        super(Reader, self).__init__(*args, **kwargs)

        self.bytes_read = 0

        self.reader = self._make_reader()
        self.state = next(self.reader)

    def send(self, message):
        # maybe just require reader.reader?
        return self.reader.send(message)

    @abstractmethod
    def _make_reader(self):
        """Called to create the parsing coroutine fed by :attribute:`send`"""
        pass


class Writer(_ProtocolElement):
    __metaclass__ = ABCMeta

    def __init__(self, *args, **kwargs):
        super(Writer, self).__init__(*args, **kwargs)

        self.bytes_written = 0

        self.writer = self._make_writer()
        self.state = M.Empty

    def __iter__(self):
        for result in self.writer:
            yield result

    def to_bytes(self):
        return b''.join(l for type, l in self._make_writer(once=False) if
                        type != M.Complete.type)

    @abstractmethod
    def _make_writer(self, once=True):
        """Called to create the iterator provided by :attribute:`next()`"""
        pass


class HeadersReader(Reader):
    ISCONTINUATION = re.compile('^[' + re.escape(''.join(set(core._LWS) -
                                                         set(core._CRLF)))
                                + ']')
    # TODO: may also want to track Trailer, Expect, Upgrade?
    _fields = Reader._fields + ('headers',)

    def __init__(self, headers=None, *args, **kwargs):
        super(HeadersReader, self).__init__(*args, **kwargs)
        if headers is None:
            headers = datastructures.Headers()
        self.headers = headers

    @classmethod
    def from_bytes(cls, bstr):
        instance = cls()
        for line in bstr.splitlines(True):
            instance.reader.send(M.HaveLine(line))
        if not instance.complete:
            raise InvalidHeaders('Missing header termination')
        return instance

    def _make_reader(self):
        prev_key = _MISSING
        while self.bytes_read < core.MAXHEADERBYTES and not self.complete:
            self.state = M.NeedLine
            t, line = yield self.state
            assert t == M.HaveLine.type

            if not line:
                raise InvalidHeaders('Cannot find header termination; '
                                     'connection closed')

            if core.LINE_END.match(line):
                break

            self.bytes_read += len(line)

            if self.ISCONTINUATION.match(line):
                if prev_key is _MISSING:
                    raise InvalidHeaders('Cannot begin with a continuation',
                                         line)
                last_value = self.headers.poplast(prev_key)
                key, value = prev_key, last_value + line.rstrip()
            else:
                key, _, value = line.partition(':')
                key, value = key.strip(), value.strip()
                if not core.TOKEN.match(key):
                    raise InvalidHeaders('Invalid field name', key)

                prev_key = key

            self.headers.add(key, value)
        else:
            raise InvalidHeaders('Consumed limit of {0} bytes '
                                 'without finding '
                                 ' headers'.format(core.MAXHEADERBYTES))
        # TODO trailers
        self.state = M.Complete
        while True:
            yield self.state


class HeadersWriter(Writer):

    def __init__(self, headers, *args, **kwargs):
        super(HeadersWriter, self).__init__(*args, **kwargs)
        self.headers = headers

    def _make_writer(self, once=True):
        for k, v in self.headers.iteritems(multi=True):
            line = b': '.join([bytes(k), bytes(v)]) + b'\r\n'

            state = M.HaveLine(line)
            if once:
                self.state = state
                self.bytes_written += len(line)
            yield state

        state = M.HaveLine(b'\r\n')
        if once:
            self.state = state
            self.bytes_written += 2
        yield state

        if once:
            self.state = M.Complete


class IdentityEncodedBodyReader(Reader):
    DEFAULT_AMOUNT = 1024

    def __init__(self, body, content_length=None, *args, **kwargs):
        self.body = body
        self.content_length = content_length
        self.bytes_remaining = None

        super(IdentityEncodedBodyReader, self).__init__(*args, **kwargs)

    def _make_reader(self):
        self.bytes_remaining = (self.DEFAULT_AMOUNT
                                if self.content_length is None
                                else self.content_length)

        while not self.complete:
            t, read = yield M.NeedData(amount=self.bytes_remaining)
            assert t == M.HaveData.type

            amount = len(read)

            if not amount:
                if self.content_length is None or self.bytes_remaining <= 0:
                    self.state = M.Complete
                    continue
                raise IncompleteBody('Could not read remaining {0} '
                                     'bytes'.format(self.bytes_remaining))

            self.bytes_read += amount

            self.body.data_received(read)

            if self.content_length is not None:
                self.bytes_remaining = (self.content_length - self.bytes_read)

            if self.bytes_remaining <= 0:
                self.body.complete(self.bytes_read)
                self.state = M.Complete

        while True:
            yield M.Complete


class IdentityEncodeBodyWriter(Writer):

    def __init__(self, body, content_length=None, *args, **kwargs):
        super(IdentityEncodeBodyWriter, self).__init__(*args, **kwargs)
        self.body = body
        self.content_length = content_length
        self.bytes_remaining = None

    def _make_writer(self):
        for data in self.body.send_data():
            self.bytes_written += len(data)
            self.state = M.HaveData(data)
            yield self.state

        if self.content_length is None:
            self.state = M.WantDisconnect
            yield self.state

        self.body.complete(self.bytes_written)

        self.state = M.Complete


class ChunkEncodedBodyReader(Reader):
    IS_HEX = re.compile('([\dA-Ha-h]+)[\t ]*' + core.LINE_END.pattern)

    def __init__(self, body, *args, **kwargs):
        self.body = body
        super(ChunkEncodedBodyReader, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.chunk_length = None
        self.chunk_read = 0
        self.chunk_partials = []

    def _make_reader(self):
        IS_HEX = self.IS_HEX

        while not self.complete:
            self.state = M.NeedLine
            t, chunk_header = yield self.state
            assert t == M.HaveLine.type

            if not chunk_header:
                raise InvalidChunk('Could not read chunk header: Disconnected')
            if not IS_HEX.match(chunk_header):
                raise InvalidChunk('Could not read chunk header', chunk_header)

            # trailing CLRF?
            self.chunk_length = int(chunk_header, 16)

            if self.chunk_length > core.MAXLINE:
                raise InvalidChunk('Requested too large a chunk',
                                   self.chunk_length)

            last = ''
            while self.chunk_read < self.chunk_length:
                self.state = M.NeedData(amount=self.chunk_length
                                        - self.chunk_read)
                t, last = yield self.state
                assert t == M.HaveData.type

                if not last:
                    raise core.EndOfStream

                self.chunk_read += len(last)
                self.bytes_read += len(last)
                self.chunk_partials.append(last)

            chunk = ''.join(self.chunk_partials)

            self.state = M.NeedPeek(amount=2)
            t, peek = yield self.state
            assert t == M.HavePeek.type

            cr, lf = peek[:2]

            if cr == '\r' and lf == '\n':
                discard = 2
            elif cr == '\n':
                # lf is not actually lf, but real data
                discard == 1
            else:
                raise InvalidChunk('No trailing CRLF|LF', chunk)

            self.state = M.NeedData(amount=discard)
            t, data = yield self.state
            assert t == M.HaveData.type

            if not self.chunk_length and not chunk:
                self.body.complete(self.bytes_read)
                self.state = M.Complete
            else:
                self.reset()
                self.body.chunk_received(chunk)

        while True:
            self.body.complete(self.bytes_read)
            yield M.Complete


class ChunkEncodedBodyWriter(Writer):

    def __init__(self, body, *args, **kwargs):
        self.body = body
        super(ChunkEncodedBodyWriter, self).__init__(*args, **kwargs)

    def _make_writer(self):
        for chunk in self.body.send_chunk():
            header = '%x\r\n' % len(chunk)

            for state in (M.HaveLine(header),
                          M.HaveData(chunk),
                          M.HaveLine('\r\n')):
                self.state = state
                yield self.state

        # maybe we got an empty chunk; if so, don't send an additional
        # end chunk
        if chunk:
            for state in (M.HaveLine('0\r\n'),
                          M.HaveLine('\r\n')):
                self.state = state
                yield self.state

        self.state = M.Complete


class RequestWriter(Writer):

    def __init__(self, request_line, headers, body=None, *args, **kwargs):
        self.request_line = request_line
        self.headers = headers
        self.body = body
        super(RequestWriter, self).__init__(*args, **kwargs)

    def _make_writer(self):
        rl = bytes(self.request_line) + '\r\n'
        self.bytes_written += len(rl)
        self.state = M.HaveLine(rl)
        yield self.state

        for m in iter(self.headers):
            self.bytes_written += self.headers.bytes_written
            self.state = m
            yield m

        if not self.body:
            self.state = M.Complete
            return

        for m in iter(self.body):
            self.bytes_written += self.body.bytes_written
            self.state = m
            yield m

        self.state = M.Complete


class ResponseReader(Reader):

    def __init__(self, *args, **kwargs):
        self.status_line = None

        self.headers = None
        self.headers_reader = HeadersReader()

        self.body_reader = None
        self.body = None

        self.content_length = None
        self.chunked = False

        super(ResponseReader, self).__init__(*args, **kwargs)

    def _parse_headers(self):
        # TODO: case-insensitive OMD!
        lowercased = dict((k.lower(), v)
                          for k, v in dict(self.headers).items())

        content_length = lowercased.get('content-length')
        encodings = lowercased.get('transfer-encoding', [])

        if content_length:
            self.content_length = int(content_length[-1])

        self.chunked = any('chunked' in v.lower() for v in encodings)
        # TODO mutual exclusion

    def _make_reader(self):
        LINE_END = core.LINE_END
        self.state = M.NeedLine

        # 4.1: In the interest of robustness, servers SHOULD
        # ignore any empty line(s) received where a
        # Request-Line is expected. In other words, if the
        # server is reading the protocol stream at the
        # beginning of a message and receives a CRLF first, it
        # should ignore the CRLF.
        #
        # Assume the same for status lines
        line = '\r\n'
        while LINE_END.match(line):
            t, line = yield self.state
            assert t == M.HaveLine.type

        match = StatusLine.PARSE_STATUS_LINE.match(line)
        self.status_line = StatusLine.from_match(match)
        if not core.LINE_END.match(line[match.end():]):
            raise InvalidStatusLine('Status line did not end with [CR]LF')

        self.state = self.headers_reader.state
        while True:
            state = self.headers_reader.send((yield self.state))
            if self.headers_reader.complete:
                self.headers = self.headers_reader.headers
                break
            self.state = state

        self._parse_headers()

        if not self.chunked:
            self.body = datastructures.Body()
            content_length = self.content_length
            b_reader = IdentityEncodedBodyReader(self.body,
                                                 content_length=content_length)
            self.body_reader = b_reader
        else:
            self.body = datastructures.ChunkedBody()
            self.body_reader = ChunkEncodedBodyReader(self.body)

        self.state = self.body_reader.state
        while not self.complete:
            self.state = self.body_reader.send((yield self.state))

        while True:
            yield M.Complete
