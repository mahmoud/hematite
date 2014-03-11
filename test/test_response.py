
from ransom.response import Response
from ransom.http_parser.ex.response import Response as RawResponse


def test_resp_raw_resp():
    raw_resp_str = ('HTTP/1.1 200 OK\r\n'
                    'Date: Tue, 11 Mar 2014 06:29:33 GMT\r\n'
                    'Server: hatnote.com\r\n'
                    '\r\n')

    raw_resp = RawResponse.from_bytes(raw_resp_str)
    resp = Response.from_raw_response(raw_resp)
    the_bytes = resp.to_bytes()
    print
    print the_bytes
    print repr(the_bytes)

    the_bytes = the_bytes + '\r\n'  # TODO: mrw: FIXIFIFIXIIFIFX
    raw_resp_two = RawResponse.from_bytes(the_bytes)
    return the_bytes
