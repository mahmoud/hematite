# TODO: byte strings have no .format in python3.3
from collections import namedtuple
from ransom.compat import BytestringHelper
from ransom.compat import OrderedMultiDict as OMD
import ransom.http_parser.ex.core as core
from ransom.url import URL, _ABS_RE
import re


MAXLINE = 9999


class HTTPParseException(Exception):
    pass


class BadStatusLine(HTTPParseException):
    pass


class BadVersion(BadStatusLine):
    pass


class BadStatusCode(BadStatusLine):
    pass


class InvalidRequest(HTTPParseException):
    pass


class HTTPVersion(namedtuple('HTTPVersion', 'major minor'), BytestringHelper):
    advance = core.advancer('HTTP/(\d+)\.(\d+)')

    @classmethod
    def parsebytes(cls, bstr):
        bstr, m = cls.advance(bstr)
        if not m:
            raise BadVersion('Unparseable version: '
                             '{0!r}'.format(bstr[:MAXLINE]))

        major, minor = m.groups()
        try:
            major, minor = int(major), int(minor)
        except ValueError:
            raise BadVersion('Major or minor version is not a digit: '
                             '{0!r}'.format(major, minor))

        return bstr, cls(major, minor)

    def _asbytes(self):
        return b'HTTP/{0}.{1}'.format(*self)


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
    def parsebytes(cls, bstr):
        bstr, m = cls.advance(bstr)
        if not m:
            raise BadStatusCode('Unparseable status code: '
                                '{0}'.format(bstr[:MAXLINE]))
        code = int(m.group())

        return bstr, cls(code, cls.CODE_REASONS.get(code, '<unknown status>'))

    def _asbytes(self):
        return b'{0!i}'.format(self[0])


class StatusLine(namedtuple('StatusLine', 'version status_code reason'),
                 BytestringHelper):
    # 6.1: No CR or LF is allowed except in the final CRLF sequence.
    advance = core.advancer('([^' + re.escape(core.TEXT_EXCLUDE) + '\r\n]*)')

    @classmethod
    def parsebytes(cls, bstr):
        bstr, version = HTTPVersion.parsebytes(bstr)
        bstr, status_code = StatusCode.parsebytes(bstr.lstrip())
        bstr, m = cls.advance(bstr.lstrip())
        reason = m.group() if m and m.group() else status_code.reason

        if bstr.strip():
            raise BadStatusLine('trailing characters: '
                                '{0}'.format(bstr[:MAXLINE]))

        return bstr, cls(version, status_code.code, reason)

    def _asbytes(self):
        version, status_code, reason = self
        if reason is None:
            reason = StatusCode.CODE_REASONS.get(status_code)
        if not reason:
            return b'{0!s} {1!s}\r\n'.format(version, status_code)
        return b'{0!s} {1!s} {2!s}\r\n'.format(version, status_code, reason)


class RequestLine(namedtuple('RequestLine', 'method uri version'),
                  BytestringHelper):
    METHOD = core.advancer('[^' + re.escape(core.TOKEN_EXCLUDE) + ']+')
    URL = core.advancer(_ABS_RE)

    @classmethod
    def parsebytes(cls, bstr):
        bstr, m = cls.METHOD(bstr)
        if not m:
            raise InvalidRequest('Unable to extract method: '
                                 '{0}'.format(bstr[:MAXLINE]))
        bstr, method = bstr.lstrip(), m.group()

        bstr, m = cls.URL(bstr)
        if not m:
            raise InvalidRequest('Unable to parse uri: '
                                 '{0}'.format(bstr[:MAXLINE]))
        uri = URL(m.group(), strict=True)

        bstr, version = HTTPVersion.parsebytes(bstr.lstrip())
        if bstr.strip():
            raise InvalidRequest('Trailing characters: '
                                 '{0}'.format(bstr[:MAXLINE]))

        return cls(method, uri, version)

    def _asbytes(self):
        return b'{0!s} {1!s} {2!s}\r\n'.format(*self)
