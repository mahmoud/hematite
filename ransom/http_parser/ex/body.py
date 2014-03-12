from ransom.http_parser.ex import core
import re
import socket
import sys


def content_length(headers):
    cl = headers.get('Content-Length')
    if cl is None:
        return None
    if not cl.isdigit():
        # TODO: this is an error per the RFC
        return None
    return int(cl)


def connection_close(headers):
    conn = headers.get('Connection', '')
    return conn.lower() == 'close'


class BodyReadException(Exception):
    pass


class InvalidChunk(BodyReadException):
    pass


class Body(object):
    def __init__(self, backlog, sock, headers, amt=8192):
        self._read_backlog = backlog
        self.sock = sock
        self.content_length = content_length(headers)
        self.connection_close = connection_close(headers)
        self._read_amount = amt
        if not (self.content_length or self.connection_close):
            # TODO: check for mutlipart/byteranges
            pass


class IdentityEncodedBody(Body):

    def read(self, size=-1):
        ret = []
        if size < 0:
            size = (sys.maxint if self.connection_close
                    else self.content_length)
        elif not self.connection_close:
            size = max(self.content_length, size)

        if self._read_backlog:
            bl, self._read_backlog = (self._read_backlog[:size],
                                      self._read_backlog[size:])
            size -= len(bl)
            ret.append(bl)

        while size > 0:
            read = self.sock.recv(min(self._read_amount, size))
            if not read:
                break
            size -= len(read)
            ret.append(read)
        return ''.join(ret)


class ChunkEncodedBody(Body):
    IS_HEX = re.compile('([\dA-Ha-h]+)')
    CHUNK_HEADER_ADVANCE = core.advancer(IS_HEX.pattern + core.DELINEATOR,
                                         re.DOTALL)

    def read_chunk(self):
        rb = self._read_backlog
        chunk = []
        chunk_length = None

        while chunk_length is None:
            if not self.IS_HEX.match(rb):
                rb += core._advance_until_lf(self.sock)
                continue

            partial_chunk, m = self.CHUNK_HEADER_ADVANCE(rb)
            if not m:
                raise InvalidChunk('could not read chunk header: '
                                   '{0!r}'.format(core._cut(rb)))
            chunk_length = int(m.group(), 16)
            chunk.append(partial_chunk)

        to_read = chunk_length - len(partial_chunk)

        if to_read < 0:
            # we overshot the chunk in advance_until_lf
            new_rb, m = core.HAS_LINE_END(partial_chunk[chunk_length:])
            if not m:
                raise InvalidChunk('No trailing CRLF|LF: ',
                                   '{0!r}'.format(
                                       partial_chunk[:-core.MAXLINE]))

            trailing_stuff = m.group().rstrip()
            if trailing_stuff:
                raise InvalidChunk('Misread chunk length, got trailing: '
                                   '{0!r}'.format(core._cut(trailing_stuff)))
            self._read_backlog = new_rb

            return partial_chunk[:chunk_length]

        to_read += 2            # trailing CRLF?

        partial_chunk = self.sock.recv(to_read, socket.MSG_WAITALL)
        if len(partial_chunk) != to_read:
            raise core.IncompleteRead('chunk interrupted')

        chunk.append(partial_chunk)

        # we know we asked for 2 too much, so hack off the last 2 bytes
        # for inspection and replace the last chunk with the trimmed version
        partial_chunk, (cr, lf) = partial_chunk[:-2], partial_chunk[-2:]
        chunk[-1] = partial_chunk

        if cr == '\r' and lf == '\n':
            self._read_backlog = ''
        elif cr == '\n':
            # lf is not actually lf, but real data
            self._read_backlog = lf
        else:
            raise InvalidChunk('No trailing CRLF|LF: '
                               '{0!r}'.format(partial_chunk[:-core.MAXLINE]))

        return ''.join(chunk)
