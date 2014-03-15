
from datetime import datetime

from hematite.response import Response
from hematite.raw.response import RawResponse


def test_resp_raw_resp():
    raw_resp_str = ('HTTP/1.1 200 OK\r\n'
                    'Date: Tue, 11 Mar 2014 06:29:33 GMT\r\n'
                    'Last-Modified: Mon, 10 Mar 2014 01:22:01 GMT\r\n'
                    'Server: hatnote.com\r\n'
                    'Expires: Tue, 11 Mar 2014 06:29:34 GMT\r\n'
                    'Content-Language: en, mi\r\n'
                    'X-Proprietary-Header: lol\r\n'
                    '\r\n')

    raw_resp = RawResponse.from_bytes(raw_resp_str)
    resp = Response.from_raw_response(raw_resp)
    assert isinstance(resp.date, datetime)
    assert isinstance(resp.content_language, list)
    the_bytes = resp.to_bytes()

    print repr(raw_resp_str)
    print repr(the_bytes)

    assert raw_resp_str == the_bytes


def test_cap_norm():
    raw_resp_str = ('HTTP/1.1 200 OK\r\n'
                    'Last-modified: Mon, 10 Mar 2014 01:22:01 GMT\r\n'
                    '\r\n')
    resp = Response.from_bytes(raw_resp_str)
    assert isinstance(resp.last_modified, datetime)
    resp_str = resp.to_bytes()

    assert 'Last-Modified' in resp_str
    assert len(resp_str) == len(raw_resp_str)


def test_proprietary_dupes():
    raw_resp_str = ('HTTP/1.1 200 OK\r\n'
                    'X-App: lol\r\n'
                    'X-App: lmao\r\n'
                    '\r\n')
    resp = Response.from_bytes(raw_resp_str)
    assert resp.headers['X-App'] == 'lmao'
    resp_str = resp.to_bytes()
    assert resp_str == raw_resp_str


def test_empty_header():
    raw_resp_str = ('HTTP/1.1 200 OK\r\n'
                    'X-Terrible-Header: \r\n'
                    '\r\n')
    resp = Response.from_bytes(raw_resp_str)
    assert resp.headers['X-Terrible-Header'] == ''
    resp_str = resp.to_bytes()
    assert 'X-Terrible' not in resp_str


def test_invalid_expires():
    import datetime
    raw_resp_str = ('HTTP/1.1 200 OK\r\n'
                    'Expires: -1\r\n'
                    '\r\n')
    resp = Response.from_bytes(raw_resp_str)
    assert resp.expires < datetime.datetime.utcnow()
    resp_str = resp.to_bytes()
    assert 'Expires' in resp_str


def test_status_reason():
    resp = Response(200)
    assert resp.reason == 'OK'
    resp = Response(500)
    assert resp.reason == 'Internal Server Error'
    resp = Response(9000)
    assert resp.reason == ''
