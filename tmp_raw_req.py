# -*- coding: utf-8 -*-

from hematite.raw import RawRequest, Headers

_GET_REQ_LINES = ('GET /wiki/Main_Page HTTP/1.1',
                  'Host: en.wikipedia.org',
                  'Connection: keep-alive',
                  'Cache-Control: max-age=0',
                  'From: mahmoud@hatnote.com',
                  'Referer: http://blog.hatnote.com/post/1',
                  'Accept: text/html,application/xhtml+xml,*/*;q=0.9',
                  'User-Agent: Mozilla/3000.0 (X11; Linux x86_64)',
                  'Accept-Encoding: gzip,deflate',
                  'Accept-Language: en-US,en;q=0.8',
                  'If-None-Match: W/"lolololol", "lmao"',
                  'If-Modified-Since: Sat, 15 Mar 2014 18:41:58 GMT',
                  '', '')  # required to get trailing CRLF
GET_REQ_BYTES = '\r\n'.join(_GET_REQ_LINES)


def main_write():
    rreq = RawRequest(headers=Headers({'AccepT': 'lol'}))
    print repr(rreq.to_bytes())
    print '------'
    print rreq.to_bytes()


def main():
    rreq = RawRequest.from_bytes(GET_REQ_BYTES)
    assert rreq.to_bytes() == GET_REQ_BYTES

if __name__ == '__main__':
    main()
