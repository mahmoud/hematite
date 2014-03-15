# -*- coding: utf-8 -*-

from datetime import datetime
from hematite.request import Request


def test_request_basic():
    req = Request(url='//google.com')
    assert req.host == 'google.com'
    assert req._url.path == '/'
    req_str = req.to_bytes()
    print repr(req_str)
    assert 'Host:' in req_str
    #import pdb;pdb.set_trace()


def test_request_rt():
    raw_req_lines = ('GET /wiki/Main_Page HTTP/1.1',
                     'Host: en.wikipedia.org',
                     'Connection: keep-alive',
                     'Cache-Control: max-age=0',
                     'Accept: text/html,application/xhtml+xml,*/*;q=0.9',
                     'User-Agent: Mozilla/3000.0 (X11; Linux x86_64)',
                     'Accept-Encoding: gzip,deflate',
                     'Accept-Language: en-US,en;q=0.8',
                     'If-Modified-Since: Sat, 15 Mar 2014 18:41:58 GMT',
                     '', '')  # required to get trailing CRLF
    raw_req_bytes = '\r\n'.join(raw_req_lines)
    req = Request.from_bytes(raw_req_bytes)
    assert req.host == 'en.wikipedia.org'
    assert req.path == '/wiki/Main_Page'
    assert req.version == (1, 1)
    assert req.if_modified_since < datetime.utcnow()
    rt_req_bytes = req.to_bytes()
    assert raw_req_bytes == rt_req_bytes


def test_path_field():
    req = Request(url='http://blog.hatnote.com/post/74043483777')
    assert req.path == '/post/74043483777'
    req.path = None
    assert req.path == '/'


def test_port_field():
    req = Request(url='http://hatnote.com:9000/')
    assert req.port == 9000
    req.port = None
    assert req.port == ''
    assert req.url == 'http://hatnote.com/'


def test_args_fields():
    req = Request(url='http://hatnote.com?hat=note&bat=quote')
    assert req.args['hat'] == 'note'
    assert req.args.get('nope') is None
    assert req.query_string == 'hat=note&bat=quote'

    req.args = None
    assert len(req.args) == 0
    req.query_string = u''
    assert len(req.query_string) == 0
    assert '?' not in req.url


def test_accept_header():
    acc_str = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    req = Request()
    req.accept = acc_str
    acc_dict = dict(req.accept)
    assert acc_dict['text/html'] == 1
    req_bytes = req.to_bytes()
    assert acc_str in req_bytes


def test_accept_encoding_header():
    acc_enc_str = 'gzip,deflate;q=0.9'
    req = Request()
    req.accept_encoding = acc_enc_str
    acc_dict = dict(req.accept_encoding)
    assert acc_dict['gzip'] == 1
    assert acc_dict['deflate'] == 0.9
    req_bytes = req.to_bytes()
    assert acc_enc_str in req_bytes


def test_accept_language_header():
    acc_lang_str = 'en-US,en;q=0.8'
    req = Request()
    req.accept_language = acc_lang_str
    acc_dict = dict(req.accept_language)
    assert acc_dict['en-US'] == 1
    assert acc_dict['en'] == 0.8
    req_bytes = req.to_bytes()
    assert acc_lang_str in req_bytes
