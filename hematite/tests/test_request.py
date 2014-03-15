# -*- coding: utf-8 -*-

from hematite.request import Request


def test_request_basic():
    req = Request(url='//google.com')
    assert req.host == 'google.com'
    assert req._url.path == '/'
    req_str = req.to_bytes()
    print repr(req_str)
    assert 'Host:' in req_str
    #import pdb;pdb.set_trace()


def test_req_path_field():
    req = Request(url='http://blog.hatnote.com/post/74043483777')
    assert req.path == '/post/74043483777'
    req.path = None
    assert req.path == '/'


def test_req_port_field():
    req = Request(url='http://hatnote.com:9000/')
    assert req.port == 9000
    req.port = None
    assert req.port == ''
    assert req.url == 'http://hatnote.com/'
