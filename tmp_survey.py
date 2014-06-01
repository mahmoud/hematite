
from hematite.url import URL
from hematite.async import join
from hematite.client import Client
from hematite.profile import HematiteProfile
from hematite.request import Request


def get_sites(filename, count):
    count = int(count)
    ret = []
    with open(filename) as f:
        for i, line in enumerate(f):
            if i > count:
                break
            ret.append(line.partition(',')[2].strip())
    return ret


def do_survey(count):
    results = []
    sites = get_sites('top_10k.csv', count)
    client = Client()
    for site in sites:
        print '------------'
        res = client.get('http://' + site + '/')
        if is_supported_redirect(res.response.status_code):
            res = follow_next_redirect(res)
        print res.raw_response
        results.append(res)
    print 'done'


def is_supported_redirect(status_code):
    return 300 < status_code < 309


def follow_next_redirect(client_resp):
    rreq = client_resp.raw_request
    resp = client_resp.response
    status_code = resp.status_code

    if not is_supported_redirect(status_code):
        raise ValueError('not followable')

    # get new method
    if status_code in (301, 302, 303):
        new_method = 'HEAD' if rreq.method == 'HEAD' else 'GET'
    elif status_code in (307, 308):
        raise ValueError()

    # get new url
    new_url = resp.location
    if not new_url:
        raise ValueError('no new location in redirect')
    new_url = URL(resp.location.to_bytes())
    if not new_url.is_absolute:
        new_url.scheme = rreq.host_url.scheme
        new_url.host = rreq.host_url.host
        new_url.port = rreq.host_url.port
    print rreq.host_url, status_code, '->', new_method, new_url

    # build new request with remaining headers
    # (usually this would include filtering cookies and auth)
    new_req = Request(method=new_method, url=new_url)
    print new_req.to_raw_request()

    return client_resp.client.request(request=new_req)


def main():
    import argparse

    a = argparse.ArgumentParser()
    a.add_argument('--top-n', '-n', type=int, default=10)
    a.add_argument('--output', '-o', default=None,
                   help='path to output file: "-" means stdout')
    args = a.parse_args()
    do_survey(args.top_n)


if __name__ == '__main__':
    main()
