
import re

from hematite.raw import core


class BodyReadException(core.HTTPException):
    pass


class InvalidChunk(BodyReadException):
    pass


class Body(object):
    def __init__(self, io_obj, headers):
        self.io_obj = io_obj

        # TODO: better handling for case sensitivity/preservation
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

    def read(self, size=-1):
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

    def read_chunk(self):
        chunk_header = self.io_obj.readline()
        if not chunk_header:
            raise InvalidChunk('Could not read chunk header: Disconnected')

        if not self.IS_HEX.match(chunk_header):
            raise InvalidChunk('Could not read chunk header', chunk_header)

        # trailing CLRF?
        chunk_length = int(chunk_header, 16)

        if chunk_length > core.MAXLINE:
            raise InvalidChunk('Requested too large a chunk', chunk_length)

        chunk = self.io_obj.read(chunk_length)
        cr, lf = self.io_obj.peek(2)[:2]

        if cr == '\r' and lf == '\n':
            discard = 2
        elif cr == '\n':
            # lf is not actually lf, but real data
            discard == 1
        else:
            raise InvalidChunk('No trailing CRLF|LF', chunk)
        self.io_obj.read(discard)
        return chunk
