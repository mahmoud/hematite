import os
import errno
from threading import Lock
from io import BlockingIOError, BufferedReader

import hematite.compat as compat
import hematite.raw.core as core


def eagain(characters_written=0):
    err = BlockingIOError(errno.EAGAIN,
                          os.strerror(errno.EAGAIN))
    err.characters_written = characters_written
    return err


class NonblockingBufferedReader(BufferedReader):
    linebuffer_lock = Lock()

    def __init__(self, *args, **kwargs):
        super(NonblockingBufferedReader, self).__init__(*args, **kwargs)
        self.linebuffer = []

    def readline(self, limit=None):
        with self.linebuffer_lock:
            line = super(NonblockingBufferedReader, self).readline(limit)
            if not line:
                return line

            self.linebuffer.append(line)
            if not core.LINE_END.search(line):
                raise eagain()
            line, self.linebuffer = ''.join(self.linebuffer), []
            return line


class NonblockingSocketIO(compat.SocketIO):
    backlog_lock = Lock()

    def __init__(self, *args, **kwargs):
        super(NonblockingSocketIO, self).__init__(*args, **kwargs)
        self.write_backlog = ''

    # TODO: better name (seems verby almost like flush)
    @property
    def empty(self):
        return not self.write_backlog

    def write(self, data=None):
        with self.backlog_lock:
            if self.write_backlog and data is not None:
                raise ValueError('data must be None when there is a '
                                 'write_backlog.  Did you call empty?')

            to_write = self.write_backlog if data is None else data
            written = super(NonblockingSocketIO, self).write(to_write)
            if not written:
                # this may be None, but characters_written on
                # BlockingIOError must be an integer.  so set it to 0.
                written = 0
                self.write_backlog = to_write
            else:
                self.write_backlog = to_write[written:]

            if self.write_backlog:
                raise eagain(characters_written=written)


def iopair_from_socket(sock):
    writer = NonblockingSocketIO(sock, "rwb")
    reader = NonblockingBufferedReader(writer)
    return reader, writer
