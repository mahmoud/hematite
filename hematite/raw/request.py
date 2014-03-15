# -*- coding: utf-8 -*-

from collections import namedtuple

from hematite.compat import BytestringHelper


class RawRequest(namedtuple('RawRequest', 'request_line, headers, body'),
                 BytestringHelper):

    def to_bytes(self):
        parts = [str(self.request_line)]
        if self.headers:
            parts.append(str(self.headers))
        parts.append('')
        return '\r\n'.join(parts)

    @classmethod
    def from_bytes(self, bytestr):
        pass
