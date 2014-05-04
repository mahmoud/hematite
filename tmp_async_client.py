
import time
import select

from hematite.client import Client
from hematite.request import Request
from hematite.response import ClientResponse


def main():
    client = Client()
    req = Request('GET', 'http://en.wikipedia.org/wiki/Main_Page')
    resp = ClientResponse(client=client, request=req)
    # TODO: where to control automatic fetching of content and
    # following of redirects? join arg, ClientResponse attr, Client
    # default (internally falling back on ClientProfile)
    join([resp])
    import pdb;pdb.set_trace()


def join(reqs, timeout=5.0, raise_exc=True,
         follow_redirects=None, select_timeout=0.05):
    ret = list(reqs)
    cutoff_time = time.time() + timeout

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
        if readers or writers:
            read_ready, write_ready, _ = select.select(readers,
                                                       writers,
                                                       [],
                                                       timeout)
            for wr in write_ready:
                wr.do_write()
            for rr in read_ready:
                rr.do_read()
    import pdb;pdb.set_trace()
    return ret


if __name__ == '__main__':
    main()
