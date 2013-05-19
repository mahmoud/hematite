# -*- coding: utf-8 -*-

#from compat import unicode, bytes


from url import URL


def test_basic():
    u1 = URL('http://googlewebsite.com/e-shops.aspx')
    assert u1.hostname == 'googlewebsite.com'


def test_idna():
    u2 = URL('http://xn--bcher-kva.ch')
    assert u2.hostname == u'bücher.ch'
