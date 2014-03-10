import socket
from collections import namedtuple
from ransom.http_parser.ex import core
from ransom.http_parser.ex import headers as h
from ransom.http_parser.ex import body as b
from ransom.compat import BytestringHelper


# TODO: timeouts


class ResponseException(Exception):
    pass


class OverlongRead(ResponseException):
    pass


class RequestURITooLarge(OverlongRead):
    status_code = h.StatusCode.REASON_CODES['Request-URI Too Large']


class IncompleteRead(ResponseException):
    pass


def _advance_until(sock, advancer, amt=1024, limit=core.MAXLINE):
    # TODO: this is quadratic time -- be more precise about '\r\n'|'\n'
    assert amt < limit, "amt {0} should be lower than limit! {1}".format(
        amt, limit)
    read_amt = 0
    buf = []
    while True:
        read = sock.recv(amt)
        if not read:
            raise IncompleteRead
        read_amt += len(read)
        if read_amt > limit:
            raise OverlongRead
        buf.append(read)
        joined = ''.join(buf)
        if advancer(joined, matchonly=True):
            return joined


class Response(namedtuple('Response', 'status_line headers body'),
               BytestringHelper):

    def _asbytes(self):
        return b'{0!s}{1!s}\r\n'.format(self.status_line, self.headers)

    @classmethod
    def parsefromsocket(cls, s):
        # TODO: timeouts
        try:
            slandhlines = _advance_until(s, core.HAS_LINE_END)
        except OverlongRead:
            raise RequestURITooLarge

        header_lines, status_line = h.StatusLine.parsebytes(slandhlines)
        _, m = core.HAS_HEADERS_END(header_lines)

        if not m:
            try:
                header_lines += _advance_until(s, core.HAS_HEADERS_END)
            except IncompleteRead:
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
