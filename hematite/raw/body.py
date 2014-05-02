import re

from hematite.raw import core
from hematite.raw import messages as m


class BodyReadException(core.HTTPException):
    pass


class InvalidChunk(BodyReadException):
    pass


class Body(object):
    def __init__(self, headers):
        norm_headers = dict([(k.lower(), v) for k, v in headers.items()])
        try:
            self.content_length = int(norm_headers['content-length'])
        except:
            self.content_length = None

        try:
            conn_close = norm_headers['connection'].lower() == 'close'
        except:
            conn_close = False
        self.connection_close = conn_close

        try:
            c = norm_headers['transfer-encoding'].lower().startswith('chunked')
        except:
            c = False
        self.chunked = c

        self.read_amt = 0
        self.closed = False
        if all(field is None for field in [self.content_length,
                                           self.connection_close,
                                           self.chunked]):
            # TODO: check for multipart/byteranges
            raise BodyReadException("Can't read lengthless body")
        self.state = m.Empty


class IdentityEncodedBody(Body):
    DEFAULT_AMT = 1024

    def __init__(self, *args, **kwargs):
        super(IdentityEncodedBody, self).__init__(*args, **kwargs)
        assert not self.chunked

        self.reader = self._make_reader()
        self.state = next(self.reader)

    @property
    def complete(self):
        return self.state.type == m.Complete.type

    def _make_reader(self):
        to_read = (self.DEFAULT_AMT if self.content_length is None
                   else self.content_length)

        while not self.complete:
            t, read = yield m.NeedData(amount=to_read)
            assert t == m.HaveData.type

            if not len(read):
                self.state = m.Complete
            else:
                self.read_amt += len(read)

                if self.content_length:
                    to_read = (self.content_length - self.read_amt)

                if to_read <= 0:
                    self.state = m.Complete
        while True:
            yield m.Complete


class ChunkEncodedBody(Body):
    IS_HEX = re.compile('([\dA-Ha-h]+)')

    def __init__(self, *args, **kwargs):
        super(ChunkEncodedBody, self).__init__(*args, **kwargs)
        assert self.chunked

        self.reader = self._make_reader()
        self.state = next(self.reader)
        self.reset()
        self.ready = False

    @property
    def complete(self):
        return self.state.type == m.Complete.type

    def reset(self):
        self.chunk_length = None
        self.read = 0
        self.partials = []

    def _make_reader(self):
        while not self.complete:
            t, chunk_header = yield m.NeedLine
            assert t == m.HaveLine.type

            if not chunk_header:
                raise InvalidChunk('Could not read chunk header: Disconnected')

            if not self.IS_HEX.match(chunk_header):
                raise InvalidChunk('Could not read chunk header', chunk_header)

            # trailing CLRF?
            self.chunk_length = int(chunk_header, 16)

            if self.chunk_length > core.MAXLINE:
                raise InvalidChunk('Requested too large a chunk',
                                   self.chunk_length)

            last = ''
            while self.read < self.chunk_length:
                t, last = yield m.NeedData(amount=self.chunk_length
                                           - self.read)
                assert t == m.HaveData.type

                if not last:
                    raise core.EndOfStream

                self.read += len(last)
                self.partials.append(last)

            chunk = ''.join(self.partials)

            t, peek = (yield m.NeedPeek(amount=2))
            assert t == m.HavePeek.type

            cr, lf = peek[:2]

            if cr == '\r' and lf == '\n':
                discard = 2
            elif cr == '\n':
                # lf is not actually lf, but real data
                discard == 1
            else:
                raise InvalidChunk('No trailing CRLF|LF', chunk)

            t, data = yield m.NeedData(amount=discard)
            assert t == m.HaveData.type

            if not self.chunk_length and not chunk:
                self.state = m.Complete
            else:
                self.reset()
                state = yield m.HaveData(value=chunk)
                assert state is m.Empty

        while True:
            yield m.Complete
