
from hematite.client import Client
from hematite.request import Request
from hematite.raw.datastructures import Body

DEFAULT_URL = 'http://localhost:5000/debug'


def test_post(url):
    client = Client()
    req = Request('POST', url, body='{}')
    req.content_type = 'application/json'
    print client.request(request=req, timeout=300.0)


def main():
    import argparse
    prs = argparse.ArgumentParser()
    prs.add_argument('url', nargs='?', default=DEFAULT_URL)
    args = prs.parse_args()
    test_post(url=args.url)


if __name__ == '__main__':
    main()
