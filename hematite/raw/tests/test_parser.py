import pytest

from hematite.url import URL
from hematite.raw import parser as P
from hematite.raw import messages as M
from itertools import izip


@pytest.mark.parametrize('input,expected',
                         [('HTTP/0.9', P.HTTPVersion(0, 9)),
                          ('HTTP/1.0', P.HTTPVersion(1, 0)),
                          ('HTTP/1.1', P.HTTPVersion(1, 1)),
                          ('HTTP/2.0', P.HTTPVersion(2, 0))])
def test_HTTPVersion_froms(input, expected):
    """HTTPVersion.from_* should parse valid HTTP versions."""

    assert P.HTTPVersion.from_bytes(input) == expected
    m = P.HTTPVersion.PARSE_VERSION.match(input)
    assert P.HTTPVersion.from_match(m) == expected


@pytest.mark.parametrize('input,expected',
                         [('HTTP1/.a', P.InvalidVersion),
                          ('SDF1/1', P.InvalidVersion)])
def test_HTTPVersion_froms_raises(input, expected):
    """HTTPVersion.from_* should fail to parse invalid HTTP versions."""

    with pytest.raises(expected):
        P.HTTPVersion.from_bytes(input)

    with pytest.raises(expected):
        m = P.HTTPVersion.PARSE_VERSION.match(input)
        P.HTTPVersion.from_match(m)


@pytest.mark.parametrize('input,expected',
                         [(P.HTTPVersion(major=0, minor=9), 'HTTP/0.9'),
                          (P.HTTPVersion(major=1, minor=0), 'HTTP/1.0'),
                          (P.HTTPVersion(major=1, minor=1), 'HTTP/1.1'),
                          (P.HTTPVersion(major=2, minor=0), 'HTTP/2.0')])
def test_HTTPVersion_to_bytes(input, expected):
    """HTTPVersion.to_bytes should generate a valid HTTP Version."""

    assert bytes(input) == expected
    assert input.to_bytes() == expected


def test_HTTPVersion_round_trip():
    """HTTPVersion.from_* should parse the output of HTTPVersion.to_bytes"""

    expected = P.HTTPVersion(1, 1)
    assert P.HTTPVersion.from_bytes(expected.to_bytes()) == expected


@pytest.mark.parametrize(
    'input,expected',
    [('HTTP/1.1 200 OK\n',
      P.StatusLine(P.HTTPVersion(1, 1), 200, 'OK')),

     ('HTTP/1.1 200 OK\r\n',
      P.StatusLine(P.HTTPVersion(1, 1), 200, 'OK')),

     ('HTTP/1.0 404 Not Found\r\n',
      P.StatusLine(P.HTTPVersion(1, 0), 404, 'Not Found')),

     ('HTTP/1.1 500\r\n',
      P.StatusLine(P.HTTPVersion(1, 1), 500, 'Internal Server Error')),

     ('HTTP/1.1 500 Something went wrong\r\n',
      P.StatusLine(P.HTTPVersion(1, 1), 500, 'Something went wrong'))])
def test_StatusLine_froms(input, expected):
    """StatusLine.from_* should parse valid Status Lines, with or without
    reasons."""
    assert P.StatusLine.from_bytes(input) == expected
    m = P.StatusLine.PARSE_STATUS_LINE.match(input)
    assert P.StatusLine.from_match(m) == expected


@pytest.mark.parametrize(
    'input,expected',
    [('HTTP/1.1  OK\r\n', P.InvalidStatusCode),

     ('HTTP/Wrong 200 OK\r\n', P.InvalidVersion),

     ('Completely unparseable\r\n', P.InvalidStatusLine)])
def test_StatusLine_froms_raises(input, expected):
    """StatusLine.from_* should fail to parse invalid status lines."""
    with pytest.raises(expected):
        P.StatusLine.from_bytes(input)

    with pytest.raises(expected):
        P.StatusLine.from_match(P.StatusLine.PARSE_STATUS_LINE.match(input))


@pytest.mark.parametrize(
    'input,expected',
    [(P.StatusLine(version=P.HTTPVersion(major=1, minor=1),
                   status_code=200,
                   reason='OK'),
      'HTTP/1.1 200 OK\r\n'),

     (P.StatusLine(version=P.HTTPVersion(major=1, minor=0),
                   status_code=404,
                   reason='Not Found'),
      'HTTP/1.0 404 Not Found\r\n'),

     (P.StatusLine(version=P.HTTPVersion(major=1, minor=1),
                   status_code=500,
                   reason=''),
      'HTTP/1.1 500\r\n'),

     (P.StatusLine(version=P.HTTPVersion(major=1, minor=1),
                   status_code=500,
                   reason=None),
      'HTTP/1.1 500 Internal Server Error\r\n'),

     (P.StatusLine(version=P.HTTPVersion(major=1, minor=1),
                   status_code=500,
                   reason='Something went wrong'),
      'HTTP/1.1 500 Something went wrong\r\n')])
def test_StatusLine_to_bytes(input, expected):
    """StatusLine.to_bytes should generate valid status lines."""
    assert bytes(input) == expected
    assert input.to_bytes() == expected


def test_StatusLine_round_trip():
    """StatusLine.from_* should parse the output of StatusLine.to_bytes"""

    expected = P.StatusLine(P.HTTPVersion(1, 1), 200, 'OK')
    assert P.StatusLine.from_bytes(expected.to_bytes()) == expected


@pytest.mark.parametrize(
    'input,expected',
    [('GET / HTTP/1.1',
      P.RequestLine('GET', URL('/'), P.HTTPVersion(1, 1))),

     ('POST http://www.site.com/something?q=abcd HTTP/1.0',
      P.RequestLine(method='POST',
                    url=URL(u'http://www.site.com/something?q=abcd'),
                    version=P.HTTPVersion(major=1, minor=0))),

     ('OPTIONS */* HTTP/1.1',
      P.RequestLine(method='OPTIONS',
                    url=URL(u'*/*'),
                    version=P.HTTPVersion(major=1, minor=1)))])
def test_RequestLine_froms(input, expected):
    """RequestLine.from_* should parse valid request lines."""

    assert P.RequestLine.from_bytes(input) == expected
    matched = P.RequestLine.PARSE_REQUEST_LINE.match(input)
    assert P.RequestLine.from_match(matched) == expected


@pytest.mark.parametrize('input,expected',
                         [(' / HTTP/1.1', P.InvalidMethod),
                          ('GET ` HTTP/1.1', P.InvalidURI),
                          ('!!CompletelyWrong!!', P.InvalidRequestLine)])
def test_RequestLine_froms_raises(input, expected):
    """RequestLine.froms_* should fail to parse invalid request lines."""

    with pytest.raises(expected):
        P.RequestLine.from_bytes(input)

    with pytest.raises(expected):
        m = P.RequestLine.PARSE_REQUEST_LINE.match(input)
        P.RequestLine.from_match(m)


@pytest.mark.parametrize(
    'input,expected',
    [(P.RequestLine(method='GET',
                    url=URL(u'/'),
                    version=P.HTTPVersion(major=1, minor=1)),
      'GET / HTTP/1.1'),

     (P.RequestLine(method='POST',
                    url=URL(u'http://www.site.com/something?q=abcd'),
                    version=P.HTTPVersion(major=1, minor=0)),
      'POST http://www.site.com/something?q=abcd HTTP/1.0'),

     (P.RequestLine(method='OPTIONS',
                    url=URL(u'*/*'),
                    version=P.HTTPVersion(major=1, minor=1)),
      'OPTIONS */* HTTP/1.1')])
def test_RequestLine(input, expected):
    """RequestLine.to_bytes should generate valid request lines."""

    assert bytes(input) == expected
    assert input.to_bytes() == expected


def test_RequestLine_round_trip():
    """RequestLine.from_* should parse the output of RequestLine.to_bytes"""

    expected = P.RequestLine(method='OPTIONS', url=URL(u'*/*'),
                             version=P.HTTPVersion(1, 1))

    assert P.RequestLine.from_bytes(expected.to_bytes()) == expected


def test_HeadersParser_reader_writer():
    lines = ['Host: www.org.com\n',
             'Content-Encoding: chunked,\r\n',
             '  irrelevant\n',
             'Accept: text/plain\r\n',
             'Accept: text/html\n']

    expected_lines = ['Host: www.org.com\r\n',
                      'Content-Encoding: chunked,  irrelevant\r\n',
                      'Accept: text/plain\r\n',
                      'Accept: text/html\r\n',
                      '\r\n']

    parser = P.HeadersParser()
    repr(parser)

    assert parser.writer is None
    assert parser.reader is None
    assert parser.state is M.Empty

    parser.begin_reading()
    assert parser.writer is None

    with pytest.raises(P.ConflictingStateError):
        parser.begin_writing()

    for line in lines:
        state = parser.reader.send(M.HaveLine(line))
        assert state is M.NeedLine
        assert parser.state is state

    state = parser.reader.send(M.HaveLine('\n'))
    assert state is M.Complete
    assert parser.state is state
    assert parser.complete

    parser.begin_writing()
    assert parser.reader is None
    assert parser.state is M.Empty

    with pytest.raises(P.ConflictingStateError):
        parser.begin_reading()

    for message, expected in izip(parser.writer, expected_lines):
        t, actual = message
        assert t == M.HaveLine.type
        assert parser.state is message
        assert actual == expected

    assert parser.complete
