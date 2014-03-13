# -*- coding: utf-8 -*-

from constants import REQUEST_HEADERS, RESPONSE_HEADERS

from headers import (HTTPHeaderField,
                     http_date_to_bytes,
                     http_date_from_bytes,
                     list_header_to_bytes,
                     list_header_from_bytes,
                     items_header_to_bytes,
                     items_header_from_bytes)
from url import URL, parse_hostinfo

from datetime import datetime

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
    REQUEST_FIELDS = HTTP_REQUEST_FIELDS + [url_field]


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


class URLField(object):
    attr_name = 'url'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._url.to_text()  # unicode for now

    def __set__(self, obj, value):
        if isinstance(value, URL):
            url_obj = value
        else:
            url_obj = URL(value, strict=True)
        if not url_obj.path:
            url_obj.path = '/'
        obj._url = url_obj
        obj.host = url_obj.http_request_host

    def __delete__(self, obj):
        raise AttributeError("can't delete field '%s'" % self.attr_name)

    def __repr__(self):
        return '%s()' % self.__class__.__name__


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


_init_field_lists()
del _init_field_lists
