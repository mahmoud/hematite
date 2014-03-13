# -*- coding: utf-8 -*-

from ransom.request import Request


def test_request_basic():
    req = Request()
    print repr(req.to_bytes())
