import errno
import io
import socket
import select

from hematite.url import URL
from hematite.socket_io import iopair_from_socket
from hematite.raw import core, messages as m, envelope as e


class ManagedSocket(object):

    def __init__(self, sock, input, output):
        self.sock = sock
        fn = sock.fileno()
        self.fileno = lambda: fn
        self.reader, self.writer = iopair_from_socket(sock)
        self.state = m.Empty
        self.input = input
        self.output = output
        self._writer_iter = input._make_writer()

    @classmethod
    def complete(self):
        return self.state is m.Complete

    def write(self):
        if not self.writer.empty:
            self.writer.write(None)

        next_bit = next(self._writer_iter, m.Empty)
        if next_bit is m.Empty:
            self.state = self.output.state
            return True
        self.writer.write(next_bit.value)
        return False

    def read(self):
        while self.state.type != m.Complete.type:
            if self.state.type == m.NeedLine.type:
                line = core.readline(self.reader)
                next_state = m.HaveLine(value=line)
            elif self.state.type != m.Complete.type:
                assert "Unknown state", self.state
            self.state = self.output.reader.send(next_state)

        return self.complete


def join(urls):
    readers, writers = [], []
    for url in urls:
        rawreq = e.RequestEnvelope(e.RequestLine('GET',
                                                 url.to_bytes(),
                                                 e.HTTPVersion(1, 1)),
                                   e.Headers([('Accept', 'text/html')]))
        rawresp = e.ResponseEnvelope()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        try:
            sock.connect((url.host, url.port or 80))
        except socket.error as exc:
            if exc[0] != errno.EINPROGRESS:
                raise

        writers.append(ManagedSocket(sock, rawreq, rawresp))
    finished = []

    while readers or writers:
        next_readers = []
        read_ready, write_ready, _ = select.select(readers, writers, [])

        for writer in write_ready:
            try:
                if writer.write():
                    writers.remove(writer)
                    next_readers.append(writer)
            except io.BlockingIOError as exc:
                pass

        for reader in read_ready:
            try:
                if reader.read():
                    readers.remove(reader)
                    finished.append(reader.output)
            except io.BlockingIOError:
                pass

        readers.extend(next_readers)
    return finished


if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument('urls', nargs='+')
    a.add_argument('-p', '--print',
                   dest='shouldprint',
                   action='store_true')

    args = a.parse_args()
    joined = join([URL(u) for u in args.urls])

    if args.shouldprint:
        for j in joined:
            print j.to_bytes()
