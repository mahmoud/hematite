# -*- coding: utf-8 -*-

from hematite.raw.messages import Complete
from hematite.raw.datastructures import Headers
from hematite.raw.parser import (HTTPVersion,
                                 RequestLine,
                                 RequestWriter,
                                 HeadersWriter)


DEFAULT_METHOD = 'GET'
DEFAULT_URL = '/'
DEFAULT_HTTP_VERSION = HTTPVersion(1, 1)


class RawRequest(object):
    # TODO: is this a good pattern at this level?
    _writer_class = RequestWriter

    def __init__(self, method=None, url=None, headers=None, body=None,
                 http_version=None, request_line=None):
        if request_line:
            method = request_line.method
            url = request_line.url
            http_version = request_line.version
        self.method = method if method is not None else DEFAULT_METHOD
        self.url = url if url is not None else DEFAULT_URL
        if http_version is None:
            http_version = DEFAULT_HTTP_VERSION
        self.http_version = http_version

        self.headers = headers or Headers()
        self.body = body  # TODO: bodies

    # TODO: setter for the following?
    @property
    def request_line(self):
        return RequestLine(method=self.method,
                           url=self.url,
                           version=self.http_version)

    def get_writer(self):
        return RequestWriter(request_line=self.request_line,
                             headers=HeadersWriter(self.headers),
                             body=self.body)  # TODO: bodies

    def to_bytes(self):
        writer = self.get_writer()
        return b''.join(part for _state, part in writer.writer if
                        _state != Complete.type)
