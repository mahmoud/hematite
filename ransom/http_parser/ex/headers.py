# TODO: byte strings have no .format in python3.3
from collections import namedtuple
from ransom.compat import BytestringHelper
from ransom.compat import OrderedMultiDict as OMD
import ransom.http_parser.ex.core as core
from ransom.url import URL, _ABS_RE
import re


class HTTPParseException(Exception):
    pass


class InvalidStatusLine(HTTPParseException):
    pass


class InvalidVersion(InvalidStatusLine):
    pass


class InvalidStatusCode(InvalidStatusLine):
    pass


class InvalidRequestLine(HTTPParseException):
    pass


class InvalidHeaders(HTTPParseException):
    pass


class HTTPVersion(namedtuple('HTTPVersion', 'major minor'), BytestringHelper):
    advance = core.advancer('HTTP/(\d+)\.(\d+)')

    @classmethod
    def from_bytes(cls, bstr):
        bstr, m = cls.advance(bstr)
        if not m:
            raise InvalidVersion('Unparseable version: '
                                 '{0!r}'.format(core._cut(bstr)))

        major, minor = m.groups()
        try:
            major, minor = int(major), int(minor)
        except ValueError:
            raise InvalidVersion('Major or minor version is not a digit: '
                                 '{0!r} {1!r}'.format(major, minor))

        return bstr, cls(major, minor)

    def to_bytes(self):
        return b'HTTP/' + b'.'.join(map(bytes, self))


class StatusCode(namedtuple('StatusCode', 'code reason'), BytestringHelper):
    advance = core.advancer('\d{3}')
    CODE_REASONS = OMD({100: 'Continue',
                        101: 'Switching Protocols',
                        200: 'OK',
                        201: 'Created',
                        202: 'Accepted',
                        203: 'Non-Authoritative Information',
                        204: 'No Content',
                        205: 'Reset Content',
                        206: 'Partial Content',
                        300: 'Multiple Choices',
                        301: 'Moved Permanently',
                        302: 'Found',
                        303: 'See Other',
                        304: 'Not Modified',
                        305: 'Use Proxy',
                        307: 'Temporary Redirect',
                        400: 'Bad Request',
                        401: 'Unauthorized',
                        402: 'Payment Required',
                        403: 'Forbidden',
                        404: 'Not Found',
                        405: 'Method Not Allowed',
                        406: 'Not Acceptable',
                        407: 'Proxy Authentication Required',
                        408: 'Request Time-out',
                        409: 'Conflict',
                        410: 'Gone',
                        411: 'Length Required',
                        412: 'Precondition Failed',
                        413: 'Request Entity Too Large',
                        414: 'Request-URI Too Large',
                        415: 'Unsupported Media Type',
                        416: 'Requested range not satisfiable',
                        417: 'Expectation Failed',
                        500: 'Internal Server Error',
                        501: 'Not Implemented',
                        502: 'Bad Gateway',
                        503: 'Service Unavailable',
                        504: 'Gateway Time-out',
                        505: 'HTTP Version not supported'})
    REASON_CODES = CODE_REASONS.inverted()

    @classmethod
    def from_bytes(cls, bstr):
        bstr, m = cls.advance(bstr)
        if not m:
            raise InvalidStatusCode('Unparseable status code: '
                                    '{0}'.format(core._cut(bstr)))
        code = int(m.group())

        return bstr, cls(code, cls.CODE_REASONS.get(code, '<unknown status>'))

    def to_bytes(self):
        return bytes(self[0])


class StatusLine(namedtuple('StatusLine', 'version status_code reason'),
                 BytestringHelper):
    # 6.1: No CR or LF is allowed except in the final CRLF sequence.
    advance = core.advancer('([^' + re.escape(core.TEXT_EXCLUDE) + '\r\n]*)')

    @classmethod
    def from_bytes(cls, bstr):
        bstr, version = HTTPVersion.from_bytes(bstr)
        bstr, status_code = StatusCode.from_bytes(bstr.lstrip())
        bstr, m = core.IS_LINE_END(bstr)
        if m:
            reason = status_code.reason
        else:
            bstr, m = cls.advance(bstr.lstrip())
            reason = m.group()
            bstr, m = core.IS_LINE_END(bstr)

        if not m:
            raise InvalidStatusLine('trailing characters: '
                                    '{0}'.format(core._cut(bstr)))

        return bstr, cls(version, status_code.code, reason)

    def to_bytes(self):
        version, status_code, reason = self
        if reason is None:
            reason = StatusCode.CODE_REASONS.get(status_code)
        bs = [version, status_code]
        if reason:
            bs.append(reason)
        return b' '.join(map(bytes, bs)) + b'\r\n'


# TODO: uri or url?

class RequestLine(namedtuple('RequestLine', 'method uri version'),
                  BytestringHelper):
    METHOD = core.advancer('[^' + re.escape(core.TOKEN_EXCLUDE) + ']+')
    URL = core.advancer(_ABS_RE)

    @classmethod
    def from_bytes(cls, bstr):
        bstr, m = cls.METHOD(bstr)
        if not m:
            raise InvalidRequestLine('Unable to extract method: '
                                     '{0}'.format(core._cut(bstr)))
        bstr, method = bstr.lstrip(), m.group()

        bstr, m = cls.URL(bstr)
        if not m:
            raise InvalidRequestLine('Unable to parse uri: '
                                     '{0}'.format(core._cut(bstr)))
        uri = URL(m.group(), strict=True)

        bstr, version = HTTPVersion.from_bytes(bstr.lstrip())

        bstr, m = core.IS_LINE_END(bstr)
        if not m:
            raise InvalidRequestLine('Trailing characters: '
                                     '{0}'.format(core._cut(bstr)))

        return bstr, cls(method, uri, version)

    def to_bytes(self):
        return b' '.join(map(bytes, self)) + b'\r\n'


class Headers(BytestringHelper, OMD):
    ISCONTINUATION = re.compile('^[' + re.escape(''.join(set(core.LWS) -
                                                         set(core.CRLF)))
                                + ']')
    ISKEY = re.compile('[^' + re.escape(core.TOKEN_EXCLUDE) + ']+')

    @classmethod
    def from_bytes(cls, bstr):
        bstr, m = core.HAS_HEADERS_END(bstr)
        if not m:
            raise InvalidHeaders('Cannot find header termination '
                                 '{0}'.format(core._cut(bstr)))

        lines = m.group().splitlines()[:-1]
        if cls.ISCONTINUATION.match(lines[0]):
            raise InvalidHeaders('Cannot begin with a continuation: '
                                 '{0}'.format(bstr[:core.MAXLINE]))

        parsed = []
        for idx in xrange(len(lines)):
            line = lines[idx]
            if cls.ISCONTINUATION.match(line):
                pidx = idx - 1
                lines[pidx] = lines[pidx] + line
                continue

            k, _, v = line.partition(':')
            if not cls.ISKEY.match(k):
                raise InvalidHeaders('Invalid field name: {0}'.format(k))

            k, v = k.title(), v.strip()
            parsed.append((k, v))

        return bstr, cls(parsed)

    def to_bytes(self):
        return (b'\r\n'.join(b': '.join([bytes(k), bytes(v)])
                             for k, v in self.items(multi=True))
                + b'\r\n')       # trailing CRLF is necessary
