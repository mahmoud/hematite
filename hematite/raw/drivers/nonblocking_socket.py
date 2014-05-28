
import io
import ssl
import errno
import socket


from hematite.socket_io import iopair_from_socket
from hematite.raw import core, messages as M, parser as P


def readline(io_obj, sock):
    try:
        return core.readline(io_obj)
    except core.EndOfStream:
        try:
            if not sock.recv(1, socket.MSG_PEEK):
                raise
        except socket.error as e:
            if e.errno != errno.EAGAIN:
                raise
        raise io.BlockingIOError(None, None)


class NonblockingSocketClientDriver(object):

    def __init__(self, sock, raw_request):
        self.writer = raw_request.get_writer()
        self.writer_iter = iter(self.writer)
        self.reader = P.ResponseReader()
        self.socket = sock
        self.inbound, self.outbound = iopair_from_socket(sock)

        self._ssl_exc = None

    @property
    def want_read(self):
        if self._ssl_exc and self._ssl_exc.errno == ssl.SSL_ERROR_WANT_READ:
            return True
        if self.writer.state == M.Complete and self.reader.state != M.Complete:
            return True
        return False

    @property
    def want_write(self):
        if self._ssl_exc and self._ssl_exc.errno == ssl.SSL_ERROR_WANT_WRITE:
            return True
        if self.writer.state != M.Complete:  # sort of implied
            return True
        return False

    def write(self):
        try:
            ret = self._write()
        except ssl.SSLError as ssle:
            ret = False
            self._ssl_exc = ssle
            if ssle.errno != ssl.SSL_ERROR_WANT_READ \
               and ssle.errno != ssl.SSL_ERROR_WANT_WRITE:
                raise
        except:
            self._ssl_exc = None
            raise
        else:
            self._ssl_exc = None
        return ret

    def _write(self):
        """
        Writes as much of the message as possible.

        Returns whether or not the whole message is
        complete. BlockingIOErrors are raised through.
        """
        if not self.outbound.empty:
            self.outbound.write(None)

        for state in self.writer_iter:
            if state is M.Complete:
                return True
            else:
                self.outbound.write(state.value)
        return False

    def read(self):
        try:
            ret = self._read()
        except ssl.SSLError as ssle:
            ret = False
            self._ssl_exc = ssle
            if ssle.errno != ssl.SSL_ERROR_WANT_READ \
               and ssle.errno != ssl.SSL_ERROR_WANT_WRITE:
                raise
        except:
            self._ssl_exc = None
            raise
        else:
            self._ssl_exc = None
        return ret

    def _read(self):
        """
        Reads and parses as much of the message as possible.

        Returns whether or not the whole message is
        complete. BlockingIOErrors are raised through.
        """
        self.state = self.reader.state
        while not self.reader.complete:
            if self.state.type == M.NeedLine.type:
                line = readline(self.inbound, self.socket)
                next_state = M.HaveLine(value=line)
            elif self.state.type == M.NeedData.type:
                data = self.inbound.read(self.state.amount)
                if data is None:
                    raise io.BlockingIOError(None, None)
                next_state = M.HaveData(value=data)
            elif self.state.type == M.NeedPeek.type:
                peeked = self.inbound.peek(self.state.amount)
                if not peeked:
                    raise io.BlockingIOError(None, None)
                next_state = M.HavePeek(amount=peeked)
            else:
                raise RuntimeError('Unknown state {0}'.format(self.state))

            self.state = self.reader.send(next_state)
        return True

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
