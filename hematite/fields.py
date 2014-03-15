# -*- coding: utf-8 -*-

from datetime import datetime

from hematite.constants import (REQUEST_HEADERS,
                                RESPONSE_HEADERS,
                                http_header_case)
from hematite.serdes import (http_date_to_bytes,
                             http_date_from_bytes,
                             list_header_to_bytes,
                             list_header_from_bytes,
                             items_header_to_bytes,
                             items_header_from_bytes)
from hematite.url import URL, parse_hostinfo

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
    URL_REQUEST_FIELDS = [url_field, url_path_field]
    REQUEST_FIELDS = HTTP_REQUEST_FIELDS + URL_REQUEST_FIELDS


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


date = HTTPHeaderField('date',
                       from_bytes=http_date_from_bytes,
                       to_bytes=http_date_to_bytes,
                       native_type=datetime)

last_modified = HTTPHeaderField('last_modified',
                                from_bytes=http_date_from_bytes,
                                to_bytes=http_date_to_bytes,
                                native_type=datetime)


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

content_language = HTTPHeaderField('content_language',
                                   from_bytes=list_header_from_bytes,
                                   to_bytes=list_header_to_bytes,
                                   native_type=list)

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


class URLField(Field):
    attr_name = 'url'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.to_text()  # unicode for now

    def __set__(self, obj, value):
        # TODO: None handling?
        if isinstance(value, URL):
            url_obj = value
        else:
            url_obj = URL(value)
        if not url_obj.path:
            url_obj.path = '/'
        obj._url = url_obj
        obj.host = url_obj.http_request_host


url_field = URLField()


def _set_host_value(self, obj, value):
    self._default_set_value(obj, value)
    cur_val = obj.headers.get('Host')
    url = obj._url
    if not cur_val:
        family, host, port = None, '', ''
    else:
        family, host, port = parse_hostinfo(cur_val)
        url.host, url.port, url.family = family, host, port


host = HTTPHeaderField('host',
                       set_value=_set_host_value)


class URLPathField(Field):
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


url_path_field = URLPathField()

_init_field_lists()
del _init_field_lists
