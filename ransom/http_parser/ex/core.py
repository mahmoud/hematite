import re

# TODO: make configurable
MAXLINE = 2 ** 19


def _cut(s, to=MAXLINE):
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
CLRF = '\r\n'
LWS = CLRF + ' \t'
# <any US-ASCII control character (octets 0 - 31) and DEL (127)>
CTL = ''.join(chr(i) for i in xrange(0, 32)) + chr(127)

SEPARATORS = r'()<>@,;:\"/[]?={} \t'
TOKEN_EXCLUDE = ''.join(set(CTL) | set(SEPARATORS))

# <any OCTET except CTLs, but including LWS>
TEXT_EXCLUDE = ''.join(set(CTL) - set(LWS))

# this *should* be CLRF but not everything uses that as its delineator
# TODO: do we have to be able to recognize just carriage returns?
DELINEATOR = '(?:(?:\r\n)|\n)'
HAS_LINE_END = advancer('.*?' + DELINEATOR, re.DOTALL)
HAS_HEADERS_END = advancer('.*?' + (DELINEATOR * 2), re.DOTALL)
IS_LINE_END = advancer(DELINEATOR, re.DOTALL)
IS_HEADERS_END = advancer((DELINEATOR * 2), re.DOTALL)


def istext(t):
    return t.translate('', '', TEXT_EXCLUDE) == t
