# -*- coding: utf-8 -*-


from headers import HTTPHeaderField
from headers import parse_http_date, serialize_http_date

from datetime import datetime


class Response(object):
    # TODO: from_request convenience method?
    def __init__(self):
        # code (default 200), message (default looked up), headers, body
        pass

    date = HTTPHeaderField('date',
                           from_bytes=parse_http_date,
                           to_bytes=serialize_http_date,
                           native_type=datetime)

    def _get_header_dict(self):
        ret = {}
        # TODO: maintain header order
        self_type = type(self)
        for field in self._header_fields:
            _val = field.__get__(self, self_type)
            ret[field.http_name] = field.to_bytes(_val)
        return ret

    @classmethod
    def from_raw_response(cls, raw_resp):
        pass

    def to_raw_response(self):
        pass

    @classmethod
    def from_bytes(cls, bytestr):
        rr = object()  # RawResponse.from_bytes(bytestr)
        return cls.from_raw_response(rr)

    def to_bytes(self):
        rr = self.to_raw_response()
        return rr.to_bytes()

    def validate(self):
        pass


def main():
    resp = Response()
    resp.date = 'Sun, 06 Nov 1994 08:49:37 GMT'
    import pdb;pdb.set_trace()


if __name__ == '__main__':
    main()
