# -*- coding: utf-8 -*-

import re
import string

import time
from datetime import datetime, timedelta


from constants import CAP_MAP


def http_header_case(text):
    text = text.replace('_', '-').lower()
    try:
        return CAP_MAP[text]
    except KeyError:
        # Exceptions: ETag, TE, WWW-Authenticate, Content-MD5
        return '-'.join([p.capitalize() for p in text.split('-')])


# TODO: lazy loading headers: good or bad?
# TODO: class decorator to make a map of headerfields, etc. for Request/Response


class HTTPHeaderField(object):
    def __init__(self, name, **kw):
        assert name
        assert name == name.lower()
        self.attr_name = name  # used for error messages
        self.http_name = kw.pop('http_name', http_header_case(name))
        try:
            self.__set__ = kw.pop('set_value')
        except KeyError:
            pass
        self.native_type = kw.pop('native_type', unicode)

        # TODO: better defaults
        self.from_bytes = kw.pop('from_bytes', lambda val: val)
        self.to_bytes = kw.pop('to_bytes', lambda val: val)
        if kw:
            raise TypeError('unexpected keyword arguments: %r' % kw)
        # TODO: documentation field
        # TODO: validate

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        try:
            return obj.headers[self.http_name]
        except KeyError:
            raise AttributeError(self.attr_name)

    def _default_set_value(self, obj, value):
        # TODO: special handling for None? text/unicode type? (i.e, not bytes)
        if isinstance(value, str):
            value = self.from_bytes(value)
        elif value is None:
            pass
        elif not isinstance(value, self.native_type):
            vtn = value.__class__.__name__
            ntn = self.native_type.__name__
            # TODO: include trunc'd value in addition to input type name
            raise TypeError('expected bytes or %s for %s, not %s'
                            % (ntn, self.attr_name, vtn))
        obj.headers[self.http_name] = value

    __set__ = _default_set_value

    def __delete__(self, obj):
        raise AttributeError("can't delete field '%s'" % self.attr_name)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s("%s")' % (cn, self.attr_name)


_TOKEN_CHARS = frozenset("!#$%&'*+-.^_`|~" + string.letters + string.digits)


def quote_header_value(value, allow_token=True):
    value = str(value)
    if allow_token:
        # TODO: is this really an optimization?
        if set(value).issubset(_TOKEN_CHARS):
            return value
    return '"%s"' % value.replace('\\', '\\\\').replace('"', '\\"')


def unquote_header_value(value, is_filename=False):
    if value and value[0] == value[-1] == '"':
        value = value[1:-1]
        if not is_filename or value[:2] != '\\\\':
            return value.replace('\\\\', '\\').replace('\\"', '"')
    return value


def list_header_from_bytes(val, unquote=True):
    "e.g., Accept-Ranges. skips blank values, per the RFC."
    ret = []
    for v in _list_header_from_bytes(val):
        if not v:
            continue
        if unquote and v[0] == '"' == v[-1]:
            v = unquote_header_value(v)
        ret.append(v)
    return ret


def list_header_to_bytes(val):
    return ', '.join([quote_header_value(v) for v in val])


def items_header_from_bytes(val, unquote=True, sep=None):
    """
    TODO: I think unquote is always true here? values can always be
    quoted.
    """
    ret, sep = [], sep or ','
    for item in _list_header_from_bytes(val, sep=sep):
        key, _part, value = item.partition('=')
        if not _part:
            ret.append((key, None))
            continue
        if unquote and value and value[0] == '"' == value[-1]:
            value = unquote_header_value(value)
        ret.append((key, value))
    return ret


def items_header_to_bytes(items, sep=None):
    parts, sep = [], sep or ', '
    for key, val in items:
        if val is None or val == '':
            parts.append(key)
        else:
            parts.append('='.join([str(key), quote_header_value(val)]))
    return sep.join(parts)

_accept_re = re.compile(r'('
                        r'(?P<media_type>[^,;]+)'
                        r'(;\s*q='
                        r'(?P<quality>[^,;]+))?),?')


def accept_header_from_bytes(val):
    """
    Parses an Accept-style header (with q-vals) into a list of tuples
    of `(media_type, quality)`. Input order is maintained (does not sort
    by quality value).

    Does not check media_type format for mimetype-style format. Does
    not implement "accept-extension", as they seem to have never been
    used. (search for "text/html;level=1" in RFC2616 to see an example)

    >>> parse_accept_header('audio/*; q=0.2 , audio/basic')
    [('audio/*', 0.2), ('audio/basic', 1.0)]
    """
    ret = []
    for match in _accept_re.finditer(val):
        media_type = (match.group('media_type') or '').strip()
        if not media_type:
            continue
        try:
            quality = max(min(float(match.group('quality') or 1.0), 1.0), 0.0)
        except:
            quality = 0.0
        ret.append((media_type, quality))
    return ret


def content_header_from_bytes(val):
    """
    Parses a Content-Type header, a combination of list and key-value
    headers, separated by semicolons.. RFC2231 is crazy, so this initial
    implementation only supports features I've seen before.

    (Also used for the Content-Disposition header)

    # TODO: find examples for tests
    # TODO: implement some _crazy_ features:
    #  - rollup of asterisk-indexed parts (param continuations) (RFC2231 #3)
    #  - parameter encodings and languages (RFC2231 #4)
    """
    items = items_header_from_bytes(val, sep=';')
    if not items:
        return '', []
    media_type = items[0][0]
    return media_type, items[1:]


def http_date_from_bytes(date_str):
    # TODO: is the strip really necessary?
    timetuple = _date_tz_from_bytes(date_str.strip())
    tz_seconds = timetuple[-1] or 0
    tz_offset = timedelta(seconds=tz_seconds)
    return datetime(*timetuple[:7]) - tz_offset


_dayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None,  # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def http_date_to_bytes(date_val=None, sep=' '):
    """
    Output an RFC1123-formatted date suitable for the Date header and
    cookies (with sep='-').

    # TODO: might have to revisit byte string handling
    """
    if date_val is None:
        time_tuple = time.gmtime()
    elif isinstance(date_val, datetime):
        time_tuple = date_val.utctimetuple()
    else:
        raise ValueError()  # support other timestamps?

    year, month, day, hh, mm, ss, wd, y, z = time_tuple
    return ("%s, %02d%s%3s%s%4d %02d:%02d:%02d GMT" %
            (_dayname[wd], day, sep, _monthname[month], sep, year, hh, mm, ss))


def _list_header_from_bytes(bytestr, sep=None):
    """Parse lists as described by RFC 2068 Section 2.

    In particular, parse comma-separated lists where the elements of
    the list may include quoted-strings.  A quoted-string could
    contain a comma.  A non-quoted string could have quotes in the
    middle.  Neither commas nor quotes count if they are escaped.
    Only double-quotes count, not single-quotes.

    (based on urllib2 from the stdlib)
    """
    res, part, sep = [], '', sep or ','

    escape = quote = False
    for cur in bytestr:
        if escape:
            part += cur
            escape = False
            continue
        if quote:
            if cur == '\\':
                escape = True
                continue
            elif cur == '"':
                quote = False
            part += cur
            continue

        if cur == sep:
            res.append(part)
            part = ''
            continue

        if cur == '"':
            quote = True

        part += cur

    # append last part
    if part:
        res.append(part)

    return [part.strip() for part in res]


def _date_tz_from_bytes(data):
    """Convert a date string to a time tuple.

    Accounts for military timezones (for some reason).

    # TODO: raise exceptions instead of returning None
    # TODO: non-GMT named timezone support necessary?

    Based on the built-in email package from Python 2.7.
    """
    data = data.split()
    # The FWS after the comma after the day-of-week is optional, so search and
    # adjust for this.
    if data[0].endswith(',') or data[0].lower() in _daynames:
        # There's a dayname here. Skip it
        del data[0]
    else:
        i = data[0].rfind(',')
        if i >= 0:
            data[0] = data[0][i+1:]
    if len(data) == 3:  # RFC 850 date, deprecated
        stuff = data[0].split('-')
        if len(stuff) == 3:
            data = stuff + data[1:]
    if len(data) == 4:
        s = data[3]
        i = s.find('+')
        if i > 0:
            data[3:] = [s[:i], s[i+1:]]
        else:
            data.append('')  # Dummy tz
    if len(data) < 5:
        return None
    data = data[:5]
    dd, mm, yy, tm, tz = data
    mm = mm.lower()
    if mm not in _monthnames:
        dd, mm = mm, dd.lower()
        if mm not in _monthnames:
            return None
    mm = _monthnames.index(mm) + 1
    if mm > 12:
        mm -= 12
    if dd[-1] == ',':
        dd = dd[:-1]
    i = yy.find(':')
    if i > 0:
        yy, tm = tm, yy
    if yy[-1] == ',':
        yy = yy[:-1]
    if not yy[0].isdigit():
        yy, tz = tz, yy
    if tm[-1] == ',':
        tm = tm[:-1]
    tm = tm.split(':')
    if len(tm) == 2:
        [thh, tmm] = tm
        tss = '0'
    elif len(tm) == 3:
        [thh, tmm, tss] = tm
    else:
        return None
    try:
        yy, dd, thh, tmm, tss = int(yy), int(dd), int(thh), int(tmm), int(tss)
    except ValueError:
        return None
    # Check for a yy specified in two-digit format, then convert it to the
    # appropriate four-digit format, according to the POSIX standard. RFC 822
    # calls for a two-digit yy, but RFC 2822 (which obsoletes RFC 822)
    # mandates a 4-digit yy. For more information, see the documentation for
    # the time module.
    if yy < 100:
        # The year is between 1969 and 1999 (inclusive).
        if yy > 68:
            yy += 1900
        # The year is between 2000 and 2068 (inclusive).
        else:
            yy += 2000
    tzoffset = None
    tz = tz.upper()
    if tz in _timezones:
        tzoffset = _timezones[tz]
    else:
        try:
            tzoffset = int(tz)
        except ValueError:
            pass
    # Convert a timezone offset into seconds ; -0500 -> -18000
    if tzoffset:
        if tzoffset < 0:
            tzsign = -1
            tzoffset = -tzoffset
        else:
            tzsign = 1
        tzoffset = tzsign * ((tzoffset // 100) * 3600 + (tzoffset % 100) * 60)
    # Daylight Saving Time flag is set to -1, since DST is unknown.
    return yy, mm, dd, thh, tmm, tss, 0, 1, -1, tzoffset


_monthnames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul',
               'aug', 'sep', 'oct', 'nov', 'dec',
               'january', 'february', 'march', 'april', 'may', 'june', 'july',
               'august', 'september', 'october', 'november', 'december']

_daynames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

# The timezone table does not include the military time zones defined
# in RFC822, other than Z.  According to RFC1123, the description in
# RFC822 gets the signs wrong, so we can't rely on any such time
# zones.  RFC1123 recommends that numeric timezone indicators be used
# instead of timezone names.

_timezones = {'UT':0, 'UTC':0, 'GMT':0, 'Z':0,
              'AST': -400, 'ADT': -300,  # Atlantic (used in Canada)
              'EST': -500, 'EDT': -400,  # Eastern
              'CST': -600, 'CDT': -500,  # Central
              'MST': -700, 'MDT': -600,  # Mountain
              'PST': -800, 'PDT': -700   # Pacific
              }


def _test_accept():
    _accept_tests = ['',
                     ' ',
                     'audio/*; q=0.2 , audio/basic',  # Accept
                     'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                     'iso-8859-5, unicode-1-1;q=0.8',  # Accept-Charset
                     '*',  # Accept-Encoding
                     'compress, gzip',
                     'compress;q=0.5, gzip;q=1.0',
                     'gzip;q=1.0, identity; q=0.5, *;q=0',
                     'da, en-gb;q=0.8, en;q=0.7',  # Accept-Language
                     'bytes',  # Accept-Ranges  # TODO
                     'none']
    for t in _accept_tests:
        print
        print accept_header_from_bytes(t)


def _test_items_header():
    _items_tests = ['',
                    ' ',
                    'Basic realm="myRealm"',  # WWW-Authenticate
                    'private, community="UCI"']  # Cache control
    for t in _items_tests:
        print items_header_from_bytes(t)

    print items_header_to_bytes([('Basic realm', 'myRealm')])
    return


def _test_list_header():
    print list_header_from_bytes('mi, en')  # Content-Language
    print list_header_from_bytes('')  # TODO: Allow, Vary, Pragma
    return


def _test_http_date():
    # date examples from 3.3.1 with seconds imcrementing
    print http_date_from_bytes('Sun, 06 Nov 1994 08:49:37 GMT')
    print http_date_from_bytes('Sunday, 06-Nov-94 08:49:38 GMT')
    print http_date_from_bytes('Sun Nov  6 08:49:39 1994')


def _test_content_header():
    _rough_content_type = ('message/external-body; access-type=URL;'
                           ' URL*0="ftp://";'
                           ' URL*1="cs.utk.edu/pub/moore/bulk-mailer/bulk-mailer.tar"')
    _content_tests = ['',
                      ' ',
                      'text/plain',
                      'text/html; charset=ISO-8859-4',
                      _rough_content_type]
    for t in _content_tests:
        print content_header_from_bytes(t)


if __name__ == '__main__':
    def _main():
        _test_accept()
        _test_items_header()
        _test_list_header()
        _test_http_date()
        _test_content_header()

    _main()
