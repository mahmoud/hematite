
import socket
from io import BytesIO
from collections import namedtuple

from hematite.compat import BytestringHelper
from hematite.socket_io import bio_from_socket
from hematite.constants import REASON_CODES

from hematite.raw import core
from hematite.raw import headers as h
from hematite.raw import body as b


# TODO: timeouts


class ResponseException(Exception):
    pass


class RequestURITooLarge(ResponseException, core.OverlongRead):
    status_code = REASON_CODES['Request-URI Too Large']


class RawResponse(namedtuple('RawResponse', 'status_line headers body'),
                  BytestringHelper):
    _fields = ['status_line', 'headers', 'body']

    def __init__(self, status_line=None, headers=None, body=None, io_obj=None):
        if any(status_line, headers, body) and io_obj:
            raise ValueError('must instantiate with either status_line, '
                             'headers, body or io_obj, but not both')
        self.status_line = status_line or h.StatusLine()
        self.headers = headers or h.Headers()
        self.body = body
        self.io_obj = io_obj

        states = {'STATUS_LINE': self.status_line.sendline,
                  'HEADERS': self.headers.sendline,
                  'BODY': self.noop}
        self.state_idx = 0

    def noop(self, *args):
        return True

    def __repr__(self):
        cn = self.__class__.__name__
        fvs = ['{0!r}={1!r}'.format(field, getattr(self, field))
               for field in self._fields]
        return '<{0}: {1}>'.format(cn, ', '.join(fvs))

    def dump(self, io_obj=None):
        raise NotImplementedError

    # def load(self, io_obj):

    def to_bytes(self):
        io_obj = BytesIO()
        self.to_io(io_obj)
        return io_obj.getvalue()

    @classmethod
    def from_io(cls, io_obj):
        status_line = h.StatusLine.from_io(io_obj)
        headers = h.Headers.from_io(io_obj)
        bcls = (b.ChunkEncodedBody
                if cls._is_chunked(headers)
                else b.IdentityEncodedBody)

        return cls(status_line, headers, bcls(io_obj, headers))

    @classmethod
    def from_bytes(cls, bytestr):
        return cls.from_io(BytesIO(bytestr))

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
    resp = RawResponse.from_io(bio_from_socket(c, mode='rb'))
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
