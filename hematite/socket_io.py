import hematite.compat as compat
import hematite.raw.core as core
import threading
import io


class NonblockingBufferedReader(io.BufferedReader):
    linebuffer_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super(NonblockingBufferedReader, self).__init__(*args, **kwargs)
        self.linebuffer = []

    def readline(self, limit):
        with self.linebuffer_lock:
            line = super(NonblockingBufferedReader, self).readline(limit)
            if not line:
                return line

            self.linebuffer.append(line)
            if not core.LINE_END.search(line):
                raise io.BlockingIOError
            line, self.linebuffer = ''.join(self.linebuffer), []
            return line


class BufferedRWPair(io.BufferedIOBase):

    """A buffered reader and writer object together.

    A buffered reader object and buffered writer object put together to
    form a sequential IO object that can read and write. This is typically
    used with a socket or two-way pipe.

    reader and writer are RawIOBase objects that are readable and
    writeable respectively. If the buffer_size is omitted it defaults to
    DEFAULT_BUFFER_SIZE. The max_buffer_size (for the buffered writer)
    defaults to twice the buffer size.
    """

    # XXX The usefulness of this (compared to having two separate IO
    # objects) is questionable.

    def __init__(self, reader, writer,
                 buffer_size=io.DEFAULT_BUFFER_SIZE, max_buffer_size=None,
                 nonblocking=False):
        """Constructor.

        The arguments are two RawIO instances.
        """
        reader._checkReadable()
        writer._checkWritable()
        self.reader = (NonblockingBufferedReader(reader, buffer_size)
                       if nonblocking
                       else
                       io.BufferedReader(reader, buffer_size))
        self.reader = io.BufferedReader(reader, buffer_size)
        self.writer = io.BufferedWriter(writer, buffer_size, max_buffer_size)

    def readline(self, limit):
        return self.reader.readline(limit)

    def read(self, n=None):
        if n is None:
            n = -1
        return self.reader.read(n)

    def readinto(self, b):
        return self.reader.readinto(b)

    def write(self, b):
        return self.writer.write(b)

    def peek(self, n=0):
        return self.reader.peek(n)

    def read1(self, n):
        return self.reader.read1(n)

    def readable(self):
        return self.reader.readable()

    def writable(self):
        return self.writer.writable()

    def flush(self):
        return self.writer.flush()

    def close(self):
        self.writer.close()
        self.reader.close()

    def isatty(self):
        return self.reader.isatty() or self.writer.isatty()

    @property
    def closed(self):
        return self.writer.closed


def bio_from_socket(sock, mode="r", buffering=None, encoding=None,
                    errors=None, newline=None):
    """\
    Backport of Python 3's socket.makefile that uses our
    BufferedRWPair and only returns binary Buffered objects (no
    TextIOWrapper); returns a Buffered* IO class that wraps a SocketIO
    instance
    """
    for _c in mode:
        if _c not in "rwb":
            raise ValueError("invalid mode %r (only r, w, b allowed)")
    writing = "w" in mode
    reading = "r" in mode or not writing
    assert reading or writing
    rawmode = ""
    if reading:
        rawmode += "r"
    if writing:
        rawmode += "w"
    raw = compat.SocketIO(sock, rawmode)
    if buffering is None:
        buffering = -1
    if buffering < 0:
        buffering = io.DEFAULT_BUFFER_SIZE
    if buffering == 0:
        return raw
    nonblocking = sock.gettimeout() == 0
    if reading and writing:
        buffer = BufferedRWPair(raw, raw, buffering, nonblocking=nonblocking)
    elif reading:
        buffer = (NonblockingBufferedReader(raw, buffering)
                  if nonblocking
                  else
                  io.BufferedReader(raw, buffering))
    else:
        assert writing
        buffer = io.BufferedWriter(raw, buffering)
    return buffer
