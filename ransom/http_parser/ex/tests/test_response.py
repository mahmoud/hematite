import io
from ransom.http_parser.ex import response as r


def io_open(path):
    return io.open(path, mode='rb')


def test_Response_from_bytes_with_google(file_fixture):

    with file_fixture('google.txt', open=io_open) as f:
        resp = r.Response.from_io(f)

        assert resp.status_line == ((1, 1), 301, 'Moved Permanently')

        expected_headers = [('location', 'http://www.google.com/'),
                            ('content-type', 'text/html; charset=UTF-8'),
                            ('date', 'Sat, 01 Mar 2014 23:10:17 GMT'),
                            ('expires', 'Mon, 31 Mar 2014 23:10:17 GMT'),
                            ('cache-control', 'public, max-age=2592000'),
                            ('server', 'gws'),
                            ('content-length', '219'),
                            ('x-xss-protection', '1; mode=block'),
                            ('x-frame-options', 'SAMEORIGIN'),
                            ('alternate-protocol', '80:quic'),
                            ('connection', 'close')]

        assert resp.headers.items() == expected_headers

        expected_body = (
            '<HTML><HEAD><meta http-equiv="content-type"'
            ' content="text/html;charset=utf-8">\n'
            '<TITLE>301 Moved</TITLE></HEAD><BODY>\n'
            '<H1>301 Moved</H1>\n'
            'The document has moved\n'
            '<A HREF="http://www.google.com/">here</A>.\r\n'
            '</BODY></HTML>'
            '\r\n')

        assert resp.body.read() == expected_body


def test_Response_to_bytes(file_fixture):
    with file_fixture('normalized_google_headers.txt',
                      open=io_open) as f:
        expected = io.BytesIO(f.read())
        actual = io.BytesIO()
        f.seek(0)
        r.Response.from_io(f).to_io(actual)
        assert expected.getvalue() == actual.getvalue()
