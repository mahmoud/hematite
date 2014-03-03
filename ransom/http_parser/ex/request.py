import socket
import re
from collections import namedtuple
from ransom.http_parser.ex import core
from ransom.http_parser.ex import headers as h
from ransom.compat import BytestringHelper

MAXLINE = 4096


class ResponseException(Exception):
    pass


class IncompleteRead(ResponseException):
    pass


def _advance_until(sock, advancer, amt=1024):
    b = []
    while True:
        read = sock.recv(amt)
        if not read:
            raise IncompleteRead
        b.append(read)
        m = advancer(read, matchonly=True)
        if m:
            return ''.join(b), m


class Response(namedtuple('Response', 'status_line headers body'),
               BytestringHelper):
    # this *should* be core.CLRF but not everything uses that as its delineator
    DELINEATOR = '(?:(?:\r\n)|\n)'
    LINE_END = core.advancer('.*?' + DELINEATOR, re.DOTALL)
    HEADERS_END = core.advancer('.*?' + (DELINEATOR * 2), re.DOTALL)

    def _asbytes(self):
        return b'{0!s}{1!s}\r\n'.format(self.status_line, self.headers)

    @classmethod
    def parsefromsocket(cls, s):
        slandhls, m = _advance_until(s, cls.LINE_END)
        sl, headersls = slandhls[:m.end()], slandhls[m.end():]

        _, status_line = h.StatusLine.parsebytes(sl)

        _, m = cls.HEADERS_END(headersls)

        if not m:
            try:
                m, read = _advance_until(s, cls.HEADERS_END)
                headersls += read
            except IncompleteRead:
                msg = ('Could not find header terminator: '
                       '{0}'.format(headersls[:MAXLINE]))
                raise h.InvalidHeaders(msg)

        body = headersls[m.end():]
        _, headers = h.Headers.parsebytes(headersls[:m.end()])

        return cls(status_line, headers, body)


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
