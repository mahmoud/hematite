"""
Next steps:
 - translate the tests so that they comply with Hematite's URL
   - path and query string autounquoting
   - relative paths autoresolution
 - add more positive tests (all of the tests below are for valid urls)
 - add negative tests
"""

from hematite.url import URL


TEST_DATA = u"""\
# Based on https://github.com/w3c/web-platform-tests/blob/master/url/urltestdata.txt
# which is based on http://trac.webkit.org/browser/trunk/LayoutTests/fast/url/

#http://example.com/././foo about:blank s:http h:example.com p:/foo  # not sure what the about:blank is about.
http://example.com/./.foo  s:http h:example.com p:/.foo
http://example.com/foo/.  s:http h:example.com p:/foo/
http://example.com/foo/./  s:http h:example.com p:/foo/
http://example.com/foo/bar/..  s:http h:example.com p:/foo/
http://example.com/foo/bar/../  s:http h:example.com p:/foo/
http://example.com/foo/..bar  s:http h:example.com p:/foo/..bar
http://example.com/foo/bar/../ton  s:http h:example.com p:/foo/ton
http://example.com/foo/bar/../ton/../../a  s:http h:example.com p:/a
http://example.com/foo/../../..  s:http h:example.com p:/
http://example.com/foo/../../../ton  s:http h:example.com p:/ton
http://example.com/foo/%2e  s:http h:example.com p:/foo/
http://example.com/foo/%2e%2  s:http h:example.com p:/foo/%2e%2
http://example.com/foo/%2e./%2e%2e/.%2e/%2e.bar  s:http h:example.com p:/%2e.bar
http://example.com////../..  s:http h:example.com p://
http://example.com/foo/bar//../..  s:http h:example.com p:/foo/
http://example.com/foo/bar//..  s:http h:example.com p:/foo/bar/
http://example.com/foo  s:http h:example.com p:/foo
http://example.com/%20foo  s:http h:example.com p:/%20foo
http://example.com/foo%  s:http h:example.com p:/foo%
http://example.com/foo%2  s:http h:example.com p:/foo%2
http://example.com/foo%2zbar  s:http h:example.com p:/foo%2zbar
http://example.com/foo%2\u00C2\u00A9zbar  s:http h:example.com p:/foo%2%C3%82%C2%A9zbar
http://example.com/foo%41%7a  s:http h:example.com p:/foo%41%7a
#http://example.com/foo\t\u0091%91  s:http h:example.com p:/foo%C2%91%91  # 91 is an invalid utf8 starting byte so %91 decoding fails.
http://example.com/foo%00%51  s:http h:example.com p:/foo%00%51
http://example.com/(%28:%3A%29)  s:http h:example.com p:/(%28:%3A%29)
http://example.com/%3A%3a%3C%3c  s:http h:example.com p:/%3A%3a%3C%3c
http://example.com/foo\tbar  s:http h:example.com p:/foobar
http://example.com\\\\foo\\\\bar  s:http h:example.com p://foo//bar
http://example.com/%7Ffp3%3Eju%3Dduvgw%3Dd  s:http h:example.com p:/%7Ffp3%3Eju%3Dduvgw%3Dd
http://example.com/@asdf%40  s:http h:example.com p:/@asdf%40
http://example.com/\u4F60\u597D\u4F60\u597D  s:http h:example.com p:/%E4%BD%A0%E5%A5%BD%E4%BD%A0%E5%A5%BD
http://example.com/\u2025/foo  s:http h:example.com p:/%E2%80%A5/foo
http://example.com/\uFEFF/foo  s:http h:example.com p:/%EF%BB%BF/foo
http://example.com/\u202E/foo/\u202D/bar  s:http h:example.com p:/%E2%80%AE/foo/%E2%80%AD/bar
"""

RES_FIELD_MAP = {'s': 'scheme',
                 'h': 'host',
                 'p': 'path',
                 'port': 'port',
                 'q': 'query',
                 'f': 'fragment'}


def parse_test(test_str):
    input_str, _, result_str = test_str.partition('  ')
    if not result_str:
        return None  # failed test or invalid format
    rfs = result_str.split()
    results = {}  # 'scheme': rfs[0]}
    for field in rfs:
        name, _, value = field.partition(':')
        results[RES_FIELD_MAP[name]] = value
    results['input'] = input_str
    return results


def run_url_tests(data=TEST_DATA):
    for line in TEST_DATA.splitlines():
        if not line or line.startswith('#'):
            continue

        parsed_test = parse_test(line)
        url = URL(parsed_test['input'])
        print parsed_test, url
        for k, v in parsed_test.items():
            if k == 'input':
                continue
            url_value = getattr(url, k, None)
            if url_value is not None:
                print '-', k, v, url_value


if __name__ == '__main__':
    run_url_tests()
