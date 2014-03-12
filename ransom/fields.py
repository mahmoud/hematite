# -*- coding: utf-8 -*-

from constants import REQUEST, RESPONSE

from headers import HTTPHeaderField
from headers import parse_http_date, serialize_http_date
from headers import parse_list_header, serialize_list_header

from datetime import datetime

ALL_FIELDS = None
RESPONSE_FIELDS = None
REQUEST_FIELDS = None


def _init_field_lists():
    global ALL_FIELDS, RESPONSE_FIELDS, REQUEST_FIELDS
    global_vals = globals().values()
    ALL_FIELDS = [f for f in global_vals if isinstance(f, HTTPHeaderField)]
    RESPONSE_FIELDS = [f for f in ALL_FIELDS if f.http_name in RESPONSE]
    REQUEST_FIELDS = [f for f in ALL_FIELDS if f.http_name in REQUEST]


date = HTTPHeaderField('date',
                       from_bytes=parse_http_date,
                       to_bytes=serialize_http_date,
                       native_type=datetime)

last_modified = HTTPHeaderField('last_modified',
                                from_bytes=parse_http_date,
                                to_bytes=serialize_http_date,
                                native_type=datetime)

expires = HTTPHeaderField('expires',
                          from_bytes=parse_http_date,
                          to_bytes=serialize_http_date,
                          native_type=datetime)

content_language = HTTPHeaderField('content_language',
                                   from_bytes=parse_list_header,
                                   to_bytes=serialize_list_header,
                                   native_type=list)


_init_field_lists()
del _init_field_lists
