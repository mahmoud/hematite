import errno
import socket
import io

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

    def __init__(self, sock, (request_line, headers, body)):
        self.writer = P.RequestWriter(request_line, headers, body)
        self.writer_iter = iter(self.writer)
        self.reader = P.ResponseReader()
        self.socket = sock
        self.inbound, self.outbound = iopair_from_socket(sock)

    def write(self):
        if not self.outbound.empty:
            self.outbound.write(None)

        to_write = next(self.writer_iter, self.writer.state)
        if to_write is M.Complete:
            return self.writer.complete
        elif to_write is M.WantDisconnect:
            self.inbound.close()
            self.outbound.close()
            self.socket.close()
        else:
            self.outbound.write(to_write.value)
        return False

    def read(self):
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
        return self.state

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
