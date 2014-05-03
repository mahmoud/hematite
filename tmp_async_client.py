
import time

from hematite.client import Client
from hematite.request import Request
from hematite.response import ClientResponse


MAX_STATE = 7  # obvs tmp


def main():
    client = Client()
    req = Request('GET', 'http://en.wikipedia.org/wiki/Main_Page')
    resp = ClientResponse(client=client, request=req)
    join([resp])
    import pdb;pdb.set_trace()


def join(reqs, timeout=5.0, raise_exc=True):
    ret = reqs
    to_proc = list(reqs)
    cutoff_time = time.time() + timeout
    while to_proc and time.time() < cutoff_time:
        for req in to_proc:
            req.process()
        to_proc = [r for r in to_proc if not r.is_complete]
        import pdb;pdb.set_trace()
    return ret


if __name__ == '__main__':
    main()
