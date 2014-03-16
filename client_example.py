
from hematite import Client

client = Client()

resp = client.get('http://en.wikipedia.org/wiki/Coffee')
resp_data = resp.get_data()

print resp_data[:1024]


def ideal_async():
    from hematite import async
    urls = ['http://en.wikipedia.org/wiki/Coffee',
            'http://en.wikipedia.org/wiki/Tea']

    client = Client()
    reqs = [client.get(u, async=True) for u in urls]
    async.join(reqs, timeout=30.0)

    for req in reqs:
        print req.response
