
from hematite.url import URL
from hematite.async import join
from hematite.client import Client, ConnectionError, RequestTimeout
from hematite.profile import HematiteProfile
from hematite.request import Request
from hematite.raw.core import EndOfStream

TIMEOUT = 15.0


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
        print '-------', site, '--------'
        try:
            res = do_single(client, site, timeout=TIMEOUT)
        except ConnectionError as ce:
            print 'Connection Error:', ce
        except RequestTimeout as rt:
            print 'Timeout', rt
        except EndOfStream as eos:
            print 'EndOfStream', eos
        results.append(res)
    print 'done'


def do_async_survey(count):
    sites = get_sites('top_10k.csv', count)
    client = Client()

    blacklist = ['akamai', 'xhamster', 'imgur']
    sites = [s for s in sites if all([bls not in s for bls in blacklist])]

    # just adding www takes care of 65% of redirects
    client_resps = [client.get.async('http://www.' + s + '/') for s in sites]
    join(client_resps, raise_exc=False, timeout=30.0)
    # [cr.norm_timings['complete'] for cr in client_resps if cr.raw_response]
    import pdb;pdb.set_trace()


def do_single(client, site, timeout=TIMEOUT):
    res = client.get('http://' + site + '/', timeout=timeout)
    if is_supported_redirect(res.response.status_code):
        res = follow_next_redirect(res)
        if is_supported_redirect(res.response.status_code):
            res = follow_next_redirect(res)
            if is_supported_redirect(res.response.status_code):
                res = follow_next_redirect(res)  # lol RECURSE
    print res.raw_response
    return res


def is_supported_redirect(status_code):
    return 300 < status_code < 309


def follow_next_redirect(client_resp, timeout=TIMEOUT):
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

    return client_resp.client.request(request=new_req, timeout=timeout)


def main():
    import argparse

    a = argparse.ArgumentParser()
    a.add_argument('--single')
    a.add_argument('--top-n', '-n', type=int, default=10)
    a.add_argument('--output', '-o', default=None,
                   help='path to output file: "-" means stdout')
    args = a.parse_args()
    if args.single:
        client = Client()
        do_single(client, args.single)
    else:
        do_survey(args.top_n)


if __name__ == '__main__':
    #do_async_survey(100)
    main()
