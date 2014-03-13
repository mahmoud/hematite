# -*- coding: utf-8 -*-

from collections import namedtuple

from ransom.http_parser.ex import headers as h
from ransom.compat import BytestringHelper


class Request(namedtuple('Request', 'request_line, headers, body'),
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


def _test():
    req = Request(h.RequestLine('GET', '/', h.HTTPVersion(1, 1)),
                  h.Headers([('Host', 'hatnote.com')]))
    print req.to_bytes()


if __name__ == '__main__':
    _test()
