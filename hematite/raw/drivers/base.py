from abc import ABCMeta, abstractmethod
from hematite.raw import messages as M


class BaseIODriver(object):
    __metaclass__ = ABCMeta

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
