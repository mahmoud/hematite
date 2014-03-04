from ransom.http_parser.ex import response as r


def test_Response_parsebytes_with_google(file_fixture):

    with file_fixture('google.txt') as f:
        resp = r.Response.parsefrombytes(f.read())

    assert resp.status_line == ((1, 1), 301, 'Moved Permanently')

    expected_headers = [('Location', 'http://www.google.com/'),
                        ('Content-Type', 'text/html; charset=UTF-8'),
                        ('Date', 'Sat, 01 Mar 2014 23:10:17 GMT'),
                        ('Expires', 'Mon, 31 Mar 2014 23:10:17 GMT'),
                        ('Cache-Control', 'public, max-age=2592000'),
                        ('Server', 'gws'),
                        ('Content-Length', '219'),
                        ('X-Xss-Protection', '1; mode=block'),
                        ('X-Frame-Options', 'SAMEORIGIN'),
                        ('Alternate-Protocol', '80:quic'),
                        ('Connection', 'close')]

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

    assert resp.body == expected_body
