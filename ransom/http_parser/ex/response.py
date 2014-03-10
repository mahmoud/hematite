import socket
from collections import namedtuple
from ransom.http_parser.ex import core
from ransom.http_parser.ex import headers as h
from ransom.http_parser.ex import body as b
from ransom.compat import BytestringHelper


# TODO: timeouts


class ResponseException(Exception):
    pass


class RequestURITooLarge(ResponseException, core.OverlongRead):
    status_code = h.StatusCode.REASON_CODES['Request-URI Too Large']


def _advance_until_lf(s):
    return core._advance_until(s, core.HAS_LINE_END)


def _advance_until_lflf(s):
    return core._advance_until(s, core.HAS_HEADERS_END)


class Response(namedtuple('Response', 'status_line headers body'),
               BytestringHelper):

    def _asbytes(self):
        return b'{0!s}{1!s}\r\n'.format(self.status_line, self.headers)

    @classmethod
    def parsefromsocket(cls, s):
        # TODO: timeouts
        try:
            slandhlines = _advance_until_lf(s)
        except core.OverlongRead:
            raise RequestURITooLarge

        header_lines, status_line = h.StatusLine.parsebytes(slandhlines)
        _, m = core.HAS_HEADERS_END(header_lines)

        if not m:
            try:
                header_lines += _advance_until_lflf(s)
            except core.IncompleteRead:
                msg = ('Could not find header terminator: '
                       '{0}'.format(core._cut(header_lines)))
                raise h.InvalidHeaders(msg)

        body_start, headers = h.Headers.parsebytes(header_lines)

        bcls = (b.ChunkEncodedBody
                if cls._is_chunked(headers)
                else b.IdentityEncodedBody)

        return cls(status_line, headers, bcls(body_start, s, headers))

    @core._callable_staticmethod
    def _is_chunked(headers):
        # 4.4 #2
        try:
            return headers['Transfer-Encoding'].lower() != 'identity'
        except KeyError:
            return False

    @property
    def is_chunked(self):
        return self._is_chunked(self.headers)

    @classmethod
    def parsefrombytes(cls, bstr):
        header_lines, status_line = h.StatusLine.parsebytes(bstr)
        body_start, headers = h.Headers.parsebytes(header_lines)
        return cls(status_line, headers, body_start)


def test(addr):
    c = socket.create_connection(addr)
    reql = bytes(h.RequestLine('GET',
                               h.URL('/'),
                               h.HTTPVersion(1, 1)))
    headers = bytes(h.Headers([('Host', 'localhost')]))
    req = reql + headers + '\r\n\r\n'
    c.sendall(req)
    resp = Response.parsefromsocket(c)
    body = resp.body.read()
    c.close()
    return resp, body


if __name__ == '__main__':
    test(('localhost', 8080))
