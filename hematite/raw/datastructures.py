from hematite.compat import OrderedMultiDict as OMD


class Headers(OMD):
    pass


class ChunkedBody(object):

    def __init__(self, chunks=None):
        self.chunks = chunks or []
        self.data = None

    def send_chunk(self):
        return iter(self.chunks)

    def chunk_received(self, chunk):
        self.chunks.append(chunk)

    def complete(self, length):
        self.data = ''.join(self.chunks)
        assert len(self.data) == length


class Body(object):

    def __init__(self, body=None):
        self.body = body or []
        self.data = None

    def data_received(self, data):
        self.body.append(data)

    def send_data(self):
        return [self.body]

    def complete(self, length):
        self.data = ''.join(self.body)
        self.reported_length = length
