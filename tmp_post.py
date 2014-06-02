
from hematite.client import Client
from hematite.request import Request

DEFAULT_URL = 'http://localhost:5000/debug'


def test_post(url):
    client = Client()
    data = '{}'  # 'a' * 2 ** 22
    req = Request('POST', url, body=data)
    req.content_type = 'application/json'
    client_resp = client.request(request=req)
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
