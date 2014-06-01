# -*- coding: utf-8 -*-

from io import BytesIO

from hematite.raw import messages as M
from hematite.raw.messages import Complete
from hematite.raw.datastructures import Headers
from hematite.raw.parser import (RequestLine,
                                 RequestWriter,
                                 RequestReader,
                                 HeadersWriter,
                                 parse_message_traits)


class RawRequest(object):
    # TODO: is this a good pattern at this level?
    _writer_class = RequestWriter

    def __init__(self, method=None, url=None, headers=None, body=None,
                 http_version=None, **kwargs):
        request_line = kwargs.pop('request_line', None)
        if request_line:
            method = request_line.method
            url = request_line.url
            http_version = request_line.version
        self.method = method
        self.url = url
        self.http_version = http_version

        self.host_url = kwargs.pop('host_url', url)
        self.headers = headers or Headers()
        self.body = body  # TODO: bodies

        traits = parse_message_traits(self.headers)
        self.chunked = kwargs.pop('chunked', traits.chunked)
        self.content_length = kwargs.pop('content_length',
                                         traits.content_length)
        if kwargs:
            raise TypeError('got unexpected kwargs: %r' % kwargs.keys())

    @property
    def request_line(self):
        return RequestLine(method=self.method,
                           url=self.url,
                           version=self.http_version)

    @request_line.setter
    def request_line(self, val):
        if isinstance(val, bytes):
            val = RequestLine.from_bytes(val)
        try:
            self.method, self.url, self.http_version = val
        except:
            raise TypeError('expected RequestLine or 3-tuple, not %r' % val)

    def get_writer(self):
        return RequestWriter(request_line=self.request_line,
                             headers=HeadersWriter(self.headers),
                             body=self.body)  # TODO: bodies

    def to_bytes(self):
        writer = self.get_writer()
        return b''.join(part for _state, part in writer.writer if
                        _state != Complete.type)

    @classmethod
    def from_bytes(cls, bytestr):
        bio = BytesIO(bytestr)
        reader = RequestReader()
        state = reader.state
        while True:
            if state is M.Complete:
                break
            elif state.type == M.NeedLine.type:
                line = bio.readline()  # TODO: limit?
                next_state = M.HaveLine(value=line)
            elif state.type == M.NeedData.type:
                data = bio.read(state.amount)
                # TODO: can this block or return None if empty etc?
                next_state = M.HaveData(value=data)
            elif state.type == M.NeedPeek.type:
                peeked = bio.peek(state.amount)
                if not peeked:
                    pass  # TODO: again, what happens on end of stream
                next_state = M.HavePeek(amount=peeked)
            else:
                raise RuntimeError('Unknown state %r' % (state,))
            state = reader.send(next_state)

        return reader.raw_request
