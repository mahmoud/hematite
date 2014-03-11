# -*- coding: utf-8 -*-

from datetime import datetime

from headers import HTTPHeaderField
from headers import parse_http_date, serialize_http_date


from http_parser.ex.headers import StatusLine, Headers, HTTPVersion
from http_parser.ex.response import Response as RawResponse

_DEFAULT_VERSION = HTTPVersion(1, 1)

class Response(object):
    # TODO: from_request convenience method?
    def __init__(self, status_code, body, **kw):
        self.status_code = status_code
        self.reason = kw.pop('reason', '')  # TODO look up
        self.headers = kw.pop('headers', Headers())  # TODO
        self.version = kw.pop('version', _DEFAULT_VERSION)

        self._body = body

        self._load_headers()
        # TODO: lots

    date = HTTPHeaderField('date',
                           from_bytes=parse_http_date,
                           to_bytes=serialize_http_date,
                           native_type=datetime)

    _header_fields = [date]  # class decorator that does this

    def _load_headers(self):
        # plenty of ways to arrange this
        hf_map = dict([(hf.http_name, hf) for hf in self._header_fields])
        for hname, hval in self.headers.items():
            # TODO: multi=True and folding
            try:
                field = hf_map[hname]  # TODO: normalization
            except KeyError:
                # TODO: extra_header_dict
                continue
            else:
                setattr(self, field.attr_name, hval)

    def _get_header_dict(self, drop_empty=True):
        ret = Headers()
        # TODO: maintain header order
        self_type = type(self)
        for field in self._header_fields:
            try:
                _val = field.__get__(self, self_type)
            except AttributeError:
                continue
            if drop_empty and _val is None:
                continue
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
        header_str = '\r\n'.join(['%s: %s' % (k, v) for k, v in header_dict.items()])
        return RawResponse(status_line, header_str, self._body)

    @classmethod
    def from_bytes(cls, bytestr):
        rr = object()  # RawResponse.from_bytes(bytestr)
        return cls.from_raw_response(rr)

    def to_bytes(self):
        rr = self.to_raw_response()
        return str(rr)

    def validate(self):
        pass


if __name__ == '__main__':
    main()
