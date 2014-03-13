# -*- coding: utf-8 -*-

#from compat import unicode, bytes

# TODO: round-tripping tests

import pytest

from ransom.url import URL, _URL_RE, parse_authority


TEST_URLS = [
    'http://googlewebsite.com/e-shops.aspx',
    'http://example.com:8080/search?q=123&business=Nothing%20Special',
    'http://hatnote.com:9000?arg=1&arg=2&arg=3',
    'https://xn--bcher-kva.ch',
    'http://tools.ietf.org/html/rfc3986#section-3.4',
    'http://wiki:pedia@hatnote.com',
    'ftp://ftp.rfc-editor.org/in-notes/tar/RFCs0001-0500.tar.gz',
    'http://[1080:0:0:0:8:800:200C:417A]/index.html',
    'ssh://192.0.2.16:22/',
    'https://[::101.45.75.219]:80/?hi=bye',
    'ldap://[::192.9.5.5]/dc=example,dc=com??sub?(sn=Jensen)',
    'mailto:me@example.com?to=me@example.com&body=hi%20http://wikipedia.org',
    'news:alt.rec.motorcycle',
    'tel:+1-800-867-5309',
    'urn:oasis:member:A00024:x']


UNICODE_URLS = [
    # 'http://مثال.آزمایشی'
    ('\xd9\x85\xd8\xab\xd8\xa7\xd9\x84'
     '.\xd8\xa2\xd8\xb2\xd9\x85\xd8\xa7'
     '\xdb\x8c\xd8\xb4\xdb\x8c')]


@pytest.fixture(scope="module", params=TEST_URLS)
def test_url(request):
    param = request.param
    #request.addfinalizer(lambda: None)
    return param


@pytest.fixture(scope="module", params=TEST_URLS)
def test_authority(request):
    match = _URL_RE.match(request.param)
    return match.groupdict()['authority']


def test_regex(test_url):
    match = _URL_RE.match(test_url)
    assert match.groupdict()


def test_parse_authorities(test_authority):
    if not test_authority:
        return True
    else:
        _, _, family, host, port = parse_authority(test_authority)
        assert bool(host)  # TODO


def test_basic():
    u1 = URL('http://googlewebsite.com/e-shops.aspx')
    assert isinstance(u1.to_text(), unicode)
    assert u1.host == 'googlewebsite.com'


def test_idna():
    u1 = URL('http://xn--bcher-kva.ch')
    assert u1.host == u'bücher.ch'


def test_urlparse_equiv(test_url):
    from urlparse import urlparse, urlunparse
    url_obj = URL(test_url)
    assert urlunparse(urlparse(test_url)) == urlunparse(url_obj)


def test_query_params(test_url):
    url_obj = URL(test_url)
    if not url_obj.args:
        return True
    assert test_url.endswith(url_obj.query_string)
