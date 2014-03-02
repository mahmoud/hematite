import pytest
from ransom.http_parser.ex import headers as h


@pytest.mark.parametrize('input,output',
                         [('HTTP/1.1', (1, 1)),
                          ('HTTP/1234.56789', (1234, 56789))])
def test_HTTPVersion_parsebytes(input, output):
    assert h.HTTPVersion.parsebytes(input) == ('', output)


@pytest.mark.parametrize('output,input',
                         test_HTTPVersion_parsebytes.parametrize.args[-1])
def test_HTTPVersion_asbytes(input, output):
    assert bytes(h.HTTPVersion(*input)) == output


@pytest.mark.parametrize('input',
                         [(''),
                          ('http/1.1'),
                          ('HTTP/a.b')])
def test_HTTPVersion_parsebytes_badversions(input):
    unadvanced, exc = h.HTTPVersion.parsebytes(input)
    assert unadvanced == input
    assert isinstance(exc, h.BadVersion)


def test_google(file_fixture):

    with file_fixture('google.txt') as f:
        f.read()
