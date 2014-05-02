import time
import errno
import io
import socket
import select

from hematite.url import URL
from hematite.socket_io import iopair_from_socket
from hematite.raw import core, messages as m, envelope as e, body as b


class RequestResponsePair(object):

    def __init__(self, sock, input_envelope):
        self.sock = sock
        fn = sock.fileno()
        self.fileno = lambda: fn
        self.reader, self.writer = iopair_from_socket(sock)
        self.input_envelope = input_envelope
        self.output_envelope = e.ResponseEnvelope()
        self.output_body = None
        self.body_bits = []

        self.body_ready = False

        self._writer_iter = input_envelope._make_writer()

    @property
    def complete(self):
        return self.state is m.Complete

    def write_request_headers(self):
        if not self.writer.empty:
            self.writer.write(None)

        next_bit = next(self._writer_iter, m.Empty)
        if next_bit is m.Empty:
            self.state = self.output_envelope.state
            return True
        self.writer.write(next_bit.value)
        return False

    def read_response_headers(self):
        while not self.complete:
            if self.state.type == m.NeedLine.type:
                line = core.readline(self.reader)
                next_state = m.HaveLine(value=line)
            else:
                raise RuntimeError('Unknown state {0}'.format(self.state))
            self.state = self.output_envelope.reader.send(next_state)
        assert self.complete, "Unknown state {0}".format(self.state)
        return self.complete

    def prep_response_body(self):
        h = self.output_envelope.headers
        if b.Body(h).chunked:
            self.output_body = b.ChunkEncodedBody(h)
            self.read_response_body = self.read_response_body_chunk
        else:
            self.output_body = b.IdentityEncodedBody(h)
        self.state = self.output_body.state

    def read_response_body_chunk(self):
        data = None
        while not self.complete:
            if self.state.type == m.NeedLine.type:
                line = core.readline(self.reader)
                next_state = m.HaveLine(value=line)
            elif self.state.type == m.NeedData.type:
                data = self.reader.read(self.state.amount)
                if data is None:
                    raise io.BlockingIOError(None, None)
                next_state = m.HaveData(value=data)
            elif self.state.type == m.NeedPeek.type:
                peeked = self.reader.peek(self.state.amount)
                next_state = m.HavePeek(amount=peeked)
            elif self.state.type == m.HaveData.type:
                self.body_bits.append(self.state.value)
                next_state = m.Empty
            else:
                raise RuntimeError('Unknown state {0}'.format(self.state))
            self.state = self.output_body.reader.send(next_state)

        assert self.complete, 'Unknown state {0}'.format(self.state)
        return self.complete

    def read_response_body(self, amt=None):
        while not self.complete:
            if self.state.type == m.NeedData.type:
                data = self.reader.read(amt or self.state.amount)
                if data is None:
                    raise io.BlockingIOError(None, None)
                self.body_bits.append(data)
                next_state = m.HaveData(value=data)
            else:
                raise RuntimeError('Unknown state {0}'.format(self.state))
            self.state = self.output_body.reader.send(next_state)

        assert self.complete, 'Unknown state {0}'.format(self.state)
        return self.complete


def join(urls):
    readers, writers = [], []
    for url in urls:
        rawreq = e.RequestEnvelope(e.RequestLine('GET',
                                                 url.path or '/',
                                                 e.HTTPVersion(1, 1)),
                                   e.Headers([('Host', url.host),
                                              ('User-Agent', 'test'),
                                              ('Accept', '*/*')]))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        try:
            sock.connect((url.host, url.port or 80))
        except socket.error as exc:
            if exc[0] != errno.EINPROGRESS:
                raise

        writers.append(RequestResponsePair(sock, rawreq))

    finished = []

    def read_body(reader):
        if reader.read_response_body():
            readers.remove(reader)
            finished.append((reader.output_envelope, reader.body_bits))

    while readers or writers:
        next_readers = []
        read_ready, write_ready, _ = select.select(readers, writers, [])

        for writer in write_ready:
            try:
                if writer.write_request_headers():
                    writers.remove(writer)
                    next_readers.append(writer)
            except io.BlockingIOError:
                pass

        for reader in read_ready:
            try:
                if reader.body_ready:
                    read_body(reader)
                else:
                    if reader.read_response_headers():
                        reader.body_ready = True
                        reader.prep_response_body()
                        read_body(reader)
            except io.BlockingIOError:
                print 'blocking read', time.time()
                pass

        readers.extend(next_readers)
    return finished


if __name__ == '__main__':
    def _main():
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
                print j[0].to_bytes(),
                print ''.join(j[1]),
        return joined

    try:
        responses = _main()
    except Exception as e:
        import pdb;pdb.post_mortem()
