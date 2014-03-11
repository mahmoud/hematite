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


class Response(namedtuple('Response', 'status_line headers body'),
               BytestringHelper):

    def to_bytes(self):
        return b'{0!s}{1!s}\r\n'.format(self.status_line, self.headers)

    @classmethod
    def from_socket(cls, s):
        # TODO: timeouts
        try:
            slandhlines = core._advance_until_lf(s)
        except core.OverlongRead:
            raise RequestURITooLarge

        header_lines, status_line = h.StatusLine.from_bytes(slandhlines)
        _, m = core.HAS_HEADERS_END(header_lines)

        if not m:
            try:
                header_lines += core._advance_until_lflf(s)
            except core.IncompleteRead:
                msg = ('Could not find header terminator: '
                       '{0}'.format(core._cut(header_lines)))
                raise h.InvalidHeaders(msg)

        body_start, headers = h.Headers.from_bytes(header_lines)

        bcls = (b.ChunkEncodedBody
                if cls._is_chunked(headers)
                else b.IdentityEncodedBody)

        return cls(status_line, headers, bcls(backlog=body_start,
                                              sock=s,
                                              headers=headers))

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
    def from_bytes(cls, bstr):
        header_lines, status_line = h.StatusLine.from_bytes(bstr)
        body_start, headers = h.Headers.from_bytes(header_lines)
        return cls(status_line, headers, body_start)


def test(addr, host, url):
    c = socket.create_connection(addr)
    reql = bytes(h.RequestLine('GET',
                               url,
                               h.HTTPVersion(1, 1)))
    headers = bytes(h.Headers([('Host', host),
                               ('Accept-Encoding', 'chunked'),
                               ('TE', 'chunked')]))
    req = reql + headers + '\r\n\r\n'
    c.sendall(req)
    resp = Response.from_socket(c)
    if resp.is_chunked:
        body = []
        while True:
            chunk = resp.body.read_chunk()
            if not chunk:
                break
            body.append(chunk)
        body = ''.join(body)
    else:
        body = resp.body.read()
    return resp, body

if __name__ == '__main__':
    test(('localhost', 8080), host='localhost', url=h.URL('/'))
