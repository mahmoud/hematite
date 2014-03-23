# -*- coding: utf-8 -*-

from datetime import datetime

from hematite.constants import (REQUEST_HEADERS,
                                RESPONSE_HEADERS,
                                http_header_case)
from hematite.serdes import (quote_header_value,
                             unquote_header_value,
                             http_date_to_bytes,
                             http_date_from_bytes,
                             list_header_to_bytes,
                             list_header_from_bytes,
                             items_header_to_bytes,
                             items_header_from_bytes,
                             accept_header_to_bytes,
                             accept_header_from_bytes,
                             default_header_to_bytes,
                             default_header_from_bytes,
                             content_header_from_bytes)
from hematite.url import URL, parse_hostinfo, QueryArgDict

ALL_FIELDS = None
RESPONSE_FIELDS = None
REQUEST_FIELDS = None
HTTP_REQUEST_FIELDS = None


def _init_field_lists():
    global ALL_FIELDS, RESPONSE_FIELDS, REQUEST_FIELDS, HTTP_REQUEST_FIELDS
    global_vals = globals().values()
    ALL_FIELDS = [f for f in global_vals if isinstance(f, HTTPHeaderField)]
    RESPONSE_FIELDS = [f for f in ALL_FIELDS
                       if f.http_name in RESPONSE_HEADERS]
    HTTP_REQUEST_FIELDS = [f for f in ALL_FIELDS
                           if f.http_name in REQUEST_HEADERS]
    _url_request_field_types = [f for f in global_vals if isinstance(f, type)
                                and issubclass(f, BaseURLField)]
    URL_REQUEST_FIELDS = [f() for f in _url_request_field_types]
    REQUEST_FIELDS = HTTP_REQUEST_FIELDS + URL_REQUEST_FIELDS


class HeaderValueWrapper(object):
    # TODO: how to indicate whether header value should be included
    # - __nonzero__ can collide with int-typed headers where 0 is valid
    # - a blank to_bytes() output might work, but is a bit confusing
    pass


class ETag(HeaderValueWrapper):
    def __init__(self, tag, is_weak=None):
        self.tag = tag
        self.is_weak = is_weak or False

    def to_bytes(self):
        if self.tag == '*':
            return '*'  # can't have a weak star
        ret = quote_header_value(self.tag, allow_token=False)
        if self.is_weak:
            ret = 'W/' + ret
        return ret

    @classmethod
    def from_bytes(cls, bytestr):
        tag = bytestr.strip()
        first_two = tag[:2]
        if first_two == 'W/' or first_two == 'w/':
            is_weak = True
            tag = tag[2:]
        else:
            is_weak = False
        tag = unquote_header_value(tag)
        return cls(tag=tag, is_weak=is_weak)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r, is_weak=%r)' % (cn, self.tag, self.is_weak)


class ETagSet(HeaderValueWrapper):
    """
    TODO: all the matching logic
    """
    def __init__(self, etags=None):
        etags = list(etags or [])
        self.etags = etags

    @classmethod
    def from_bytes(cls, bytestr):
        etags = []
        raw_tags = bytestr.split(',')
        for raw_tag in raw_tags:
            etags.append(ETag.from_bytes(raw_tag))
            # TODO except on ValueError, drop invalid etags
        return cls(etags=etags)

    def to_bytes(self):
        return ', '.join([etag.to_bytes() for etag in self.etags])

    def __len__(self):
        return len(self.etags)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r)' % (cn, self.etags)


class Field(object):
    attr_name = None

    def __delete__(self, obj):
        raise AttributeError("can't delete field '%s'" % self.attr_name)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s("%s")' % (cn, self.attr_name)


class HTTPHeaderField(Field):
    def __init__(self, name, **kw):
        assert name
        assert name == name.lower()
        self.attr_name = name  # used for error messages
        self.http_name = kw.pop('http_name', http_header_case(name))
        self.native_type = kw.pop('native_type', unicode)

        default_from_bytes = (getattr(self.native_type, 'from_bytes', None)
                              or default_header_from_bytes)
        default_to_bytes = (getattr(self.native_type, 'to_bytes', None)
                            or default_header_to_bytes)

        self.from_bytes = kw.pop('from_bytes', default_from_bytes)
        self.to_bytes = kw.pop('to_bytes', default_to_bytes)
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
        # TODO: if obj.headers.get(self.http_name) != value:
        obj.headers[self.http_name] = value

    __set__ = _default_set_value


date = HTTPHeaderField('date',
                       from_bytes=http_date_from_bytes,
                       to_bytes=http_date_to_bytes,
                       native_type=datetime)

last_modified = HTTPHeaderField('last_modified',
                                from_bytes=http_date_from_bytes,
                                to_bytes=http_date_to_bytes,
                                native_type=datetime)

etag = HTTPHeaderField('etag', native_type=ETag)


def expires_from_bytes(bytestr):
    """
    According to RFC2616 14.21, invalid Expires headers MUST treat
    invalid timestamps as "already expired", thus the epoch datetime.
    """
    try:
        return http_date_from_bytes(bytestr)
    except:
        return datetime.utcfromtimestamp(0)


expires = HTTPHeaderField('expires',
                          from_bytes=expires_from_bytes,
                          to_bytes=http_date_to_bytes,
                          native_type=datetime)


class ContentType(HeaderValueWrapper):
    def __init__(self, media_type, charset=None, params=None):
        self.media_type = media_type
        self.charset = charset
        self.params = dict(params) if params else {}

    @classmethod
    def from_bytes(cls, bytestr):
        # TODO: order
        media_type, items = content_header_from_bytes(bytestr)
        params = dict(items)
        charset = params.pop('charset', None)
        return cls(media_type=media_type, charset=charset, params=params)

    def to_bytes(self):
        # TODO: quote parameter values
        parts = [self.media_type]
        if self.charset:
            parts.append('charset=' + self.charset)
        if self.params:
            parts.extend(['%s=%s' % (k, v) for k, v in self.params.items()])
        return '; '.join(parts)

    def __repr__(self):
        cn = self.__class__.__name__
        if self.params:
            return ('%s(%r, charset=%r, params=%r)'
                    % (cn, self.media_type, self.charset, self.params))
        return '%s(%r, charset=%r)' % (cn, self.media_type, self.charset)


content_type = HTTPHeaderField('content_type', native_type=ContentType)


class ContentDisposition(HeaderValueWrapper):
    def __init__(self,
                 disp_type,
                 filename=None,
                 filename_ext=None,
                 params=None):
        self.disp_type = disp_type
        self.filename = filename
        self.filename_ext = filename_ext
        self.params = dict(params) if params else {}

    @classmethod
    def from_bytes(cls, bytestr):
        # TODO: RFC5987 decoding and saving of ext charsets where applicable
        disp_type, params = content_header_from_bytes(bytestr)
        filename, filename_ext, ext_params = None, None, []
        for item in params:
            if item[0].lower() == 'filename':
                filename = item[1]
            elif item[0].lower() == 'filename*':
                filename_ext = item[1]
            else:
                ext_params.append(item)
        return cls(disp_type=disp_type,
                   filename=filename,
                   filename_ext=filename_ext,
                   params=ext_params)

    def to_bytes(self):
        # TODO: quote parameter values
        parts = [self.disp_type]
        if self.filename is not None:
            parts.append('filename=' + self.filename)
        if self.filename_ext is not None:
            parts.append('filename*=' + self.filename_ext)
        if self.params:
            parts.extend(['%s=%s' % (k, v) for k, v in self.params.items()])
        return '; '.join(parts)

    def get_filename(self, coerce_ext=True):
        """TODO: convenience method that automatically bridges the
        presence of filename/filename_ext"""

    @property
    def is_inline(self):
        return self.disp_type.lower() == 'inline'

    @property
    def is_attachment(self):
        return self.disp_type.lower() == 'attachment'

    def __repr__(self):
        cn = self.__class__.__name__
        if self.params:
            return ('%s(%r, filename=%r, filename_ext=%r, params=%r)'
                    % (cn, self.disp_type, self.filename,
                       self.filename_ext, self.params))
        return ('%s(%r, filename=%r, filename_ext=%r)'
                % (cn, self.disp_type, self.filename, self.filename_ext))


content_disposition = HTTPHeaderField('content_disposition',
                                      native_type=ContentDisposition)

content_language = HTTPHeaderField('content_language',
                                   from_bytes=list_header_from_bytes,
                                   to_bytes=list_header_to_bytes,
                                   native_type=list)

if_match = HTTPHeaderField('if_match', native_type=ETagSet)
if_none_match = HTTPHeaderField('if_none_match', native_type=ETagSet)

if_modified_since = HTTPHeaderField('if_modified_since',
                                    from_bytes=http_date_from_bytes,
                                    to_bytes=http_date_to_bytes,
                                    native_type=datetime)

if_unmodified_since = HTTPHeaderField('if_unmodified_since',
                                      from_bytes=http_date_from_bytes,
                                      to_bytes=http_date_to_bytes,
                                      native_type=datetime)

www_authenticate = HTTPHeaderField('www_authenticate',
                                   from_bytes=items_header_from_bytes,
                                   to_bytes=items_header_to_bytes,
                                   native_type=list)

cache_control = HTTPHeaderField('cache_control',
                                from_bytes=items_header_from_bytes,
                                to_bytes=items_header_to_bytes,
                                native_type=list)

accept = HTTPHeaderField('accept',
                         from_bytes=accept_header_from_bytes,
                         to_bytes=accept_header_to_bytes,
                         native_type=list)

accept_language = HTTPHeaderField('accept_language',
                                  from_bytes=accept_header_from_bytes,
                                  to_bytes=accept_header_to_bytes,
                                  native_type=list)

accept_encoding = HTTPHeaderField('accept_encoding',
                                  from_bytes=accept_header_from_bytes,
                                  to_bytes=accept_header_to_bytes,
                                  native_type=list)


accept_charset = HTTPHeaderField('accept_charset',
                                 from_bytes=accept_header_from_bytes,
                                 to_bytes=accept_header_to_bytes,
                                 native_type=list)

# TODO: referer or referrer?
referer = HTTPHeaderField('referer',
                          native_type=URL)


class HostHeaderField(HTTPHeaderField):
    def __init__(self):
        super(HostHeaderField, self).__init__(name='host')

    def __set__(self, obj, value):
        super(HostHeaderField, self).__set__(obj, value)
        cur_val = obj.headers.get('Host')
        url = obj._url

        if not cur_val:
            family, host, port = None, '', ''
        else:
            family, host, port = parse_hostinfo(cur_val)
        url.family, url.host, url.port = family, host, port
        return


host = HostHeaderField()


from_field = HTTPHeaderField('_from', http_name='From')
server_field = HTTPHeaderField('server')
user_agent = HTTPHeaderField('user_agent')
connection = HTTPHeaderField('connection')
trailer = HTTPHeaderField('trailer',
                          from_bytes=list_header_from_bytes,
                          to_bytes=list_header_to_bytes)
vary = HTTPHeaderField('vary',
                       from_bytes=list_header_from_bytes,
                       to_bytes=list_header_to_bytes)

location = HTTPHeaderField('location', native_type=URL)



"""
Several key Request attributes are URL-based. Similar to the
HTTPHeaderField, which is backed by a Headers dict, URL fields are
backed by a URL object on the Request instance.

desired url-related fields:

request.url - bytes or unicode? can be set with URL instance, too
request.host - host *header* (should be equal to url.host + url.port)
request.hostname/request.domain - host attr of URL
request.path - url path (unicode)
request.port - int
request.args/.params/.query_params/.GET - QueryArgDict
request.query_string - bytes or unicode?
request.scheme - http/https

Some of these will need to trigger updates to the Host header and
the Host header field will need to trigger updates to some of
these.

other potential fields (that will likely remain on the underlying URL
object only for the time being):

 - username
 - password
 - fragment

note: wz request obj has 71 public attributes (not starting with '_')
"""


class BaseURLField(Field):
    pass


class URLField(BaseURLField):
    attr_name = 'url'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.to_text()  # unicode for now

    def __set__(self, obj, value):
        if isinstance(value, URL):
            url_obj = value
        else:
            url_obj = URL(value)
        if not url_obj.path:
            # A bit concerned about this, but Chrome does add a slash
            # to the end of many URLs, client-side
            url_obj.path = '/'
        obj._url = url_obj


class URLPathField(BaseURLField):
    attr_name = 'path'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.path

    def __set__(self, obj, value):
        # TODO: how to handle stuff like OPTIONS *
        if value is None or value == '':
            value = '/'
        obj._url.path = value  # TODO: type checking/parsing?


class URLHostnameField(BaseURLField):
    attr_name = 'hostname'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.host

    def __set__(self, obj, value):
        if value is None or value == '':
            value = ''
        obj._url.host = value


class URLPortField(BaseURLField):
    attr_name = 'port'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.port

    def __set__(self, obj, value):
        if value is None or value == '':
            value = ''
        else:
            value = int(value)
        obj._url.port = value


class URLArgsField(BaseURLField):
    attr_name = 'args'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.args

    def __set__(self, obj, value):
        if value is None:
            obj._url.args.clear()
        elif not isinstance(value, QueryArgDict):
            raise TypeError('expected QueryArgDict, not %r' % type(value))
        else:
            obj._url.args = value
        return


class URLQueryStringField(BaseURLField):
    attr_name = 'query_string'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.query_string

    def __set__(self, obj, value):
        if value is None:
            obj._url.args.clear()
        elif not isinstance(value, unicode):  # allow bytestrings?
            raise TypeError('expected unicode, not %r' % type(value))
        else:
            obj._url.args = QueryArgDict.from_string(value)


class URLSchemeField(BaseURLField):
    attr_name = 'scheme'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.scheme

    def __set__(self, obj, value):
        if value is None:
            obj._url.scheme = ''
        elif not isinstance(value, unicode):  # allow bytestrings?
            raise TypeError('expected unicode, not %r' % type(value))
        else:
            obj._url.scheme = value


_init_field_lists()
del _init_field_lists
