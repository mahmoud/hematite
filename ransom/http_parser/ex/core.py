import re

# TODO: make configurable
MAXLINE = 2 ** 19


def _cut(s, to=MAXLINE):
    if len(s) <= to:
        return s
    return s[:to]


class _callable_staticmethod(staticmethod):

    def __call__(self, *args, **kwargs):
        return self.__func__(*args, **kwargs)


def advancer(regex, flags=0):
    r = re.compile(regex, flags)

    @_callable_staticmethod
    def advance(string, matchonly=False):
        m = r.match(string)
        if matchonly:
            return m
        if m:
            return string[m.end():], m
        return string, None

    return advance

# RFC 2616 p.17
CRLF = '\r\n'
LWS = CRLF + ' \t'
# <any US-ASCII control character (octets 0 - 31) and DEL (127)>
CTL = ''.join(chr(i) for i in xrange(0, 32)) + chr(127)

SEPARATORS = r'()<>@,;:\"/[]?={} \t'
TOKEN_EXCLUDE = ''.join(set(CTL) | set(SEPARATORS))

# <any OCTET except CTLs, but including LWS>
TEXT_EXCLUDE = ''.join(set(CTL) - set(LWS))

# this *should* be CRLF but not everything uses that as its delineator
# TODO: do we have to be able to recognize just carriage returns?
DELINEATOR = '(?:(?:\r\n)|\n)'
_LINE_END = re.compile(DELINEATOR, re.DOTALL)
_HEADERS_END = re.compile((DELINEATOR * 2), re.DOTALL)
HAS_LINE_END = advancer('.*?' + _LINE_END.pattern, re.DOTALL)
HAS_HEADERS_END = advancer('.*?' + _HEADERS_END.pattern, re.DOTALL)
IS_LINE_END = advancer(_LINE_END.pattern, re.DOTALL)
IS_HEADERS_END = advancer(_HEADERS_END.pattern, re.DOTALL)


def istext(t):
    return t.translate('', '', TEXT_EXCLUDE) == t


class ReadException(Exception):
    pass


class OverlongRead(ReadException):
    pass


class IncompleteRead(ReadException):
    pass


def _advance_until_lf(sock, amt=1024, limit=MAXLINE):
    assert amt < limit, "amt {0} should be lower than limit! {1}".format(
        amt, limit)
    read_amt = 0
    buf = []
    while True:
        read = sock.recv(amt)
        if not read:
            raise IncompleteRead
        read_amt += len(read)
        if read_amt > limit:
            raise OverlongRead
        buf.append(read)
        if '\n' in read:
            return ''.join(buf)


def _advance_until_lflf(sock, amt=1024, limit=MAXLINE):
    assert amt < limit, "amt {0} should be lower than limit! {1}".format(
        amt, limit)
    read_amt = 0
    buf = []
    prev = ''
    while True:
        read = sock.recv(amt)
        if not read:
            raise IncompleteRead
        read_amt += len(read)
        if read_amt > limit:
            raise OverlongRead
        buf.append(read)
        if (_HEADERS_END.search(read) or _HEADERS_END.match(prev[-2:] +
                                                            read[:2])):
            return ''.join(buf)
        prev = read
