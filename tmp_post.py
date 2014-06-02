
from hematite.client import Client
from hematite.request import Request
from hematite.raw.datastructures import Body

DEFAULT_URL = 'http://localhost:5000/debug'


def test_post(url):
    client = Client()
    req = Request('POST', url, body='{}')
    req.content_type = 'application/json'
    client_resp = client.request(request=req, timeout=300.0)
    import pdb
    pdb.set_trace()


def main():
    import argparse
    prs = argparse.ArgumentParser()
    prs.add_argument('url', nargs='?', default=DEFAULT_URL)
    args = prs.parse_args()
    test_post(url=args.url)


if __name__ == '__main__':
    main()
