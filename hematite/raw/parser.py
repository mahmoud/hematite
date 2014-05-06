import re
from collections import namedtuple

from hematite.compat import (BytestringHelper,
                             make_sentinel)

from hematite.raw import core
from hematite.url import URL, _ABS_RE
from hematite.constants import CODE_REASONS, HEADER_CASE_MAP
from hematite.raw import messages as m

# TODO: maintain case

_MISSING = make_sentinel()


class HTTPParseException(core.HTTPException):
    pass


class InvalidStatusLine(HTTPParseException):
    pass


class InvalidVersion(InvalidStatusLine):
    pass


class InvalidStatusCode(InvalidStatusLine):
    pass


class InvalidRequestLine(HTTPParseException):
    pass


class InvalidMethod(InvalidRequestLine):
    pass


class InvalidURL(InvalidRequestLine):
    pass


class InvalidHeaders(HTTPParseException):
    pass


class ParseError(core.HTTPException):
    pass


class BodyReadException(core.HTTPException):
    pass


class InvalidChunk(BodyReadException):
    pass


class Protocol(object):

    def __init__(self, *args, **kwargs):
        super(Protocol, self).__init__(*args, **kwargs)
        self.bytes_read = 0
        self.bytes_written = 0
        self.token = m.Empty
        self.error = None

    def _next_state(self, message):
        raise ParseError('Unknown token {0}'.format(self.token))

    _feed_start = _emit_start = _next_state

    def _line_received(self, message):
        raise NotImplementedError

    def _send_line(self, message):
        raise NotImplementedError

    def _data_received(self, message):
        raise NotImplementedError

    def _send_data(self, message):
        raise NotImplementedError

    def _peek_received(self, message):
        raise NotImplementedError

    @property
    def completed(self):
        return self.token is m.Complete

    def feed(self, message):
        if self.token is m.Empty:
            self._next_state = self._feed_start
        elif self.token is m.Complete:
            return self.token
        return self._next_state(message)

    def emit(self, message):
        if self.token is m.Empty:
            self._next_state = self._emit_start
        elif self.token is m.Complete:
            return self.token

        return self._next_state(message)


class HTTPVersion(namedtuple('HTTPVersion', 'major minor'), BytestringHelper):
    PARSE_VERSION = re.compile('HTTP/'
                               '(?P<http_major_version>\d+)'
                               '\.'
                               '(?P<http_minor_version>\d+)')

    def to_bytes(self):
        return b'HTTP/' + b'.'.join(map(bytes, self))

    @classmethod
    def from_match(cls, m):
        major = m.group('http_major_version')
        minor = m.group('http_minor_version')

        if not (major or minor):
            raise InvalidVersion('Unparseable version', m.string)

        return cls(int(major), int(minor))


class StatusLine(namedtuple('StatusLine', 'version status_code reason'),
                 BytestringHelper):
    # section 6.1
    PARSE_LINE = re.compile(
        '(?:' + HTTPVersion.PARSE_VERSION.pattern + ')?'
        + core.START_LINE_SEP.pattern +
        '(?P<status_code>\d{3})?' +
        '(:?' + core.START_LINE_SEP.pattern +
        # 6.1: No CR or LF is allowed except in the final CRLF
        # sequence.
        '(?P<reason>[^' + re.escape(core._TEXT_EXCLUDE) + '\r\n]*?))?'
        + core._LINE_END)

    def to_bytes(self):
        version, status_code, reason = self
        if reason is None:
            reason = CODE_REASONS.get(status_code)
        bs = [version, status_code]
        if reason:
            bs.append(reason)
        return b' '.join(map(bytes, bs)) + b'\r\n'

    @classmethod
    def from_bytes(cls, line):
        match = cls.PARSE_LINE.match(line)
        if not match:
            raise InvalidStatusLine('Could not parse status line', line)

        version = HTTPVersion.from_match(match)

        raw_status_code = match.group('status_code')
        if not raw_status_code:
            raise InvalidStatusCode('Could not retrieve status code', line)

        status_code = int(match.group('status_code'))

        reason = match.group('reason')
        if not reason:
            reason = CODE_REASONS.get(status_code)

        c = cls(version, status_code, reason)
        return c


class RequestLine(namedtuple('RequestLine', 'method url version'),
                  BytestringHelper):
    PARSE_LINE = re.compile(
        '(?P<method>' + core.TOKEN.pattern + ')?'
        + core.START_LINE_SEP.pattern +
        '(?P<url>' + _ABS_RE + ')?'
        + core.START_LINE_SEP.pattern +
        '(?:' + HTTPVersion.PARSE_VERSION.pattern + ')?'
        + core._LINE_END)

    def to_bytes(self):
        return b' '.join(map(bytes, self)) + b'\r\n'

    @classmethod
    def from_bytes(cls, line):
        match = cls.PARSE_LINE.match(line)
        if not match:
            raise InvalidRequestLine('Could not parse request line', line)

        method = match.group('method')
        if not method:
            raise InvalidMethod('Could not parse method', line)

        raw_url = match.group('url')
        if not raw_url:
            raise InvalidURL('Could not parse url', line)

        url = URL(raw_url, strict=True)

        version = HTTPVersion.from_match(match)

        return cls(method, url, version)


class HeadersProtocol(Protocol):
    ISCONTINUATION = re.compile('^['
                                + re.escape(''.join(set(core._LWS) -
                                                    set(core._CRLF)))
                                + ']')

    def __init__(self, headers, *args, **kwargs):
        super(HeadersProtocol, self).__init__(*args, **kwargs)
        self._prev_key = _MISSING
        self.headers = headers

    def _line_received(self, message):
        t, line = message
        assert t == m.HaveLine.type

        if not line:
            self.error = InvalidHeaders('Cannot find header termination; '
                                        'connection closed')
            raise self.error

        if core.LINE_END.match(line):
            self.expected_token = m.Complete
            return self.expected_token

        new_bytes_read = self.bytes_read + len(line)
        if new_bytes_read > core.MAXHEADERBYTES:
            self.error = InvalidHeaders('Consumed limit of {0} bytes '
                                        'without finding '
                                        ' headers'.format(core.MAXHEADERBYTES))
            raise self.error

        self.bytes_read = new_bytes_read

        if self.ISCONTINUATION.match(line):
            if self._prev_key is _MISSING:
                raise InvalidHeaders('Cannot begin with a continuation',
                                     line)
            last_value = self.headers.poplast(self._prev_key)
            key, value = self._prev_key, last_value + line.rstrip()
        else:
            key, colon, value = line.partition(':')

            if not colon:
                raise InvalidHeaders('Invalid header line', line)

            key, value = key.strip(), value.strip()
            if not core.TOKEN.match(key):
                raise InvalidHeaders('Invalid field name', key)

            self._prev_key = key

        self.headers.add(key, value)

        self.expected_token = m.NeedLine
        return self.expected_token

    def _send_line(self, message):
        t, _ = message
        assert t == m.NeedLine.type

        if self.token is m.Empty:
            self._write_cursor = self.headers.iteritems(multi=True)

        k, v = next(self._write_cursor, (_MISSING, None))
        if k is _MISSING:
            self.token = m.Complete
            return m.HaveLine(b'\r\n')

        self.token = m.HaveLine(b': '.join([bytes(k), bytes(v)]) + b'\r\n')
        return self.token

    _feed_start = _line_received
    _emit_start = _send_line


class IdentityEncodedBodyProtocol(Protocol):
    DEFAULT_AMOUNT = 1024

    def __init__(self, iterable=None, content_length=None):
        super(IdentityEncodedBodyProtocol, self).__init__()
        if isinstance(iterable, bytes):
            iterable = iter([iterable])

        self.iterable = iterable
        self.content_length = content_length

    def _data_received(self, message):
        t, data = message
        assert t == m.HaveData

        if not data:
            if self.content_length is not None:
                raise core.EndOfStream('Connection closed with only {0} '
                                       'of expected {1} bytes '
                                       'read'.format(self.bytes_read,
                                                     self.content_length))
            self.token = m.Complete
            return self.token

        self.bytes_read += len(data)
        self.token = m.NeedData(self.content_length
                                if self.content_length is not None else
                                self.DEFAULT_AMOUNT)
        return m.HaveData(data)

    def _send_data(self, message):
        t, _ = message
        assert t == m.NeedData.type

        data = next(self.iterable, _MISSING)
        if data is _MISSING:
            if self.content_length is not None:
                raise core.EndOfStream('Only wrote {0} bytes of expected '
                                       '{1}'.format(self.bytes_written,
                                                    self.content_length))
            self.token = m.Complete
            return self.token

        self.bytes_written += len(data)
        return m.HaveData(data)

    _feed_start = _data_received
    _emit_start = _send_data


class ChunkEncodedBodyProtocol(Protocol):
    IS_HEX = re.compile('([\dA-Ha-h]+)')

    def __init__(self, iterable=None):
        super(ChunkEncodedBodyProtocol, self).__init__()
        if isinstance(iterable, bytes):
            iterable = iter([iterable])
        self.iterable = iterable
        self.reset()

    def reset(self):
        self.chunk_length = 0
        self.partials = []

    def _line_received(self, message):
        t, chunk_header = message
        assert t == m.HaveLine.type

        if not chunk_header:
            raise InvalidChunk('Could not read chunk header: Disconnected')

        if not self.IS_HEX.match(chunk_header):
            raise InvalidChunk('Could not read chunk header', chunk_header)

        # trailing CLRF?
        self.chunk_length = int(chunk_header, 16)

        if self.chunk_length > core.MAXLINE:
            raise InvalidChunk('Requested too large a chunk',
                               self.chunk_length)
        elif self.chunk_length == 0:
            self.token = m.Complete
            return self.token

        self.token = m.NeedData(self.chunk_length)
        self._next_state = self._data_received

        return self.token

    def _data_received(self, message):
        t, chunk_or_partial = message
        assert t == m.HaveData.type

        if not chunk_or_partial:
            raise core.EndOfStream('Incomplete chunk: Disconnected')

        self.bytes_read += len(chunk_or_partial)
        self.partials.append(chunk_or_partial)

        if self.bytes_read < self.chunk_length:
            self.token = m.NeedData(self.chunk_length - self.bytes_read)
            self._next_state = self._peek_received
            return self.token

        self.token = m.NeedPeek(amount=2)
        self._next_state = self._peek_received

        return self.token

    def _peek_received(self, message):
        t, peeked = message
        assert t == m.HavePeek.type

        cr, lf = peeked[:2]

        if cr == '\r' and lf == '\n':
            discard = 2
        elif cr == '\n':
            # lf is not actually lf, but real data
            discard == 1
        else:
            raise InvalidChunk('No trailing CRLF|LF', ''.join(self.partials))

        self.token = m.NeedData(discard)
        self._next_state = self._complete_chunk

        return self.token

    # a hack
    def _complete_chunk(self, message):
        t, data = message
        assert t == m.HaveData.type

        chunk = ''.join(self.partials)
        self.reset()

        self.token = m.NeedLine
        self._next_state = self._line_received

        return m.HaveData(chunk)

    def _send_line(self, message):
        t, _ = message
        assert t == m.NeedLine.type

        chunk = next(self.iterable, '')
        chunk_length = len(chunk)

        self.token = m.HaveData(chunk + '\r\n')
        self._next_state = self._send_data

        return m.HaveLine(hex(chunk_length)[2:] + '\r\n')

    def _send_data(self, message):
        t, _ = message
        assert t == m.NeedData.type

        token = self.token

        if token[1] == '\r\n':
            self.token = m.Complete
        else:
            self.token = m.NeedLine
            self._next_state = self._send_line

        return token

    _feed_start = _line_received
    _emit_start = _send_line
