
import re
from collections import namedtuple

from hematite.compat import BytestringHelper
from hematite.compat import OrderedMultiDict as OMD

from hematite.raw import core
from hematite.url import URL, _ABS_RE
from hematite.constants import CODE_REASONS

# TODO: maintain case


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


def _start_line(io_obj):
    # TODO: make sure that an external timer watches this
    while True:
        line = io_obj.readline(core.MAXLINE)
        if line.strip():
            return line


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
    def from_io(cls, io_obj):
        line = _start_line(io_obj)
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

    def to_io(self, io_obj):
        return io_obj.write(self.to_bytes())

    @classmethod
    def from_io(cls, io_obj):
        line = _start_line(io_obj)

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
        print repr(url)

        version = HTTPVersion.from_match(m)

        return cls(method, url, version)


class Headers(BytestringHelper, OMD):
    ISCONTINUATION = re.compile('^[' + re.escape(''.join(set(core._LWS) -
                                                         set(core._CRLF)))
                                + ']')

    def to_bytes(self):
        items = self.items(multi=True)
        lines = [b': '.join([bytes(k), bytes(v)]) for k, v in items]
        lines.append(b'')  # trailing CRLF is required
        return b'\r\n'.join(lines)

    def to_io(self, io_obj):
        io_obj.write(self.to_bytes())

    @classmethod
    def from_io(cls, io_obj):
        lines = []
        bytes_read = 0
        while bytes_read < core.MAXHEADERBYTES:
            line = io_obj.readline(core.MAXLINE)
            if not line:
                raise InvalidHeaders('Cannot find header termination; '
                                     'connection closed')
            if core.LINE_END.match(line):
                break
            bytes_read += len(line)
            lines.append(line)
        else:
            raise InvalidHeaders('Consumed limit of {0} bytes '
                                 'without finding '
                                 ' headers'.format(core.MAXHEADERBYTES))

        if cls.ISCONTINUATION.match(lines[0]):
            raise InvalidHeaders('Cannot begin with a continuation',
                                 lines[0])

        parsed = []
        for idx in xrange(len(lines)):
            line = lines[idx]
            if cls.ISCONTINUATION.match(line):
                pidx = idx - 1
                lines[pidx] = lines[pidx] + line
                continue

            k, _, v = line.partition(':')
            k, v = k.strip(), v.strip()
            if not core.TOKEN.match(k):
                raise InvalidHeaders('Invalid field name', k)

            parsed.append((k, v))

        return cls(parsed)
