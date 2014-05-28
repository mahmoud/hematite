
import time
import select

from hematite.client import Client
from hematite.request import Request
from hematite.response import ClientResponse

# NOTE: hatnote.com returns the funniest response when the request
# line is omitted (encountered due to socket_io.py bug)


def main():
    client = Client()
    req = Request('GET', 'http://makuro.org/')
    #req = Request('GET', 'http://en.wikipedia.org/wiki/Main_Page')
    #req = Request('GET', 'http://hatnote.com/')
    resp = ClientResponse(client=client, request=req)
    resp2 = ClientResponse(client=client, request=req)
    resp.nonblocking = True
    resp2.nonblocking = True
    # TODO: where to control automatic fetching of content and
    # following of redirects? join arg, ClientResponse attr, Client
    # default (internally falling back on ClientProfile)
    join([resp], timeout=5.0)

    # true for wikipedia:
    # assert resp.raw_response.headers != resp2.raw_response.headers
    #assert resp.get_data() == resp2.get_data()
    print resp.raw_response
    import pdb;pdb.set_trace()


def join(reqs, timeout=5.0, raise_exc=True,
         follow_redirects=None, select_timeout=0.05):
    ret = list(reqs)
    cutoff_time = time.time() + timeout

    while True:
        readers = [r for r in reqs if r.want_read]
        writers = [r for r in reqs if r.want_write]

        # forced writers are e.g., resolving/connecting, don't have sockets yet
        forced_writers = [r for r in writers if r.fileno() is None]
        selectable_writers = [r for r in writers if r.fileno() is not None]

        if not (readers or writers):
            break
        if time.time() > cutoff_time:
            # TODO: is time.time monotonic? no, so... time.clock()?
            break

        if readers or selectable_writers:
            read_ready, write_ready, _ = select.select(readers,
                                                       selectable_writers,
                                                       [],
                                                       select_timeout)
            write_ready.extend(forced_writers)
        else:
            read_ready = []
            write_ready = forced_writers
        for wr in write_ready:
            while True:
                _keep_writing = wr.do_write()
                if not _keep_writing:
                    break
        for rr in read_ready:
            while True:
                _keep_reading = rr.do_read()
                if not _keep_reading:
                    break
    return ret


if __name__ == '__main__':
    main()


class Joinable(object):
    "just a sketch of an interface"

    def fileno():
        pass  # None if not selectable

    # TODO: attribute/property?
    def want_read(self):
        pass

    def want_write(self):
        pass

    def do_read(self):
        pass

    def do_write(self):
        pass

    def is_complete(self):
        # can this be implicit from not wanting read or write?
        pass
