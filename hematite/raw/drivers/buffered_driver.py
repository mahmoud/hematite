from hematite.raw import core
from hematite.raw import parser as P
from .base import BaseIODriver


class BufferedReaderClientIODriver(BaseIODriver):

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
