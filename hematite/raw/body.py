import re

from hematite.raw import core
from hematite.raw import messages as m


class BodyReadException(core.HTTPException):
    pass


class InvalidChunk(BodyReadException):
    pass


class Body(object):
    def __init__(self, io_obj, headers):
        self.io_obj = io_obj
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

        self.read_amt = 0
        self.closed = False
        if not (self.content_length or self.connection_close):
            # TODO: check for multipart/byteranges
            pass


class IdentityEncodedBody(Body):

    def __init__(self, *args, **kwargs):
        super(IdentityEncodedBody, self).__init__(*args, **kwargs)
        self._reader = self._make_reader()
        self.loop = self._make_loop()
        self.state = next(self._reader)

    @property
    def complete(self):
        return self.state.type == m.Complete.type

    def _make_loop(self):
        while not self.complete:
            if self.state.type == m.NeedData:
                data = self.io_obj.read(self.state)

    def _make_reader(self, size=-1):
        if self.content_length:
            size = (self.content_length if size < 0
                    else min(self.content_length, size))
        if self.content_length and self.read_amt == self.content_length \
           or self.closed:
            return ''

        ret = self.io_obj.read(size)
        if not ret:
            self.closed = True

        self.read_amt += len(ret)
        return ret


class ChunkEncodedBody(Body):
    IS_HEX = re.compile('([\dA-Ha-h]+)')

    def __init__(self, *args, **kwargs):
        super(ChunkEncodedBody, self).__init__(*args, **kwargs)
        self._reader = self._make_reader()
        self.state = next(self._reader)
        self.loop = self.loop()
        self.reset()
        self.ready = False

    @property
    def complete(self):
        return self.state.type == m.Complete.type

    def reset(self):
        self.chunk_length = None
        self.read = 0
        self.partials = []

    def _make_loop(self):
        while not self.complete:
            if self.state.type == m.NeedLine.type:
                line = core.readline(self.io_obj)
                next_state = m.HaveLine(value=line)
            elif self.state.type == m.NeedData.type:
                data = self.io_obj.read(self.state.value)
                next_state = m.HaveData(value=data)
            elif self.state.type == m.NeedPeek.type:
                peeked = self.io_obj.peek(self.state.value)
                next_state = m.HavePeek(value=peeked)
            elif self.state.type == m.HaveData.type:
                yield self.state.value
                self.state = m.NeedLine
            elif self.state.type == m.Complete.type:
                pass
            else:
                assert "Unknown state", self.state
            self.state = self._reader.send(next_state)

        return

    def read_chunk(self):
        if self.complete:
            return ''
        return next(self.loop)

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
                t, last = yield m.NeedData(amount=self.chunk_length - len(last))
                assert t == m.HaveData.type

                if not last:
                    raise core.EndOfStream

                self.read -= len(last)
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
                self.complete = True

            self.reset()
            yield m.HaveData(chunk)

        while True:
            yield m.Complete
