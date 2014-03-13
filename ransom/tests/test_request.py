# -*- coding: utf-8 -*-

from ransom.request import Request


def test_request_basic():
    req = Request(url='//google.com')
    print repr(req.to_bytes())
    import pdb;pdb.set_trace()
