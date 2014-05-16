import re
from collections import namedtuple

from hematite.compat import (BytestringHelper,
                             OrderedMultiDict as OMD,
                             make_sentinel)

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
        return b'HTTP/' + b'.'.join(map(bytes, self))

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
            InvalidVersion('Unparseable version', match.string)
            cls.invalid(match.string)

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

    PARSE_STATUS_LINE = re.compile(
        '(?:' + HTTPVersion.PARSE_VERSION.pattern + ')?'
        + core.START_LINE_SEP.pattern +
        '(?P<status_code>\d{3})?' +
        '(?:' + core.START_LINE_SEP.pattern +
        # 6.1: No CR or LF is allowed except in the final CRLF
        # sequence.
        '(?P<reason>[^' + re.escape(core._TEXT_EXCLUDE) + '\r\n]+?))?'
        + core.LINE_END.pattern)

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
        bs = [version, status_code]
        if reason:
            bs.append(reason)
        return b' '.join(map(bytes, bs)) + b'\r\n'

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
        r"""Create a :class:`StatusLine` from a byte string. Raises
        :exc:`InvalidStatusCode` on missing/unparseable status codes
        and :exc:`InvalidStatusLine` on other errors.  Note that a
        missing reason is allowed!

        >>> StatusLine.from_bytes('HTTP/2.0 200 OK\r\n')
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

    PARSE_REQUEST_LINE = re.compile(
        '(?P<method>' + core.TOKEN.pattern + ')?'
        + core.START_LINE_SEP.pattern +
        '(?P<url>' + _ABS_RE + ')?'
        + core.START_LINE_SEP.pattern +
        '(?:' + HTTPVersion.PARSE_VERSION.pattern + ')?')

    def to_bytes(self):
        """Return a byte string representing this request line without the
        trailing carriage return and line feed:

        >>> RequestLine(method='GET',
        ...             url=URL(u'/'),
        ...             version=HTTPVersion(1, 1)).to_bytes()
        'GET / HTTP/1.1'
        """
        return b' '.join(map(bytes, self))

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
        carriage return and new line are *not* considered.

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


class StatefulParse(object):

    def __init__(self, *args, **kwargs):
        super(StatefulParse, self).__init__(*args, **kwargs)
        self.state = M.Empty
        self.reader = self._make_reader()
        self.state = next(self.reader)

    @property
    def complete(self):
        return self.state is M.Complete


class Headers(BytestringHelper):
    ISCONTINUATION = re.compile('^[' + re.escape(''.join(set(core._LWS) -
                                                         set(core._CRLF)))
                                + ']')
    # TODO: may also want to track Trailer, Expect, Upgrade?

    def __init__(self, *args, **kwargs):
        self.bytes_read = 0
        super(Headers, self).__init__(*args, **kwargs)

    def to_bytes(self):
        return b''.join(l for _, l in self._make_writer())

    @classmethod
    def from_bytes(cls, bstr):
        instance = cls()
        for line in bstr.splitlines(True):
            instance.reader.send(M.HaveLine(line))
        if not instance.complete:
            raise InvalidHeaders('Missing header termination')
        return instance

    def _make_writer(self):
        for k, v in self.iteritems(multi=True):
            yield M.HaveLine(b': '.join([bytes(k), bytes(v)]) + b'\r\n')
        yield M.HaveLine(b'\r\n')

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
                last_value = self.poplast(prev_key)
                key, value = prev_key, last_value + line.rstrip()
            else:
                key, _, value = line.partition(':')
                key, value = key.strip(), value.strip()
                if not core.TOKEN.match(key):
                    raise InvalidHeaders('Invalid field name', key)

                prev_key = key

            self.add(key, value)
        else:
            raise InvalidHeaders('Consumed limit of {0} bytes '
                                 'without finding '
                                 ' headers'.format(core.MAXHEADERBYTES))
        # TODO trailers
        self.state = M.Complete
        while True:
            yield self.state


class RequestEnvelope(StatefulParse, BytestringHelper):

    def __init__(self, request_line=None, headers=None):
        super(RequestEnvelope, self).__init__()
        self.request_line = request_line
        self.headers = headers or Headers()
        self.reader = self._make_reader()
        self.state = next(self.reader)
        if request_line and headers:
            self.state = M.Complete

    def to_bytes(self):
        return self.request_line.to_bytes() + self.headers.to_bytes()

    @classmethod
    def from_bytes(cls, bstr):
        instance = cls()
        for line in bstr.splitlines(True):
            instance.reader.send(M.HaveLine(line))
        return instance

    def _make_writer(self):
        yield M.HaveLine(bytes(self.request_line))
        for next_state in self.headers._make_writer():
            yield next_state

    def _make_reader(self):
        line = ''
        while not line.strip():
            t, line = yield M.NeedLine
            assert t == M.HaveLine.type
        self.request_line = RequestLine.from_bytes(line)

        self.state = self.headers.state
        while not self.headers.complete:
            next_state = yield self.state
            self.state = self.headers.reader.send(next_state)

        self.state = M.Complete
        while True:
            yield self.state


class ResponseEnvelope(StatefulParse, BytestringHelper):

    def __init__(self, status_line=None, headers=None):
        super(ResponseEnvelope, self).__init__()
        self.status_line = status_line
        self.headers = headers or Headers()
        self.reader = self._make_reader()
        self.state = next(self.reader)
        if headers and status_line:
            self.state = M.Complete

    def to_bytes(self):
        return self.status_line.to_bytes() + self.headers.to_bytes()

    @classmethod
    def from_bytes(cls, bstr):
        instance = cls()
        for line in bstr.splitlines(True):
            instance.reader.send(M.HaveLine(line))
        return instance

    def _make_writer(self):
        yield M.HaveLine(bytes(self.status_line))
        for next_state in self.headers._make_writer():
            yield next_state

    def _make_reader(self):
        line = ''
        while not line.strip():
            t, line = yield M.NeedLine
            assert t == M.HaveLine.type
        self.status_line = StatusLine.from_bytes(line)

        self.state = self.headers.state
        while not self.headers.complete:
            next_state = yield self.state
            self.state = self.headers.reader.send(next_state)

        self.state = M.Complete
        while True:
            yield self.state

    def __repr__(self):
        cn = self.__class__.__name__
        return '<{0}: {1!s} {2!r}>'.format(cn, self.status_line, self.headers)
