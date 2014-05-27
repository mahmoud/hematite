
import os
import errno
import socket
from threading import Lock
from io import BlockingIOError, BufferedReader

import hematite.compat as compat
import hematite.raw.core as core
from hematite.raw.core import MAXLINE, LINE_END, EndOfStream, OverlongRead


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
            data = data or self.write_backlog
            written = super(NonblockingSocketIO, self).write(data)
            if written is None:
                if self.write_backlog:
                    self.write_backlog += data
                else:
                    self.write_backlog = data
                raise eagain()
            self.write_backlog = data[written:]
            if self.write_backlog:
                raise eagain()


def iopair_from_socket(sock):
    writer = NonblockingSocketIO(sock, "rwb")
    reader = NonblockingBufferedReader(writer)
    return reader, writer
