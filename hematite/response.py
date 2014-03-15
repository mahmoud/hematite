# -*- coding: utf-8 -*-

from hematite.raw.headers import StatusLine, Headers, HTTPVersion
from hematite.raw.response import RawResponse

from hematite import serdes
from hematite.fields import RESPONSE_FIELDS

_DEFAULT_VERSION = HTTPVersion(1, 1)


class Response(object):
    # TODO: from_request convenience method?
    def __init__(self, status_code, body, **kw):
        self.status_code = status_code
        self.reason = kw.pop('reason', '')  # TODO look up
        self._raw_headers = kw.pop('headers', Headers())  # TODO
        self.version = kw.pop('version', _DEFAULT_VERSION)

        self._body = body

        self._init_headers()
        # TODO: lots
        return

    # TODO: could use a metaclass for this, could also build it at init
    _header_field_map = dict([(hf.http_name, hf) for hf in RESPONSE_FIELDS])
    locals().update([(hf.attr_name, hf) for hf in RESPONSE_FIELDS])
    _init_headers = serdes._init_headers
    _get_header_dict = serdes._get_headers

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
        headers = self._get_header_dict()
        return RawResponse(status_line, headers, self._body)

    @classmethod
    def from_bytes(cls, bytestr):
        rr = RawResponse.from_bytes(bytestr)
        return cls.from_raw_response(rr)

    def to_bytes(self):
        rr = self.to_raw_response()
        return rr.to_bytes()

    def validate(self):
        pass


if __name__ == '__main__':
    main()
