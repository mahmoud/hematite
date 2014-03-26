# -*- coding: utf-8 -*-

from hematite import Client

client = Client()

# some unicode URL examples
#url_bytes = b'http://magyarorsz\xc3\xa1g.icom.museum'
#url_ref_text = u'http://magyarország.icom.museum'
#url_encoded = u'xn--magyarorszg-t7a.icom.museum'

url_ref_text = u'http://en.wikipedia.org/wiki/Coffee'
resp = client.get(url_ref_text)
resp_data = resp.get_data()

print resp_data[:1024]


def ideal_async():
    from hematite import async
    urls = ['http://en.wikipedia.org/wiki/Coffee',
            'http://en.wikipedia.org/wiki/Tea']

    client = Client()
    resps = [client.get(u, async=True) for u in urls]
    async.join(resps, timeout=30.0)

    for resp in resps:
        print resp.get_data()
