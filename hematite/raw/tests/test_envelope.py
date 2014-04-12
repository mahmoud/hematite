from hematite.raw import envelope as e
from hematite.url import URL
import hematite.raw.core as core
import pytest


@pytest.mark.parametrize('input,output',
                         [(b'HTTP/1.1', (1, 1)),
                          (b'HTTP/1234.56789', (1234, 56789))])
def test_HTTPVersion_from_bytes(input, output):
    m = e.HTTPVersion.PARSE_VERSION.match(input)
    assert e.HTTPVersion.from_match(m) == output


@pytest.mark.parametrize('output,input',
                         test_HTTPVersion_from_bytes.parametrize.args[-1])
def test_HTTPVersion_to_bytes(input, output):
    assert bytes(e.HTTPVersion(*input)) == output


@pytest.mark.parametrize(
    'input,output',
    [(b'HTTP/1.1 301 Moved Permanently\r\n', ((1, 1), 301,
                                              b'Moved Permanently')),
     (b'HTTP/1.1 200\r\n', ((1, 1), 200, 'OK')),
     (b'HTTP/1.0 404 Not Found\n', ((1, 0), 404, b'Not Found')),
     (b'HTTP/1.1 500 Some thing\r\n', ((1, 1), 500, b'Some thing'))])
def test_StatusLine_sendline(input, output):
    assert e.StatusLine.from_bytes(input) == output


@pytest.mark.parametrize(
    'input,output',
    [((e.HTTPVersion(1, 1),
       301, 'Moved Permanently'), b'HTTP/1.1 301 Moved Permanently\r\n'),
     ((e.HTTPVersion(1, 1), 200, None), b'HTTP/1.1 200 OK\r\n'),
     ((e.HTTPVersion(1, 1), 200, ''), b'HTTP/1.1 200\r\n')])
def test_StatusLine_to_bytes_and_iterlines(input, output):
    bytes(e.StatusLine(*input)) == output
    e.StatusLine(*input).to_bytes() == output


@pytest.mark.parametrize(
    'input,exc_type',
    [(b'hTTP/1.1 404 Not Found\r\n', e.InvalidStatusLine),
     (b'HTTP/1.1 xxx\r\n', e.InvalidStatusLine),
     (b'HTTP/1.0 200 OK\x00\r\n', e.InvalidStatusLine)])
def test_StatusLine_exc(input, exc_type):
    with pytest.raises(exc_type):
        e.StatusLine.from_bytes(input)


def test_Headers_from_bytes():
    h = e.Headers.from_bytes(b'Host: some host\r\n'
                             b'Content-Type: text/plain;charset=utf-8\r\n'
                             b'\r\n')
    assert h == e.Headers([(b'Host', b'some host'),
                           (b'Content-Type', b'text/plain;charset=utf-8')])


def test_Headers_to_bytes():
    h = e.Headers({b'Host': b'some host',
                   b'Content-Type': b'text/plain;charset=utf-8'})
    expected = (b'Host: some host\r\n'
                b'Content-Type: text/plain;charset=utf-8\r\n'
                b'\r\n')
    assert h.to_bytes() == expected
    assert bytes(h) == expected


def test_Headers_maxheaders(monkeypatch):
    monkeypatch.setattr(core, 'MAXHEADERBYTES', 31)
    headers = e.Headers()
    too_long = 'a' * 32
    with pytest.raises(e.InvalidHeaders):
        headers.from_bytes(too_long)


def test_RequestEnvelope_from_bytes():
    r = e.RequestEnvelope.from_bytes(b'GET http://www.some.com HTTP/1.1\r\n'
                                     b'TE: deflate\r\n'
                                     b'Content-Length: 1234\r\n'
                                     b'\r\n')

    assert r.request_line == e.RequestLine(method=b'GET',
                                           url=URL(u'http://www.some.com'),
                                           version=e.HTTPVersion(1, 1))

    assert r.headers == e.Headers([(b'TE', b'deflate'),
                                   (b'Content-Length', b'1234')])


def test_ResponseEnvelope_from_bytes():
    r = e.ResponseEnvelope.from_bytes(b'HTTP/1.1 200 OK\r\n'
                                      b'Transfer-Encoding: deflate\r\n'
                                      b'Connection: close\r\n'
                                      b'\r\n')

    assert r.status_line == e.StatusLine(version=e.HTTPVersion(1, 1),
                                         status_code=200,
                                         reason=b'OK')

    assert r.headers == e.Headers([(b'Transfer-Encoding', b'deflate'),
                                   (b'Connection', b'close')])
