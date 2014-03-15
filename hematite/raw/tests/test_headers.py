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
def test_StatusLine_from_io(input, output):
    io_obj = io.BytesIO(input)
    assert h.StatusLine.from_io(io_obj) == output


@pytest.mark.parametrize(
    'input,output',
    [((h.HTTPVersion(1, 1),
       301, 'Moved Permanently'), 'HTTP/1.1 301 Moved Permanently\r\n'),
     ((h.HTTPVersion(1, 1), 200, None), 'HTTP/1.1 200 OK\r\n'),
     ((h.HTTPVersion(1, 1), 200, ''), 'HTTP/1.1 200\r\n')])
def test_StatusLine_to_bytes_and_to_io(input, output):
    sl = h.StatusLine(*input)
    assert bytes(sl) == output
    io_obj = io.BytesIO()
    sl.to_io(io_obj)
    assert io_obj.getvalue() == output


@pytest.mark.parametrize(
    'input,exc_type',
    [('hTTP/1.1 404 Not Found\r\n', h.InvalidStatusLine),
     ('HTTP/1.1 xxx\r\n', h.InvalidStatusLine),
     ('HTTP/1.0 200 OK\x00\r\n', h.InvalidStatusLine)])
def test_StatusLine_exc(input, exc_type):
    io_obj = io.BytesIO(input)
    with pytest.raises(exc_type):
        h.StatusLine.from_io(io_obj)


def test_Headers_maxheaders(monkeypatch):
    monkeypatch.setattr(core, 'MAXHEADERBYTES', 31)
    with pytest.raises(h.InvalidHeaders):
        h.Headers.from_io(io.BytesIO('a' * 32))


def test_Headers_missing_clrf_terminates():
    with pytest.raises(h.InvalidHeaders):
        h.Headers.from_io(io.BytesIO('One\r\n\Two\r\n'))
