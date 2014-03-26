import re
from collections import namedtuple

from hematite.compat import (BytestringHelper,
                             OrderedMultiDict as OMD,
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
            cls.invalid(m.string)

        return cls(int(major), int(minor))

    @staticmethod
    def invalid(bstr):
        raise InvalidVersion('Unparseable version', bstr)


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

    def to_io(self, io_obj):
        return io_obj.write(self.to_bytes())

    @classmethod
    def from_io(cls, io_obj):
        line = start_line(io_obj)
        if not line.strip():
            return
        m = cls.PARSE_LINE.match(line)
        if not m:
            raise InvalidStatusLine('Could not parse status line', line)

        version = HTTPVersion.from_match(m)

        raw_status_code = m.group('status_code')
        if not raw_status_code:
            raise InvalidStatusCode('Could not retrieve status code', line)

        status_code = int(m.group('status_code'))

        reason = m.group('reason')
        if not reason:
            reason = CODE_REASONS.get(status_code)

        c = cls(version, status_code, reason)
        return c

    def to_io(self, io_obj):
        return io_obj.write(self.to_bytes())


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
        return b' '.join(map(bytes, self))

    def iterlines(self):
        yield bytes(self)

    @classmethod
    def readline(cls, line):
        if not line.strip():
            return
        m = cls.PARSE_LINE.match(line)
        if not m:
            raise InvalidRequestLine('Could not parse request line', line)

        method = m.group('method')
        if not method:
            raise InvalidMethod('Could not parse method', line)

        raw_url = m.group('url')
        if not raw_url:
            raise InvalidURL('Could not parse url', line)

        url = URL(raw_url, strict=True)

        version = HTTPVersion.from_match(m)

        return cls(method, url, version)


class Headers(BytestringHelper, OMD):
    ISCONTINUATION = re.compile('^[' + re.escape(''.join(set(core._LWS) -
                                                         set(core._CRLF)))
                                + ']')
    _tracked_keys = frozenset(['Connection',
                               'Content-Encoding',
                               'Content-Length',
                               'Transfer-Encoding'])
    # TODO: may also want to track Trailer, Expect, Upgrade?

    def __init__(self, *args, **kwargs):
        super(Headers, self).__init__(*args, **kwargs)
        self.bytes_read = 0
        # TODO: these could come from kwargs
        self.is_conn_close = None
        self.is_conn_keep_alive = None
        self.is_chunked = None
        self.content_length = None
        self.content_encodings = []  # TODO
        self._writer = self._make_writer()
        self._reader = self._make_reader()
        self.state = next(self._reader)

    @property
    def complete(self):
        return self.state is m.Complete

    def to_bytes(self):
        return b''.join(self._make_writer())

    def to_io(self, io_obj):
        # todo, repeatable?
        for line in self._writer:
            io_obj.write(line)

    def _make_writer(self):
        for k, v in self.iteritems(multi=True):
            yield b': '.join([bytes(k), bytes(v)]) + b'\r\n'
        yield b'\r\n'

    def from_io(self, io_obj):
        while self.state.type != m.Complete.type:
            if self.state.type == m.NeedLine.type:
                line = core.readline(io_obj)
                next_state = m.HaveLine(value=line)
            elif self.state.type == m.Complete.type:
                pass
            else:
                assert "Unknown state", self.state
            self.state = self._reader.send(next_state)

        return self.complete

    def _make_reader(self):
        prev_key = _MISSING
        while self.bytes_read < core.MAXHEADERBYTES and not self.complete:
            t, line = yield m.NeedLine
            assert t == m.HaveLine.type

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

                ckey = HEADER_CASE_MAP[key]  # canonical key
                if ckey in self._tracked_keys:
                    self._update_http_attribute(ckey, value)
                prev_key = key

            self.add(key, value)
        else:
            raise InvalidHeaders('Consumed limit of {0} bytes '
                                 'without finding '
                                 ' headers'.format(core.MAXHEADERBYTES))
        # TODO trailers
        while True:
            yield m.Complete

    def iterlines(self):
        for k, v in self.iteritems(multi=True):
            yield b': '.join([bytes(k), bytes(v)]) + b'\r\n'
        yield b'\r\n'

    def _update_attribute(self, ckey, value):
        """
        Called once an interesting header is parsed to update certain
        attributes relevant to further processing of the
        Request/Response.

        NOTE: expects canonical key (see _readline for usage)
        """
        if ckey == 'Connection':
            for v in value.split(','):
                v = v.strip().lower()
                if v == 'close':
                    self.is_conn_close = True
                elif v == 'keep-alive':
                    self.is_conn_keep_alive = True
        elif ckey == 'Transfer-Encoding':
            for v in value.split(','):
                v = v.strip().lower()
                if v == 'chunked':
                    self.is_chunked = True
        elif ckey == 'Content-Length':
            try:
                self.content_length = int(value)
            except:
                self.content_length = None
        elif ckey == 'Content-Encoding':
            pass  # TODO
        return

    def _update_all_attributes(self):
        """
        Called to sync attribute values with Headers dict
        contents. Not used atm, but would ostensibly be useful if
        headers are constructed manually from values passed into
        __init__
        """
        for key, value in self.iteritems(multi=True):
            ckey = HEADER_CASE_MAP[key]  # canonical key
            if ckey in self._tracked_keys:
                self._update_http_attribute(ckey, value)


