import socket
import re
from collections import namedtuple
from ransom.http_parser.ex import core
from ransom.http_parser.ex import headers as h
from ransom.compat import BytestringHelper


class ResponseException(Exception):
    pass


class OverlongRead(ResponseException):
    pass


class RequestURITooLarge(OverlongRead):
    status_code = h.StatusCode.REASON_CODES['Request-URI Too Large']


class IncompleteRead(ResponseException):
    pass


def _advance_until(sock, advancer, amt=1024, limit=core.MAXLINE):
    assert amt < limit, "amt {0} should be lower than limit! {1}".format(
        amt, limit)
    read_amt = 0
    b = []
    while True:
        read = sock.recv(amt)
        if not read:
            raise IncompleteRead
        read_amt += len(read)
        if read_amt > limit:
            raise OverlongRead
        b.append(read)
        if advancer(read, matchonly=True):
            return ''.join(b)


class Response(namedtuple('Response', 'status_line headers body'),
               BytestringHelper):

    def _asbytes(self):
        return b'{0!s}{1!s}\r\n'.format(self.status_line, self.headers)

    @classmethod
    def parsefromsocket(cls, s):
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

        body, headers = h.Headers.parsebytes(header_lines)

        return cls(status_line, headers, body)

    @classmethod
    def parsefrombytes(cls, bstr):
        header_lines, status_line = h.StatusLine.parsebytes(bstr)
        body_start, headers = h.Headers.parsebytes(header_lines)
        return cls(status_line, headers, body_start)


def test():
    c = socket.create_connection(('localhost', 8080))
    req = bytes(h.RequestLine('GET',
                              h.URL('/'),
                              h.HTTPVersion(1, 1)))
    c.sendall(req + '\r\n\r\n')
    resp = Response.parsefromsocket(c)
    c.close()
    return resp


if __name__ == '__main__':
    test()
