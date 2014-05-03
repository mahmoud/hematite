# -*- coding: utf-8 -*-

from io import BytesIO
from collections import namedtuple

from hematite.compat import BytestringHelper
from hematite.raw.envelope import RequestLine, Headers
from hematite.raw.body import Body


class RawRequest(namedtuple('RawRequest', 'request_line, headers, body'),
                 BytestringHelper):

    def to_bytes(self):
        parts = [self.request_line.to_bytes()]
        if self.headers:
            parts.append(self.headers.to_bytes())
        parts.append('')
        return ''.join(parts)

    @classmethod
    def from_bytes(cls, bytestr):
        bio = BytesIO(bytestr)
        req_line = RequestLine.from_io(bio)
        headers = Headers.from_io(bio)
        body = Body(bio, headers)
        return cls(req_line, headers, body)
