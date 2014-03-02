import re


class _callable_staticmethod(staticmethod):

    def __call__(self, *args, **kwargs):
        return self.__func__(*args, **kwargs)


def advancer(regex):
    r = re.compile(regex)

    @_callable_staticmethod
    def advance(string):
        m = r.match(string)
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


def istext(t):
    return t.translate('', '', TEXT_EXCLUDE) == t
