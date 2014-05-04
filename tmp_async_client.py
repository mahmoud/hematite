
import time
import select

from hematite.client import Client
from hematite.request import Request
from hematite.response import ClientResponse


def main():
    client = Client()
    req = Request('GET', 'http://en.wikipedia.org/wiki/Main_Page')
    #req = Request('GET', 'http://hatnote.com/')
    resp = ClientResponse(client=client, request=req)
    resp2 = ClientResponse(client=client, request=req)
    # TODO: where to control automatic fetching of content and
    # following of redirects? join arg, ClientResponse attr, Client
    # default (internally falling back on ClientProfile)
    join([resp, resp2], timeout=5.0)

    assert resp.raw_response.headers != resp2.raw_response.headers
    assert resp.get_data() == resp2.get_data()
    import pdb;pdb.set_trace()


def join(reqs, timeout=5.0, raise_exc=True,
         follow_redirects=None, select_timeout=0.05):
    ret = list(reqs)
    cutoff_time = time.time() + timeout
    _st = select_timeout
    while True:
        not_connected = [r for r in reqs if r.socket is None]
        readers = [r for r in reqs if r.fileno() and r.want_read]
        writers = [r for r in reqs if r.fileno() and r.want_write]

        if not (readers or writers or not_connected):
            break
        if time.time() > cutoff_time:
            # TODO: is time.time monotonic?
            break
        for r in not_connected:
            r.process()
        if not (readers or writers):
            continue
        read_ready, write_ready, _ = select.select(readers, writers, [], _st)
        for wr in write_ready:
            wr.do_write()
        for rr in read_ready:
            rr.do_read()
    return ret


if __name__ == '__main__':
    main()
