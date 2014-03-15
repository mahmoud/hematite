# -*- coding: utf-8 -*-

from collections import namedtuple

from hematite.compat import BytestringHelper


class RawRequest(namedtuple('RawRequest', 'request_line, headers, body'),
                 BytestringHelper):

    def to_bytes(self):
        parts = [self.request_line.to_bytes()]
        if self.headers:
            parts.append(self.headers.to_bytes())
        parts.append('')
        return '\r\n'.join(parts)

    @classmethod
    def from_bytes(self, bytestr):
        pass
