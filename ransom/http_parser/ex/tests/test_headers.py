import pytest
from ransom.http_parser.ex import headers as h


@pytest.mark.parametrize('input,output',
                         [('HTTP/1.1', (1, 1)),
                          ('HTTP/1234.56789', (1234, 56789))])
def test_HTTPVersion_from_bytes(input, output):
    assert h.HTTPVersion.from_bytes(input) == ('', output)


@pytest.mark.parametrize('output,input',
                         test_HTTPVersion_from_bytes.parametrize.args[-1])
def test_HTTPVersion_to_bytes(input, output):
    assert bytes(h.HTTPVersion(*input)) == output


@pytest.mark.parametrize('input',
                         [(''),
                          ('http/1.1'),
                          ('HTTP/a.b')])
def test_HTTPVersion_from_bytes_badversions(input):
    with pytest.raises(h.InvalidVersion):
        h.HTTPVersion.from_bytes(input)


@pytest.mark.parametrize(
    'input,output',
    [('HTTP/1.1 301 Moved Permanently\r\n', ((1, 1), 301,
                                             'Moved Permanently')),
     ('HTTP/1.1 200\r\n', ((1, 1), 200, 'OK')),
     ('HTTP/1.0 404 Not Found\n', ((1, 0), 404, 'Not Found')),
     ('HTTP/1.1 500 Some thing\r\n', ((1, 1), 500, 'Some thing'))])
def test_StatusLine_from_bytes(input, output):
    assert h.StatusLine.from_bytes(input) == ('', output)


@pytest.mark.parametrize(
    'input,output',
    [((h.HTTPVersion(1, 1),
       301, 'Moved Permanently'), 'HTTP/1.1 301 Moved Permanently\r\n'),
     ((h.HTTPVersion(1, 1), 200, None), 'HTTP/1.1 200 OK\r\n'),
     ((h.HTTPVersion(1, 1), 200, ''), 'HTTP/1.1 200\r\n')])
def test_StatusLine_to_bytes(input, output):
    assert bytes(h.StatusLine(*input)) == output


@pytest.mark.parametrize(
    'input,exc_type',
    [('hTTP/1.1 404 Not Found\r\n', h.InvalidVersion),
     ('HTTP/1.1 xxx\r\n', h.InvalidStatusCode),
     ('HTTP/1.0 200 OK\x00\r\n', h.InvalidStatusLine)])
def test_StatusLine_exc(input, exc_type):
    with pytest.raises(exc_type):
        h.StatusLine.from_bytes(input)
