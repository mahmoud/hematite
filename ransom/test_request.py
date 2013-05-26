# -*- coding: utf-8 -*-

from request import Request

BASIC_REQ = ('GET /html/rfc3986 HTTP/1.1\r\n'
             'Host: tooxols.ietf.org\r\n'
             '\r\n')


def test_basic():
    req = Request.from_string(BASIC_REQ)
    assert req.encode() == BASIC_REQ


def test_basic_url():
    req = Request.from_string(BASIC_REQ)
    assert req.url.encode() == 'http://tooxols.ietf.org/html/rfc3986'
