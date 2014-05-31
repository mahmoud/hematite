from abc import ABCMeta, abstractmethod
from hematite.compat import SocketIO
from hematite.raw import core
from hematite.raw import messages as M
from hematite.raw import parser as P
import errno
import io
import socket
import ssl
from threading import Lock, RLock


class BaseIODriver(object):
    __metaclass__ = ABCMeta

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.writer_iter = iter(writer)

    @abstractmethod
    def write_line(self, line):
        """
        Writes a line to output
        """
        pass

    @abstractmethod
    def write_data(self, data):
        """
        Writes data to output
        """
        pass

    @abstractmethod
    def read_line(self):
        """
        Read a line from input
        """
        pass

    @abstractmethod
    def read_data(self, amount):
        """
        Read data from input
        """
        pass

    @abstractmethod
    def read_peek(self, amount):
        """
        Peek data from input
        """
        pass

    def write(self):
        for state in self.writer_iter:
            self.state = state
            if state is M.Complete:
                return True
            elif state.type == M.HaveLine.type:
                self.write_line(state.value)
            elif state == M.HaveData.type:
                self.write_data(state.value)
            else:
                raise RuntimeError("Unknown state {0!r}".format(state))
        return False

    def read(self):
        self.state = self.reader.state
        while not self.reader.complete:
            if self.state.type == M.NeedLine.type:
                line = self.read_line()
                next_state = M.HaveLine(value=line)
            elif self.state.type == M.NeedData.type:
                data = self.read_data(self.state.amount)
                next_state = M.HaveData(value=data)
            elif self.state.type == M.NeedPeek.type:
                peeked = self.read_peek(self.state.amount)
                next_state = M.HavePeek(value=peeked)
            else:
                raise RuntimeError('Unknown state {0!r}'.format(self.state))
            self.state = self.reader.send(next_state)
        return True

    @property
    def want_read(self):
        return self.writer.complete and not self.reader.complete

    @property
    def want_write(self):
        return not self.writer.complete

    @property
    def outbound_headers(self):
        return self.writer.headers

    @property
    def outbound_completed(self):
        return self.writer.complete

    @property
    def inbound_headers(self):
        return self.reader.headers

    @property
    def inbound_headers_completed(self):
        return self.reader.headers_reader.complete

    @property
    def inbound_completed(self):
        return self.reader.complete

    @property
    def inbound_body(self):
        return self.reader.body.data


class SocketDriver(BaseIODriver):
    readline_buffer_lock = Lock()
    write_backlog_rlock = RLock()

    # NB we're shadowing the socket module here!
    def __init__(self, socket, reader, writer):
        super(SocketDriver, self).__init__(reader=reader, writer=writer)

        self.outbound = SocketIO(socket, 'rwb')
        self.inbound = io.BufferedReader(self.outbound)
        self.socket = socket

        self.readline_buffer = []
        self.write_backlog = ''

    def distinguish_empty(self, io_method, args):
        """Some io.SocketIO methods return the empty string both for
        disconnects and EAGAIN.  Attempt to distinguish between the two.
        """
        result = io_method(*args)
        if not result:
            try:
                if self.socket.recv(1, socket.MSG_PEEK):
                    # the socket has become readable in the time it took
                    # to get here.  raise a BlockingIOError so we can get
                    # selected as readable again
                    raise core.eagain()
                else:
                    # the socket was actually disconnected
                    raise core.EndOfStream
            except socket.error as e:
                if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                    # if this isn't a blocking io errno, raise the legitimate
                    # exception
                    raise
                # a socket can't be reopened for reading if it's
                # closed/shutdown, so it's still unreadable.  raise a
                # BlockingIOError to communicate this upward
                raise io.BlockingIOError(*e.args)
        return result

    def write_data(self, data):
        with self.write_backlog_rlock:
            written = self.outbound.write(data)
            if not written:
                # written may be None, but characters_written on
                # BlockingIOError must be an integer. so set it to 0.
                written = 0
                self.write_backlog = data
            else:
                self.write_backlog = data[written:]
            if self.write_backlog:
                raise core.eagain(characters_written=written)

            return written

    write_line = write_data

    def read_line(self):
        with self.readline_buffer_lock:
            partial_line = self.distinguish_empty(self.inbound.readline,
                                                  (core.MAXLINE,))

            self.readline_buffer.append(partial_line)
            if not core.LINE_END.search(partial_line):
                raise core.eagain()

            line = ''.join(self.readline_buffer)
            self.readline_buffer = []
            return line

    def read_data(self, amount):
        data = self.inbound.read(amount)
        if data is None:
            raise core.eagain()
        return data

    def read_peek(self, amount):
        return self.distinguish_empty(self.inbound.peek, (amount,))

    def write(self):
        with self.write_backlog_rlock:
            if self.write_backlog:
                self.outbound.write(self.write_backlog)
        return super(SocketDriver, self).write()


class SSLSocketDriver(SocketDriver):

    def __init__(self, *args, **kwargs):
        self._socket = None
        super(SSLSocketDriver, self).__init__(*args, **kwargs)
        self._ssl_exc = None

    @property
    def socket(self):
        return self._socket

    @socket.setter
    def socket(self, sock):
        self._socket = sock._sock

    def _do_ssl(self, method):
        try:
            ret = method()
        except ssl.SSLError as ssle:
            ret = False
            print ssle.errno, ssl.SSL_ERROR_WANT_READ
            self._ssl_exc = ssle
            if ssle.errno != ssl.SSL_ERROR_WANT_READ \
               and ssle.errno != ssl.SSL_ERROR_WANT_WRITE:
                raise core.eagain()
        except Exception:
            self._ssl_exc = None
            raise
        else:
            self._ssl_exc = None
        return ret

    def write(self):
        return self._do_ssl(super(SSLSocketDriver, self).write)

    def read(self):
        return self._do_ssl(super(SSLSocketDriver, self).read)

    @property
    def want_read(self):
        if self._ssl_exc:
            return self._ssl_exc.errno == ssl.SSL_ERROR_WANT_READ
        return super(SSLSocketDriver, self).want_read

    @property
    def want_write(self):
        if self._ssl_exc:
            return self._ssl_exc.errno == ssl.SSL_ERROR_WANT_WRITE
        return super(SSLSocketDriver, self).want_write


class BufferedReaderDriver(BaseIODriver):

    def __init__(self, raw_request, inbound, outbound):
        self.writer = raw_request.get_writer()
        self.writer_iter = iter(self.writer)
        self.reader = P.ResponseReader()
        self.inbound, self.outbound = inbound, outbound

    def write_data(self, data):
        self.outbound.write(data)

    write_line = write_data

    def read_line(self):
        line = self.inbound.readline(core.MAXLINE)
        if len(line) == core.MAXLINE and not core.LINE_END.match(line):
            raise core.OverlongRead

        return self.inbound.readline(core.MAXLINE)

    def read_data(self, amount):
        data = self.inbound.read(amount)
        return data

    def read_peek(self, amount):
        return self.inbound.peek(amount)
