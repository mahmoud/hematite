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


class StatefulParse(object):

    def __init__(self, *args, **kwargs):
        super(StatefulParse, self).__init__(*args, **kwargs)
        self.state = m.Empty
        self.reader = self._make_reader()
        self.state = next(self.reader)

    @property
    def complete(self):
        return self.state is m.Complete


class Headers(StatefulParse, BytestringHelper, OMD):
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
            instance.reader.send(m.HaveLine(line))
        if not instance.complete:
            raise InvalidHeaders('Missing header termination')
        return instance

    def _make_writer(self):
        for k, v in self.iteritems(multi=True):
            yield m.HaveLine(b': '.join([bytes(k), bytes(v)]) + b'\r\n')
        yield m.HaveLine(b'\r\n')

    def _make_reader(self):
        prev_key = _MISSING
        while self.bytes_read < core.MAXHEADERBYTES and not self.complete:
            self.state = m.NeedLine
            t, line = yield self.state
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

                prev_key = key

            self.add(key, value)
        else:
            raise InvalidHeaders('Consumed limit of {0} bytes '
                                 'without finding '
                                 ' headers'.format(core.MAXHEADERBYTES))
        # TODO trailers
        self.state = m.Complete
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
            self.state = m.Complete

    def to_bytes(self):
        return self.request_line.to_bytes() + self.headers.to_bytes()

    @classmethod
    def from_bytes(cls, bstr):
        instance = cls()
        for line in bstr.splitlines(True):
            instance.reader.send(m.HaveLine(line))
        return instance

    def _make_writer(self):
        yield m.HaveLine(bytes(self.request_line) + '\r\n')
        for next_state in self.headers._make_writer():
            yield next_state

    def _make_reader(self):
        line = ''
        while not line.strip():
            t, line = yield m.NeedLine
            assert t == m.HaveLine.type
        self.request_line = RequestLine.from_bytes(line)

        self.state = self.headers.state
        while not self.headers.complete:
            next_state = yield self.state
            self.state = self.headers.reader.send(next_state)

        self.state = m.Complete
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
            self.state = m.Complete

    def to_bytes(self):
        return self.status_line.to_bytes() + self.headers.to_bytes()

    @classmethod
    def from_bytes(cls, bstr):
        instance = cls()
        for line in bstr.splitlines(True):
            instance.reader.send(m.HaveLine(line))
        return instance

    def _make_writer(self):
        yield m.HaveLine(bytes(self.status_line) + '\r\n')
        for next_state in self.headers._make_writer():
            yield next_state

    def _make_reader(self):
        line = ''
        while not line.strip():
            t, line = yield m.NeedLine
            assert t == m.HaveLine.type
        self.status_line = StatusLine.from_bytes(line)

        self.state = self.headers.state
        while not self.headers.complete:
            next_state = yield self.state
            self.state = self.headers.reader.send(next_state)

        self.state = m.Complete
        while True:
            yield self.state

    def __repr__(self):
        cn = self.__class__.__name__
        return '<{0}: {1!s} {2!r}>'.format(cn, self.status_line, self.headers)
