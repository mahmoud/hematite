# -*- coding: utf-8 -*-

from datetime import datetime

from headers import HTTPHeaderField
from headers import parse_http_date, serialize_http_date

from http_parser.ex.headers import StatusLine
from http_parser.ex.response import Response as RawResponse


class Response(object):
    # TODO: from_request convenience method?
    def __init__(self, status_code, body, **kw):
        self.status_code = status_code
        self.reason = kw.pop('reason', '')  # TODO look up
        self.headers = kw.pop('headers', {})  # TODO
        self.version = kw.pop('version', '1.1')  # TODO

        self._body = body

        # TODO: lots

    date = HTTPHeaderField('date',
                           from_bytes=parse_http_date,
                           to_bytes=serialize_http_date,
                           native_type=datetime)

    _header_fields = [date]  # class decorator that does this

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
        sl = raw_resp.status_line
        kw = {'status_code': sl.status_code,
              'reason': sl.reason,
              'version': sl.version,
              'headers': raw_resp.headers,
              'body': raw_resp.body}
        return cls(**kw)

    def to_raw_response(self):
        status_line = StatusLine(self.version, self.status_code, self.reason)
        header_dict = self._get_header_dict()
        return RawResponse(status_line, header_dict, self._body)

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
    resp = Response.from_raw_response()
    import pdb;pdb.set_trace()


if __name__ == '__main__':
    main()
