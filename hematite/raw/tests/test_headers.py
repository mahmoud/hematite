from hematite.raw import headers as h
import hematite.raw.core as core
import io
import pytest


@pytest.mark.parametrize('input,output',
                         [('HTTP/1.1', (1, 1)),
                          ('HTTP/1234.56789', (1234, 56789))])
def test_HTTPVersion_from_bytes(input, output):
    m = h.HTTPVersion.PARSE_VERSION.match(input)
    assert h.HTTPVersion.from_match(m) == output


@pytest.mark.parametrize('output,input',
                         test_HTTPVersion_from_bytes.parametrize.args[-1])
def test_HTTPVersion_to_bytes(input, output):
    assert bytes(h.HTTPVersion(*input)) == output


@pytest.mark.parametrize(
    'input,output',
    [('HTTP/1.1 301 Moved Permanently\r\n', ((1, 1), 301,
                                             'Moved Permanently')),
     ('HTTP/1.1 200\r\n', ((1, 1), 200, 'OK')),
     ('HTTP/1.0 404 Not Found\n', ((1, 0), 404, 'Not Found')),
     ('HTTP/1.1 500 Some thing\r\n', ((1, 1), 500, 'Some thing'))])
def test_StatusLine_sendline(input, output):
    assert h.StatusLine.from_io(io.BytesIO(input)) == output


@pytest.mark.parametrize(
    'input,output',
    [((h.HTTPVersion(1, 1),
       301, 'Moved Permanently'), 'HTTP/1.1 301 Moved Permanently\r\n'),
     ((h.HTTPVersion(1, 1), 200, None), 'HTTP/1.1 200 OK\r\n'),
     ((h.HTTPVersion(1, 1), 200, ''), 'HTTP/1.1 200\r\n')])
def test_StatusLine_to_bytes_and_iterlines(input, output):
    h.StatusLine(*input).to_bytes == output
    bytes_io = io.BytesIO()
    h.StatusLine(*input).to_io(bytes_io)
    assert bytes_io.getvalue() == output


@pytest.mark.parametrize(
    'input,exc_type',
    [('hTTP/1.1 404 Not Found\r\n', h.InvalidStatusLine),
     ('HTTP/1.1 xxx\r\n', h.InvalidStatusLine),
     ('HTTP/1.0 200 OK\x00\r\n', h.InvalidStatusLine)])
def test_StatusLine_exc(input, exc_type):
    bytes_io = io.BytesIO(input)
    with pytest.raises(exc_type):
        h.StatusLine.from_io(bytes_io)


def test_Headers_maxheaders(monkeypatch):
    monkeypatch.setattr(core, 'MAXHEADERBYTES', 31)
    headers = h.Headers()
    bytes_io = io.BytesIO('a' * 32)
    with pytest.raises(core.EndOfStream):
        headers.from_io(bytes_io)


def test_Headers_missing_clrf_terminates():
    headers = h.Headers()
    bytes_io = io.BytesIO('')
    with pytest.raises(core.EndOfStream):
        headers.from_io(bytes_io)
