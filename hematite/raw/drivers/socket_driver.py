import errno
import io
import socket
import ssl
from hematite.socket_io import iopair_from_socket
from hematite.raw import core
from hematite.raw import parser as P
from .base import BaseIODriver


class SocketClientDriver(BaseIODriver):
    def __init__(self, sock, raw_request):
        self.writer = raw_request.get_writer()
        self.writer_iter = iter(self.writer)
        self.reader = P.ResponseReader()
        self.socket = sock
        self.inbound, self.outbound = iopair_from_socket(sock)

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
        self.outbound.write(data)

    write_line = write_data

    def read_line(self):
        line = self.distinguish_empty(self.inbound.readline, (core.MAXLINE,))

        if len(line) == core.MAXLINE and not core.LINE_END.match(line):
            raise core.OverlongRead

        return line

    def read_data(self, amount):
        data = self.inbound.read(amount)
        if data is None:
            raise core.eagain()
        return data

    def read_peek(self, amount):
        return self.distinguish_empty(self.inbound.peek, (amount,))

    def write(self):
        if not self.outbound.empty:
            self.outbound.write(None)
        return super(SocketClientDriver, self).write()


class SSLSocketClientDriver(SocketClientDriver):

    def __init__(self, *args, **kwargs):
        super(SSLSocketClientDriver, self).__init__(*args, **kwargs)
        self._ssl_exc = None

    def _do_ssl(self, method):
        try:
            ret = method()
        except ssl.SSLError as ssle:
            ret = False
            self._ssl_exc = ssle
            if ssle.errno != ssl.SSL_ERROR_WANT_READ \
               and ssle.errno != ssl.SSL_ERROR_WANT_WRITE:
                raise
        except Exception as e:
            self._ssl_exc = None
            raise
        else:
            self._ssl_exc = None
        return ret

    def write(self):
        return self._do_ssl(super(SSLSocketClientDriver, self).write)

    def read(self):
        return self._do_ssl(super(SSLSocketClientDriver, self).read)

    @property
    def want_read(self):
        if self._ssl_exc:
            return self._ssl_exc.errno == ssl.SSL_ERROR_WANT_READ
        return super(SSLSocketClientDriver, self).want_read

    @property
    def want_write(self):
        if self._ssl_exc:
            return self._ssl_exc.errno == ssl.SSL_ERROR_WANT_WRITE
        return super(SSLSocketClientDriver, self).want_write
