# -*- coding: utf-8 -*-

from compat import (unicode, bytes, OrderedDict, StringIO,
                    urlparse, urlunparse, urlencode, requote)


# From RFC3987
_ESC_RANGES = [(0xA0, 0xD7FF),
               (0xE000, 0xF8FF),
               (0xF900, 0xFDCF),
               (0xFDF0, 0xFFEF),
               (0xE1000, 0xFFFFD),
               (0xF0000, 0xFFFFD),
               (0x100000, 0x10FFFD)]
_ESC_RANGES.extend([(i, i + 0xFFFD) for i in range(0x10000, 0xE0000, 0x10000)])
_ESC_RANGES.sort(key=lambda x: x[0])


def parse_url(url_str, encoding='utf-8'):
    if not isinstance(url_str, unicode):
        try:
            url_str = url_str.decode(encoding)
        except AttributeError:
            raise TypeError('parse_url expected str, unicode, or bytes')
    parsed = urlparse(url_str)
    parsed = parsed._replace(netloc=parsed.netloc.decode('idna'))
    print parsed
    return parsed


class URL(object):
    _attrs = ('scheme', 'username', 'password', 'hostname',
              'port', 'path', 'params', 'query', 'fragment')

    def __init__(self, url_str):
        up = parse_url(url_str)
        _d = unicode()
        for attr in self._attrs:
            setattr(self, attr, getattr(up, attr) or _d)

    @property
    def netloc(self):
        ret = []
        if self.username:
            ret.append(self.username)
            if self.password:
                ret.extend([':', self.password])
            ret.append('@')
        ret.append(self.hostname)
        port = str(self.port)
        if port:
            ret.extend([':', self.port])
        return u''.join(ret)

    def __iter__(self):
        s, i = self, iter
        return i((s.scheme, s.netloc, s.path, s.params, s.query, s.fragment))

    def __str__(self):
        # TODO: inherit or duck type
        return urlunparse(self).encode('utf-8')  # TODO
