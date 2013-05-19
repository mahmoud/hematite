# -*- coding: utf-8 -*-

#from compat import unicode, bytes

# TODO: round-tripping tests

import pytest

from url import URL, _URL_RE


TEST_URLS = [
    'http://googlewebsite.com/e-shops.aspx',
    'http://example.com:8080/search?q=123&business=Nothing%20Special',
    'https://xn--bcher-kva.ch',
    'http://tools.ietf.org/html/rfc3986#section-3.4',
    'ftp://ftp.rfc-editor.org/in-notes/tar/RFCs0001-0500.tar.gz',
    'http://[1080:0:0:0:8:800:200C:417A]/index.html',
    'ssh://192.0.2.16:22/',
    'https://::101.45.75.219/?hi=bye',
    'ldap://[::192.9.5.5]/dc=example,dc=com??sub?(sn=Jensen)',
    'mailto:me@example.com?to=me@example.com&body=hi%20http://wikipedia.org',
    'news:alt.rec.motorcycle',
    'tel:+1-800-867-5309',
    'urn:oasis:member:A00024:x']


@pytest.fixture(scope="module", params=TEST_URLS)
def test_url(request):
    param = request.param
    #request.addfinalizer(lambda: None)
    return param


def test_regex(test_url):
    match = _URL_RE.match(test_url)
    assert match.groupdict()


def test_basic():
    u1 = URL('http://googlewebsite.com/e-shops.aspx')
    assert u1.hostname == 'googlewebsite.com'


def test_idna():
    u1 = URL('http://xn--bcher-kva.ch')
    assert u1.hostname == u'bücher.ch'
