# -*- coding: utf-8 -*-

from constants import REQUEST_HEADERS, RESPONSE_HEADERS

from headers import (HTTPHeaderField,
                     http_date_to_bytes,
                     http_date_from_bytes,
                     list_header_to_bytes,
                     list_header_from_bytes,
                     items_header_to_bytes,
                     items_header_from_bytes)


from datetime import datetime

ALL_FIELDS = None
RESPONSE_FIELDS = None
REQUEST_FIELDS = None


def _init_field_lists():
    global ALL_FIELDS, RESPONSE_FIELDS, REQUEST_FIELDS
    global_vals = globals().values()
    ALL_FIELDS = [f for f in global_vals if isinstance(f, HTTPHeaderField)]
    RESPONSE_FIELDS = [f for f in ALL_FIELDS
                       if f.http_name in RESPONSE_HEADERS]
    REQUEST_FIELDS = [f for f in ALL_FIELDS
                      if f.http_name in REQUEST_HEADERS]


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
    def __init__(self, name, **kw):
        assert name
        assert name == name.lower()
        self.attr_name = name  # used for error messages
        self.url_name = kw.pop('url_name', self.attr_name)
        try:
            self.__set__ = kw.pop('set_value')
        except KeyError:
            pass
        if kw:
            raise TypeError('unexpected keyword arguments: %r' % kw)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # TODO: error message?
        return getattr(obj.url, self.url_name)

    def __set__(self, obj, value):
        pass

    def __delete__(self, obj):
        raise AttributeError("can't delete field '%s'" % self.attr_name)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s("%s")' % (cn, self.attr_name)



_init_field_lists()
del _init_field_lists
