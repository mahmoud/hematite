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


expires = HTTPHeaderField('expires',
                          from_bytes=http_date_from_bytes,
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


_init_field_lists()
del _init_field_lists
